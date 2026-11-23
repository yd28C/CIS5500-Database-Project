# Flight Insights API

The server returns JSON at `http://localhost:8080`. Flight operations and airport weather cover 2025. Historical fares use quotes observed in 2022. Airport requests that accept `year` default to 2025 and accept only that value.

Individual airline or airport details return one object. Searches, rankings, comparisons, monthly series and dropdowns return arrays. An empty ranking or search returns `[]`. An unknown resource on a detail endpoint returns 404. Counts can be zero; an unavailable measurement or a rate with no denominator is null.

Invalid parameters on the numbered routes return 400. A database failure returns 500. Errors use `{"error":"message"}`. For Q5 and Q8, `limit` must be a positive safe integer supplied once; the default is 5.

**Delay rates.** `out_delay_rate` and `in_delay_rate` count delays of at least 15 minutes among flights with a departure or arrival measurement respectively. Q6 uses `scheduled_in_delay_rate` because it divides by all scheduled flights. Rates are percentages.

## Flights

### Q1: GET /flights/search

All request parameters below are URL query parameters. Search individual 2025 flight operations and attach separately aggregated route reliability and 2022 fare references. Historical fares are not prices for the 2025 flights.

| Parameter | Type | Required | Description |
|---|---|---|---|
| origin, destination | string | yes | Three-letter airport codes |
| date | string | yes | 2025 flight date, YYYY-MM-DD |
| departureStart, departureEnd | string | no | Local scheduled departure range, HH:MM; start inclusive and end exclusive |
| ticketType | string | no | `any` (default), `basic`, or `refundable`; filters historical quotes only |

SQL parameters: `$1` origin, `$2` destination, `$3` flight date, `$4` and `$5` local departure times as HHMM integers, `$6` ticket type. Fare statistics match the route, airline code and departure month, with all matching 2022 search dates and booking windows. Empty fare matches return null fare values and zero quotes. Operating and marketing carrier codes may differ. Departure time filtering does not filter historical fares. Invalid inputs return 400; database failures return 500.

Response: an array of flight objects, ordered by local scheduled departure time and flight number.

| Field | Type | Meaning |
|---|---|---|
| operation_id, flight_number | integer | Operation identifier and operating flight number |
| airline_code, airline_name | string, string or null | Operating airline code and name |
| scheduled_dep_hhmm, scheduled_arr_hhmm | integer or null | Local scheduled departure and arrival times as HHMM |
| scheduled_elapsed_min | integer or null | Scheduled duration in minutes |
| cancellation_code | string or null | Cancellation reason code |
| dep_delay_min, arr_delay_min | integer or null | Actual departure and arrival delays, in minutes; negative values indicate early flights |
| monthly_flights, measured_departures | integer | Scheduled flights and flights with departure-delay data on this route, airline and month |
| out_delay_rate, cancellation_rate | number or null | Percentage delayed among measured departures; percentage cancelled among scheduled flights |
| median_fare, min_fare, max_fare | number or null | Median, lowest and highest matching historical fare, in dollars |
| quote_count | integer | Number of matching historical quotes |

### Q2: GET /routes/reliability

Compares airline reliability on a specified 2025 route, ordered by arrival delay rate from lowest to highest (nulls last).

| Param | Type | In | Required | Description |
|---|---|---|---|---|
| origin | string | query | yes | departure airport code, e.g. `PHL` |
| destination | string | query | yes | arrival airport code, e.g. `LAX` |

Query parameters used in SQL: `$1 = origin`, `$2 = destination`

Response: array of `{ airline_name: string or null, origin_code: string, destination_code: string, total_flights: integer, out_delay_rate: number or null, in_delay_rate: number or null, cancellation_rate: number }`.

Delay rates are the percentage of flights delayed by at least 15 minutes among flights with a recorded departure or arrival delay, respectively. Cancellation rate uses all scheduled flights for that airline on the route.

### Q3: GET /flights/booking-trends

Returns nonstop fare averages for quotes observed in 2022 across all routes, grouped by the number of days between the search date and departure date. Same-day searches are excluded. No request or SQL parameters are supported.

Response: an array of `{ booking_window: string, avg_price: number, total_quotes: integer }`, ordered from the shortest booking window to the longest. Empty windows are omitted. Invalid parameters return 400; a database failure returns 500.

## Airlines

### Q4: GET /airlines/:airlineCode/summary

Returns the airline’s historical itinerary network size and average nonstop ticket price from 2022 quotes.

| Param | Type | In | Required | Description |
|---|---|---|---|---|
| airlineCode | string | path | yes | airline code, e.g. `AA` |

Query parameters used in SQL: `$1 = airlineCode`

Response (object):

| Field | Type | Description |
|---|---|---|
| airline_code | string | airline code |
| airline_name | string or null | airline name |
| cities_served | integer | distinct destination cities |
| airports_served | integer | distinct destination airports |
| total_routes | integer | distinct origin-destination pairs |
| avg_ticket_price | number or null | average nonstop fare in dollars from quotes observed in 2022 |

404 if the airline does not exist.

### Q5: GET /airlines/:airlineCode/top-routes

An airline's busiest routes by number of flights.

| Param | Type | In | Required | Description |
|---|---|---|---|---|
| airlineCode | string | path | yes | airline code, e.g. `AA` |
| limit | integer | query | no | positive integer, default 5 |

Query parameters used in SQL: `$1 = airlineCode`, `$2 = limit`

Response: array of `{ origin_code: string, destination_code: string, number_of_flights: integer }`, busiest first, ties by origin then destination. No matches return an empty array.

### Q6: GET /airlines/:airlineCode/reliability

Returns an airline's on-time, delay, and cancellation rates, average delay duration, and total delay minutes by cause.

| Param | Type | In | Required | Description |
|---|---|---|---|---|
| airlineCode | string | path | yes | airline code, e.g. `AA` |

Query parameters used in SQL: `$1 = airlineCode`

Response: one object. An unknown airline returns 404. A known airline with no 2025 operations has zero flights and null rates, averages and cause totals.

| Field | Type | Meaning |
|---|---|---|
| airline_name | string or null | Operating airline name |
| total_flights | integer | Scheduled flights in 2025 |
| on_time_rate | number or null | Percentage of all scheduled flights arriving less than 15 minutes late, excluding cancellations and diversions from the numerator |
| scheduled_in_delay_rate | number or null | Percentage of all scheduled flights arriving at least 15 minutes late |
| cancellation_rate | number or null | Percentage of all scheduled flights with a cancellation code |
| avg_delay_duration | number or null | Mean positive arrival delay in minutes |
| carrier_delay, weather_delay, nas_delay, security_delay, late_aircraft_delay | integer or null | Total delay minutes attributed to the carrier, weather, national airspace system, security, or a late aircraft, respectively |

## Airports

### Shared Q7, Q9 and Q10 inputs and fields

| Name | In | Type | Required | Meaning |
|---|---|---|---|---|
| `airportCode` | path | string | yes | Three letters identifying an airport in the airport table. Case-insensitive. |
| `year` | query | integer | no | Only 2025. Omit to use 2025 or supply once. |

Each SQL file receives `$1` (uppercase airport code) and `$2` (calendar year). Records must fall on or after January 1 of that year and before January 1 of the next year. Q9 applies the same dates to both directions. Q10 filters both weather observation dates and flight dates.

The following fields appear in Q7, Q9 and each Q10 monthly record.

| Field | Type | Meaning |
|---|---|---|
| `airport_code`, `year` | string, integer | Selected airport and calendar year |
| `total_departures` | integer | Recorded scheduled flights with the airport as origin during the year (month for Q10), including cancellations |
| `first_departure_date`, `last_departure_date` | string or null | Earliest and latest outbound flight dates in the group (YYYY-MM-DD). Intermediate dates may have gaps. |

Known airports return 200 even when the selected airport has no recorded operations. Empty groups have zero record counts, null dates, and null rates/averages. An invalid airport-code format, unsupported parameter, empty, repeated, or invalid year returns 400. An unknown airport returns 404. A database failure returns 500. The response shape for errors is `{"error":"message"}`.

### Q7: GET /airports/:airportCode/overview

`GET /airports/PHL/overview?year=2025`

Returns one airport object. Use **Scheduled arrivals + departures** for the main traffic figure. A flight from PHL to JFK contributes one departure at PHL and one arrival at JFK. Cancelled records still count toward the schedule. Summing the figures across airports therefore counts both ends of a flight when both airports are included.

| Field | Type | Meaning |
|---|---|---|
| `city`, `state` | string or null | City label and state as stored in the airport table |
| `total_arrivals` | integer | Scheduled inbound records (airport is the destination) |
| `total_scheduled_operations` | integer | Scheduled arrivals plus scheduled departures at the selected airport |
| `airlines_served` | integer | Distinct operating carriers in either direction, counted once per carrier |
| `destinations` | integer | Distinct scheduled destination airports among outbound records |

Example from the project RDS:

```json
{"airport_code":"PHL","year":2025,"city":"Philadelphia, PA","state":"PA","total_departures":97519,"total_arrivals":97510,"total_scheduled_operations":195029,"airlines_served":11,"destinations":88,"first_departure_date":"2025-01-01","last_departure_date":"2025-12-31"}
```

### Q8: GET /airports/:airportCode/top-routes

Returns the busiest scheduled routes departing from an airport in 2025.

| Parameter | Type | In | Required | Description |
|---|---|---|---|---|
| airportCode | string | path | yes | Three-letter departure airport code |
| limit | integer | query | no | Positive integer, default 5 |
| year | integer | query | no | Only 2025; defaults to 2025 |

SQL parameters: `$1` uppercase airport code, `$2` limit, `$3` year.

Response: array of `{ origin_code: string, destination_code: string, number_of_flights: integer }` with each route's scheduled flight count. Sorted by count descending, then destination. No matches return an empty array.

### Q9: GET /airports/:airportCode/efficiency

`GET /airports/PHL/efficiency?year=2025`

Returns one object with departure reliability and taxi times in each direction. Both Q9 and Q10 return these outbound measures. Q9 groups the full year and Q10 groups each month separately.

| Field | Type | Meaning |
|---|---|---|
| `departures_with_delay_data` | integer | Outbound records with a measured departure delay (early departures included) |
| `delayed_departures` | integer | Outbound records at least 15 minutes late |
| `cancelled_departures` | integer | Outbound records with a non-null BTS cancellation code |
| `out_delay_rate` | number or null | 100 × delayed_departures / departures_with_delay_data |
| `cancellation_rate` | number or null | 100 × cancelled_departures / total_departures |

Rates are percentages rounded to two decimals. Each rate is null when its denominator is zero. To recover an annual rate from months, sum the underlying counts before dividing.

| Additional Q9 field | Type | Meaning |
|---|---|---|
| `total_arrivals` | integer | Scheduled records with this airport as destination, filtered by flight date |
| `avg_taxi_out_min`, `departures_with_taxi_out_data` | number or null, integer | Mean recorded outbound taxi-out minutes and its count of non-null observations |
| `avg_taxi_in_min`, `arrivals_with_taxi_in_data` | number or null, integer | Mean recorded inbound taxi-in minutes and its count of non-null observations |
| `first_arrival_date`, `last_arrival_date` | string or null | First/latest flight date among inbound records |

PHL example (selected response fields): 22,822 of 95,672 measured departures were delayed, giving `out_delay_rate: 23.85`. There were 2,039 cancellations among 97,519 scheduled departures, giving `cancellation_rate: 2.09`. The mean taxi-out and taxi-in times were 22.10 and 8.13 minutes, respectively.

### Q10: GET /airports/:airportCode/weather-reliability

`GET /airports/PHL/weather-reliability?year=2025`

Returns an array of 12 objects in calendar order. Weather and outbound flights are aggregated separately by month before joining to a 12-month calendar. The weather station maps to the airport through the unique airport code in weather_station. An airport without a station retains its flight statistics. These monthly series describe historical patterns.

| Additional field in each monthly object | Type | Meaning |
|---|---|---|
| `weather_station_id` | string or null | Station mapped to the selected airport |
| `month`, `days_in_month` | integer | Calendar month (1–12) and its length |
| `monthly_max_temp_f` | number or null | Highest valid daily TMAX recorded during the month, in °F |
| `monthly_min_temp_f` | number or null | Lowest valid daily TMIN recorded during the month, in °F |
| `precipitation_inches` | number or null | Sum of reported daily PRCP, in inches. Raw units are tenths of a millimeter, divided by 254. |
| `snowfall_inches` | number or null | Sum of reported new snowfall (SNOW), in inches. Raw units are millimeters, divided by 25.4. |
| `tmax_days`, `tmin_days`, `precipitation_days`, `snowfall_days` | integer | Number of valid daily observations used for the corresponding statistic, including reported zeros |

The API returns both temperature extremes. The airport chart displays the monthly high alongside departure delay and cancellation rates. These extrema describe the range of temperatures observed within each month. Each weather statistic is null when its observation count is zero. A total with fewer observed days than calendar days covers only those reported days. Missing months still appear in the array.

First object in the PHL 2025 response:

```json
{"airport_code":"PHL","year":2025,"weather_station_id":"USW00013739","month":1,"days_in_month":31,"monthly_max_temp_f":53.06,"monthly_min_temp_f":10.22,"precipitation_inches":0.93,"snowfall_inches":4.65,"snowfall_days":31,"tmax_days":31,"tmin_days":31,"precipitation_days":31,"total_departures":6688,"departures_with_delay_data":6511,"delayed_departures":1149,"cancelled_departures":185,"out_delay_rate":17.65,"cancellation_rate":2.77,"first_departure_date":"2025-01-01","last_departure_date":"2025-01-31"}
```

## Dropdowns

### GET /airlines

Airline codes and display names for dropdowns, sorted by name.

- Request and SQL parameters: none
- Response: array of `{ airline_code: string, airline_name: string or null }`

### GET /airports

Airport codes, cities and states for dropdowns, sorted by airport code.

- Request and SQL parameters: none
- Response: array of `{ airport_code: string, city: string or null, state: string or null }`

## Run the integration checks

From `server/`, copy `.env.example` to `.env` for first-time setup. Run `npm ci` if dependencies are missing, configure the project database in `.env`, and start the server with `npm start`. In a second terminal in `server/`, run:

```sh
cd test
python3 -B -m unittest -v airport_api test_query_contracts
```

The tests use Python's standard library and issue read-only HTTP requests. By default they target `http://localhost:8080` (override with `AIRPORT_API_URL`). Use the project dataset for these checks. They compare PHL's January flight counts and twelve months of weather to the checked-in BTS and NOAA CSVs. They also check annual/monthly consistency, the Q8 route and airport dropdown, an airport without a station, the supported year, the rate fields, individual airline objects, list responses and invalid parameters.
