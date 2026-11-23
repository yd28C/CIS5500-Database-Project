-- $1 = airline code. Network counts use the historical itinerary segments.
WITH network_stats AS (
    SELECT COUNT(DISTINCT (ap.city, ap.state))
               FILTER (WHERE ap.city IS NOT NULL AND ap.state IS NOT NULL) AS cities_served,
           COUNT(DISTINCT s.destination_code) AS airports_served,
           COUNT(DISTINCT (s.origin_code, s.destination_code)) AS total_routes
    FROM segment s
    JOIN airport ap ON ap.airport_code = s.destination_code
    WHERE s.airline_code = $1
), price_stats AS (
    SELECT ROUND(AVG(f.total_fare), 2) AS avg_ticket_price
    FROM segment s
    JOIN itinerary i ON i.leg_id = s.leg_id
    JOIN fare_quote f ON f.leg_id = i.leg_id
    WHERE s.airline_code = $1 AND i.is_nonstop
      AND f.search_date >= DATE '2022-01-01' AND f.search_date < DATE '2023-01-01'
)
SELECT a.airline_code, a.airline_name, n.cities_served, n.airports_served,
       n.total_routes, p.avg_ticket_price
FROM airline a
CROSS JOIN network_stats n
CROSS JOIN price_stats p
WHERE a.airline_code = $1;
