/**
 * Firebase config for imPro PWA
 * Uses Firestore for cross-device activity sync
 */
import { initializeApp } from 'firebase/app';
import { getFirestore, collection, doc, setDoc, getDocs, query, where, orderBy, limit, Timestamp } from 'firebase/firestore';

// Firebase config — set via localStorage or hardcoded after setup
const DEFAULT_CONFIG = {
  apiKey: "AIzaSyC-VpUxByGfphYwTNnO5U31MmKDTEKC6eM",
  authDomain: "impro-sales.firebaseapp.com",
  projectId: "impro-sales",
  storageBucket: "impro-sales.firebasestorage.app",
  messagingSenderId: "99160080398",
  appId: "1:99160080398:web:52bd73ccc67e07facabc5f"
};

let firebaseApp = null;
let db = null;

function getConfig() {
  try {
    const saved = localStorage.getItem('impro_firebase_config');
    if (saved) return JSON.parse(saved);
  } catch {}
  return DEFAULT_CONFIG;
}

export function initFirebase(config = null) {
  try {
    const cfg = config || getConfig();
    if (!cfg.projectId) return false;
    firebaseApp = initializeApp(cfg);
    db = getFirestore(firebaseApp);
    return true;
  } catch (e) {
    console.warn('Firebase init failed:', e);
    return false;
  }
}

// Upload a file (video/image picked from the phone gallery) to Firebase
// Storage and return a public download URL for embedding in an email.
// onProgress(0..1) is called as bytes upload. Returns null on failure.
export async function uploadEmailAttachment(file, onProgress) {
  if (!firebaseApp) return null;
  try {
    const { getStorage, ref, uploadBytesResumable, getDownloadURL } = await import('firebase/storage');
    const storage = getStorage(firebaseApp);
    const safeName = (file.name || 'attachment').replace(/[^a-zA-Z0-9._-]/g, '_');
    const path = `email_attachments/${Date.now()}_${Math.random().toString(36).slice(2, 8)}_${safeName}`;
    const storageRef = ref(storage, path);
    const task = uploadBytesResumable(storageRef, file, { contentType: file.type || 'application/octet-stream' });
    return await new Promise((resolve) => {
      task.on('state_changed',
        (snap) => { if (onProgress && snap.totalBytes) onProgress(snap.bytesTransferred / snap.totalBytes); },
        (err) => { console.warn('uploadEmailAttachment error:', err); resolve(null); },
        async () => {
          try { resolve(await getDownloadURL(task.snapshot.ref)); }
          catch (e) { console.warn('getDownloadURL error:', e); resolve(null); }
        }
      );
    });
  } catch (e) {
    console.warn('uploadEmailAttachment error:', e);
    return null;
  }
}

export function isFirebaseReady() {
  return db !== null;
}

/**
 * Resolve once Firebase is initialized (or after timeout).
 * Lets claim/dibs loaders wait instead of silently bailing on cold start.
 */
export function whenFirebaseReady(timeoutMs = 8000) {
  if (db !== null) return Promise.resolve(true);
  // Make sure an init attempt is in flight.
  initFirebase();
  return new Promise((resolve) => {
    const start = Date.now();
    const tick = () => {
      if (db !== null) return resolve(true);
      if (Date.now() - start >= timeoutMs) return resolve(false);
      setTimeout(tick, 150);
    };
    tick();
  });
}

// Eagerly initialize on module load so dibs/claims are ready before
// any component mounts (prevents claims being lost on cold start/refresh).
try { initFirebase(); } catch {}

/**
 * Log activity to Firestore
 */
export async function syncActivity(repName, repId, action, details = {}) {
  if (!db) return false;
  try {
    const today = new Date().toISOString().slice(0, 10);
    const docId = `${repId}_${today}`;
    const docRef = doc(db, 'activity_daily', docId);
    
    // Get or create daily summary
    const { getDoc } = await import('firebase/firestore');
    const existing = await getDoc(docRef);
    const data = existing.exists() ? existing.data() : {
      repName,
      repId,
      date: today,
      logins: 0,
      pageViews: 0,
      searches: 0,
      calls: 0,
      emails: 0,
      appointments: 0,
      storeViews: 0,
      prospectViews: 0,
      renewalViews: 0,
      lastActive: ''
    };
    
    // Increment counter
    switch (action) {
      case 'login': data.logins++; break;
      case 'page_view': data.pageViews++; break;
      case 'search': data.searches++; break;
      case 'call': data.calls++; break;
      case 'email': data.emails++; break;
      case 'appointment': data.appointments++; break;
      case 'store_view': data.storeViews++; break;
      case 'prospect_view': data.prospectViews++; break;
      case 'renewal_view': data.renewalViews++; break;
    }
    data.lastActive = new Date().toISOString();
    data.repName = repName;
    data.repId = repId;
    data.date = today;
    
    await setDoc(docRef, data);
    return true;
  } catch (e) {
    console.warn('Firebase sync error:', e);
    return false;
  }
}

/**
 * Get all reps' activity (for manager view)
 */
export async function getAllRepActivity(days = 7) {
  if (!db) return [];
  try {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    const cutoffStr = cutoff.toISOString().slice(0, 10);
    
    const q = query(
      collection(db, 'activity_daily'),
      where('date', '>=', cutoffStr),
      orderBy('date', 'desc')
    );
    
    const snapshot = await getDocs(q);
    return snapshot.docs.map(d => d.data());
  } catch (e) {
    console.warn('Firebase read error:', e);
    return [];
  }
}

/**
 * Get activity for a specific rep
 */
export async function getRepActivity(repId, days = 30) {
  if (!db) return [];
  try {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    const cutoffStr = cutoff.toISOString().slice(0, 10);
    
    const q = query(
      collection(db, 'activity_daily'),
      where('repId', '==', repId),
      where('date', '>=', cutoffStr),
      orderBy('date', 'desc')
    );
    
    const snapshot = await getDocs(q);
    return snapshot.docs.map(d => d.data());
  } catch (e) {
    console.warn('Firebase rep read error:', e);
    return [];
  }
}

export function saveFirebaseConfig(config) {
  localStorage.setItem('impro_firebase_config', JSON.stringify(config));
}

// ── Lead Claims ("Dibs on Prospects") ──────────────────────────────

function hashLeadId(name, address) {
  const raw = ((name || '') + '_' + (address || '')).toLowerCase().replace(/[^a-z0-9]/g, '');
  // Simple string hash
  let h = 0;
  for (let i = 0; i < raw.length; i++) {
    h = ((h << 5) - h + raw.charCodeAt(i)) | 0;
  }
  return Math.abs(h).toString(36);
}

export { hashLeadId };

/**
 * Claim a lead for a rep. Resets 30-day timer on each action.
 */
export async function claimLead(repName, repId, prospectName, prospectAddr, action) {
  if (!db) return false;
  try {
    const id = hashLeadId(prospectName, prospectAddr);
    const now = new Date();
    const expiresAt = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000);
    await setDoc(doc(db, 'activity_daily', `dibs_lead_${id}`), {
      type: 'lead_claim',
      repName,
      repId,
      prospectName: prospectName || '',
      prospectAddress: prospectAddr || '',
      claimedAt: now.toISOString(),
      expiresAt: expiresAt.toISOString(),
      lastAction: action || '',
      lastActionAt: now.toISOString(),
    });
    return true;
  } catch (e) {
    console.warn('claimLead error:', e);
    return false;
  }
}

/**
 * Release a lead claim.
 */
export async function releaseLead(prospectName, prospectAddr) {
  if (!db) return false;
  try {
    const id = hashLeadId(prospectName, prospectAddr);
    const { deleteDoc } = await import('firebase/firestore');
    await deleteDoc(doc(db, 'activity_daily', `dibs_lead_${id}`));
    return true;
  } catch (e) {
    console.warn('releaseLead error:', e);
    return false;
  }
}

/**
 * Get all active lead claims. Expired ones are cleaned up.
 */
export async function getAllLeadClaims() {
  if (!db) return [];
  try {
    const { deleteDoc } = await import('firebase/firestore');
    const now = new Date();
    const q = query(collection(db, 'activity_daily'), where('type', '==', 'lead_claim'));
    const snapshot = await getDocs(q);
    const active = [];
    const deletePromises = [];
    snapshot.docs.forEach(d => {
      const data = d.data();
      if (new Date(data.expiresAt) < now) {
        deletePromises.push(deleteDoc(d.ref));
      } else {
        active.push({ ...data, _docId: d.id });
      }
    });
    if (deletePromises.length) Promise.all(deletePromises).catch(() => {});
    return active;
  } catch (e) {
    console.warn('getAllLeadClaims error:', e);
    return [];
  }
}

// ── Persistent Lead Data (Owner, Contact, Notes) ──────────────────

/**
 * Save lead data (owner, contact phone, notes) to Firebase.
 */
export async function saveLeadData(prospectName, prospectAddr, data) {
  if (!db) return false;
  try {
    const id = hashLeadId(prospectName, prospectAddr);
    await setDoc(doc(db, 'activity_daily', `lead_data_${id}`), {
      type: 'lead_data',
      prospectName: prospectName || '',
      prospectAddress: prospectAddr || '',
      ownerName: data.ownerName || '',
      contactPhone: data.contactPhone || '',
      notes: data.notes || '',
      updatedBy: data.updatedBy || '',
      updatedAt: new Date().toISOString(),
    });
    return true;
  } catch (e) {
    console.warn('saveLeadData error:', e);
    return false;
  }
}

/**
 * Get lead data for a prospect.
 */
export async function getLeadData(prospectName, prospectAddr) {
  if (!db) return null;
  try {
    const id = hashLeadId(prospectName, prospectAddr);
    const { getDoc } = await import('firebase/firestore');
    const snap = await getDoc(doc(db, 'activity_daily', `lead_data_${id}`));
    return snap.exists() ? snap.data() : null;
  } catch (e) {
    console.warn('getLeadData error:', e);
    return null;
  }
}

/**
 * Get ALL lead data docs (for pre-loading).
 */
export async function getAllLeadData() {
  if (!db) return [];
  try {
    const q = query(collection(db, 'activity_daily'), where('type', '==', 'lead_data'));
    const snapshot = await getDocs(q);
    return snapshot.docs.map(d => d.data());
  } catch (e) {
    console.warn('getAllLeadData error:', e);
    return [];
  }
}

// ── Per-prospect contact activity log ────────────────────────────────
// A running log of who contacted a prospect, how (call/text/email/walk-in/
// note/status), and when. Stored one doc per prospect keyed by lead hash,
// with the events appended to an `entries` array (capped at 50).
export async function appendLeadActivity(prospectName, prospectAddr, entry) {
  if (!db) return false;
  try {
    const id = hashLeadId(prospectName, prospectAddr);
    const ref = doc(db, 'activity_daily', `lead_activity_${id}`);
    const { getDoc } = await import('firebase/firestore');
    const snap = await getDoc(ref);
    const existing = (snap.exists() && Array.isArray(snap.data().entries)) ? snap.data().entries : [];
    const clean = {
      action: entry.action || 'contact',
      rep: entry.rep || '',
      repId: entry.repId != null ? String(entry.repId) : '',
      detail: entry.detail || '',
      at: entry.at || new Date().toISOString(),
    };
    const entries = [...existing, clean];
    // Keep last 50 events per prospect
    if (entries.length > 50) entries.splice(0, entries.length - 50);
    await setDoc(ref, {
      type: 'lead_activity',
      prospectName: prospectName || '',
      prospectAddress: prospectAddr || '',
      entries,
      lastAction: clean.action,
      lastRep: clean.rep,
      lastAt: clean.at,
      updatedAt: new Date().toISOString(),
    });
    return true;
  } catch (e) {
    console.warn('appendLeadActivity error:', e);
    return false;
  }
}

// Get ALL lead-activity docs (for pre-loading into a cache).
export async function getAllLeadActivity() {
  if (!db) return [];
  try {
    const q = query(collection(db, 'activity_daily'), where('type', '==', 'lead_activity'));
    const snapshot = await getDocs(q);
    return snapshot.docs.map(d => d.data());
  } catch (e) {
    console.warn('getAllLeadActivity error:', e);
    return [];
  }
}

// ── Call-In Lead Assignments (manager assigns inbound leads to reps) ──
// A call-in lead is hidden from reps until Tyler/Rick assigns it to a rep.
// Stored one doc per lead, keyed by a stable lead key (crm_id or hash).

export function callInLeadKey(lead) {
  const raw = (lead.crm_id || ((lead.business_name || lead.name || '') + '_' + (lead.lead_zip || lead.zip || ''))) + '';
  return raw.toLowerCase().replace(/[^a-z0-9]/g, '') || 'lead';
}

/**
 * Assign (or reassign) a call-in lead to a rep. Pass repId='' to unassign.
 */
export async function assignCallInLead(leadKey, repId, repName, assignedBy) {
  if (!db || !leadKey) return false;
  try {
    await setDoc(doc(db, 'activity_daily', `callin_assign_${leadKey}`), {
      type: 'callin_assignment',
      leadKey: String(leadKey),
      repId: repId ? String(repId) : '',
      repName: repName || '',
      assignedBy: assignedBy || '',
      assignedAt: new Date().toISOString(),
    });
    return true;
  } catch (e) {
    console.warn('assignCallInLead error:', e);
    return false;
  }
}

/**
 * Get all call-in lead assignments as a map: leadKey -> assignment.
 */
export async function getAllCallInAssignments() {
  if (!db) return {};
  try {
    const q = query(collection(db, 'activity_daily'), where('type', '==', 'callin_assignment'));
    const snapshot = await getDocs(q);
    const map = {};
    snapshot.docs.forEach(d => { const v = d.data(); map[v.leadKey] = v; });
    return map;
  } catch (e) {
    console.warn('getAllCallInAssignments error:', e);
    return {};
  }
}

// ── Saved Prospects (cross-device per rep) ─────────────────────────

/**
 * Save a rep's full saved-prospects array to Firestore (doc id = repId).
 * One doc per rep so the list is identical across all their devices.
 */
export async function saveRepProspects(repId, prospects) {
  if (!db || !repId) return false;
  try {
    // Stored inside the proven 'activity_daily' collection (same one used by
    // store claims / lead data) to inherit its working write permissions.
    await setDoc(doc(db, 'activity_daily', `rep_prospects_${repId}`), {
      type: 'rep_prospects',
      repId: String(repId),
      prospects: Array.isArray(prospects) ? prospects : [],
      updatedAt: new Date().toISOString(),
    });
    return true;
  } catch (e) {
    console.warn('saveRepProspects error:', e);
    return false;
  }
}

/**
 * Get a rep's saved-prospects array from Firestore. Returns [] if none.
 */
export async function getRepProspects(repId) {
  if (!db || !repId) return [];
  try {
    const { getDoc } = await import('firebase/firestore');
    const snap = await getDoc(doc(db, 'activity_daily', `rep_prospects_${repId}`));
    if (!snap.exists()) return [];
    const data = snap.data();
    return Array.isArray(data.prospects) ? data.prospects : [];
  } catch (e) {
    console.warn('getRepProspects error:', e);
    return [];
  }
}

// ── Store Claims ("Dibs") ──────────────────────────────────────────

/**
 * Calculate next Saturday 23:59:59 local time.
 * If today IS Saturday, expires end of today.
 */
function getNextSaturdayEnd() {
  const now = new Date();
  const day = now.getDay(); // 0=Sun … 6=Sat
  const daysUntilSat = day === 6 ? 0 : (6 - day);
  const sat = new Date(now);
  sat.setDate(sat.getDate() + daysUntilSat);
  sat.setHours(23, 59, 59, 999);
  return sat;
}

/**
 * Claim a store for a rep. One claim per store (doc id = storeName).
 */
export async function claimStore(repName, repId, storeName, zone) {
  if (!db) return false;
  try {
    const now = new Date();
    const expiresAt = getNextSaturdayEnd();
    // Use activity_daily collection (already has write permissions) with a dibs_ prefix
    await setDoc(doc(db, 'activity_daily', `dibs_${storeName}`), {
      type: 'store_claim',
      repName,
      repId,
      storeName,
      zone: zone || '',
      claimedAt: now.toISOString(),
      expiresAt: expiresAt.toISOString(),
    });
    return true;
  } catch (e) {
    console.warn('claimStore error:', e);
    return false;
  }
}

/**
 * Release a store claim.
 */
export async function releaseStore(storeName) {
  if (!db) return false;
  try {
    const { deleteDoc } = await import('firebase/firestore');
    await deleteDoc(doc(db, 'activity_daily', `dibs_${storeName}`));
    return true;
  } catch (e) {
    console.warn('releaseStore error:', e);
    return false;
  }
}

/**
 * Get all active (non-expired) claims, optionally filtered by zone.
 * Expired claims are deleted on read.
 */
export async function getZoneClaims(zone) {
  if (!db) return [];
  try {
    const { deleteDoc } = await import('firebase/firestore');
    const now = new Date();
    // Query all dibs docs from activity_daily (type == 'store_claim')
    const q = query(collection(db, 'activity_daily'), where('type', '==', 'store_claim'));
    const snapshot = await getDocs(q);
    const active = [];
    const deletePromises = [];
    snapshot.docs.forEach(d => {
      const data = d.data();
      if (new Date(data.expiresAt) < now) {
        // Expired — clean up
        deletePromises.push(deleteDoc(d.ref));
      } else if (!zone || data.zone === zone || zone === '') {
        active.push(data);
      }
    });
    // Fire-and-forget cleanup
    if (deletePromises.length) Promise.all(deletePromises).catch(() => {});
    return active;
  } catch (e) {
    console.warn('getZoneClaims error:', e);
    return [];
  }
}
