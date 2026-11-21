// All API routes. Each route runs one SQL query and returns the rows as JSON.
// Teammates: add your routes below in the same style.
const express = require('express');
const { query } = require('./db');

const router = express.Router();

// ---------- Dropdown options ----------

// GET /airlines: all airlines (for dropdowns)
router.get('/airlines', async (req, res) => {
  try {
    const rows = await query(
      'SELECT airline_code, airline_name FROM airline ORDER BY airline_name'
    );
    res.json(rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Database error' });
  }
});

// GET /airports: all airports (for dropdowns)
router.get('/airports', async (req, res) => {
  try {
    const rows = await query(
      'SELECT airport_code, city, state FROM airport ORDER BY airport_code'
    );
    res.json(rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Database error' });
  }
});

// ---------- Q4: airline network and pricing summary ----------
// GET /airlines/:airlineCode/summary
router.get('/airlines/:airlineCode/summary', async (req, res) => {
  const code = req.params.airlineCode.toUpperCase();
  try {
    const rows = await query(`
      WITH network_stats AS (
        SELECT
          COUNT(DISTINCT ap.city || ', ' || ap.state)
            FILTER (WHERE ap.city IS NOT NULL AND ap.state IS NOT NULL) AS cities_served,
          COUNT(DISTINCT s.destination_code) AS airports_served,
          COUNT(DISTINCT (s.origin_code, s.destination_code)) AS total_routes
        FROM segment s
        JOIN airport ap ON s.destination_code = ap.airport_code
        WHERE s.airline_code = $1
      ),
      price_stats AS (
        SELECT ROUND(AVG(f.total_fare), 2) AS avg_ticket_price
        FROM segment s
        JOIN itinerary i ON s.leg_id = i.leg_id
        JOIN fare_quote f ON i.leg_id = f.leg_id
        WHERE s.airline_code = $1 AND i.is_nonstop = TRUE
      )
      SELECT a.airline_code, a.airline_name,
             n.cities_served, n.airports_served, n.total_routes, p.avg_ticket_price
      FROM airline a, network_stats n, price_stats p
      WHERE a.airline_code = $1
    `, [code]);

    if (rows.length === 0) return res.status(404).json({ error: `Airline ${code} not found` });
    res.json(rows[0]);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Database error' });
  }
});

// ---------- Q5: an airline's busiest routes ----------
// GET /airlines/:airlineCode/top-routes?limit=5
router.get('/airlines/:airlineCode/top-routes', async (req, res) => {
  const code = req.params.airlineCode.toUpperCase();
  const limit = parseInt(req.query.limit, 10) || 5;
  try {
    const rows = await query(`
      SELECT origin_code, destination_code, COUNT(*) AS number_of_flights
      FROM flight_operation
      WHERE airline_code = $1
      GROUP BY origin_code, destination_code
      ORDER BY number_of_flights DESC
      LIMIT $2
    `, [code, limit]);
    res.json(rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Database error' });
  }
});

// ---------- Q8: an airport's busiest departing routes ----------
// GET /airports/:airportCode/top-routes?limit=5&year=2025
router.get('/airports/:airportCode/top-routes', async (req, res) => {
  const code = req.params.airportCode.toUpperCase();
  const limit = parseInt(req.query.limit, 10) || 5;
  const year = parseInt(req.query.year, 10) || 2025;
  try {
    const rows = await query(`
      SELECT origin_code, destination_code, COUNT(*) AS number_of_flights
      FROM flight_operation
      WHERE origin_code = $1
        AND flight_date >= make_date($3, 1, 1)
        AND flight_date <  make_date($3 + 1, 1, 1)
      GROUP BY origin_code, destination_code
      ORDER BY number_of_flights DESC
      LIMIT $2
    `, [code, limit, year]);
    res.json(rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Database error' });
  }
});

router.use(require('./airport-routes'));
router.use(require('./flight-routes'));
module.exports = router;
