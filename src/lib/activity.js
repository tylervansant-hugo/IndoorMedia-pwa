/**
 * Activity Tracker — logs rep usage to localStorage + Firebase (cross-device)
 * Tracks: logins, page views, searches, calls, emails, appointments booked
 */
import { isFirebaseReady, syncActivity } from './firebase.js';

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
    }
  } catch {}
}

function updateDailySummary(entry) {
  try {
    const summaries = JSON.parse(localStorage.getItem(ACTIVITY_SYNC_KEY) || '{}');
    const date = entry.date;
    if (!summaries[date]) {
      summaries[date] = { logins: 0, searches: 0, calls: 0, emails: 0, appointments: 0, pageViews: 0, storeViews: 0, prospectViews: 0, renewalViews: 0 };
    }
    const s = summaries[date];
    switch (entry.action) {
      case 'login': s.logins++; break;
      case 'search': s.searches++; break;
      case 'call': s.calls++; break;
      case 'email': s.emails++; break;
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
