const express = require('express');
const { query } = require('./db');

const router = express.Router();

// ---------- Dropdown options ----------

// GET /airlines: all airlines (for dropdowns)
router.get('/airlines', async (req, res, next) => {
  try {
    const rows = await query(
      'SELECT airline_code, airline_name FROM airline ORDER BY airline_name'
    );
    res.json(rows);
  } catch (err) {
    next(err);
  }
});

// GET /airports: all airports (for dropdowns)
router.get('/airports', async (req, res, next) => {
  try {
    const rows = await query(
      'SELECT airport_code, city, state FROM airport ORDER BY airport_code'
    );
    res.json(rows);
  } catch (err) {
    next(err);
  }
});

router.use(require('./flight-routes'));
router.use(require('./airline-routes'));
router.use(require('./airport-routes'));

router.use((err, req, res, next) => {
  if (res.headersSent) return next(err);
  console.error('API query failed', err.code ?? err.name);
  res.status(500).json({ error: 'Database error' });
});

module.exports = router;
