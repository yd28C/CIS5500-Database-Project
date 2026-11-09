"""
Clean the Expedia flight-prices file (D1, itineraries.csv, ~31 GB) into the Milestone 2 tables,
reading it in chunks so it never has to fit in memory.

Usage (on the computer that has the file):
    python clean_itineraries.py --input "C:/Users/judyl/Downloads/itineraries-dataset1.csv" --out output
    python clean_itineraries.py --input ... --out output_test --limit 2000000     # quick trial run

Writes:
    itinerary.csv      leg_id, flight_date, travel_duration, total_travel_distance, is_nonstop
    segment.csv        leg_id, segment_no, departure_at, arrival_at, origin_code, destination_code, airline_code
    fare_quote.csv     quote_id, search_date, total_fare, is_basic_economy, is_refundable, leg_id
    books.csv          quote_id, segment_no, cabin_code
    d1_airport.csv     airport codes seen in D1
    d1_airline.csv     airline_code, airline_name (most common name per code)
    d1_route.csv       origin_code, destination_code, distance_miles (most common segmentsDistance)
    d1_rejects.csv     every rejected input row with the reason (raw columns)
    report_itineraries.md
    _d1_work.sqlite    scratch database used to de-duplicate legIds across chunks (safe to delete)

How the file maps to the schema:
  - one input row = one fare observation (legId on a searchDate with a ticket type), so each
    row becomes one fare_quote; quotes for the same legId on other search dates or with other
    basic-economy / refundable flags are all kept
  - the segments* columns hold one value per flight segment separated by '||'; they are split
    and numbered 1, 2, 3, ... (segment_no); segment rows are written once per legId
  - segmentsCabinCode belongs to the quote, not the itinerary, so it goes to books
    (quote_id, segment_no, cabin_code)

Checks (counted in the report; the ones marked REJECT drop the row):
  - REJECT: legId blank or > 64 chars; searchDate / flightDate not a date; totalFare not a
    number or negative; isBasicEconomy / isRefundable / isNonStop not True/False;
    travelDuration not ISO 8601 (PT#H#M)
  - REJECT: the '||' lists have different lengths; a segment airport is not 3 letters;
    a segment airline code is malformed; a departure/arrival time does not parse;
    arrival not after departure; segment origin = destination
  - REJECT: isNonStop disagrees with the number of segments
  - REJECT: the same legId appears later with different segments, flightDate or isNonStop
    (the first version is kept, so segment numbers in books always exist in segment)
  - kept, counted: first/last segment airport differs from startingAirport/destinationAirport
    (Expedia searches by metro area, e.g. a DFW search returns DAL flights); connection airport changes (arrive LGA, leave JFK); flightDate differs from
    the local date of the first departure; searchDate after flightDate; travelDuration or
    totalTravelDistance differing across rows of a legId; segment durations or distances not
    matching the epoch times or totalTravelDistance; exact duplicate rows within a chunk
"""
import argparse
import os
import re
import sqlite3
import time
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

from common import AIRLINE_RE, AIRPORT_RE, Report, std_code

SEG = {  # raw column -> short name
    "segmentsDepartureTimeEpochSeconds": "dep_epoch",
    "segmentsDepartureTimeRaw": "dep_raw",
    "segmentsArrivalTimeEpochSeconds": "arr_epoch",
    "segmentsArrivalTimeRaw": "arr_raw",
    "segmentsArrivalAirportCode": "arr_ap",
    "segmentsDepartureAirportCode": "dep_ap",
    "segmentsAirlineName": "al_name",
    "segmentsAirlineCode": "al_code",
    "segmentsDurationInSeconds": "dur",
    "segmentsDistance": "dist",
    "segmentsCabinCode": "cabin",
}
BASE = ["legId", "searchDate", "flightDate", "startingAirport", "destinationAirport",
        "travelDuration", "isBasicEconomy", "isRefundable", "isNonStop", "baseFare",
        "totalFare", "totalTravelDistance"]
CABINS = {"coach", "premium coach", "business", "first"}
DUR_RE = re.compile(r"^P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$")
NULLS = {"", "None", "none", "NaN", "nan", "null", "NULL"}


def as_bool(s):
    m = s.str.strip().str.lower().map({"true": True, "false": False})
    return m


def null_out(s):
    s = s.astype("string").str.strip()
    return s.mask(s.isin(NULLS))


def num(s):
    return pd.to_numeric(s, errors="coerce").astype("float64")


def iso_minutes(s):
    p = s.str.extract(DUR_RE)
    ok = s.str.match(DUR_RE) & (p.notna().any(axis=1))
    p = p.astype(float).fillna(0)
    return (p[0] * 1440 + p[1] * 60 + p[2] + p[3] / 60).where(ok), ok


def stable_hash(s: pd.Series) -> pd.Series:
    return pd.util.hash_pandas_object(s, index=False).astype("int64")


class Stats:
    def __init__(self):
        self.c = Counter()

    def __getitem__(self, k):
        return self.c[k]

    def add(self, k, n):
        self.c[k] += int(n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", default="output")
    ap.add_argument("--chunksize", type=int, default=250_000)
    ap.add_argument("--limit", type=int, default=0, help="stop after this many input rows (0 = all)")
    ap.add_argument("--append", action="store_true",
                    help="add rows to an existing --out folder instead of starting over (used by the "
                         "metro-area recovery: --input output/d1_rejects.csv --append)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    P = lambda name: os.path.join(args.out, name)

    db_path = P("_d1_work.sqlite")
    if args.append and not os.path.exists(db_path):
        raise SystemExit(f"--append needs {db_path} from the earlier run")
    if os.path.exists(db_path) and not args.append:
        os.remove(db_path)
    db = sqlite3.connect(db_path)
    db.executescript("""
        PRAGMA journal_mode = OFF; PRAGMA synchronous = OFF; PRAGMA temp_store = MEMORY;
        CREATE TABLE IF NOT EXISTS itin (leg_id TEXT PRIMARY KEY, flight_date TEXT, travel_duration TEXT,
                           total_travel_distance INTEGER, is_nonstop INTEGER, sig INTEGER,
                           dur_min REAL, nseg INTEGER) WITHOUT ROWID;
        CREATE TABLE IF NOT EXISTS seg (leg_id TEXT, segment_no INTEGER, departure_at TEXT, arrival_at TEXT,
                          origin_code TEXT, destination_code TEXT, airline_code TEXT,
                          PRIMARY KEY (leg_id, segment_no)) WITHOUT ROWID;
    """)

    st = Stats()
    route_dist = defaultdict(Counter)
    airline_names = defaultdict(Counter)
    airports = set()
    cabins = Counter()
    alt_pairs = Counter()
    search_range = [None, None]
    flight_range = [None, None]
    days_ahead = Counter()
    quote_id = 0
    first = {"fq": True, "bk": True, "rj": True}
    suffix = ""
    if args.append:
        # continue quote_id after the last one already written
        with open(P("fare_quote.csv"), "rb") as f:
            f.seek(max(0, os.path.getsize(P("fare_quote.csv")) - 4096))
            last = [ln for ln in f.read().decode().splitlines() if ln.strip()][-1]
        quote_id = int(last.split(",")[0])
        first.update(fq=False, bk=False)
        suffix = "_recovered"
        print(f"appending; quote_id continues after {quote_id:,}", flush=True)
    t0 = time.time()

    # open the file ourselves (plain buffered read) rather than letting pandas do it
    src = open(args.input, "r", encoding="utf-8", newline="", buffering=16 * 1024 * 1024)
    reader = pd.read_csv(src, dtype=str, keep_default_na=False, chunksize=args.chunksize,
                         usecols=lambda c: c in set(BASE) | set(SEG) | {"fareBasisCode", "reject_reason"})
    for chunk_no, raw in enumerate(reader, 1):
        if args.limit and st["rows"] >= args.limit:
            break
        if args.limit:
            raw = raw.iloc[: args.limit - st["rows"]]
        if "reject_reason" in raw.columns:
            # recovery input: only rows the old version rejected for the metro-area airport check
            metro = raw.reject_reason.str.startswith(("first segment not from", "last segment not to"))
            st.add("rows in rejects file skipped (other reasons)", (~metro).sum())
            raw = raw[metro].drop(columns="reject_reason")
        st.add("rows", len(raw))
        dup = raw.duplicated()
        st.add("exact duplicate rows within a chunk (dropped)", dup.sum())
        raw = raw[~dup]
        df = raw.copy()
        why = pd.Series("", index=df.index, dtype=object)

        def reject(mask, reason):
            nonlocal why
            mask = pd.Series(mask, index=df.index).fillna(False).astype(bool)
            new = mask & (why == "")
            why = why.where(~new, reason)
            st.add("REJECT " + reason, new.sum())

        # ---------- row level ----------
        df["legId"] = df.legId.str.strip()
        reject((df.legId == "") | (df.legId.str.len() > 64), "bad legId")
        st.add("legIds that are not 32 hex characters (kept)", (~df.legId.str.match(r"^[0-9a-f]{32}$")).sum())
        sd = pd.to_datetime(df.searchDate, format="%Y-%m-%d", errors="coerce")
        fd = pd.to_datetime(df.flightDate, format="%Y-%m-%d", errors="coerce")
        reject(sd.isna(), "bad searchDate")
        reject(fd.isna(), "bad flightDate")
        ahead = (fd - sd).dt.days
        st.add("searchDate after flightDate (kept)", (ahead < 0).sum())
        days_ahead.update(ahead.dropna().clip(-1, 61).astype(int).tolist())
        for rng, s in ((search_range, sd), (flight_range, fd)):
            if s.notna().any():
                rng[0] = min(filter(None, [rng[0], s.min()]))
                rng[1] = max(filter(None, [rng[1], s.max()]))
        fare = num(df.totalFare)
        base = num(df.baseFare)
        reject(fare.isna() | (fare < 0), "bad totalFare")
        st.add("totalFare = 0 (kept)", (fare == 0).sum())
        st.add("totalFare below baseFare (kept)", (fare < base).sum())
        st.add("totalFare over $5,000 (kept)", (fare > 5000).sum())
        be, rf, ns = as_bool(df.isBasicEconomy), as_bool(df.isRefundable), as_bool(df.isNonStop)
        reject(be.isna(), "bad isBasicEconomy")
        reject(rf.isna(), "bad isRefundable")
        reject(ns.isna(), "bad isNonStop")
        dur_min, dur_ok = iso_minutes(df.travelDuration.str.strip())
        reject(~dur_ok, "bad travelDuration")
        ttd = num(null_out(df.totalTravelDistance))
        st.add("totalTravelDistance missing (kept as null)", ttd.isna().sum())
        st.add("totalTravelDistance <= 0 (set to null)", (ttd <= 0).sum())
        ttd = ttd.where(ttd > 0)
        df["startingAirport"] = std_code(df.startingAirport)
        df["destinationAirport"] = std_code(df.destinationAirport)
        reject(~df.startingAirport.fillna("").str.match(AIRPORT_RE) |
               ~df.destinationAirport.fillna("").str.match(AIRPORT_RE), "bad starting/destination airport")

        # ---------- split the '||' lists ----------
        parts = pd.DataFrame({short: df[col].str.split(r"\|\|", regex=True) for col, short in SEG.items()})
        lens = pd.DataFrame({short: df[col].str.count(r"\|\|") + 1 for col, short in SEG.items()})
        nseg = lens["dep_ap"]
        reject(lens.max(axis=1) != lens.min(axis=1), "segment lists have different lengths")
        reject(nseg < 1, "no segments")
        reject((nseg == 1) != ns.fillna(nseg == 1), "isNonStop disagrees with segment count")
        good = why == ""
        seg = parts[good].assign(row=parts.index[good]).explode(list(SEG.values()))
        seg["segment_no"] = seg.groupby(level=0).cumcount() + 1
        seg = seg.reset_index(drop=True)
        for c in ("arr_ap", "dep_ap", "al_code"):
            seg[c] = std_code(seg[c])
        for c in ("dist", "dur", "dep_epoch", "arr_epoch", "al_name", "cabin"):
            seg[c] = null_out(seg[c])
        dep = pd.to_datetime(seg.dep_raw, utc=True, errors="coerce", format="ISO8601")
        arr = pd.to_datetime(seg.arr_raw, utc=True, errors="coerce", format="ISO8601")
        bad = pd.Series(False, index=seg.index)

        def seg_reject(mask, reason):
            nonlocal bad
            rows = seg.row[mask.fillna(False) & ~bad].unique()
            bad |= seg.row.isin(rows)
            reject(df.index.isin(rows), reason)

        seg_reject(~seg.dep_ap.fillna("").str.match(AIRPORT_RE) | ~seg.arr_ap.fillna("").str.match(AIRPORT_RE),
                   "bad segment airport code")
        seg_reject(~seg.al_code.fillna("").str.match(AIRLINE_RE), "bad segment airline code")
        seg_reject(dep.isna() | arr.isna(), "bad segment departure/arrival time")
        seg_reject(arr <= dep, "segment arrives before it departs")
        seg_reject(seg.dep_ap == seg.arr_ap, "segment origin equals destination")
        # alignment with the itinerary
        last = seg.groupby("row").segment_no.transform("max") == seg.segment_no
        start = seg.row.map(df.startingAirport)
        dest = seg.row.map(df.destinationAirport)
        # Expedia searches by metro area (a DFW search can return a DAL flight), so a different
        # first/last airport is kept; itinerary origin/destination come from the segments anyway
        alt_o = (seg.segment_no == 1) & (seg.dep_ap != start) & ~bad
        alt_d = last & (seg.arr_ap != dest) & ~bad
        st.add("first segment leaves from another airport than startingAirport (kept, metro-area search)", alt_o.sum())
        st.add("last segment arrives at another airport than destinationAirport (kept, metro-area search)", alt_d.sum())
        alt_pairs.update(zip(start[alt_o], seg.dep_ap[alt_o]))
        alt_pairs.update(zip(dest[alt_d], seg.arr_ap[alt_d]))
        nxt_dep_ap = seg.groupby("row").dep_ap.shift(-1)
        nxt_dep = dep.groupby(seg.row).shift(-1)
        st.add("connections where the next segment leaves from a different airport (kept)",
               (nxt_dep_ap.notna() & (nxt_dep_ap != seg.arr_ap) & ~bad).sum())
        seg_reject(nxt_dep.notna() & (nxt_dep < arr), "next segment departs before previous arrives")
        st.add("flightDate differs from local date of first departure (kept)",
               ((seg.segment_no == 1) & (seg.dep_raw.str[:10] != seg.row.map(df.flightDate)) & ~bad).sum())
        epoch_dep = num(seg.dep_epoch)
        st.add("departure epoch seconds disagree with the raw time (kept)",
               ((epoch_dep - (dep - pd.Timestamp(0, tz="UTC")).dt.total_seconds()).abs() > 60).sum())
        sdur = num(seg.dur)
        st.add("segmentsDurationInSeconds != arrival - departure (kept; duration is computed in queries)",
               ((sdur - (arr - dep).dt.total_seconds()).abs() > 60)[~bad].sum())
        total_span = (arr.groupby(seg.row).max() - dep.groupby(seg.row).min()).dt.total_seconds() / 60
        rows_ok = pd.Index(seg.row[~bad].unique())
        st.add("travelDuration != first departure to last arrival (kept)",
               ((total_span.reindex(rows_ok) - dur_min.reindex(rows_ok)).abs() > 1).sum())
        sdist = num(seg.dist)
        st.add("segments with no segmentsDistance", sdist.isna().sum())
        dist_sum = sdist.groupby(seg.row).sum(min_count=1)
        all_dist = sdist.notna().groupby(seg.row).all()
        st.add("sum of segmentsDistance differs from totalTravelDistance by > 1 mile (kept)",
               ((dist_sum - ttd.reindex(dist_sum.index)).abs() > 1)[all_dist].sum())
        st.add("cabin codes outside coach/premium coach/business/first (kept)",
               (seg.cabin.notna() & ~seg.cabin.isin(CABINS)).sum())
        cabins.update(seg.cabin.fillna("<null>").tolist())

        seg = seg[~bad]
        ok_rows = df.index[why == ""]
        # ---------- legId consistency across rows and chunks ----------
        o = df.loc[ok_rows]
        sig_text = (o.flightDate + "|" + o.isNonStop.str.lower() + "|" +
                    o.segmentsDepartureAirportCode.str.upper() + "|" + o.segmentsArrivalAirportCode.str.upper() + "|" +
                    o.segmentsAirlineCode.str.upper() + "|" + o.segmentsDepartureTimeRaw + "|" + o.segmentsArrivalTimeRaw)
        sig = stable_hash(sig_text)
        legs = df.loc[ok_rows, "legId"]
        uniq = pd.unique(legs)
        db.execute("CREATE TEMP TABLE IF NOT EXISTS ids (leg_id TEXT PRIMARY KEY)")
        db.execute("DELETE FROM ids")
        db.executemany("INSERT INTO ids VALUES (?)", ((x,) for x in uniq))
        known, known_nseg = {}, {}
        for leg_id, sg, n in db.execute("SELECT i.leg_id, i.sig, i.nseg FROM itin i JOIN ids USING (leg_id)"):
            known[leg_id], known_nseg[leg_id] = sg, n
        first_sig = sig.groupby(legs.values).transform("first")
        in_known = legs.isin(known)
        ref = np.where(in_known, [known.get(x, 0) for x in legs], first_sig.to_numpy()).astype("int64")
        reject(df.index.isin(ok_rows[sig.to_numpy() != ref]), "legId seen before with different segments/flightDate/isNonStop")
        st.add("rows for a legId already seen in an earlier chunk", legs.isin(known).sum())

        ok_rows = df.index[why == ""]
        okd = df.loc[ok_rows]
        # soft consistency: duration/distance per legId within the chunk
        g = pd.DataFrame({"leg": okd.legId, "td": okd.travelDuration, "dist": ttd[ok_rows]}).groupby("leg")
        st.add("legIds whose travelDuration differs between rows (first kept)", (g.td.nunique() > 1).sum())
        st.add("legIds whose totalTravelDistance differs between rows (first kept)", (g.dist.nunique() > 1).sum())

        seg = seg[seg.row.isin(ok_rows)]
        new_mask = ~okd.legId.isin(known) & ~okd.legId.duplicated()
        new = okd[new_mask]
        db.executemany("INSERT INTO itin VALUES (?,?,?,?,?,?,?,?)", zip(
            new.legId, new.flightDate, new.travelDuration.str.strip(),
            ttd[new.index].astype("Int64").astype(object).where(ttd[new.index].notna(), None),
            ns[new.index].astype(int), sig[new.index].astype(int).tolist(),
            dur_min[new.index].astype(float), nseg[new.index].astype(int)))
        nseg_rows = seg[seg.row.isin(new.index)]
        db.executemany("INSERT INTO seg VALUES (?,?,?,?,?,?,?)", zip(
            nseg_rows.row.map(df.legId), nseg_rows.segment_no.astype(int), nseg_rows.dep_raw, nseg_rows.arr_raw,
            nseg_rows.dep_ap, nseg_rows.arr_ap, nseg_rows.al_code))
        db.commit()
        st.add("new itineraries", len(new))

        # dimensions
        for o, d, x in zip(seg.dep_ap, seg.arr_ap, sdist[seg.index]):
            if x == x:
                route_dist[(o, d)][int(round(x))] += 1
            else:
                route_dist[(o, d)]
        for code, name in zip(seg.al_code, seg.al_name):
            airline_names[code][name if isinstance(name, str) else None] += 1
        airports.update(seg.dep_ap)
        airports.update(seg.arr_ap)

        # books -> segment cross-table rule: every quote's segment_no must exist for its legId
        leg_nseg = {**known_nseg, **dict(zip(new.legId, nseg[new.index].astype(int)))}
        st.add("CHECK books segment_no not in segment for the quote's legId (must be 0)",
               (seg.segment_no.to_numpy() > seg.row.map(df.legId).map(leg_nseg).to_numpy()).sum())
        st.add("CHECK fare_quote legId not in itinerary (must be 0)", (~okd.legId.isin(leg_nseg)).sum())

        # quotes and books
        qid = pd.Series(np.arange(quote_id + 1, quote_id + 1 + len(ok_rows)), index=ok_rows)
        quote_id += len(ok_rows)
        fq = pd.DataFrame({"quote_id": qid, "search_date": okd.searchDate, "total_fare": fare[ok_rows].round(2),
                           "is_basic_economy": be[ok_rows], "is_refundable": rf[ok_rows], "leg_id": okd.legId})
        fq.to_csv(P("fare_quote.csv"), mode="w" if first["fq"] else "a", header=first["fq"], index=False)
        first["fq"] = False
        bk = pd.DataFrame({"quote_id": seg.row.map(qid), "segment_no": seg.segment_no, "cabin_code": seg.cabin})
        bk = bk[bk.quote_id.notna()].astype({"quote_id": "int64"})
        bk.to_csv(P("books.csv"), mode="w" if first["bk"] else "a", header=first["bk"], index=False)
        first["bk"] = False
        st.add("fare_quote rows", len(fq))
        st.add("books rows", len(bk))

        rj = raw.loc[why != ""].assign(reject_reason=why[why != ""])
        if len(rj):
            rj.to_csv(P(f"d1_rejects{suffix}.csv"), mode="w" if first["rj"] else "a", header=first["rj"], index=False)
            first["rj"] = False
        el = time.time() - t0
        print(f"chunk {chunk_no}: {st['rows']:,} rows read, {st['fare_quote rows']:,} quotes, "
              f"{st['new itineraries']:,} itineraries, {el/60:.1f} min", flush=True)

    # ---------------- export ----------------
    print("writing itinerary.csv and segment.csv ...", flush=True)
    pd.read_sql_query("SELECT leg_id, flight_date, travel_duration, total_travel_distance, "
                      "CASE is_nonstop WHEN 1 THEN 'true' ELSE 'false' END AS is_nonstop FROM itin",
                      db, dtype={"total_travel_distance": "Int64"}).to_csv(P("itinerary.csv"), index=False)
    with open(P("segment.csv"), "w", encoding="utf-8", newline="") as f:
        header = True
        for part in pd.read_sql_query("SELECT * FROM seg", db, chunksize=1_000_000):
            part.to_csv(f, header=header, index=False)
            header = False
    seg_counts = dict(db.execute("SELECT segment_no, COUNT(*) FROM seg GROUP BY 1").fetchall())
    db.close()

    names = [(c, cnt.most_common(1)[0][0] if cnt else None, len([n for n in cnt if n])) for c, cnt in sorted(airline_names.items())]
    ap_out = pd.DataFrame({"airport_code": sorted(airports)})
    al_out = pd.DataFrame(names, columns=["airline_code", "airline_name", "n_names"]).drop(columns="n_names")
    routes = pd.DataFrame([(o, d, (cnt.most_common(1)[0][0] if cnt else None), len(cnt))
                           for (o, d), cnt in sorted(route_dist.items())],
                          columns=["origin_code", "destination_code", "distance_miles", "n_values"])
    rt_out = routes.drop(columns="n_values").astype({"distance_miles": "Int64"})
    if args.append:  # keep what the earlier run found, add anything new
        old = lambda n: pd.read_csv(P(n), dtype=str, keep_default_na=False, na_values=[""])
        ap_out = pd.concat([old("d1_airport.csv"), ap_out]).drop_duplicates("airport_code").sort_values("airport_code")
        al_out = pd.concat([old("d1_airline.csv"), al_out]).drop_duplicates("airline_code").sort_values("airline_code")
        rt_out = (pd.concat([old("d1_route.csv"), rt_out.astype(str).replace("<NA>", pd.NA)])
                  .drop_duplicates(["origin_code", "destination_code"]).sort_values(["origin_code", "destination_code"]))
    ap_out.to_csv(P("d1_airport.csv"), index=False)
    al_out.to_csv(P("d1_airline.csv"), index=False)
    rt_out.to_csv(P("d1_route.csv"), index=False)

    # ---------------- report ----------------
    rep = Report("Expedia flight prices (D1) cleaning report")
    rep.section("Input")
    rep.add("file", os.path.basename(args.input))
    rep.add("rows read", st["rows"])
    rep.add("chunk size", args.chunksize)
    rep.add("searchDate range", f"{search_range[0].date()} to {search_range[1].date()}" if search_range[0] is not None else "n/a")
    rep.add("flightDate range", f"{flight_range[0].date()} to {flight_range[1].date()}" if flight_range[0] is not None else "n/a")
    rep.add("run time", f"{(time.time() - t0) / 60:.1f} min")
    rep.section("Rejected rows")
    for k, v in sorted(st.c.items()):
        if k.startswith("REJECT"):
            rep.add(k[7:], v)
    rep.add("total rejected", sum(v for k, v in st.c.items() if k.startswith("REJECT")))
    rep.section("Kept, but worth knowing")
    for k, v in sorted(st.c.items()):
        if not k.startswith("REJECT") and k not in {"rows", "fare_quote rows", "books rows", "new itineraries"}:
            rep.add(k, v)
    rep.add("cabin codes", dict(cabins.most_common()))
    rep.add("searched airport -> airport actually used (metro-area substitutes)",
            ", ".join(f"{a}->{b}: {n:,}" for (a, b), n in alt_pairs.most_common()) or "none")
    rep.add("airline codes with more than one name", ", ".join(f"{c}: {sorted(n for n in cnt if n)}" for c, cnt in airline_names.items() if len([n for n in cnt if n]) > 1) or "none")
    rep.add("routes with more than one segmentsDistance value", int((routes.n_values > 1).sum()))
    rep.add("days between search and flight (0..60)", f"min {min(days_ahead) if days_ahead else 'n/a'}, max {max(days_ahead) if days_ahead else 'n/a'}")
    rep.section("Output")
    rep.add("new itinerary rows" if args.append else "itinerary rows", st["new itineraries"])
    if args.append:
        rep.add("itinerary rows in total (earlier run + this one)", int(seg_counts.get(1, 0)))
    rep.add("segment rows by segment_no", seg_counts)
    rep.add("fare_quote rows", st["fare_quote rows"])
    rep.add("books rows", st["books rows"])
    rep.add("airports", len(airports))
    rep.add("airlines", len(airline_names))
    rep.add("routes", len(routes))
    rep.write(P(f"report_itineraries{suffix}.md"))


if __name__ == "__main__":
    main()
