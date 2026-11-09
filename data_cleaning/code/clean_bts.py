"""
Clean the BTS on-time performance file (D2) into the Milestone 2 tables.

Usage:
    python clean_bts.py --input ../../flight_delays_2025_01.csv --out output

Writes (all ready for PostgreSQL COPY ... CSV HEADER):
    bts_airport.csv        airport_code, city, state          (Origin*/Dest* columns)
    bts_airline.csv        airline_code, airline_name
    bts_route.csv          origin_code, destination_code, distance_miles
    flight_operation.csv   one row per scheduled flight, operation_id = 1..n
    delayed_flight.csv     one row per flight with ArrDel15 = 1 (delay causes)
    bts_rejects.csv        rows that could not be loaded, with the reason
    report_bts.md          what every check found

Rules (from the project outline):
  - airport and airline codes are trimmed and upper-cased, then checked for format
  - dates and local HHMM times are validated; out-of-range times become a reject
  - negative delays are kept (early departures / arrivals)
  - cancelled and diverted flights stay in; missing actual times and delays stay null
  - duplicate operations are checked on (FlightDate, airline, flight number, Origin)
  - delay causes are checked for completeness and that they add up to ArrDelay
  - cancelled = (cancellation_code is not null) and actual elapsed time are not stored,
    but both are checked here so dropping them loses nothing
"""
import argparse
import os

import numpy as np
import pandas as pd

from common import AIRLINE_RE, AIRPORT_RE, BTS_AIRLINE_NAMES, Report, std_code

CAUSES = {
    "CarrierDelay": "carrier_delay_min",
    "WeatherDelay": "weather_delay_min",
    "NASDelay": "nas_delay_min",
    "SecurityDelay": "security_delay_min",
    "LateAircraftDelay": "late_aircraft_delay_min",
}


def num(s):
    return pd.to_numeric(s, errors="coerce")


def hhmm_ok(s: pd.Series) -> pd.Series:
    """True where an HHMM value is null or a valid local clock time (0000-2400)."""
    v = num(s)
    return v.isna() | ((v >= 0) & (v <= 2400) & (v % 100 < 60))


def minutes(hhmm: pd.Series) -> pd.Series:
    v = num(hhmm)
    return (v // 100) * 60 + v % 100


def clock_diff(actual, scheduled):
    """actual - scheduled in minutes, wrapped to (-720, 720] to handle midnight."""
    d = minutes(actual) - minutes(scheduled)
    return ((d + 720) % 1440) - 720


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="../../flight_delays_2025_01.csv")
    ap.add_argument("--out", default="output")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    rep = Report("BTS flight performance (D2) cleaning report")

    raw = pd.read_csv(args.input, dtype=str, keep_default_na=False, na_values=[""])
    rep.section("Input")
    rep.add("file", os.path.basename(args.input))
    rep.add("rows", len(raw))
    rep.add("columns", len(raw.columns))
    df = raw.copy()
    reject = pd.Series("", index=df.index)

    def flag(mask, reason):
        nonlocal reject
        mask = mask.fillna(False)
        reject = reject.where(~mask | (reject != ""), reason)
        return int(mask.sum())

    # ---------------- codes ----------------
    rep.section("Airport and airline codes")
    for c in ["Origin", "Dest", "Reporting_Airline", "OriginState", "DestState"]:
        changed = int((df[c].fillna("") != std_code(df[c]).fillna("")).sum())
        df[c] = std_code(df[c])
        rep.add(f"{c}: values changed by trim/upper-case", changed)
    bad_ap = ~df["Origin"].fillna("").str.match(AIRPORT_RE) | ~df["Dest"].fillna("").str.match(AIRPORT_RE)
    rep.add("rows with an airport code that is not 3 letters (rejected)", flag(bad_ap, "bad airport code"))
    bad_al = ~df["Reporting_Airline"].fillna("").str.match(AIRLINE_RE)
    rep.add("rows with a malformed airline code (rejected)", flag(bad_al, "bad airline code"))
    rep.add("rows with Origin = Dest (rejected)", flag(df["Origin"] == df["Dest"], "origin equals destination"))
    rep.add("distinct airports", int(pd.concat([df.Origin, df.Dest]).nunique()))
    rep.add("distinct airlines", int(df.Reporting_Airline.nunique()))
    unknown = sorted(set(df.Reporting_Airline.dropna()) - set(BTS_AIRLINE_NAMES))
    rep.add("airline codes with no name in the lookup", ", ".join(unknown) or "none")

    # airport -> city/state must be a function (it becomes the airport table)
    places = pd.concat([
        df[["Origin", "OriginCityName", "OriginState"]].set_axis(["airport_code", "city", "state"], axis=1),
        df[["Dest", "DestCityName", "DestState"]].set_axis(["airport_code", "city", "state"], axis=1),
    ]).drop_duplicates()
    multi = places.groupby("airport_code").size()
    rep.add("airports with more than one city/state spelling", int((multi > 1).sum()))
    bad_state = ~places["state"].fillna("").str.match(r"^[A-Z]{2}$")
    rep.add("airports whose state is not a 2-letter code", int(bad_state.sum()))

    # ---------------- dates ----------------
    rep.section("Dates")
    fd = pd.to_datetime(df["FlightDate"], format="%Y-%m-%d", errors="coerce")
    rep.add("unparseable FlightDate (rejected)", flag(fd.isna(), "bad FlightDate"))
    parts_ok = (fd.dt.year == num(df.Year)) & (fd.dt.month == num(df.Month)) & \
               (fd.dt.day == num(df.DayofMonth)) & (fd.dt.quarter == num(df.Quarter)) & \
               (fd.dt.day_of_week + 1 == num(df.DayOfWeek))
    rep.add("rows where Year/Quarter/Month/DayofMonth/DayOfWeek disagree with FlightDate", int((~parts_ok & fd.notna()).sum()))
    rep.add("date range", f"{fd.min().date()} to {fd.max().date()}")

    # ---------------- times ----------------
    rep.section("Local HHMM times")
    for c in ["CRSDepTime", "DepTime", "CRSArrTime", "ArrTime"]:
        n = flag(~hhmm_ok(df[c]), f"bad {c}")
        rep.add(f"{c}: out-of-range values (rejected)", n)
        rep.add(f"{c}: null", int(df[c].isna().sum()))
        rep.add(f"{c}: value 2400 (BTS midnight, kept as 2400)", int((num(df[c]) == 2400).sum()))
    rep.add("scheduled times missing (rejected)", flag(df.CRSDepTime.isna() | df.CRSArrTime.isna(), "missing scheduled time"))

    # ---------------- status ----------------
    rep.section("Status indicators")
    canc, div = num(df.Cancelled), num(df.Diverted)
    rep.add("Cancelled not 0/1 (rejected)", flag(~canc.isin([0, 1]), "bad Cancelled"))
    rep.add("Diverted not 0/1 (rejected)", flag(~div.isin([0, 1]), "bad Diverted"))
    rep.add("cancelled flights (kept)", int((canc == 1).sum()))
    rep.add("diverted flights (kept)", int((div == 1).sum()))
    cc = std_code(df.CancellationCode)
    df["CancellationCode"] = cc
    rep.add("CancellationCode outside A/B/C/D (rejected)", flag(cc.notna() & ~cc.isin(list("ABCD")), "bad CancellationCode"))
    mism = ((canc == 1) & cc.isna()) | ((canc == 0) & cc.notna())
    rep.add("Cancelled flag disagrees with CancellationCode (rejected; cancelled is derived from the code)",
            flag(mism, "Cancelled/CancellationCode mismatch"))
    rep.add("cancelled AND diverted (rejected, breaks CHECK)", flag((canc == 1) & (div == 1), "cancelled and diverted"))
    rep.add("cancellation codes", cc.value_counts().to_dict())
    rep.add("cancelled flights that still have a DepTime (pushed back then cancelled; kept)",
            int(((canc == 1) & df.DepTime.notna()).sum()))
    rep.add("non-cancelled, non-diverted flights missing ArrTime or ArrDelay",
            int(((canc == 0) & (div == 0) & (df.ArrTime.isna() | df.ArrDelay.isna())).sum()))
    rep.add("diverted flights with an ArrDelay (BTS normally leaves it null)", int(((div == 1) & df.ArrDelay.notna()).sum()))

    # ---------------- delays and durations ----------------
    rep.section("Delay values")
    for c in ["DepDelay", "ArrDelay", "TaxiOut", "TaxiIn", "CRSElapsedTime", "AirTime", "Distance"]:
        v = num(df[c])
        rep.add(f"{c}: non-numeric (rejected)", flag(df[c].notna() & v.isna(), f"bad {c}"))
        if c in ("DepDelay", "ArrDelay"):
            rep.add(f"{c}: negative (early, kept)", int((v < 0).sum()))
            rep.add(f"{c}: null (kept as null)", int(v.isna().sum()))
            rep.add(f"{c}: min / max", f"{v.min():g} / {v.max():g}")
        else:
            rep.add(f"{c}: <= 0 where present", int((v <= 0).sum()))
        rep.add(f"{c}: non-integer values", int((v.notna() & (v % 1 != 0)).sum()))
    dep_chk = clock_diff(df.DepTime, df.CRSDepTime)
    dd = num(df.DepDelay)
    rep.add("DepDelay != DepTime - CRSDepTime (mod 24h), excluding delays over 12h",
            int(((dep_chk - dd).abs() > 0)[dd.notna() & (dd.abs() < 720)].sum()))
    arr_chk = clock_diff(df.ArrTime, df.CRSArrTime)
    ad = num(df.ArrDelay)
    rep.add("ArrDelay != ArrTime - CRSArrTime (mod 24h), excluding delays over 12h",
            int(((arr_chk - ad).abs() > 0)[ad.notna() & (ad.abs() < 720)].sum()))
    dm = num(df.DepDelayMinutes)
    rep.add("DepDelayMinutes != max(DepDelay, 0) (column not stored)", int(((dm - dd.clip(lower=0)).abs() > 0).sum()))
    d15 = num(df.ArrDel15)
    rep.add("ArrDel15 != (ArrDelay >= 15) (column not stored)", int(((ad >= 15).astype(float).where(ad.notna()) != d15)[d15.notna()].sum()))
    ae = num(df.ActualElapsedTime)
    parts = num(df.TaxiOut) + num(df.AirTime) + num(df.TaxiIn)
    rep.add("ActualElapsedTime != TaxiOut + AirTime + TaxiIn (column not stored)", int(((ae - parts).abs() > 0)[ae.notna()].sum()))

    # ---------------- delay causes ----------------
    rep.section("Delay-cause completeness")
    cause = df[list(CAUSES)].apply(num)
    has_any = cause.notna().any(axis=1)
    has_all = cause.notna().all(axis=1)
    rep.add("flights with ArrDel15 = 1", int((d15 == 1).sum()))
    rep.add("flights with delay-cause values", int(has_any.sum()))
    rep.add("flights with only some of the five causes filled", int((has_any & ~has_all).sum()))
    rep.add("ArrDel15 = 1 but no causes", int(((d15 == 1) & ~has_any).sum()))
    rep.add("causes present but ArrDel15 != 1", int((has_any & (d15 != 1)).sum()))
    rep.add("negative cause minutes", int((cause < 0).sum().sum()))
    rep.add("causes that do not add up to ArrDelay", int(((cause.sum(axis=1) - ad).abs() > 0)[has_all].sum()))

    # ---------------- duplicates ----------------
    rep.section("Duplicate operation records")
    key = ["FlightDate", "Reporting_Airline", "Flight_Number_Reporting_Airline", "Origin"]
    rep.add("exact duplicate rows (dropped, first kept)", int(df.duplicated().sum()))
    exact = df.duplicated()
    rep.add("rows sharing the candidate key (FlightDate, airline, flight number, Origin), excluding exact copies",
            flag(df[~exact].duplicated(key, keep="first").reindex(df.index, fill_value=False), "duplicate key"))
    fn = num(df.Flight_Number_Reporting_Airline)
    rep.add("flight number missing or not a positive integer (rejected)",
            flag(fn.isna() | (fn <= 0) | (fn % 1 != 0), "bad flight number"))

    # ---------------- route distance ----------------
    rep.section("Route distance")
    dist = num(df.Distance)
    per_route = pd.DataFrame({"o": df.Origin, "d": df.Dest, "dist": dist}).dropna().groupby(["o", "d"]).dist.nunique()
    rep.add("routes", len(per_route))
    rep.add("routes with more than one Distance value", int((per_route > 1).sum()))
    rd = pd.DataFrame({"o": df.Origin, "d": df.Dest, "dist": dist}).dropna().groupby(["o", "d"]).dist.first()
    rev = rd.rename_axis(["d", "o"]).reorder_levels(["o", "d"])
    both = rd.to_frame("ab").join(rev.to_frame("ba"), how="inner")
    rep.add("routes whose A->B distance differs from B->A", int((both.ab != both.ba).sum()))
    rep.add("distance <= 0 (rejected)", flag(dist <= 0, "bad Distance"))

    # ---------------- outputs ----------------
    rep.section("Output")
    ok = (reject == "") & ~exact
    rej = raw[(reject != "")].assign(reject_reason=reject[reject != ""])
    rej.to_csv(os.path.join(args.out, "bts_rejects.csv"), index=False)
    rep.add("rows rejected", len(rej))
    if len(rej):
        rep.add("reject reasons", rej.reject_reason.value_counts().to_dict())
    g = df[ok].reset_index(drop=True)

    def int_col(c):
        return num(g[c]).round().astype("Int64")

    op = pd.DataFrame({
        "operation_id": np.arange(1, len(g) + 1),
        "flight_date": g.FlightDate,
        "flight_number": int_col("Flight_Number_Reporting_Airline"),
        "scheduled_dep_hhmm": int_col("CRSDepTime"),
        "actual_dep_hhmm": int_col("DepTime"),
        "scheduled_arr_hhmm": int_col("CRSArrTime"),
        "actual_arr_hhmm": int_col("ArrTime"),
        "dep_delay_min": int_col("DepDelay"),
        "arr_delay_min": int_col("ArrDelay"),
        "taxi_out_min": int_col("TaxiOut"),
        "taxi_in_min": int_col("TaxiIn"),
        "cancellation_code": g.CancellationCode,
        "diverted": num(g.Diverted) == 1,
        "scheduled_elapsed_min": int_col("CRSElapsedTime"),
        "air_time_min": int_col("AirTime"),
        "origin_code": g.Origin,
        "destination_code": g.Dest,
        "airline_code": g.Reporting_Airline,
    })
    op.to_csv(os.path.join(args.out, "flight_operation.csv"), index=False)
    rep.add("flight_operation rows", len(op))

    dl = g[num(g.ArrDel15) == 1]
    delayed = pd.DataFrame({"operation_id": op.operation_id[dl.index]})
    for src, dst in CAUSES.items():
        delayed[dst] = num(dl[src]).round().astype("Int64")
    incomplete = delayed.drop(columns="operation_id").isna().any(axis=1)
    delayed = delayed[~incomplete]
    delayed.to_csv(os.path.join(args.out, "delayed_flight.csv"), index=False)
    rep.add("delayed_flight rows", len(delayed))
    rep.add("ArrDel15 = 1 flights left out because a cause is missing", int(incomplete.sum()))

    airports = (places[places.airport_code.isin(set(g.Origin) | set(g.Dest))]
                .drop_duplicates("airport_code").sort_values("airport_code"))
    airports.to_csv(os.path.join(args.out, "bts_airport.csv"), index=False)
    rep.add("airports", len(airports))

    airlines = pd.DataFrame({"airline_code": sorted(g.Reporting_Airline.unique())})
    airlines["airline_name"] = airlines.airline_code.map(BTS_AIRLINE_NAMES)
    airlines.to_csv(os.path.join(args.out, "bts_airline.csv"), index=False)
    rep.add("airlines", len(airlines))

    routes = (pd.DataFrame({"origin_code": g.Origin, "destination_code": g.Dest, "distance_miles": num(g.Distance)})
              .groupby(["origin_code", "destination_code"]).distance_miles.agg(lambda s: s.mode().iloc[0])
              .round().astype("Int64").reset_index())
    routes.to_csv(os.path.join(args.out, "bts_route.csv"), index=False)
    rep.add("routes", len(routes))

    rep.write(os.path.join(args.out, "report_bts.md"))


if __name__ == "__main__":
    main()
