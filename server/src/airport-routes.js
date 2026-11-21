const express = require('express');
const fs = require('node:fs');
const path = require('node:path');
const { query } = require('./db');

const router = express.Router();
const routes = [
  ['overview', 'q7-airport-overview.sql'],
  ['efficiency', 'q9-airport-efficiency.sql'],
  ['weather-reliability', 'q10-airport-weather.sql'],
];

for (const [endpoint, file] of routes) {
  const sql = fs.readFileSync(path.join(__dirname, '../sql', file), 'utf8');

  router.get(`/airports/:airportCode/${endpoint}`, async (req, res) => {
    const { airportCode } = req.params;
    if (!/^[a-z]{3}$/i.test(airportCode)) {
      return res.status(400).json({ error: 'airportCode must contain three letters' });
    }
    if (Object.keys(req.query).some(key => key !== 'year')) {
      return res.status(400).json({ error: 'Only the year query parameter is supported' });
    }
    const year = req.query.year ?? '2025';
    if (typeof year !== 'string' || !/^\d{4}$/.test(year) || Number(year) < 1900 || Number(year) > 2100) {
      return res.status(400).json({ error: 'year must be one integer between 1900 and 2100' });
    }

    const code = airportCode.toUpperCase();
    try {
      const rows = await query(sql, [code, Number(year)]);
      if (!rows.length) return res.status(404).json({ error: `Airport ${code} not found` });
      res.json(endpoint === 'weather-reliability' ? rows : rows[0]);
    } catch (err) {
      console.error('Airport query failed', file, err.code ?? err.name);
      res.status(500).json({ error: 'Database error' });
    }
  });
}

module.exports = router;
