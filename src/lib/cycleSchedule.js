// Cycle → start-month schedule helper
// -----------------------------------
// A store's Cycle letter (A/B/C) determines which month of each quarter its
// ad rotation cycle starts. It rotates every 3 months. (Tyler, Aug 2026)
//
//   A1=January  B1=February  C1=March
//   A2=April    B2=May       C2=June
//   A3=July     B3=August    C3=September
//   A4=October  B4=November  C4=December
//
// i.e. A = 1st month of each quarter, B = 2nd, C = 3rd.
//   A → Jan, Apr, Jul, Oct
//   B → Feb, May, Aug, Nov
//   C → Mar, Jun, Sep, Dec

// 0-based cycle offset within a quarter.
const CYCLE_OFFSET = { A: 0, B: 1, C: 2 };

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

/**
 * Normalize a Cycle value to a single upper-case letter A/B/C.
 * Accepts 'a', 'B', 'C1', 'Cycle A', etc.
 */
export function normalizeCycle(cycle) {
  if (!cycle) return null;
  const m = String(cycle).toUpperCase().match(/[ABC]/);
  return m ? m[0] : null;
}

/**
 * All start months (0-based month indexes) for a given cycle letter.
 * A → [0,3,6,9], B → [1,4,7,10], C → [2,5,8,11]
 */
export function cycleStartMonthIndexes(cycle) {
  const c = normalizeCycle(cycle);
  if (c == null) return [];
  const off = CYCLE_OFFSET[c];
  return [0, 1, 2, 3].map((q) => q * 3 + off);
}

/** Human-readable start months, e.g. "Jan, Apr, Jul, Oct". */
export function cycleStartMonths(cycle, { long = false } = {}) {
  return cycleStartMonthIndexes(cycle).map((i) =>
    long ? MONTH_NAMES[i] : MONTH_NAMES[i].slice(0, 3)
  );
}

/**
 * The label for a specific cycle+quarter, e.g. ('B', 3) → "August".
 * quarter is 1-4.
 */
export function cycleQuarterMonth(cycle, quarter, { long = true } = {}) {
  const c = normalizeCycle(cycle);
  if (c == null || quarter < 1 || quarter > 4) return null;
  const idx = (quarter - 1) * 3 + CYCLE_OFFSET[c];
  return long ? MONTH_NAMES[idx] : MONTH_NAMES[idx].slice(0, 3);
}

/**
 * Given a cycle letter and a reference date, return the current cycle
 * period start (the most recent cycle-start on/before the date) and the
 * next cycle start (3 months later). Dates default to the store's cycle
 * start day-of-month = 1 unless you pass a startDay.
 */
export function cyclePeriod(cycle, refDate = new Date(), startDay = 1) {
  const starts = cycleStartMonthIndexes(cycle);
  if (!starts.length) return null;
  const ref = refDate instanceof Date ? refDate : new Date(refDate);
  const year = ref.getFullYear();

  // Build all start dates across previous, current, and next year for safety.
  const candidates = [];
  for (const y of [year - 1, year, year + 1]) {
    for (const mi of starts) {
      candidates.push(new Date(y, mi, startDay));
    }
  }
  candidates.sort((a, b) => a - b);

  let current = null;
  let next = null;
  for (const d of candidates) {
    if (d <= ref) current = d;
    else { next = d; break; }
  }
  return { current, next };
}

/**
 * Convenience: short summary string for a store's cycle, e.g.
 * "Cycle B — starts Feb, May, Aug, Nov (currently Aug 2026, next Nov 2026)".
 */
export function cycleSummary(cycle, refDate = new Date()) {
  const c = normalizeCycle(cycle);
  if (c == null) return null;
  const months = cycleStartMonths(c).join(', ');
  const period = cyclePeriod(c, refDate);
  const fmt = (d) =>
    d ? d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) : '—';
  return {
    cycle: c,
    startMonths: months,
    currentStart: period?.current || null,
    nextStart: period?.next || null,
    label: `Cycle ${c} — starts ${months}` +
      (period ? ` (current ${fmt(period.current)}, next ${fmt(period.next)})` : ''),
  };
}

export { MONTH_NAMES };
