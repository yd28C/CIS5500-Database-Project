# Data Cleaning Methodology

CIS 5500 final project, Milestone 2 · Nov 9, 2026 · @judy

## Overview

Three raw datasets were cleaned into CSV files that load directly into the BCNF schema (`schema_BCNF_fixed.sql`). Only 2,610 of 82.8 million input rows (0.003%) were rejected, and every primary key, foreign key and CHECK constraint passes.

| Dataset | Source file | Rows in | Coverage | Target tables |
| --- | --- | --- | --- | --- |
| D1 Flight prices | Expedia `itineraries.csv` (Kaggle dilwong/flightprices), 31 GB | 82,138,753 | searches 2022-04-16 to 2022-10-05, flights to 2022-11-19 | itinerary, segment, fare\_quote, books |
| D2 Flight performance | BTS On-Time Reporting `flight_delays_2025_01.csv` | 539,747 | January 2025, 14 carriers, 329 airports | flight\_operation, delayed\_flight |
| D3 Weather | NOAA GHCN-Daily `ghcn_raw_2025.csv` | 120,371 | 2025, 32 airport stations | weather\_station, weather\_observation |
| Shared | built from all three | n/a | n/a | airport, airline, route |

The pipeline runs in this order, with each script writing a report of every check it ran:

1. `clean_bts.py`: BTS flight performance (about 20 seconds).
2. `clean_ghcn.py`: GHCN weather (a few seconds).
3. `clean_itineraries.py`: Expedia prices, read in 250,000-row chunks with an on-disk SQLite index to de-duplicate legIds across chunks (75 minutes for the full file).
4. `build_dimensions.py`: merges airport, airline and route codes from all three datasets and checks every foreign key.
5. `load.sql`: loads the CSVs with psql `\copy` in foreign-key order.

General rules applied everywhere: codes are trimmed and upper-cased; missing values stay null and are never replaced with 0; rows that would break a schema constraint are written to a rejects file with the reason instead of being silently dropped.

## Flight performance (BTS, D2)

All 539,747 flights passed validation and were kept; none were rejected or deduplicated.

**Rules applied**

- **Codes.** Origin, Dest and Reporting\_Airline trimmed and upper-cased; airports must be 3 letters, airlines 2 to 3 alphanumerics, and Origin must differ from Dest. Each airport maps to exactly one city and state.
- **Dates.** FlightDate parsed and cross-checked against Year, Quarter, Month, DayofMonth and DayOfWeek, which are then dropped as derivable.
- **Local times.** CRSDepTime, DepTime, CRSArrTime and ArrTime must be valid HHMM (0000 to 2400, minutes under 60). 2400 is kept as BTS's end-of-day midnight.
- **Delays.** Negative delays are kept because they mean early departures or arrivals. DepDelay and ArrDelay were recomputed from the clock times as a consistency check.
- **Status.** Cancelled and diverted flights stay in the table with null actual times and delays. Cancelled must agree with CancellationCode (A to D), since the schema derives cancelled from the code, and no flight may be both cancelled and diverted.
- **Duplicates.** Checked on the candidate key (FlightDate, airline, flight number, Origin) and on whole rows.
- **Delay causes.** For every flight with ArrDel15 = 1, all five causes must be present and non-negative and must add up to ArrDelay. These rows form `delayed_flight`.
- **Dropped derived columns.** ActualElapsedTime, DepDelayMinutes and ArrDel15 were each confirmed to be exactly derivable before being dropped; Distance moved to `route`.

**What the checks found**

| Check | Result |
| --- | --- |
| Malformed codes, dates or HHMM times | 0 |
| Duplicate candidate keys | 0 |
| Cancelled flights kept | 16,312 (codes: B weather 14,327, A carrier 1,635, C NAS 342, D security 8) |
| Diverted flights kept | 1,166 |
| Negative DepDelay / ArrDelay kept | 325,311 / 341,773 |
| Null DepDelay / ArrDelay kept | 15,923 / 17,478 |
| Delayed flights with complete causes summing to ArrDelay | 98,130 of 98,130 |
| ActualElapsedTime = TaxiOut + AirTime + TaxiIn | true for every row |
| ArrDelay inconsistent with clock times | 2 rows, off by about 6 minutes, kept |
| Routes with more than one Distance value | 0 of 5,649 |

## Weather (GHCN-Daily, D3)

All 120,371 observations were valid and kept in long format, one row per station, date and element.

**Rules applied**

- **Station mapping.** Each airport must map to exactly one station and each station to one airport. Every station must be the airport's ASOS station, `USW000` + its WBAN number, matching the download list in `ghcn_download.py`.
- **Quality flags.** Observations with a non-blank qflag (failed NOAA quality control) are excluded.
- **Invalid or missing values.** The -9999 missing code, non-numeric or non-integer values, physically impossible values (per-element ranges in raw units, for example TMAX and TMIN between -60.0 and 60.0 °C) and station-days with TMAX below TMIN are excluded, never replaced with 0. Weather-type elements (WT01 to WT10) must equal 1.
- **Preserved as-is.** Raw values in NOAA units (tenths of °C, tenths of mm, tenths of m/s), mflag (for example T = trace precipitation) and sflag.
- **Observation time.** obstime is not stored in `weather_observation`. In this data (station, element) determines obstime, a partial-key dependency that breaks BCNF, and the script confirmed it holds for every pair. The value stays in the raw file.
- **Duplicates.** Checked on the primary key (station, date, element).

**What the checks found**

| Check | Result |
| --- | --- |
| Airports / stations, one-to-one | 32 / 32 |
| Stations that are not the expected airport station | 0 |
| Failed quality control (qflag set) | 0 |
| -9999, non-numeric or out-of-range values | 0 |
| Days with TMAX below TMIN | 0 |
| Duplicate primary keys | 0 |
| Trace precipitation (mflag T) | 1,824 rows, value 0, kept |
| sflag "1" (not in the script's code list) | 43,417 rows, kept |
| obstime filled | 37,355 of 120,371 rows; one value per (station, element) |

Coverage is close to complete for temperature, precipitation and wind (at most 6 missing days per airport in 2025). Snowfall and snow depth are often not reported: LAX, SFO, OAK, HNL and SAN have no snowfall rows at all. A missing row means "not reported", not zero.

## Flight prices (Expedia, D1)

82,136,143 of 82,138,753 rows became fare quotes; 2,610 (0.003%) were rejected. Each input row is one fare observation (a legId seen on a search date with a ticket type), so all observations across search dates and ticket types are preserved.

**Processing approach**

- The 31 GB file is read in 250,000-row chunks with pandas, so it never has to fit in memory.
- A small SQLite database on disk records each legId the first time it appears. Later rows for the same legId add a fare quote but no new itinerary or segments.
- `quote_id` is a global counter across chunks, so it is unique without a database sequence.

**Rules applied**

- **Row fields.** legId must be non-blank (all were 32-character hex). searchDate and flightDate must be valid dates. totalFare must be numeric and non-negative. isBasicEconomy, isRefundable and isNonStop must be True or False. travelDuration must be ISO 8601 (for example `PT5H32M`).
- **Segment split.** The eleven `segments*` columns are split on `||` and numbered 1, 2, 3, ... as `segment_no`. All lists in a row must have the same length.
- **Segment checks.** Airports must be 3 letters, airline codes valid, departure and arrival timestamps parseable with arrival after departure, and the next segment must depart after the previous one arrives.
- **Alignment.** isNonStop must match the segment count. Segment durations, epoch seconds and travelDuration were cross-checked against the timestamps.
- **Metro-area searches.** Expedia searches by city, so a search from DFW can return a flight from Dallas Love Field (DAL). The first or last segment airport may therefore differ from startingAirport or destinationAirport. These rows are real fares and are kept; the itinerary's true origin and destination come from its segments.
- **legId consistency.** A legId that reappears with different segments, flightDate or isNonStop is rejected, keeping its first version, so every `books` row points at a segment that exists.
- **Cabin.** segmentsCabinCode belongs to the quote, not the itinerary, so it goes to `books` (quote\_id, segment\_no, cabin\_code).
- **Not stored** (crossed out in the outline): fareBasisCode, elapsedDays, baseFare, seatsRemaining, the epoch-second columns, equipment description and segment duration (computed in queries). segmentsDistance moves to `route`.

**What the checks found**

| Check | Result |
| --- | --- |
| Malformed dates, fares, booleans, codes or timestamps | 0 |
| Segment lists of different lengths | 0 |
| isNonStop disagreeing with segment count | 0 |
| Malformed travelDuration (rejected) | 142 |
| Next segment departs before previous arrives (rejected) | 17 |
| legId reused with different segments (rejected) | 2,451 |
| Metro-area substitutes (kept) | 4.07 million rows; LAX to ONT 3,099,180, DFW to DAL 915,303, PHL to TTN 70,648, DEN to BJC 10,527 |
| Exact duplicate rows | 0 |
| Rows with no totalTravelDistance (kept as null) | 6,120,137 |
| totalFare above $5,000 (kept) | 111 |
| Days between search and flight | 1 to 60 |
| Cabin codes | coach 99.8%, first 0.08%, premium coach 0.06%, business 0.02% |
| fare\_quote legId not in itinerary | 0 |
| books segment\_no missing from segment | 0 |

## Cross-dataset integration

All three datasets join on standardized IATA codes, and every foreign key in the schema passes.

**How the shared tables are built**

- **airport** (365 rows): the union of airport codes from all three datasets. City and state come from BTS, since D1 and D3 carry codes only.
- **airline** (21 rows): the union of carrier codes. Names come from Expedia's segmentsAirlineName where present, otherwise from a lookup of BTS carrier names.
- **route** (6,151 rows): every directed airport pair flown in BTS or in an Expedia segment. distance\_miles uses BTS Distance when the route is in BTS, otherwise the most common Expedia segmentsDistance.

**Overlap between datasets**

| Measure | Result |
| --- | --- |
| Expedia airports also in BTS 2025 | 192 of 228 |
| Expedia airports with a weather station | 31 of 228 |
| Routes in both Expedia and BTS | 2,699 |
| Carriers in both | AA, AS, B6, DL, F9, HA, NK, UA |
| BTS flights departing a weather airport | 358,500 of 539,747 |
| BTS flights with weather at both ends | 207,321 |

**Known limitations**

- BTS reports the operating carrier (for example SkyWest OO, Envoy MQ, Republic YX), while Expedia shows the marketing carrier (AA, DL, UA). Regional flights therefore compare at the brand level only.
- 36 small or foreign Expedia airports (for example ACK, MVY, CUN) are not in the January 2025 BTS data, so their city and state are null.
- 7 Expedia carriers have no BTS counterpart (3M, 4B, 9K, 9X, KG, LF, SY).
- On 995 shared routes the Expedia distance differs from BTS by more than 5 miles; the BTS value is stored. 31 Expedia-only routes have no distance.
- Prices are from 2022 and performance from 2025, so the two are compared at aggregated airline or route level, not flight by flight. Performance and weather link by airport and date.

**Foreign-key checks (all 0 violations):** route to airport, weather\_station to airport, flight\_operation to airline and route, delayed\_flight to flight\_operation, weather\_observation to weather\_station, segment to itinerary, airline and route, fare\_quote to itinerary, and books to segment through fare\_quote.leg\_id. The full D2 and D3 tables plus a synthetic D1 test sample were also loaded into PostgreSQL 16 with the schema's constraints enabled, and all of them loaded without error.

## Final tables and how to reproduce

The cleaned output is about 10.4 GB of CSV across 11 tables.

| Table | Rows | Source |
| --- | --- | --- |
| books | 150,191,099 | D1 |
| fare\_quote | 82,136,143 | D1 |
| segment | 12,579,730 | D1 |
| itinerary | 5,999,650 | D1 |
| flight\_operation | 539,747 | D2 |
| weather\_observation | 120,371 | D3 |
| delayed\_flight | 98,130 | D2 |
| route | 6,151 | D1 + D2 |
| airport | 365 | D1 + D2 + D3 |
| weather\_station | 32 | D3 |
| airline | 21 | D1 + D2 |

Itineraries by number of segments: nonstop 651,615; 2 segments 4,133,183; 3 segments 1,197,691; 4 segments 17,129; 5 segments 32.

**To reproduce** (Python 3 with pandas, from the `cleaning/` folder):

```
py clean_bts.py --input flight_delays_2025_01.csv --out output
py clean_ghcn.py --input ghcn_raw_2025.csv --out output
py clean_itineraries.py --input itineraries.csv --out output
py build_dimensions.py --out output
psql -h <host> -U <user> -d <db> -f schema_BCNF_fixed.sql
psql -h <host> -U <user> -d <db> -f load.sql
```

Each step writes a report (`report_bts.md`, `report_ghcn.md`, `report_itineraries.md`, `report_integration.md`) and a rejects file listing every excluded row with its reason. In our run, the Expedia metro-area rows were first rejected by an earlier version of the script and then restored with `clean_itineraries.py --input output/d1_rejects.csv --append`; a fresh run with the current script keeps them in one pass.
