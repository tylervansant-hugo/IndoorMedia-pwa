<script>
  import { loading, error, setLoading, setError } from '../lib/stores.js';
  import { onMount } from 'svelte';

  const CATEGORIES = {
    "🍽️ Restaurants": ["Mexican", "Pizza", "Coffee/Café", "Sushi/Japanese", "Fast Food", "Chinese", "Thai", "Indian", "BBQ/Steakhouse", "Italian", "Bakery", "Bar/Pub", "All Restaurants"],
    "🚗 Automotive": ["Oil Change/Lube", "Car Wash", "Auto Repair", "Tires", "Car Dealer", "Body Shop", "Transmission"],
    "💄 Beauty & Wellness": ["Hair Salon", "Barber", "Nail Salon", "Spa/Massage", "Gym/Fitness", "Yoga/Pilates", "Tanning"],
    "🏥 Health/Medical": ["Dentist", "Chiropractor", "Veterinarian", "Physical Therapy", "Optical", "Urgent Care"],
    "🛍️ Retail": ["Clothing/Apparel", "Home & Garden", "Electronics", "Books/Music", "Sporting Goods", "General Retail"],
    "🏠 Home Services": ["Plumbing", "HVAC", "Roofing", "Landscaping", "Cleaning", "Electrician"],
    "📱 Services": ["Phone/Telecom", "Insurance", "Real Estate", "Financial", "Legal", "Accounting"]
  };

  let searchTerm = '';
  let selectedCategory = '';
  let selectedSubcategory = '';
  let allProspects = [];
  let filtered = [];
  let userLocation = null;
  let useGeolocation = false;
  let view = 'search'; // 'search', 'categories', 'results'

  onMount(async () => {
    try {
      const response = await fetch('/data/prospect_data.json');
      const data = await response.json();
      
      // Flatten all reps' saved prospects into one list
      const reps = data.reps || {};
      allProspects = [];
      for (const [repId, rep] of Object.entries(reps)) {
        const saved = rep.saved_prospects || {};
        for (const [pid, prospect] of Object.entries(saved)) {
          allProspects.push({
            id: pid,
            repName: rep.name,
            name: prospect.name || '',
            business: prospect.name || '',
            address: prospect.address || '',
            phone: prospect.phone || '',
            email: prospect.email || '',
            score: prospect.score || 0,
            status: prospect.status || 'new',
            category: prospect.category || '',
            latitude: prospect.latitude || 0,
            longitude: prospect.longitude || 0,
            notes: prospect.notes || []
          });
        }
      }
      console.log(`Loaded ${allProspects.length} prospects`);
    } catch (err) {
      setError('Failed to load prospects: ' + err.message);
    }
  });

  function searchProspects() {
    if (!searchTerm.trim()) {
      filtered = [];
      return;
    }
    const term = searchTerm.toLowerCase();
    filtered = allProspects
      .filter(p => 
        p.business?.toLowerCase().includes(term) ||
        p.address?.toLowerCase().includes(term) ||
        p.name?.toLowerCase().includes(term) ||
        p.category?.toLowerCase().includes(term)
      )
      .sort((a, b) => b.score - a.score)
      .slice(0, 20);
  }

  function startCategories() {
    view = 'categories';
  }

  function selectCategory(cat) {
    selectedCategory = cat;
  }

  function selectSubcategory(subcat) {
    selectedSubcategory = subcat;
    view = 'results';
    // Filter by category keyword
    const keyword = subcat.toLowerCase();
    filtered = allProspects
      .filter(p => p.category?.toLowerCase().includes(keyword) || p.business?.toLowerCase().includes(keyword))
      .sort((a, b) => b.score - a.score)
      .slice(0, 20);
  }

  function findNearby() {
    if (!navigator.geolocation) {
      setError('Geolocation not supported');
      return;
    }

    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      position => {
        const { latitude, longitude } = position.coords;
        userLocation = { lat: latitude, lng: longitude };
        useGeolocation = true;

        // Sort by distance
        filtered = allProspects
          .filter(p => p.latitude && p.longitude)
          .map(p => ({
            ...p,
            _dist: Math.sqrt(Math.pow(p.latitude - latitude, 2) + Math.pow(p.longitude - longitude, 2))
          }))
          .sort((a, b) => a._dist - b._dist)
          .slice(0, 20);

        view = 'categories';
        setLoading(false);
      },
      err => {
        setError('Unable to access location');
        setLoading(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  function goBack() {
    if (view === 'results') {
      view = 'categories';
      selectedSubcategory = '';
    } else if (view === 'categories') {
      view = 'search';
      selectedCategory = '';
      searchTerm = '';
      filtered = [];
    }
  }

  function getStatusBadge(status) {
    const badges = {
      'new': '🆕',
      'interested': '✅',
      'contacted': '⏳',
      'proposal': '📋',
      'closed': '🎉'
    };
    return badges[status] || '◯';
  }
</script>

<div class="prospect-container">
  {#if view === 'search'}
    <h2>🎯 Find Prospects</h2>
    <p class="subtitle">Search by location or store name, then choose categories</p>

    <div class="search-box">
      <input
        type="text"
        placeholder="Search by city, store name, or business..."
        bind:value={searchTerm}
        on:input={searchProspects}
      />
      {#if searchTerm && filtered.length > 0}
        <div class="search-results-dropdown">
          {#each filtered.slice(0, 5) as prospect}
            <button class="result-item" on:click={() => { searchTerm = prospect.address; view = 'categories'; }}>
              {prospect.business} — {prospect.address}
            </button>
          {/each}
        </div>
      {/if}
    </div>

    <div class="search-actions">
      <button class="action-btn primary" on:click={startCategories} disabled={!searchTerm.trim()}>
        🔍 Search This Area
      </button>
      <button class="action-btn secondary" on:click={findNearby} disabled={$loading}>
        {$loading ? '📍 Getting location...' : '📍 Find Nearby'}
      </button>
    </div>

    {#if $error}
      <div class="error-box">{$error}</div>
    {/if}

  {:else if view === 'categories'}
    <button class="back-btn" on:click={goBack}>← Back to Search</button>
    
    <h3>{selectedCategory ? selectedCategory : 'Choose Category'}</h3>

    {#if !selectedCategory}
      <div class="category-grid">
        {#each Object.keys(CATEGORIES) as cat}
          <button class="category-card" on:click={() => selectCategory(cat)}>
            {cat}
          </button>
        {/each}
      </div>
    {:else}
      <div class="subcat-grid">
        {#each CATEGORIES[selectedCategory] || [] as subcat}
          <button class="subcat-card" on:click={() => selectSubcategory(subcat)}>
            {subcat}
          </button>
        {/each}
      </div>
    {/if}

  {:else if view === 'results'}
    <button class="back-btn" on:click={goBack}>← Back to Categories</button>

    <h3>Prospects in {selectedSubcategory}</h3>

    {#if $loading}
      <p class="loading">Loading prospects...</p>
    {:else if filtered.length === 0}
      <p class="no-results">No prospects found in this category</p>
    {:else}
      <div class="prospect-list">
        {#each filtered as prospect (prospect.id)}
          <div class="prospect-card">
            <div class="prospect-header">
              <div class="prospect-title">
                <h4>{prospect.business}</h4>
                <span class="status-badge">{getStatusBadge(prospect.status)}</span>
              </div>
              <span class="score">{Math.round(prospect.score)}</span>
            </div>

            <p class="prospect-address">📍 {prospect.address}</p>

            <div class="prospect-actions">
              {#if prospect.phone}
                <a href="tel:{prospect.phone}" class="action-icon" title="Call">
                  📞
                </a>
              {/if}
              {#if prospect.email}
                <a href="mailto:{prospect.email}" class="action-icon" title="Email">
                  ✉️
                </a>
              {/if}
              <button class="action-icon" title="Notes">
                📝
              </button>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  {/if}
</div>

<style>
  .prospect-container { max-width: 700px; margin: 0 auto; }
  h2 { margin: 0 0 6px 0; font-size: 20px; }
  h3 { margin: 0 0 16px 0; font-size: 16px; }
  h4 { margin: 0; font-size: 15px; color: #1a1a1a; }
  .subtitle { margin: 0 0 16px 0; font-size: 13px; color: #999; }

  .search-box {
    position: relative;
    margin-bottom: 16px;
  }

  input {
    width: 100%;
    padding: 12px 14px;
    border: 2px solid #ddd;
    border-radius: 8px;
    font-size: 15px;
  }

  input:focus {
    outline: none;
    border-color: #CC0000;
  }

  .search-results-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: white;
    border: 2px solid #CC0000;
    border-top: none;
    border-radius: 0 0 8px 8px;
    z-index: 10;
    max-height: 160px;
    overflow-y: auto;
  }

  .result-item {
    display: block;
    width: 100%;
    padding: 10px 14px;
    background: none;
    border: none;
    text-align: left;
    font-size: 13px;
    cursor: pointer;
    border-bottom: 1px solid #f0f0f0;
  }

  .result-item:hover { background: #fff5f5; }

  .search-actions {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
  }

  .action-btn {
    flex: 1;
    padding: 12px;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .action-btn.primary {
    background: #CC0000;
    color: white;
  }

  .action-btn.primary:hover { background: #990000; }

  .action-btn.secondary {
    background: #f0f0f0;
    color: #333;
  }

  .action-btn.secondary:hover { background: #e0e0e0; }

  .action-btn:disabled {
    background: #ccc;
    cursor: not-allowed;
    color: #999;
  }

  .back-btn {
    padding: 10px 14px;
    background: none;
    border: none;
    color: #CC0000;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    margin-bottom: 12px;
  }

  .category-grid, .subcat-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .category-card, .subcat-card {
    background: white;
    border: 2px solid #e0e0e0;
    border-radius: 12px;
    padding: 16px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
    transition: all 0.2s;
    text-align: center;
  }

  .category-card:hover, .subcat-card:hover {
    border-color: #CC0000;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  }

  .prospect-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .prospect-card {
    background: white;
    border-radius: 10px;
    padding: 14px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border-left: 4px solid #CC0000;
  }

  .prospect-header {
    display: flex;
    justify-content: space-between;
    align-items: start;
    margin-bottom: 8px;
  }

  .prospect-title {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .status-badge { font-size: 16px; }
  .score { font-size: 14px; font-weight: 700; color: #CC0000; }

  .prospect-address { margin: 6px 0; font-size: 12px; color: #666; }

  .prospect-actions {
    display: flex;
    gap: 8px;
    margin-top: 10px;
  }

  .action-icon {
    flex: 1;
    padding: 8px;
    background: #f0f0f0;
    border: none;
    border-radius: 6px;
    font-size: 16px;
    cursor: pointer;
    transition: all 0.2s;
    text-decoration: none;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .action-icon:hover { background: #CC0000; color: white; }

  .error-box {
    background: #fee;
    color: #c33;
    padding: 12px;
    border-radius: 8px;
    font-size: 13px;
    margin-top: 16px;
  }

  .loading, .no-results {
    text-align: center;
    color: #999;
    padding: 40px 20px;
    font-size: 14px;
  }

  @media (max-width: 480px) {
    .category-grid, .subcat-grid { grid-template-columns: 1fr; }
    .search-actions { flex-direction: column; }
    .prospect-actions { gap: 6px; }
  }
</style>
