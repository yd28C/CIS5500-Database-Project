const express = require('express');
const { loadSql, query } = require('./db');
const { OPERATIONS_YEAR, hasOnlyParams } = require('./request-params');

const router = express.Router();
const searchSql = loadSql('q1-search-flights.sql');
const routeReliabilitySql = loadSql('q2-route-reliability.sql');
const trendsSql = loadSql('q3-booking-trends.sql');

// 2025 flight operations with same-route, carrier and month 2022 fare statistics.
router.get('/flights/search', async (req, res, next) => {
  const allowed = ['origin', 'destination', 'date', 'departureStart', 'departureEnd', 'ticketType'];
  if (!hasOnlyParams(req.query, allowed) ||
      Object.values(req.query).some(value => typeof value !== 'string' || value.trim() === '')) {
    return res.status(400).json({ error: 'Invalid or repeated query parameter' });
  }
  const { origin, destination, date } = req.query;
  if (!origin || !destination || !/^[a-z]{3}$/i.test(origin) || !/^[a-z]{3}$/i.test(destination)) {
    return res.status(400).json({ error: 'origin and destination must be three-letter airport codes' });
  }
  const parsedDate = typeof date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(date) ? new Date(`${date}T00:00:00Z`) : null;
  if (!parsedDate || Number.isNaN(parsedDate.getTime()) || parsedDate.toISOString().slice(0, 10) !== date || date.startsWith('0000')) {
    return res.status(400).json({ error: 'date must be a valid date in YYYY-MM-DD format' });
  }
  if (parsedDate.getUTCFullYear() !== OPERATIONS_YEAR) {
    return res.status(400).json({ error: 'Flight operations are available for 2025' });
  }
  const { departureStart, departureEnd, ticketType = 'any' } = req.query;
  const validTime = value => value === undefined || /^([01]\d|2[0-3]):[0-5]\d$/.test(value);
  if (!validTime(departureStart) || !validTime(departureEnd) ||
      (departureStart && departureEnd && departureStart >= departureEnd)) {
    return res.status(400).json({ error: 'Departure times must use local HH:MM, with start before end' });
  }
  if (!['any', 'basic', 'refundable'].includes(ticketType)) {
    return res.status(400).json({ error: 'ticketType must be any, basic, or refundable' });
  }
  try {
    const rows = await query(searchSql, [origin.toUpperCase(), destination.toUpperCase(), date,
      departureStart ? Number(departureStart.replace(':', '')) : null,
      departureEnd ? Number(departureEnd.replace(':', '')) : null, ticketType]);
    res.json(rows);
  } catch (err) {
    next(err);
  }
});

router.get('/routes/reliability', async (req, res, next) => {
  const { origin, destination } = req.query;
  const validAirport = code => typeof code === 'string' && /^[a-z]{3}$/i.test(code);
  if (!hasOnlyParams(req.query, ['origin', 'destination']) || !validAirport(origin) || !validAirport(destination)) {
    return res.status(400).json({ error: 'Provide origin and destination as three-letter airport codes' });
  }
  try {
    res.json(await query(routeReliabilitySql, [origin.toUpperCase(), destination.toUpperCase()]));
  } catch (err) {
    next(err);
  }
});

// Average fares by days between the search date and departure.
router.get('/flights/booking-trends', async (req, res, next) => {
  if (Object.keys(req.query).length) {
    return res.status(400).json({ error: 'No query parameters are supported' });
  }
  try {
    res.json(await query(trendsSql));
  } catch (err) {
    next(err);
  }
});

module.exports = router;
