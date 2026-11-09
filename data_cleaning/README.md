# Flight Price & Reliability: data and cleaning (CIS 5500, Milestone 2)

Raw data, cleaned data, cleaning code and documentation for three datasets that load into
the BCNF schema in `code/schema_BCNF_fixed.sql`. The full methodology and the results of every
check are in [docs/data_cleaning_methodology.md](docs/data_cleaning_methodology.md).

## Folder layout

```
code/                    cleaning scripts, schema and load script
  clean_bts.py           D2 flight performance  -> flight_operation, delayed_flight
  clean_ghcn.py          D3 weather             -> weather_station, weather_observation
  clean_itineraries.py   D1 flight prices       -> itinerary, segment, fare_quote, books (chunked)
  build_dimensions.py    shared airport, airline, route + foreign-key checks
  common.py              shared helpers
  schema_BCNF_fixed.sql  PostgreSQL DDL
  load.sql               \copy every table in foreign-key order
data/raw/                uncleaned data
  ghcn_raw_2025.csv              NOAA GHCN-Daily, 32 airport stations, 2025
  flight_delays_2025_01.csv.gz   BTS On-Time Performance, January 2025 (gzipped)
  itineraries_sample.csv         first 10,000 rows of the Expedia file
data/cleaned/            cleaned tables, one CSV per schema table
  samples/               first 10,000 rows of the four big Expedia tables
docs/                    cleaning methodology
reports/                 per-script check reports and rejected rows
```

## Data not stored in GitHub

GitHub rejects files over 100 MB, so these are listed in `.gitignore`:

| File | Size | How to get it |
|---|---|---|
| Raw Expedia `itineraries.csv` | 31 GB | [Kaggle: dilwong/flightprices](https://www.kaggle.com/datasets/dilwong/flightprices) |
| `data/cleaned/fare_quote.csv` | 5.9 GB | run `code/clean_itineraries.py` |
| `data/cleaned/books.csv` | 2.7 GB | run `code/clean_itineraries.py` |
| `data/cleaned/segment.csv` | 1.3 GB | run `code/clean_itineraries.py` |
| `data/cleaned/itinerary.csv` | 381 MB | run `code/clean_itineraries.py` |

The other sources: BTS [On-Time Reporting Carrier On-Time Performance](https://www.transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FGJ&QO_fu146_anzr=b0-gvzr)
and NOAA [GHCN-Daily](https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/).

## Reproduce

Python 3 with pandas (`pip install pandas`), from the repository root:

```
python code/clean_bts.py --input <flight_delays_2025_01.csv> --out data/cleaned
python code/clean_ghcn.py --input data/raw/ghcn_raw_2025.csv --out data/cleaned
python code/clean_itineraries.py --input <itineraries.csv> --out data/cleaned
python code/build_dimensions.py --out data/cleaned
```

`clean_itineraries.py` takes about 75 minutes on the full file. Each script prints and
saves a report of its checks; rejected rows are written with the reason.

## Load into PostgreSQL

```
psql -h <host> -U <user> -d <db> -f code/schema_BCNF_fixed.sql
psql -h <host> -U <user> -d <db> -f code/load.sql
```

## Row counts

| Table | Rows |
|---|---|
| books | 150,191,099 |
| fare_quote | 82,136,143 |
| segment | 12,579,730 |
| itinerary | 5,999,650 |
| flight_operation | 539,747 |
| weather_observation | 120,371 |
| delayed_flight | 98,130 |
| route | 6,151 |
| airport | 365 |
| weather_station | 32 |
| airline | 21 |
