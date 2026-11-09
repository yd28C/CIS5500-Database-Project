# Cross-dataset integration report


## Inputs

- BTS (D2) outputs: found
- GHCN (D3) outputs: found
- Expedia (D1) outputs: found

## Airport

- airports: 382
- weather airports: 32
- weather airports also in BTS: 32
- D1 airports: 228
- D1 airports also in BTS 2025: 198
- D1 airports with a weather station: 31
- D1 airports missing from BTS (no city/state): BFD, BJC, BOG, CEZ, CNM, CNY, CSG, CUN, CVN, DSI, DUJ, ELD, GLH, GYE, HOT, HRO, IPL, IWD, LNS, LWB, MKL, MSS, MWA, OGS, OWB, SHD, SLK, TBN, TEX, UIN

## Airline

- airlines: 21
- BTS reporting (operating) carriers: AA, AS, B6, DL, F9, G4, HA, MQ, NK, OH, OO, UA, WN, YX
- D1 (marketing) carriers: 3M, 4B, 9K, 9X, AA, AS, B6, DL, F9, HA, KG, LF, NK, SY, UA
- carriers in both: AA, AS, B6, DL, F9, HA, NK, UA
- D1 carriers not in BTS: 3M, 4B, 9K, 9X, KG, LF, SY
- note: BTS Reporting_Airline is the operating carrier (OO, MQ, YX, OH fly for AA/DL/UA); Expedia shows the marketing carrier, so regional flights compare at the brand level only

## Route

- routes: 7,205
- from BTS: 6,938
- D1-only routes (distance from segmentsDistance): 267
- routes in both: 2,934
- routes in both whose D1 and BTS distance differ by > 5 miles: 1,065
- routes with null distance: 23

## Foreign-key checks

- route endpoints missing from airport: 0
- weather_station airports missing from airport: 0
- flight_operation airline missing from airline: 0
- flight_operation route missing from route: 0
- delayed_flight operation_id missing from flight_operation: 0
- weather_observation station missing from weather_station: 0
- segment leg_id missing from itinerary: 0
- segment airline missing from airline: 0
- segment route missing from route: 0
- fare_quote -> itinerary and books -> segment: checked chunk by chunk inside clean_itineraries.py (see the CHECK lines in report_itineraries.md)

## Join coverage (D2 x D3)

- BTS flights departing a weather airport: 4,612,460 of 7,001,619
- BTS flights with weather at both ends: 2,617,265
