const express = require('express');
const { loadSql, query } = require('./db');
const { OPERATIONS_YEAR, hasOnlyParams, parseLimit } = require('./request-params');

const router = express.Router();
const topRoutesSql = loadSql('q8-airport-top-routes.sql');

router.param('airportCode', (req, res, next, code) => {
  if (!/^[a-z]{3}$/i.test(code)) {
    return res.status(400).json({ error: 'airportCode must contain three letters' });
  }
  if (req.query.year !== undefined && req.query.year !== String(OPERATIONS_YEAR)) {
    return res.status(400).json({ error: 'Airport data is available only for 2025' });
  }
  req.params.airportCode = code.toUpperCase();
  next();
});

router.get('/airports/:airportCode/top-routes', async (req, res, next) => {
  if (!hasOnlyParams(req.query, ['year', 'limit'])) {
    return res.status(400).json({ error: 'Only year and limit are supported' });
  }
  const limit = parseLimit(req.query.limit);
  if (limit === null) return res.status(400).json({ error: 'limit must be a positive integer' });
  try {
    res.json(await query(topRoutesSql, [req.params.airportCode, limit, OPERATIONS_YEAR]));
  } catch (err) {
    next(err);
  }
});

const routes = [
  ['overview', 'q7-airport-overview.sql'],
  ['efficiency', 'q9-airport-efficiency.sql'],
  ['weather-reliability', 'q10-airport-weather.sql'],
];

for (const [endpoint, file] of routes) {
  const sql = loadSql(file);
  router.get(`/airports/:airportCode/${endpoint}`, async (req, res, next) => {
    if (!hasOnlyParams(req.query, ['year'])) {
      return res.status(400).json({ error: 'Only the year query parameter is supported' });
    }
    const code = req.params.airportCode;
    try {
      const rows = await query(sql, [code, OPERATIONS_YEAR]);
      if (!rows.length) return res.status(404).json({ error: `Airport ${code} not found` });
      res.json(endpoint === 'weather-reliability' ? rows : rows[0]);
    } catch (err) {
      next(err);
    }
  });
}

module.exports = router;
