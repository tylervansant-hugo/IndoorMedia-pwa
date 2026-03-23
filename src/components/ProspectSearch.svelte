<script>
  import { onMount } from 'svelte';
  
  let allStores = [];
  let prospects = [];
  let savedProspects = [];
  let view = 'main'; // main, search, results, saved
  let searchRadius = 5; // miles
  let selectedStore = null;
  let selectedCategory = null;
  let userLocation = null;
  let loading = false;
  let error = '';

  const CATEGORIES = {
    '🍽️ Restaurants': ['Mexican', 'Pizza', 'Coffee', 'Sushi', 'Fast Food', 'Chinese', 'Thai', 'Indian', 'BBQ', 'Italian', 'Bakery', 'Bar/Pub', 'All'],
    '🚗 Automotive': ['Oil Change', 'Car Wash', 'Auto Repair', 'Tires', 'Car Dealer', 'Body Shop', 'Transmission'],
    '💄 Beauty & Wellness': ['Hair Salon', 'Barber', 'Nails', 'Spa', 'Gym', 'Yoga', 'Tanning'],
    '🏥 Health/Medical': ['Dentist', 'Chiropractor', 'Eye Care', 'Vet', 'Physical Therapy', 'Urgent Care', 'Pharmacy'],
    '🏠 Home Services': ['Plumber', 'Electrician', 'HVAC', 'Roofing', 'Landscaping', 'Cleaning', 'Contractor', 'Pest Control'],
    '🛍️ Retail': ['Clothing', 'Pet Store', 'Jewelry', 'Furniture', 'Florist', 'Cell Phone', 'Liquor', 'Dispensary'],
    '👔 Professionals': ['Real Estate', 'Insurance', 'Accountant', 'Lawyer', 'Financial', 'Mortgage'],
    '👦 Kids & Tutoring': ['Tutoring', 'Music', 'Dance', 'Martial Arts', 'Sports', 'Camps', 'General'],
    '👶 Care Centers': ['Daycare', 'After School', 'Assisted Living', 'Adult Care']
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

  function loadSavedProspects() {
    const saved = localStorage.getItem('savedProspects');
    savedProspects = saved ? JSON.parse(saved) : [];
  }

  function saveProspect(prospect) {
    const existing = savedProspects.find(p => p.id === prospect.id);
    if (!existing) {
      savedProspects = [...savedProspects, { ...prospect, savedAt: new Date().toISOString(), status: 'new', notes: '' }];
      localStorage.setItem('savedProspects', JSON.stringify(savedProspects));
      alert(`✅ Saved: ${prospect.name}`);
    } else {
      alert('Already saved');
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

  function startNearMeSearch() {
    error = '';
    loading = true;

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        userLocation = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        
        // Find nearest store
        let nearest = null;
        let minDist = Infinity;
        
        for (const store of allStores) {
          if (!store.latitude || !store.longitude) continue;
          const dist = Math.sqrt(
            Math.pow(store.latitude - userLocation.lat, 2) +
            Math.pow(store.longitude - userLocation.lng, 2)
          ) * 69; // rough miles conversion
          
          if (dist < minDist) {
            minDist = dist;
            nearest = store;
          }
        }

        if (nearest) {
          selectedStore = nearest;
          view = 'search';
        } else {
          error = 'No stores found nearby';
        }
        loading = false;
      },
      (err) => {
        error = 'Enable location services';
        loading = false;
      }
    );
  }

  function startSearchByCity(city) {
    error = '';
    const stores = allStores.filter(s => s.City?.toLowerCase().includes(city.toLowerCase()));
    
    if (stores.length === 0) {
      error = `No stores found in ${city}`;
      return;
    }

    // Use first store as reference location
    selectedStore = stores[0];
    view = 'search';
  }

  function startSearchByStore(storeNum) {
    error = '';
    const store = allStores.find(s => s.StoreName?.toUpperCase() === storeNum.toUpperCase());
    
    if (!store) {
      error = 'Store not found';
      return;
    }

    selectedStore = store;
    view = 'search';
  }

  function searchProspects(category, subcat) {
    error = '';
    loading = true;
    selectedCategory = { category, subcat };

    // Simulate search - in real app would call Google Places
    const mockProspects = [
      { id: '1', name: `${subcat} Prospect 1`, address: '123 Main St', distance: 0.3, rating: 4.5, reviews: 87, score: 92 },
      { id: '2', name: `${subcat} Prospect 2`, address: '456 Oak Ave', distance: 0.8, rating: 4.2, reviews: 43, score: 78 },
      { id: '3', name: `${subcat} Prospect 3`, address: '789 Pine Ln', distance: 1.2, rating: 4.7, reviews: 156, score: 85 },
      { id: '4', name: `${subcat} Prospect 4`, address: '321 Elm St', distance: 1.5, rating: 3.9, reviews: 22, score: 65 },
      { id: '5', name: `${subcat} Prospect 5`, address: '654 Maple Dr', distance: 2.1, rating: 4.4, reviews: 78, score: 72 }
    ];

    prospects = mockProspects;
    view = 'results';
    loading = false;
  }

  function goBack() {
    if (view === 'results') {
      view = 'search';
      selectedCategory = null;
    } else if (view === 'search') {
      view = 'main';
      selectedStore = null;
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

      <button class="main-btn" on:click={() => view = 'city-search'}>
        <div class="btn-icon">🏙️</div>
        <div class="btn-text">By City</div>
        <div class="btn-desc">Search by location</div>
      </button>

      <button class="main-btn" on:click={() => view = 'store-search'}>
        <div class="btn-icon">🏪</div>
        <div class="btn-text">By Store #</div>
        <div class="btn-desc">Enter store number</div>
      </button>

      <button class="main-btn" on:click={() => view = 'saved'}>
        <div class="btn-icon">💾</div>
        <div class="btn-text">Saved ({savedProspects.length})</div>
        <div class="btn-desc">Your prospects</div>
      </button>
    </div>
  {/if}

  <!-- City Search -->
  {#if view === 'city-search'}
    <button class="back-btn" on:click={() => view = 'main'}>← Back</button>
    <h2>Search by City</h2>
    <input type="text" placeholder="Enter city..." id="city-input" class="search-input" />
    <button class="search-btn" on:click={() => {
      const input = document.getElementById('city-input');
      startSearchByCity(input.value);
    }}>Search</button>
  {/if}

  <!-- Store Number Search -->
  {#if view === 'store-search'}
    <button class="back-btn" on:click={() => view = 'main'}>← Back</button>
    <h2>Search by Store #</h2>
    <input type="text" placeholder="e.g. FME07Z-0236" id="store-input" class="search-input" />
    <button class="search-btn" on:click={() => {
      const input = document.getElementById('store-input');
      startSearchByStore(input.value);
    }}>Search</button>
  {/if}

  <!-- Category Selection -->
  {#if view === 'search' && selectedStore && !selectedCategory}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h3>📍 {selectedStore.GroceryChain} - {selectedStore.City}, {selectedStore.State}</h3>
    <p class="subtitle">Choose a category to find prospects</p>

    <div class="category-grid">
      {#each Object.entries(CATEGORIES) as [cat, subcats]}
        <button class="category-btn" on:click={() => { selectedCategory = cat; }}>
          {cat}
        </button>
      {/each}
    </div>
  {/if}

  <!-- Subcategory Selection -->
  {#if view === 'search' && selectedCategory && typeof selectedCategory === 'string'}
    <button class="back-btn" on:click={() => { selectedCategory = null; }}>← Back</button>
    <h3>{selectedCategory}</h3>

    <div class="subcat-grid">
      {#each CATEGORIES[selectedCategory] || [] as subcat}
        <button class="subcat-btn" on:click={() => searchProspects(selectedCategory, subcat)}>
          {subcat}
        </button>
      {/each}
    </div>
  {/if}

  <!-- Prospect Results -->
  {#if view === 'results'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h3>Results for {selectedCategory.category} → {selectedCategory.subcat}</h3>

    <div class="prospect-list">
      {#each prospects as prospect (prospect.id)}
        <div class="prospect-card">
          <div class="prospect-header">
            <div>
              <h4>{prospect.name}</h4>
              <p class="address">📍 {prospect.address}</p>
              <p class="meta">⭐ {prospect.rating} ({prospect.reviews} reviews) • {prospect.distance} mi • Score: {prospect.score}%</p>
            </div>
            <button class="expand-btn" on:click={() => { /* expand actions */ }}>▼</button>
          </div>
          <div class="prospect-actions">
            <a href="tel:+15551234567" class="action-btn">📞 Call</a>
            <a href="https://maps.google.com" target="_blank" class="action-btn">📍 Maps</a>
            <button class="action-btn" on:click={() => saveProspect(prospect)}>💾 Save</button>
            <button class="action-btn">📝 Notes</button>
            <button class="action-btn">📧 Email</button>
            <button class="action-btn">📅 Calendar</button>
          </div>
        </div>
      {/each}
    </div>
  {/if}

  <!-- Saved Prospects -->
  {#if view === 'saved'}
    <button class="back-btn" on:click={() => view = 'main'}>← Back</button>
    <h2>💾 Saved Prospects ({savedProspects.length})</h2>

    {#if savedProspects.length === 0}
      <p class="subtitle">No saved prospects yet</p>
    {:else}
      <div class="prospect-list">
        {#each savedProspects as prospect (prospect.id)}
          <div class="prospect-card">
            <h4>{prospect.name}</h4>
            <p class="address">{prospect.address}</p>
            <div style="margin-top: 0.5rem; display: flex; gap: 0.5rem;">
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
    max-width: 800px;
    margin: 0 auto;
    padding: 1rem;
  }

  h2, h3 {
    margin: 0 0 0.5rem 0;
    color: #1a1a1a;
  }

  h2 { font-size: 1.5rem; }
  h3 { font-size: 1.25rem; }

  .subtitle {
    margin-bottom: 1.5rem;
    color: #666;
    font-size: 0.95rem;
  }

  .error-box {
    background: #fee;
    color: #c33;
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
    border-left: 4px solid #cc0000;
  }

  .loading {
    text-align: center;
    padding: 2rem;
    color: #999;
  }

  .back-btn {
    background: none;
    border: none;
    color: #cc0000;
    font-weight: 600;
    cursor: pointer;
    margin-bottom: 1rem;
  }

  /* Main Menu Buttons */
  .button-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
  }

  .main-btn {
    background: white;
    border: 2px solid #ddd;
    border-radius: 12px;
    padding: 1.5rem;
    cursor: pointer;
    transition: all 0.2s;
    text-align: center;
  }

  .main-btn:hover {
    border-color: #cc0000;
    box-shadow: 0 4px 12px rgba(204, 0, 0, 0.1);
    transform: translateY(-2px);
  }

  .btn-icon { font-size: 2rem; margin-bottom: 0.5rem; }
  .btn-text { font-weight: 600; color: #1a1a1a; margin-bottom: 0.25rem; }
  .btn-desc { font-size: 0.85rem; color: #999; }

  /* Search Input */
  .search-input {
    width: 100%;
    padding: 0.75rem;
    border: 2px solid #cc0000;
    border-radius: 8px;
    font-size: 1rem;
    margin-bottom: 1rem;
  }

  .search-btn {
    width: 100%;
    padding: 0.75rem;
    background: #cc0000;
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
  }

  .search-btn:hover { background: #990000; }

  /* Categories */
  .category-grid, .subcat-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
    margin-bottom: 1rem;
  }

  .category-btn, .subcat-btn {
    background: white;
    border: 2px solid #ddd;
    border-radius: 8px;
    padding: 1rem;
    cursor: pointer;
    text-align: center;
    font-weight: 600;
    transition: all 0.2s;
  }

  .category-btn:hover, .subcat-btn:hover {
    border-color: #cc0000;
    background: #fff5f5;
  }

  /* Prospect Cards */
  .prospect-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .prospect-card {
    background: white;
    border-radius: 10px;
    padding: 1rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    border-left: 4px solid #cc0000;
  }

  .prospect-header {
    display: flex;
    justify-content: space-between;
    align-items: start;
  }

  .prospect-card h4 {
    margin: 0 0 0.5rem 0;
    color: #1a1a1a;
  }

  .address { margin: 0.25rem 0; font-size: 0.9rem; color: #666; }
  .meta { margin: 0.5rem 0 0 0; font-size: 0.85rem; color: #999; }

  .expand-btn {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
  }

  /* Actions */
  .prospect-actions {
    display: flex;
    gap: 0.5rem;
    margin-top: 1rem;
    flex-wrap: wrap;
  }

  .action-btn {
    flex: 1;
    min-width: 70px;
    padding: 0.5rem;
    background: #f0f0f0;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.85rem;
    text-decoration: none;
    text-align: center;
    transition: background 0.2s;
  }

  .action-btn:hover { background: #cc0000; color: white; }

  /* Saved Prospects */
  .status-select {
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.9rem;
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
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.9rem;
    min-height: 60px;
    resize: vertical;
  }

  @media (max-width: 600px) {
    .button-grid { grid-template-columns: 1fr; }
    .category-grid, .subcat-grid { grid-template-columns: 1fr; }
  }
</style>
