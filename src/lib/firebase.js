/**
 * Firebase config for imPro PWA
 * Uses Firestore for cross-device activity sync
 */
import { initializeApp } from 'firebase/app';
import { getFirestore, collection, doc, setDoc, getDocs, query, where, orderBy, limit, Timestamp } from 'firebase/firestore';

// Firebase config — set via localStorage or hardcoded after setup
const DEFAULT_CONFIG = {
  apiKey: "",
  authDomain: "",
  projectId: "",
  storageBucket: "",
  messagingSenderId: "",
  appId: ""
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

export function isFirebaseReady() {
  return db !== null;
}

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
