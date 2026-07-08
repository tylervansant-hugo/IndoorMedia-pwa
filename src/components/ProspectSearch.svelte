<script>
  import { onMount, onDestroy, tick } from 'svelte';
  import { user, currentUser, sharedNearbyStores, sharedSelectedStore, sharedUserLocation } from '../lib/stores.js';
  import { logActivity } from '../lib/activity.js';
  import { isFirebaseReady, whenFirebaseReady, claimStore, releaseStore, getZoneClaims, claimLead, releaseLead, getAllLeadClaims, saveLeadData, getLeadData, getAllLeadData, hashLeadId, saveRepProspects, getRepProspects, callInLeadKey, assignCallInLead, getAllCallInAssignments, appendLeadActivity, getAllLeadActivity } from '../lib/firebase.js';
  import HotLeadsSubmit from './HotLeadsSubmit.svelte';
  import PendingLeads from './PendingLeads.svelte';
  import MeetingPrep from './MeetingPrep.svelte';
  import StoreSearchInput from '../lib/StoreSearchInput.svelte';
  import L from 'leaflet';
  import 'leaflet/dist/leaflet.css';
  
  let allStores = [];
  let nearbyStores = [];
  let prospects = [];
  let meetingPrepProspect = null; // when set, MeetingPrep overlay runs prefilled

  function runMeetingPrep(prospect) {
    meetingPrepProspect = {
      name: prospect.name || '',
      address: prospect.address || '',
      phone: prospect.phone || '',
      category: prospect.category || prospect.subcategory || '',
      website: prospect.website || '',
      types: prospect.types || [],
      store: selectedStore || null
    };
  }
  let savedProspects = [];
  let savedSearch = '';
  let savedStatusFilter = 'all';
  let expandedSaved = null;
  let teamProspects = []; // All reps' prospects from prospect_data.json
  let teamRepFilter = 'all';
  let teamStatusFilter = 'all';
  let teamSearch = '';
  let expandedTeam = null;
  let allContracts = []; // For attribution matching
  let phoneClicks = []; // Track call history
  let hotLeads = [];
  let callInLeads = []; // Inbound 'New Call In Lead' emails — always shown, NOT cycle-filtered
  let allCallInLeads = []; // full inbound pool before assignment filtering (manager assigns from here)
  let callInAssignments = {}; // leadKey -> { repId, repName } assignment map from Firebase
  let repRoster = []; // [{ id, name }] reps available to assign call-in leads to
  let view = 'main'; // main, nearby-stores, categories, subcategories, results, saved, hot-leads, call-in, pending, submit-lead

  // ── Store Claims (Dibs) ──
  let storeClaims = {};
  let claimLoading = {};

  // ── Lead Claims (Dibs on Prospects) ──
  let leadClaims = {}; // keyed by hash
  let leadDataCache = {}; // keyed by hash — persistent lead data from Firebase
  let leadActivityCache = {}; // keyed by hash — per-prospect contact activity log
  let activityLogProspect = null; // prospect whose full activity log modal is open

  async function loadStoreClaims() {
    // Show cached dibs instantly (survives offline / cold start)
    try {
      const cache = JSON.parse(localStorage.getItem('impro_store_claims') || '{}');
      const now = new Date();
      const fresh = {};
      Object.values(cache).forEach(c => {
        if (c && c.expiresAt && new Date(c.expiresAt) > now) fresh[c.storeName] = c;
      });
      if (Object.keys(fresh).length) storeClaims = fresh;
    } catch {}

    if (!(await whenFirebaseReady())) return;
    const claims = await getZoneClaims('');
    const map = {};
    claims.forEach(c => { map[c.storeName] = c; });
    // Firestore is source of truth — replace and refresh the local cache
    storeClaims = map;
    try { localStorage.setItem('impro_store_claims', JSON.stringify(map)); } catch {}
  }

  async function loadLeadClaims() {
    if (!(await whenFirebaseReady())) return;
    const claims = await getAllLeadClaims();
    const map = {};
    claims.forEach(c => {
      const id = hashLeadId(c.prospectName, c.prospectAddress);
      map[id] = c;
    });
    leadClaims = map;
  }

  async function loadAllLeadData() {
    if (!(await whenFirebaseReady())) return;
    const all = await getAllLeadData();
    const map = {};
    all.forEach(d => {
      const id = hashLeadId(d.prospectName, d.prospectAddress);
      map[id] = d;
    });
    leadDataCache = map;
    loadAllLeadActivity();
  }

  async function loadAllLeadActivity() {
    if (!(await whenFirebaseReady())) return;
    try {
      const all = await getAllLeadActivity();
      const map = {};
      all.forEach(d => {
        const id = hashLeadId(d.prospectName, d.prospectAddress);
        map[id] = d;
      });
      leadActivityCache = map;
    } catch {}
  }

  // Human-friendly action label + emoji for an activity entry.
  const ACTIVITY_META = {
    call:   { icon: '📞', label: 'Called' },
    text:   { icon: '💬', label: 'Texted' },
    email:  { icon: '✉️', label: 'Emailed' },
    'walk-in': { icon: '🚶', label: 'Walk-In' },
    note:   { icon: '📝', label: 'Note' },
    status: { icon: '🏷️', label: 'Status' },
  };
  function activityMeta(action) {
    return ACTIVITY_META[action] || { icon: '•', label: (action || 'Contact') };
  }

  // Relative time like "2h ago", "3d ago", falling back to a date.
  function timeAgo(iso) {
    if (!iso) return '';
    const then = new Date(iso).getTime();
    if (isNaN(then)) return '';
    const diff = Date.now() - then;
    const min = Math.floor(diff / 60000);
    if (min < 1) return 'just now';
    if (min < 60) return min + 'm ago';
    const hr = Math.floor(min / 60);
    if (hr < 24) return hr + 'h ago';
    const d = Math.floor(hr / 24);
    if (d < 7) return d + 'd ago';
    return new Date(iso).toLocaleDateString();
  }

  // Most-recent activity entry for a prospect (or null).
  function getLastActivity(prospect) {
    const doc = leadActivityCache[getLeadHash(prospect)];
    if (doc && Array.isArray(doc.entries) && doc.entries.length) {
      return doc.entries[doc.entries.length - 1];
    }
    // Fall back to a lead-claim's lastAction if no activity log yet.
    const claim = leadClaims[getLeadHash(prospect)];
    if (claim && claim.lastAction) {
      return { action: claim.lastAction, rep: claim.repName || '', at: claim.lastActionAt || claim.claimedAt };
    }
    return null;
  }

  function getActivityEntries(prospect) {
    const doc = leadActivityCache[getLeadHash(prospect)];
    return (doc && Array.isArray(doc.entries)) ? [...doc.entries].reverse() : [];
  }

  function openActivityLog(prospect) {
    activityLogProspect = prospect;
  }
  function closeActivityLog() {
    activityLogProspect = null;
  }

  function getLeadHash(prospect) {
    return hashLeadId(prospect.name, prospect.address);
  }

  // ── Call-In Lead assignment plumbing ──────────────────────────────
  async function loadCallInAssignments() {
    if (!(await whenFirebaseReady())) return;
    try { callInAssignments = await getAllCallInAssignments(); } catch { callInAssignments = {}; }
  }

  // Reps see only leads assigned to them; Tyler + Rick see all (with an assign control).
  function applyCallInVisibility() {
    if (isPrivilegedViewer()) {
      callInLeads = allCallInLeads;
      return;
    }
    const myId = String($user?.id || $user?.rep_id || '');
    const myName = repDisplayName().toLowerCase();
    callInLeads = allCallInLeads.filter(l => {
      const a = callInAssignments[callInLeadKey(l)];
      if (!a || !a.repId) return false; // unassigned → hidden from reps
      return String(a.repId) === myId || (a.repName || '').toLowerCase() === myName;
    });
  }

  // Build the rep roster (id + display name) for the assign dropdown from
  // rep_registry.json, falling back to reps seen in contracts / team data.
  async function buildRepRoster() {
    const roster = new Map();
    try {
      const res = await fetch(import.meta.env.BASE_URL + 'data/rep_registry.json?t=' + Date.now());
      const reg = await res.json();
      const entries = Array.isArray(reg)
        ? reg.map(v => ({ _key: v.id || v.rep_id, ...v }))
        : Object.entries(reg).map(([k, v]) => ({ ...v, _key: k }));
      for (const r of entries) {
        const name = r.name || r.display_name || r.full_name || '';
        const id = r._key || r.id || r.rep_id || name;
        // Skip placeholder / blank entries
        if (!name || String(id) === '999999999') continue;
        roster.set(String(id), { id: String(id), name });
      }
    } catch {}
    repRoster = [...roster.values()].sort((a, b) => a.name.localeCompare(b.name));
  }

  async function handleAssignCallIn(lead, repId) {
    const key = callInLeadKey(lead);
    const rep = repRoster.find(r => String(r.id) === String(repId));
    const repName = rep ? rep.name : '';
    await whenFirebaseReady();
    const ok = await assignCallInLead(key, repId || '', repName, repDisplayName());
    if (ok) {
      if (repId) callInAssignments[key] = { leadKey: key, repId: String(repId), repName, assignedBy: repDisplayName(), assignedAt: new Date().toISOString() };
      else delete callInAssignments[key];
      callInAssignments = callInAssignments;
      applyCallInVisibility();
    }
  }

  function callInAssignedName(lead) {
    const a = callInAssignments[callInLeadKey(lead)];
    return a && a.repId ? (a.repName || 'Assigned') : '';
  }

  // ── Role / Privacy helpers ────────────────────────────────────────
  // Only the rep who logged the notes, Tyler, and Rick Leibowitz may see the
  // private lead details (owner/decision-maker name, contact phone, contact
  // email, and notes). Everyone else sees only a BOOKED/CLOSED status badge.
  function repDisplayName() {
    const u = $user;
    return (u?.name || u?.display_name || '').trim();
  }
  // Tyler + Rick are full-visibility managers.
  function isPrivilegedViewer() {
    const n = repDisplayName().toLowerCase();
    return n.includes('tyler') || n.includes('rick') || ($user?.role === 'manager');
  }
  // Can the current user see the private notes/contact for this lead-data doc?
  function canSeePrivate(ld) {
    if (isPrivilegedViewer()) return true;
    if (!ld) return true; // nothing logged yet — the current rep may start logging
    const owner = (ld.updatedBy || '').trim().toLowerCase();
    if (!owner || owner === 'auto-scrub') return true; // system-scraped, not a rep's private notes
    return owner === repDisplayName().toLowerCase();
  }
  // Derive a BOOKED / CLOSED status shown to reps who can't see private notes.
  // Sources: an explicit saved status, or the last lead-claim action.
  function getSharedStatus(prospect) {
    const ld = leadDataCache[getLeadHash(prospect)] || {};
    const claim = getLeadClaim(prospect) || {};
    const raw = ((ld.status || claim.lastAction || prospect.status || '') + '').toLowerCase();
    if (/(clos|sold|sale|won|signed|contract)/.test(raw)) return 'CLOSED';
    if (/(book|appt|appointment|meeting|scheduled)/.test(raw)) return 'BOOKED';
    return '';
  }

  function getLeadClaim(prospect) {
    return leadClaims[getLeadHash(prospect)] || null;
  }

  async function handleLeadAction(prospect, action) {
    const u = $user;
    if (!u) return;
    const repName = u.name || u.display_name || 'Unknown';
    const repId = u.id || u.rep_id || 'unknown';
    await whenFirebaseReady();
    const ok = await claimLead(repName, repId, prospect.name, prospect.address, action);
    if (ok) {
      const id = getLeadHash(prospect);
      const now = new Date();
      leadClaims[id] = {
        repName, repId,
        prospectName: prospect.name,
        prospectAddress: prospect.address,
        claimedAt: now.toISOString(),
        expiresAt: new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000).toISOString(),
        lastAction: action,
        lastActionAt: now.toISOString(),
      };
      leadClaims = leadClaims;
    }
    // Record a per-prospect activity-log entry (who / what / when).
    recordProspectActivity(prospect, action, repName, repId);
  }

  // Append a contact event to the prospect's activity log (local cache +
  // Firebase) so the card can show "who did it and when" and the full log.
  async function recordProspectActivity(prospect, action, repName, repId, detail = '') {
    const id = getLeadHash(prospect);
    const entry = {
      action,
      rep: repName || repDisplayName() || 'Unknown',
      repId: repId != null ? String(repId) : String($user?.id || $user?.rep_id || ''),
      detail: detail || '',
      at: new Date().toISOString(),
    };
    // Update local cache immediately for instant UI feedback.
    const existing = leadActivityCache[id] || { prospectName: prospect.name, prospectAddress: prospect.address, entries: [] };
    const entries = [...(existing.entries || []), entry];
    if (entries.length > 50) entries.splice(0, entries.length - 50);
    leadActivityCache[id] = { ...existing, prospectName: prospect.name, prospectAddress: prospect.address, entries, lastAction: action, lastRep: entry.rep, lastAt: entry.at };
    leadActivityCache = leadActivityCache;
    try {
      if (await whenFirebaseReady(4000)) await appendLeadActivity(prospect.name, prospect.address, entry);
    } catch {}
  }

  async function handleLeadRelease(prospect) {
    const ok = await releaseLead(prospect.name, prospect.address);
    if (ok) {
      delete leadClaims[getLeadHash(prospect)];
      leadClaims = leadClaims;
    }
  }

  function canReleaseLeadClaim(claim) {
    const u = $user;
    if (!u) return false;
    const name = (u.name || '').toLowerCase();
    const isManager = name.includes('tyler') || name.includes('rick') || (u.role === 'manager');
    if (isManager) return true;
    return claim.repId === (u.id || u.rep_id || '');
  }

  let _pendingSave = {};

  async function handleSaveLeadData(prospect, field, value) {
    const id = getLeadHash(prospect);
    if (!_pendingSave[id]) _pendingSave[id] = {};
    
    // Track the latest value for each field
    _pendingSave[id][field] = value;
    _pendingSave[id]._prospect = prospect;
    
    // Debounce: save after 800ms of no typing
    if (_pendingSave[id]._timer) clearTimeout(_pendingSave[id]._timer);
    _pendingSave[id]._timer = setTimeout(() => flushLeadSave(id), 800);
  }

  async function flushLeadSave(id) {
    const pending = _pendingSave[id];
    if (!pending || !pending._prospect) return;
    
    const prospect = pending._prospect;
    const u = $user;
    const existing = leadDataCache[id] || {};
    
    const data = {
      ownerName: pending.ownerName !== undefined ? pending.ownerName : (existing.ownerName || ''),
      contactPhone: pending.contactPhone !== undefined ? pending.contactPhone : (existing.contactPhone || ''),
      contactEmail: pending.contactEmail !== undefined ? pending.contactEmail : (existing.contactEmail || ''),
      notes: pending.notes !== undefined ? pending.notes : (existing.notes || ''),
      updatedBy: u?.name || u?.display_name || 'Unknown',
    };
    
    // Update local cache immediately
    leadDataCache[id] = { ...existing, ...data, updatedAt: new Date().toISOString(), prospectName: prospect.name, prospectAddress: prospect.address };
    leadDataCache = leadDataCache;
    
    // Save to Firebase
    await saveLeadData(prospect.name, prospect.address, data);
    
    // Clear pending
    delete _pendingSave[id];
  }

  function getNextSatEnd() {
    const now = new Date();
    const day = now.getDay();
    const daysUntilSat = (6 - day) % 7 || 7;
    const sat = new Date(now);
    sat.setDate(now.getDate() + (day === 6 ? 0 : daysUntilSat));
    sat.setHours(23, 59, 59, 999);
    return sat;
  }

  async function handleStoreClaim(store) {
    const u = $user;
    if (!u) return;
    claimLoading[store.StoreName] = true; claimLoading = claimLoading;
    await whenFirebaseReady();
    const ok = await claimStore(
      u.name || u.display_name || 'Unknown',
      u.id || u.rep_id || 'unknown',
      store.StoreName,
      store.ZoneName || u.zone || ''
    );
    if (ok) {
      // Cache locally too so the dibs survives an offline refresh
      try {
        const cache = JSON.parse(localStorage.getItem('impro_store_claims') || '{}');
        cache[store.StoreName] = {
          repName: u.name || u.display_name || 'Unknown',
          repId: u.id || u.rep_id || 'unknown',
          storeName: store.StoreName,
          zone: store.ZoneName || '',
          expiresAt: getNextSatEnd().toISOString(),
        };
        localStorage.setItem('impro_store_claims', JSON.stringify(cache));
      } catch {}
    }
    if (ok) {
      storeClaims[store.StoreName] = {
        repName: u.name || u.display_name || 'Unknown',
        repId: u.id || u.rep_id || 'unknown',
        storeName: store.StoreName,
        zone: store.ZoneName || '',
        expiresAt: getNextSatEnd().toISOString(),
      };
      storeClaims = storeClaims;
    }
    claimLoading[store.StoreName] = false; claimLoading = claimLoading;
  }

  async function handleStoreRelease(storeName) {
    claimLoading[storeName] = true; claimLoading = claimLoading;
    await whenFirebaseReady();
    const ok = await releaseStore(storeName);
    if (ok) {
      delete storeClaims[storeName];
      storeClaims = storeClaims;
      try {
        const cache = JSON.parse(localStorage.getItem('impro_store_claims') || '{}');
        delete cache[storeName];
        localStorage.setItem('impro_store_claims', JSON.stringify(cache));
      } catch {}
    }
    claimLoading[storeName] = false; claimLoading = claimLoading;
  }

  function canReleaseClaim(claim) {
    const u = $user;
    if (!u) return false;
    const isManager = (u.name || '').toLowerCase().includes('tyler') || (u.role === 'manager');
    if (isManager) return true;
    return claim.repId === (u.id || u.rep_id || '');
  }

  function shortName(name) {
    if (!name) return '?';
    const parts = name.split(' ');
    return parts.length > 1 ? `${parts[0]} ${parts[1][0]}.` : parts[0];
  }
  let _edgeSwipeActive = false;
  let _edgeSwipeStartX = 0;
  let _edgeSwipeX = 0;
  let selectedCycle = 'all'; // all, A, B, C
  let selectedStore = null;
  let loadingCustomers = false;
  let customerLoadMessage = '';
  let showCredentialsModal = false;
  let roogleEmail = '';
  let rooglePassword = '';
  let pendingStoreId = null;
  let loadedCustomers = null;
  let videoLibrary = null;

  // Load video library on mount
  function handleStoreSelectFromMap(e) {
    const payload = e.detail;
    // If a full store object was passed, select it directly (skip lookup/intermediate screens)
    if (payload && typeof payload === 'object' && payload.StoreName) {
      selectStore(payload);
      return;
    }
    const storeName = payload;
    // Try immediately, then retry if allStores hasn't loaded yet
    function trySelect() {
      const store = nearbyStores.find(s => s.StoreName === storeName) || allStores.find(s => s.StoreName === storeName);
      if (store) {
        selectStore(store);
        return true;
      }
      return false;
    }
    if (!trySelect()) {
      // Retry after stores finish loading (up to 3 seconds)
      let attempts = 0;
      const retry = setInterval(() => {
        attempts++;
        if (trySelect() || attempts >= 15) clearInterval(retry);
      }, 200);
    }
  }
  
  function handleEdgeSwipeBack() {
    if (view !== 'main') goBack();
  }

  // Jump straight to the Call-In Leads view (fired from the homepage)
  function handleShowCallIn() {
    view = 'call-in';
  }

  // Friendly date formatter for lead cards (e.g. "Jun 29, 2026")
  function fmtLeadDate(s) {
    if (!s) return '';
    const d = new Date(s);
    if (isNaN(d)) return '';
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  // Map a Hot Lead / Call-In Lead record into the full prospect-card shape so
  // it renders with the exact same look, data, and action buttons as prospects.
  function leadToProspect(lead) {
    const phone = (lead.phone || '').toString();
    const email = lead._email || lead.email || '';
    return {
      id: `lead-${lead.crm_id || lead.place_id || lead.business_name}-${lead.store_id || ''}`,
      name: lead.business_name || 'Business',
      address: lead.address || `${lead.store_city || ''}${lead.store_state ? ', ' + lead.store_state : ''}`,
      category: lead.subcategory || lead.category || 'Lead',
      phone,
      email,
      website: lead.website || '',
      rating: lead.rating || 0,
      reviews: lead.reviews || 0,
      distance: lead.distance_mi != null ? lead.distance_mi : null,
      score: lead.category === 'Call-In Lead' ? 90 : (lead.score || 75),
      lat: lead.lat || null,
      lng: lead.lon || null,
      hours: null,
      _sourceLead: lead,
      _callInDate: lead.call_in_date || null,
      _leadComments: lead.lead_comments || '',
      _contactName: lead.contact_name || '',
      _showNotes: false, _showEmail: false, _showScript: false, _showText: false,
    };
  }

  // Open a lead as a full prospect card (same view used for search results).
  function openLeadAsProspect(lead) {
    // Point selectedStore at the lead's targeted store so Book Appt / context work
    const st = allStores.find(s => s.StoreName === lead.store_id);
    if (st) selectedStore = st;
    selectedCategory = lead.subcategory || lead.category || '';
    selectedSubcategory = lead.subcategory || '';
    const p = leadToProspect(lead);
    prospects = [p];
    // Pre-fill the saved contact name into lead data so emails greet them
    if (p._contactName) {
      try {
        const h = getLeadHash(p);
        leadDataCache[h] = { ...(leadDataCache[h] || {}), ownerName: p._contactName,
          contactPhone: p.phone || '', contactEmail: p.email || '' };
        leadDataCache = leadDataCache;
      } catch {}
    }
    leadReturnView = view; // remember where we came from
    view = 'results';
  }

  let leadReturnView = 'hot-leads';

  // Call-In Leads filters/search (separate from Hot Leads)
  let callInSearch = '';
  $: filteredCallInLeads = callInLeads.filter(l => {
    if (!callInSearch) return true;
    const q = callInSearch.toLowerCase();
    return (l.business_name || '').toLowerCase().includes(q) ||
      (l.contact_name || '').toLowerCase().includes(q) ||
      (l.store_city || '').toLowerCase().includes(q) ||
      (l.subcategory || '').toLowerCase().includes(q) ||
      (l.lead_zip || '').includes(q);
  });

  onMount(async () => {
    document.addEventListener('select-store-from-map', handleStoreSelectFromMap);
    document.addEventListener('edge-swipe-back', handleEdgeSwipeBack);
    document.addEventListener('show-callin-leads', handleShowCallIn);
    loadStoreClaims();
    loadLeadClaims();
    loadAllLeadData();
    
    // If user location was already set from Rates tab, auto-trigger Near Me search
    const sharedLoc = $sharedUserLocation;
    if (sharedLoc && sharedLoc.lat && sharedLoc.lng && allStores.length === 0) {
      // Will auto-search once allStores loads (handled below after fetch)
    }
    try {
      const response = await fetch(import.meta.env.BASE_URL + 'data/video_library.json?t=' + Date.now());
      videoLibrary = await response.json();
    } catch (e) {
      console.warn('Could not load video library:', e);
    }
    // Load contracts for attribution
    try {
      const cRes = await fetch(import.meta.env.BASE_URL + 'data/contracts.json?t=' + Date.now());
      const cData = await cRes.json();
      allContracts = cData.contracts || cData || [];
    } catch { allContracts = []; }
    // Load phone click history
    try {
      phoneClicks = JSON.parse(localStorage.getItem('impro_phone_clicks') || '[]');
    } catch { phoneClicks = []; }

    // Load team prospect data for manager view
    try {
      const pdRes = await fetch(import.meta.env.BASE_URL + 'data/prospect_data.json?t=' + Date.now());
      const pdData = await pdRes.json();
      const reps = pdData.reps || {};
      teamProspects = [];
      for (const [repId, repData] of Object.entries(reps)) {
        const repName = repData.name || 'Unknown';
        const prospects = repData.saved_prospects || {};
        for (const [pid, p] of Object.entries(prospects)) {
          teamProspects.push({
            ...p,
            id: pid,
            rep_name: repName,
            rep_id: repId,
            notes: Array.isArray(p.notes) ? p.notes.join('\n') : (p.notes || ''),
          });
        }
      }
    } catch { teamProspects = []; }
  });
  
  onDestroy(() => {
    document.removeEventListener('select-store-from-map', handleStoreSelectFromMap);
    document.removeEventListener('edge-swipe-back', handleEdgeSwipeBack);
    document.removeEventListener('show-callin-leads', handleShowCallIn);

  });

  function getVideoForCategory() {
    if (!videoLibrary) return null;
    
    const categories = videoLibrary.categories || {};
    const subCat = (selectedSubcategory || '').toLowerCase();
    const mainCat = (selectedCategory || '').toLowerCase();
    const searchTerms = [subCat, mainCat].filter(Boolean);
    
    // Try matching subcategory then category against video library keywords
    for (const term of searchTerms) {
      for (const [catName, catData] of Object.entries(categories)) {
        const keywords = (catData.keywords || []).map(k => k.toLowerCase());
        const catNameLower = catName.toLowerCase();
        if (keywords.some(k => term.includes(k) || k.includes(term)) || catNameLower.includes(term) || term.includes(catNameLower)) {
          const videos = catData.videos || [];
          if (videos.length > 0) {
            return videos[Math.floor(Math.random() * videos.length)];
          }
        }
      }
    }
    
    // Fallback: try Food & Drink for restaurant-like categories
    if (mainCat.includes('restaurant') || subCat.includes('pizza') || subCat.includes('coffee') || subCat.includes('taco') || subCat.includes('food')) {
      const foodVideos = categories['Food & Drink']?.videos || [];
      if (foodVideos.length > 0) {
        return foodVideos[Math.floor(Math.random() * foodVideos.length)];
      }
    }
    
    return null;
  }

  let testimonialCache = null;
  
  async function getTestimonialsForCategory() {
    if (!testimonialCache) {
      try {
        // Try slim first, fall back to full
        let response = await fetch(import.meta.env.BASE_URL + 'data/testimonials_slim.json?t=' + Date.now()).catch(() => null);
        if (!response?.ok) response = await fetch(import.meta.env.BASE_URL + 'data/testimonials_cache.json?t=' + Date.now());
        testimonialCache = await response.json();
      } catch (e) {
        console.warn('Could not load testimonials:', e);
        return [];
      }
    }
    
    const subCat = (selectedSubcategory || '').toLowerCase();
    const mainCat = (selectedCategory || '').toLowerCase();
    const searchTerms = [subCat, mainCat].filter(Boolean);
    
    const results = [];
    const testimonials = Array.isArray(testimonialCache) ? testimonialCache : (testimonialCache.testimonials || []);
    
    // Normalize fields (slim format uses b/c/u, full uses business/comment/url)
    const normalize = (t) => ({
      business_name: t.b || t.business_name || t.business || '',
      comments: t.c || t.comments || t.comment || '',
      url: t.u || t.url || '',
      id: t.id || 0,
      searchable: t.searchable || ''
    });

    for (const t of testimonials) {
      const nt = normalize(t);
      const text = (nt.searchable || (nt.business_name + ' ' + nt.comments)).toLowerCase();
      if (searchTerms.some(term => text.includes(term))) {
        results.push(nt);
        if (results.length >= 5) break;
      }
    }
    
    // Add a nearby testimonial if we have a selected store
    if (selectedStore) {
      const city = (selectedStore.City || '').toLowerCase();
      const chain = (selectedStore.GroceryChain || '').toLowerCase();
      const resultIds = new Set(results.map(r => r.id));
      
      for (const t of testimonials) {
        const nt = normalize(t);
        if (resultIds.has(nt.id)) continue;
        const text = (nt.business_name + ' ' + nt.comments).toLowerCase();
        if (text.includes(city) || text.includes(chain)) {
          nt._isLocal = true;
          results.push(nt);
          break;
        }
      }
    }
    
    return results;
  }
  let selectedCategory = null;
  let selectedSubcategory = null;
  let userLocation = null;
  let loading = false;
  let error = '';
  let searchInput = '';
  let customSearch = '';
  let storeSearchQuery = '';
  let filteredStoreResults = [];
  let repRegistry = {};
  let inviteRepEmail = '';
  let copiedAddress = '';
  let prospectSort = 'score'; // score, distance, rating, reviews
  
  // Hot Leads filters
  let hotLeadStoreFilter = 'all';
  let hotLeadZoneFilter = 'all';
  let hotLeadCategoryFilter = 'all';
  let hotLeadRepFilter = 'all';
  let hotLeadSearch = '';
  
  // Build store→rep map from registry
  $: storeToRep = (() => {
    const map = {};
    for (const [uid, info] of Object.entries(repRegistry)) {
      const name = info.display_name || '';
      for (const sid of (info.assigned_stores || [])) {
        map[sid] = name;
      }
    }
    return map;
  })();
  
  $: hotLeadStores = [...new Set(hotLeads.map(l => `${l.store_chain} ${l.store_city} (${l.store_id})`))].sort();
  $: hotLeadZones = [...new Set(hotLeads.map(l => (l.store_id || '').match(/\d+[A-Z]/)?.[0] || '').filter(Boolean))].sort();
  $: hotLeadCategories = [...new Set(hotLeads.map(l => l.category).filter(Boolean))].sort();
  $: hotLeadReps = [...new Set(hotLeads.map(l => storeToRep[l.store_id] || 'Unassigned').filter(Boolean))].sort();
  
  $: filteredHotLeads = hotLeads.filter(l => {
    if (hotLeadStoreFilter !== 'all' && !`${l.store_chain} ${l.store_city} (${l.store_id})`.includes(hotLeadStoreFilter)) return false;
    if (hotLeadZoneFilter !== 'all' && !(l.store_id || '').includes(hotLeadZoneFilter)) return false;
    if (hotLeadCategoryFilter !== 'all' && l.category !== hotLeadCategoryFilter) return false;
    if (hotLeadRepFilter !== 'all' && (storeToRep[l.store_id] || 'Unassigned') !== hotLeadRepFilter) return false;
    if (hotLeadSearch) {
      const q = hotLeadSearch.toLowerCase();
      return (l.business_name || '').toLowerCase().includes(q) ||
        (l.address || '').toLowerCase().includes(q) ||
        (l.store_city || '').toLowerCase().includes(q) ||
        (l.category || '').toLowerCase().includes(q);
    }
    return true;
  });

  const CATEGORIES = {
    '🍽️ Restaurants': ['Mexican', 'Pizza', 'Sandwich Shop', 'Coffee', 'Sushi', 'Fast Food', 'Chinese', 'Thai', 'Indian', 'BBQ', 'Italian', 'Bakery', 'Breakfast/Brunch', 'Seafood', 'Mediterranean', 'Korean', 'Vietnamese', 'Wings', 'Ice Cream/Dessert', 'Juice/Smoothie', 'Bar/Pub', 'Catering', 'Food Truck', 'Brewery/Taproom', 'Winery', 'Donut Shop', 'Deli', 'All'],
    '🚗 Automotive': ['Oil Change', 'Car Wash', 'Auto Repair', 'Tires', 'Car Dealer', 'Body Shop', 'Transmission', 'Detailing', 'Towing', 'Glass Repair'],
    '💄 Beauty & Wellness': ['Hair Salon', 'Barber', 'Nails', 'Spa', 'Gym', 'Yoga', 'Tanning', 'Med Spa', 'Lashes/Brows', 'Tattoo/Piercing', 'Massage'],
    '🏥 Health/Medical': ['Dentist', 'Chiropractor', 'Eye Care', 'Vet', 'Physical Therapy', 'Urgent Care', 'Pharmacy', 'Dermatologist', 'Pediatrician', 'Mental Health', 'Hearing Aid'],
    '🏠 Home Services': ['Plumber', 'Electrician', 'HVAC', 'Roofing', 'Landscaping', 'Cleaning', 'Contractor', 'Pest Control', 'Painting', 'Garage Door', 'Fencing', 'Moving'],
    '🛍️ Retail': ['Clothing', 'Pet Store', 'Jewelry', 'Furniture', 'Florist', 'Cell Phone', 'Liquor', 'Dispensary', 'Thrift/Consignment', 'Gift Shop', 'Smoke Shop', 'Hardware', 'Dry Cleaning'],
    '👔 Professionals': ['Real Estate', 'Insurance', 'Accountant', 'Lawyer', 'Financial', 'Mortgage', 'Tax Prep', 'Notary', 'Printing/Signs'],
    '👦 Kids & Tutoring': ['Tutoring', 'Music', 'Dance', 'Martial Arts', 'Sports', 'Camps', 'General'],
    '👶 Care Centers': ['Daycare', 'After School', 'Assisted Living', 'Adult Care'],
    '🐾 Pet Services': ['Grooming', 'Boarding/Kennel', 'Dog Training', 'Pet Sitting', 'Vet', 'Pet Store'],

  };

  const CATEGORY_KEYWORDS = {
    'Mexican': 'mexican restaurant',
    'Pizza': 'pizza restaurant',
    'Coffee': 'coffee cafe',
    'Sushi': 'sushi restaurant',
    'Fast Food': 'fast food restaurant',
    'Chinese': 'chinese restaurant',
    'Thai': 'thai restaurant',
    'Indian': 'indian restaurant',
    'BBQ': 'bbq restaurant',
    'Italian': 'italian restaurant',
    'Bakery': 'bakery',
    'Bar/Pub': 'bar pub',
    'All': 'restaurant',
    'Oil Change': 'oil change',
    'Car Wash': 'car wash',
    'Auto Repair': 'auto repair',
    'Tires': 'tire shop',
    'Car Dealer': 'car dealer',
    'Body Shop': 'body shop',
    'Transmission': 'transmission repair',
    'Hair Salon': 'hair salon',
    'Barber': 'barber',
    'Nails': 'nail salon',
    'Spa': 'spa massage',
    'Gym': 'gym fitness',
    'Yoga': 'yoga studio',
    'Tanning': 'tanning salon',
    'Dentist': 'dentist',
    'Chiropractor': 'chiropractor',
    'Eye Care': 'optometrist eye care',
    'Vet': 'veterinarian',
    'Physical Therapy': 'physical therapy',
    'Urgent Care': 'urgent care',
    'Pharmacy': 'pharmacy',
    'Plumber': 'plumber',
    'Electrician': 'electrician',
    'HVAC': 'hvac',
    'Roofing': 'roofing',
    'Landscaping': 'landscaping',
    'Cleaning': 'cleaning service',
    'Contractor': 'contractor',
    'Pest Control': 'pest control',
    'Sandwich Shop': 'sandwich shop sub shop deli',
    'Breakfast/Brunch': 'breakfast brunch restaurant',
    'Seafood': 'seafood restaurant',
    'Mediterranean': 'mediterranean restaurant',
    'Korean': 'korean restaurant',
    'Vietnamese': 'vietnamese pho restaurant',
    'Wings': 'wings restaurant',
    'Ice Cream/Dessert': 'ice cream dessert shop',
    'Juice/Smoothie': 'juice smoothie bar',
    'Detailing': 'auto detailing',
    'Towing': 'towing service',
    'Glass Repair': 'auto glass repair',
    'Med Spa': 'med spa aesthetics',
    'Lashes/Brows': 'lash brow salon',
    'Tattoo/Piercing': 'tattoo piercing shop',
    'Massage': 'massage therapist',
    'Dermatologist': 'dermatologist skin care',
    'Pediatrician': 'pediatrician',
    'Mental Health': 'therapist counselor mental health',
    'Hearing Aid': 'hearing aid audiologist',
    'Painting': 'house painting painter',
    'Garage Door': 'garage door repair',
    'Fencing': 'fence company fencing',
    'Moving': 'moving company movers',
    'Thrift/Consignment': 'thrift store consignment',
    'Gift Shop': 'gift shop',
    'Smoke Shop': 'smoke shop vape',
    'Hardware': 'hardware store',
    'Tax Prep': 'tax preparation',
    'Notary': 'notary public',
    'Printing/Signs': 'print shop sign shop',
    'Grooming': 'pet grooming dog grooming',
    'Boarding/Kennel': 'pet boarding kennel',
    'Dog Training': 'dog training obedience',
    'Pet Sitting': 'pet sitting dog walking',
    'Catering': 'catering service',
    'Food Truck': 'food truck',
    'Brewery/Taproom': 'brewery taproom',
    'Winery': 'winery tasting room',
    'Donut Shop': 'donut shop',
    'Deli': 'deli delicatessen',
    'Dry Cleaning': 'dry cleaner laundry'
  };

  onMount(async () => {
    try {
      const [storesRes, leadsRes, repRes] = await Promise.all([
        fetch(import.meta.env.BASE_URL + 'data/stores.json?t=' + Date.now()),
        fetch(import.meta.env.BASE_URL + 'data/hot_leads.json?t=' + Date.now()),
        fetch(import.meta.env.BASE_URL + 'data/rep_registry.json?t=' + Date.now()).catch(() => ({ json: () => ({}) }))
      ]);
      allStores = await storesRes.json();
      repRegistry = await repRes.json().catch(() => ({}));
      
      // If user location was shared from Rates tab, auto-populate nearby stores
      const sharedLoc2 = $sharedUserLocation;
      if (sharedLoc2 && sharedLoc2.lat && sharedLoc2.lng && nearbyStores.length === 0 && view === 'main') {
        userLocation = sharedLoc2;
        const withDistances = allStores
          .map(store => ({
            ...store,
            distance: calculateDistance(sharedLoc2.lat, sharedLoc2.lng, store.latitude, store.longitude)
          }))
          .filter(s => s.distance <= 25)
          .sort((a, b) => a.distance - b.distance)
          .slice(0, 10);
        if (withDistances.length > 0) {
          nearbyStores = withDistances;
          view = 'nearby-stores';
        }
      }
      
      // Load hot leads - scoped to stores rep has sold at, filtered by current cycle
      let allLeadsData = await leadsRes.json();
      
      // Load contracts to find which stores this rep has sold at
      let repStoreIds = new Set();
      try {
        const contractsRes = await fetch(import.meta.env.BASE_URL + 'data/contracts.json?t=' + Date.now());
        const contractsData = await contractsRes.json();
        const contracts = contractsData.contracts || [];
        const rn = ($user?.name || '').toLowerCase();
        const isManager = rn.includes('tyler') || rn.includes('rick') || $user?.role === 'manager';
        
        if (isManager) {
          // Managers see all leads
          repStoreIds = null; // null = no filter
        } else {
          // Find stores where this rep has sold
          for (const c of contracts) {
            const rep = (c.sales_rep || '').toLowerCase();
            if (rep.includes(rn.split(' ')[0])) {
              const chain = (c.store_name || '').trim();
              const num = (c.store_number || '').trim();
              const zone = (c.zone || '').trim();
              if (chain && num) {
                // Match to stores.json format: find StoreName that contains the store number
                const matched = allStores.find(s => 
                  s.StoreName && s.StoreName.includes(num) && 
                  s.GroceryChain && s.GroceryChain.toLowerCase().includes(chain.toLowerCase().split(' ')[0])
                );
                if (matched) repStoreIds.add(matched.StoreName);
              }
            }
          }
        }
      } catch (err) {
        console.error('Error loading contracts for rep stores:', err);
        repStoreIds = null; // fallback: show all
      }
      
      // Determine current selling cycle
      // Cycle schedule: B selling until Apr 11, then C selling from Apr 11
      // Install dates (7th): A=Jan/Apr/Jul/Oct, B=Feb/May/Aug/Nov, C=Mar/Jun/Sep/Dec
      // Selling: A install → C sell, B install → A sell, C install → B sell
      const now = new Date();
      const month = now.getMonth(); // 0-indexed
      const day = now.getDate();
      const cycleMap = ['A','B','C'];
      // Current install cycle based on month
      const installIdx = month % 3; // 0=A, 1=B, 2=C
      const installCycle = cycleMap[installIdx];
      // Before the 11th = previous selling cycle, after 11th = current selling cycle
      // Selling cycle: A install→C sell, B install→A sell, C install→B sell
      const sellMap = { 'A': 'C', 'B': 'A', 'C': 'B' };
      let currentSellingCycle;
      if (day < 11) {
        // Still on previous cycle's selling
        const prevMonth = (month + 11) % 12;
        const prevInstall = cycleMap[prevMonth % 3];
        currentSellingCycle = sellMap[prevInstall];
      } else {
        currentSellingCycle = sellMap[installCycle];
      }
      
      // Filter stores by current cycle
      const cycleStores = new Set(
        allStores.filter(s => s.Cycle === currentSellingCycle).map(s => s.StoreName)
      );
      
      // Hot Leads exclude Call-In Leads (those get their own always-on section)
      const hotLeadPool = allLeadsData.filter(l => l.category !== 'Call-In Lead');
      // Filter hot leads: rep's stores + current cycle
      if (repStoreIds === null) {
        // Manager: show all leads for current cycle stores
        hotLeads = hotLeadPool.filter(l => !l.store_id || cycleStores.has(l.store_id));
      } else if (repStoreIds.size > 0) {
        // Rep: show leads for their stores that are in current cycle
        const repCycleStores = new Set([...repStoreIds].filter(id => cycleStores.has(id)));
        hotLeads = hotLeadPool.filter(l => !l.store_id || repCycleStores.has(l.store_id));
      } else {
        hotLeads = []; // No stores found for this rep
      }
      
      console.log(`Hot Leads: ${hotLeads.length} leads, Selling Cycle: ${currentSellingCycle}, Rep stores: ${repStoreIds === null ? 'all (manager)' : repStoreIds.size}`);

      // Call-In Leads: inbound, time-sensitive — ALWAYS shown regardless of cycle.
      // ASSIGNMENT MODEL: a call-in lead is hidden from a rep until Tyler/Rick
      // assigns it to them. Tyler + Rick always see every call-in lead.
      allCallInLeads = allLeadsData
        .filter(l => l.category === 'Call-In Lead')
        .sort((a, b) => (b.generated_at || '').localeCompare(a.generated_at || ''));
      await loadCallInAssignments();
      applyCallInVisibility();
      buildRepRoster();
      console.log(`Call-In Leads (visible): ${callInLeads.length} of ${allCallInLeads.length}`);
      
      loadSavedProspects();
    } catch (err) {
      error = 'Failed to load data';
      console.error(err);
    }
  });

  // Detect stores with dummy/state-center coordinates
  // States outside OR/WA/CA got a single geocode point per state
  function isBadCoords(lat, lng) {
    if (!lat || !lng) return true;
    // Check if many stores share this exact coord (dummy data)
    const matching = allStores.filter(s => 
      Math.abs((s.latitude || 0) - lat) < 0.01 && 
      Math.abs((s.longitude || 0) - lng) < 0.01
    );
    return matching.length > 10; // More than 10 stores at same spot = dummy coords
  }

  // Svelte action: renders a mini Leaflet map showing prospect + selected store + nearby stores
  function initMiniMap(node, params) {
    const { prospect, store } = params;
    const pLat = prospect.lat;
    const pLng = prospect.lng;
    const sLat = store?.latitude || store?.Latitude;
    const sLng = store?.longitude || store?.Longitude;

    const map = L.map(node, {
      center: [pLat, pLng],
      zoom: 13,
      zoomControl: true,
      attributionControl: false,
      dragging: true,
      scrollWheelZoom: false,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
    }).addTo(map);

    // Prospect marker (red)
    L.circleMarker([pLat, pLng], {
      radius: 10, fillColor: '#CC0000', color: '#fff', weight: 2, fillOpacity: 0.9,
    }).addTo(map).bindPopup(`<strong>${prospect.name}</strong><br><span style="font-size:12px;">${prospect.address || ''}</span>`).openPopup();

    const bounds = [[pLat, pLng]];

    // Selected store marker (blue) + distance line
    if (sLat && sLng) {
      L.circleMarker([sLat, sLng], {
        radius: 12, fillColor: '#1a73e8', color: '#fff', weight: 3, fillOpacity: 0.9,
      }).addTo(map).bindPopup(`<strong>🏪 ${store.GroceryChain || ''}</strong><br><span style="font-size:12px;">${store.StoreName || ''}<br>${store.Address || ''}, ${store.City || ''}</span><br><span style="font-size:11px;color:#666;">Cycle ${store.Cycle || '?'} · ${store['Case Count'] || '?'} cases</span>`);

      // Dashed line between store and prospect
      L.polyline([[sLat, sLng], [pLat, pLng]], {
        color: '#CC0000', weight: 2, dashArray: '8, 6', opacity: 0.7,
      }).addTo(map);

      // Distance label at midpoint
      const midLat = (pLat + sLat) / 2;
      const midLng = (pLng + sLng) / 2;
      const dist = calculateDistance(pLat, pLng, sLat, sLng);
      L.marker([midLat, midLng], {
        icon: L.divIcon({
          className: 'distance-label',
          html: `<div style="background:#fff;border:1px solid #ccc;border-radius:8px;padding:2px 8px;font-size:12px;font-weight:700;color:#CC0000;white-space:nowrap;box-shadow:0 1px 3px rgba(0,0,0,0.2);">${dist.toFixed(1)} mi</div>`,
          iconSize: [60, 24],
          iconAnchor: [30, 12],
        }),
      }).addTo(map);

      bounds.push([sLat, sLng]);
    }

    // Nearby stores (green, smaller) — within 10mi of the prospect
    const selectedName = store?.StoreName || '';
    const nearby = allStores.filter(s => {
      if (s.StoreName === selectedName) return false;
      const lat = s.latitude || s.Latitude;
      const lng = s.longitude || s.Longitude;
      if (!lat || !lng) return false;
      const d = calculateDistance(pLat, pLng, lat, lng);
      return d <= 10;
    }).sort((a, b) => {
      const dA = calculateDistance(pLat, pLng, a.latitude || a.Latitude, a.longitude || a.Longitude);
      const dB = calculateDistance(pLat, pLng, b.latitude || b.Latitude, b.longitude || b.Longitude);
      return dA - dB;
    }).slice(0, 15);

    nearby.forEach(s => {
      const lat = s.latitude || s.Latitude;
      const lng = s.longitude || s.Longitude;
      const d = calculateDistance(pLat, pLng, lat, lng);
      L.circleMarker([lat, lng], {
        radius: 7, fillColor: '#2e7d32', color: '#fff', weight: 1.5, fillOpacity: 0.75,
      }).addTo(map).bindPopup(`<strong>🏪 ${s.GroceryChain || ''}</strong><br><span style="font-size:12px;">${s.StoreName || ''}<br>${s.Address || ''}, ${s.City || ''}</span><br><span style="font-size:11px;color:#666;">Cycle ${s.Cycle || '?'} · ${s['Case Count'] || '?'} cases · ${d.toFixed(1)} mi</span>`);
      bounds.push([lat, lng]);
    });

    // Fit all markers in view
    if (bounds.length > 1) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
    }

    return {
      destroy() {
        map.remove();
      }
    };
  }

  function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 3959; // Earth radius in miles
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
             Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
             Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
  }

  function startNearMeSearch() {
    error = '';
    loading = true;

    if (!navigator.geolocation) {
      error = 'Geolocation not supported';
      loading = false;
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        userLocation = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        
        // Save last GPS location for this rep (used by territory map beacons)
        try {
          const repName = $user?.contract_name || $user?.display_name || $user?.name || 'Unknown';
          const repLocations = JSON.parse(localStorage.getItem('repLastLocations') || '{}');
          repLocations[repName] = { lat: pos.coords.latitude, lng: pos.coords.longitude, timestamp: new Date().toISOString() };
          localStorage.setItem('repLastLocations', JSON.stringify(repLocations));
        } catch (e) { /* ignore */ }
        
        // Find 10 nearest stores
        const withDistances = allStores
          .map(store => ({
            ...store,
            distance: calculateDistance(userLocation.lat, userLocation.lng, store.latitude, store.longitude)
          }))
          .filter(s => s.distance <= 25) // Within 25 miles
          .sort((a, b) => a.distance - b.distance)
          .slice(0, 10);

        if (withDistances.length > 0) {
          nearbyStores = withDistances;
          view = 'nearby-stores';
          // Share with other tabs (Rates, Map)
          sharedNearbyStores.set(withDistances);
          sharedUserLocation.set(userLocation);
        } else {
          error = 'No stores found within 25 miles';
        }
        loading = false;
      },
      (err) => {
        error = 'Enable location services to use Near Me';
        loading = false;
      }
    );
  }

  const PLACES_KEY_PS = 'AIzaSyBoslNJj8aO6wkQOfkH9e4qTVJZ-G9nOuA';

  async function lookupStorePhone(store) {
    if (!store || store._phone || store._phoneLoading) return;
    store._phoneLoading = true;
    selectedStore = selectedStore; // trigger reactivity
    try {
      const query = `${store.GroceryChain} ${store.Address} ${store.City} ${store.State}`;
      const res = await fetch('https://places.googleapis.com/v1/places:searchText', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Goog-Api-Key': PLACES_KEY_PS,
          'X-Goog-FieldMask': 'places.nationalPhoneNumber,places.internationalPhoneNumber' },
        body: JSON.stringify({ textQuery: query, maxResultCount: 1 })
      });
      const data = await res.json();
      store._phone = data.places?.[0]?.nationalPhoneNumber || data.places?.[0]?.internationalPhoneNumber || '';
    } catch { store._phone = ''; }
    store._phoneLoading = false;
    selectedStore = selectedStore; // trigger reactivity
  }

  function selectStore(store) {
    selectedStore = store;
    sharedSelectedStore.set(store);
    lookupStorePhone(store);
    view = 'categories';
  }

  function selectCategory(cat) {
    selectedCategory = cat;
    view = 'subcategories';
  }

  function promptForCredentials() {
    if (!selectedStore) return;
    
    // Get user from store
    const currentUser = localStorage.getItem('impro_user');
    if (!currentUser) {
      alert('Please log in first');
      return;
    }
    
    const user = JSON.parse(currentUser);
    pendingStoreId = selectedStore.StoreName;
    
    // Get credentials from session (set during login)
    const sessionCreds = sessionStorage.getItem('indoormedia_credentials');
    if (!sessionCreds) {
      alert('Session expired. Please log in again.');
      return;
    }
    
    const creds = JSON.parse(sessionCreds);
    roogleEmail = creds.email;
    rooglePassword = creds.password;
    submitCredentialsAndLoad();
  }

  async function submitCredentialsAndLoad() {
    if (!roogleEmail || !rooglePassword) {
      customerLoadMessage = '❌ Email and password required';
      return;
    }

    loadingCustomers = true;
    customerLoadMessage = 'Loading customers from Roogle...';
    showCredentialsModal = false;
    
    // Save credentials to localStorage for future use
    localStorage.setItem('roogleCredentials', JSON.stringify({
      email: roogleEmail,
      password: rooglePassword
    }));
    
    try {
      let data = null;
      
      // Try local server first (if running)
      try {
        const localResponse = await Promise.race([
          fetch('http://localhost:3001/api/roogle-scraper', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
              storeId: pendingStoreId,
              email: roogleEmail,
              password: rooglePassword
            })
          }),
          new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 5000))
        ]);
        
        if (localResponse.ok) {
          data = await localResponse.json();
          console.log('✅ Using local Roogle server data');
        }
      } catch (localError) {
        // Local server not available or timed out, use Vercel demo API
        console.log('Local server not available, using demo data');
      }
      
      // If local server failed, use Vercel demo API
      if (!data) {
        const vercelResponse = await fetch(import.meta.env.BASE_URL + 'api/roogle-scraper', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            storeId: pendingStoreId,
            email: roogleEmail,
            password: rooglePassword
          })
        });
        
        if (!vercelResponse.ok) {
          // Silently use demo data even on error
          console.log('Demo data (no live API)');
          data = {
            success: true,
            storeId: pendingStoreId,
            current: [{ businessName: "Demo Data", status: "Active", price: "Demo", category: "Demo" }],
            past: [],
            all: [{ businessName: "Demo Data", status: "Active", price: "Demo", category: "Demo" }]
          };
        } else {
          data = await vercelResponse.json();
        }
      }
      
      if (!data.success && !data.current) {
        throw new Error(data.error || 'Failed to load customers');
      }
      
      // Add current customers to savedProspects (Clients tab)
      data.current?.forEach(customer => {
        if (!savedProspects.find(p => p.name === customer.businessName)) {
          savedProspects.push({
            id: `${pendingStoreId}-${customer.businessName}`,
            name: customer.businessName,
            category: customer.category || 'Active Contract',
            status: 'active',
            notes: `${customer.contractType} - ${customer.price}`,
            savedAt: new Date().toISOString()
          });
        }
      });
      
      // Add all customers to prospects (Prospects tab)
      data.all?.forEach(customer => {
        if (!prospects.find(p => p.name === customer.businessName)) {
          prospects.push({
            id: `${pendingStoreId}-${customer.businessName}`,
            name: customer.businessName,
            address: selectedStore.City + ', ' + selectedStore.State,
            category: customer.category || customer.status,
            phone: '',
            email: '',
            website: '',
            rating: 0,
            reviews: 0,
            _showNotes: false,
            _showEmail: false,
            _showScript: false
          });
        }
      });
      
      savedProspects = [...savedProspects];
      prospects = [...prospects];
      persistProspects();
      
      // Store loaded customers for display
      loadedCustomers = {
        current: data.current || [],
        past: data.past || []
      };
      
      customerLoadMessage = `✅ Loaded ${data.current?.length || 0} active + ${data.past?.length || 0} past customers`;
      
      // Clear credentials after use
      roogleEmail = '';
      rooglePassword = '';
      pendingStoreId = null;
      
      setTimeout(() => {
        customerLoadMessage = '';
      }, 3000);
      
    } catch (err) {
      console.error('Roogle load failed:', err);
      customerLoadMessage = `❌ Error: ${err.message}`;
    } finally {
      loadingCustomers = false;
    }
  }

  function closeCredentialsModal() {
    showCredentialsModal = false;
    roogleEmail = '';
    rooglePassword = '';
    pendingStoreId = null;
  }

  async function searchCustom() {
    if (!customSearch.trim()) return;
    loading = true;
    error = '';
    selectedSubcategory = customSearch.trim();

    try {
      const results = await searchGooglePlaces(selectedStore.latitude, selectedStore.longitude, customSearch.trim());
      prospects = results;
      trackSearch(selectedCategory, customSearch.trim(), selectedStore?.StoreName);
      view = 'results';
    } catch (err) {
      console.error('Custom search failed:', err);
      error = 'Search failed. Try a different keyword.';
    } finally {
      loading = false;
    }
  }

  // Top-performing categories from 10K+ testimonials (ranked by advertiser success)
  const NEW_BIZ_QUERIES = [
    'new restaurant', 'new mexican restaurant', 'new pizza',
    'new car wash', 'new oil change', 'new auto repair',
    'new hair salon', 'new barber', 'new nail salon',
    'new coffee shop', 'new bakery', 'new sushi',
    'new spa', 'new massage', 'new vet veterinarian',
    'new gym fitness', 'new dentist',
  ];

  async function searchNewBusinesses() {
    selectedCategory = '🆕 New Businesses';
    selectedSubcategory = 'New (Last Year)';
    loading = true;
    error = '';

    try {
      const lat = selectedStore?.latitude || selectedStore?.Latitude || 0;
      const lng = selectedStore?.longitude || selectedStore?.Longitude || 0;
      const storeCity = selectedStore?.City || '';
      const storeState = selectedStore?.State || '';
      const storeZip = selectedStore?.PostalCode || '';
      const hasRealCoords = selectedStore && !isBadCoords(lat, lng);

      const allResults = [];
      const seenNames = new Set();

      const searchBatch = async (queries) => {
        const promises = queries.map(async (q) => {
          let textQuery;
          if (hasRealCoords) {
            textQuery = q;
          } else if (storeZip) {
            textQuery = `${q} near ${storeCity}, ${storeState} ${storeZip}`;
          } else {
            textQuery = `${q} near ${storeCity}, ${storeState}`;
          }

          const requestBody = { textQuery, maxResultCount: 5 };
          if (hasRealCoords) {
            requestBody.locationBias = { circle: { center: { latitude: lat, longitude: lng }, radius: 16000.0 } };
          }

          try {
            const response = await fetch('https://places.googleapis.com/v1/places:searchText', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': PLACES_API_KEY,
                'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.location,places.businessStatus,places.nationalPhoneNumber,places.websiteUri,places.googleMapsUri,places.regularOpeningHours'
              },
              body: JSON.stringify(requestBody)
            });
            const data = await response.json();
            return data.places || [];
          } catch { return []; }
        });
        return (await Promise.all(promises)).flat();
      };

      // Run in batches of 4
      for (let i = 0; i < NEW_BIZ_QUERIES.length; i += 4) {
        const batch = NEW_BIZ_QUERIES.slice(i, i + 4);
        const places = await searchBatch(batch);
        for (const place of places) {
          const name = place.displayName?.text || '';
          const reviews = place.userRatingCount || 0;
          if (name && !seenNames.has(name.toLowerCase()) && reviews <= 40) {
            seenNames.add(name.toLowerCase());
            const pLat = place.location?.latitude || 0;
            const pLng = place.location?.longitude || 0;
            const dist = calculateDistance(lat, lng, pLat, pLng);
            allResults.push({
              id: name,
              name,
              address: place.formattedAddress || 'Address unavailable',
              rating: place.rating || 0,
              reviews,
              distance: Math.round(dist * 10) / 10,
              score: reviews <= 10 ? 98 : reviews <= 20 ? 90 : reviews <= 30 ? 80 : 70,
              phone: place.nationalPhoneNumber || null,
              email: place.emailAddress || null,
              website: place.websiteUri || null,
              mapsUrl: place.googleMapsUri || null,
              status: place.businessStatus === 'OPERATIONAL' ? 'open' : 'check',
              hours: place.regularOpeningHours?.weekdayDescriptions || null,
              lat: pLat, lng: pLng,
            });
          }
        }
      }

      // New businesses must be within 5 miles of the selected store
      prospects = allResults.filter(p => !p.distance || p.distance <= 5).sort((a, b) => a.reviews - b.reviews);
      trackSearch('🆕 New Businesses', 'New (Last Year)', selectedStore?.StoreName);
      view = 'results';
    } catch (err) {
      console.error('New business search failed:', err);
      error = 'Failed to find new businesses. Try again.';
    } finally {
      loading = false;
    }
  }

  async function selectSubcategory(subcat) {
    selectedSubcategory = subcat;
    loading = true;
    error = '';

    try {
      // Use Google Places API to find real businesses
      const keyword = CATEGORY_KEYWORDS[subcat] || subcat.toLowerCase();
      const results = await searchGooglePlaces(selectedStore.latitude, selectedStore.longitude, keyword);
      prospects = results;
      trackSearch(selectedCategory, subcat, selectedStore?.StoreName);
      view = 'results';
    } catch (err) {
      console.error('Search failed:', err);
      error = 'Failed to find prospects. Try another category.';
    } finally {
      loading = false;
    }
  }

  const PLACES_API_KEY = 'AIzaSyBoslNJj8aO6wkQOfkH9e4qTVJZ-G9nOuA';

  async function searchGooglePlaces(lat, lng, keyword) {
    try {
      // Build location-aware query
      const storeCity = selectedStore?.City || '';
      const storeState = selectedStore?.State || '';
      const storeAddr = selectedStore?.Address || '';
      const storeZip = selectedStore?.PostalCode || '';
      const hasRealCoords = selectedStore && !isBadCoords(lat, lng);
      
      // If store has bad/dummy coords, use address/city/zip for a precise text search
      let textQuery;
      if (hasRealCoords) {
        textQuery = keyword;
      } else if (storeZip) {
        textQuery = `${keyword} near ${storeCity}, ${storeState} ${storeZip}`;
      } else {
        textQuery = `${keyword} near ${storeCity}, ${storeState}`;
      }
      
      const requestBody = {
        textQuery: textQuery,
        maxResultCount: 10
      };

      // Only use locationBias if we have real coordinates
      if (hasRealCoords) {
        requestBody.locationBias = {
          circle: {
            center: { latitude: lat, longitude: lng },
            radius: 16000.0
          }
        };
      }

      const response = await fetch('https://places.googleapis.com/v1/places:searchText', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Goog-Api-Key': PLACES_API_KEY,
          'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.location,places.businessStatus,places.nationalPhoneNumber,places.websiteUri,places.googleMapsUri,places.regularOpeningHours'
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const errText = await response.text();
        console.error('Google API error:', response.status, errText);
        throw new Error('API error ' + response.status);
      }

      const data = await response.json();

      return (data.places || []).map((place) => {
        const pLat = place.location?.latitude || 0;
        const pLng = place.location?.longitude || 0;
        const dist = calculateDistance(lat, lng, pLat, pLng);
        const rating = place.rating || 0;
        const reviews = place.userRatingCount || 0;

        const distScore = Math.max(0, 40 - (dist * 8));
        const ratingScore = (rating / 5) * 30;
        const reviewScore = Math.min(30, (reviews / 100) * 30);
        const score = Math.round(distScore + ratingScore + reviewScore);

        return {
          id: place.displayName?.text || 'unknown',
          name: place.displayName?.text || 'Unnamed',
          address: place.formattedAddress || 'Address unavailable',
          rating,
          reviews,
          distance: Math.round(dist * 10) / 10,
          score: Math.min(100, score),
          phone: place.nationalPhoneNumber || null,
          email: place.emailAddress || null,
          website: place.websiteUri || null,
          mapsUrl: place.googleMapsUri || null,
          status: place.businessStatus === 'OPERATIONAL' ? 'open' : 'check',
          hours: place.regularOpeningHours?.weekdayDescriptions || null,
          lat: pLat,
          lng: pLng
        };
      }).filter(p => !p.distance || p.distance <= 3).sort((a, b) => b.score - a.score);
    } catch (err) {
      console.error('Google Places error:', err);
      error = 'Search failed. Please try again.';
      return [];
    }
  }

  // Email templates — uses {business}, {contact}, {rep}, {store} placeholders
  // {store} = full store reference like "the Safeway on Center Street in Salem"
  const emailTemplates = [
    { id: 'initial', icon: '🎯', name: 'Initial Appointment',
      subject: '{chain} shoppers could be walking into {business}',
      body: 'Hi {contact},\n\nI noticed {business} in the area and wanted to reach out. We work with local businesses to help drive foot traffic through register tape advertising at {store}.\n\nThousands of businesses like yours have seen measurable results — would you be open to a quick 10-minute chat this week?\n\nBest,\n{rep}\nIndoorMedia' },
    { id: 'roi', icon: '📊', name: 'ROI / Value Focused',
      subject: '{customers} {chain} shoppers a week — within reach of {business}',
      body: 'Hi {contact},\n\n{store_cap} sees {customers} customers per week. That\'s {customers} potential customers seeing your ad every single week.\n\nBusinesses in your category have reported strong ROI — many seeing results within the first month. Our register tape ads put your name, offer, and location directly in shoppers\' hands at {store}.\n\nI\'d love to show you how the numbers work for {business}. Can we schedule a quick call?\n\nBest,\n{rep}\nIndoorMedia' },
    { id: 'followup', icon: '⏰', name: 'Follow-up (No Response)',
      subject: 'Still holding a {chain} spot for {business}',
      body: 'Hi {contact},\n\nI reached out a few days ago about a partnership opportunity for {business} at {store} and wanted to follow up.\n\nWith {customers} shoppers coming through each week, register tape advertising is one of the most effective ways to reach local customers. I think there\'s a great fit here.\n\nWould you have 10 minutes this week for a quick chat?\n\nBest,\n{rep}\nIndoorMedia' },
    { id: 'reengagement', icon: '🔄', name: 'Re-engagement',
      subject: 'New {chain} availability — perfect for {business}',
      body: 'Hi {contact},\n\nIt\'s been a while since we last connected about {business}. A lot has changed at IndoorMedia — new store locations, better pricing, and stronger results for businesses like yours.\n\nWe have availability at {store} right now and I think it could be a great fit.\n\nWould you be open to reconnecting for a quick 10-minute call?\n\nBest,\n{rep}\nIndoorMedia' },
    { id: 'limited', icon: '⚡', name: 'Limited Time Offer',
      subject: 'Only one {chain} spot left for {business}',
      body: 'Hi {contact},\n\nI wanted to give you a heads up — we have limited ad placement availability at {store}.\n\nWith {customers} shoppers per week, this is one of the highest-traffic locations in the area. Our partnership program is filling up fast, and I\'d hate for {business} to miss out.\n\nCan we schedule a quick call this week?\n\nBest,\n{rep}\nIndoorMedia' },
  ];

  // Program-specific email templates — one per product across Tape, Cart, and
  // Digital. Surfaced under a "By Program" picker so reps can lead with the
  // exact product they want to pitch. Subjects carry the {chain} name + an
  // open-worthy hook; bodies greet the saved contact by name.
  const programEmailTemplates = [
    // ── TAPE ──
    { id: 'prog-tape', icon: '🧾', name: 'Register Tape', group: 'Tape',
      subject: 'Put {business} in every {chain} shopper\u2019s hand',
      body: 'Hi {contact},\n\nEvery customer who checks out at {store} walks away holding their receipt — and that\'s prime real estate for {business}. Our register tape ads print your name, offer, and location right on the back, reaching {customers} local shoppers every week.\n\nIt\'s repetition where people already are, at a fraction of the cost of a billboard. Could I show you how it works in 10 minutes?\n\nBest,\n{rep}\nIndoorMedia' },
    // ── CART ──
    { id: 'prog-cart', icon: '🛒', name: 'Cartvertising', group: 'Cart',
      subject: 'Your brand on every cart at {chain}, {business}',
      body: 'Hi {contact},\n\nImagine {business} riding along on every shopping cart at {store} for six months straight. Cartvertising puts your ad in front of {customers} shoppers a week — eye-level, all day, every aisle.\n\nOne business per category, so once the spot is yours, your competition can\'t take it. Want me to check if it\'s still open?\n\nBest,\n{rep}\nIndoorMedia' },
    // ── DIGITAL ──
    { id: 'prog-digitalboost', icon: '🚀', name: 'DigitalBoost (Geofencing)', group: 'Digital',
      subject: 'Reach phones near {chain} for {business}',
      body: 'Hi {contact},\n\nWhat if {business} could send an ad straight to the phone of every shopper near {store}? DigitalBoost draws a digital fence around high-traffic spots and delivers your ad to people inside it — then follows them with it.\n\nIt pairs perfectly with our in-store advertising: they see you at the store, then see you again on their phone. Got 10 minutes to see how it targets your area?\n\nBest,\n{rep}\nIndoorMedia' },
    { id: 'prog-findlocal', icon: '📍', name: 'FindLocal (Local SEO)', group: 'Digital',
      subject: 'Make sure {business} actually gets found online',
      body: 'Hi {contact},\n\nWhen someone near {chain} searches for what {business} offers, do they find you — or a competitor? FindLocal gets your business listed accurately across 50+ directories, maps, and search engines, so you show up where it counts.\n\nIt\'s the foundation that makes every other ad work harder. Worth a quick 10-minute look?\n\nBest,\n{rep}\nIndoorMedia' },
    { id: 'prog-reviewboost', icon: '⭐', name: 'ReviewBoost (Reviews)', group: 'Digital',
      subject: 'Turn happy {business} customers into 5-star reviews',
      body: 'Hi {contact},\n\nReviews are the new word of mouth — and most happy customers just need a nudge. ReviewBoost automatically asks them by email and text right after their visit, sending the happy ones to leave a public review and quietly catching the unhappy ones first.\n\nMore stars means more {chain} shoppers choosing {business} over the competition. Can I show you how it runs on autopilot?\n\nBest,\n{rep}\nIndoorMedia' },
    { id: 'prog-loyaltyboost', icon: '💎', name: 'LoyaltyBoost (Loyalty)', group: 'Digital',
      subject: 'Keep {business} customers coming back all year',
      body: 'Hi {contact},\n\nWinning a customer is hard; keeping them should be easy. LoyaltyBoost gives {business} a year-round rewards program that brings customers back again and again — with automated offers that drive repeat visits.\n\nCombine it with reaching new shoppers at {store}, and you\'re filling the top of the funnel and the bottom. Got 10 minutes this week?\n\nBest,\n{rep}\nIndoorMedia' },
  ];

  // Category-specific email templates. Keyed by a matcher run against the
  // selected category + subcategory (lowercased). The first matching group's
  // templates are surfaced ABOVE the generic ones with a category badge.
  const categoryEmailTemplates = [
    {
      match: ['real estate', 'realtor', 'realty', 'mortgage', 'broker'],
      label: 'Realtor',
      templates: [
        { id: 'realtor-listings', icon: '🏡', name: 'Realtor — Own Your Market',
          subject: 'Be the agent {business}\'s neighbors think of first',
          body: 'Hi {contact},\n\nIn real estate, the agent who stays top-of-mind wins the listing. {store_cap} puts your name, photo, and number directly into the hands of {customers} local homeowners every week — the exact people deciding to buy or sell.\n\nWhile other agents pay for clicks that disappear, your register tape ad rides home in every shopper\'s bag. It\'s how you become the name people call before they ever Google one.\n\nCould I show you how a few of our agents are turning this into listings? 10 minutes this week?\n\nBest,\n{rep}\nIndoorMedia' },
        { id: 'realtor-farm', icon: '📍', name: 'Realtor — Farm a Neighborhood',
          subject: 'Own the {store_short} neighborhood, {business}',
          body: 'Hi {contact},\n\nThe best way to dominate a farm area is repetition where people already are — and everyone shops. {store_cap} reaches {customers} households a week, right in your target neighborhood.\n\nOne agent per category, so your competition can\'t take the spot once it\'s yours. Want me to check if your area is still open?\n\nBest,\n{rep}\nIndoorMedia' },
      ],
    },
    {
      match: ['dentist', 'dental', 'orthodont'],
      label: 'Dental',
      templates: [
        { id: 'dental-newpatients', icon: '🦷', name: 'Dental — New Patients',
          subject: 'Fill your chairs with local patients, {business}',
          body: 'Hi {contact},\n\nNew patients are the lifeblood of a practice — and they\'re all shopping at {store_short}. Our register tape ads put {business} (with your new-patient or whitening offer) into the hands of {customers} local families every week.\n\nDental practices in the area are seeing steady new-patient flow from this. Could we grab 10 minutes so I can show you the numbers?\n\nBest,\n{rep}\nIndoorMedia' },
      ],
    },
    {
      match: ['auto repair', 'oil change', 'tires', 'body shop', 'transmission', 'car wash', 'detailing', 'automotive'],
      label: 'Automotive',
      templates: [
        { id: 'auto-trust', icon: '🚗', name: 'Auto — Be the Trusted Shop',
          subject: 'Be the shop {business}\'s neighbors trust',
          body: 'Hi {contact},\n\nWhen someone\'s check-engine light comes on, they go with the name they recognize. {store_cap} puts {business} in front of {customers} local drivers every week — with your coupon right in their hand.\n\nShops in the area are filling bays with this. Worth a quick 10-minute look?\n\nBest,\n{rep}\nIndoorMedia' },
      ],
    },
    {
      match: ['hair salon', 'barber', 'nails', 'spa', 'gym', 'yoga', 'med spa', 'lash', 'massage', 'beauty', 'wellness', 'tanning'],
      label: 'Beauty & Wellness',
      templates: [
        { id: 'beauty-book', icon: '💅', name: 'Beauty — Fill the Books',
          subject: 'Keep {business} booked solid',
          body: 'Hi {contact},\n\nNew clients keep a salon thriving — and they\'re all walking through {store_short}. Our register tape ads put {business} and a first-visit offer into {customers} local hands every week.\n\nSalons and spas nearby are filling slow days this way. Could I show you how it works in 10 minutes?\n\nBest,\n{rep}\nIndoorMedia' },
      ],
    },
    {
      match: ['restaurant', 'pizza', 'mexican', 'coffee', 'cafe', 'bakery', 'sushi', 'bbq', 'deli', 'food', 'bar', 'pub', 'brewery', 'taco', 'wings'],
      label: 'Restaurant',
      templates: [
        { id: 'rest-tables', icon: '🍽️', name: 'Restaurant — Fill Tables',
          subject: 'Fill more tables at {business}',
          body: 'Hi {contact},\n\nHungry people are deciding where to eat the second they leave {store_short}. Our register tape ads put {business} — and a tempting offer — right in the hands of {customers} local shoppers every week.\n\nNo 30% delivery fees, no fleeting social posts — just your name in front of customers on their way home. Restaurants nearby are filling slow shifts with this.\n\nGot 10 minutes this week?\n\nBest,\n{rep}\nIndoorMedia' },
      ],
    },
    {
      match: ['plumber', 'electrician', 'hvac', 'roofing', 'landscaping', 'cleaning', 'contractor', 'pest', 'painting', 'garage door', 'fencing', 'moving', 'home services'],
      label: 'Home Services',
      templates: [
        { id: 'home-firstcall', icon: '🔧', name: 'Home Services — Be the First Call',
          subject: 'Be the first call when something breaks, {business}',
          body: 'Hi {contact},\n\nHome-service jobs go to whoever\'s name is on the fridge. {store_cap} puts {business} into the hands of {customers} local homeowners every week — so when the pipe bursts or the AC quits, they call you first.\n\nContractors in the area are booking jobs off this. Worth a 10-minute look?\n\nBest,\n{rep}\nIndoorMedia' },
      ],
    },
  ];

  // Returns category-specific templates that match the current category/subcat
  function getCategoryTemplates() {
    const hay = `${selectedCategory || ''} ${selectedSubcategory || ''}`.toLowerCase();
    for (const group of categoryEmailTemplates) {
      if (group.match.some(m => hay.includes(m))) {
        return group.templates.map(t => ({ ...t, _categoryLabel: group.label }));
      }
    }
    return [];
  }

  // Program templates tagged with their group label so they render with a badge.
  function getProgramTemplates() {
    return programEmailTemplates.map(t => ({ ...t, _programLabel: t.group }));
  }

  // ── Smart Multi-Pronged template ──────────────────────────────────
  // A category-aware, business-researched email that sells the in-person +
  // digital one-two punch and the outsized results it drives — written to sound
  // like Tyler, not a template. Body is generated per-prospect at render time.

  // Per-category framing: {noun}=who they serve, {win}=the outcome they want,
  // {moment}=the buying moment we intercept.
  const CATEGORY_ANGLE = [
    { m: ['real estate','realtor','realty','mortgage','broker'], noun: 'homeowners', win: 'listings and closings', moment: 'the moment someone starts thinking about buying or selling' },
    { m: ['dentist','dental','orthodont'], noun: 'families', win: 'new patients in the chair', moment: 'when a family is picking a dentist' },
    { m: ['auto repair','oil change','tires','body shop','transmission','car wash','detailing','automotive'], noun: 'drivers', win: 'booked bays', moment: 'the second a check-engine light comes on' },
    { m: ['hair salon','barber','nails','spa','gym','yoga','med spa','lash','massage','beauty','wellness','tanning'], noun: 'locals', win: 'a booked-solid calendar', moment: 'when someone finally books that appointment they keep putting off' },
    { m: ['restaurant','pizza','mexican','coffee','cafe','bakery','sushi','bbq','deli','food','bar','pub','brewery','taco','wings'], noun: 'hungry shoppers', win: 'full tables and bigger tickets', moment: 'the second they leave the store deciding where to eat' },
    { m: ['plumber','electrician','hvac','roofing','landscaping','cleaning','contractor','pest','painting','garage door','fencing','moving','home services'], noun: 'homeowners', win: 'a full job calendar', moment: 'the day something breaks and they need someone fast' },
  ];
  function getCategoryAngle() {
    const hay = `${selectedCategory || ''} ${selectedSubcategory || ''}`.toLowerCase();
    for (const a of CATEGORY_ANGLE) if (a.m.some(x => hay.includes(x))) return a;
    return { noun: 'local customers', win: 'more customers through the door', moment: 'the moment they’re deciding who to go with' };
  }

  // Turn scraped research into one natural, specific sentence about the business.
  function researchLine(prospect) {
    const r = prospect && prospect._research;
    if (!r || r.empty) return '';
    const name = prospect.name;
    const flags = r.flags || [];
    if (r.services && r.services.length) {
      const svc = r.services.slice(0, 2).join(' and ');
      if (r.yearsCount) return `I did a little homework before reaching out — ${r.yearsCount} years doing ${svc} is no accident, and it tells me ${name} already does the hard part right.`;
      if (flags.includes('family-owned') || flags.includes('locally-owned')) return `I did a little homework first — a ${flags.includes('family-owned') ? 'family-owned' : 'locally-owned'} shop known for ${svc} is exactly the kind of business this works best for.`;
      return `I did a little homework before reaching out — the ${svc} side of what you do at ${name} really stood out.`;
    }
    if (r.yearsCount) return `I did a little homework first — ${r.yearsCount} years in business tells me ${name} is doing something right, and I think we can put a lot more eyes on it.`;
    if (flags.includes('award-winning')) return `I did a little homework first — an award-winning reputation like ${name}’s deserves to be in front of a lot more people.`;
    if (r.tagline) return `I did a little homework before reaching out — “${r.tagline}” is a great line, and it’s exactly the kind of story that lands when the right people see it.`;
    return '';
  }

  // Build the full multi-pronged body for a specific prospect (Tyler's voice).
  function buildMultiProngedBody(prospect) {
    const a = getCategoryAngle();
    const research = researchLine(prospect);
    const openerResearch = research ? research + '\n\n' : '';
    return (
`Hi {contact},

${openerResearch}Here’s the thing most advertising gets wrong: it picks a lane. You’re either in front of people out in the community, or you’re chasing them online — rarely both. So the message never really sticks.

We do both, on purpose. Picture ${a.noun} near {store_short}: first they see ${prospect.name} in their hands at the checkout — your name, your offer, ${getStoreCustomers()} of them every week. Then, that same day, they see you again on their phone as they scroll, because we’ve drawn a digital fence around the neighborhoods that actually matter to you.

Same customer. Two touchpoints. ${a.moment.charAt(0).toUpperCase() + a.moment.slice(1)} — and there you are, twice. That’s when a name goes from “never heard of them” to “oh yeah, those guys,” and that shift is where the real money is.

The businesses running both together aren’t seeing little bumps. They’re seeing the kind of ${a.win} that changes how a month looks. In-person builds the trust; digital keeps you top of mind until they’re ready — and they always get ready.

I’d love 10 minutes to map out exactly what this looks like for ${prospect.name}. No pitch marathon, just the plan. What does later this week look like for you?

Best,
{rep}
IndoorMedia`
    );
  }

  // The special dynamic template descriptor. body is a function(prospect).
  function getMultiProngedTemplate() {
    return {
      id: 'multi-pronged',
      icon: '🚀',
      name: 'Multi-Pronged (In-Person + Digital)',
      _featured: true,
      _dynamic: true,
      subject: 'Two ways {business} shows up for {chain} shoppers — same day',
      body: (p) => buildMultiProngedBody(p),
    };
  }

  // Combined list: featured Multi-Pronged first, then category-specific,
  // then program templates (Tape / Cart / Digital), then the generic five.
  function getEmailTemplatesFor() {
    return [getMultiProngedTemplate(), ...getCategoryTemplates(), ...getProgramTemplates(), ...emailTemplates];
  }

  // Build a natural store reference like "the Safeway on Center Street in Salem"
  function getStoreRef() {
    if (!selectedStore) return 'a nearby grocery store';
    const chain = selectedStore.GroceryChain || 'the store';
    const street = (selectedStore.Address || '').split(',')[0].trim();
    const city = selectedStore.City || '';
    if (street && city) return `the ${chain} on ${street} in ${city}`;
    if (city) return `the ${chain} in ${city}`;
    return `the ${chain}`;
  }

  function getStoreShort() {
    if (!selectedStore) return 'a nearby store';
    const chain = selectedStore.GroceryChain || 'the store';
    const city = selectedStore.City || '';
    return city ? `${chain} in ${city}` : chain;
  }

  // Weekly customer impressions: cases × 50 × 137 × 2 / 90 = daily, × 7 = weekly
  function getStoreCustomers() {
    const cases = selectedStore?.['Case Count'] || 0;
    if (!cases) return '10,000+';
    const weekly = cases * 50 * 137 * 2 / 90 * 7;
    const rounded = Math.round(weekly / 1000) * 1000;
    return rounded.toLocaleString() + '+';
  }

  // Just the grocery chain name, e.g. "Safeway" — used in subject lines
  function getStoreChain() {
    if (!selectedStore) return 'your local grocery store';
    return selectedStore.GroceryChain || 'your local grocery store';
  }

  // Read the saved contact / decision-maker name for a prospect (from lead data).
  function getSavedContactName(prospect) {
    if (!prospect) return '';
    try {
      const ld = leadDataCache[getLeadHash(prospect)];
      const name = (ld && ld.ownerName ? String(ld.ownerName) : '').trim();
      if (!name) return '';
      // Greet by first name only for warmth ("Hi John,") unless it's a title/full co. name
      const first = name.split(/\s+/)[0];
      return first;
    } catch { return ''; }
  }

  // Replace all template placeholders including {store} and {customers} variants.
  // Pass the full prospect so we can read the saved contact name and address them.
  function fillTemplate(text, prospect) {
    // Dynamic templates supply a function body(prospect); resolve it first.
    if (typeof text === 'function') text = text(prospect);
    const rep = $user?.name || $user?.first_name || 'Your Rep';
    const prospectName = (prospect && typeof prospect === 'object') ? prospect.name : prospect;
    const contact = (prospect && typeof prospect === 'object') ? getSavedContactName(prospect) : '';
    // "Hi John," when we know them, otherwise a clean "Hi there,"
    const greetName = contact || 'there';
    return text
      .replace(/\{business\}/g, prospectName)
      .replace(/\{contact\}/g, greetName)
      .replace(/\{rep\}/g, rep)
      .replace(/\{chain\}/g, getStoreChain())
      .replace(/\{store_cap\}/g, getStoreRef().replace(/^the /, 'The '))
      .replace(/\{store_short\}/g, getStoreShort())
      .replace(/\{store\}/g, getStoreRef())
      .replace(/\{customers\}/g, getStoreCustomers());
  }

  // ── Email scrubbing ──────────────────────────────────────────────
  // Google Places almost never returns an email, so we (1) try the saved
  // Notes email, then (2) scrape the prospect's website for a public address.
  // Scrape goes through a CORS-friendly read proxy since GitHub Pages is static.

  const GENERIC_EMAIL_PREFIXES = ['info', 'contact', 'hello', 'office', 'admin', 'sales', 'frontdesk', 'reception', 'support', 'team', 'service', 'booking', 'appointments', 'mail'];

  function getSavedEmail(prospect) {
    try {
      const ld = leadDataCache[getLeadHash(prospect)];
      if (ld && ld.contactEmail && ld.contactEmail.includes('@')) return ld.contactEmail.trim();
    } catch {}
    // Also sniff a saved free-text note for an email pattern
    try {
      const ld = leadDataCache[getLeadHash(prospect)];
      const note = (ld?.notes || getProspectNote(prospect.id || prospect.name) || '');
      const m = note.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/);
      if (m) return m[0];
    } catch {}
    return '';
  }

  // Resolve best-known email WITHOUT network: explicit field > saved/notes
  function resolveProspectEmail(prospect) {
    if (prospect.email && prospect.email.includes('@')) return prospect.email;
    const saved = getSavedEmail(prospect);
    if (saved) return saved;
    return '';
  }

  function rankEmail(email, prospect) {
    const e = email.toLowerCase();
    // Penalize file-ish / image-ish false positives
    if (/\.(png|jpg|jpeg|gif|webp|svg|css|js)$/i.test(e)) return -100;
    if (/(example|sentry|wixpress|godaddy|\.wpengine|@2x|\.wixpress|placeholder|yourdomain|domain\.com|email\.com|sample|test@|noreply|no-reply|donotreply|do-not-reply)/.test(e)) return -50;
    const prefix = e.split('@')[0];
    const domain = (e.split('@')[1] || '');
    let score = 0;
    if (GENERIC_EMAIL_PREFIXES.some(p => prefix === p)) score += 5;       // info@, contact@ etc are ideal cold targets
    else if (GENERIC_EMAIL_PREFIXES.some(p => prefix.startsWith(p))) score += 3;
    if (/(owner|manager|gm|frontoffice|principal|director|president|ceo)/.test(prefix)) score += 6;
    // Prefer an email whose domain matches the prospect's own website (avoids grabbing a
    // web-designer / vendor / social-widget address embedded in the page).
    if (prospect && prospect.website) {
      try {
        const host = new URL(prospect.website.startsWith('http') ? prospect.website : 'https://' + prospect.website).hostname.replace(/^www\./, '');
        const root = host.split('.').slice(-2).join('.');
        if (domain === host || domain.endsWith('.' + root) || domain === root) score += 8;
      } catch {}
    }
    // Free-mail providers are still useful for small businesses, but rank below own-domain
    if (/(gmail|yahoo|hotmail|outlook|aol|icloud|comcast|live|msn)\./.test(domain)) score += 2;
    if (e.endsWith('.com')) score += 1;
    return score;
  }

  // Decode common email obfuscations so "info [at] shop [dot] com", HTML-entity, and
  // simple JS-concatenated addresses are recoverable.
  function deobfuscateEmails(rawHtml) {
    let html = rawHtml;
    // HTML entity decode (numeric + named) via a detached element
    try {
      const ta = document.createElement('textarea');
      // decode in chunks to avoid pathological huge strings
      ta.innerHTML = html.replace(/&#(\d+);/g, (_, n) => '&#' + n + ';');
      html = html + '\n' + ta.value;
    } catch {}
    // Normalize [at]/(at)/ AT  and [dot]/(dot)/ DOT  spacing tricks
    let normalized = html
      .replace(/\s*[\[(<{]\s*(?:at|@)\s*[\])>}]\s*/gi, '@')
      .replace(/\s+(?:at)\s+/gi, '@')
      .replace(/\s*[\[(<{]\s*(?:dot|\.)\s*[\])>}]\s*/gi, '.')
      .replace(/\s+(?:dot)\s+/gi, '.');
    return html + '\n' + normalized;
  }

  function harvestEmails(html, found) {
    const decoded = deobfuscateEmails(html);
    // mailto: links first (highest confidence)
    for (const m of decoded.matchAll(/mailto:([^"'?>\s]+@[^"'?>\s]+)/gi)) {
      found.add(m[1].toLowerCase().replace(/[.,;:]+$/, ''));
    }
    // bare email patterns in the page text
    for (const m of decoded.matchAll(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g)) {
      found.add(m[0].toLowerCase().replace(/[.,;:]+$/, ''));
    }
  }

  // Strip tags to readable text for name scanning.
  function htmlToText(html) {
    return html
      .replace(/<script[\s\S]*?<\/script>/gi, ' ')
      .replace(/<style[\s\S]*?<\/style>/gi, ' ')
      .replace(/<[^>]+>/g, ' ')
      .replace(/&nbsp;/gi, ' ')
      .replace(/&amp;/gi, '&')
      .replace(/\s+/g, ' ')
      .trim();
  }

  const NAME = '[A-Z][a-z]+(?:\\.?)?(?:\\s+[A-Z]\\.?)?\\s+[A-Z][a-z]+(?:-[A-Z][a-z]+)?';
  const NON_NAME_WORDS = /^(The|Our|Your|About|Contact|Home|Welcome|Services|Team|Staff|Menu|Hours|Location|Reviews|Gallery|Book|Call|Email|Privacy|Terms|Copyright|All|New|Best|Free|Read|View|Learn|More|Get|Meet|We|Us|My|This)$/;

  // Look for an owner / proprietor / decision-maker name on the page.
  function harvestOwnerNames(html, names) {
    const text = htmlToText(html);
    const patterns = [
      // "Owner: John Smith"  /  "Owner - John Smith"  /  "Owner, John Smith"
      new RegExp('(?:owner|proprietor|founder|co-?founder|president|principal|managing partner|general manager|gm|ceo)\\s*[:\\-,\\u2013]?\\s+(' + NAME + ')', 'gi'),
      // "John Smith, Owner"  /  "John Smith - Owner"  /  "John Smith, Founder & CEO"
      new RegExp('(' + NAME + ')\\s*[,\\-\\u2013]\\s*(?:the\\s+)?(?:owner|proprietor|founder|co-?founder|president|principal|managing partner|general manager|gm|ceo)', 'gi'),
      // "Meet John Smith" / "Owned by John Smith" / "Founded by John Smith"
      new RegExp('(?:meet|owned by|founded by|established by|run by|led by)\\s+(' + NAME + ')', 'gi'),
      // "Dr. John Smith" (common for dental/medical prospects)
      new RegExp('(Dr\\.?\\s+' + NAME + ')', 'g'),
    ];
    for (let i = 0; i < patterns.length; i++) {
      for (const m of text.matchAll(patterns[i])) {
        let nm = (m[1] || '').trim().replace(/\s+/g, ' ');
        if (!nm) continue;
        const first = nm.split(/\s+/)[0].replace(/\.$/, '');
        if (NON_NAME_WORDS.test(first)) continue;
        // weight: title-adjacent patterns (0,1) are strongest; "meet/owned by" (2) next; Dr. (3)
        const weight = i === 0 || i === 1 ? 5 : i === 2 ? 3 : 2;
        names.set(nm, Math.max(names.get(nm) || 0, weight));
      }
    }
  }

  // Normalize a phone string to just its digits (drop +1 country code).
  function phoneDigits(s) {
    let d = (s || '').replace(/[^0-9]/g, '');
    if (d.length === 11 && d.startsWith('1')) d = d.slice(1);
    return d;
  }
  function formatPhone(d) {
    if (d.length === 10) return `(${d.slice(0,3)}) ${d.slice(3,6)}-${d.slice(6)}`;
    return d;
  }

  // Look for phone numbers on the page (tel: links + text patterns), excluding
  // the business's already-listed number. Returns normalized 10-digit strings.
  function harvestPhones(html, phones, listedDigits) {
    const decoded = deobfuscateEmails(html); // reuse entity-decode pass
    const add = (raw, weight) => {
      const d = phoneDigits(raw);
      if (d.length !== 10) return;                 // US 10-digit only
      if (/^(0|1)/.test(d)) return;                // invalid area code start
      if (/^(\d)\1{9}$/.test(d)) return;           // 0000000000 etc
      if (listedDigits && d === listedDigits) return; // skip the business listing #
      phones.set(d, Math.max(phones.get(d) || 0, weight));
    };
    // tel: links are highest confidence
    for (const m of decoded.matchAll(/tel:\+?([0-9().\-\s]{7,20})/gi)) add(m[1], 5);
    // labeled numbers: "Cell: 555-...", "Mobile", "Direct", "Owner", "Text"
    for (const m of decoded.matchAll(/(cell|mobile|direct|owner|text|fax|call|phone|tel|reach)[^0-9]{0,15}(\+?1?[\s.\-]?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4})/gi)) {
      const isFax = /fax/i.test(m[1]);
      add(m[2], isFax ? 2 : 4);
    }
    // bare US phone patterns in the text
    for (const m of decoded.matchAll(/\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}/g)) add(m[0], 3);
  }

  // Fetch a URL through whichever CORS read-proxy responds first; falls back across proxies.
  async function fetchViaProxy(target, timeoutMs = 8000) {
    const proxies = [
      (u) => 'https://api.allorigins.win/raw?url=' + encodeURIComponent(u),
      (u) => 'https://corsproxy.io/?url=' + encodeURIComponent(u),
      (u) => 'https://thingproxy.freeboard.io/fetch/' + u,
      (u) => 'https://r.jina.ai/' + (u.startsWith('http') ? u : 'https://' + u),
    ];
    for (const build of proxies) {
      try {
        const res = await Promise.race([
          fetch(build(target)),
          new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), timeoutMs)),
        ]);
        if (res.ok) {
          const text = await res.text();
          if (text && text.length > 50) return text;
        }
      } catch { /* next proxy */ }
    }
    return '';
  }

  // ── Business research (for the smart multi-pronged email) ────────────
  // Pulls real, specific signals off the prospect's own website so the email
  // can reference what THIS business actually does — not generic filler.
  // Stashes { services:[], specialty, years, tagline } on prospect._research.
  const RESEARCH_STOP = /^(and|the|for|with|your|our|you|all|new|our|get|book|call|now|home|about|contact|menu|hours|more|read|view|learn|free|best|shop|team|staff|us|we|to|of|in|on|at|a|an|is|are|we're|welcome)$/i;

  function harvestBusinessResearch(html, acc) {
    const text = htmlToText(html);
    const low = text.toLowerCase();

    // Services / offerings: look for common list phrasing.
    const svcPatterns = [
      /(?:we (?:offer|provide|specialize in|do)|our services include|services[:\-]|specializing in|specialties[:\-])\s+([^.!?]{6,140})/gi,
    ];
    for (const re of svcPatterns) {
      for (const m of low.matchAll(re)) {
        const chunk = (m[1] || '').replace(/&amp;/g, '&');
        chunk.split(/,|\band\b|\/|\u2022|\|/).forEach(s => {
          const t = s.trim().replace(/[^a-z0-9 &'-]/gi, '').trim();
          const words = t.split(/\s+/).filter(Boolean);
          if (t.length >= 4 && t.length <= 34 && words.length <= 4 && !RESEARCH_STOP.test(words[0])) {
            acc.services.set(t, (acc.services.get(t) || 0) + 1);
          }
        });
      }
    }

    // "Since 1998" / "est. 2004" / "family-owned since" / "X years"
    const yr = low.match(/(?:since|established|est\.?|serving[^.]*since)\s*(19\d\d|20[0-2]\d)/);
    if (yr && !acc.years) acc.years = yr[1];
    const yrs = low.match(/(\d{1,3})\+?\s*years/);
    if (yrs && !acc.yearsCount) acc.yearsCount = yrs[1];

    // Trust signals worth name-dropping.
    if (/family[\s-]owned/.test(low)) acc.flags.add('family-owned');
    if (/locally[\s-]owned|local(?:ly)?\s+owned/.test(low)) acc.flags.add('locally-owned');
    if (/award[\s-]winning|voted best|best of/.test(low)) acc.flags.add('award-winning');
    if (/licensed (?:and|&) insured|licensed[\s,]+insured/.test(low)) acc.flags.add('licensed & insured');
    if (/free (?:estimate|consultation|quote)/.test(low)) acc.flags.add('free estimates');

    // Meta description often has a crisp one-liner about the business.
    const meta = html.match(/<meta[^>]+name=["']description["'][^>]+content=["']([^"']{20,180})["']/i);
    if (meta && !acc.tagline) acc.tagline = meta[1].replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim();
  }

  // Crawl a few pages of the prospect's site and return a compact research object.
  async function researchProspect(prospect, opts = {}) {
    if (!prospect.website) { prospect._research = { empty: true }; return prospect._research; }
    let base;
    try { base = new URL(prospect.website.startsWith('http') ? prospect.website : 'https://' + prospect.website).origin; }
    catch { base = prospect.website.replace(/\/$/, ''); }
    const acc = { services: new Map(), years: '', yearsCount: '', flags: new Set(), tagline: '' };
    const paths = ['', '/about', '/about-us', '/services', '/what-we-do'];
    let count = 0;
    for (const p of paths) {
      if (count >= (opts.deep ? 5 : 4)) break;
      count++;
      try { const html = await fetchViaProxy(base + p, 7000); if (html) harvestBusinessResearch(html, acc); }
      catch { /* keep going */ }
    }
    const services = [...acc.services.entries()].sort((a, b) => b[1] - a[1]).map(([s]) => s).slice(0, 3);
    prospect._research = {
      services,
      years: acc.years || '',
      yearsCount: acc.yearsCount || '',
      flags: [...acc.flags],
      tagline: acc.tagline || '',
      empty: services.length === 0 && !acc.years && !acc.yearsCount && acc.flags.size === 0 && !acc.tagline,
    };
    return prospect._research;
  }

  // Deep-comb the prospect's website for a contact email: crawls the homepage +
  // common contact pages, follows contact/about links found on the homepage,
  // de-obfuscates addresses, tries multiple proxies, and ranks by own-domain match.
  async function scrapeWebsiteEmail(prospect, opts = {}) {
    if (!prospect.website) return '';
    let base;
    try {
      base = new URL(prospect.website.startsWith('http') ? prospect.website : 'https://' + prospect.website).origin;
    } catch {
      base = prospect.website.replace(/\/$/, '');
    }
    const commonPaths = [
      '', '/contact', '/contact-us', '/contactus', '/contact.html', '/about', '/about-us',
      '/get-in-touch', '/reach-us', '/connect', '/support', '/team', '/staff', '/our-team',
      '/location', '/locations', '/hours', '/book', '/appointments', '/schedule', '/quote',
    ];
    const visited = new Set();
    const found = new Set();
    const names = new Map();
    const phones = new Map();
    const listedDigits = phoneDigits(prospect.phone || prospect.formatted_phone_number || '');
    const queue = commonPaths.map(p => base + p);

    // 1) Grab the homepage first so we can discover real contact-page links.
    try {
      const home = await fetchViaProxy(base, 8000);
      if (home) {
        harvestEmails(home, found);
        harvestOwnerNames(home, names);
        harvestPhones(home, phones, listedDigits);
        // discover internal links whose text/href hints at contact/about/team pages
        for (const m of home.matchAll(/href=["']([^"'#]+)["'][^>]*>([^<]{0,60})/gi)) {
          const href = m[1];
          const label = (m[2] || '').toLowerCase();
          if (/(contact|about|team|staff|reach|connect|get.?in.?touch|location|book|appoint)/i.test(href + ' ' + label)) {
            try {
              const abs = new URL(href, base).href;
              if (abs.startsWith(base) && !queue.includes(abs)) queue.push(abs);
            } catch {}
          }
        }
      }
    } catch {}

    // 2) Crawl the queue (cap total pages to stay fast/polite).
    const MAX_PAGES = opts.deep ? 14 : 8;
    let count = 0;
    for (const target of queue) {
      if (count >= MAX_PAGES) break;
      const key = target.replace(/\/$/, '');
      if (visited.has(key)) continue;
      visited.add(key);
      count++;
      try {
        const html = await fetchViaProxy(target, 7000);
        if (html) { harvestEmails(html, found); harvestOwnerNames(html, names); harvestPhones(html, phones, listedDigits); }
      } catch { /* keep going */ }
      // Early exit only once we already have a strong own-domain hit AND an owner name
      const best = [...found].map(e => rankEmail(e, prospect)).sort((a, b) => b - a)[0] || 0;
      if (best >= 8 && names.size && !opts.deep) break;
    }

    const ranked = [...found]
      .filter(e => rankEmail(e, prospect) > -10)
      .sort((a, b) => rankEmail(b, prospect) - rankEmail(a, prospect));
    // stash the full ranked list so the UI can offer alternates
    prospect._emailCandidates = ranked.slice(0, 8);

    // Rank owner-name candidates and stash them for the UI / auto-fill.
    const rankedNames = [...names.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([n]) => n);
    prospect._ownerCandidates = rankedNames.slice(0, 5);
    prospect._scrapedOwner = rankedNames[0] || '';

    // Rank phone candidates (excluding the listed business number) for the UI.
    const rankedPhones = [...phones.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([d]) => formatPhone(d));
    prospect._phoneCandidates = rankedPhones.slice(0, 5);
    prospect._scrapedPhone = rankedPhones[0] || '';
    return ranked[0] || '';
  }

  // Called when the email panel opens: fill prospect.email from saved/notes,
  // and kick off a website scrape if we still don't have one.
  async function ensureProspectEmail(prospect, opts = {}) {
    const known = resolveProspectEmail(prospect);
    if (known && !prospect.email) { prospect.email = known; prospects = prospects; }
    // On a normal open, don't re-scrape if we already have an address. A forced
    // deep comb (opts.deep / opts.force) always runs, even to find alternates.
    if (prospect.email && prospect.email.includes('@') && !opts.force && !opts.deep) return;
    if (!prospect.website) return;
    if (prospect._emailScrapeTried && !opts.force && !opts.deep) return;
    prospect._emailScrapeTried = true;
    prospect._emailScrapeFailed = false;
    prospect._emailScraping = true;
    prospect._emailDeep = !!opts.deep;
    prospects = prospects;
    const scraped = await scrapeWebsiteEmail(prospect, opts);
    prospect._emailScraping = false;
    prospect._emailDeep = false;
    if (scraped) {
      // Deep comb should not silently overwrite a manually-chosen address.
      if (!prospect.email || !prospect._emailManual) {
        prospect.email = scraped;
        prospect._emailScraped = true;
        persistScrapedEmail(prospect, scraped);
      }
    } else if (!prospect.email) {
      prospect._emailScrapeFailed = true;
    }
    // Auto-fill owner name if we found one and there isn't a saved/manual name yet.
    if (prospect._scrapedOwner) {
      const savedName = (leadDataCache[getLeadHash(prospect)]?.ownerName || '').trim();
      if (!savedName && !prospect._ownerManual) {
        prospect._ownerScraped = true;
        persistScrapedOwner(prospect, prospect._scrapedOwner);
      }
    }
    // Auto-fill a scraped direct/cell phone if there isn't a saved/manual one yet.
    if (prospect._scrapedPhone) {
      const savedPhone = (leadDataCache[getLeadHash(prospect)]?.contactPhone || '').trim();
      if (!savedPhone && !prospect._phoneManual) {
        prospect._phoneScraped = true;
        persistScrapedPhone(prospect, prospect._scrapedPhone);
      }
    }
    prospects = prospects;
  }

  // User picks an alternate candidate from the deep-comb results.
  function chooseProspectEmail(prospect, email) {
    prospect.email = email;
    prospect._emailManual = true;
    prospect._emailScraped = true;
    prospects = prospects;
    persistScrapedEmail(prospect, email);
  }

  // User picks (or confirms) an owner-name candidate from the deep comb.
  function chooseProspectOwner(prospect, name) {
    prospect._ownerManual = true;
    prospect._ownerScraped = true;
    prospects = prospects;
    persistScrapedOwner(prospect, name);
  }

  // User picks (or confirms) a phone candidate from the deep comb.
  function chooseProspectPhone(prospect, phone) {
    prospect._phoneManual = true;
    prospect._phoneScraped = true;
    prospects = prospects;
    persistScrapedPhone(prospect, phone);
  }

  // Auto-save a scraped email into the prospect's Notes (lead data) so it
  // syncs across devices. Never overwrites a manually-entered Notes email.
  async function persistScrapedEmail(prospect, email) {
    const id = getLeadHash(prospect);
    const existing = leadDataCache[id] || {};
    if (existing.contactEmail && existing.contactEmail.includes('@')) return; // keep manual entry
    const u = $user;
    const data = {
      ownerName: existing.ownerName || '',
      contactPhone: existing.contactPhone || '',
      contactEmail: email,
      notes: existing.notes || '',
      updatedBy: u?.name || u?.display_name || 'auto-scrub',
      emailSource: 'website',
    };
    leadDataCache[id] = { ...existing, ...data, updatedAt: new Date().toISOString(), prospectName: prospect.name, prospectAddress: prospect.address };
    leadDataCache = leadDataCache;
    try {
      if (await whenFirebaseReady(4000)) await saveLeadData(prospect.name, prospect.address, data);
    } catch {}
  }

  // Auto-save a scraped/selected owner name into the prospect's Notes (lead data)
  // so it syncs across devices and greets emails by name. Never clobbers a manual entry.
  async function persistScrapedOwner(prospect, name) {
    const id = getLeadHash(prospect);
    const existing = leadDataCache[id] || {};
    if (existing.ownerName && existing.ownerName.trim() && !prospect._ownerManual) return; // keep existing
    const u = $user;
    const data = {
      ownerName: name,
      contactPhone: existing.contactPhone || '',
      contactEmail: existing.contactEmail || (prospect.email && prospect.email.includes('@') ? prospect.email : ''),
      notes: existing.notes || '',
      updatedBy: u?.name || u?.display_name || 'auto-scrub',
      ownerSource: prospect._ownerManual ? 'website-confirmed' : 'website',
    };
    leadDataCache[id] = { ...existing, ...data, updatedAt: new Date().toISOString(), prospectName: prospect.name, prospectAddress: prospect.address };
    leadDataCache = leadDataCache;
    try {
      if (await whenFirebaseReady(4000)) await saveLeadData(prospect.name, prospect.address, data);
    } catch {}
  }

  // Auto-save a scraped/selected contact phone into the prospect's Notes (lead data).
  // Never clobbers a manual entry.
  async function persistScrapedPhone(prospect, phone) {
    const id = getLeadHash(prospect);
    const existing = leadDataCache[id] || {};
    if (existing.contactPhone && existing.contactPhone.trim() && !prospect._phoneManual) return;
    const u = $user;
    const data = {
      ownerName: existing.ownerName || '',
      contactPhone: phone,
      contactEmail: existing.contactEmail || (prospect.email && prospect.email.includes('@') ? prospect.email : ''),
      notes: existing.notes || '',
      updatedBy: u?.name || u?.display_name || 'auto-scrub',
      phoneSource: prospect._phoneManual ? 'website-confirmed' : 'website',
    };
    leadDataCache[id] = { ...existing, ...data, updatedAt: new Date().toISOString(), prospectName: prospect.name, prospectAddress: prospect.address };
    leadDataCache = leadDataCache;
    try {
      if (await whenFirebaseReady(4000)) await saveLeadData(prospect.name, prospect.address, data);
    } catch {}
  }

  // ── Shareable marketing graphics (mirrors Present.svelte) ─────────
  const SHARE_GRAPHICS = [
    { id: 'household-name', file: 'marketing/household-name.jpg', title: 'Become a Household Name' },
    { id: 'grow-your-business', file: 'marketing/grow-your-business.jpg', title: 'Grow Your Business' },
    { id: 'neighbors-customers', file: 'marketing/neighbors-customers.jpg', title: 'Turn Neighbors Into Customers' },
    { id: 'reach-local-families', file: 'marketing/reach-local-families.jpg', title: 'Reach Local Families Daily' },
    { id: 'billboard-vs-cart-cost', file: 'marketing/billboard-vs-cart-cost.jpg', title: 'Billboard vs Grocery Cart' },
    { id: 'easy-choice', file: 'marketing/easy-choice.jpg', title: 'Be the Easy Choice' },
    { id: 'fill-slow-hours', file: 'marketing/fill-slow-hours.jpg', title: 'Fill Your Slow Hours' },
    { id: 'drive-traffic-not-fees', file: 'marketing/drive-traffic-not-fees.jpg', title: 'Drive Traffic, Not 30% Fees' },
    { id: 'win-your-neighborhood', file: 'marketing/win-your-neighborhood.jpg', title: 'Win Your Neighborhood' },
    { id: 'every-customers-hand', file: 'marketing/every-customers-hand.jpg', title: "In Every Customer's Hand" },
    { id: 'register-tape-testimonial', file: 'marketing/register-tape-testimonial.jpg', title: 'Register Tape Testimonial' },
  ];
  function graphicUrl(g) {
    const origin = (typeof window !== 'undefined') ? window.location.origin : '';
    return origin + (import.meta.env.BASE_URL || '/') + g.file;
  }

  // Build the email body with optional graphic + testimonial appended.
  function composeEmailBody(tpl, prospect) {
    const rawBody = tpl._dynamic && typeof tpl.body === 'function' ? tpl.body(prospect) : tpl.body;
    let body = fillTemplate(rawBody, prospect);
    const extras = [];
    if (prospect._emailGraphic) {
      const g = SHARE_GRAPHICS.find(x => x.id === prospect._emailGraphic);
      if (g) extras.push(`Here's a quick look at how it works:\n${graphicUrl(g)}`);
    }
    if (prospect._emailTestimonial && prospect._emailTestimonialData) {
      const t = prospect._emailTestimonialData;
      const biz = (t.business_name || 'A local business').replace(/&#x27;/g, "'").replace(/&amp;/g, '&');
      const quote = (t.comments || 'Great results with IndoorMedia!').replace(/&#x27;/g, "'").replace(/&amp;/g, '&');
      let block = `What other businesses are saying:\n"${quote}"\n— ${biz}`;
      if (t.url) block += `\n${t.url}`;
      extras.push(block);
    }
    if (extras.length) {
      // Insert extras before the sign-off (last two lines: rep + IndoorMedia)
      const lines = body.split('\n');
      const signoffIdx = lines.lastIndexOf('Best,');
      const insertAt = signoffIdx > 0 ? signoffIdx : lines.length;
      const block = '\n' + extras.join('\n\n') + '\n';
      lines.splice(insertAt, 0, block);
      body = lines.join('\n');
    }
    return body;
  }

  async function toggleEmailTestimonial(prospect, checked) {
    prospect._emailTestimonial = checked;
    prospects = prospects;
    if (checked && !prospect._emailTestimonialData) {
      const list = await getTestimonialsForCategory();
      prospect._emailTestimonialData = list && list.length ? list[0] : null;
      prospects = prospects;
    }
  }

  function loadSavedProspects() {
    const saved = localStorage.getItem('savedProspects');
    savedProspects = saved ? JSON.parse(saved) : [];
    // Backfill notes from prospectNotes if saved prospect has empty notes
    let updated = false;
    savedProspects.forEach(p => {
      if (!p.notes) {
        const note = getProspectNote(p.id || p.name);
        if (note) { p.notes = note; updated = true; }
      }
    });
    if (updated) localStorage.setItem('savedProspects', JSON.stringify(savedProspects));
    // Pull cloud copy and merge so every device shows the full list
    syncProspectsFromCloud();
  }

  // Stable key for de-duping prospects across devices
  function prospectKey(p) {
    return p.id || p.placeId || (p.name && p.address ? `${p.name}|${p.address}` : p.name) || JSON.stringify(p);
  }

  // Write the current saved list to both localStorage AND Firestore (per rep)
  function persistProspects() {
    localStorage.setItem('savedProspects', JSON.stringify(savedProspects));
    const repId = $user?.id;
    if (repId) {
      // Fire-and-forget cloud write; localStorage already updated for instant UX
      whenFirebaseReady(4000).then((ready) => {
        if (ready) saveRepProspects(repId, savedProspects);
      });
    }
  }

  // Merge cloud-saved prospects into the local list (union by stable key).
  // Cloud is treated as source of truth for shared fields; newer wins by savedAt.
  async function syncProspectsFromCloud() {
    const repId = $user?.id;
    if (!repId) return;
    const ready = await whenFirebaseReady(6000);
    if (!ready) return;
    let cloud = [];
    try { cloud = await getRepProspects(repId); } catch { return; }
    if (!Array.isArray(cloud)) return;

    const byKey = new Map();
    // Seed with local first
    for (const p of savedProspects) byKey.set(prospectKey(p), p);
    // Merge cloud, preferring the more recently-updated record
    for (const c of cloud) {
      const k = prospectKey(c);
      const existing = byKey.get(k);
      if (!existing) {
        byKey.set(k, c);
      } else {
        const cT = Date.parse(c.savedAt || c.updatedAt || 0) || 0;
        const eT = Date.parse(existing.savedAt || existing.updatedAt || 0) || 0;
        byKey.set(k, cT >= eT ? { ...existing, ...c } : { ...c, ...existing });
      }
    }
    const merged = Array.from(byKey.values());
    // Only update if something actually changed (avoid loops)
    if (merged.length !== savedProspects.length || JSON.stringify(merged) !== JSON.stringify(savedProspects)) {
      savedProspects = merged;
      localStorage.setItem('savedProspects', JSON.stringify(savedProspects));
      // Push the merged superset back up so all devices converge
      saveRepProspects(repId, savedProspects);
    }
  }

  function getProspectNote(id) {
    try {
      const notes = JSON.parse(localStorage.getItem('prospectNotes') || '{}');
      return notes[id] || '';
    } catch { return ''; }
  }

  function saveProspectNote(id, text) {
    try {
      const notes = JSON.parse(localStorage.getItem('prospectNotes') || '{}');
      notes[id] = text;
      localStorage.setItem('prospectNotes', JSON.stringify(notes));
    } catch {}
    // Also sync to savedProspects if this prospect is saved
    const idx = savedProspects.findIndex(p => (p.id || p.name) === id);
    if (idx >= 0) {
      savedProspects[idx].notes = text;
      persistProspects();
    }
  }

  function getTextTemplates(prospect) {
    const bizName = prospect.name || 'your business';
    const chain = selectedStore?.GroceryChain || 'the grocery store';
    const rawStreet = selectedStore?.Address?.split(',')[0]?.trim() || '';
    const street = rawStreet.replace(/^\d+\s+/, '');
    const city = selectedStore?.City || '';
    const storeName = street && city ? `${chain} on ${street} in ${city}` : chain;
    const repName = $user?.name || $user?.first_name || '[Your Name]';
    const subcat = selectedSubcategory || selectedCategory?.replace(/^[^\s]+\s/, '') || 'business';
    return [
      { label: '🤝 Cold Intro', msg: `Hey! This is ${repName} with IndoorMedia. I work with ${storeName} — we're featuring one ${subcat.toLowerCase()} on their register tape to all their shoppers. Got 10 min this week to chat?` },
      { label: '📊 Value Drop', msg: `Hi it's ${repName} w/ IndoorMedia. We put local businesses on the register tape at ${storeName}. ${subcat}s in the area are seeing great results. Interested in hearing how it works?` },
      { label: '⏰ Follow-up', msg: `Hey just circling back — still interested in getting ${bizName} in front of all the shoppers at ${storeName}? Happy to swing by whenever works` },
      { label: '🔥 Last Spot', msg: `Hey! One ad spot left at ${storeName} this cycle — wanted to give ${bizName} first dibs before it fills. Want me to send details?` },
      { label: '🔄 Re-engage', msg: `Hey! We talked a while back about getting ${bizName} on the tape at ${storeName}. Lot of businesses have jumped on since then. Worth another look?` },
      { label: '📸 Post-Visit', msg: `Great meeting you! Here's what we talked about — featuring ${bizName} to thousands of shoppers at ${storeName}. Any questions just text me back 👍` }
    ];
  }

  function trackSearch(category, subcategory, storeName) {
    try {
      const searches = JSON.parse(localStorage.getItem('impro_searches') || '[]');
      searches.push({ category, subcategory, store: storeName, date: new Date().toISOString(), rep: $user?.name || 'Unknown' });
      localStorage.setItem('impro_searches', JSON.stringify(searches.slice(-500))); // keep last 500
    } catch (e) { console.warn('Track search error:', e); }
  }

  function trackPhoneClick(prospect) {
    try {
      const clicks = JSON.parse(localStorage.getItem('impro_phone_clicks') || '[]');
      clicks.push({ business: prospect.name, phone: prospect.phone, address: prospect.address || '', date: new Date().toISOString(), rep: $user?.name || 'Unknown' });
      localStorage.setItem('impro_phone_clicks', JSON.stringify(clicks.slice(-500)));
      phoneClicks = clicks;
      logActivity('call', { business: prospect.name, rep: $user?.name || 'Unknown' });
    } catch (e) { console.warn('Track phone click error:', e); }
  }

  // Attribution: match prospect phone clicks → contracts
  function norm(s) { return (s || '').toLowerCase().replace(/[^a-z0-9 ]/g, ' ').replace(/\s+/g, ' ').trim(); }

  function getAttribution(prospect) {
    if (!allContracts.length) return null;
    const pName = norm(prospect.name);
    const pPhone = (prospect.phone || '').replace(/\D/g, '');
    
    // Generic words to ignore in fuzzy matching
    const stopWords = new Set(['the','and','inc','llc','corp','auto','car','wash','restaurant','cafe','shop','store','bar','grill','pizza','salon','spa','dental','repair','service','services','center','east','west','north','south','new','old','big','little','great']);
    
    const pWords = pName.split(' ').filter(w => w.length > 2 && !stopWords.has(w));
    
    // Find matching contract
    const match = allContracts.find(c => {
      const cName = norm(c.business_name);
      const cPhone = (c.contact_phone || '').replace(/\D/g, '');
      
      // Phone match — must be 7+ digits and exact
      if (pPhone.length >= 7 && cPhone.length >= 7 && pPhone.slice(-7) === cPhone.slice(-7)) return true;
      
      // Exact business name match
      if (pName === cName) return true;
      
      // Substantial name overlap — require 2+ meaningful words matching AND at least 60% overlap
      const cWords = cName.split(' ').filter(w => w.length > 2 && !stopWords.has(w));
      if (pWords.length === 0 || cWords.length === 0) return false;
      const common = pWords.filter(w => cWords.some(cw => cw === w));
      return common.length >= 2 && (common.length / Math.max(pWords.length, cWords.length)) >= 0.6;
    });
    
    if (!match) return null;
    
    // Check if there's a phone click for this prospect
    const callMade = phoneClicks.find(c => {
      const cBiz = norm(c.business);
      const cWords = cBiz.split(' ').filter(w => w.length > 2 && !stopWords.has(w));
      const common = pWords.filter(w => cWords.some(cw => cw === w));
      return common.length >= 2 || pName === cBiz;
    });
    
    return { contract: match, callMade };
  }

  function saveProspect(prospect) {
    if (!savedProspects.find(p => p.id === prospect.id)) {
      // Carry over notes from prospectNotes if they exist
      const existingNote = getProspectNote(prospect.id || prospect.name);
      savedProspects = [...savedProspects, { ...prospect, savedAt: new Date().toISOString(), status: 'new', notes: existingNote || '' }];
      persistProspects();
      alert(`✅ Saved: ${prospect.name}`);
    }
  }

  function deleteProspect(id) {
    savedProspects = savedProspects.filter(p => p.id !== id);
    persistProspects();
  }

  function updateProspectNotes(id, notes) {
    const idx = savedProspects.findIndex(p => p.id === id);
    if (idx >= 0) {
      savedProspects[idx].notes = notes;
      persistProspects();
    }
    // Also sync to prospectNotes store
    try {
      const allNotes = JSON.parse(localStorage.getItem('prospectNotes') || '{}');
      allNotes[id] = notes;
      localStorage.setItem('prospectNotes', JSON.stringify(allNotes));
    } catch {}
  }

  function onProspectStoreResults(e) {
    filteredStoreResults = e.detail || [];
  }

  function selectStoreFromBrowse(store) {
    selectedStore = store;
    lookupStorePhone(store);
    storeSearchQuery = '';
    filteredStoreResults = [];
    view = 'categories';
  }

  function goBack() {
    if (view === 'results') {
      // If we opened a lead as a full card, return to its lead list
      if (prospects.length === 1 && prospects[0]?._sourceLead) {
        prospects = [];
        view = leadReturnView || 'hot-leads';
        return;
      }
      view = 'subcategories';
      selectedSubcategory = null;
    } else if (view === 'subcategories') {
      view = 'categories';
      selectedCategory = null;
    } else if (view === 'categories') {
      if (nearbyStores.length > 0) {
        view = 'nearby-stores';
      } else {
        view = 'browse-stores';
      }
      selectedStore = null;
    } else if (view === 'nearby-stores') {
      view = 'main';
      userLocation = null;
      nearbyStores = [];
    } else if (view === 'browse-stores') {
      view = 'main';
      storeSearchQuery = '';
      filteredStoreResults = [];
    } else if (view === 'saved') {
      view = 'main';
    }
  }
</script>

<div class="prospects-container">
  {#if error}
    <div class="error-box">{error}</div>
  {/if}

  {#if loading}
    <div class="loading">⏳ Searching...</div>
  {/if}

  <!-- Tab Navigation -->
  <div class="prospect-tabs">
    <button class="tab-btn" class:active={view === 'main' || view === 'browse-stores'} on:click={() => view = 'main'}>🎯 Find Prospects</button>
    <button class="tab-btn" class:active={view === 'hot-leads'} on:click={() => view = 'hot-leads'}>🔥 Hot Leads {#if hotLeads.length > 0}({hotLeads.length}){/if}</button>
    <button class="tab-btn tab-callin" class:active={view === 'call-in'} on:click={() => view = 'call-in'}>📞 Call-In Leads {#if callInLeads.length > 0}({callInLeads.length}){/if}</button>
    <button class="tab-btn" class:active={view === 'saved'} on:click={() => view = 'saved'}>💾 Saved ({savedProspects.length})</button>
    {#if isPrivilegedViewer()}
      <button class="tab-btn" class:active={view === 'team'} on:click={() => view = 'team'}>👥 Team ({teamProspects.length})</button>
    {/if}
    {#if isPrivilegedViewer()}
      <button class="tab-btn" class:active={view === 'pending'} on:click={() => view = 'pending'}>⏳ Pending</button>
      <button class="tab-btn" class:active={view === 'submit-lead'} on:click={() => view = 'submit-lead'}>➕ Add Lead</button>
    {/if}
  </div>

  <!-- Main Menu -->
  {#if view === 'main'}
    <h2>🎯 Find Prospects</h2>
    <p class="subtitle">Discover new business opportunities</p>

    <div class="button-grid">
      <a href="https://coupons.indoormedia.com/" target="_blank" class="main-btn" style="text-decoration: none; color: inherit; font-size: inherit; font-family: inherit;">
        <div class="btn-icon">📋</div>
        <div class="btn-text">Nearby Advertisers</div>
        <div class="btn-desc">See who's already advertising</div>
      </a>

      <button class="main-btn" on:click={startNearMeSearch}>
        <div class="btn-icon">📍</div>
        <div class="btn-text">Near Me</div>
        <div class="btn-desc">Find stores nearby</div>
      </button>

      <button class="main-btn" on:click={() => view = 'browse-stores'}>
        <div class="btn-icon">🏪</div>
        <div class="btn-text">Browse Stores</div>
        <div class="btn-desc">Search any store nationwide</div>
      </button>

      <button class="main-btn" on:click={() => view = 'saved'}>
        <div class="btn-icon">💾</div>
        <div class="btn-text">Saved ({savedProspects.length})</div>
        <div class="btn-desc">Your prospects</div>
      </button>

      <button class="main-btn" on:click={() => view = 'hot-leads'}>
        <div class="btn-icon">🔥</div>
        <div class="btn-text">Hot Leads</div>
        <div class="btn-desc">{hotLeads.length > 0 ? hotLeads.length + ' ready to call' : 'Coming soon'}</div>
      </button>

      <button class="main-btn" on:click={() => view = 'submit-lead'}>
        <div class="btn-icon">➕</div>
        <div class="btn-text">Add Lead</div>
        <div class="btn-desc">Submit a new lead</div>
      </button>
    </div>
  {/if}

  <!-- Browse All Stores -->
  {#if view === 'browse-stores'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>🏪 Browse Stores</h2>
    <p class="subtitle">Search any store to find prospects nearby</p>

    <div class="search-box">
      <StoreSearchInput
        stores={allStores}
        placeholder="Search by city, chain, store #, state, street, or zip..."
        maxResults={20}
        showGeo={true}
        on:select={e => selectStoreFromBrowse(e.detail)}
        on:results={onProspectStoreResults}
      />
    </div>

    {#if filteredStoreResults.length > 0}
      <div class="store-list">
        {#each filteredStoreResults as store (store.StoreName)}
          <button class="store-item" on:click={() => selectStoreFromBrowse(store)}>
            <div class="store-info">
              <h4>{store.GroceryChain}</h4>
              <p class="address">{store.City}, {store.State}</p>
              <p class="store-addr-detail">{store.Address}</p>
            </div>
            <div class="store-right">
              <div class="store-num">{store.StoreName}</div>
              <div class="store-cycle">Cycle {store.Cycle || '?'}</div>
              {#if store['Case Count']}<div class="store-cases">📦 {store['Case Count']} cases</div>{/if}
              {#if store._dist !== undefined}<div class="store-distance">📍 {store._dist.toFixed(1)} mi</div>{/if}
            </div>
          </button>
        {/each}
      </div>
    {:else if storeSearchQuery.trim()}
      <p class="empty-msg">No stores found for "{storeSearchQuery}"</p>
    {:else}
      <p class="empty-msg">Type to search 7,835+ stores or use address/GPS</p>
    {/if}
  {/if}

  <!-- Nearby Stores List -->
  {#if view === 'nearby-stores'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>📍 Nearby Stores</h2>
    <p class="subtitle">Select a store to find prospects nearby</p>

    <div class="cycle-filter">
      <button class="cycle-btn" class:active={selectedCycle === 'all'} on:click={() => selectedCycle = 'all'}>All</button>
      <button class="cycle-btn" class:active={selectedCycle === 'A'} on:click={() => selectedCycle = 'A'}>Cycle A</button>
      <button class="cycle-btn" class:active={selectedCycle === 'B'} on:click={() => selectedCycle = 'B'}>Cycle B</button>
      <button class="cycle-btn" class:active={selectedCycle === 'C'} on:click={() => selectedCycle = 'C'}>Cycle C</button>
    </div>

    <div class="store-list">
      {#each nearbyStores.filter(s => selectedCycle === 'all' || s.Cycle === selectedCycle) as store (store.StoreName)}
        {@const claim = storeClaims[store.StoreName]}
        <div class="store-item-wrap" class:store-claimed={!!claim}>
          <button class="store-item" on:click={() => selectStore(store)}>
            <div class="store-info">
              <h4>{store.GroceryChain}</h4>
              {#if store.Address}
                <p class="street-address">📍 {store.Address.split(',')[0]}</p>
              {/if}
              <p class="address">{store.City}, {store.State}</p>
              <p class="distance">{store.distance.toFixed(1)} miles away</p>
              {#if store['Case Count']}
                <p class="case-count">📦 {store['Case Count']} cases on shelf</p>
              {/if}
            </div>
            <div class="store-right">
              <div class="store-num">{store.StoreName}</div>
              <div class="store-cycle">Cycle {store.Cycle || '?'}</div>
            </div>
          </button>
          {#if claim}
            <div class="dibs-badge">
              <span>🔒 {shortName(claim.repName)} — dibs through Sat</span>
              {#if canReleaseClaim(claim)}
                <button class="dibs-release" on:click|stopPropagation={() => handleStoreRelease(store.StoreName)} disabled={claimLoading[store.StoreName]}>✕</button>
              {/if}
            </div>
          {:else}
            <button class="dibs-claim-btn" on:click|stopPropagation={() => handleStoreClaim(store)} disabled={claimLoading[store.StoreName]}>
              {claimLoading[store.StoreName] ? '⏳' : '🎯 Claim'}
            </button>
          {/if}
        </div>
      {/each}
    </div>
  {/if}

  <!-- Category Selection -->
  {#if view === 'categories'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h3>📍 {selectedStore.GroceryChain} - {selectedStore.City}, {selectedStore.State}</h3>
    {#if selectedStore._phone}
      <p class="store-phone-display"><a href="tel:{selectedStore._phone}">📞 {selectedStore._phone}</a></p>
    {:else if selectedStore._phoneLoading}
      <p class="store-phone-display" style="color:#999;">📞 Looking up store phone...</p>
    {/if}
    <p class="subtitle">Search by name or choose a category</p>



    <div class="custom-search-bar">
      <input 
        type="text" 
        bind:value={customSearch} 
        placeholder="Search business name or keyword..."
        on:keydown={(e) => e.key === 'Enter' && searchCustom()}
      />
      <button class="search-go-btn" on:click={searchCustom} disabled={!customSearch.trim() || loading}>
        {loading ? '...' : '🔍'}
      </button>
    </div>

    {#if loadedCustomers}
      <div class="loaded-customers-section">
        <h3>📊 Current/Past Customers</h3>
        
        {#if loadedCustomers.current.length > 0}
          <div class="customers-subsection">
            <h4 style="color: #2e7d32;">🟢 Current Customers ({loadedCustomers.current.length})</h4>
            {#each loadedCustomers.current as customer}
              <div class="customer-card current">
                <div class="customer-name">{customer.businessName}</div>
                <div class="customer-meta">
                  <span>📅 Started: {new Date(customer.startDate).toLocaleDateString()}</span>
                  {#if customer.endDate}
                    <span>📅 Ended: {new Date(customer.endDate).toLocaleDateString()}</span>
                  {:else}
                    <span style="color: #2e7d32; font-weight: 600;">• Active</span>
                  {/if}
                </div>
                <div class="customer-details">
                  <span>{customer.category}</span> • <span>{customer.contractType}</span>
                </div>
                {#if customer.totalSpent}
                  <div class="customer-revenue">💰 Total Revenue: ${customer.totalSpent.toLocaleString()}</div>
                {/if}
              </div>
            {/each}
          </div>
        {/if}
        
        {#if loadedCustomers.past.length > 0}
          <div class="customers-subsection">
            <h4 style="color: #c33;">🔴 Past Customers ({loadedCustomers.past.length})</h4>
            {#each loadedCustomers.past as customer}
              <div class="customer-card past">
                <div class="customer-name">{customer.businessName}</div>
                <div class="customer-meta">
                  <span>📅 {new Date(customer.startDate).toLocaleDateString()} → {new Date(customer.endDate).toLocaleDateString()}</span>
                </div>
                <div class="customer-details">
                  <span>{customer.category}</span> • <span>{customer.contractType}</span>
                </div>
                {#if customer.totalSpent}
                  <div class="customer-revenue">💰 Total Revenue: ${customer.totalSpent.toLocaleString()}</div>
                {/if}
              </div>
            {/each}
          </div>
        {/if}
      </div>
    {/if}

    <p class="or-divider">— or pick a category —</p>

    <button class="new-biz-banner" on:click={searchNewBusinesses}>
      🆕 New Businesses
      <span class="new-biz-hint">Opened in the last year near this store</span>
    </button>

    <div class="category-grid">
      {#each Object.keys(CATEGORIES) as cat}
        <button class="category-btn" on:click={() => selectCategory(cat)}>
          {cat}
        </button>
      {/each}
    </div>
  {/if}

  <!-- Subcategory Selection -->
  {#if view === 'subcategories'}
    <button class="back-btn" on:click={goBack}>← {selectedCategory}</button>
    <h3>Choose a type</h3>

    <div class="subcat-grid">
      {#each CATEGORIES[selectedCategory] as subcat}
        <button class="subcat-btn" on:click={() => selectSubcategory(subcat)}>
          {subcat}
        </button>
      {/each}
    </div>
  {/if}

  <!-- Prospect Results -->
  {#if view === 'results'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h3>{selectedCategory} → {selectedSubcategory}</h3>
    <p class="subtitle">Nearby {selectedCategory} near {selectedStore.GroceryChain}</p>

    <div class="prospect-toolbar">
      <div class="sort-bar">
        <span class="sort-label">Sort:</span>
        <button class="sort-btn" class:active={prospectSort === 'score'} on:click={() => prospectSort = 'score'}>🎯 Score</button>
        <button class="sort-btn" class:active={prospectSort === 'distance'} on:click={() => prospectSort = 'distance'}>📍 Distance</button>
        <button class="sort-btn" class:active={prospectSort === 'rating'} on:click={() => prospectSort = 'rating'}>⭐ Rating</button>
        <button class="sort-btn" class:active={prospectSort === 'reviews'} on:click={() => prospectSort = 'reviews'}>💬 Reviews</button>
      </div>
    </div>

    {#if true}
    <div class="prospect-list">
      {#each [...prospects].sort((a, b) => {
        if (prospectSort === 'distance') return (a.distance || 999) - (b.distance || 999);
        if (prospectSort === 'rating') return (b.rating || 0) - (a.rating || 0);
        if (prospectSort === 'reviews') return (b.reviews || 0) - (a.reviews || 0);
        return (b.score || 0) - (a.score || 0);
      }) as prospect, i (prospect.id + '-' + i)}
        <div class="prospect-card">
          <div class="prospect-header">
            <span class="score-emoji">{prospect.score >= 80 ? '🔥' : prospect.score >= 70 ? '⭐' : '👀'}</span>
            <h4>{prospect.name}</h4>
          </div>
          <p class="prospect-address" style="cursor:pointer;" on:click={() => { navigator.clipboard.writeText(prospect.address); copiedAddress = prospect.address; setTimeout(() => copiedAddress = '', 2000); }}>📍 {copiedAddress === prospect.address ? '✅ Copied!' : prospect.address}</p>
          <p class="prospect-meta">
            ⭐ {prospect.rating.toFixed(1)} ({prospect.reviews} reviews) • {prospect.distance} mi • Score: {prospect.score}%
          </p>
          {#if prospect.phone}
            <p class="prospect-phone">📞 <a href="tel:{prospect.phone}" style="color:inherit;text-decoration:none;">{prospect.phone}</a></p>
          {/if}
          {#if prospect.email}
            <p class="prospect-email">📧 <a href="mailto:{prospect.email}" style="color:inherit;text-decoration:none;">{prospect.email}</a></p>
          {/if}
          {#if prospect.hours && prospect.hours.length > 0}
            {@const today = new Date().toLocaleDateString('en-US', { weekday: 'long' })}
            {@const todayHours = prospect.hours.find(h => h.startsWith(today))}
            <p class="prospect-hours" on:click|stopPropagation={() => { prospect._showAllHours = !prospect._showAllHours; prospects = prospects; }}>
              🕐 {todayHours || prospect.hours[0]}
            </p>
            {#if prospect._showAllHours}
              <div class="hours-detail">
                {#each prospect.hours as h}
                  <p class="hours-line" class:today-line={h.startsWith(today)}>{h}</p>
                {/each}
              </div>
            {/if}
          {/if}
          <!-- Lead Claim Badge -->
          {#if getLeadClaim(prospect)}
            {@const lc = getLeadClaim(prospect)}
            <div class="lead-claim-badge">
              🔒 {shortName(lc.repName)} — dibs through {new Date(lc.expiresAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              {#if canReleaseLeadClaim(lc)}
                <button class="release-lead-btn" on:click|stopPropagation={() => handleLeadRelease(prospect)}>✕</button>
              {/if}
            </div>
          {/if}

          <div class="prospect-actions">
            <!-- Row 1: Contact -->
            <div class="action-row">
              {#if prospect.phone}
                <a href="tel:{prospect.phone}" class="action-btn btn-green" on:click={() => { trackPhoneClick(prospect); handleLeadAction(prospect, 'call'); }}>📞 Call</a>
                <button class="action-btn btn-blue" on:click={() => { prospect._showText = !prospect._showText; prospect._showEmail = false; prospect._showScript = false; prospect._showNotes = false; prospects = prospects; handleLeadAction(prospect, 'text'); }}>💬 Text</button>
              {/if}
              <button class="action-btn btn-purple" on:click={() => { prospect._showEmail = !prospect._showEmail; prospect._showText = false; prospect._showScript = false; prospect._showNotes = false; prospects = prospects; if (prospect._showEmail) { ensureProspectEmail(prospect); if (!prospect._research && !prospect._researching) { prospect._researching = true; researchProspect(prospect).finally(() => { prospect._researching = false; prospects = prospects; }); } handleLeadAction(prospect, 'email'); } }}>✉️ Email</button>
              <button class="action-btn btn-orange" on:click={() => { handleLeadAction(prospect, 'walk-in'); }}>🚶 Walk-In</button>
            </div>

            <!-- Last contact activity -->
            {#if getLastActivity(prospect)}
              {@const la = getLastActivity(prospect)}
              {@const lm = activityMeta(la.action)}
              <button class="last-activity" on:click|stopPropagation={() => openActivityLog(prospect)} title="View full activity log">
                <span class="la-icon">{lm.icon}</span>
                <span class="la-text">{lm.label}{#if la.rep} by {shortName(la.rep)}{/if} · {timeAgo(la.at)}</span>
                <span class="la-more">Log ›</span>
              </button>
            {:else}
              <button class="last-activity la-empty" on:click|stopPropagation={() => openActivityLog(prospect)} title="View activity log">
                <span class="la-icon">🕒</span>
                <span class="la-text">No contact logged yet</span>
                <span class="la-more">Log ›</span>
              </button>
            {/if}

            <!-- Row 2: Research -->
            <div class="action-row">
              {#if prospect.website}
                <a href={prospect.website} target="_blank" class="action-btn btn-gray">🌐 Website</a>
              {/if}
              <button class="action-btn btn-gray" on:click={() => saveProspect(prospect)}>💾 Save</button>
              <button class="action-btn btn-gray" on:click={() => { prospect._showNotes = !prospect._showNotes; prospects = prospects; }}>📝 Notes</button>
            </div>

            <!-- Row 3: Sales tools -->
            <div class="action-row">
              <button class="action-btn btn-outline" on:click={() => { prospect._showScript = !prospect._showScript; prospect._showEmail = false; prospect._showNotes = false; prospects = prospects; }}>📋 Scripts</button>
              <button class="action-btn btn-outline" on:click={async () => { 
                prospect._showTestimonials = !prospect._showTestimonials;
                if (prospect._showTestimonials) {
                  prospect._testimonialData = await getTestimonialsForCategory();
                }
                prospects = prospects;
              }}>⭐ Testimonials</button>
            </div>

            <!-- Big Book Appointment -->
            <div class="invite-row">
              <select bind:value={inviteRepEmail} class="invite-select">
                <option value="">No invite (just me)</option>
                {#each Object.entries(repRegistry).filter(([k, v]) => v.email) as [id, rep]}
                  <option value={rep.email}>{rep.display_name || rep.contract_name}</option>
                {/each}
              </select>
            </div>
            <a href="https://calendar.google.com/calendar/render?action=TEMPLATE&text={encodeURIComponent('Visit: ' + prospect.name)}&details={encodeURIComponent('Prospect: ' + prospect.name + '\nAddress: ' + prospect.address + (prospect.phone ? '\nPhone: ' + prospect.phone : '') + (prospect.website ? '\nWebsite: ' + prospect.website : '') + '\nStore: ' + (selectedStore?.GroceryChain || '') + ' ' + (selectedStore?.StoreName || '') + '\nRep: ' + ($user?.name || '') + (getProspectNote(prospect.id || prospect.name) ? '\n\n📝 Notes:\n' + getProspectNote(prospect.id || prospect.name) : ''))}&location={encodeURIComponent(prospect.address)}&add={encodeURIComponent('tyler.vansant@indoormedia.com')}{inviteRepEmail ? ',' + encodeURIComponent(inviteRepEmail) : ''}" target="_blank" class="action-btn btn-book-appt">📅 Book Appointment{inviteRepEmail ? ' (+ rep)' : ''}</a>
            {#if prospect.address}
              <a href="https://maps.apple.com/?daddr={encodeURIComponent(prospect.address)}" target="_blank" class="action-btn btn-navigate">🗺️ Navigate</a>
            {/if}
            {#if prospect.lat && prospect.lng}
              <button class="action-btn btn-showmap" on:click={() => { prospect._showMap = !prospect._showMap; prospects = prospects; }}>
                {prospect._showMap ? '✕ Close Map' : '📍 Show on Map'}
              </button>
            {/if}
            <button class="action-btn btn-meeting-prep" on:click={() => runMeetingPrep(prospect)}>🎯 Run Meeting Prep</button>
          </div>

          {#if prospect._showMap && prospect.lat && prospect.lng}
            <div class="prospect-minimap" use:initMiniMap={{ prospect, store: selectedStore }}></div>
          {/if}

          {#if prospect._showText}
            <div class="text-templates-section">
              <h4 class="text-templates-title">💬 Text Templates</h4>
              <p class="text-templates-hint">Tap to copy, then paste into your text. Or tap "Send" to open SMS.</p>
              {#each getTextTemplates(prospect) as template}
                <div class="text-template-card">
                  <div class="text-template-label">{template.label}</div>
                  <div class="text-template-msg">{template.msg}</div>
                  <div class="text-template-actions">
                    <button class="text-copy-btn" on:click|stopPropagation={() => { navigator.clipboard.writeText(template.msg); prospect._copiedText = template.label; prospects = prospects; setTimeout(() => { prospect._copiedText = ''; prospects = prospects; }, 2000); }}>
                      {prospect._copiedText === template.label ? '✅ Copied!' : '📋 Copy'}
                    </button>
                    {#if prospect.phone}
                      <a href="sms:{prospect.phone}?body={encodeURIComponent(template.msg)}" class="text-send-btn">📱 Send</a>
                    {/if}
                  </div>
                </div>
              {/each}
            </div>
          {/if}
          {#if prospect._showTestimonials}
            <div class="testimonials-section">
              <h4 class="testimonials-title">📋 Testimonials for {selectedSubcategory || selectedCategory || 'this category'}</h4>
              <a class="video-testimonials-link" href="https://youtube.com/playlist?list=PLjTXw9VlAiGP7cKVD_F1rPWERnmjeDCB1&si=oXd6wcbA6uUTCkSs" target="_blank" rel="noopener" on:click|stopPropagation>▶️ Video Testimonials (YouTube playlist)</a>
              {#if prospect._testimonialData && prospect._testimonialData.length > 0}
                {#each prospect._testimonialData as testimonial}
                  <div class="testimonial-card" class:local-testimonial={testimonial._isLocal} class:clickable-testimonial={testimonial.url} on:click|stopPropagation={() => { if (testimonial.url) window.open(testimonial.url, '_blank'); }} role={testimonial.url ? 'link' : undefined}>
                    {#if testimonial._isLocal}
                      <p class="local-badge">📍 Nearby Business</p>
                    {/if}
                    <p class="testimonial-business"><strong>{(testimonial.business_name || 'Business').replace(/&#x27;/g, "'").replace(/&#x9;/g, '').replace(/&amp;/g, '&')}</strong></p>
                    <p class="testimonial-text">"{testimonial.comments || 'Great experience with IndoorMedia!'}"</p>
                    {#if testimonial.url}
                      <p class="testimonial-tap-hint">Tap to view on IndoorMedia ↗</p>
                    {/if}
                  </div>
                {/each}
              {:else}
                <p class="no-testimonials">No testimonials found for this category. Try a broader category.</p>
              {/if}
            </div>
          {/if}
          {#if prospect._showNotes}
            {@const ldHash = getLeadHash(prospect)}
            {@const ld = leadDataCache[ldHash] || {}}
            {#if canSeePrivate(ld)}
            <div class="notes-section">
              <label class="lead-field-label">👤 Owner / Decision Maker</label>
              <input 
                type="text" 
                class="lead-field-input"
                placeholder="Owner or decision maker name..."
                value={ld.ownerName || ''}
                on:input={(e) => handleSaveLeadData(prospect, 'ownerName', e.target.value)}
                on:blur={(e) => handleSaveLeadData(prospect, 'ownerName', e.target.value)}
              />
              <label class="lead-field-label">📱 Contact Phone</label>
              <input 
                type="tel" 
                class="lead-field-input"
                placeholder="Contact phone number..."
                value={ld.contactPhone || ''}
                on:input={(e) => handleSaveLeadData(prospect, 'contactPhone', e.target.value)}
                on:blur={(e) => handleSaveLeadData(prospect, 'contactPhone', e.target.value)}
              />
              <label class="lead-field-label">📧 Contact Email</label>
              <input 
                type="email" 
                class="lead-field-input"
                placeholder="Contact email address..."
                autocomplete="email"
                value={ld.contactEmail || ''}
                on:input={(e) => handleSaveLeadData(prospect, 'contactEmail', e.target.value)}
                on:blur={(e) => handleSaveLeadData(prospect, 'contactEmail', e.target.value)}
              />
              <label class="lead-field-label">📝 Notes</label>
              <textarea 
                placeholder="Add notes about this prospect..." 
                rows="3"
                value={ld.notes || getProspectNote(prospect.id || prospect.name)}
                on:input={(e) => { saveProspectNote(prospect.id || prospect.name, e.target.value); handleSaveLeadData(prospect, 'notes', e.target.value); }}
                on:blur={(e) => handleSaveLeadData(prospect, 'notes', e.target.value)}
              ></textarea>
              {#if ld.updatedBy}
                <p class="note-saved">Updated by {ld.updatedBy} on {new Date(ld.updatedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</p>
              {:else if getProspectNote(prospect.id || prospect.name)}
                <p class="note-saved">Saved locally</p>
              {/if}
            </div>
            {:else}
            {@const sharedStatus = getSharedStatus(prospect)}
            <div class="notes-section notes-private">
              {#if sharedStatus}
                <span class="status-badge status-{sharedStatus.toLowerCase()}">{sharedStatus}</span>
              {/if}
              <p class="note-private-msg">🔒 Contact details and notes for this prospect are private to {ld.updatedBy || 'the rep working it'}.</p>
            </div>
            {/if}
          {/if}
          {#if prospect._showScript}
            <!-- CALL SCRIPTS FEATURE - LIVE AS OF MAR 30 2026 -->
            <div class="script-section">
              <h4 class="script-title">📋 Call Scripts</h4>
              <button class="script-select-btn" on:click={() => { prospect._selectedScript = 'tvs-appt'; prospects = prospects; }}>
                📞 TVS Appointment Setting
              </button>
              <button class="script-select-btn" on:click={() => { prospect._selectedScript = 'tvs-spanish'; prospects = prospects; }}>
                📞 Spanish Appointment Setting
              </button>
              {#if prospect._selectedScript === 'tvs-appt'}
                <div class="script-preview-box">
                  <p class="script-label">🚪 Opener</p>
                  <p class="script-text">Hey there, I was hoping you could point me in the right direction…</p>
                  <p class="script-text">My name is <strong>{$user?.name || $user?.first_name || '[Your Name]'}</strong> and I am working with the <strong>{selectedStore?.GroceryChain || '[Store]'}</strong> store down the road{#if selectedStore?.Address} on <strong>{selectedStore.Address.split(',')[0]}</strong>{/if}.</p>
                  <p class="script-text">Reason for the visit is we're kicking off a big promotion over at the store and will be featuring and recommending just a few local businesses to all their customers.</p>
                  <p class="script-text">We see huge success for other businesses like yours and some of your neighbors as well <em>(give examples if you have them)</em>.</p>
                  <p class="script-text"><em>Who should I talk to about doing the same for your business?</em></p>

                  <p class="script-label">✅ If it's the decision-maker</p>
                  <p class="script-text">Oh perfect — what I'd like to do is schedule a brief meeting to learn more about your business, share what we do for similar local businesses, and most importantly what we could do for you.</p>
                  <p class="script-text">I can be back in about 15 minutes or at ____. Which works best for you?</p>
                  <p class="script-text">Great! And I'm sure you're going to love it. If for some reason you don't, you have no problem just telling me no, right?</p>
                  <p class="script-text">But on the other hand, when you love it like I predict — <em>is there anyone else who needs to see my program in order to say yes?</em></p>

                  <p class="script-reminder">⚠️ <strong>Reminder:</strong> Schedule for a time that fits all parties (including any other decision-makers).</p>

                  <p class="script-label">💡 Coaching Notes</p>
                  <ul class="script-notes">
                    <li>Pattern interrupt + social proof opens the door without a hard pitch.</li>
                    <li>"Be back in 15 minutes or at ____" is an assumptive close — keep it confident.</li>
                    <li>"You have no problem telling me no, right?" lowers resistance (tie-down).</li>
                    <li>The decision-maker question is the money line. Don't skip it — it prevents wasted closes where the buyer says "I need to check with my partner."</li>
                  </ul>

                  <button class="action-btn full-width" on:click={() => {
                    const rep = $user?.name || $user?.first_name || '[Your Name]';
                    const store = selectedStore?.GroceryChain || '[Store]';
                    const script = `TVS COLD WALK-IN / APPOINTMENT SETTING\n\n— OPENER —\nHey there, I was hoping you could point me in the right direction…\n\nMy name is ${rep} and I am working with the ${store} store down the road.\n\nReason for the visit is we're kicking off a big promotion over at the store and will be featuring and recommending just a few local businesses to all their customers.\n\nWe see huge success for other businesses like yours and some of your neighbors as well (give examples if you have them).\n\nWho should I talk to about doing the same for your business?\n\n— IF IT'S THE DECISION-MAKER —\nOh perfect — what I'd like to do is schedule a brief meeting to learn more about your business, share what we do for similar local businesses, and most importantly what we could do for you.\n\nI can be back in about 15 minutes or at ____. Which works best for you?\n\nGreat! And I'm sure you're going to love it. If for some reason you don't, you have no problem just telling me no, right?\n\nBut on the other hand, when you love it like I predict — is there anyone else who needs to see my program in order to say yes?\n\n⚠️ REMINDER: Schedule for a time that fits all parties (including any other decision-makers).`;
                    navigator.clipboard.writeText(script);
                    alert('✅ Script copied!');
                  }}>📋 Copy Script</button>
                </div>
              {/if}
              {#if prospect._selectedScript === 'tvs-spanish'}
                <div class="script-preview-box">
                  <p class="script-text">Hola, ¿podría orientarme un poco con algo?</p>
                  <p class="script-text">Me llamo <strong>{$user?.name || $user?.first_name || '[Su nombre]'}</strong> y le llamaba porque estoy trabajando con la cadena <strong>{selectedStore?.GroceryChain || '[Nombre de la cadena]'}</strong> —ubicada en <strong>{selectedStore?.Address?.split(',')[0] || '[Dirección]'}</strong>—; me ponía en contacto con usted porque estamos poniendo en marcha una gran promoción para apoyar a los negocios locales.</p>
                  <p class="script-text">Vamos a destacar y recomendar a un grupo selecto de excelentes negocios de la zona y, en este momento, busco recomendar a un único negocio del sector <strong>{selectedSubcategory || selectedCategory || '[Tipo de negocio]'}</strong> a todos sus clientes.</p>
                  <p class="script-text">Ya trabajamos con una gran cantidad de negocios de la categoría <strong>{selectedSubcategory || selectedCategory || '[Tipo de negocio]'}</strong>, logrando un enorme éxito a la hora de atraerles clientes; por ello, me preguntaba: <em>¿con quién debería hablar para hacer lo mismo por ustedes?</em></p>
                  <button class="action-btn full-width" on:click={() => {
                    const script = `Hola, ¿podría orientarme un poco con algo?\n\nMe llamo ${$user?.name || $user?.first_name || '[Su nombre]'} y le llamaba porque estoy trabajando con la cadena ${selectedStore?.GroceryChain || '[Nombre de la cadena]'} —ubicada en ${selectedStore?.Address?.split(',')[0] || '[Dirección]'}—; me ponía en contacto con usted porque estamos poniendo en marcha una gran promoción para apoyar a los negocios locales.\n\nVamos a destacar y recomendar a un grupo selecto de excelentes negocios de la zona y, en este momento, busco recomendar a un único negocio del sector ${selectedSubcategory || selectedCategory || '[Tipo de negocio]'} a todos sus clientes.\n\nYa trabajamos con una gran cantidad de negocios de la categoría ${selectedSubcategory || selectedCategory || '[Tipo de negocio]'}, logrando un enorme éxito a la hora de atraerles clientes; por ello, me preguntaba: ¿con quién debería hablar para hacer lo mismo por ustedes?`;
                    navigator.clipboard.writeText(script);
                    alert('✅ Script copied!');
                  }}>📋 Copy Script</button>
                </div>
              {/if}
            </div>
          {/if}
          {#if prospect._showEmail}
            {@const tplList = getEmailTemplatesFor()}
            <div class="email-section">
              <!-- Email-address status / scrub -->
              <div class="email-to-row">
                {#if prospect._emailScraping}
                  <span class="email-to-status scraping">🔍 {prospect._emailDeep ? 'Deep-combing' : 'Scanning'} {prospect.name}'s website for an email…</span>
                {:else if prospect.email && prospect.email.includes('@')}
                  <span class="email-to-status found">✉️ To: <strong>{prospect.email}</strong>{#if prospect._emailScraped} <em>(found on website — saved to Notes)</em>{/if}</span>
                {:else}
                  <span class="email-to-status missing">⚠️ No email on file{#if prospect._emailScrapeFailed} (couldn't find one on their site){/if} — add one in 📝 Notes, or send to yourself to forward.</span>
                {/if}
                {#if prospect.website && !prospect._emailScraping}
                  {#if !(prospect.email && prospect.email.includes('@'))}
                    <button class="email-scrub-btn" on:click={() => { prospect._emailScrapeTried = false; prospect._emailScrapeFailed = false; ensureProspectEmail(prospect); }}>🔍 Find Email</button>
                  {/if}
                  <button class="email-scrub-btn deep" on:click={() => ensureProspectEmail(prospect, { deep: true, force: true })}>🕵️ Deep comb</button>
                {/if}
              </div>
              {#if prospect._emailCandidates && prospect._emailCandidates.length > 1 && !prospect._emailScraping}
                <div class="email-alt-row">
                  <span class="email-alt-label">Other addresses found:</span>
                  {#each prospect._emailCandidates as cand}
                    {#if cand !== prospect.email}
                      <button class="email-alt-btn" on:click={() => chooseProspectEmail(prospect, cand)}>{cand}</button>
                    {/if}
                  {/each}
                </div>
              {/if}
              {#if !prospect._emailScraping && (prospect._scrapedOwner || (leadDataCache[getLeadHash(prospect)]?.ownerName))}
                {@const savedOwner = leadDataCache[getLeadHash(prospect)]?.ownerName}
                <div class="owner-found-row">
                  <span class="owner-found-status">👤 Owner: <strong>{savedOwner || prospect._scrapedOwner}</strong>{#if prospect._ownerScraped && !prospect._ownerManual} <em>(found on website — saved to Notes)</em>{/if}</span>
                </div>
                {#if prospect._ownerCandidates && prospect._ownerCandidates.length > 1}
                  <div class="email-alt-row">
                    <span class="email-alt-label">Other names found:</span>
                    {#each prospect._ownerCandidates as nm}
                      {#if nm !== (savedOwner || prospect._scrapedOwner)}
                        <button class="email-alt-btn" on:click={() => chooseProspectOwner(prospect, nm)}>{nm}</button>
                      {/if}
                    {/each}
                  </div>
                {/if}
              {/if}
              {#if !prospect._emailScraping && (prospect._scrapedPhone || (leadDataCache[getLeadHash(prospect)]?.contactPhone))}
                {@const savedPhone = leadDataCache[getLeadHash(prospect)]?.contactPhone}
                <div class="owner-found-row">
                  <span class="owner-found-status">📞 Direct/other #: <strong><a href="tel:{savedPhone || prospect._scrapedPhone}" style="color:inherit;">{savedPhone || prospect._scrapedPhone}</a></strong>{#if prospect._phoneScraped && !prospect._phoneManual} <em>(found on website — saved to Notes)</em>{/if}</span>
                </div>
                {#if prospect._phoneCandidates && prospect._phoneCandidates.length > 1}
                  <div class="email-alt-row">
                    <span class="email-alt-label">Other numbers found:</span>
                    {#each prospect._phoneCandidates as ph}
                      {#if ph !== (savedPhone || prospect._scrapedPhone)}
                        <button class="email-alt-btn" on:click={() => chooseProspectPhone(prospect, ph)}>{ph}</button>
                      {/if}
                    {/each}
                  </div>
                {/if}
              {/if}

              <h4 class="email-title">Choose a template:</h4>
              {#each tplList as tpl}
                <button class="email-tpl-btn" class:featured-tpl={tpl._featured} class:cat-tpl={tpl._categoryLabel} class:prog-tpl={tpl._programLabel} on:click={() => { prospect._selectedTpl = tpl.id; if (tpl._dynamic && !prospect._research && !prospect._researching) { prospect._researching = true; researchProspect(prospect).finally(() => { prospect._researching = false; prospects = prospects; }); } prospects = prospects; }}>
                  {tpl.icon} {tpl.name}{#if tpl._featured} <span class="featured-badge">⭐ Best</span>{/if}{#if tpl._categoryLabel} <span class="cat-badge">{tpl._categoryLabel}</span>{/if}{#if tpl._programLabel} <span class="prog-badge">{tpl._programLabel}</span>{/if}
                </button>
              {/each}
              {#if prospect._selectedTpl}
                {@const tpl = tplList.find(t => t.id === prospect._selectedTpl) || tplList[0]}

                <!-- Add-ons: graphic + testimonial -->
                <div class="email-addons">
                  <label class="email-addon-toggle">
                    <input type="checkbox" checked={prospect._emailTestimonial} on:change={(e) => toggleEmailTestimonial(prospect, e.target.checked)} />
                    ⭐ Include a testimonial
                  </label>
                  <div class="email-graphic-picker">
                    <span class="email-addon-label">🖼️ Attach a graphic (link):</span>
                    <select bind:value={prospect._emailGraphic} on:change={() => prospects = prospects} class="email-graphic-select">
                      <option value={undefined}>None</option>
                      {#each SHARE_GRAPHICS as g}
                        <option value={g.id}>{g.title}</option>
                      {/each}
                    </select>
                  </div>
                  {#if prospect._emailGraphic}
                    {@const g = SHARE_GRAPHICS.find(x => x.id === prospect._emailGraphic)}
                    {#if g}<img class="email-graphic-thumb" src={graphicUrl(g)} alt={g.title} loading="lazy" />{/if}
                  {/if}
                </div>

                <div class="email-preview-box">
                  {#if tpl._dynamic && prospect._researching}
                    <p class="email-research-hint">🔍 Researching {prospect.name}’s website to personalize this email… (you can send now; it’ll sharpen once done)</p>
                  {:else if tpl._dynamic && prospect._research && !prospect._research.empty}
                    <p class="email-research-hint done">✅ Personalized using details from {prospect.name}’s website</p>
                  {/if}
                  <p class="email-subject">Subject: {fillTemplate(tpl.subject, prospect)}</p>
                  <p class="email-body-text">{composeEmailBody(tpl, prospect)}</p>
                  <button class="action-btn full-width email-btn" on:click={() => {
                    const subject = encodeURIComponent(fillTemplate(tpl.subject, prospect));
                    const rawBody = composeEmailBody(tpl, prospect);
                    const body = encodeURIComponent(rawBody.replace(/\n\n/g, '\r\n\r\n').replace(/(?<!\r)\n/g, '\r\n'));
                    window.open('mailto:' + (prospect.email || '') + '?subject=' + subject + '&body=' + body);
                  }}>📧 Open in Email App</button>
                  <button class="action-btn full-width email-btn-secondary" on:click={() => {
                    navigator.clipboard.writeText(composeEmailBody(tpl, prospect));
                    prospect._emailCopied = true; prospects = prospects;
                    setTimeout(() => { prospect._emailCopied = false; prospects = prospects; }, 2000);
                  }}>{prospect._emailCopied ? '✅ Copied!' : '📋 Copy Email'}</button>
                </div>
              {/if}
            </div>
          {/if}
        </div>
      {/each}
    </div>
    {/if}
  {/if}

  <!-- Team Prospects (Manager View) -->
  {#if view === 'team'}
    <button class="back-btn" on:click={() => view = 'main'}>← Back</button>
    <h2>👥 Team Prospects ({teamProspects.length})</h2>
    <p class="subtitle">All reps' saved prospects &amp; notes</p>

    {#if teamProspects.length === 0}
      <p class="subtitle">No team prospect data found.</p>
    {:else}
      <input type="text" class="filter-input" placeholder="Search all team prospects..." bind:value={teamSearch} style="margin-bottom:12px;" />
      <div class="filter-chips" style="margin-bottom:8px;">
        <select class="filter-select" bind:value={teamRepFilter} style="flex:1; padding:8px; border-radius:8px; border:1px solid var(--border-color, #ddd); font-size:14px; font-weight:600;">
          <option value="all">All Reps ({teamProspects.length})</option>
          {#each [...new Set(teamProspects.map(p => p.rep_name).filter(n => n && n !== 'Unknown' && n !== '?'))].sort() as rep}
            <option value={rep}>{rep} ({teamProspects.filter(p => p.rep_name === rep).length})</option>
          {/each}
        </select>
      </div>
      <div class="filter-chips" style="margin-bottom:12px;">
        <button class="chip" class:active={teamStatusFilter === 'all'} on:click={() => teamStatusFilter = 'all'}>All</button>
        <button class="chip" class:active={teamStatusFilter === 'new'} on:click={() => teamStatusFilter = 'new'}>🆕 New</button>
        <button class="chip" class:active={teamStatusFilter === 'interested'} on:click={() => teamStatusFilter = 'interested'}>🎯 Interested</button>
        <button class="chip" class:active={teamStatusFilter === 'follow-up'} on:click={() => teamStatusFilter = 'follow-up'}>⏳ Follow-up</button>
        <button class="chip" class:active={teamStatusFilter === 'contacted'} on:click={() => teamStatusFilter = 'contacted'}>📞 Contacted</button>
        <button class="chip" class:active={teamStatusFilter === 'proposal'} on:click={() => teamStatusFilter = 'proposal'}>📋 Proposal</button>
        <button class="chip" class:active={teamStatusFilter === 'closed'} on:click={() => teamStatusFilter = 'closed'}>🎉 Closed</button>
      </div>

      <div class="prospect-list">
        {#each teamProspects.filter(p => {
          if (teamRepFilter !== 'all' && p.rep_name !== teamRepFilter) return false;
          if (teamStatusFilter !== 'all' && p.status !== teamStatusFilter) return false;
          if (teamSearch) {
            const q = teamSearch.toLowerCase();
            return (p.name || '').toLowerCase().includes(q) || (p.address || '').toLowerCase().includes(q) || (p.notes || '').toLowerCase().includes(q) || (p.rep_name || '').toLowerCase().includes(q);
          }
          return true;
        }) as prospect (prospect.id)}
          <div class="prospect-card saved-card" class:expanded={expandedTeam === prospect.id}>
            <div class="saved-header" on:click={() => expandedTeam = expandedTeam === prospect.id ? null : prospect.id}>
              <div>
                <h4>{prospect.name || 'Unknown'}</h4>
                <p class="saved-addr">{prospect.address || ''}</p>
                {#if prospect.phone}
                  <p class="saved-meta">📞 {prospect.phone}</p>
                {/if}
                <p class="saved-meta" style="color: var(--accent-color, #CC0000); font-weight: 600;">👤 {prospect.rep_name}</p>
              </div>
              <div class="saved-right">
                <span class="status-badge status-{prospect.status}">{prospect.status === 'new' ? '🆕' : prospect.status === 'interested' ? '🎯' : prospect.status === 'follow-up' ? '⏳' : prospect.status === 'contacted' ? '📞' : prospect.status === 'proposal' ? '📋' : '🎉'} {prospect.status || 'new'}</span>
                <span class="expand-arrow">{expandedTeam === prospect.id ? '▲' : '▼'}</span>
              </div>
            </div>

            {#if expandedTeam === prospect.id}
              <div class="saved-actions">
                <div class="action-row">
                  {#if prospect.phone}
                    <a href="tel:{prospect.phone}" class="action-btn">📞 Call</a>
                    <a href="sms:{prospect.phone}" class="action-btn text-btn">💬 Text</a>
                  {/if}
                  {#if prospect.email}
                    <a href="mailto:{prospect.email}" class="action-btn">✉️ Email</a>
                  {/if}
                  <a href="https://maps.google.com/maps?q={encodeURIComponent((prospect.name || '') + ' ' + (prospect.address || ''))}" target="_blank" class="action-btn">📍 Maps</a>
                </div>

                <div class="saved-contact-info">
                  {#if prospect.phone}<p>📞 <a href="tel:{prospect.phone}">{prospect.phone}</a></p>{/if}
                  {#if prospect.email}<p>✉️ <a href="mailto:{prospect.email}">{prospect.email}</a></p>{/if}
                  {#if prospect.contact_name}<p>👤 Contact: {prospect.contact_name}</p>{/if}
                  {#if prospect.rating}<p>⭐ {prospect.rating} ({prospect.reviews || 0} reviews)</p>{/if}
                  {#if prospect.score}<p>🎯 Score: {prospect.score}%</p>{/if}
                  <p>📅 Saved: {prospect.saved_date ? new Date(prospect.saved_date).toLocaleDateString() : 'N/A'}</p>
                  {#if prospect.last_contacted}<p>📞 Last Contact: {new Date(prospect.last_contacted).toLocaleDateString()}</p>{/if}
                </div>

                {#if prospect.notes}
                  <div class="notes-section" style="margin-top:8px;">
                    <p class="tmpl-label">📝 Notes:</p>
                    <div style="background: var(--bg-secondary, #f5f5f5); padding: 10px; border-radius: 8px; font-size: 13px; white-space: pre-wrap;">{prospect.notes}</div>
                  </div>
                {/if}
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  {/if}

  <!-- Saved Prospects -->
  {#if view === 'saved'}
    <button class="back-btn" on:click={() => view = 'main'}>← Back</button>
    <h2>💾 Saved Prospects ({savedProspects.length})</h2>

    {@const totalCalls = phoneClicks.length}
    {@const conversions = savedProspects.filter(p => getAttribution(p)).length}
    {#if totalCalls > 0 || conversions > 0}
      <div class="attribution-summary">
        <div class="attr-stat">
          <span class="attr-value">{totalCalls}</span>
          <span class="attr-label">Calls Made</span>
        </div>
        <div class="attr-stat">
          <span class="attr-value">{savedProspects.length}</span>
          <span class="attr-label">Saved</span>
        </div>
        <div class="attr-stat highlight">
          <span class="attr-value">{conversions}</span>
          <span class="attr-label">Converted ✅</span>
        </div>
        {#if totalCalls > 0 && conversions > 0}
          <div class="attr-stat">
            <span class="attr-value">{Math.round(conversions / totalCalls * 100)}%</span>
            <span class="attr-label">Close Rate</span>
          </div>
        {/if}
      </div>
    {/if}

    {#if savedProspects.length === 0}
      <p class="subtitle">No saved prospects yet. Start searching!</p>
    {:else}
      <input type="text" class="filter-input" placeholder="Search saved prospects..." bind:value={savedSearch} style="margin-bottom:12px;" />
      <div class="filter-chips" style="margin-bottom:12px;">
        <button class="chip" class:active={savedStatusFilter === 'all'} on:click={() => savedStatusFilter = 'all'}>All ({savedProspects.length})</button>
        <button class="chip" class:active={savedStatusFilter === 'new'} on:click={() => savedStatusFilter = 'new'}>🆕 New</button>
        <button class="chip" class:active={savedStatusFilter === 'contacted'} on:click={() => savedStatusFilter = 'contacted'}>⏳ Contacted</button>
        <button class="chip" class:active={savedStatusFilter === 'proposal'} on:click={() => savedStatusFilter = 'proposal'}>📋 Proposal</button>
        <button class="chip" class:active={savedStatusFilter === 'closed'} on:click={() => savedStatusFilter = 'closed'}>🎉 Closed</button>
      </div>
      <div class="prospect-list">
        {#each savedProspects.filter(p => {
          if (savedStatusFilter !== 'all' && p.status !== savedStatusFilter) return false;
          if (savedSearch) {
            const q = savedSearch.toLowerCase();
            return (p.name || '').toLowerCase().includes(q) || (p.address || '').toLowerCase().includes(q) || (p.notes || '').toLowerCase().includes(q);
          }
          return true;
        }) as prospect (prospect.id)}
          {@const attribution = getAttribution(prospect)}
          {@const callCount = phoneClicks.filter(c => norm(c.business).includes(norm(prospect.name).split(' ')[0]) && norm(prospect.name).split(' ').length > 0).length}
          <div class="prospect-card saved-card" class:expanded={expandedSaved === prospect.id} class:converted={attribution}>
            <!-- Attribution banner -->
            {#if attribution}
              <div class="attribution-banner">
                ✅ CONTRACT SIGNED — {attribution.contract.business_name} | ${(attribution.contract.total_amount || 0).toLocaleString()} | {attribution.contract.sales_rep}
                {#if attribution.callMade}
                  <span class="call-tracked">📞 Call tracked {new Date(attribution.callMade.date).toLocaleDateString()}</span>
                {/if}
              </div>
            {/if}
            <!-- Header (always visible) -->
            <div class="saved-header" on:click={() => expandedSaved = expandedSaved === prospect.id ? null : prospect.id}>
              <div>
                <h4>{prospect.name}</h4>
                <p class="saved-addr">{prospect.address || ''}</p>
                {#if prospect.phone}
                  <p class="saved-meta">📞 {prospect.phone} {#if callCount > 0}<span class="call-count">({callCount} call{callCount > 1 ? 's' : ''} made)</span>{/if}</p>
                {/if}
              </div>
              <div class="saved-right">
                <span class="status-badge status-{prospect.status}">{prospect.status === 'new' ? '🆕' : prospect.status === 'contacted' ? '⏳' : prospect.status === 'proposal' ? '📋' : '🎉'} {prospect.status}</span>
                <span class="expand-arrow">{expandedSaved === prospect.id ? '▲' : '▼'}</span>
              </div>
            </div>

            <!-- Expanded actions -->
            {#if expandedSaved === prospect.id}
              <div class="saved-actions">
                <!-- Quick actions row -->
                <div class="action-row">
                  {#if prospect.phone}
                    <a href="tel:{prospect.phone}" class="action-btn" on:click={() => trackPhoneClick(prospect)}>📞 Call</a>
                    <a href="sms:{prospect.phone}" class="action-btn text-btn">💬 Text</a>
                  {/if}
                  {#if prospect.email}
                    <a href="mailto:{prospect.email}" class="action-btn">✉️ Email</a>
                  {/if}
                  <a href="https://maps.google.com/maps?q={encodeURIComponent(prospect.name + ' ' + (prospect.address || ''))}" target="_blank" class="action-btn">📍 Maps</a>
                  {#if prospect.website}
                    <a href={prospect.website} target="_blank" class="action-btn">🌐 Web</a>
                  {/if}
                </div>

                <!-- Contact info -->
                <div class="saved-contact-info">
                  {#if prospect.phone}
                    <p>📞 <a href="tel:{prospect.phone}">{prospect.phone}</a></p>
                  {/if}
                  {#if prospect.email}
                    <p>✉️ <a href="mailto:{prospect.email}">{prospect.email}</a></p>
                  {/if}
                  {#if prospect.website}
                    <p>🌐 <a href={prospect.website} target="_blank">{prospect.website.replace('https://','').split('/')[0]}</a></p>
                  {/if}
                  {#if prospect.rating}
                    <p>⭐ {prospect.rating} ({prospect.reviews || 0} reviews)</p>
                  {/if}
                  <p class="saved-addr-copy" on:click={() => { navigator.clipboard.writeText(prospect.address); copiedAddress = prospect.address; setTimeout(() => copiedAddress = '', 2000); }}>
                    📋 {copiedAddress === prospect.address ? '✅ Copied!' : 'Copy address'}
                  </p>
                </div>

                <!-- Email templates -->
                <div class="saved-email-templates">
                  <p class="tmpl-label">📧 Email Templates:</p>
                  <div class="tmpl-btns">
                    {#each [
                      { id: 'intro', icon: '🎯', name: 'Initial Appointment' },
                      { id: 'roi', icon: '📊', name: 'ROI / Value' },
                      { id: 'followup', icon: '⏰', name: 'Follow-up' },
                      { id: 'reengagement', icon: '🔄', name: 'Re-engagement' },
                      { id: 'limited', icon: '⚡', name: 'Limited Time' }
                    ] as tpl}
                      <button class="tmpl-btn" on:click|stopPropagation={() => {
                        const templates = {
                          intro: { subject: `Partnership Opportunity — ${prospect.name}`, body: `Hi,\n\nI noticed ${prospect.name} near one of our grocery store partners and wanted to reach out about a great advertising opportunity.\n\nWe help local businesses reach thousands of shoppers each week through register tape advertising. It's affordable, hyper-local, and puts your name directly in customers' hands.\n\nWould you have 10 minutes this week for a quick chat?\n\nBest,\n${$user?.name || 'Your Rep'}\nIndoorMedia` },
                          roi: { subject: `The Value of Register Tape Advertising — ${prospect.name}`, body: `Hi,\n\nDid you know the average grocery store gets 10,000+ visitors per week? That's 10,000 potential customers seeing your ad every single week.\n\nBusinesses like yours have reported strong ROI — many seeing results within the first month. Our register tape ads put your name, offer, and location directly in shoppers' hands.\n\nI'd love to show you how the numbers work for ${prospect.name}. Can we schedule a quick call?\n\nBest,\n${$user?.name || 'Your Rep'}\nIndoorMedia` },
                          followup: { subject: `Following Up — ${prospect.name}`, body: `Hi,\n\nI reached out a few days ago about a potential partnership with ${prospect.name} and wanted to follow up.\n\nWe help local businesses reach thousands of nearby shoppers each week through register tape advertising. I think there's a great fit here.\n\nWould you have 10 minutes this week for a quick chat?\n\nBest,\n${$user?.name || 'Your Rep'}\nIndoorMedia` },
                          reengagement: { subject: `New Opportunities for ${prospect.name}`, body: `Hi,\n\nIt's been a while since we last connected, and I wanted to reach out. We've been growing our grocery store network and there are some exciting new opportunities in your area.\n\nI'd love to share how ${prospect.name} could benefit from being in front of thousands of local shoppers every week.\n\nWhen would be a good time for a quick 5-minute call?\n\nBest,\n${$user?.name || 'Your Rep'}\nIndoorMedia` },
                          limited: { subject: `Limited Availability — Ad Space Near ${prospect.name}`, body: `Hi,\n\nI wanted to reach out because we have limited ad space available at a grocery store near ${prospect.name}. These spots fill quickly and your business would be a great fit.\n\nRegister tape advertising puts your name, offer, and contact info directly in the hands of every shopper — hundreds per day.\n\nCan I send you a quick overview of the opportunity?\n\nBest,\n${$user?.name || 'Your Rep'}\nIndoorMedia` }
                        };
                        const t = templates[tpl.id];
                        const body = t.body.replace(/\n\n/g, '\r\n\r\n').replace(/(?<!\r)\n/g, '\r\n');
                        window.open(`mailto:${prospect.email || ''}?subject=${encodeURIComponent(t.subject)}&body=${encodeURIComponent(body)}`);
                      }}>{tpl.icon} {tpl.name}</button>
                    {/each}
                  </div>
                </div>

                <!-- Schedule -->
                <div class="saved-schedule">
                  <p class="tmpl-label">📅 Schedule:</p>
                  <div class="tmpl-btns">
                    <button class="tmpl-btn" on:click|stopPropagation={() => {
                      const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1); tomorrow.setHours(10,0,0,0);
                      const end = new Date(tomorrow); end.setMinutes(30);
                      const fmt = d => d.toISOString().replace(/[-:]/g,'').split('.')[0]+'Z';
                      window.open(`https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent('📞 Call: ' + prospect.name)}&dates=${fmt(tomorrow)}/${fmt(end)}&details=${encodeURIComponent('Prospect call\nBusiness: ' + prospect.name + '\nPhone: ' + (prospect.phone||'N/A') + '\nAddress: ' + (prospect.address||''))}&add=${encodeURIComponent('tyler.vansant@indoormedia.com')}`, '_blank');
                    }}>📞 Schedule Call</button>
                    <button class="tmpl-btn" on:click|stopPropagation={() => {
                      const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1); tomorrow.setHours(10,0,0,0);
                      const end = new Date(tomorrow); end.setHours(11);
                      const fmt = d => d.toISOString().replace(/[-:]/g,'').split('.')[0]+'Z';
                      window.open(`https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent('🚗 Visit: ' + prospect.name)}&dates=${fmt(tomorrow)}/${fmt(end)}&details=${encodeURIComponent('Prospect visit\nBusiness: ' + prospect.name + '\nPhone: ' + (prospect.phone||'N/A'))}&location=${encodeURIComponent(prospect.address||'')}&add=${encodeURIComponent('tyler.vansant@indoormedia.com')}`, '_blank');
                    }}>🚗 Schedule Visit</button>
                  </div>
                </div>

                <!-- Nearby advertisers -->
                <a href="https://coupons.indoormedia.com/?location={encodeURIComponent(prospect.address || '')}" target="_blank" class="nearby-btn">📋 View Nearby Advertisers</a>

                <!-- Status + Notes -->
                <div class="saved-status-row">
                  <select class="status-select" value={prospect.status} on:change={(e) => { prospect.status = e.target.value; updateProspectNotes(prospect.id, prospect.notes); savedProspects = savedProspects; persistProspects(); }}>
                    <option value="new">🆕 New</option>
                    <option value="contacted">⏳ Contacted</option>
                    <option value="proposal">📋 Proposal</option>
                    <option value="closed">🎉 Closed</option>
                  </select>
                  <button class="delete-btn" on:click={() => deleteProspect(prospect.id)}>🗑️ Delete</button>
                </div>
                {#each [leadDataCache[getLeadHash(prospect)] || {}] as savedLd}
                {#if canSeePrivate(savedLd)}
                <label class="lead-field-label">👤 Owner / Decision Maker</label>
                <input 
                  type="text" 
                  class="lead-field-input"
                  placeholder="Owner or decision maker name..."
                  value={savedLd.ownerName || ''}
                  on:input={(e) => handleSaveLeadData(prospect, 'ownerName', e.target.value)}
                  on:blur={(e) => handleSaveLeadData(prospect, 'ownerName', e.target.value)}
                />
                <label class="lead-field-label">📱 Contact Phone</label>
                <input 
                  type="tel" 
                  class="lead-field-input"
                  placeholder="Contact phone number..."
                  value={savedLd.contactPhone || ''}
                  on:input={(e) => handleSaveLeadData(prospect, 'contactPhone', e.target.value)}
                  on:blur={(e) => handleSaveLeadData(prospect, 'contactPhone', e.target.value)}
                />
                <label class="lead-field-label">📝 Notes</label>
                <textarea placeholder="Add notes..." class="notes-input" 
                  value={savedLd.notes || prospect.notes || ''} 
                  on:input={(e) => { updateProspectNotes(prospect.id, e.target.value); handleSaveLeadData(prospect, 'notes', e.target.value); }}
                  on:blur={(e) => handleSaveLeadData(prospect, 'notes', e.target.value)}
                ></textarea>
                {#if savedLd.updatedBy}
                  <p class="note-saved">Updated by {savedLd.updatedBy}</p>
                {/if}
                {:else}
                {@const sharedStatus = getSharedStatus(prospect)}
                {#if sharedStatus}
                  <span class="status-badge status-{sharedStatus.toLowerCase()}">{sharedStatus}</span>
                {/if}
                <p class="note-private-msg">🔒 Private to {savedLd.updatedBy || 'the rep working it'}.</p>
                {/if}
                {/each}
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  {/if}

  <!-- Hot Leads Section -->
  {#if view === 'hot-leads'}
    <div class="hot-leads-section">
      <button class="back-btn" on:click={() => view = 'main'}>← Back</button>
      <h2>🔥 Hot Leads ({filteredHotLeads.length})</h2>
      
      <div class="filter-bar">
        <input type="text" placeholder="Search business, address, city..." bind:value={hotLeadSearch} class="filter-input" />
      </div>
      <div class="filter-row">
        <select bind:value={hotLeadZoneFilter} class="filter-select">
          <option value="all">All Zones</option>
          {#each hotLeadZones as zone}
            <option value={zone}>{zone}</option>
          {/each}
        </select>
        <select bind:value={hotLeadRepFilter} class="filter-select">
          <option value="all">All Reps</option>
          {#each hotLeadReps as rep}
            <option value={rep}>{rep}</option>
          {/each}
        </select>
        <select bind:value={hotLeadStoreFilter} class="filter-select">
          <option value="all">All Stores</option>
          {#each hotLeadStores as store}
            <option value={store}>{store}</option>
          {/each}
        </select>
        <select bind:value={hotLeadCategoryFilter} class="filter-select">
          <option value="all">All Categories</option>
          {#each hotLeadCategories as cat}
            <option value={cat}>{cat}</option>
          {/each}
        </select>
      </div>

      {#if filteredHotLeads.length === 0}
        <div class="empty-state">
          <p>{hotLeads.length === 0 ? 'No Hot Leads assigned to you yet. Check back soon!' : 'No leads match your filters.'}</p>
        </div>
      {:else}
        <div class="hot-leads-grid">
          {#each filteredHotLeads as lead}
            <div class="hot-lead-card clickable-card" on:click={() => openLeadAsProspect(lead)}>
              <div class="lead-header">
                <h4>{lead.business_name}</h4>
                {#if lead.rating}
                  <span class="rating">⭐{lead.rating}</span>
                {/if}
              </div>
              <div class="lead-cat-row">
                <span class="lead-category">{lead.category}</span>
                {#if lead.generated_at}
                  <span class="lead-date">📅 {fmtLeadDate(lead.generated_at)}</span>
                {/if}
              </div>
              {#if lead._hook}
                <div class="lead-hook">"{lead._hook}"</div>
              {/if}
              <div class="lead-contact">
                {#if lead.phone}
                  <a href="tel:{lead.phone}" class="phone" on:click|stopPropagation>📞 {lead.phone}</a>
                {/if}
                {#if lead._email || lead.website}
                  <a href="mailto:{lead._email || ''}" class="email" on:click|stopPropagation>📧 Email</a>
                {/if}
              </div>
              {#if lead.address}
                <div class="lead-address" style="cursor:pointer;" on:click|stopPropagation={() => { navigator.clipboard.writeText(lead.address); copiedAddress = lead.address; setTimeout(() => copiedAddress = '', 2000); }}>📍 {copiedAddress === lead.address ? '✅ Copied!' : lead.address}</div>
              {/if}
              <div class="lead-store">{lead.store_chain} {lead.store_city} ({lead.store_id})</div>
              <button class="open-full-btn" on:click|stopPropagation={() => openLeadAsProspect(lead)}>Open full card →</button>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}

  <!-- Call-In Leads (inbound, always shown, not cycle-filtered) -->
  {#if view === 'call-in'}
    <div class="hot-leads-section callin-section">
      <button class="back-btn" on:click={() => view = 'main'}>← Back</button>
      <h2>📞 Call-In Leads ({filteredCallInLeads.length})</h2>
      <p class="callin-subtitle">Inbound leads — these people called us. Reach out fast! 🔥</p>

      <div class="filter-bar">
        <input type="text" placeholder="Search business, caller, city, zip..." bind:value={callInSearch} class="filter-input" />
      </div>

      {#if filteredCallInLeads.length === 0}
        <div class="empty-state">
          <p>{callInLeads.length === 0 ? 'No call-in leads yet. New ones import automatically each morning.' : 'No call-in leads match your search.'}</p>
        </div>
      {:else}
        <div class="hot-leads-grid">
          {#each filteredCallInLeads as lead}
            <div class="hot-lead-card callin-card clickable-card" on:click={() => openLeadAsProspect(lead)}>
              <div class="lead-header">
                <h4>{lead.business_name}</h4>
                {#if lead.rating}
                  <span class="rating">⭐{lead.rating}</span>
                {/if}
              </div>
              <div class="callin-badge-row">
                <span class="callin-badge">📞 CALLED IN</span>
                {#if lead.call_in_date}
                  <span class="callin-date">📅 {fmtLeadDate(lead.call_in_date)}</span>
                {/if}
                <span class="lead-category callin-cat">{lead.subcategory || 'Lead'}</span>
                {#if callInAssignedName(lead)}
                  <span class="callin-assigned-badge">🎯 {callInAssignedName(lead)}</span>
                {:else if isPrivilegedViewer()}
                  <span class="callin-unassigned-badge">⚪ Unassigned</span>
                {/if}
              </div>
              {#if isPrivilegedViewer()}
                <div class="callin-assign-row" on:click|stopPropagation>
                  <label class="callin-assign-label">Assign to:</label>
                  <select
                    class="callin-assign-select"
                    value={(callInAssignments[callInLeadKey(lead)] || {}).repId || ''}
                    on:change={(e) => handleAssignCallIn(lead, e.target.value)}
                    on:click|stopPropagation
                  >
                    <option value="">— Unassigned —</option>
                    {#each repRoster as r}
                      <option value={r.id}>{r.name}</option>
                    {/each}
                  </select>
                </div>
              {/if}
              {#if lead.contact_name}
                <div class="callin-contact-name">👤 {lead.contact_name}</div>
              {/if}
              {#if lead.lead_comments}
                <div class="lead-hook callin-comments">“{lead.lead_comments}”</div>
              {/if}
              <div class="lead-contact">
                {#if lead.phone}
                  <a href="tel:{lead.phone}" class="phone" on:click|stopPropagation>📞 {lead.phone}</a>
                {/if}
                {#if lead._email}
                  <a href="mailto:{lead._email}" class="email" on:click|stopPropagation>📧 {lead._email}</a>
                {/if}
              </div>
              {#if lead.address}
                <div class="lead-address" style="cursor:pointer;" on:click|stopPropagation={() => { navigator.clipboard.writeText(lead.address); copiedAddress = lead.address; setTimeout(() => copiedAddress = '', 2000); }}>📍 {copiedAddress === lead.address ? '✅ Copied!' : lead.address}</div>
              {/if}
              <div class="callin-store">
                🏪 Target store: <strong>{lead.store_chain} {lead.store_city}</strong> ({lead.store_id}){#if lead.distance_mi != null} · {lead.distance_mi} mi{/if}
              </div>
              <div class="callin-meta">Zip {lead.lead_zip}{#if lead.website} · <a href={lead.website} target="_blank" rel="noopener" on:click|stopPropagation>website</a>{/if}{#if lead._research_note} · <em>{lead._research_note}</em>{/if}</div>
              <button class="open-full-btn callin-open" on:click|stopPropagation={() => openLeadAsProspect(lead)}>Open full card →</button>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}

  <!-- Pending Leads (Manager only) -->
  {#if view === 'pending' && ($user?.role === 'manager' || $user?.name?.toLowerCase().includes('tyler'))}
    <div class="pending-section">
      <button class="back-btn" on:click={() => view = 'main'}>← Back</button>
      <PendingLeads />
    </div>
  {/if}

  <!-- Submit Lead -->
  {#if view === 'submit-lead'}
    <div class="submit-section">
      <button class="back-btn" on:click={() => view = 'main'}>← Back</button>
      <HotLeadsSubmit user={$user} onLeadSubmitted={() => view = 'main'} />
    </div>
  {/if}

  <!-- Meeting Prep overlay (launched from a prospect card) -->
  {#if meetingPrepProspect}
    <div class="meeting-prep-overlay" on:click|self={() => meetingPrepProspect = null}>
      <div class="meeting-prep-modal">
        <button class="mp-close" on:click={() => meetingPrepProspect = null}>✕ Close</button>
        <MeetingPrep prefill={meetingPrepProspect} onBack={() => meetingPrepProspect = null} />
      </div>
    </div>
  {/if}

  <!-- Full activity-log modal -->
  {#if activityLogProspect}
    {@const entries = getActivityEntries(activityLogProspect)}
    <div class="activity-log-overlay" on:click|self={closeActivityLog}>
      <div class="activity-log-modal">
        <button class="al-close" on:click={closeActivityLog}>✕</button>
        <h3 class="al-title">📋 Activity Log</h3>
        <p class="al-sub">{activityLogProspect.name}</p>
        {#if entries.length}
          <div class="al-list">
            {#each entries as e}
              {@const m = activityMeta(e.action)}
              <div class="al-item">
                <span class="al-item-icon">{m.icon}</span>
                <div class="al-item-body">
                  <div class="al-item-line">
                    <strong>{m.label}</strong>{#if e.rep} by {shortName(e.rep)}{/if}
                    {#if e.detail}<span class="al-detail"> — {e.detail}</span>{/if}
                  </div>
                  <div class="al-item-time">{new Date(e.at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })} · {timeAgo(e.at)}</div>
                </div>
              </div>
            {/each}
          </div>
        {:else}
          <p class="al-empty-msg">No contact activity logged yet. Tapping Call, Text, Email, or Walk-In will start the log.</p>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  /* Last-contact activity line under the action buttons */
  .last-activity {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    margin: 6px 0 2px;
    padding: 7px 10px;
    background: #f1f8f4;
    border: 1px solid #cde9d6;
    border-radius: 8px;
    font-size: 0.82rem;
    color: #256b43;
    cursor: pointer;
    text-align: left;
  }
  .last-activity:active { transform: scale(0.99); }
  .last-activity.la-empty { background: #f5f5f5; border-color: #e0e0e0; color: #888; }
  .la-icon { font-size: 0.95rem; }
  .la-text { flex: 1; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .la-more { font-weight: 700; opacity: 0.7; font-size: 0.78rem; }
  :global([data-theme='dark']) .last-activity { background: #1b3a2a; border-color: #2e6b47; color: #a5e3bd; }
  :global([data-theme='dark']) .last-activity.la-empty { background: #2a2a2a; border-color: #444; color: #999; }

  /* Full activity-log modal */
  .activity-log-overlay {
    position: fixed; inset: 0; z-index: 1000;
    background: rgba(0,0,0,0.5);
    display: flex; align-items: center; justify-content: center;
    padding: 16px;
  }
  .activity-log-modal {
    position: relative;
    background: #fff;
    border-radius: 14px;
    width: 100%; max-width: 440px;
    max-height: 80vh; overflow-y: auto;
    padding: 20px 18px 18px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.3);
  }
  :global([data-theme='dark']) .activity-log-modal { background: #1e1e1e; color: #eee; }
  .al-close {
    position: absolute; top: 12px; right: 12px;
    background: none; border: none; font-size: 1.2rem; cursor: pointer; color: #999;
  }
  .al-title { margin: 0 0 2px; font-size: 1.1rem; }
  .al-sub { margin: 0 0 14px; color: #777; font-size: 0.9rem; }
  :global([data-theme='dark']) .al-sub { color: #aaa; }
  .al-list { display: flex; flex-direction: column; gap: 10px; }
  .al-item { display: flex; gap: 10px; padding: 8px 0; border-bottom: 1px solid #eee; }
  :global([data-theme='dark']) .al-item { border-color: #333; }
  .al-item-icon { font-size: 1.1rem; line-height: 1.4; }
  .al-item-body { flex: 1; }
  .al-item-line { font-size: 0.9rem; }
  .al-detail { color: #666; }
  :global([data-theme='dark']) .al-detail { color: #bbb; }
  .al-item-time { font-size: 0.78rem; color: #999; margin-top: 2px; }
  .al-empty-msg { color: #888; font-size: 0.9rem; text-align: center; padding: 20px 8px; }

  .meeting-prep-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    z-index: 2000;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding: 12px;
    overflow-y: auto;
  }
  .meeting-prep-modal {
    background: #fff;
    border-radius: 14px;
    width: 100%;
    max-width: 640px;
    margin: 20px auto 40px;
    padding: 12px;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
    position: relative;
  }
  .mp-close {
    position: sticky;
    top: 0;
    margin-left: auto;
    display: block;
    background: #ef4444;
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
    font-weight: 700;
    cursor: pointer;
    z-index: 5;
  }
  .btn-meeting-prep {
    background: #6366f1;
    color: #fff;
    border: none;
  }
  .video-testimonials-link {
    display: block;
    background: linear-gradient(135deg, #dc2626, #b91c1c);
    color: #fff;
    text-decoration: none;
    font-weight: 700;
    text-align: center;
    padding: 10px 12px;
    border-radius: 10px;
    margin: 4px 0 12px;
    font-size: 14px;
  }
  .prospect-tabs {
    display: flex;
    gap: 8px;
    margin: 0 0 20px 0;
    overflow-x: auto;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--border-color);
  }

  .tab-btn {
    background: none;
    border: none;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    color: #999;
    border-bottom: 3px solid transparent;
    transition: all 0.2s;
    white-space: nowrap;
  }

  .tab-btn.active {
    color: #CC0000;
    border-bottom-color: #CC0000;
  }

  .tab-btn:hover {
    color: #333;
  }

  .toggle-btn {
    background: var(--input-bg, #f5f5f5);
    border: 2px solid var(--border-color, #ddd);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    color: var(--text-secondary, #666);
    transition: all 0.2s;
    white-space: nowrap;
  }

  .toggle-btn:hover {
    background: var(--border-color, #e8e8e8);
  }

  .toggle-btn.active {
    background: #CC0000;
    color: white;
    border-color: #CC0000;
  }

  .filter-bar { margin-top: 12px; }
  .filter-input { width: 100%; padding: 10px 14px; border: 2px solid var(--border-color, #ddd); border-radius: 10px; font-size: 14px; background: var(--input-bg, white); color: var(--text-primary, #333); box-sizing: border-box; }
  .filter-row { display: flex; gap: 8px; margin-top: 8px; flex-wrap: wrap; }
  .filter-select { flex: 1; min-width: 120px; padding: 8px 10px; border: 2px solid var(--border-color, #ddd); border-radius: 8px; font-size: 13px; background: var(--input-bg, white); color: var(--text-primary, #333); }
  .lead-address { font-size: 12px; color: var(--text-tertiary, #999); margin-top: 4px; }

  .hot-leads-section, .pending-section, .submit-section {
    margin-top: 20px;
  }

  .roogle-load-btn {
    background: linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    width: 100%;
    margin-bottom: 16px;
    transition: all 0.2s;
  }

  .roogle-load-btn:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px #2e7d324d;
  }

  .roogle-load-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .customer-load-msg {
    background: #e8f5e9;
    border: 1px solid #81c784;
    border-radius: 6px;
    padding: 12px;
    margin-bottom: 16px;
    font-size: 13px;
    color: #2e7d32;
    font-weight: 600;
    text-align: center;
  }

  .credentials-modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
  }

  .credentials-modal {
    background: white;
    border-radius: 16px;
    padding: 28px;
    max-width: 400px;
    width: 100%;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  }

  .credentials-modal h3 {
    color: #333;
    margin: 0 0 4px;
    font-size: 22px;
  }

  .modal-subtitle {
    color: #666;
    margin: 0 0 20px;
    font-size: 14px;
  }

  .credentials-modal .form-group {
    margin-bottom: 16px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .credentials-modal label {
    color: #333;
    font-size: 13px;
    font-weight: 600;
  }

  .credentials-modal input {
    border: 2px solid #ddd;
    border-radius: 8px;
    padding: 12px;
    font-size: 14px;
    font-family: inherit;
  }

  .credentials-modal input:focus {
    border-color: #CC0000;
    outline: none;
    box-shadow: 0 0 0 3px rgba(204, 0, 0, 0.1);
  }

  .modal-actions {
    display: flex;
    gap: 12px;
    margin-top: 24px;
  }

  .btn-load {
    flex: 1;
    background: #CC0000;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-load:hover {
    background: #990000;
  }

  .btn-cancel {
    flex: 1;
    background: #f0f0f0;
    color: #333;
    border: none;
    border-radius: 8px;
    padding: 12px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  }

  .btn-cancel:hover {
    background: #e0e0e0;
  }

  .modal-note {
    color: #999;
    font-size: 12px;
    margin-top: 12px;
    text-align: center;
  }

  .loaded-customers-section {
    background: #f9f9f9;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 24px;
    border: 2px solid #e0e0e0;
  }

  .loaded-customers-section h3 {
    color: #333;
    margin: 0 0 16px;
    font-size: 16px;
  }

  .customers-subsection {
    margin-bottom: 16px;
  }

  .customers-subsection h4 {
    margin: 0 0 12px;
    font-size: 14px;
  }

  .customer-card {
    background: white;
    border-left: 4px solid #e0e0e0;
    border-radius: 6px;
    padding: 12px;
    margin-bottom: 8px;
    font-size: 13px;
  }

  .customer-card.current {
    border-left-color: #2e7d32;
    background: #f0f8f4;
  }

  .customer-card.past {
    border-left-color: #c33;
    background: #fff5f5;
    opacity: 0.85;
  }

  .customer-name {
    font-weight: 600;
    color: #333;
    margin-bottom: 6px;
    font-size: 14px;
  }

  .customer-meta {
    color: #666;
    margin-bottom: 4px;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    font-size: 12px;
  }

  .customer-details {
    color: #999;
    font-size: 11px;
  }

  .customer-revenue {
    color: #2e7d32;
    font-weight: 600;
    font-size: 13px;
    margin-top: 6px;
    padding-top: 6px;
    border-top: 1px solid rgba(46, 125, 50, 0.2);
  }

  .customer-card.past .customer-revenue {
    color: #666;
  }

  /* Text Templates */
  .text-templates-section {
    background: #f0f7ff;
    border-radius: 10px;
    padding: 14px;
    margin-top: 10px;
  }
  :global([data-theme='dark']) .text-templates-section { background: #1a2332; }
  .text-templates-title { font-size: 15px; font-weight: 700; margin: 0 0 4px; color: var(--text-primary); }
  .text-templates-hint { font-size: 12px; color: var(--text-secondary); margin: 0 0 12px; }
  .text-template-card {
    background: var(--card-bg, white);
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 10px;
    border: 1px solid var(--border-color, #e0e0e0);
  }
  :global([data-theme='dark']) .text-template-card { background: #1e1e1e; border-color: #333; }
  .text-template-label { font-size: 13px; font-weight: 700; margin-bottom: 6px; color: var(--text-primary); }
  .text-template-msg { font-size: 14px; line-height: 1.5; color: var(--text-secondary); margin-bottom: 10px; white-space: pre-wrap; }
  .text-template-actions { display: flex; gap: 8px; }
  .text-copy-btn {
    flex: 1;
    padding: 8px 12px;
    border-radius: 8px;
    border: 1.5px solid #2563EB;
    background: white;
    color: #2563EB;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    text-align: center;
  }
  .text-copy-btn:active { background: #2563EB; color: white; }
  :global([data-theme='dark']) .text-copy-btn { background: #1e1e1e; border-color: #5b9aff; color: #5b9aff; }
  .text-send-btn {
    flex: 1;
    padding: 8px 12px;
    border-radius: 8px;
    border: none;
    background: #2563EB;
    color: white;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    text-align: center;
    text-decoration: none;
  }
  .text-send-btn:active { background: #1d4ed8; }

  .testimonials-section {
    background: #f9f9f9;
    border-radius: 10px;
    padding: 14px;
    margin-top: 10px;
    border: 1px solid #e0e0e0;
  }

  .testimonials-title {
    margin: 0 0 12px;
    font-size: 15px;
    color: #333;
  }

  .testimonial-card {
    background: var(--card-bg, #ffffff);
    border-radius: 12px;
    border: 1px solid #e8e8e8;
    border-left: 4px solid #CC0000;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
    padding: 16px;
    margin-bottom: 10px;
    transition: box-shadow 0.2s;
  }
  .testimonial-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
  .testimonial-card.clickable-testimonial { cursor: pointer; transition: transform 0.15s, box-shadow 0.15s; }
  .testimonial-card.clickable-testimonial:active { transform: scale(0.98); }
  .testimonial-tap-hint { font-size: 12px; color: #CC0000; font-weight: 500; margin-top: 8px; }
  :global([data-theme='dark']) .testimonial-tap-hint { color: #ff6666; }
  :global([data-theme='dark']) .testimonial-card { background: #1e1e1e; border-color: #333; border-left-color: #CC0000; }

  .testimonial-business {
    margin: 0 0 6px;
    font-size: 14px;
    color: #333;
  }

  .testimonial-text {
    margin: 0 0 6px;
    font-size: 13px;
    color: #555;
    font-style: italic;
    line-height: 1.4;
  }

  .testimonial-meta {
    margin: 0;
    font-size: 11px;
    color: #999;
  }
  .testimonial-link {
    display: inline-block;
    margin-top: 6px;
    font-size: 12px;
    color: #CC0000;
    text-decoration: none;
    font-weight: 600;
  }
  .testimonial-link:hover { text-decoration: underline; }
  .local-testimonial {
    border-left-color: #1565C0 !important;
    background: rgba(21, 101, 192, 0.03) !important;
  }
  .local-badge {
    margin: 0 0 4px;
    font-size: 11px;
    font-weight: 700;
    color: #1565C0;
  }
  /* testimonial-card dark mode handled above */

  .testimonial-btn {
    background: #CC0000 !important;
    color: white !important;
    border: none !important;
  }

  .no-testimonials {
    color: #999;
    font-size: 13px;
    text-align: center;
    padding: 12px;
  }

  .cycle-filter {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
  }

  .cycle-btn {
    flex: 1;
    padding: 10px;
    border: 2px solid #ddd;
    border-radius: 8px;
    background: white;
    font-size: 13px;
    font-weight: 600;
    color: #666;
    cursor: pointer;
    transition: all 0.2s;
  }

  .cycle-btn.active {
    background: #CC0000;
    color: white;
    border-color: #CC0000;
  }

  .cycle-btn:hover:not(.active) {
    border-color: #CC0000;
    color: #CC0000;
  }

  .hot-leads-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 12px;
    margin-top: 16px;
  }

  .hot-lead-card {
    background: var(--bg-primary, white);
    border: 2px solid var(--border-color, #e0e0e0);
    border-radius: 10px;
    padding: 14px;
    transition: all 0.2s;
    color: var(--text-primary, #222);
  }

  /* ── Call-In Leads styling ── */
  .tab-btn.tab-callin.active {
    background: #0a7d2c;
    border-color: #0a7d2c;
  }
  .callin-subtitle {
    margin: 2px 0 12px;
    font-size: 13px;
    color: var(--text-secondary, #666);
  }
  .callin-card {
    border-left: 5px solid #0a7d2c;
  }
  .callin-card:hover {
    border-color: #0a7d2c;
    box-shadow: 0 2px 8px rgba(10, 125, 44, 0.15);
  }
  .callin-badge-row {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 8px;
    flex-wrap: wrap;
  }
  .callin-badge {
    display: inline-block;
    background: #0a7d2c;
    color: #fff;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.3px;
    padding: 2px 7px;
    border-radius: 4px;
  }
  .lead-category.callin-cat {
    margin-bottom: 0;
  }
  .callin-assigned-badge {
    font-size: 10px;
    font-weight: 800;
    color: #fff;
    background: #1565c0;
    padding: 2px 7px;
    border-radius: 4px;
  }
  .callin-unassigned-badge {
    font-size: 10px;
    font-weight: 700;
    color: #8a6d00;
    background: rgba(255, 193, 7, 0.18);
    padding: 2px 7px;
    border-radius: 4px;
  }
  .callin-assign-row {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 6px 0 4px;
  }
  .callin-assign-label {
    font-size: 11px;
    font-weight: 700;
    color: var(--text-secondary, #555);
  }
  .callin-assign-select {
    flex: 1;
    font-size: 12px;
    padding: 4px 6px;
    border: 1px solid var(--border-color, #ccc);
    border-radius: 6px;
    background: var(--bg-primary, #fff);
    color: var(--text-primary, #111);
  }
  .status-badge.status-booked {
    background: #1565c0;
    color: #fff;
  }
  .status-badge.status-closed {
    background: #0a7d2c;
    color: #fff;
  }
  .notes-private {
    padding: 10px;
    background: var(--bg-secondary, #f5f5f5);
    border-radius: 8px;
  }
  .note-private-msg {
    font-size: 12px;
    color: var(--text-secondary, #666);
    margin: 6px 0 0;
    font-style: italic;
  }
  .callin-date {
    font-size: 11px;
    font-weight: 700;
    color: #0a7d2c;
    background: rgba(10, 125, 44, 0.1);
    padding: 2px 7px;
    border-radius: 4px;
  }
  .lead-cat-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    margin-bottom: 8px;
  }
  .lead-date {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-secondary, #888);
    white-space: nowrap;
  }
  .clickable-card { cursor: pointer; }
  .open-full-btn {
    margin-top: 10px;
    width: 100%;
    padding: 8px 10px;
    border: none;
    border-radius: 8px;
    background: #CC0000;
    color: #fff;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    transition: background 0.15s;
  }
  .open-full-btn:hover { background: #a30000; }
  .open-full-btn.callin-open { background: #0a7d2c; }
  .open-full-btn.callin-open:hover { background: #086523; }
  .callin-contact-name {
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 6px;
    color: var(--text-primary, #222);
  }
  .callin-comments {
    font-style: italic;
  }
  .callin-store {
    margin-top: 8px;
    font-size: 12px;
    color: var(--text-primary, #222);
    background: rgba(10, 125, 44, 0.08);
    padding: 6px 8px;
    border-radius: 6px;
  }
  .callin-meta {
    margin-top: 6px;
    font-size: 11px;
    color: var(--text-secondary, #777);
  }
  .callin-meta a { color: #0a7d2c; }

  .hot-lead-card:hover {
    border-color: #CC0000;
    box-shadow: 0 2px 8px rgba(204, 0, 0, 0.1);
  }

  .lead-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 6px;
  }

  .lead-header h4 {
    margin: 0;
    font-size: 14px;
    font-weight: 700;
    flex: 1;
    color: var(--text-primary, #222);
  }

  .rating {
    font-size: 12px;
    font-weight: 600;
  }

  .lead-category {
    display: inline-block;
    background: var(--bg-secondary, #f0f0f0);
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 11px;
    color: var(--text-secondary, #666);
    margin-bottom: 8px;
  }

  .lead-hook {
    font-size: 12px;
    font-style: italic;
    color: var(--text-primary, #333);
    background: var(--bg-secondary, #fff5f5);
    padding: 8px;
    border-radius: 4px;
    margin-bottom: 8px;
    line-height: 1.4;
  }

  .lead-contact {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 8px;
    font-size: 12px;
  }

  .phone, .email {
    color: #CC0000;
    text-decoration: none;
    font-weight: 500;
  }

  .phone:hover, .email:hover {
    text-decoration: underline;
  }

  .lead-store {
    font-size: 11px;
    color: var(--text-muted, #999);
  }

  .empty-state {
    text-align: center;
    padding: 40px 20px;
    color: #999;
  }

  .back-btn {
    background: none;
    border: none;
    color: #CC0000;
    font-weight: 600;
    cursor: pointer;
    padding: 0;
    margin-bottom: 16px;
    font-size: 13px;
  }
  .prospects-container {
    max-width: 1000px;
    margin: 0 auto;
    padding: 0;
    padding-bottom: 140px;
    color: var(--text-primary);
  }

  h2, h3 { margin: 0 0 0.75rem 0; color: var(--text-primary); font-weight: 700; }
  h2 { font-size: 22px; }
  h3 { font-size: 17px; }

  .attribution-summary { display: flex; gap: 10px; margin-bottom: 14px; }
  .attr-stat { flex: 1; text-align: center; padding: 10px 6px; background: var(--card-bg, white); border-radius: 10px; border: 1px solid var(--border-color, #e0e0e0); }
  .attr-stat.highlight { border-color: #2E7D32; background: #E8F5E9; }
  .attr-value { font-size: 20px; font-weight: 800; display: block; color: var(--text-primary); }
  .attr-label { font-size: 10px; color: var(--text-secondary, #888); text-transform: uppercase; font-weight: 600; }
  .attribution-banner { padding: 8px 12px; background: #E8F5E9; border: 1px solid #2E7D32; border-radius: 8px; margin-bottom: 8px; font-size: 12px; font-weight: 700; color: #2E7D32; }
  .call-tracked { display: block; font-size: 11px; font-weight: 600; color: #1565C0; margin-top: 2px; }
  .call-count { color: #1565C0; font-weight: 700; font-size: 11px; }
  .saved-card.converted { border-left: 4px solid #2E7D32; }
  .saved-card { cursor: default; }
  .saved-header { display: flex; justify-content: space-between; align-items: flex-start; cursor: pointer; }
  .saved-header h4 { margin: 0 0 2px; font-size: 15px; }
  .saved-addr { font-size: 12px; color: var(--text-secondary, #888); margin: 0; }
  .saved-meta { font-size: 12px; color: var(--text-secondary, #888); margin: 2px 0 0; }
  .saved-right { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; flex-shrink: 0; }
  .expand-arrow { font-size: 12px; color: var(--text-secondary, #888); }
  .status-badge { font-size: 11px; padding: 3px 8px; border-radius: 12px; font-weight: 700; text-transform: capitalize; }
  .status-new { background: #E3F2FD; color: #1565C0; }
  .status-contacted { background: #FFF3E0; color: #E65100; }
  .status-proposal { background: #F3E5F5; color: #6A1B9A; }
  .status-closed { background: #E8F5E9; color: #2E7D32; }
  .saved-actions { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border-color, #eee); }
  .saved-contact-info { margin: 10px 0; font-size: 13px; }
  .saved-contact-info p { margin: 4px 0; }
  .saved-contact-info a { color: #1565C0; text-decoration: none; }
  .saved-addr-copy { cursor: pointer; color: #1565C0; font-weight: 600; }
  .saved-email-templates { margin: 12px 0; padding-top: 10px; border-top: 1px solid var(--border-color, #eee); }
  .saved-schedule { margin: 10px 0; padding-top: 10px; border-top: 1px solid var(--border-color, #eee); }
  .saved-status-row { display: flex; gap: 8px; margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--border-color, #eee); }
  .nearby-btn { display: block; padding: 10px; margin: 10px 0; background: var(--card-bg, white); border: 2px solid #CC0000; border-radius: 8px; text-align: center; text-decoration: none; color: #CC0000; font-size: 13px; font-weight: 700; }
  .filter-chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .chip { padding: 6px 12px; border-radius: 20px; border: 1px solid var(--border-color, #ddd); background: var(--card-bg, white); font-size: 12px; font-weight: 600; cursor: pointer; color: var(--text-primary); }
  .chip.active { background: #CC0000; color: white; border-color: #CC0000; }
  .store-phone-display { margin: 4px 0 8px; font-size: 14px; }
  .store-phone-display a { color: #1565C0; text-decoration: none; font-weight: 600; }
  .subtitle { margin-bottom: 20px; color: var(--text-secondary); font-size: 14px; }

  .error-box {
    background: #fee;
    color: #c33;
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
    border-left: 4px solid #cc0000;
  }

  .loading { text-align: center; padding: 2rem; color: var(--text-tertiary); }
  .back-btn { background: none; border: none; color: #CC0000; font-weight: 600; cursor: pointer; margin-bottom: 16px; font-size: 14px; }

  .search-box { margin-bottom: 16px; }
  .search-box input {
    width: 100%;
    padding: 14px 16px;
    border: 2px solid var(--border-color);
    border-radius: 10px;
    font-size: 16px;
    font-family: inherit;
    background: var(--input-bg, white);
    color: var(--text-primary);
    box-sizing: border-box;
    transition: border-color 0.2s;
  }
  .search-box input:focus { outline: none; border-color: #CC0000; box-shadow: 0 0 0 3px rgba(204, 0, 0, 0.1); }
  .store-addr-detail { margin: 2px 0; font-size: 11px; color: var(--text-tertiary); }
  .empty-msg { text-align: center; color: var(--text-tertiary); font-size: 14px; padding: 30px 20px; }

  .button-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1.5rem;
    width: 100%;
  }

  @media (min-width: 768px) {
    .button-grid {
      grid-template-columns: repeat(3, 1fr);
      gap: 2rem;
    }
  }

  @media (min-width: 1200px) {
    .button-grid {
      grid-template-columns: repeat(4, 1fr);
      gap: 2rem;
    }
  }

  .main-btn {
    background: var(--card-bg);
    border: 2px solid var(--border-color);
    border-radius: 16px;
    padding: 2rem 1.5rem;
    cursor: pointer;
    transition: all 0.2s;
    text-align: center;
    color: var(--text-primary);
    min-height: 180px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 100%;
  }

  .main-btn:hover {
    border-color: #cc0000;
    box-shadow: 0 4px 12px rgba(204, 0, 0, 0.1);
    transform: translateY(-2px);
  }

  .btn-icon { font-size: 32px; margin-bottom: 0.5rem; }
  .btn-text { font-size: 15px; font-weight: 600; color: var(--text-primary); margin-bottom: 0.25rem; line-height: 1.3; }
  .btn-desc { font-size: 13px; color: var(--text-tertiary); line-height: 1.3; }

  .store-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .store-item {
    background: var(--card-bg);
    border: 2px solid var(--border-color);
    border-radius: 10px;
    padding: 1rem;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: var(--text-primary);
  }

  .store-item:hover {
    border-color: #cc0000;
    box-shadow: 0 4px 12px rgba(204, 0, 0, 0.1);
  }

  .store-info h4 { margin: 0 0 6px 0; color: var(--text-primary); font-weight: 600; font-size: 16px; }
  .address { margin: 4px 0; font-size: 13px; color: var(--text-secondary); }
  .street-address { margin: 2px 0 6px; font-size: 12px; color: #CC0000; font-weight: 600; }
  .case-count { margin: 4px 0 0; font-size: 12px; color: #0066cc; font-weight: 500; }
  .distance { margin: 6px 0 0 0; font-size: 12px; color: #CC0000; font-weight: 600; }
  .store-right { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }
  .store-num { background: rgba(204, 0, 0, 0.1); padding: 6px 10px; border-radius: 6px; font-weight: 700; font-size: 12px; color: #CC0000; }
  .store-cycle { font-size: 11px; font-weight: 600; color: #666; }
  .store-cases { font-size: 11px; font-weight: 600; color: #2e7d32; }

  .new-biz-banner {
    width: 100%; padding: 14px 16px; border-radius: 12px; font-size: 16px; font-weight: 700;
    background: linear-gradient(135deg, #1a73e8, #0d47a1); color: white;
    border: none; cursor: pointer; text-align: center; margin-bottom: 12px;
    display: flex; flex-direction: column; align-items: center; gap: 2px;
    transition: transform 0.1s;
  }
  .new-biz-banner:active { transform: scale(0.97); }
  .new-biz-hint { font-size: 11px; font-weight: 400; opacity: 0.8; }

  .category-grid, .subcat-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
    margin-bottom: 1rem;
  }

  .category-btn, .subcat-btn {
    background: var(--card-bg);
    border: 2px solid var(--border-color);
    border-radius: 8px;
    padding: 1rem;
    cursor: pointer;
    text-align: center;
    font-weight: 600;
    transition: all 0.2s;
    color: var(--text-primary);
  }

  .category-btn:hover, .subcat-btn:hover {
    border-color: #cc0000;
    background: rgba(204, 0, 0, 0.05);
  }

  .prospect-toolbar { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; justify-content: space-between; align-items: center; }
  .sort-bar { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .sort-label { font-size: 12px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; flex-shrink: 0; }
  .sort-btn { padding: 6px 12px; border: 1px solid var(--border-color); border-radius: 16px; background: var(--card-bg); font-size: 12px; font-weight: 600; cursor: pointer; color: var(--text-secondary); transition: all 0.2s; white-space: nowrap; }
  .sort-btn.active { background: #CC0000; color: white; border-color: #CC0000; }
  .sort-btn:hover:not(.active) { border-color: #CC0000; color: #CC0000; }
  .view-toggle { display: flex; gap: 6px; flex-shrink: 0; }
  .prospect-list { display: flex; flex-direction: column; gap: 1rem; }

  .prospect-card {
    background: var(--card-bg, #ffffff);
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
    border: 1px solid #e8e8e8;
    color: var(--text-primary);
    transition: box-shadow 0.2s;
    position: relative;
    overflow: hidden;
    user-select: none;
    -webkit-user-select: none;
    box-sizing: border-box;
    max-width: 100%;
  }
  .prospect-card:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }
  :global([data-theme='dark']) .prospect-card {
    background: #1e1e1e;
    border-color: #333;
  }

  .prospect-header { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
  .score-emoji { font-size: 18px; }
  .prospect-card h4 { margin: 0; color: var(--text-primary); font-weight: 600; font-size: 15px; }
  .prospect-address { margin: 4px 0; font-size: 13px; color: var(--text-secondary); }
  .prospect-meta { margin: 6px 0; font-size: 12px; color: var(--text-tertiary); }
  .prospect-phone { margin: 6px 0 4px; font-size: 15px; font-weight: 600; color: var(--text-primary); }
  .prospect-email { margin: 2px 0 10px; font-size: 14px; font-weight: 500; color: var(--text-secondary, #555); }
  .prospect-hours { margin: 2px 0 8px; font-size: 12px; color: var(--text-secondary); cursor: pointer; }
  .hours-detail { background: var(--bg-secondary, #f5f5f5); border-radius: 8px; padding: 8px 12px; margin: 4px 0 8px; }
  .hours-line { margin: 2px 0; font-size: 11px; color: var(--text-secondary); }
  .hours-line.today-line { font-weight: 700; color: #CC0000; }
  :global([data-theme='dark']) .hours-detail { background: #2a2a2a; }

  .prospect-actions {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding-top: 10px;
    border-top: 1px solid var(--border-color);
    overflow: hidden;
    width: 100%;
    box-sizing: border-box;
  }

  .action-btn {
    flex: 1;
    min-width: 0;
    padding: 8px 4px;
    background: var(--hover-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.82rem;
    text-decoration: none;
    text-align: center;
    font-weight: 600;
    transition: all 0.2s;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    box-sizing: border-box;
  }

  .action-btn:hover { background: #cc0000; color: white; }

  .action-row {
    display: flex;
    gap: 8px;
    width: 100%;
  }

  .action-row .action-btn { flex: 1; min-width: 0; }

  .full-width { width: 100%; flex: none !important; }

  .call-btn { background: #2e7d32 !important; color: white !important; border-color: #2e7d32 !important; }
  .call-btn:hover { background: #1b5e20 !important; }

  /* Color-coded buttons */
  .btn-green { background: #2e7d32 !important; color: white !important; border-color: #2e7d32 !important; }
  .btn-green:hover { background: #1b5e20 !important; }

  .btn-blue { background: #1565C0 !important; color: white !important; border-color: #1565C0 !important; }
  .btn-blue:hover { background: #0D47A1 !important; }

  .btn-purple { background: #6A1B9A !important; color: white !important; border-color: #6A1B9A !important; }
  .btn-purple:hover { background: #4A148C !important; }

  .btn-orange { background: #E65100 !important; color: white !important; border-color: #E65100 !important; }
  .btn-orange:hover { background: #BF360C !important; }

  .lead-claim-badge {
    display: flex; align-items: center; gap: 6px;
    background: #FFF3E0; border: 1px solid #FFB74D; border-radius: 8px;
    padding: 4px 10px; font-size: 12px; color: #E65100; font-weight: 600;
    margin-bottom: 6px;
  }
  :global([data-theme='dark']) .lead-claim-badge { background: #3e2723; border-color: #8d6e63; color: #ffcc80; }
  .release-lead-btn {
    background: none; border: none; color: #E65100; font-size: 14px; cursor: pointer; margin-left: auto; padding: 0 4px;
  }

  .lead-field-label { display: block; font-size: 11px; font-weight: 700; color: #666; margin: 6px 0 2px; text-transform: uppercase; letter-spacing: 0.5px; }
  :global([data-theme='dark']) .lead-field-label { color: #aaa; }
  .lead-field-input {
    width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px;
    background: white; color: #333; box-sizing: border-box;
  }
  :global([data-theme='dark']) .lead-field-input { background: #1a1a1a; color: #eee; border-color: #444; }

  .btn-gray { background: #f5f5f5 !important; color: #333 !important; border-color: #ddd !important; }
  :global([data-theme='dark']) .btn-gray { background: #2a2a2a !important; color: #ddd !important; border-color: #444 !important; }
  .btn-gray:hover { background: #e0e0e0 !important; }

  .btn-outline { background: transparent !important; color: #CC0000 !important; border: 2px solid #CC0000 !important; }
  .btn-outline:hover { background: #CC0000 !important; color: white !important; }

  .btn-book-appt {
    display: block !important;
    width: 100% !important;
    flex: none !important;
    padding: 14px 16px !important;
    background: #CC0000 !important;
    color: white !important;
    border-color: #CC0000 !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    border-radius: 12px !important;
    text-align: center;
    text-decoration: none;
    letter-spacing: 0.3px;
    box-shadow: 0 2px 8px rgba(204, 0, 0, 0.3);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    box-sizing: border-box;
  }
  .btn-book-appt:hover { background: #aa0000 !important; box-shadow: 0 4px 12px rgba(204, 0, 0, 0.4); }
  .btn-navigate {
    display: block !important;
    width: 100% !important;
    flex: none !important;
    padding: 14px 16px !important;
    background: #34a853 !important;
    color: white !important;
    border-color: #34a853 !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    border-radius: 12px !important;
    text-align: center;
    text-decoration: none;
    letter-spacing: 0.3px;
    box-shadow: 0 2px 8px rgba(52, 168, 83, 0.3);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    box-sizing: border-box;
  }
  .btn-navigate:hover { background: #2d8a46 !important; }
  .btn-showmap {
    display: block !important;
    width: 100% !important;
    flex: none !important;
    padding: 14px 16px !important;
    background: #1a73e8 !important;
    color: white !important;
    border-color: #1a73e8 !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    border-radius: 12px !important;
    text-align: center;
    box-shadow: 0 2px 8px rgba(26, 115, 232, 0.3);
    box-sizing: border-box;
  }
  .btn-showmap:hover { background: #0d47a1 !important; }
  .prospect-minimap {
    height: 250px;
    border-radius: 12px;
    overflow: hidden;
    border: 2px solid var(--border-color, #ddd);
    margin-top: 10px;
  }
  .text-btn { background: #1565C0 !important; color: white !important; border-color: #1565C0 !important; }
  .text-btn:hover { background: #0D47A1 !important; }

  .email-btn { background: #1565c0 !important; color: white !important; border-color: #1565c0 !important; }
  .email-btn:hover { background: #0d47a1 !important; }

  .notes-section, .email-section, .script-section {
    margin-top: 10px;
    padding: 10px;
    background: var(--hover-bg);
    border-radius: 8px;
  }

  .script-btn { background: #1565c0 !important; color: white !important; border-color: #1565c0 !important; }
  .script-btn:hover { background: #0d47a1 !important; }

  .script-title { margin: 0 0 10px; font-size: 15px; color: var(--text-primary); }

  .script-select-btn {
    display: block;
    width: 100%;
    padding: 10px 14px;
    margin-bottom: 8px;
    background: var(--card-bg);
    border: 2px solid var(--border-color);
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    text-align: left;
    color: var(--text-primary);
    transition: all 0.2s;
  }

  .script-select-btn:hover { border-color: #1565c0; background: #e3f2fd; }

  .script-preview-box {
    padding: 14px;
    background: var(--card-bg);
    border: 2px solid #1565c0;
    border-radius: 8px;
    margin-top: 8px;
  }

  .script-text {
    margin: 0 0 12px;
    font-size: 14px;
    line-height: 1.6;
    color: var(--text-primary);
  }

  .script-text:last-of-type { margin-bottom: 14px; }
  .script-text strong { color: #1565c0; }
  .script-text em { font-style: italic; color: #c62828; font-weight: 600; }

  .script-label {
    margin: 14px 0 8px;
    font-size: 13px;
    font-weight: 800;
    color: #1565c0;
    text-transform: uppercase;
    letter-spacing: .3px;
    border-bottom: 2px solid var(--border-color);
    padding-bottom: 4px;
  }
  .script-label:first-child { margin-top: 0; }
  .script-reminder {
    margin: 14px 0;
    padding: 10px 12px;
    background: rgba(255, 193, 7, .12);
    border-left: 4px solid #ffb300;
    border-radius: 6px;
    font-size: 13px;
    line-height: 1.5;
    color: var(--text-primary);
  }
  .script-notes {
    margin: 8px 0 14px;
    padding-left: 18px;
    font-size: 13px;
    line-height: 1.6;
    color: var(--text-secondary);
  }
  .script-notes li { margin-bottom: 6px; }

  .note-saved { margin: 4px 0 0; font-size: 11px; color: #2e7d32; font-weight: 600; text-align: right; }

  .notes-section textarea {
    width: 100%;
    padding: 8px;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    font-size: 13px;
    font-family: inherit;
    resize: vertical;
    box-sizing: border-box;
    background: var(--input-bg);
    color: var(--text-primary);
  }

  .email-preview {
    margin: 0 0 6px;
    font-weight: 600;
    font-size: 13px;
    color: var(--text-primary);
  }

  .email-title {
    margin: 0 0 10px;
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .email-tpl-btn {
    display: block;
    width: 100%;
    padding: 10px 12px;
    margin-bottom: 6px;
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    text-align: left;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    color: var(--text-primary);
  }

  .email-tpl-btn:hover {
    border-color: #CC0000;
    background: #fff5f5;
  }

  .email-tpl-btn.cat-tpl {
    border-color: #CC0000;
    background: #fff8f8;
  }
  .cat-badge {
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    color: #fff;
    background: #CC0000;
    border-radius: 6px;
    padding: 1px 6px;
    margin-left: 6px;
    vertical-align: middle;
  }
  :global([data-theme='dark']) .email-tpl-btn.cat-tpl { background: #2a1414; }

  .email-tpl-btn.prog-tpl {
    border-color: #1a73e8;
    background: #f5f9ff;
  }
  .prog-badge {
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    color: #fff;
    background: #1a73e8;
    border-radius: 6px;
    padding: 1px 6px;
    margin-left: 6px;
    vertical-align: middle;
  }
  :global([data-theme='dark']) .email-tpl-btn.prog-tpl { background: #0e1a2a; }

  .email-tpl-btn.featured-tpl {
    border: 2px solid #7c3aed;
    background: linear-gradient(135deg, #f5f3ff, #ede9fe);
    font-weight: 700;
  }
  :global([data-theme='dark']) .email-tpl-btn.featured-tpl { background: #1e1633; }
  .featured-badge {
    display: inline-block;
    font-size: 10px;
    font-weight: 800;
    color: #fff;
    background: linear-gradient(135deg, #7c3aed, #6d28d9);
    border-radius: 6px;
    padding: 1px 7px;
    margin-left: 6px;
    vertical-align: middle;
  }
  .email-research-hint {
    font-size: 12px;
    color: #6d28d9;
    background: #f5f3ff;
    border-radius: 8px;
    padding: 7px 10px;
    margin: 0 0 8px;
    font-style: italic;
  }
  .email-research-hint.done { color: #15803d; background: #f0fdf4; font-style: normal; }

  .email-to-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 12px;
    padding: 8px 10px;
    border-radius: 8px;
    background: var(--card-bg, #f7f7f7);
    border: 1px solid var(--border-color, #e0e0e0);
  }
  .email-to-status { font-size: 12px; line-height: 1.4; flex: 1; min-width: 0; }
  .email-to-status.found { color: #1565c0; }
  .email-to-status.found em { color: #2e7d32; font-style: normal; font-weight: 600; }
  .email-to-status.scraping { color: #b26a00; }
  .email-to-status.missing { color: #999; }
  .email-scrub-btn {
    flex-shrink: 0;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 10px;
    border: 1px solid #1565c0;
    color: #1565c0;
    background: transparent;
    border-radius: 8px;
    cursor: pointer;
  }
  .email-scrub-btn:hover { background: #1565c0; color: #fff; }
  .email-scrub-btn.deep { border-color: #6a1b9a; color: #6a1b9a; }
  .email-scrub-btn.deep:hover { background: #6a1b9a; color: #fff; }

  .email-alt-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin: 4px 0 10px;
  }
  .email-alt-label { font-size: 11px; color: #888; margin-right: 2px; }
  .email-alt-btn {
    font-size: 11px;
    padding: 3px 8px;
    border: 1px solid #cfd8dc;
    background: #f5f7f9;
    color: #37474f;
    border-radius: 12px;
    cursor: pointer;
  }
  .email-alt-btn:hover { background: #1565c0; color: #fff; border-color: #1565c0; }

  .owner-found-row { margin: 2px 0 6px; }
  .owner-found-status { font-size: 12px; line-height: 1.4; color: #2e7d32; }
  .owner-found-status em { color: #2e7d32; font-style: normal; font-weight: 600; }

  .email-addons {
    margin-top: 10px;
    padding: 10px;
    border: 1px dashed var(--border-color, #ddd);
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .email-addon-toggle {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    cursor: pointer;
  }
  .email-graphic-picker {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .email-addon-label { font-size: 13px; font-weight: 600; color: var(--text-primary); }
  .email-graphic-select {
    flex: 1;
    min-width: 140px;
    padding: 6px 8px;
    border-radius: 8px;
    border: 1px solid var(--border-color, #ddd);
    font-size: 13px;
    background: var(--card-bg, #fff);
    color: var(--text-primary);
  }
  .email-graphic-thumb {
    width: 100%;
    max-width: 260px;
    border-radius: 8px;
    border: 1px solid var(--border-color, #ddd);
    align-self: center;
  }
  .email-btn-secondary {
    background: transparent !important;
    color: #1565c0 !important;
    border: 1px solid #1565c0 !important;
    margin-top: 8px;
  }
  .email-btn-secondary:hover { background: #e3f0fc !important; }

  .email-preview-box {
    margin-top: 12px;
    padding: 12px;
    background: white;
    border: 1px solid var(--border-color);
    border-radius: 8px;
  }

  .email-subject {
    margin: 0 0 8px;
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .email-body-text {
    margin: 0 0 12px;
    font-size: 12px;
    color: var(--text-secondary);
    white-space: pre-line;
    line-height: 1.5;
    max-height: 200px;
    overflow-y: auto;
  }

  .status-select {
    padding: 0.5rem;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    font-size: 0.9rem;
    background: var(--input-bg);
    color: var(--text-primary);
  }

  .delete-btn {
    padding: 0.5rem 1rem;
    background: #fee;
    color: #c33;
    border: 1px solid #fcc;
    border-radius: 4px;
    cursor: pointer;
  }

  .notes-input {
    width: 100%;
    margin-top: 0.5rem;
    padding: 0.5rem;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    font-size: 0.9rem;
    min-height: 60px;
    resize: vertical;
    background: var(--input-bg);
    color: var(--text-primary);
  }

  @media (max-width: 600px) {
    .category-grid, .subcat-grid { grid-template-columns: 1fr; }
  }

  .custom-search-bar {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
  }

  .custom-search-bar input {
    flex: 1;
    padding: 12px;
    border: 2px solid #ddd;
    border-radius: 8px;
    font-size: 14px;
    font-family: inherit;
  }

  .custom-search-bar input:focus {
    border-color: #CC0000;
    outline: none;
  }

  .search-go-btn {
    padding: 12px 18px;
    background: #CC0000;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    cursor: pointer;
    font-weight: 700;
  }

  .search-go-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .or-divider {
    text-align: center;
    color: var(--text-tertiary, #999);
    font-size: 12px;
    margin: 12px 0;
  }

  .calendar-booking { width: 100%; }
  .invite-row { margin-bottom: 8px; width: 100%; }
  .invite-select { width: 100%; padding: 10px 12px; border: 2px solid var(--border-color, #ddd); border-radius: 8px; font-size: 16px; background: var(--input-bg, white); color: var(--text-primary, #333); box-sizing: border-box; max-width: 100%; }
  .calendar-btn { background: #1a73e8 !important; color: white !important; }
  .calendar-btn:hover { background: #1557b0 !important; }
  /* Dibs / Store Claims */
  .store-item-wrap { position: relative; width: 100%; border-radius: 12px; overflow: hidden; background: var(--card-bg); border: 2px solid var(--border-color); }
  .store-item-wrap .store-item { border: none; border-radius: 0; width: 100%; }
  .store-item-wrap.store-claimed { border-color: #FF9800; border-left: 4px solid #FF9800; }
  .dibs-badge { display: flex; align-items: center; justify-content: space-between; padding: 6px 12px; background: #FFF3E0; font-size: 12px; font-weight: 600; color: #E65100; }
  .dibs-release { background: none; border: none; color: #E65100; font-size: 14px; cursor: pointer; padding: 2px 6px; font-weight: 700; }
  .dibs-claim-btn { width: 100%; padding: 8px; background: none; border: none; border-top: 1px dashed #FF9800; color: #E65100; font-size: 12px; font-weight: 600; cursor: pointer; }
  .dibs-claim-btn:hover { background: #FFF3E0; }
  :global([data-theme='dark']) .dibs-badge { background: #3e2c00; color: #FFB74D; }
  :global([data-theme='dark']) .dibs-claim-btn { border-top-color: #FF9800; color: #FFB74D; }
  :global([data-theme='dark']) .dibs-claim-btn:hover { background: #3e2c00; }
</style>
