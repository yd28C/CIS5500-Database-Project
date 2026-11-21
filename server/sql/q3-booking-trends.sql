WITH booking_prices AS (
    SELECT
        i.flight_date - f.search_date AS days_before,
        f.total_fare
    FROM fare_quote f
    JOIN itinerary i
        ON f.leg_id = i.leg_id
    WHERE f.search_date >= DATE '2022-01-01'
      AND f.search_date < DATE '2023-01-01'
      AND i.is_nonstop = TRUE
      AND i.flight_date >= f.search_date
)
SELECT
    CASE
        WHEN days_before BETWEEN 1 AND 3 THEN '1-3 days'
        WHEN days_before BETWEEN 4 AND 7 THEN '4-7 days'
        WHEN days_before BETWEEN 8 AND 14 THEN '8-14 days'
        WHEN days_before BETWEEN 15 AND 30 THEN '15-30 days'
        ELSE '30+ days'
    END AS booking_window,
    ROUND(AVG(total_fare), 2) AS avg_price,
    COUNT(*) AS total_quotes
FROM booking_prices
WHERE days_before >= 1
GROUP BY booking_window
ORDER BY MIN(days_before);
