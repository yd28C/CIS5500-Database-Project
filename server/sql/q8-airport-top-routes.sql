-- $1 = airport code, $2 = maximum number of routes, $3 = operations year (2025).
SELECT origin_code, destination_code, COUNT(*) AS number_of_flights
FROM flight_operation
WHERE origin_code = $1
  AND flight_date >= make_date($3, 1, 1) AND flight_date < make_date($3 + 1, 1, 1)
GROUP BY origin_code, destination_code
ORDER BY number_of_flights DESC, destination_code
LIMIT $2;
