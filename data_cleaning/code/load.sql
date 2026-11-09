-- Load the cleaned CSVs into the Milestone 2 schema. Run from the repository root:
--     psql -h <host> -U <user> -d <db> -f code/schema_BCNF_fixed.sql
--     psql -h <host> -U <user> -d <db> -f code/load.sql
-- \copy reads the files on your computer, so this works against AWS RDS too.
-- The four big Expedia tables are not in the GitHub repo; regenerate them first (see README).

\copy airport             FROM 'data/cleaned/airport.csv'             WITH (FORMAT csv, HEADER true)
\copy airline             FROM 'data/cleaned/airline.csv'             WITH (FORMAT csv, HEADER true)
\copy route               FROM 'data/cleaned/route.csv'               WITH (FORMAT csv, HEADER true)

\copy flight_operation    FROM 'data/cleaned/flight_operation.csv'    WITH (FORMAT csv, HEADER true)
\copy delayed_flight      FROM 'data/cleaned/delayed_flight.csv'      WITH (FORMAT csv, HEADER true)

\copy weather_station     FROM 'data/cleaned/weather_station.csv'     WITH (FORMAT csv, HEADER true)
\copy weather_observation FROM 'data/cleaned/weather_observation.csv' WITH (FORMAT csv, HEADER true)

\copy itinerary           FROM 'data/cleaned/itinerary.csv'           WITH (FORMAT csv, HEADER true)
\copy segment             FROM 'data/cleaned/segment.csv'             WITH (FORMAT csv, HEADER true)
\copy fare_quote          FROM 'data/cleaned/fare_quote.csv'          WITH (FORMAT csv, HEADER true)
\copy books               FROM 'data/cleaned/books.csv'               WITH (FORMAT csv, HEADER true)

SELECT setval(pg_get_serial_sequence('flight_operation', 'operation_id'), COALESCE(MAX(operation_id), 1)) FROM flight_operation;
SELECT setval(pg_get_serial_sequence('fare_quote', 'quote_id'), COALESCE(MAX(quote_id), 1)) FROM fare_quote;
ANALYZE;
