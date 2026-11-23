-- Compare individual 2025 operations with separately aggregated historical data.
WITH selected AS (
  SELECT fo.*, a.airline_name
  FROM flight_operation fo
  LEFT JOIN airline a ON a.airline_code = fo.airline_code
  WHERE fo.origin_code = $1 AND fo.destination_code = $2 AND fo.flight_date = $3::date
    AND ($4::integer IS NULL OR fo.scheduled_dep_hhmm >= $4)
    AND ($5::integer IS NULL OR fo.scheduled_dep_hhmm < $5)
), carriers AS (
  SELECT DISTINCT airline_code FROM selected
), reliability AS (
  SELECT fo.airline_code, COUNT(*) AS monthly_flights,
    COUNT(fo.dep_delay_min) AS measured_departures,
    ROUND(100.0 * COUNT(*) FILTER (WHERE fo.dep_delay_min >= 15) / NULLIF(COUNT(fo.dep_delay_min), 0), 2) AS out_delay_rate,
    ROUND(100.0 * COUNT(*) FILTER (WHERE fo.cancellation_code IS NOT NULL) / NULLIF(COUNT(*), 0), 2) AS cancellation_rate
  FROM flight_operation fo JOIN carriers c ON c.airline_code = fo.airline_code
  WHERE fo.origin_code = $1 AND fo.destination_code = $2
    AND fo.flight_date >= date_trunc('month', $3::date)::date
    AND fo.flight_date < (date_trunc('month', $3::date) + interval '1 month')::date
  GROUP BY fo.airline_code
), fares AS (
  SELECT s.airline_code,
    ROUND(percentile_cont(0.5) WITHIN GROUP (ORDER BY f.total_fare)::numeric, 2) AS median_fare,
    MIN(f.total_fare) AS min_fare, MAX(f.total_fare) AS max_fare, COUNT(*) AS quote_count
  FROM itinerary i JOIN segment s ON s.leg_id = i.leg_id
  JOIN carriers c ON c.airline_code = s.airline_code
  JOIN fare_quote f ON f.leg_id = i.leg_id
  WHERE i.is_nonstop AND s.origin_code = $1 AND s.destination_code = $2
    AND i.flight_date >= make_date(2022, EXTRACT(MONTH FROM $3::date)::integer, 1)
    AND i.flight_date < make_date(2022, EXTRACT(MONTH FROM $3::date)::integer, 1) + interval '1 month'
    AND f.search_date >= DATE '2022-01-01' AND f.search_date < DATE '2023-01-01'
    AND ($6 = 'any' OR ($6 = 'basic' AND f.is_basic_economy) OR ($6 = 'refundable' AND f.is_refundable))
  GROUP BY s.airline_code
)
SELECT selected.operation_id, selected.flight_number, selected.airline_code, selected.airline_name,
  selected.scheduled_dep_hhmm, selected.scheduled_arr_hhmm, selected.scheduled_elapsed_min,
  selected.cancellation_code, selected.dep_delay_min, selected.arr_delay_min,
  r.monthly_flights, r.measured_departures, r.out_delay_rate, r.cancellation_rate,
  f.median_fare, f.min_fare, f.max_fare, COALESCE(f.quote_count, 0) AS quote_count
FROM selected
LEFT JOIN reliability r ON r.airline_code = selected.airline_code
LEFT JOIN fares f ON f.airline_code = selected.airline_code
ORDER BY selected.scheduled_dep_hhmm NULLS LAST, selected.flight_number;
