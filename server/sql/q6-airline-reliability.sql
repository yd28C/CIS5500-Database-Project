-- $1 = airline code. The denominator of all three rates is scheduled flights.
WITH operations AS (
    SELECT operation_id, arr_delay_min, cancellation_code, diverted
    FROM flight_operation
    WHERE airline_code = $1
      AND flight_date >= DATE '2025-01-01' AND flight_date < DATE '2026-01-01'
), reliability AS (
    SELECT COUNT(*) AS total_flights,
           ROUND(100.0 * COUNT(*) FILTER (
                     WHERE arr_delay_min < 15 AND cancellation_code IS NULL AND diverted = FALSE
                 ) / NULLIF(COUNT(*), 0), 2) AS on_time_rate,
           ROUND(100.0 * COUNT(*) FILTER (WHERE arr_delay_min >= 15)
                 / NULLIF(COUNT(*), 0), 2) AS scheduled_in_delay_rate,
           ROUND(100.0 * COUNT(*) FILTER (WHERE cancellation_code IS NOT NULL)
                 / NULLIF(COUNT(*), 0), 2) AS cancellation_rate,
           ROUND(AVG(arr_delay_min) FILTER (WHERE arr_delay_min > 0), 2) AS avg_delay_duration
    FROM operations
), delay_causes AS (
    SELECT SUM(df.carrier_delay_min) AS carrier_delay,
           SUM(df.weather_delay_min) AS weather_delay,
           SUM(df.nas_delay_min) AS nas_delay,
           SUM(df.security_delay_min) AS security_delay,
           SUM(df.late_aircraft_delay_min) AS late_aircraft_delay
    FROM operations fo
    JOIN delayed_flight df ON df.operation_id = fo.operation_id
)
SELECT a.airline_name, r.*, d.*
FROM airline a
CROSS JOIN reliability r
CROSS JOIN delay_causes d
WHERE a.airline_code = $1;
