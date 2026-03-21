<script>
  import { searchResults, loading, error, setLoading, setError, addToCart } from '../lib/stores.js';
  import { onMount } from 'svelte';

  let searchTerm = '';
  let allStores = [];
  let filtered = [];
  let useGeolocation = false;
  let userLocation = null;

  async function loadStores() {
    try {
      setLoading(true);
      const response = await fetch('/data/stores_with_gps.json');
      if (!response.ok) throw new Error('Failed to load stores');
      const data = await response.json();
      allStores = data || [];
    } catch (err) {
      setError('Failed to load stores: ' + err.message);
    } finally {
      setLoading(false);
    }
  }

  function filterStores() {
    if (!searchTerm.trim()) {
      filtered = [];
      return;
    }

    const term = searchTerm.toLowerCase();
    filtered = allStores.filter(store => 
      (store.name && store.name.toLowerCase().includes(term)) ||
      (store.city && store.city.toLowerCase().includes(term)) ||
      (store.number && store.number.toString().includes(term))
    ).slice(0, 20);

    searchResults.set(filtered);
  }

  function requestGeolocation() {
    if (!navigator.geolocation) {
      setError('Geolocation not supported in this browser');
      return;
    }

    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      position => {
        const { latitude, longitude } = position.coords;
        userLocation = { lat: latitude, lng: longitude };
        useGeolocation = true;
        setLoading(false);
        
        // Sort by distance
        filtered = filtered.sort((a, b) => {
          const distA = calcDistance(latitude, longitude, a.lat, a.lng);
          const distB = calcDistance(latitude, longitude, b.lat, b.lng);
          return distA - distB;
        }).slice(0, 10);
      },
      () => {
        setError('Unable to access location');
        setLoading(false);
      }
    );
  }

  function calcDistance(lat1, lon1, lat2, lon2) {
    const R = 3959; // Earth radius in miles
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = 
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  function handleAddToCart(store) {
    addToCart({
      id: store.number,
      type: 'store',
      name: store.name,
      city: store.city,
      chain: store.chain
    });
    setError('Added to cart');
  }

  onMount(loadStores);
</script>

<div class="search-container">
  <div class="search-box">
    <input
      type="text"
      placeholder="Search by store name, city, or number..."
      bind:value={searchTerm}
      on:input={filterStores}
      disabled={$loading}
    />
    {#if $loading}
      <div class="spinner"></div>
    {/if}
  </div>

  {#if filtered.length > 0}
    <div class="location-toggle">
      <button
        class="geo-btn"
        on:click={requestGeolocation}
        disabled={$loading}
      >
        📍 Find Nearby
      </button>
      {#if useGeolocation && userLocation}
        <span class="location-indicator">Using your location</span>
      {/if}
    </div>
  {/if}

  {#if $error}
    <div class="error-box">{$error}</div>
  {/if}

  <div class="results">
    {#if $loading}
      <p class="loading">Loading stores...</p>
    {:else if filtered.length === 0 && searchTerm}
      <p class="no-results">No stores found matching "{searchTerm}"</p>
    {:else if filtered.length === 0}
      <p class="hint">Start typing to search for stores</p>
    {:else}
      <div class="store-grid">
        {#each filtered as store (store.number)}
          <div class="store-card">
            <div class="store-header">
              <h3>{store.name}</h3>
              <span class="store-number">#{store.number}</span>
            </div>
            <div class="store-info">
              <p>{store.chain || 'Store'}</p>
              <p class="city">{store.city}, {store.state}</p>
              {#if useGeolocation && userLocation && store.lat && store.lng}
                <p class="distance">
                  {(calcDistance(userLocation.lat, userLocation.lng, store.lat, store.lng)).toFixed(1)} mi away
                </p>
              {/if}
            </div>
            <button
              class="add-btn"
              on:click={() => handleAddToCart(store)}
            >
              + Add to Cart
            </button>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>

<style>
  .search-container {
    max-width: 1200px;
    margin: 0 auto;
  }

  .search-box {
    position: relative;
    margin-bottom: 20px;
  }

  input {
    width: 100%;
    padding: 14px 16px;
    border: 2px solid #ddd;
    border-radius: 8px;
    font-size: 16px;
    font-family: inherit;
    transition: border-color 0.3s;
  }

  input:focus {
    outline: none;
    border-color: #FF6B35;
    box-shadow: 0 0 0 3px rgba(255, 107, 53, 0.1);
  }

  input:disabled {
    background: #f5f5f5;
    cursor: not-allowed;
  }

  .spinner {
    position: absolute;
    right: 14px;
    top: 50%;
    transform: translateY(-50%);
    width: 18px;
    height: 18px;
    border: 2px solid #f0f0f0;
    border-top-color: #FF6B35;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: translateY(-50%) rotate(360deg); }
  }

  .location-toggle {
    display: flex;
    gap: 12px;
    align-items: center;
    margin-bottom: 16px;
  }

  .geo-btn {
    padding: 8px 14px;
    background: white;
    border: 2px solid #FF6B35;
    color: #FF6B35;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 500;
    font-size: 13px;
    transition: all 0.2s;
  }

  .geo-btn:hover:not(:disabled) {
    background: #fff5f0;
  }

  .geo-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .location-indicator {
    font-size: 12px;
    color: #666;
    padding: 0 8px;
  }

  .error-box {
    background: #fee;
    color: #c33;
    padding: 12px;
    border-radius: 6px;
    margin-bottom: 16px;
    font-size: 14px;
  }

  .results {
    min-height: 200px;
  }

  .loading, .no-results, .hint {
    text-align: center;
    color: #999;
    padding: 40px 20px;
    font-size: 14px;
  }

  .store-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
  }

  .store-card {
    background: white;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    transition: all 0.2s;
  }

  .store-card:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
    transform: translateY(-2px);
  }

  .store-header {
    display: flex;
    justify-content: space-between;
    align-items: start;
    margin-bottom: 12px;
  }

  .store-header h3 {
    margin: 0;
    font-size: 16px;
    color: #1a1a1a;
    flex: 1;
  }

  .store-number {
    background: #f5f5f5;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    color: #666;
    font-weight: 500;
    white-space: nowrap;
    margin-left: 8px;
  }

  .store-info {
    margin-bottom: 12px;
  }

  .store-info p {
    margin: 4px 0;
    font-size: 14px;
    color: #666;
  }

  .city {
    font-weight: 500;
    color: #333;
  }

  .distance {
    color: #FF6B35;
    font-weight: 500;
    font-size: 13px;
  }

  .add-btn {
    width: 100%;
    padding: 10px;
    background: #FF6B35;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
    font-size: 14px;
    transition: background 0.2s;
  }

  .add-btn:hover {
    background: #E55A24;
  }

  @media (max-width: 640px) {
    .store-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
