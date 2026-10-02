/**
 * Activity Tracker — logs rep usage to localStorage + Firebase (cross-device)
 * Tracks: logins, page views, searches, calls, emails, appointments booked
 */
import { isFirebaseReady, syncActivity, syncActivityEvent } from './firebase.js';

// Actions that are meaningful enough to sync as itemized events (for the
// manager day-drilldown). Mirrors FEED_ACTIONS below.
const EVENT_SYNC_ACTIONS = new Set([
  'search', 'call', 'text', 'email', 'quote', 'contract',
  'appointment', 'store_view', 'prospect_view', 'renewal_view',
]);

const ACTIVITY_KEY = 'impro_activity';
const ACTIVITY_SYNC_KEY = 'impro_activity_sync';

export function getActivityLog() {
  try {
    return JSON.parse(localStorage.getItem(ACTIVITY_KEY) || '[]');
  } catch { return []; }
}

export function logActivity(action, details = {}) {
  try {
    const log = getActivityLog();
    const entry = {
      action,
      timestamp: new Date().toISOString(),
      date: new Date().toISOString().slice(0, 10),
      ...details
    };
    log.push(entry);
    // Keep last 500 entries per device
    if (log.length > 500) log.splice(0, log.length - 500);
    localStorage.setItem(ACTIVITY_KEY, JSON.stringify(log));
    updateDailySummary(entry);
    
    // Sync to Firebase if available
    if (isFirebaseReady() && details.rep) {
      const repId = details.repId || details.rep.toLowerCase().replace(/\s+/g, '_');
      syncActivity(details.rep, repId, action, details).catch(() => {});
      // Also sync the itemized event so managers can drill into a specific day.
      if (EVENT_SYNC_ACTIONS.has(action)) {
        syncActivityEvent(details.rep, repId, entry).catch(() => {});
      }
    }
  } catch {}
}

function updateDailySummary(entry) {
  try {
    const summaries = JSON.parse(localStorage.getItem(ACTIVITY_SYNC_KEY) || '{}');
    const date = entry.date;
    if (!summaries[date]) {
      summaries[date] = { logins: 0, searches: 0, calls: 0, emails: 0, texts: 0, quotes: 0, appointments: 0, pageViews: 0, storeViews: 0, prospectViews: 0, renewalViews: 0 };
    }
    const s = summaries[date];
    switch (entry.action) {
      case 'login': s.logins++; break;
      case 'search': s.searches++; break;
      case 'call': s.calls++; break;
      case 'email': s.emails++; break;
      case 'text': s.texts = (s.texts || 0) + 1; break;
      case 'quote': s.quotes = (s.quotes || 0) + 1; break;
      case 'appointment': s.appointments++; break;
      case 'page_view': s.pageViews++; break;
      case 'store_view': s.storeViews++; break;
      case 'prospect_view': s.prospectViews++; break;
      case 'renewal_view': s.renewalViews++; break;
    }
    // Keep last 30 days
    const keys = Object.keys(summaries).sort();
    if (keys.length > 30) {
      keys.slice(0, keys.length - 30).forEach(k => delete summaries[k]);
    }
    localStorage.setItem(ACTIVITY_SYNC_KEY, JSON.stringify(summaries));
  } catch {}
}

export function getDailySummaries() {
  try {
    return JSON.parse(localStorage.getItem(ACTIVITY_SYNC_KEY) || '{}');
  } catch { return {}; }
}

/**
 * Recent real activity feed for the Home screen — the actual things the rep
 * did in the app (searches, calls, store/prospect lookups, emails, texts,
 * quotes, contracts, appointments). Filters out low-signal noise (raw page
 * views, logins, manual status updates) and de-dupes rapid repeats.
 */
const FEED_ACTIONS = new Set([
  'search', 'call', 'text', 'email', 'quote', 'contract',
  'appointment', 'store_view', 'prospect_view', 'renewal_view',
]);

export function getRecentActivity(limit = 8) {
  const log = getActivityLog();
  const out = [];
  let lastKey = '';
  // Walk newest-first.
  for (let i = log.length - 1; i >= 0; i--) {
    const e = log[i];
    if (!e || !FEED_ACTIONS.has(e.action)) continue;
    const label = (e.store || e.business || e.subcategory || e.category || e.tab || '').toString();
    // Collapse immediate duplicate (same action+target logged twice in a row).
    const key = e.action + '|' + label.toLowerCase();
    if (key === lastKey) continue;
    lastKey = key;
    out.push(e);
    if (out.length >= limit) break;
  }
  return out;
}

export function getRepActivityReport() {
  const summaries = getDailySummaries();
  const dates = Object.keys(summaries).sort().reverse();
  const last7 = dates.slice(0, 7);
  const last30 = dates.slice(0, 30);
  
  const sum = (arr) => arr.reduce((acc, d) => {
    const s = summaries[d];
    Object.keys(s).forEach(k => acc[k] = (acc[k] || 0) + s[k]);
    return acc;
  }, {});

  return {
    today: summaries[new Date().toISOString().slice(0, 10)] || {},
    last7days: sum(last7),
    last30days: sum(last30),
    dailyBreakdown: last7.map(d => ({ date: d, ...summaries[d] }))
  };
}
