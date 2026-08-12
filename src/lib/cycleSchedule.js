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

// ── Launch (in-store) date + sell-by deadline ────────────────────────────
//
// A store's ad rotation "launches" (goes in-store) on the zone install day of
// each cycle-start month. Reps must have the ad SOLD by a deadline ahead of
// that launch — the print/production buffer.
//
// Tyler's reference (Zone 7): C3 launches in-store Sept 7, last ad must be
// sold by Aug 15 → a 23-day lead time before the in-store date. We apply the
// same lead-time buffer across all stores; because each zone has a different
// install day (and each cycle a different month), the actual launch and
// sell-by dates differ per store, but the buffer is consistent.

export const DEFAULT_SELL_BY_LEAD_DAYS = 23;

/**
 * The full list of launch (in-store) dates for a store's cycle across a year
 * window, given the zone install day-of-month.
 * @param {string} cycle  A/B/C
 * @param {number} installDay  day-of-month the zone goes in-store (1-31)
 * @param {Date} refDate
 * @returns {Date[]} sorted launch dates (prev year..next year)
 */
export function cycleLaunchDates(cycle, installDay, refDate = new Date()) {
  const starts = cycleStartMonthIndexes(cycle);
  if (!starts.length) return [];
  const day = parseInt(installDay, 10) || 1;
  const ref = refDate instanceof Date ? refDate : new Date(refDate);
  const year = ref.getFullYear();
  const dates = [];
  for (const y of [year - 1, year, year + 1]) {
    for (const mi of starts) dates.push(new Date(y, mi, day));
  }
  return dates.sort((a, b) => a - b);
}

/**
 * The current/next launch (in-store) date for a store and the matching
 * sell-by deadline (launch minus lead days).
 * @returns {{ launch: Date, sellBy: Date, nextLaunch: Date, nextSellBy: Date,
 *            daysUntilSellBy: number, sellByPassed: boolean }|null}
 */
export function launchAndSellBy(cycle, installDay, {
  refDate = new Date(),
  leadDays = DEFAULT_SELL_BY_LEAD_DAYS,
} = {}) {
  const c = normalizeCycle(cycle);
  if (c == null || !installDay) return null;
  const ref = refDate instanceof Date ? refDate : new Date(refDate);
  const dates = cycleLaunchDates(c, installDay, ref);
  if (!dates.length) return null;

  const MS = 24 * 60 * 60 * 1000;
  const sellByOf = (d) => new Date(d.getTime() - leadDays * MS);

  // "Current" launch = the next launch whose SELL-BY has not yet fully passed
  // is what a rep cares about, but we report the next upcoming launch and the
  // one after it.
  let launch = null;
  let nextLaunch = null;
  for (const d of dates) {
    if (d >= ref) {
      if (!launch) launch = d;
      else if (!nextLaunch) { nextLaunch = d; break; }
    }
  }
  if (!launch) { launch = dates[dates.length - 1]; }
  if (!nextLaunch) {
    // find first date strictly after launch
    nextLaunch = dates.find((d) => d > launch) || launch;
  }

  const sellBy = sellByOf(launch);
  const nextSellBy = sellByOf(nextLaunch);
  const daysUntilSellBy = Math.round((sellBy - ref) / MS);

  return {
    cycle: c,
    installDay: parseInt(installDay, 10) || 1,
    leadDays,
    launch,
    sellBy,
    nextLaunch,
    nextSellBy,
    daysUntilSellBy,
    sellByPassed: daysUntilSellBy < 0,
  };
}

/**
 * Human-readable sell-by summary for a store.
 * e.g. "Next launch: Sep 7, 2026 — sell by Aug 15, 2026 (23-day buffer)".
 */
export function sellBySummary(cycle, installDay, opts = {}) {
  const info = launchAndSellBy(cycle, installDay, opts);
  if (!info) return null;
  const fmt = (d) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  let effLaunch = info.launch;
  let effSellBy = info.sellBy;
  // If this launch's sell-by already passed, roll to the next window.
  if (info.sellByPassed) { effLaunch = info.nextLaunch; effSellBy = info.nextSellBy; }
  const days = Math.round((effSellBy - (opts.refDate || new Date())) / (24 * 60 * 60 * 1000));
  return {
    ...info,
    effLaunch,
    effSellBy,
    daysUntilSellBy: days,
    label: `Next launch ${fmt(effLaunch)} — sell by ${fmt(effSellBy)} (${info.leadDays}-day buffer)`,
  };
}

export { MONTH_NAMES };
