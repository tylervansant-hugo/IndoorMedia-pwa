<script>
  import { onMount, onDestroy, tick } from 'svelte';
  import { user, currentUser, sharedNearbyStores, sharedSelectedStore, sharedUserLocation } from '../lib/stores.js';
  import { logActivity } from '../lib/activity.js';
  import { isFirebaseReady, claimStore, releaseStore, getZoneClaims, claimLead, releaseLead, getAllLeadClaims, saveLeadData, getLeadData, getAllLeadData, hashLeadId } from '../lib/firebase.js';
  import HotLeadsSubmit from './HotLeadsSubmit.svelte';
  import PendingLeads from './PendingLeads.svelte';
  import StoreSearchInput from '../lib/StoreSearchInput.svelte';
  import L from 'leaflet';
  import 'leaflet/dist/leaflet.css';
  
  let allStores = [];
  let nearbyStores = [];
  let prospects = [];
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
  let view = 'main'; // main, nearby-stores, categories, subcategories, results, saved, hot-leads, pending, submit-lead

  // ── Store Claims (Dibs) ──
  let storeClaims = {};
  let claimLoading = {};

  // ── Lead Claims (Dibs on Prospects) ──
  let leadClaims = {}; // keyed by hash
  let leadDataCache = {}; // keyed by hash — persistent lead data from Firebase

  async function loadStoreClaims() {
    if (!isFirebaseReady()) return;
    const claims = await getZoneClaims('');
    const map = {};
    claims.forEach(c => { map[c.storeName] = c; });
    storeClaims = map;
  }

  async function loadLeadClaims() {
    if (!isFirebaseReady()) return;
    const claims = await getAllLeadClaims();
    const map = {};
    claims.forEach(c => {
      const id = hashLeadId(c.prospectName, c.prospectAddress);
      map[id] = c;
    });
    leadClaims = map;
  }

  async function loadAllLeadData() {
    if (!isFirebaseReady()) return;
    const all = await getAllLeadData();
    const map = {};
    all.forEach(d => {
      const id = hashLeadId(d.prospectName, d.prospectAddress);
      map[id] = d;
    });
    leadDataCache = map;
  }

  function getLeadHash(prospect) {
    return hashLeadId(prospect.name, prospect.address);
  }

  function getLeadClaim(prospect) {
    return leadClaims[getLeadHash(prospect)] || null;
  }

  async function handleLeadAction(prospect, action) {
    const u = $user;
    if (!u) return;
    const repName = u.name || u.display_name || 'Unknown';
    const repId = u.id || u.rep_id || 'unknown';
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
    const ok = await claimStore(
      u.name || u.display_name || 'Unknown',
      u.id || u.rep_id || 'unknown',
      store.StoreName,
      store.ZoneName || u.zone || ''
    );
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
    const ok = await releaseStore(storeName);
    if (ok) {
      delete storeClaims[storeName];
      storeClaims = storeClaims;
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
    const storeName = e.detail;
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

  onMount(async () => {
    document.addEventListener('select-store-from-map', handleStoreSelectFromMap);
    document.addEventListener('edge-swipe-back', handleEdgeSwipeBack);
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
      
      // Filter hot leads: rep's stores + current cycle
      if (repStoreIds === null) {
        // Manager: show all leads for current cycle stores
        hotLeads = allLeadsData.filter(l => !l.store_id || cycleStores.has(l.store_id));
      } else if (repStoreIds.size > 0) {
        // Rep: show leads for their stores that are in current cycle
        const repCycleStores = new Set([...repStoreIds].filter(id => cycleStores.has(id)));
        hotLeads = allLeadsData.filter(l => !l.store_id || repCycleStores.has(l.store_id));
      } else {
        hotLeads = []; // No stores found for this rep
      }
      
      console.log(`Hot Leads: ${hotLeads.length} leads, Selling Cycle: ${currentSellingCycle}, Rep stores: ${repStoreIds === null ? 'all (manager)' : repStoreIds.size}`);
      
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

  // Svelte action: renders a mini Leaflet map showing prospect + store + distance
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

    // Store marker (blue) + distance line
    if (sLat && sLng) {
      L.circleMarker([sLat, sLng], {
        radius: 12, fillColor: '#1a73e8', color: '#fff', weight: 3, fillOpacity: 0.9,
      }).addTo(map).bindPopup(`<strong>🏪 ${store.GroceryChain || ''}</strong><br><span style="font-size:12px;">${store.Address || ''}, ${store.City || ''}</span>`);

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

      // Fit both markers in view
      map.fitBounds([[pLat, pLng], [sLat, sLng]], { padding: [40, 40] });
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
      subject: 'Quick question about {business}',
      body: 'Hi {contact},\n\nI noticed {business} in the area and wanted to reach out. We work with local businesses to help drive foot traffic through register tape advertising at {store}.\n\nThousands of businesses like yours have seen measurable results — would you be open to a quick 10-minute chat this week?\n\nBest,\n{rep}\nIndoorMedia' },
    { id: 'roi', icon: '📊', name: 'ROI / Value Focused',
      subject: 'How {business} can reach {customers} local customers weekly',
      body: 'Hi {contact},\n\n{store_cap} sees {customers} customers per week. That\'s {customers} potential customers seeing your ad every single week.\n\nBusinesses in your category have reported strong ROI — many seeing results within the first month. Our register tape ads put your name, offer, and location directly in shoppers\' hands at {store}.\n\nI\'d love to show you how the numbers work for {business}. Can we schedule a quick call?\n\nBest,\n{rep}\nIndoorMedia' },
    { id: 'followup', icon: '⏰', name: 'Follow-up (No Response)',
      subject: 'Following up — {business}',
      body: 'Hi {contact},\n\nI reached out a few days ago about a partnership opportunity for {business} at {store} and wanted to follow up.\n\nWith {customers} shoppers coming through each week, register tape advertising is one of the most effective ways to reach local customers. I think there\'s a great fit here.\n\nWould you have 10 minutes this week for a quick chat?\n\nBest,\n{rep}\nIndoorMedia' },
    { id: 'reengagement', icon: '🔄', name: 'Re-engagement',
      subject: 'Things have changed — {business}',
      body: 'Hi {contact},\n\nIt\'s been a while since we last connected about {business}. A lot has changed at IndoorMedia — new store locations, better pricing, and stronger results for businesses like yours.\n\nWe have availability at {store} right now and I think it could be a great fit.\n\nWould you be open to reconnecting for a quick 10-minute call?\n\nBest,\n{rep}\nIndoorMedia' },
    { id: 'limited', icon: '⚡', name: 'Limited Time Offer',
      subject: 'Limited availability at {store_short} near {business}',
      body: 'Hi {contact},\n\nI wanted to give you a heads up — we have limited ad placement availability at {store}.\n\nWith {customers} shoppers per week, this is one of the highest-traffic locations in the area. Our partnership program is filling up fast, and I\'d hate for {business} to miss out.\n\nCan we schedule a quick call this week?\n\nBest,\n{rep}\nIndoorMedia' },
  ];

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

  // Replace all template placeholders including {store} and {customers} variants
  function fillTemplate(text, prospectName) {
    const rep = $user?.name || $user?.first_name || 'Your Rep';
    return text
      .replace(/\{business\}/g, prospectName)
      .replace(/\{contact\}/g, '')
      .replace(/\{rep\}/g, rep)
      .replace(/\{store_cap\}/g, getStoreRef().replace(/^the /, 'The '))
      .replace(/\{store_short\}/g, getStoreShort())
      .replace(/\{store\}/g, getStoreRef())
      .replace(/\{customers\}/g, getStoreCustomers());
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
      localStorage.setItem('savedProspects', JSON.stringify(savedProspects));
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
      localStorage.setItem('savedProspects', JSON.stringify(savedProspects));
      alert(`✅ Saved: ${prospect.name}`);
    }
  }

  function deleteProspect(id) {
    savedProspects = savedProspects.filter(p => p.id !== id);
    localStorage.setItem('savedProspects', JSON.stringify(savedProspects));
  }

  function updateProspectNotes(id, notes) {
    const idx = savedProspects.findIndex(p => p.id === id);
    if (idx >= 0) {
      savedProspects[idx].notes = notes;
      localStorage.setItem('savedProspects', JSON.stringify(savedProspects));
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
    <button class="tab-btn" class:active={view === 'saved'} on:click={() => view = 'saved'}>💾 Saved ({savedProspects.length})</button>
    {#if $user?.role === 'manager' || $user?.name?.toLowerCase().includes('tyler')}
      <button class="tab-btn" class:active={view === 'team'} on:click={() => view = 'team'}>👥 Team ({teamProspects.length})</button>
    {/if}
    {#if $user?.role === 'manager' || $user?.name?.toLowerCase().includes('tyler')}
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
        <div class="prospect-card swipeable"
          style="transform: translateX({prospect._dismissing ? '-120vw' : (prospect._swipeX || 0) + 'px'}) rotate({prospect._dismissing ? '-30deg' : ((prospect._swipeX || 0) * 0.05) + 'deg'}); {prospect._dismissing ? 'transition: transform 0.4s ease, opacity 0.4s ease; opacity: 0;' : prospect._swiping ? '' : 'transition: transform 0.3s ease;'}"
          on:touchstart|passive={(e) => { prospect._swipeStartX = e.touches[0].clientX; prospect._swipeStartY = e.touches[0].clientY; prospect._swiping = false; prospect._swipeX = 0; prospects = prospects; }}
          on:touchmove|passive={(e) => {
            const dx = e.touches[0].clientX - prospect._swipeStartX;
            const dy = e.touches[0].clientY - prospect._swipeStartY;
            if (!prospect._swiping && Math.abs(dx) > 10 && Math.abs(dx) > Math.abs(dy)) prospect._swiping = true;
            if (prospect._swiping) { prospect._swipeX = dx; prospects = prospects; }
          }}
          on:touchend={() => {
            if (prospect._swipeX > 80) {
              // Swipe right → Book appointment
              const calUrl = `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent('Visit: ' + prospect.name)}&details=${encodeURIComponent('Prospect: ' + prospect.name + '\nAddress: ' + prospect.address + (prospect.phone ? '\nPhone: ' + prospect.phone : '') + (prospect.website ? '\nWebsite: ' + prospect.website : '') + '\nStore: ' + (selectedStore?.GroceryChain || '') + ' ' + (selectedStore?.StoreName || '') + '\nRep: ' + ($user?.name || ''))}&location=${encodeURIComponent(prospect.address)}&add=${encodeURIComponent('tyler.vansant@indoormedia.com')}${inviteRepEmail ? ',' + encodeURIComponent(inviteRepEmail) : ''}`;
              window.open(calUrl, '_blank');
              prospect._swipeX = 0; prospect._swiping = false; prospects = prospects;
            } else if (prospect._swipeX < -80) {
              // Swipe left → Dismiss
              prospect._dismissing = true; prospect._dismissDir = -1; prospects = prospects;
              setTimeout(() => { prospects = prospects.filter(p => p !== prospect); }, 400);
            } else {
              prospect._swipeX = 0; prospect._swiping = false; prospects = prospects;
            }
          }}
          on:mousedown={(e) => { prospect._mouseDown = true; prospect._swipeStartX = e.clientX; prospect._swiping = false; prospect._swipeX = 0; prospects = prospects; }}
          on:mousemove={(e) => {
            if (!prospect._mouseDown) return;
            const dx = e.clientX - prospect._swipeStartX;
            if (!prospect._swiping && Math.abs(dx) > 10) prospect._swiping = true;
            if (prospect._swiping) { e.preventDefault(); prospect._swipeX = dx; prospects = prospects; }
          }}
          on:mouseup={() => {
            if (!prospect._mouseDown) return;
            prospect._mouseDown = false;
            if (prospect._swipeX > 80) {
              const calUrl = `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent('Visit: ' + prospect.name)}&details=${encodeURIComponent('Prospect: ' + prospect.name + '\nAddress: ' + prospect.address + (prospect.phone ? '\nPhone: ' + prospect.phone : '') + (prospect.website ? '\nWebsite: ' + prospect.website : '') + '\nStore: ' + (selectedStore?.GroceryChain || '') + ' ' + (selectedStore?.StoreName || '') + '\nRep: ' + ($user?.name || ''))}&location=${encodeURIComponent(prospect.address)}&add=${encodeURIComponent('tyler.vansant@indoormedia.com')}${inviteRepEmail ? ',' + encodeURIComponent(inviteRepEmail) : ''}`;
              window.open(calUrl, '_blank');
              prospect._swipeX = 0; prospect._swiping = false; prospects = prospects;
            } else if (prospect._swipeX < -80) {
              prospect._dismissing = true; prospect._dismissDir = -1; prospects = prospects;
              setTimeout(() => { prospects = prospects.filter(p => p !== prospect); }, 400);
            } else {
              prospect._swipeX = 0; prospect._swiping = false; prospects = prospects;
            }
          }}
          on:mouseleave={() => { if (prospect._mouseDown) { prospect._mouseDown = false; prospect._swipeX = 0; prospect._swiping = false; prospects = prospects; } }}
        >
          <!-- Swipe indicators -->
          {#if prospect._swipeX > 30}
            <div class="swipe-indicator swipe-book" style="opacity: {Math.min((prospect._swipeX - 30) / 50, 1)}">📅 BOOK</div>
          {/if}
          {#if prospect._swipeX < -30}
            <div class="swipe-indicator swipe-skip" style="opacity: {Math.min((-prospect._swipeX - 30) / 50, 1)}">♻️ SKIP</div>
          {/if}
          <div class="prospect-header">
            <span class="score-emoji">{prospect.score >= 80 ? '🔥' : prospect.score >= 70 ? '⭐' : '👀'}</span>
            <h4>{prospect.name}</h4>
          </div>
          <p class="prospect-address" style="cursor:pointer;" on:click={() => { navigator.clipboard.writeText(prospect.address); copiedAddress = prospect.address; setTimeout(() => copiedAddress = '', 2000); }}>📍 {copiedAddress === prospect.address ? '✅ Copied!' : prospect.address}</p>
          <p class="prospect-meta">
            ⭐ {prospect.rating.toFixed(1)} ({prospect.reviews} reviews) • {prospect.distance} mi • Score: {prospect.score}%
          </p>
          {#if prospect.phone}
            <p class="prospect-phone">📞 {prospect.phone}</p>
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
              <button class="action-btn btn-purple" on:click={() => { prospect._showEmail = !prospect._showEmail; prospect._showText = false; prospect._showScript = false; prospect._showNotes = false; prospects = prospects; handleLeadAction(prospect, 'email'); }}>✉️ Email</button>
              <button class="action-btn btn-orange" on:click={() => { handleLeadAction(prospect, 'walk-in'); }}>🚶 Walk-In</button>
            </div>

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
                  <p class="script-text">Hey there, I was hoping you could point me in the right direction on something…?</p>
                  <p class="script-text">My name is <strong>{$user?.name || $user?.first_name || '[Your Name]'}</strong> and I was calling because I'm working with the <strong>{selectedStore?.GroceryChain || '[Store Chain]'}</strong> over on <strong>{selectedStore?.Address?.split(',')[0] || '[Street Name]'}</strong> and was getting in touch because we are kicking off a huge promotion and support of local business.</p>
                  <p class="script-text">We are going to be featuring and recommending just a few great local businesses, and right now I am looking to recommend just one <strong>{selectedSubcategory || selectedCategory || '[Business Type]'}</strong> to all of their shoppers.</p>
                  <p class="script-text">We already work with a ton of <strong>{selectedSubcategory || selectedCategory || '[Business Type]'}s</strong> with huge success in driving customers, and I was curious, <em>who should I talk to about doing the same for you?</em></p>
                  <button class="action-btn full-width" on:click={() => {
                    const script = `Hey there, I was hoping you could point me in the right direction on something…?\n\nMy name is ${$user?.name || $user?.first_name || '[Your Name]'} and I was calling because I'm working with the ${selectedStore?.GroceryChain || '[Store Chain]'} over on ${selectedStore?.Address?.split(',')[0] || '[Street Name]'} and was getting in touch because we are kicking off a huge promotion and support of local business.\n\nWe are going to be featuring and recommending just a few great local businesses, and right now I am looking to recommend just one ${selectedSubcategory || selectedCategory || '[Business Type]'} to all of their shoppers.\n\nWe already work with a ton of ${selectedSubcategory || selectedCategory || '[Business Type]'}s with huge success in driving customers, and I was curious, who should I talk to about doing the same for you?`;
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
            <div class="email-section">
              <h4 class="email-title">Choose a template:</h4>
              {#each emailTemplates as tpl}
                <button class="email-tpl-btn" on:click={() => { prospect._selectedTpl = tpl.id; prospects = prospects; }}>
                  {tpl.icon} {tpl.name}
                </button>
              {/each}
              {#if prospect._selectedTpl}
                {@const tpl = emailTemplates.find(t => t.id === prospect._selectedTpl)}
                <div class="email-preview-box">
                  <p class="email-subject">Subject: {fillTemplate(tpl.subject, prospect.name)}</p>
                  <p class="email-body-text">{fillTemplate(tpl.body, prospect.name)}</p>
                  <button class="action-btn full-width email-btn" on:click={() => {
                    const subject = encodeURIComponent(fillTemplate(tpl.subject, prospect.name));
                    const rawBody = fillTemplate(tpl.body, prospect.name);
                    const body = encodeURIComponent(rawBody.replace(/\n\n/g, '\r\n\r\n').replace(/(?<!\r)\n/g, '\r\n'));
                    window.open('mailto:?subject=' + subject + '&body=' + body);
                  }}>📧 Open in Email App</button>
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
                  <select class="status-select" value={prospect.status} on:change={(e) => { prospect.status = e.target.value; updateProspectNotes(prospect.id, prospect.notes); savedProspects = savedProspects; localStorage.setItem('savedProspects', JSON.stringify(savedProspects)); }}>
                    <option value="new">🆕 New</option>
                    <option value="contacted">⏳ Contacted</option>
                    <option value="proposal">📋 Proposal</option>
                    <option value="closed">🎉 Closed</option>
                  </select>
                  <button class="delete-btn" on:click={() => deleteProspect(prospect.id)}>🗑️ Delete</button>
                </div>
                {#each [leadDataCache[getLeadHash(prospect)] || {}] as savedLd}
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
            <div class="hot-lead-card">
              <div class="lead-header">
                <h4>{lead.business_name}</h4>
                {#if lead.rating}
                  <span class="rating">⭐{lead.rating}</span>
                {/if}
              </div>
              <div class="lead-category">{lead.category}</div>
              {#if lead._hook}
                <div class="lead-hook">"{lead._hook}"</div>
              {/if}
              <div class="lead-contact">
                {#if lead.phone}
                  <a href="tel:{lead.phone}" class="phone">📞 {lead.phone}</a>
                {/if}
                {#if lead._email || lead.website}
                  <a href="mailto:{lead._email || ''}" class="email">📧 Email</a>
                {/if}
              </div>
              {#if lead.address}
                <div class="lead-address" style="cursor:pointer;" on:click={() => { navigator.clipboard.writeText(lead.address); copiedAddress = lead.address; setTimeout(() => copiedAddress = '', 2000); }}>📍 {copiedAddress === lead.address ? '✅ Copied!' : lead.address}</div>
              {/if}
              <div class="lead-store">{lead.store_chain} {lead.store_city} ({lead.store_id})</div>
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
</div>

<style>
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
  .prospect-card.swipeable { cursor: grab; touch-action: pan-y; }
  .swipe-indicator {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    font-size: 22px;
    font-weight: 800;
    padding: 8px 16px;
    border-radius: 10px;
    z-index: 10;
    pointer-events: none;
  }
  .swipe-book { right: 16px; color: #fff; background: rgba(34,139,34,0.85); }
  .swipe-skip { left: 16px; color: #fff; background: rgba(204,0,0,0.85); }
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
  .prospect-phone { margin: 6px 0 10px; font-size: 15px; font-weight: 600; color: var(--text-primary); }
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
