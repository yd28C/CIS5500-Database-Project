-- $1 = airport code, $2 = calendar year.
-- Scheduled departures include cancelled flights.
WITH departures AS (
    SELECT COUNT(*) AS total_departures,
           COUNT(DISTINCT airline_code) AS airlines_served,
           COUNT(DISTINCT destination_code) AS destinations,
           MIN(flight_date)::text AS first_departure_date,
           MAX(flight_date)::text AS last_departure_date
    FROM flight_operation
    WHERE origin_code = $1
      AND flight_date >= make_date($2::integer, 1, 1)
      AND flight_date < make_date($2::integer + 1, 1, 1)
)
SELECT a.airport_code, $2::integer AS year, a.city, a.state,
       d.total_departures, d.airlines_served, d.destinations,
       d.first_departure_date, d.last_departure_date
FROM airport a
CROSS JOIN departures d
WHERE a.airport_code = $1;
