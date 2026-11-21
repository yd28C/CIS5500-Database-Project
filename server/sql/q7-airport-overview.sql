-- $1 = airport code, $2 = calendar year. Scheduled traffic includes cancellations.
WITH traffic AS (
    SELECT COUNT(*) FILTER (WHERE origin_code = $1) AS total_departures,
           COUNT(*) FILTER (WHERE destination_code = $1) AS total_arrivals,
           COUNT(DISTINCT airline_code) AS airlines_served,
           COUNT(DISTINCT destination_code) FILTER (WHERE origin_code = $1) AS destinations,
           (MIN(flight_date) FILTER (WHERE origin_code = $1))::text AS first_departure_date,
           (MAX(flight_date) FILTER (WHERE origin_code = $1))::text AS last_departure_date
    FROM flight_operation
    WHERE (origin_code = $1 OR destination_code = $1)
      AND flight_date >= make_date($2::integer, 1, 1)
      AND flight_date < make_date($2::integer + 1, 1, 1)
)
SELECT a.airport_code, $2::integer AS year, a.city, a.state,
       t.total_departures, t.total_arrivals,
       t.total_departures + t.total_arrivals AS total_scheduled_operations,
       t.airlines_served, t.destinations, t.first_departure_date, t.last_departure_date
FROM airport a
CROSS JOIN traffic t
WHERE a.airport_code = $1;
