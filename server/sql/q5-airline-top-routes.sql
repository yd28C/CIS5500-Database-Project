-- $1 = airline code, $2 = maximum number of routes.
SELECT origin_code, destination_code, COUNT(*) AS number_of_flights
FROM flight_operation
WHERE airline_code = $1
  AND flight_date >= DATE '2025-01-01' AND flight_date < DATE '2026-01-01'
GROUP BY origin_code, destination_code
ORDER BY number_of_flights DESC, origin_code, destination_code
LIMIT $2;
