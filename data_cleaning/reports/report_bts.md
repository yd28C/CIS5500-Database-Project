# BTS flight performance (D2) cleaning report


## Input

- file: flight_delays_2025_01.csv
- rows: 539,747
- columns: 40

## Airport and airline codes

- Origin: values changed by trim/upper-case: 0
- Dest: values changed by trim/upper-case: 0
- Reporting_Airline: values changed by trim/upper-case: 0
- OriginState: values changed by trim/upper-case: 0
- DestState: values changed by trim/upper-case: 0
- rows with an airport code that is not 3 letters (rejected): 0
- rows with a malformed airline code (rejected): 0
- rows with Origin = Dest (rejected): 0
- distinct airports: 329
- distinct airlines: 14
- airline codes with no name in the lookup: none
- airports with more than one city/state spelling: 0
- airports whose state is not a 2-letter code: 0

## Dates

- unparseable FlightDate (rejected): 0
- rows where Year/Quarter/Month/DayofMonth/DayOfWeek disagree with FlightDate: 0
- date range: 2025-01-01 to 2025-01-31

## Local HHMM times

- CRSDepTime: out-of-range values (rejected): 0
- CRSDepTime: null: 0
- CRSDepTime: value 2400 (BTS midnight, kept as 2400): 0
- DepTime: out-of-range values (rejected): 0
- DepTime: null: 15,886
- DepTime: value 2400 (BTS midnight, kept as 2400): 33
- CRSArrTime: out-of-range values (rejected): 0
- CRSArrTime: null: 0
- CRSArrTime: value 2400 (BTS midnight, kept as 2400): 0
- ArrTime: out-of-range values (rejected): 0
- ArrTime: null: 16,580
- ArrTime: value 2400 (BTS midnight, kept as 2400): 245
- scheduled times missing (rejected): 0

## Status indicators

- Cancelled not 0/1 (rejected): 0
- Diverted not 0/1 (rejected): 0
- cancelled flights (kept): 16,312
- diverted flights (kept): 1,166
- CancellationCode outside A/B/C/D (rejected): 0
- Cancelled flag disagrees with CancellationCode (rejected; cancelled is derived from the code): 0
- cancelled AND diverted (rejected, breaks CHECK): 0
- cancellation codes: {'B': 14327, 'A': 1635, 'C': 342, 'D': 8}
- cancelled flights that still have a DepTime (pushed back then cancelled; kept): 426
- non-cancelled, non-diverted flights missing ArrTime or ArrDelay: 0
- diverted flights with an ArrDelay (BTS normally leaves it null): 0

## Delay values

- DepDelay: non-numeric (rejected): 0
- DepDelay: negative (early, kept): 325,311
- DepDelay: null (kept as null): 15,923
- DepDelay: min / max: -50 / 3298
- DepDelay: non-integer values: 0
- ArrDelay: non-numeric (rejected): 0
- ArrDelay: negative (early, kept): 341,773
- ArrDelay: null (kept as null): 17,478
- ArrDelay: min / max: -87 / 3282
- ArrDelay: non-integer values: 0
- TaxiOut: non-numeric (rejected): 0
- TaxiOut: <= 0 where present: 0
- TaxiOut: non-integer values: 0
- TaxiIn: non-numeric (rejected): 0
- TaxiIn: <= 0 where present: 0
- TaxiIn: non-integer values: 0
- CRSElapsedTime: non-numeric (rejected): 0
- CRSElapsedTime: <= 0 where present: 0
- CRSElapsedTime: non-integer values: 0
- AirTime: non-numeric (rejected): 0
- AirTime: <= 0 where present: 0
- AirTime: non-integer values: 0
- Distance: non-numeric (rejected): 0
- Distance: <= 0 where present: 0
- Distance: non-integer values: 0
- DepDelay != DepTime - CRSDepTime (mod 24h), excluding delays over 12h: 0
- ArrDelay != ArrTime - CRSArrTime (mod 24h), excluding delays over 12h: 2
- DepDelayMinutes != max(DepDelay, 0) (column not stored): 0
- ArrDel15 != (ArrDelay >= 15) (column not stored): 0
- ActualElapsedTime != TaxiOut + AirTime + TaxiIn (column not stored): 0

## Delay-cause completeness

- flights with ArrDel15 = 1: 98,130
- flights with delay-cause values: 98,130
- flights with only some of the five causes filled: 0
- ArrDel15 = 1 but no causes: 0
- causes present but ArrDel15 != 1: 0
- negative cause minutes: 0
- causes that do not add up to ArrDelay: 0

## Duplicate operation records

- exact duplicate rows (dropped, first kept): 0
- rows sharing the candidate key (FlightDate, airline, flight number, Origin), excluding exact copies: 0
- flight number missing or not a positive integer (rejected): 0

## Route distance

- routes: 5,649
- routes with more than one Distance value: 0
- routes whose A->B distance differs from B->A: 0
- distance <= 0 (rejected): 0

## Output

- rows rejected: 0
- flight_operation rows: 539,747
- delayed_flight rows: 98,130
- ArrDel15 = 1 flights left out because a cause is missing: 0
- airports: 329
- airlines: 14
- routes: 5,649
