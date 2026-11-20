# API Specification (B: Q4, Q5, Q8 + dropdowns)

Run: `cd server && npm install`, copy `.env.example` to `.env` and fill in the DB credentials, then `npm start`.
Base URL: `http://localhost:8080`. Errors return `{ "error": "<message>" }` with status 404 or 500.

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
