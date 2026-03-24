<script>
  import { onMount } from 'svelte';
  import { user } from '../lib/stores.js';
  
  let allStores = [];
  let nearbyStores = [];
  let prospects = [];
  let savedProspects = [];
  let view = 'main'; // main, nearby-stores, categories, subcategories, results, saved
  let selectedStore = null;
  let selectedCategory = null;
  let selectedSubcategory = null;
  let userLocation = null;
  let loading = false;
  let error = '';
  let searchInput = '';
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
      const res = await fetch('/data/stores.json');
      allStores = await res.json();
      loadSavedProspects();
    } catch (err) {
      error = 'Failed to load store data';
      console.error(err);
    }
  });

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
      const response = await fetch('https://places.googleapis.com/v1/places:searchText', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Goog-Api-Key': PLACES_API_KEY,
          'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.location,places.businessStatus,places.nationalPhoneNumber,places.websiteUri,places.googleMapsUri'
        },
        body: JSON.stringify({
          textQuery: keyword,
          locationBias: {
            circle: {
              center: { latitude: lat, longitude: lng },
              radius: 8000.0
            }
          },
          maxResultCount: 10
        })
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
    <p class="subtitle">Choose a category to find prospects</p>

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
            <button class="action-btn full-width email-btn" on:click={() => { prospect._showEmail = !prospect._showEmail; prospect._showNotes = false; prospects = prospects; }}>✉️ Draft Email</button>
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
</div>

<style>
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
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
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

  .notes-section, .email-section {
    margin-top: 10px;
    padding: 10px;
    background: var(--hover-bg);
    border-radius: 8px;
  }

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
</style>
