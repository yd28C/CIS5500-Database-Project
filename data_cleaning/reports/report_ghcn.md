# GHCN weather (D3) cleaning report


## Input

- file: ghcn_raw_2025.csv
- rows: 120,371
- columns: airport_code, id, date, element, value, mflag, qflag, sflag, obstime

## Airport-to-station mapping

- airports: 32
- stations: 32
- airports with more than one station: 0
- stations with more than one airport: 0
- airport codes that are not 3 letters: 0
- stations that are not the expected USW000+WBAN airport station: 0
- airports in the download list but missing from the file: none
- weather airports not in the BTS airport list: none

## Dates, elements and flags

- date range: 2025-01-01 to 2025-12-31
- unparseable dates (left out): 0
- elements: {'PRCP': 11672, 'TMIN': 11671, 'TMAX': 11670, 'AWND': 11653, 'WSF2': 11652, 'WDF2': 11651, 'WDF5': 11602, 'WSF5': 11598, 'SNOW': 9513, 'SNWD': 9030, 'WT01': 3698, 'WT08': 1666, 'WT03': 1365, 'PGTM': 1045, 'WT02': 351, 'WESD': 277, 'WT04': 95, 'WT06': 68, 'WT07': 35, 'WT05': 28, 'WT09': 27, 'WT10': 3, 'PSUN': 1}
- element codes longer than 4 characters (left out): 0
- qflag values: {<NA>: 120371}
- failed NOAA quality control, qflag not blank (left out): 0
- mflag values (kept): {<NA>: 118547, 'T': 1824}
- mflag codes not in this script's list (kept): 0
- sflag values (kept): {'W': 76668, '1': 43417, '7': 277, 'Z': 9}
- sflag codes not in this script's list (kept; check the GHCN readme): 43,417
- multi-character flags (left out, column is CHAR(1)): 0

## Measurement values

- blank or non-numeric values (left out): 0
- -9999 missing code (left out): 0
- non-integer values (left out): 0
- physically impossible values (left out): 0
- trace (mflag T) rows and their values: 1824 rows, values [0]
- elements with no range check: none
- station-days with TMAX < TMIN (both left out): 0

## Duplicates and completeness

- exact duplicate rows (dropped): 0
- conflicting rows for the same station, date and element (all left out): 0
- missing days per airport for the core elements (out of 365 days)

| airport_code | TMAX | TMIN | PRCP | AWND | SNOW | SNWD |
|---|---|---|---|---|---|---|
| ATL | 0 | 0 | 0 | 2 | 14 | 164 |
| AUS | 0 | 0 | 0 | 0 | 0 | 0 |
| BNA | 0 | 0 | 0 | 3 | 0 | 0 |
| BOS | 0 | 0 | 0 | 0 | 0 | 365 |
| BWI | 0 | 0 | 0 | 0 | 1 | 19 |
| CLT | 0 | 0 | 0 | 0 | 0 | 0 |
| DCA | 0 | 0 | 0 | 1 | 0 | 14 |
| DEN | 0 | 0 | 0 | 0 | 1 | 2 |
| DFW | 0 | 0 | 2 | 0 | 0 | 30 |
| DTW | 0 | 0 | 0 | 0 | 0 | 0 |
| EWR | 0 | 0 | 0 | 0 | 0 | 1 |
| FLL | 2 | 2 | 1 | 0 | 4 | 4 |
| HNL | 2 | 2 | 2 | 2 | 365 | 365 |
| IAD | 0 | 0 | 0 | 1 | 2 | 17 |
| IAH | 0 | 0 | 0 | 1 | 0 | 2 |
| JFK | 0 | 0 | 0 | 0 | 0 | 1 |
| LAS | 0 | 0 | 0 | 0 | 0 | 0 |
| LAX | 0 | 0 | 0 | 0 | 365 | 365 |
| LGA | 0 | 0 | 0 | 0 | 0 | 0 |
| MCO | 0 | 0 | 0 | 1 | 0 | 0 |
| MDW | 0 | 0 | 0 | 0 | 364 | 230 |
| MIA | 0 | 0 | 0 | 3 | 6 | 7 |
| MSP | 0 | 0 | 0 | 1 | 0 | 0 |
| OAK | 0 | 0 | 0 | 2 | 365 | 365 |
| ORD | 0 | 0 | 0 | 0 | 0 | 0 |
| PHL | 0 | 0 | 0 | 0 | 0 | 0 |
| PHX | 0 | 0 | 0 | 0 | 0 | 5 |
| SAN | 2 | 1 | 0 | 2 | 313 | 313 |
| SEA | 0 | 0 | 1 | 0 | 0 | 0 |
| SFO | 0 | 0 | 0 | 2 | 365 | 365 |
| SLC | 4 | 4 | 2 | 6 | 2 | 16 |
| TPA | 0 | 0 | 0 | 0 | 0 | 0 |

- note: SNOW/SNWD are often not reported at warm-climate airports; a missing row means 'not reported', not 0
- obstime filled: 37355 of 120371 rows
- (station, element) pairs with more than one obstime: 0
- obstime values: {nan: 83016, '2400': 36990, '0600': 365}

## Output

- measurements left out: 0
- weather_observation rows: 120,371
- weather_station rows: 32
