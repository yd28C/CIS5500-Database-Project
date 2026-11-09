"""
Cross-dataset step: build the shared airport, airline and route tables from the three
cleaned datasets, then check every foreign key before anything is loaded.

Run after clean_bts.py, clean_ghcn.py and (when its output exists) clean_itineraries.py:
    python build_dimensions.py --out output

Reads from --out:  bts_airport/bts_airline/bts_route, weather_station, and if present
                   d1_airport/d1_airline/d1_route plus segment/itinerary/fare_quote/books
Writes to --out:   airport.csv, airline.csv, route.csv, report_integration.md

Rules:
  - codes are already trimmed/upper-cased by the cleaning scripts; this step takes the union
  - airport city/state come from BTS (D1 and GHCN have codes only)
  - airline_name: Expedia's segmentsAirlineName when present, else the BTS lookup
  - route.distance_miles: BTS Distance when the route is flown in BTS, else the most common
    Expedia segmentsDistance
"""
import argparse
import os

import pandas as pd

from common import Report


def load(out, name, **kw):
    path = os.path.join(out, name)
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""], **kw) if os.path.exists(path) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="output")
    args = ap.parse_args()
    O = args.out
    rep = Report("Cross-dataset integration report")

    bts_ap, bts_al, bts_rt = load(O, "bts_airport.csv"), load(O, "bts_airline.csv"), load(O, "bts_route.csv")
    ws = load(O, "weather_station.csv")
    d1_ap, d1_al, d1_rt = load(O, "d1_airport.csv"), load(O, "d1_airline.csv"), load(O, "d1_route.csv")
    have_d1 = d1_ap is not None
    rep.section("Inputs")
    rep.add("BTS (D2) outputs", "found" if bts_ap is not None else "MISSING, run clean_bts.py")
    rep.add("GHCN (D3) outputs", "found" if ws is not None else "MISSING, run clean_ghcn.py")
    rep.add("Expedia (D1) outputs", "found" if have_d1 else "not found yet (run clean_itineraries.py, then rerun this)")
    if bts_ap is None or ws is None:
        raise SystemExit("run clean_bts.py and clean_ghcn.py first")

    # ---------- airport ----------
    codes = set(bts_ap.airport_code) | set(ws.airport_code) | (set(d1_ap.airport_code) if have_d1 else set())
    airport = pd.DataFrame({"airport_code": sorted(codes)}).merge(bts_ap, on="airport_code", how="left")
    airport.to_csv(os.path.join(O, "airport.csv"), index=False)
    rep.section("Airport")
    rep.add("airports", len(airport))
    rep.add("weather airports", len(ws))
    rep.add("weather airports also in BTS", int(ws.airport_code.isin(bts_ap.airport_code).sum()))
    if have_d1:
        d1c = set(d1_ap.airport_code)
        rep.add("D1 airports", len(d1c))
        rep.add("D1 airports also in BTS 2025", len(d1c & set(bts_ap.airport_code)))
        rep.add("D1 airports with a weather station", len(d1c & set(ws.airport_code)))
        rep.add("D1 airports missing from BTS (no city/state)", ", ".join(sorted(d1c - set(bts_ap.airport_code))) or "none")

    # ---------- airline ----------
    al = bts_al.set_index("airline_code").airline_name
    if have_d1:
        d1n = d1_al.set_index("airline_code").airline_name
        al = d1n.combine_first(al)
    airline = al.rename_axis("airline_code").reset_index().sort_values("airline_code")
    airline.to_csv(os.path.join(O, "airline.csv"), index=False)
    rep.section("Airline")
    rep.add("airlines", len(airline))
    rep.add("BTS reporting (operating) carriers", ", ".join(sorted(bts_al.airline_code)))
    if have_d1:
        d1c, bc = set(d1_al.airline_code), set(bts_al.airline_code)
        rep.add("D1 (marketing) carriers", ", ".join(sorted(d1c)))
        rep.add("carriers in both", ", ".join(sorted(d1c & bc)) or "none")
        rep.add("D1 carriers not in BTS", ", ".join(sorted(d1c - bc)) or "none")
        rep.add("note", "BTS Reporting_Airline is the operating carrier (OO, MQ, YX, OH fly for AA/DL/UA); "
                "Expedia shows the marketing carrier, so regional flights compare at the brand level only")

    # ---------- route ----------
    rt = bts_rt.assign(src="BTS")
    if have_d1:
        extra = d1_rt[~d1_rt.set_index(["origin_code", "destination_code"]).index.isin(
            rt.set_index(["origin_code", "destination_code"]).index)].assign(src="D1")
        both = d1_rt.merge(bts_rt, on=["origin_code", "destination_code"], suffixes=("_d1", "_bts"))
        diff = (pd.to_numeric(both.distance_miles_d1) - pd.to_numeric(both.distance_miles_bts)).abs()
        rt = pd.concat([rt, extra], ignore_index=True)
    route = rt.drop(columns="src").sort_values(["origin_code", "destination_code"])
    route.to_csv(os.path.join(O, "route.csv"), index=False)
    rep.section("Route")
    rep.add("routes", len(route))
    rep.add("from BTS", int((rt.src == "BTS").sum()))
    if have_d1:
        rep.add("D1-only routes (distance from segmentsDistance)", int((rt.src == "D1").sum()))
        rep.add("routes in both", len(both))
        rep.add("routes in both whose D1 and BTS distance differ by > 5 miles", int((diff > 5).sum()))
    rep.add("routes with null distance", int(route.distance_miles.isna().sum()))

    # ---------- foreign keys ----------
    rep.section("Foreign-key checks")
    ap_set, al_set = set(airport.airport_code), set(airline.airline_code)
    rt_set = set(zip(route.origin_code, route.destination_code))
    rep.add("route endpoints missing from airport", int((~route.origin_code.isin(ap_set) | ~route.destination_code.isin(ap_set)).sum()))
    rep.add("weather_station airports missing from airport", int((~ws.airport_code.isin(ap_set)).sum()))

    fo = load(O, "flight_operation.csv", usecols=["operation_id", "origin_code", "destination_code", "airline_code"])
    rep.add("flight_operation airline missing from airline", int((~fo.airline_code.isin(al_set)).sum()))
    rep.add("flight_operation route missing from route",
            int((~pd.Series(list(zip(fo.origin_code, fo.destination_code))).isin(rt_set)).sum()))
    dl = load(O, "delayed_flight.csv", usecols=["operation_id"])
    rep.add("delayed_flight operation_id missing from flight_operation", int((~dl.operation_id.isin(set(fo.operation_id))).sum()))
    wo = load(O, "weather_observation.csv", usecols=["station_id"])
    rep.add("weather_observation station missing from weather_station", int((~wo.station_id.isin(set(ws.station_id))).sum()))

    if have_d1 and os.path.exists(os.path.join(O, "segment.csv")):
        legs = set(load(O, "itinerary.csv", usecols=["leg_id"]).leg_id)
        bad_seg_leg, bad_seg_al, bad_seg_rt = 0, 0, 0
        for s in pd.read_csv(os.path.join(O, "segment.csv"), dtype=str, chunksize=2_000_000):
            bad_seg_leg += int((~s.leg_id.isin(legs)).sum())
            bad_seg_al += int((~s.airline_code.isin(al_set)).sum())
            bad_seg_rt += int((~pd.Series(list(zip(s.origin_code, s.destination_code))).isin(rt_set)).sum())
        rep.add("segment leg_id missing from itinerary", bad_seg_leg)
        rep.add("segment airline missing from airline", bad_seg_al)
        rep.add("segment route missing from route", bad_seg_rt)
        rep.add("fare_quote -> itinerary and books -> segment",
                "checked chunk by chunk inside clean_itineraries.py (see the CHECK lines in report_itineraries.md)")

    rep.section("Join coverage (D2 x D3)")
    fo_full = load(O, "flight_operation.csv", usecols=["origin_code", "destination_code"])
    wap = set(ws.airport_code)
    rep.add("BTS flights departing a weather airport",
            f"{int(fo_full.origin_code.isin(wap).sum()):,} of {len(fo_full):,}")
    rep.add("BTS flights with weather at both ends",
            f"{int((fo_full.origin_code.isin(wap) & fo_full.destination_code.isin(wap)).sum()):,}")
    rep.write(os.path.join(O, "report_integration.md"))


if __name__ == "__main__":
    main()
