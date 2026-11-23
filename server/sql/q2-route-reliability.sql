-- $1 = origin, $2 = destination. Delay rates use flights measured in each direction.
SELECT a.airline_name, fo.origin_code, fo.destination_code,
       COUNT(*) AS total_flights,
       ROUND(100.0 * COUNT(*) FILTER (WHERE fo.dep_delay_min >= 15)
             / NULLIF(COUNT(fo.dep_delay_min), 0), 2) AS out_delay_rate,
       ROUND(100.0 * COUNT(*) FILTER (WHERE fo.arr_delay_min >= 15)
             / NULLIF(COUNT(fo.arr_delay_min), 0), 2) AS in_delay_rate,
       ROUND(100.0 * COUNT(*) FILTER (WHERE fo.cancellation_code IS NOT NULL)
             / COUNT(*), 2) AS cancellation_rate
FROM flight_operation fo
JOIN airline a ON a.airline_code = fo.airline_code
WHERE fo.origin_code = $1 AND fo.destination_code = $2
  AND fo.flight_date >= DATE '2025-01-01' AND fo.flight_date < DATE '2026-01-01'
GROUP BY a.airline_code, a.airline_name, fo.origin_code, fo.destination_code
ORDER BY in_delay_rate ASC NULLS LAST, a.airline_code;
