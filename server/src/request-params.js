const OPERATIONS_YEAR = 2025;

function hasOnlyParams(params, allowed) {
  return Object.keys(params).every(key => allowed.includes(key));
}

function parseLimit(value) {
  if (value === undefined) return 5;
  if (typeof value !== 'string' || !/^\d+$/.test(value)) return null;
  const limit = Number(value);
  return Number.isSafeInteger(limit) && limit > 0 ? limit : null;
}

module.exports = { OPERATIONS_YEAR, hasOnlyParams, parseLimit };
