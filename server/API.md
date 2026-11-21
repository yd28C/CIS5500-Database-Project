# API Specification: airline and airport endpoints

Run: `cd server && npm install`, copy `.env.example` to `.env` and fill in the DB credentials, then `npm start`.
Base URL: `http://localhost:8080`. Errors return `{ "error": "<message>" }` with an HTTP error status. The Part D routes also return 400 for invalid parameters.

---

### GET /airlines
All airlines, for dropdowns.
- Request params: none
- Response: array of `{ airline_code: string, airline_name: string }`

### GET /airports
All airports, for dropdowns.
- Request params: none
- Response: array of `{ airport_code: string, city: string, state: string }`

---

### Q4: GET /airlines/:airlineCode/summary
An airline's network size and average nonstop ticket price.

| Param | Type | In | Required | Description |
|---|---|---|---|---|
| airlineCode | string | path | yes | airline code, e.g. `AA` |

Query parameters used in SQL: `$1 = airlineCode`

Response (object):

| Field | Type | Description |
|---|---|---|
| airline_code | string | airline code |
| airline_name | string | airline name |
| cities_served | integer | distinct destination cities |
| airports_served | integer | distinct destination airports |
| total_routes | integer | distinct origin-destination pairs |
| avg_ticket_price | number | average nonstop fare (null if none) |

404 if the airline does not exist.

### Q5: GET /airlines/:airlineCode/top-routes
An airline's busiest routes by number of flights.

| Param | Type | In | Required | Description |
|---|---|---|---|---|
| airlineCode | string | path | yes | airline code, e.g. `AA` |
| limit | integer | query | no | number of routes, default 5 |

Query parameters used in SQL: `$1 = airlineCode`, `$2 = limit`

Response: array of `{ origin_code: string, destination_code: string, number_of_flights: integer }`, busiest first.

### Q8: GET /airports/:airportCode/top-routes
An airport's busiest departing routes in a year.

| Param | Type | In | Required | Description |
|---|---|---|---|---|
| airportCode | string | path | yes | airport code, e.g. `PHL` |
| limit | integer | query | no | number of routes, default 5 |
| year | integer | query | no | year, default 2025 |

Query parameters used in SQL: `$1 = airportCode`, `$2 = limit`, `$3 = year`

Response: array of `{ origin_code: string, destination_code: string, number_of_flights: integer }`, busiest first.

---

## Airports page · Part D (Q7, Q9, Q10)

| Method | Path | Result |
|---|---|---|
| GET | `/airports/:airportCode/overview` | One airport profile and its recorded outbound network (Q7) |
| GET | `/airports/:airportCode/efficiency` | One object with outbound reliability and taxi time by direction (Q9) |
| GET | `/airports/:airportCode/weather-reliability` | Array of 12 monthly weather and outbound reliability records, January first (Q10) |

### Inputs for all three routes

| Name | In | Type | Required | Meaning |
|---|---|---|---|---|
| `airportCode` | path | string | yes | Three letters identifying an airport in the airport table. Case-insensitive. |
| `year` | query | integer | no | Four digits, 1900–2100 inclusive. Defaults to 2025, as in Q8. Supply at most once. |

Each SQL file receives `$1` (uppercase airport code) and `$2` (calendar year). Records must fall on or after January 1 of that year and before January 1 of the next year. Q9 applies the same dates to both directions. Q10 filters both weather observation dates and flight dates.

The following field names and types apply to every result object, including each row of Q10.

| Field | Type | Meaning |
|---|---|---|
| `airport_code`, `year` | string, integer | Selected airport and calendar year |
| `total_departures` | integer | Recorded scheduled flights with the airport as origin during the year (month for Q10), including cancellations |
| `first_departure_date`, `last_departure_date` | string or null | Earliest and latest outbound flight dates in the group (YYYY-MM-DD). Intermediate dates may have gaps. |

Known airports return 200 even when a period has no records. Empty groups have zero record counts, null dates, and null rates/averages. An invalid airport-code format, unsupported parameter, empty, repeated, or invalid year returns 400. An unknown airport returns 404. A database failure returns 500. The response shape for errors is `{"error":"message"}`.

### Q7 · Airport overview

`GET /airports/PHL/overview?year=2025`

Use this object for the airport profile and network figures. In addition to the common fields, it includes:

| Field | Type | Meaning |
|---|---|---|
| `city`, `state` | string or null | City label and state as stored in the airport table |
| `airlines_served` | integer | Distinct operating carriers among outbound records |
| `destinations` | integer | Distinct scheduled destination airports among outbound records |

Example from the project RDS:

```json
{"airport_code":"PHL","year":2025,"city":"Philadelphia, PA","state":"PA","total_departures":97519,"airlines_served":11,"destinations":88,"first_departure_date":"2025-01-01","last_departure_date":"2025-12-31"}
```

### Q9 · Airport efficiency

`GET /airports/PHL/efficiency?year=2025`

Both Q9 and Q10 return these outbound measures. Q9 groups the full year and Q10 groups each month separately.

| Field | Type | Meaning |
|---|---|---|
| `departures_with_delay_data` | integer | Outbound records with a measured departure delay (early departures included) |
| `delayed_departures` | integer | Outbound records at least 15 minutes late |
| `cancelled_departures` | integer | Outbound records with a non-null BTS cancellation code |
| `departure_delay_rate` | number or null | 100 × delayed_departures / departures_with_delay_data |
| `cancellation_rate` | number or null | 100 × cancelled_departures / total_departures |

Rates are percentages rounded to two decimals. Each rate is null when its denominator is zero. To recover an annual rate from months, sum the underlying counts before dividing.

| Additional Q9 field | Type | Meaning |
|---|---|---|
| `total_arrivals` | integer | Scheduled records with this airport as destination, filtered by flight date |
| `avg_taxi_out_min`, `departures_with_taxi_out_data` | number or null, integer | Mean recorded outbound taxi-out minutes and its count of non-null observations |
| `avg_taxi_in_min`, `arrivals_with_taxi_in_data` | number or null, integer | Mean recorded inbound taxi-in minutes and its count of non-null observations |
| `first_arrival_date`, `last_arrival_date` | string or null | First/latest flight date among inbound records |

PHL example (selected response fields): 22,822 of 95,672 measured departures were delayed, giving `departure_delay_rate: 23.85`. There were 2,039 cancellations among 97,519 scheduled departures, giving `cancellation_rate: 2.09`. The mean taxi-out and taxi-in times were 22.10 and 8.13 minutes, respectively.

### Q10 · Monthly weather and reliability

`GET /airports/PHL/weather-reliability?year=2025`

Weather and outbound flights are aggregated separately by month before joining to a 12-month calendar. The weather station maps to the airport through the unique airport code in weather_station. An airport without a station retains its flight statistics. These monthly series describe historical patterns.

| Additional field in each monthly object | Type | Meaning |
|---|---|---|
| `weather_station_id` | string or null | Station mapped to the selected airport |
| `month`, `days_in_month` | integer | Calendar month (1–12) and its length |
| `avg_daily_max_temp_f` | number or null | Average daily high across valid TMAX observations, in °F. Raw tenths of °C are divided by 10 before conversion. |
| `precipitation_inches` | number or null | Sum of reported daily PRCP, in inches. Raw units are tenths of a millimeter, divided by 254. |
| `snowfall_inches` | number or null | Sum of reported new snowfall (SNOW), in inches. Raw units are millimeters, divided by 25.4. |
| `temperature_days`, `precipitation_days`, `snowfall_days` | integer | Number of valid daily observations used for the corresponding statistic, including reported zeros |

Each weather statistic is null when its observation count is zero. A total with fewer observed days than calendar days covers only those reported days. Missing months still appear in the array.

First object in the PHL 2025 response:

```json
{"airport_code":"PHL","year":2025,"weather_station_id":"USW00013739","month":1,"days_in_month":31,"avg_daily_max_temp_f":36.98,"precipitation_inches":0.93,"snowfall_inches":4.65,"snowfall_days":31,"temperature_days":31,"precipitation_days":31,"total_departures":6688,"departures_with_delay_data":6511,"delayed_departures":1149,"cancelled_departures":185,"departure_delay_rate":17.65,"cancellation_rate":2.77,"first_departure_date":"2025-01-01","last_departure_date":"2025-01-31"}
```

### Run the Part D checks

From `server/`, run `npm ci` if dependencies are missing, configure the project database in `.env`, and start the server with `npm start`. In a second terminal in `server/`, run:

```sh
python3 test/airport_api.py
```

The tests use Python's standard library and issue read-only HTTP requests. By default they target `http://localhost:8080` (override with `AIRPORT_API_URL`). Use the project dataset for these checks. They compare PHL's January flight counts and twelve months of weather to the checked-in BTS and NOAA CSVs. They also check annual/monthly consistency, the Q8 route and airport dropdown, an airport without a station, an empty leap year, and invalid parameters.
