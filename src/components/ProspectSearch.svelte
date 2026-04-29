<script>
  import { onMount, onDestroy, tick } from 'svelte';
  import { user } from '../lib/stores.js';
  import { logActivity } from '../lib/activity.js';
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
  let allContracts = []; // For attribution matching
  let phoneClicks = []; // Track call history
  let hotLeads = [];
  let view = 'main'; // main, nearby-stores, categories, subcategories, results, saved, hot-leads, pending, submit-lead
  let selectedCycle = 'all'; // all, A, B, C
  let storesViewMode = 'list'; // list or map
  let prospectsViewMode = 'list'; // list or map
  let subcatsViewMode = 'list'; // list or map
  let categoriesViewMode = 'list'; // list or map
  let selectedStore = null;
  
  // Map state
  let storeMapContainer;
  let storeMap;
  let prospectMapContainer;
  let prospectMap;
  let subcatMapContainer;
  let subcatMap;
  let categoriesMapContainer;
  let categoriesMap;
  
  async function initStoreMap() {
    await tick();
    if (!storeMapContainer || storeMap) return;
    const filtered = nearbyStores.filter(s => selectedCycle === 'all' || s.Cycle === selectedCycle);
    if (filtered.length === 0) return;
    
    const firstWithCoords = filtered.find(s => s.latitude && s.longitude);
    const center = firstWithCoords ? [firstWithCoords.latitude, firstWithCoords.longitude] : [45.5, -122.5];
    
    storeMap = L.map(storeMapContainer, { center, zoom: 10, zoomControl: true });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap',
      maxZoom: 19,
    }).addTo(storeMap);
    
    const bounds = [];
    filtered.forEach(store => {
      if (!store.latitude || !store.longitude) return;
      bounds.push([store.latitude, store.longitude]);
      
      const marker = L.circleMarker([store.latitude, store.longitude], {
        radius: 10,
        fillColor: '#CC0000',
        color: '#fff',
        weight: 2,
        fillOpacity: 0.9,
      }).addTo(storeMap);
      
      marker.bindPopup(`
        <div style="min-width: 180px;">
          <strong>${store.GroceryChain}</strong><br>
          <span style="font-size:12px;">${store.Address || ''}</span><br>
          <span style="font-size:12px;">${store.City}, ${store.State}</span><br>
          <span style="font-size:11px; color:#666;">Cycle ${store.Cycle || '?'} · ${store.StoreName}</span><br>
          <span style="font-size:11px; color:#666;">${store.distance ? store.distance.toFixed(1) + ' mi' : ''} ${store['Case Count'] ? '· ' + store['Case Count'] + ' cases' : ''}</span><br>
          <button onclick="document.dispatchEvent(new CustomEvent('select-store-from-map', {detail: '${store.StoreName}'}))" 
            style="margin-top:8px; background:#CC0000; color:white; border:none; border-radius:6px; padding:8px 12px; font-size:12px; font-weight:600; cursor:pointer; width:100%;">
            🎯 Find Prospects
          </button>
        </div>
      `);
    });
    
    if (bounds.length > 1) storeMap.fitBounds(bounds, { padding: [30, 30] });
  }
  
  function destroyStoreMap() {
    if (storeMap) { storeMap.remove(); storeMap = null; }
  }
  
  async function initProspectMap() {
    await tick();
    if (!prospectMapContainer || prospectMap) return;
    if (prospects.length === 0) return;
    
    // Use store location as center, or first prospect
    const storeLat = selectedStore?.latitude;
    const storeLng = selectedStore?.longitude;
    const center = storeLat && storeLng ? [storeLat, storeLng] : 
      (prospects[0]?.lat && prospects[0]?.lng ? [prospects[0].lat, prospects[0].lng] : [45.5, -122.5]);
    
    prospectMap = L.map(prospectMapContainer, { center, zoom: 13, zoomControl: true });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap',
      maxZoom: 19,
    }).addTo(prospectMap);
    
    // Add store marker (star)
    if (storeLat && storeLng) {
      L.circleMarker([storeLat, storeLng], {
        radius: 14,
        fillColor: '#CC0000',
        color: '#fff',
        weight: 3,
        fillOpacity: 1,
      }).addTo(prospectMap).bindPopup(`<strong>🏪 ${selectedStore.GroceryChain}</strong><br>${selectedStore.City}, ${selectedStore.State}`);
    }
    
    const bounds = storeLat && storeLng ? [[storeLat, storeLng]] : [];
    
    prospects.forEach((p, i) => {
      const lat = p.lat || p.latitude;
      const lng = p.lng || p.longitude;
      if (!lat || !lng) return;
      bounds.push([lat, lng]);
      
      const score = p.score || 0;
      const color = score >= 80 ? '#22c55e' : score >= 70 ? '#f59e0b' : '#6b7280';
      const emoji = score >= 80 ? '🔥' : score >= 70 ? '⭐' : '👀';
      
      const marker = L.circleMarker([lat, lng], {
        radius: 8,
        fillColor: color,
        color: '#fff',
        weight: 2,
        fillOpacity: 0.9,
      }).addTo(prospectMap);
      
      marker.bindPopup(`
        <div style="min-width: 200px;">
          <strong>${emoji} ${p.name}</strong><br>
          <span style="font-size:12px;">📍 ${p.address || ''}</span><br>
          <span style="font-size:12px;">⭐ ${(p.rating || 0).toFixed(1)} (${p.reviews || 0} reviews) · ${p.distance || '?'} mi</span><br>
          <span style="font-size:11px; color:#666;">Score: ${score}%</span><br>
          ${p.phone ? `<a href="tel:${p.phone}" style="display:block; margin-top:6px; background:#CC0000; color:white; text-align:center; border-radius:6px; padding:6px; font-size:12px; font-weight:600; text-decoration:none;">📞 ${p.phone}</a>` : ''}
          ${p.website ? `<a href="${p.website}" target="_blank" style="display:block; margin-top:4px; background:#2563eb; color:white; text-align:center; border-radius:6px; padding:6px; font-size:12px; font-weight:600; text-decoration:none;">🌐 Website</a>` : ''}
        </div>
      `);
    });
    
    if (bounds.length > 1) prospectMap.fitBounds(bounds, { padding: [30, 30] });
  }
  
  function destroyProspectMap() {
    if (prospectMap) { prospectMap.remove(); prospectMap = null; }
  }

  async function initSubcatMap() {
    await tick();
    if (!subcatMapContainer || subcatMap) return;
    
    const center = [selectedStore?.latitude || 45.5, selectedStore?.longitude || -122.5];
    subcatMap = L.map(subcatMapContainer, { center, zoom: 12, zoomControl: true });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap',
      maxZoom: 19,
    }).addTo(subcatMap);
    
    // Add store marker
    if (selectedStore?.latitude && selectedStore?.longitude) {
      L.circleMarker([selectedStore.latitude, selectedStore.longitude], {
        radius: 12,
        fillColor: '#CC0000',
        color: '#fff',
        weight: 3,
        fillOpacity: 1,
      }).addTo(subcatMap).bindPopup(`<strong>🏪 ${selectedStore.GroceryChain}</strong>`);
    }
  }

  function destroySubcatMap() {
    if (subcatMap) { subcatMap.remove(); subcatMap = null; }
  }

  async function initCategoriesMap() {
    await tick();
    if (!categoriesMapContainer || categoriesMap) return;
    
    const center = [selectedStore?.latitude || 45.5, selectedStore?.longitude || -122.5];
    categoriesMap = L.map(categoriesMapContainer, { center, zoom: 12, zoomControl: true });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap',
      maxZoom: 19,
    }).addTo(categoriesMap);
    
    // Add store marker
    if (selectedStore?.latitude && selectedStore?.longitude) {
      L.circleMarker([selectedStore.latitude, selectedStore.longitude], {
        radius: 12,
        fillColor: '#CC0000',
        color: '#fff',
        weight: 3,
        fillOpacity: 1,
      }).addTo(categoriesMap).bindPopup(`<strong>🏪 ${selectedStore.GroceryChain}</strong>`);
    }
  }

  function destroyCategoriesMap() {
    if (categoriesMap) { categoriesMap.remove(); categoriesMap = null; }
  }
  
  // React to view mode changes
  $: if (storesViewMode === 'map') { destroyStoreMap(); setTimeout(initStoreMap, 50); } else { destroyStoreMap(); }
  $: if (prospectsViewMode === 'map') { destroyProspectMap(); setTimeout(initProspectMap, 50); } else { destroyProspectMap(); }
  $: if (subcatsViewMode === 'map') { destroySubcatMap(); setTimeout(initSubcatMap, 50); } else { destroySubcatMap(); }
  $: if (categoriesViewMode === 'map') { destroyCategoriesMap(); setTimeout(initCategoriesMap, 50); } else { destroyCategoriesMap(); }
  $: if (storesViewMode === 'map' && selectedCycle) { destroyStoreMap(); setTimeout(initStoreMap, 50); }
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
    const store = nearbyStores.find(s => s.StoreName === storeName) || allStores.find(s => s.StoreName === storeName);
    if (store) selectStore(store);
  }
  
  onMount(async () => {
    document.addEventListener('select-store-from-map', handleStoreSelectFromMap);
    try {
      const response = await fetch(import.meta.env.BASE_URL + 'data/video_library.json');
      videoLibrary = await response.json();
    } catch (e) {
      console.warn('Could not load video library:', e);
    }
    // Load contracts for attribution
    try {
      const cRes = await fetch(import.meta.env.BASE_URL + 'data/contracts.json');
      const cData = await cRes.json();
      allContracts = cData.contracts || cData || [];
    } catch { allContracts = []; }
    // Load phone click history
    try {
      phoneClicks = JSON.parse(localStorage.getItem('impro_phone_clicks') || '[]');
    } catch { phoneClicks = []; }
  });
  
  onDestroy(() => {
    document.removeEventListener('select-store-from-map', handleStoreSelectFromMap);
    destroyStoreMap();
    destroyProspectMap();
    destroySubcatMap();
    destroyCategoriesMap();
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
        if (!response?.ok) response = await fetch(import.meta.env.BASE_URL + 'data/testimonials_cache.json');
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
        fetch(import.meta.env.BASE_URL + 'data/stores.json'),
        fetch(import.meta.env.BASE_URL + 'data/hot_leads.json?t=' + Date.now()),
        fetch(import.meta.env.BASE_URL + 'data/rep_registry.json').catch(() => ({ json: () => ({}) }))
      ]);
      allStores = await storesRes.json();
      repRegistry = await repRes.json().catch(() => ({}));
      
      // Load hot leads - scoped to stores rep has sold at, filtered by current cycle
      let allLeadsData = await leadsRes.json();
      
      // Load contracts to find which stores this rep has sold at
      let repStoreIds = new Set();
      try {
        const contractsRes = await fetch(import.meta.env.BASE_URL + 'data/contracts.json');
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
          'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.location,places.businessStatus,places.nationalPhoneNumber,places.websiteUri,places.googleMapsUri'
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

  const emailTemplates = [
    { id: 'initial', icon: '🎯', name: 'Initial Appointment',
      subject: 'Quick question about {business}',
      body: 'Hi {contact},\n\nI noticed {business} in the area and wanted to reach out. We work with local businesses to help drive foot traffic through register tape advertising at nearby grocery stores.\n\nThousands of businesses like yours have seen measurable results — would you be open to a quick 10-minute chat this week?\n\nBest,\n{rep}\nIndoorMedia' },
    { id: 'roi', icon: '📊', name: 'ROI / Value Focused',
      subject: 'How {business} can reach 10,000+ local customers',
      body: 'Hi {contact},\n\nDid you know the average grocery store gets 10,000+ visitors per week? That\'s 10,000 potential customers seeing your ad every single week.\n\nBusinesses in your category have reported strong ROI — many seeing results within the first month. Our register tape ads put your name, offer, and location directly in shoppers\' hands.\n\nI\'d love to show you how the numbers work for {business}. Can we schedule a quick call?\n\nBest,\n{rep}\nIndoorMedia' },
    { id: 'followup', icon: '⏰', name: 'Follow-up (No Response)',
      subject: 'Following up — {business}',
      body: 'Hi {contact},\n\nI reached out a few days ago about a potential partnership with {business} and wanted to follow up.\n\nWe help local businesses reach thousands of nearby shoppers each week through register tape advertising. I think there\'s a great fit here.\n\nWould you have 10 minutes this week for a quick chat?\n\nBest,\n{rep}\nIndoorMedia' },
    { id: 'reengagement', icon: '🔄', name: 'Re-engagement',
      subject: 'Things have changed — {business}',
      body: 'Hi {contact},\n\nIt\'s been a while since we last connected about {business}. A lot has changed at IndoorMedia — new store locations, better pricing, and stronger results for businesses like yours.\n\nWould you be open to reconnecting for a quick 10-minute call?\n\nBest,\n{rep}\nIndoorMedia' },
    { id: 'limited', icon: '⚡', name: 'Limited Time Offer',
      subject: 'Limited availability near {business}',
      body: 'Hi {contact},\n\nI wanted to give you a heads up — we have limited ad placement availability at the grocery store near {business}.\n\nOur partnership program is filling up fast, and I\'d hate for {business} to miss out on reaching thousands of local shoppers each week.\n\nCan we schedule a quick call this week?\n\nBest,\n{rep}\nIndoorMedia' },
  ];

  function loadSavedProspects() {
    const saved = localStorage.getItem('savedProspects');
    savedProspects = saved ? JSON.parse(saved) : [];
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
    const pWords = pName.split(' ').filter(w => w.length > 2);
    const pPhone = (prospect.phone || '').replace(/\D/g, '');
    
    // Find matching contract
    const match = allContracts.find(c => {
      const cName = norm(c.business_name);
      const cPhone = (c.contact_phone || '').replace(/\D/g, '');
      
      // Phone match (strongest)
      if (pPhone && cPhone && (pPhone.includes(cPhone) || cPhone.includes(pPhone))) return true;
      
      // Business name fuzzy match
      const cWords = cName.split(' ').filter(w => w.length > 2);
      const common = pWords.filter(w => cWords.some(cw => cw.includes(w) || w.includes(cw)));
      return common.length >= 1 && (common.length / Math.min(pWords.length, cWords.length)) >= 0.5;
    });
    
    if (!match) return null;
    
    // Check if there's a phone click for this prospect
    const callMade = phoneClicks.find(c => {
      const cBiz = norm(c.business);
      return pWords.some(w => cBiz.includes(w));
    });
    
    return { contract: match, callMade };
  }

  function saveProspect(prospect) {
    if (!savedProspects.find(p => p.id === prospect.id)) {
      savedProspects = [...savedProspects, { ...prospect, savedAt: new Date().toISOString(), status: 'new', notes: '' }];
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
      <button class="tab-btn" class:active={view === 'pending'} on:click={() => view = 'pending'}>⏳ Pending</button>
      <button class="tab-btn" class:active={view === 'submit-lead'} on:click={() => view = 'submit-lead'}>➕ Add Lead</button>
    {/if}
  </div>

  <!-- Main Menu -->
  {#if view === 'main'}
    <h2>🎯 Find Prospects</h2>
    <p class="subtitle">Discover new business opportunities</p>

    <div class="button-grid">
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

    <div class="view-toggle" style="display: flex; gap: 12px; margin: 16px 0; padding: 16px; background: #CC0000; border-radius: 12px; justify-content: center; align-items: center; position: relative; z-index: 100;">
      <button class="toggle-btn" class:active={storesViewMode === 'list'} on:click={() => { console.log('List clicked'); storesViewMode = 'list'; }} style="flex: 1; padding: 16px; font-size: 18px; font-weight: 700; background: white; color: #333;">📋 List</button>
      <button class="toggle-btn" class:active={storesViewMode === 'map'} on:click={() => { console.log('Map clicked'); storesViewMode = 'map'; }} style="flex: 1; padding: 16px; font-size: 18px; font-weight: 700; background: white; color: #333;">🗺️ Map</button>
    </div>

    {#if storesViewMode === 'list'}
    <div class="store-list">
      {#each nearbyStores.filter(s => selectedCycle === 'all' || s.Cycle === selectedCycle) as store (store.StoreName)}
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
      {/each}
    </div>
    {:else if storesViewMode === 'map'}
    <div bind:this={storeMapContainer} style="height: 500px; margin: 16px 0; border-radius: 12px; overflow: hidden; border: 2px solid var(--border-color, #ddd);"></div>
    <p style="font-size: 12px; color: #999; text-align: center; margin: 8px 0;">🔴 = Store · Tap for details & "Find Prospects" · {nearbyStores.filter(s => selectedCycle === 'all' || s.Cycle === selectedCycle).length} stores shown</p>
    {/if}
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

    <div class="view-toggle" style="display: flex; gap: 12px; margin: 16px 0; padding: 16px; background: #CC0000; border-radius: 12px; justify-content: center; align-items: center; position: relative; z-index: 100;">
      <button class="toggle-btn" class:active={categoriesViewMode === 'list'} on:click={() => categoriesViewMode = 'list'} style="flex: 1; padding: 16px; font-size: 18px; font-weight: 700; background: white; color: #333;">📋 List</button>
      <button class="toggle-btn" class:active={categoriesViewMode === 'map'} on:click={() => categoriesViewMode = 'map'} style="flex: 1; padding: 16px; font-size: 18px; font-weight: 700; background: white; color: #333;">🗺️ Map</button>
    </div>

    {#if selectedStore && selectedStore.StoreName}
      <button 
        class="roogle-load-btn"
        on:click={promptForCredentials}
        disabled={loadingCustomers}
      >
        {loadingCustomers ? '⏳ Loading...' : '🔄 Load Roogle Customers'}
      </button>
      {#if customerLoadMessage}
        <p class="customer-load-msg">{customerLoadMessage}</p>
      {/if}
    {/if}

    {#if showCredentialsModal}
      <div class="credentials-modal-overlay" on:click={closeCredentialsModal}>
        <div class="credentials-modal" on:click={(e) => e.stopPropagation()}>
          <h3>🔐 Roogle Login</h3>
          <p class="modal-subtitle">Enter your sales.indoormedia.com credentials</p>
          
          <div class="form-group">
            <label>Email</label>
            <input 
              type="email"
              bind:value={roogleEmail}
              placeholder="tyler.vansant@indoormedia.com"
            />
          </div>

          <div class="form-group">
            <label>Password</label>
            <input 
              type="password"
              bind:value={rooglePassword}
              placeholder="Enter your password"
            />
          </div>

          <div class="modal-actions">
            <button class="btn-load" on:click={submitCredentialsAndLoad}>Load Customers</button>
            <button class="btn-cancel" on:click={closeCredentialsModal}>Cancel</button>
          </div>
          
          <p class="modal-note">✅ Your credentials are only sent to Roogle. They won't be stored.</p>
        </div>
      </div>
    {/if}

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

    {#if categoriesViewMode === 'list'}
      <div class="category-grid">
        {#each Object.keys(CATEGORIES) as cat}
          <button class="category-btn" on:click={() => selectCategory(cat)}>
            {cat}
          </button>
        {/each}
      </div>
    {:else if categoriesViewMode === 'map'}
      <div bind:this={categoriesMapContainer} style="height: 500px; margin: 16px 0; border-radius: 12px; overflow: hidden; border: 2px solid var(--border-color, #ddd);"></div>
      <p style="font-size: 12px; color: #999; text-align: center; margin: 8px 0;">📍 Store location · Click "List" to browse categories</p>
    {/if}
  {/if}

  <!-- Subcategory Selection -->
  {#if view === 'subcategories'}
    <button class="back-btn" on:click={goBack}>← {selectedCategory}</button>
    <h3>Choose a type</h3>

    <div class="view-toggle" style="display: flex; gap: 12px; margin: 16px 0; padding: 16px; background: #f9f9f9; border-radius: 12px; justify-content: center; align-items: center;">
      <button class="toggle-btn" class:active={subcatsViewMode === 'list'} on:click={() => subcatsViewMode = 'list'} style="flex: 1; padding: 14px; font-size: 16px; font-weight: 700;">📋 List</button>
      <button class="toggle-btn" class:active={subcatsViewMode === 'map'} on:click={() => subcatsViewMode = 'map'} style="flex: 1; padding: 14px; font-size: 16px; font-weight: 700;">🗺️ Map</button>
    </div>

    {#if subcatsViewMode === 'list'}
      <div class="subcat-grid">
        {#each CATEGORIES[selectedCategory] as subcat}
          <button class="subcat-btn" on:click={() => selectSubcategory(subcat)}>
            {subcat}
          </button>
        {/each}
      </div>
    {:else if subcatsViewMode === 'map'}
      <div bind:this={subcatMapContainer} style="height: 500px; margin: 16px 0; border-radius: 12px; overflow: hidden; border: 2px solid var(--border-color, #ddd);"></div>
      <p style="font-size: 12px; color: #999; text-align: center; margin: 8px 0;">🟢 = High match (80%+) · 🟡 = Good match (70%+) · ⚪ = Other · Tap a marker to select category</p>
    {/if}
  {/if}

  <!-- Prospect Results -->
  {#if view === 'results'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h3>{selectedCategory} → {selectedSubcategory}</h3>
    <p class="subtitle">Nearby {selectedCategory} near {selectedStore.GroceryChain}</p>

    <div style="display: flex; gap: 8px; margin: 12px 0; justify-content: space-between; align-items: center;">
      <div class="sort-bar">
        <span class="sort-label">Sort:</span>
        <button class="sort-btn" class:active={prospectSort === 'score'} on:click={() => prospectSort = 'score'}>🎯 Score</button>
        <button class="sort-btn" class:active={prospectSort === 'distance'} on:click={() => prospectSort = 'distance'}>📍 Distance</button>
        <button class="sort-btn" class:active={prospectSort === 'rating'} on:click={() => prospectSort = 'rating'}>⭐ Rating</button>
        <button class="sort-btn" class:active={prospectSort === 'reviews'} on:click={() => prospectSort = 'reviews'}>💬 Reviews</button>
      </div>
      <div class="view-toggle" style="display: flex; gap: 8px; flex-shrink: 0;">
        <button class="toggle-btn" class:active={prospectsViewMode === 'list'} on:click={() => prospectsViewMode = 'list'} style="padding: 10px 14px; font-size: 14px; font-weight: 700;">📋 List</button>
        <button class="toggle-btn" class:active={prospectsViewMode === 'map'} on:click={() => prospectsViewMode = 'map'} style="padding: 10px 14px; font-size: 14px; font-weight: 700;">🗺️ Map</button>
      </div>
    </div>

    {#if prospectsViewMode === 'list'}
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
            <p class="prospect-phone">📞 {prospect.phone}</p>
          {/if}
          <div class="prospect-actions">
            {#if prospect.website}
              <a href={prospect.website} target="_blank" class="action-btn full-width">🌐 Website</a>
            {/if}
            <div class="action-row">
              {#if prospect.mapsUrl}
                <a href={prospect.mapsUrl} target="_blank" class="action-btn">📍 Maps</a>
              {:else}
                <a href="https://maps.google.com/maps?q={encodeURIComponent(prospect.name + ' ' + prospect.address)}" target="_blank" class="action-btn">📍 Maps</a>
              {/if}
              <a href="https://sales.indoormedia.com/mappoint" target="_blank" class="action-btn">🗺️ Mappoint</a>
              <a href="https://coupons.indoormedia.com/?location={encodeURIComponent((selectedStore?.City || '') + ', ' + (selectedStore?.State || ''))}" target="_blank" class="action-btn">📋 Nearby Advertisers</a>
            </div>
            <div class="action-row">
              <button class="action-btn" on:click={() => saveProspect(prospect)}>💾 Save</button>
              {#if getVideoForCategory()}
                <a href={getVideoForCategory().url} target="_blank" class="action-btn">🎬 Video</a>
              {:else}
                <a href="https://www.google.com/search?q={encodeURIComponent('IndoorMedia ' + (selectedSubcategory || selectedCategory || 'testimonial'))}&tbm=vid" target="_blank" class="action-btn">🎬 Video</a>
              {/if}
            </div>
            <div class="action-row">
              <button class="action-btn" on:click={() => { prospect._showNotes = !prospect._showNotes; prospects = prospects; }}>📝 Notes</button>
              <button class="action-btn testimonial-btn" on:click={async () => { 
                prospect._showTestimonials = !prospect._showTestimonials;
                if (prospect._showTestimonials) {
                  prospect._testimonialData = await getTestimonialsForCategory();
                }
                prospects = prospects;
              }}>📋 Testimonials</button>
            </div>
            {#if prospect.phone}
              <div class="action-row">
                <a href="tel:{prospect.phone}" class="action-btn call-btn" on:click={() => trackPhoneClick(prospect)}>📞 Call {prospect.phone}</a>
                <a href="sms:{prospect.phone}" class="action-btn text-btn">💬 Text</a>
              </div>
            {/if}
            <button class="action-btn full-width script-btn" on:click={() => { prospect._showScript = !prospect._showScript; prospect._showEmail = false; prospect._showNotes = false; prospects = prospects; }}>📋 Call Scripts</button>
            <button class="action-btn full-width email-btn" on:click={() => { prospect._showEmail = !prospect._showEmail; prospect._showScript = false; prospect._showNotes = false; prospects = prospects; }}>✉️ Draft Email</button>
            <div class="calendar-booking">
              <div class="invite-row">
                <select bind:value={inviteRepEmail} class="invite-select">
                  <option value="">No invite (just me)</option>
                  {#each Object.entries(repRegistry).filter(([k, v]) => v.email) as [id, rep]}
                    <option value={rep.email}>{rep.display_name || rep.contract_name}</option>
                  {/each}
                </select>
              </div>
              <a href="https://calendar.google.com/calendar/render?action=TEMPLATE&text={encodeURIComponent('Visit: ' + prospect.name)}&details={encodeURIComponent('Prospect: ' + prospect.name + '\nAddress: ' + prospect.address + (prospect.phone ? '\nPhone: ' + prospect.phone : '') + (prospect.website ? '\nWebsite: ' + prospect.website : '') + '\nStore: ' + (selectedStore?.GroceryChain || '') + ' ' + (selectedStore?.StoreName || '') + '\nRep: ' + ($user?.name || '') + (getProspectNote(prospect.id || prospect.name) ? '\n\n📝 Notes:\n' + getProspectNote(prospect.id || prospect.name) : ''))}&location={encodeURIComponent(prospect.address)}&add={encodeURIComponent('tyler.vansant@indoormedia.com')}{inviteRepEmail ? ',' + encodeURIComponent(inviteRepEmail) : ''}" target="_blank" class="action-btn full-width calendar-btn">📅 Book Appointment (invites manager{inviteRepEmail ? ' + rep' : ''})</a>
            </div>
          </div>
          {#if prospect._showTestimonials}
            <div class="testimonials-section">
              <h4 class="testimonials-title">📋 Testimonials for {selectedSubcategory || selectedCategory || 'this category'}</h4>
              {#if prospect._testimonialData && prospect._testimonialData.length > 0}
                {#if prospect._testimonialData.filter(t => t.url).length > 1}
                  <button class="open-all-testimonials-btn" on:click|stopPropagation={() => { prospect._testimonialData.filter(t => t.url).forEach(t => window.open(t.url, '_blank')); }}>
                    📂 Open All ({prospect._testimonialData.filter(t => t.url).length})
                  </button>
                {/if}
                {#each prospect._testimonialData as testimonial}
                  <div class="testimonial-card" class:local-testimonial={testimonial._isLocal} class:clickable-testimonial={testimonial.url} on:click|stopPropagation={() => { if (testimonial.url) window.open(testimonial.url, '_blank'); }}>
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
            <div class="notes-section">
              <textarea 
                placeholder="Add notes about this prospect..." 
                rows="3"
                value={getProspectNote(prospect.id || prospect.name)}
                on:input={(e) => saveProspectNote(prospect.id || prospect.name, e.target.value)}
              ></textarea>
              {#if getProspectNote(prospect.id || prospect.name)}
                <p class="note-saved">Saved</p>
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
                  <p class="email-subject">Subject: {tpl.subject.replace('{business}', prospect.name)}</p>
                  <p class="email-body-text">{tpl.body.replace(/\{business\}/g, prospect.name).replace(/\{contact\}/g, '').replace(/\{rep\}/g, $user?.name || $user?.first_name || 'Your Rep')}</p>
                  <button class="action-btn full-width email-btn" on:click={() => {
                    const subject = encodeURIComponent(tpl.subject.replace('{business}', prospect.name));
                    const rawBody = tpl.body.replace(/\{business\}/g, prospect.name).replace(/\{contact\}/g, '').replace(/\{rep\}/g, $user?.name || $user?.first_name || 'Your Rep');
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
    {:else if prospectsViewMode === 'map'}
    <div bind:this={prospectMapContainer} style="height: 500px; margin: 16px 0; border-radius: 12px; overflow: hidden; border: 2px solid var(--border-color, #ddd);"></div>
    <p style="font-size: 12px; color: #999; text-align: center; margin: 8px 0;">🔴 = Store · 🟢 = Hot (80%+) · 🟡 = Warm (70%+) · ⚪ = Cool · Tap for details · {prospects.length} businesses</p>
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
                <textarea placeholder="Add notes..." class="notes-input" value={prospect.notes} on:change={(e) => updateProspectNotes(prospect.id, e.target.value)}></textarea>
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
  .open-all-testimonials-btn { display: block; width: 100%; padding: 10px; margin-bottom: 10px; border-radius: 8px; border: 2px solid #CC0000; background: white; color: #CC0000; font-size: 14px; font-weight: 600; cursor: pointer; text-align: center; }
  .open-all-testimonials-btn:active { background: #CC0000; color: white; }
  :global([data-theme='dark']) .open-all-testimonials-btn { background: #1e1e1e; border-color: #ff6666; color: #ff6666; }
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

  .btn-icon { font-size: 2rem; margin-bottom: 0.5rem; }
  .btn-text { font-weight: 600; color: var(--text-primary); margin-bottom: 0.25rem; }
  .btn-desc { font-size: 0.85rem; color: var(--text-tertiary); }

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

  .sort-bar { display: flex; align-items: center; gap: 6px; margin-bottom: 12px; overflow-x: auto; white-space: nowrap; padding-bottom: 4px; }
  .sort-label { font-size: 12px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; flex-shrink: 0; }
  .sort-btn { padding: 6px 12px; border: 1px solid var(--border-color); border-radius: 16px; background: var(--card-bg); font-size: 12px; font-weight: 600; cursor: pointer; color: var(--text-secondary); transition: all 0.2s; flex-shrink: 0; }
  .sort-btn.active { background: #CC0000; color: white; border-color: #CC0000; }
  .sort-btn:hover:not(.active) { border-color: #CC0000; color: #CC0000; }
  .prospect-list { display: flex; flex-direction: column; gap: 1rem; }

  .prospect-card {
    background: var(--card-bg, #ffffff);
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
    border: 1px solid #e8e8e8;
    color: var(--text-primary);
    transition: box-shadow 0.2s;
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
  .prospect-phone { margin: 6px 0 10px; font-size: 15px; font-weight: 600; color: var(--text-primary); }

  .prospect-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    padding-top: 10px;
    border-top: 1px solid var(--border-color);
  }

  .action-btn {
    flex: 1;
    min-width: 60px;
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
  }

  .action-btn:hover { background: #cc0000; color: white; }

  .action-row {
    display: flex;
    gap: 8px;
    width: 100%;
  }

  .action-row .action-btn { flex: 1; }

  .full-width { width: 100%; flex: none !important; }

  .call-btn { background: #2e7d32 !important; color: white !important; border-color: #2e7d32 !important; }
  .call-btn:hover { background: #1b5e20 !important; }
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
  .invite-row { margin-bottom: 8px; }
  .invite-select { width: 100%; padding: 10px 12px; border: 2px solid var(--border-color, #ddd); border-radius: 8px; font-size: 13px; background: var(--input-bg, white); color: var(--text-primary, #333); }
  .calendar-btn { background: #1a73e8 !important; color: white !important; }
  .calendar-btn:hover { background: #1557b0 !important; }
</style>
