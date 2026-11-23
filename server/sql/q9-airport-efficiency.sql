-- $1 = airport code, $2 = calendar year.
-- Delay rates use departures with a recorded delay. Cancellation rates use all scheduled departures.
WITH departures AS (
    SELECT COUNT(*) AS total_departures,
           COUNT(dep_delay_min) AS departures_with_delay_data,
           COUNT(*) FILTER (WHERE dep_delay_min >= 15) AS delayed_departures,
           COUNT(*) FILTER (
               WHERE cancellation_code IS NOT NULL
           ) AS cancelled_departures,
           ROUND(100.0 * COUNT(*) FILTER (WHERE dep_delay_min >= 15)
                 / NULLIF(COUNT(dep_delay_min), 0), 2) AS out_delay_rate,
           ROUND(100.0 * COUNT(*) FILTER (
                     WHERE cancellation_code IS NOT NULL
                 ) / NULLIF(COUNT(*), 0), 2) AS cancellation_rate,
           ROUND(AVG(taxi_out_min), 2) AS avg_taxi_out_min,
           COUNT(taxi_out_min) AS departures_with_taxi_out_data,
           MIN(flight_date)::text AS first_departure_date,
           MAX(flight_date)::text AS last_departure_date
    FROM flight_operation
    WHERE origin_code = $1
      AND flight_date >= make_date($2::integer, 1, 1)
      AND flight_date < make_date($2::integer + 1, 1, 1)
), arrivals AS (
    SELECT COUNT(*) AS total_arrivals,
           ROUND(AVG(taxi_in_min), 2) AS avg_taxi_in_min,
           COUNT(taxi_in_min) AS arrivals_with_taxi_in_data,
           MIN(flight_date)::text AS first_arrival_date,
           MAX(flight_date)::text AS last_arrival_date
    FROM flight_operation
    WHERE destination_code = $1
      AND flight_date >= make_date($2::integer, 1, 1)
      AND flight_date < make_date($2::integer + 1, 1, 1)
)
SELECT a.airport_code, $2::integer AS year, d.*, r.*
FROM airport a
CROSS JOIN departures d
CROSS JOIN arrivals r
WHERE a.airport_code = $1;
