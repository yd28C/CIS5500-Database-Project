-- $1 = airport code, $2 = calendar year.
-- Group each source by month before joining so each observation is counted once.
WITH months AS (
    SELECT generate_series(1, 12) AS month
), monthly_weather AS (
    -- GHCN units: TMAX in tenths of °C, PRCP in tenths of mm, SNOW in mm.
    SELECT EXTRACT(MONTH FROM wo.observation_date)::integer AS month,
           ROUND(AVG(wo.raw_value / 10.0) FILTER (
                     WHERE wo.element_code = 'TMAX' AND wo.raw_value <> -9999
                 ) * 9 / 5 + 32, 2) AS avg_daily_max_temp_f,
           ROUND(SUM(wo.raw_value / 254.0) FILTER (
                     WHERE wo.element_code = 'PRCP' AND wo.raw_value >= 0
                 ), 2) AS precipitation_inches,
           ROUND(SUM(wo.raw_value) FILTER (
                     WHERE wo.element_code = 'SNOW' AND wo.raw_value >= 0
                 ) / 25.4, 2) AS snowfall_inches,
           COUNT(*) FILTER (
               WHERE wo.element_code = 'SNOW' AND wo.raw_value >= 0
           ) AS snowfall_days,
           COUNT(*) FILTER (
               WHERE wo.element_code = 'TMAX' AND wo.raw_value <> -9999
           ) AS temperature_days,
           COUNT(*) FILTER (
               WHERE wo.element_code = 'PRCP' AND wo.raw_value >= 0
           ) AS precipitation_days
    FROM weather_observation wo
    JOIN weather_station s ON s.station_id = wo.station_id
    WHERE s.airport_code = $1
      AND wo.observation_date >= make_date($2::integer, 1, 1)
      AND wo.observation_date < make_date($2::integer + 1, 1, 1)
      AND wo.element_code IN ('TMAX', 'PRCP', 'SNOW')
    GROUP BY EXTRACT(MONTH FROM wo.observation_date)
), monthly_flights AS (
    SELECT EXTRACT(MONTH FROM flight_date)::integer AS month,
           COUNT(*) AS total_departures,
           COUNT(dep_delay_min) AS departures_with_delay_data,
           COUNT(*) FILTER (WHERE dep_delay_min >= 15) AS delayed_departures,
           COUNT(*) FILTER (
               WHERE cancellation_code IS NOT NULL
           ) AS cancelled_departures,
           ROUND(100.0 * COUNT(*) FILTER (WHERE dep_delay_min >= 15)
                 / NULLIF(COUNT(dep_delay_min), 0), 2) AS departure_delay_rate,
           ROUND(100.0 * COUNT(*) FILTER (
                     WHERE cancellation_code IS NOT NULL
                 ) / NULLIF(COUNT(*), 0), 2) AS cancellation_rate,
           MIN(flight_date)::text AS first_departure_date,
           MAX(flight_date)::text AS last_departure_date
    FROM flight_operation
    WHERE origin_code = $1
      AND flight_date >= make_date($2::integer, 1, 1)
      AND flight_date < make_date($2::integer + 1, 1, 1)
    GROUP BY EXTRACT(MONTH FROM flight_date)
)
SELECT a.airport_code, $2::integer AS year, s.station_id AS weather_station_id, m.month,
       EXTRACT(DAY FROM (
           make_date($2::integer, m.month, 1)
           + INTERVAL '1 month' - INTERVAL '1 day'
       ))::integer AS days_in_month,
       w.avg_daily_max_temp_f, w.precipitation_inches, w.snowfall_inches,
       COALESCE(w.snowfall_days, 0) AS snowfall_days,
       COALESCE(w.temperature_days, 0) AS temperature_days,
       COALESCE(w.precipitation_days, 0) AS precipitation_days,
       COALESCE(f.total_departures, 0) AS total_departures,
       COALESCE(f.departures_with_delay_data, 0) AS departures_with_delay_data,
       COALESCE(f.delayed_departures, 0) AS delayed_departures,
       COALESCE(f.cancelled_departures, 0) AS cancelled_departures,
       f.departure_delay_rate, f.cancellation_rate,
       f.first_departure_date, f.last_departure_date
FROM airport a
CROSS JOIN months m
LEFT JOIN weather_station s ON s.airport_code = a.airport_code
LEFT JOIN monthly_weather w ON w.month = m.month
LEFT JOIN monthly_flights f ON f.month = m.month
WHERE a.airport_code = $1
ORDER BY m.month;
