// Shared PostgreSQL connection. Credentials come from server/.env (not committed).
require('dotenv').config({ quiet: true });
const { Pool, types } = require('pg');
const { readFileSync } = require('node:fs');

// Postgres sends COUNT(*) and NUMERIC as strings; convert them to JS numbers.
types.setTypeParser(20, Number);   // bigint (COUNT)
types.setTypeParser(1700, Number); // numeric (ROUND, AVG)

const pool = new Pool({
  host: process.env.DB_HOST,
  port: process.env.DB_PORT || 5432,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME || 'postgres',
  ssl: process.env.DB_SSL === 'false' ? false : {
    rejectUnauthorized: Boolean(process.env.DB_SSL_CA_FILE),
    ...(process.env.DB_SSL_CA_FILE && { ca: readFileSync(process.env.DB_SSL_CA_FILE, 'utf8') }),
  },
});

// Run a query with $1, $2, ... placeholders and return the rows.
async function query(text, params = []) {
  const result = await pool.query(text, params);
  return result.rows;
}

module.exports = { query };
