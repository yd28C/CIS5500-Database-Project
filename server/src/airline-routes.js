const express = require('express');
const { loadSql, query } = require('./db');
const { hasOnlyParams, parseLimit } = require('./request-params');

const router = express.Router();
const summarySql = loadSql('q4-airline-summary.sql');
const topRoutesSql = loadSql('q5-airline-top-routes.sql');
const reliabilitySql = loadSql('q6-airline-reliability.sql');

for (const [path, sql] of [['summary', summarySql], ['reliability', reliabilitySql]]) {
  router.get(`/airlines/:airlineCode/${path}`, async (req, res, next) => {
    if (!hasOnlyParams(req.query, [])) return res.status(400).json({ error: 'No query parameters are supported' });
    const code = req.params.airlineCode.toUpperCase();
    try {
      const [row] = await query(sql, [code]);
      if (!row) return res.status(404).json({ error: `Airline ${code} not found` });
      res.json(row);
    } catch (err) {
      next(err);
    }
  });
}

router.get('/airlines/:airlineCode/top-routes', async (req, res, next) => {
  if (!hasOnlyParams(req.query, ['limit'])) return res.status(400).json({ error: 'Only limit is supported' });
  const limit = parseLimit(req.query.limit);
  if (limit === null) return res.status(400).json({ error: 'limit must be a positive integer' });
  try {
    res.json(await query(topRoutesSql, [req.params.airlineCode.toUpperCase(), limit]));
  } catch (err) {
    next(err);
  }
});

module.exports = router;
