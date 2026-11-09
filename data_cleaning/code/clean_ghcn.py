"""
Clean the NOAA GHCN-Daily raw file (D3) into the Milestone 2 weather tables.

Usage:
    python clean_ghcn.py --input ../../milestone1/ghcn2025/ghcn_raw_2025.csv --out output
        [--bts-airports output/bts_airport.csv]

Writes:
    weather_station.csv       station_id, airport_code
    weather_observation.csv   station_id, observation_date, element_code, raw_value, mflag, sflag
                              (long format: one row per station, date and element)
    ghcn_rejects.csv          measurements left out, with the reason
    report_ghcn.md            what every check found

Rules (from the project outline):
  - every airport maps to exactly one station and every station to one airport; airport
    stations must be the USW000 + WBAN id that ghcn_download.py fetched
  - values that failed NOAA quality control (qflag not blank), the -9999 missing code,
    non-numeric values and physically impossible values are left out, never set to 0
  - raw values (NOAA units, e.g. tenths of degC), mflag and sflag are kept as they are
  - obstime is not a column of weather_observation (BCNF fix: station+element -> obstime);
    it stays in the raw file, and the check below confirms that dependency still holds
"""
import argparse
import os

import pandas as pd

from common import AIRPORT_RE, Report, std_code

# Station list the raw file was downloaded from (milestone1/ghcn_download.py)
WBAN = {
    "ATL": "13874", "AUS": "13904", "BNA": "13897", "BOS": "14739", "BWI": "93721",
    "CLT": "13881", "DCA": "13743", "DEN": "03017", "DFW": "03927", "DTW": "94847",
    "EWR": "14734", "FLL": "12849", "IAD": "93738", "IAH": "12960", "JFK": "94789",
    "LAS": "23169", "LAX": "23174", "LGA": "14732", "MCO": "12815", "MDW": "14819",
    "MIA": "12839", "MSP": "14922", "OAK": "23230", "ORD": "94846", "PHL": "13739",
    "PHX": "23183", "SAN": "23188", "SEA": "24233", "SFO": "23234", "SLC": "24127",
    "TPA": "12842", "HNL": "22521",
}

# Plausible range per element, in raw GHCN units (inclusive). Values outside are invalid.
RANGES = {
    "TMAX": (-600, 600), "TMIN": (-600, 600), "TAVG": (-600, 600),  # tenths of degC
    "PRCP": (0, 10000),                                              # tenths of mm
    "SNOW": (0, 2000), "SNWD": (0, 5000), "WESD": (0, 5000),         # mm
    "AWND": (0, 1000), "WSF2": (0, 1000), "WSF5": (0, 1500),         # tenths of m/s
    "WDF2": (0, 360), "WDF5": (0, 360),                              # degrees
    "PSUN": (0, 100),                                                # percent
    "TSUN": (0, 1440),                                               # minutes
}
HHMM_ELEMENTS = {"PGTM", "FMTM"}  # time of peak gust, HHMM
QFLAGS = set("DGIKLMNORSTWXZ")
MFLAGS = set("BDHKLOPTUW")
SFLAGS = set("0678ABCEFGHIKMNQRSTUWXZ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="../../milestone1/ghcn2025/ghcn_raw_2025.csv")
    ap.add_argument("--out", default="output")
    ap.add_argument("--bts-airports", default="output/bts_airport.csv",
                    help="airport list from clean_bts.py, to check the weather airports exist there")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    rep = Report("GHCN weather (D3) cleaning report")

    raw = pd.read_csv(args.input, dtype=str, keep_default_na=False)
    df = raw.copy()
    rep.section("Input")
    rep.add("file", os.path.basename(args.input))
    rep.add("rows", len(df))
    rep.add("columns", ", ".join(df.columns))
    for c in ["airport_code", "id", "element", "mflag", "qflag", "sflag"]:
        df[c] = std_code(df[c])
    df["obstime"] = df["obstime"].str.strip().replace("", pd.NA)

    # ---------------- station mapping ----------------
    rep.section("Airport-to-station mapping")
    pairs = df[["airport_code", "id"]].drop_duplicates()
    rep.add("airports", int(pairs.airport_code.nunique()))
    rep.add("stations", int(pairs.id.nunique()))
    rep.add("airports with more than one station", int((pairs.groupby("airport_code").size() > 1).sum()))
    rep.add("stations with more than one airport", int((pairs.groupby("id").size() > 1).sum()))
    rep.add("airport codes that are not 3 letters", int((~pairs.airport_code.fillna("").str.match(AIRPORT_RE)).sum()))
    expected = pairs.airport_code.map(lambda a: "USW000" + WBAN[a] if a in WBAN else None)
    wrong = pairs[pairs.id != expected]
    rep.add("stations that are not the expected USW000+WBAN airport station", len(wrong))
    if len(wrong):
        rep.table(wrong.assign(expected=expected[wrong.index]))
    rep.add("airports in the download list but missing from the file",
            ", ".join(sorted(set(WBAN) - set(pairs.airport_code))) or "none")
    if os.path.exists(args.bts_airports):
        bts = set(pd.read_csv(args.bts_airports, dtype=str).airport_code)
        rep.add("weather airports not in the BTS airport list",
                ", ".join(sorted(set(pairs.airport_code) - bts)) or "none")
    bad_station = pairs.id.isna() | pairs.airport_code.isna()
    if bad_station.any():
        raise SystemExit("rows with blank station or airport; fix the raw file first")

    # ---------------- dates, elements, flags ----------------
    rep.section("Dates, elements and flags")
    d = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
    df["observation_date"] = d.dt.strftime("%Y-%m-%d")
    rep.add("date range", f"{d.min().date()} to {d.max().date()}")
    reason = pd.Series("", index=df.index)

    def drop(mask, why):
        nonlocal reason
        mask = mask.fillna(False)
        reason = reason.where(~mask | (reason != ""), why)
        return int(mask.sum())

    rep.add("unparseable dates (left out)", drop(d.isna(), "bad date"))
    rep.add("elements", df.element.value_counts().to_dict())
    rep.add("element codes longer than 4 characters (left out)", drop(df.element.str.len() > 4, "bad element"))
    rep.add("qflag values", df.qflag.value_counts(dropna=False).to_dict())
    rep.add("failed NOAA quality control, qflag not blank (left out)", drop(df.qflag.notna(), "qflag " + df.qflag.fillna("")))
    rep.add("mflag values (kept)", df.mflag.value_counts(dropna=False).to_dict())
    rep.add("mflag codes not in this script's list (kept)", int((df.mflag.notna() & ~df.mflag.isin(MFLAGS)).sum()))
    rep.add("sflag values (kept)", df.sflag.value_counts(dropna=False).to_dict())
    rep.add("sflag codes not in this script's list (kept; check the GHCN readme)", int((df.sflag.notna() & ~df.sflag.isin(SFLAGS)).sum()))
    rep.add("multi-character flags (left out, column is CHAR(1))",
            drop((df.mflag.str.len() > 1) | (df.sflag.str.len() > 1), "flag too long"))

    # ---------------- values ----------------
    rep.section("Measurement values")
    v = pd.to_numeric(df.value, errors="coerce")
    rep.add("blank or non-numeric values (left out)", drop(v.isna(), "missing or non-numeric value"))
    rep.add("-9999 missing code (left out)", drop(v == -9999, "missing code -9999"))
    rep.add("non-integer values (left out)", drop(v.notna() & (v % 1 != 0), "non-integer value"))
    out_of_range = pd.Series(False, index=df.index)
    for el, (lo, hi) in RANGES.items():
        m = (df.element == el) & ((v < lo) | (v > hi))
        out_of_range |= m
    out_of_range |= df.element.str.match(r"^WT\d\d$").fillna(False) & (v != 1)
    hh = df.element.isin(HHMM_ELEMENTS)
    out_of_range |= hh & ((v < 0) | (v > 2359) | (v % 100 >= 60))
    rep.add("physically impossible values (left out)", drop(out_of_range, "out of range"))
    trace = (df.mflag == "T")
    rep.add("trace (mflag T) rows and their values", f"{int(trace.sum())} rows, values {sorted(v[trace].unique().tolist())}")
    known = set(RANGES) | HHMM_ELEMENTS
    other = sorted(set(df.element) - known - set(df.element[df.element.str.match(r'^WT\d\d$')]))
    rep.add("elements with no range check", ", ".join(other) or "none")

    # TMAX < TMIN on the same station-day: both readings are suspect, so both are left out
    t = df.assign(v=v)[df.element.isin(["TMAX", "TMIN"]) & (reason == "")]
    tw = t.pivot_table(index=["id", "date"], columns="element", values="v", aggfunc="first")
    bad_days = tw[(tw.get("TMAX") < tw.get("TMIN"))].index if {"TMAX", "TMIN"} <= set(tw.columns) else []
    bad_idx = df.set_index(["id", "date"]).index.isin(bad_days) & df.element.isin(["TMAX", "TMIN"])
    rep.add("station-days with TMAX < TMIN (both left out)", len(bad_days))
    drop(pd.Series(bad_idx, index=df.index), "TMAX < TMIN")

    # ---------------- duplicates and completeness ----------------
    rep.section("Duplicates and completeness")
    key = ["id", "date", "element"]
    rep.add("exact duplicate rows (dropped)", int(df.duplicated().sum()))
    dupkey = df.duplicated(key, keep=False) & ~df.duplicated(keep=False)
    rep.add("conflicting rows for the same station, date and element (all left out)", drop(dupkey, "conflicting duplicate"))
    df = df[~df.duplicated()]
    reason = reason[df.index]

    days = pd.date_range(d.min(), d.max()).size
    core = ["TMAX", "TMIN", "PRCP", "AWND", "SNOW", "SNWD"]
    kept = df[reason == ""]
    cov = (kept[kept.element.isin(core)].groupby(["airport_code", "element"]).size()
           .unstack(fill_value=0).reindex(columns=core, fill_value=0))
    miss = (days - cov).reset_index()
    rep.add(f"missing days per airport for the core elements (out of {days} days)")
    rep.table(miss)
    rep.add("note", "SNOW/SNWD are often not reported at warm-climate airports; a missing row means 'not reported', not 0")

    # obstime dependency check (justifies dropping it from the table)
    ot = df[df.obstime.notna()].groupby(["id", "element"]).obstime.nunique()
    rep.add("obstime filled", f"{int(df.obstime.notna().sum())} of {len(df)} rows")
    rep.add("(station, element) pairs with more than one obstime", int((ot > 1).sum()))
    rep.add("obstime values", df.obstime.value_counts(dropna=False).to_dict())

    # ---------------- outputs ----------------
    rep.section("Output")
    rej = df[reason != ""].assign(reject_reason=reason[reason != ""])
    rej.drop(columns=["observation_date"]).to_csv(os.path.join(args.out, "ghcn_rejects.csv"), index=False)
    rep.add("measurements left out", len(rej))
    if len(rej):
        rep.add("reasons", rej.reject_reason.value_counts().to_dict())
    k = df[reason == ""]
    obs = pd.DataFrame({
        "station_id": k.id, "observation_date": k.observation_date, "element_code": k.element,
        "raw_value": pd.to_numeric(k.value).astype(int), "mflag": k.mflag, "sflag": k.sflag,
    }).sort_values(["station_id", "observation_date", "element_code"])
    obs.to_csv(os.path.join(args.out, "weather_observation.csv"), index=False)
    rep.add("weather_observation rows", len(obs))
    st = pairs.rename(columns={"id": "station_id"})[["station_id", "airport_code"]].sort_values("airport_code")
    st.to_csv(os.path.join(args.out, "weather_station.csv"), index=False)
    rep.add("weather_station rows", len(st))
    rep.write(os.path.join(args.out, "report_ghcn.md"))


if __name__ == "__main__":
    main()
