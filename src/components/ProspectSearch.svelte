<script>
  import { onMount } from 'svelte';
  import { user } from '../lib/stores.js';
  import HotLeadsSubmit from './HotLeadsSubmit.svelte';
  import PendingLeads from './PendingLeads.svelte';
  
  let allStores = [];
  let nearbyStores = [];
  let prospects = [];
  let savedProspects = [];
  let hotLeads = [];
  let view = 'main'; // main, nearby-stores, categories, subcategories, results, saved, hot-leads, pending, submit-lead
  let selectedStore = null;
  let selectedCategory = null;
  let selectedSubcategory = null;
  let userLocation = null;
  let loading = false;
  let error = '';
  let searchInput = '';
  let customSearch = '';
  let storeSearchQuery = '';
  let filteredStoreResults = [];

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
      const [storesRes, leadsRes] = await Promise.all([
        fetch('/data/stores.json'),
        fetch('/data/hot_leads.json')
      ]);
      allStores = await storesRes.json();
      
      // Load hot leads (filtered by rep visibility)
      let allLeadsData = await leadsRes.json();
      const isManager = $user?.name?.toLowerCase().includes('tyler') || $user?.role === 'manager' || $user?.role === 'admin';
      
      if (!isManager && $user?.assigned_stores) {
        const assignedStoreIds = Array.isArray($user.assigned_stores) ? $user.assigned_stores : [$user.assigned_stores];
        hotLeads = allLeadsData.filter(l => assignedStoreIds.includes(l.store_id));
      } else if (!isManager) {
        hotLeads = [];
      } else {
        hotLeads = allLeadsData;
      }
      
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

  function selectStore(store) {
    selectedStore = store;
    view = 'categories';
  }

  function selectCategory(cat) {
    selectedCategory = cat;
    view = 'subcategories';
  }

  async function searchCustom() {
    if (!customSearch.trim()) return;
    loading = true;
    error = '';
    selectedSubcategory = customSearch.trim();

    try {
      const results = await searchGooglePlaces(selectedStore.latitude, selectedStore.longitude, customSearch.trim());
      prospects = results;
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
      const hasRealCoords = selectedStore && !isBadCoords(lat, lng);
      
      // If store has bad/dummy coords, put city+state in the query text instead
      const textQuery = hasRealCoords ? keyword : `${keyword} near ${storeCity}, ${storeState}`;
      
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
      }).sort((a, b) => b.score - a.score);
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

  function filterStoresForProspecting() {
    if (!storeSearchQuery.trim()) {
      filteredStoreResults = [];
      return;
    }
    const term = storeSearchQuery.toLowerCase();
    filteredStoreResults = allStores.filter(s =>
      (s.StoreName && s.StoreName.toLowerCase().includes(term)) ||
      (s.GroceryChain && s.GroceryChain.toLowerCase().includes(term)) ||
      (s.City && s.City.toLowerCase().includes(term)) ||
      (s.State && s.State.toLowerCase().includes(term)) ||
      (s.Address && s.Address.toLowerCase().includes(term))
    ).slice(0, 20);
  }

  function selectStoreFromBrowse(store) {
    selectedStore = store;
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
        // Restore the previous search so results are still visible
        filterStoresForProspecting();
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
      <input
        type="text"
        placeholder="Search by city, chain, store #, or state..."
        bind:value={storeSearchQuery}
        on:input={filterStoresForProspecting}
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
            </div>
          </button>
        {/each}
      </div>
    {:else if storeSearchQuery.trim()}
      <p class="empty-msg">No stores found for "{storeSearchQuery}"</p>
    {:else}
      <p class="empty-msg">Type to search 7,835+ stores</p>
    {/if}
  {/if}

  <!-- Nearby Stores List -->
  {#if view === 'nearby-stores'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>📍 Nearby Stores</h2>
    <p class="subtitle">Select a store to find prospects nearby</p>

    <div class="store-list">
      {#each nearbyStores as store (store.StoreName)}
        <button class="store-item" on:click={() => selectStore(store)}>
          <div class="store-info">
            <h4>{store.GroceryChain}</h4>
            <p class="address">{store.City}, {store.State}</p>
            <p class="distance">{store.distance.toFixed(1)} miles away</p>
          </div>
          <div class="store-right">
            <div class="store-num">{store.StoreName}</div>
            <div class="store-cycle">Cycle {store.Cycle || '?'}</div>
          </div>
        </button>
      {/each}
    </div>
  {/if}

  <!-- Category Selection -->
  {#if view === 'categories'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h3>📍 {selectedStore.GroceryChain} - {selectedStore.City}, {selectedStore.State}</h3>
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

    <p class="or-divider">— or pick a category —</p>

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

    <div class="prospect-list">
      {#each prospects as prospect, i (prospect.id + '-' + i)}
        <div class="prospect-card">
          <div class="prospect-header">
            <span class="score-emoji">{prospect.score >= 80 ? '🔥' : prospect.score >= 70 ? '⭐' : '👀'}</span>
            <h4>{prospect.name}</h4>
          </div>
          <p class="prospect-address">📍 {prospect.address}</p>
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
            </div>
            <div class="action-row">
              <button class="action-btn" on:click={() => saveProspect(prospect)}>💾 Save</button>
              <a href="https://www.google.com/search?q={encodeURIComponent(prospect.name + ' ' + (prospect.address || '').split(',')[0])}&tbm=vid" target="_blank" class="action-btn">🎬 Video</a>
            </div>
            <div class="action-row">
              <button class="action-btn" on:click={() => { prospect._showNotes = !prospect._showNotes; prospects = prospects; }}>📝 Notes</button>
              <button class="action-btn" on:click={() => alert('Search testimonials for this business category in the Tools tab')}>📋 Testimonials</button>
            </div>
            {#if prospect.phone}
              <a href="tel:{prospect.phone}" class="action-btn full-width call-btn">📞 Call {prospect.phone}</a>
            {/if}
            <button class="action-btn full-width script-btn" on:click={() => { prospect._showScript = !prospect._showScript; prospect._showEmail = false; prospect._showNotes = false; prospects = prospects; }}>📋 Call Scripts</button>
            <button class="action-btn full-width email-btn" on:click={() => { prospect._showEmail = !prospect._showEmail; prospect._showScript = false; prospect._showNotes = false; prospects = prospects; }}>✉️ Draft Email</button>
            <a href="https://calendar.google.com/calendar/render?action=TEMPLATE&text={encodeURIComponent('Visit: ' + prospect.name)}&details={encodeURIComponent('Prospect: ' + prospect.name + '\nAddress: ' + prospect.address + (prospect.phone ? '\nPhone: ' + prospect.phone : '') + (prospect.website ? '\nWebsite: ' + prospect.website : '') + '\nStore: ' + (selectedStore?.GroceryChain || '') + ' ' + (selectedStore?.StoreName || ''))}&location={encodeURIComponent(prospect.address)}" target="_blank" class="action-btn full-width">📅 Calendar</a>
          </div>
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
            <div class="script-section">
              <h4 class="script-title">📋 Call Scripts</h4>
              <button class="script-select-btn" on:click={() => { prospect._selectedScript = 'tvs-appt'; prospects = prospects; }}>
                📞 TVS Appointment Setting
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
                    const body = encodeURIComponent(tpl.body.replace(/\{business\}/g, prospect.name).replace(/\{contact\}/g, '').replace(/\{rep\}/g, $user?.name || $user?.first_name || 'Your Rep'));
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

  <!-- Saved Prospects -->
  {#if view === 'saved'}
    <button class="back-btn" on:click={() => view = 'main'}>← Back</button>
    <h2>💾 Saved Prospects ({savedProspects.length})</h2>

    {#if savedProspects.length === 0}
      <p class="subtitle">No saved prospects yet. Start searching!</p>
    {:else}
      <div class="prospect-list">
        {#each savedProspects as prospect (prospect.id)}
          <div class="prospect-card">
            <h4>{prospect.name}</h4>
            <p class="address">{prospect.address}</p>
            <div style="margin-top: 0.5rem; display: flex; gap: 0.5rem; flex-wrap: wrap;">
              <select class="status-select" value={prospect.status} on:change={(e) => { prospect.status = e.target.value; updateProspectNotes(prospect.id, prospect.notes); }}>
                <option value="new">🆕 New</option>
                <option value="contacted">⏳ Contacted</option>
                <option value="proposal">📋 Proposal</option>
                <option value="closed">🎉 Closed</option>
              </select>
              <button class="delete-btn" on:click={() => deleteProspect(prospect.id)}>🗑️ Delete</button>
            </div>
            <textarea placeholder="Add notes..." class="notes-input" value={prospect.notes} on:change={(e) => updateProspectNotes(prospect.id, e.target.value)}></textarea>
          </div>
        {/each}
      </div>
    {/if}
  {/if}

  <!-- Hot Leads Section -->
  {#if view === 'hot-leads'}
    <div class="hot-leads-section">
      <button class="back-btn" on:click={() => view = 'main'}>← Back</button>
      <h2>🔥 Hot Leads</h2>
      {#if hotLeads.length === 0}
        <div class="empty-state">
          <p>No Hot Leads assigned to you yet. Check back soon!</p>
        </div>
      {:else}
        <div class="hot-leads-grid">
          {#each hotLeads as lead}
            <div class="hot-lead-card">
              <div class="lead-header">
                <h4>{lead.business_name}</h4>
                <span class="rating">⭐{lead.rating}</span>
              </div>
              <div class="lead-category">{lead.category}</div>
              <div class="lead-hook">"{lead._hook}"</div>
              <div class="lead-contact">
                <a href="tel:{lead.phone}" class="phone">📞 {lead.phone}</a>
                <a href="mailto:{lead._email}" class="email">📧 {lead._email}</a>
              </div>
              <div class="lead-store">{lead.store_chain} {lead.store_city}</div>
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

  .hot-leads-section, .pending-section, .submit-section {
    margin-top: 20px;
  }

  .hot-leads-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 12px;
    margin-top: 16px;
  }

  .hot-lead-card {
    background: white;
    border: 2px solid #e0e0e0;
    border-radius: 10px;
    padding: 14px;
    transition: all 0.2s;
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
  }

  .rating {
    font-size: 12px;
    font-weight: 600;
  }

  .lead-category {
    display: inline-block;
    background: #f0f0f0;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 11px;
    color: #666;
    margin-bottom: 8px;
  }

  .lead-hook {
    font-size: 12px;
    font-style: italic;
    color: #333;
    background: #fff5f5;
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
    color: #999;
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
  h2 { font-size: 24px; }
  h3 { font-size: 18px; }

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
    gap: 1rem;
    max-width: 600px;
  }

  .main-btn {
    background: var(--card-bg);
    border: 2px solid var(--border-color);
    border-radius: 12px;
    padding: 1.5rem;
    cursor: pointer;
    transition: all 0.2s;
    text-align: center;
    color: var(--text-primary);
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

  .prospect-list { display: flex; flex-direction: column; gap: 1rem; }

  .prospect-card {
    background: var(--card-bg);
    border-radius: 12px;
    padding: 14px;
    box-shadow: 0 2px 8px var(--card-shadow);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
  }

  .prospect-header { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
  .score-emoji { font-size: 18px; }
  .prospect-card h4 { margin: 0; color: var(--text-primary); font-weight: 700; font-size: 17px; }
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
</style>
