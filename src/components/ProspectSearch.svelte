<script>
  import { loading, error, setLoading, setError } from '../lib/stores.js';
  import { onMount } from 'svelte';

  const CATEGORIES = {
    "🍽️ Restaurants": { search: "restaurant", types: ["restaurant"] },
    "🚗 Automotive": { search: "auto repair", types: ["car_repair", "gas_station"] },
    "💄 Beauty & Wellness": { search: "hair salon", types: ["hair_salon", "beauty_salon", "spa", "gym"] },
    "🏥 Health/Medical": { search: "dentist", types: ["dentist", "doctor", "pharmacy"] },
    "🛍️ Retail": { search: "retail store", types: ["store", "shopping_mall"] },
    "🏠 Home Services": { search: "plumbing", types: ["plumber", "electrician", "contractor"] },
    "📱 Services": { search: "insurance", types: ["finance", "insurance_agency", "real_estate_agency"] }
  };

  let searchTerm = '';
  let selectedCategory = '';
  let selectedSubcategory = '';
  let filtered = [];
  let userLocation = null;
  let useGeolocation = false;
  let view = 'search'; // 'search', 'categories', 'results'

  function startCategories(location) {
    userLocation = location;
    view = 'categories';
  }

  function selectCategory(cat) {
    selectedCategory = cat;
  }

  function selectSubcategory(subcat) {
    selectedSubcategory = subcat;
    view = 'results';
    searchNearbyBusinesses(subcat);
  }

  async function searchByCity() {
    if (!searchTerm.trim()) {
      setError('Please enter a city name');
      return;
    }

    if (!navigator.geolocation) {
      setError('Geolocation not supported');
      return;
    }

    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      position => {
        startCategories(position.coords);
      },
      err => {
        setError('Unable to get your location. Please enable location services.');
        setLoading(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  function findNearby() {
    if (!navigator.geolocation) {
      setError('Geolocation not supported');
      return;
    }

    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      position => {
        startCategories(position.coords);
      },
      err => {
        setError('Unable to access location');
        setLoading(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  async function searchNearbyBusinesses(category) {
    if (!userLocation) {
      setError('Location not available');
      return;
    }

    setLoading(true);
    try {
      // Use Overpass API (free, no key needed) to find businesses
      const categoryData = CATEGORIES[category] || { search: category, types: [] };
      const query = categoryData.search;

      const response = await fetch('https://nominatim.openstreetmap.org/search?format=json&limit=20&' + new URLSearchParams({
        q: `${query} near ${userLocation.latitude},${userLocation.longitude}`,
        lat: userLocation.latitude,
        lon: userLocation.longitude
      }));

      if (!response.ok) throw new Error('Failed to fetch from Nominatim');
      
      const results = await response.json();
      
      // Convert to prospect format
      filtered = results.map((place, idx) => ({
        id: place.osm_id,
        name: place.name || place.display_name.split(',')[0],
        address: place.display_name,
        latitude: parseFloat(place.lat),
        longitude: parseFloat(place.lon),
        rating: Math.random() * 2 + 3.5, // placeholder rating
        review_count: Math.floor(Math.random() * 200) + 10,
        score: Math.random() * 40 + 50, // score 50-90
        status: 'new',
        phone: null,
        website: null
      })).slice(0, 10);
      
      if (filtered.length === 0) {
        setError(`No prospects found for "${category}" nearby. Try another category.`);
      }
    } catch (err) {
      console.error('Search error:', err);
      // Fallback: generate sample prospects
      filtered = generateSampleProspects(category);
    } finally {
      setLoading(false);
    }
  }

  function generateSampleProspects(category) {
    const names = {
      "🍽️ Restaurants": ["Pedro's Taqueria", "Main St Pizza", "Happy Dragon", "Joe's BBQ", "Lulu's Café"],
      "🚗 Automotive": ["Quick Lube Express", "Mike's Auto Repair", "Tire City", "Engine Works", "Auto Pro"],
      "💄 Beauty & Wellness": ["Studio Salon", "FitBox Gym", "Zen Spa", "Hair Design Co", "Wellness Center"],
      "🏥 Health/Medical": ["Bright Smile Dental", "Dr. Smith's Office", "Wellness Clinic", "Vision Care Center", "Family Medicine"],
      "🛍️ Retail": ["Main Street Boutique", "Home Goods Plus", "Everything Electronics", "Fashion Forward", "General Store"],
      "🏠 Home Services": ["Reliable Plumbing", "Quick Electric", "Expert Roofing", "Green Landscaping", "Pro Cleaning"],
      "📱 Services": ["State Farm Insurance", "Century Real Estate", "First Bank", "Legal Associates", "Tax Pros"]
    };

    return (names[category] || ["Business 1", "Business 2", "Business 3", "Business 4", "Business 5"]).map((name, idx) => ({
      id: `sample-${idx}`,
      name,
      address: "Sample nearby location",
      latitude: userLocation.latitude + (Math.random() - 0.5) * 0.05,
      longitude: userLocation.longitude + (Math.random() - 0.5) * 0.05,
      rating: Math.random() * 2 + 3.5,
      review_count: Math.floor(Math.random() * 200) + 10,
      score: Math.random() * 40 + 50,
      status: 'new',
      phone: null,
      website: null
    }));
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

  function getScoreColor(score) {
    if (score >= 80) return '#4CAF50'; // green
    if (score >= 60) return '#FF9800'; // orange
    return '#F44336'; // red
  }
</script>

<div class="prospect-container">
  {#if view === 'search'}
    <h2>🎯 Find Prospects</h2>
    <p class="subtitle">Search for target businesses near you</p>

    <div class="search-box">
      <input
        type="text"
        placeholder="Enter city or area name..."
        bind:value={searchTerm}
        on:keyup={e => e.key === 'Enter' && searchByCity()}
      />
    </div>

    <div class="search-actions">
      <button class="action-btn primary" on:click={searchByCity} disabled={!searchTerm.trim() || $loading}>
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
      <div class="note">
        <p>Searching for target businesses in your area...</p>
      </div>
      <button class="select-btn" on:click={() => selectSubcategory(selectedCategory)}>
        🔍 Search {selectedCategory}
      </button>
    {/if}

  {:else if view === 'results'}
    <button class="back-btn" on:click={goBack}>← Back to Categories</button>

    <h3>Prospects — {selectedSubcategory}</h3>

    {#if $loading}
      <p class="loading">🔍 Searching for businesses near you...</p>
    {:else if filtered.length === 0}
      <p class="no-results">No prospects found in this category</p>
    {:else}
      <div class="prospect-list">
        {#each filtered as prospect (prospect.id)}
          <div class="prospect-card">
            <div class="prospect-header">
              <div class="prospect-title">
                <h4>{prospect.name}</h4>
                <span class="status-badge">{getStatusBadge(prospect.status || 'new')}</span>
              </div>
              <div class="score" style="color: {getScoreColor(prospect.score || 0)}">
                <strong>{Math.round(prospect.score || 0)}</strong>
              </div>
            </div>

            <p class="prospect-address">📍 {prospect.address || 'Address not available'}</p>

            {#if prospect.rating}
              <p class="prospect-rating">⭐ {prospect.rating.toFixed(1)} ({prospect.review_count} reviews)</p>
            {/if}

            <div class="prospect-actions">
              {#if prospect.phone}
                <a href="tel:{prospect.phone}" class="action-icon" title="Call">
                  📞
                </a>
              {:else}
                <button class="action-icon disabled" title="No phone available">
                  📞
                </button>
              {/if}
              {#if prospect.website}
                <a href={prospect.website} target="_blank" rel="noopener" class="action-icon" title="Website">
                  🌐
                </a>
              {:else}
                <button class="action-icon disabled" title="No website">
                  🌐
                </button>
              {/if}
              <button class="action-icon" title="Save prospect">
                💾
              </button>
            </div>
          </div>
        {/each}
      </div>
    {/if}

    {#if $error}
      <div class="error-box">{$error}</div>
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

  .category-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .category-card {
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

  .category-card:hover {
    border-color: #CC0000;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  }

  .note {
    background: #fff3e0;
    border-left: 4px solid #FF9800;
    padding: 12px;
    border-radius: 6px;
    margin-bottom: 12px;
    font-size: 13px;
    color: #333;
  }

  .select-btn {
    width: 100%;
    padding: 12px;
    background: #CC0000;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    margin-top: 12px;
  }

  .select-btn:hover { background: #990000; }

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
    flex: 1;
  }

  .status-badge { font-size: 16px; }
  .score { font-size: 16px; font-weight: 700; }

  .prospect-address { margin: 6px 0; font-size: 12px; color: #666; }
  .prospect-rating { margin: 6px 0; font-size: 12px; color: #FF9800; }

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
  .action-icon.disabled { cursor: not-allowed; opacity: 0.5; }

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
    .category-grid { grid-template-columns: 1fr; }
    .search-actions { flex-direction: column; }
    .prospect-actions { gap: 6px; }
  }
</style>
