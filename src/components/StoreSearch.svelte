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
      const response = await fetch('/data/stores.json');
      if (!response.ok) throw new Error('Failed to load stores');
      const data = await response.json();
      allStores = data || [];
      console.log(`Loaded ${allStores.length} stores`);
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
      (store.StoreName && store.StoreName.toLowerCase().includes(term)) ||
      (store.GroceryChain && store.GroceryChain.toLowerCase().includes(term)) ||
      (store.City && store.City.toLowerCase().includes(term)) ||
      (store.Address && store.Address.toLowerCase().includes(term)) ||
      (store.State && store.State.toLowerCase().includes(term))
    ).slice(0, 20);

    searchResults.set(filtered);
  }

  function findNearby() {
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
        
        // Sort ALL stores by distance, show closest 20
        filtered = allStores
          .filter(s => s.latitude && s.longitude)
          .map(s => ({
            ...s,
            _dist: calcDistance(latitude, longitude, s.latitude, s.longitude)
          }))
          .sort((a, b) => a._dist - b._dist)
          .slice(0, 20);
        
        searchTerm = '';
        searchResults.set(filtered);
        setLoading(false);
      },
      (err) => {
        setError('Unable to access location. Please allow location access.');
        setLoading(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
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

  // Track expanded cards, ad type, and co-op unlock
  let expandedStore = null;
  let adType = {}; // { storeName: 'single' | 'double' }
  let coopUnlocked = {}; // { storeName: true/false }

  function toggleExpand(storeName) {
    expandedStore = expandedStore === storeName ? null : storeName;
    if (!adType[storeName]) adType[storeName] = 'single';
  }

  function toggleAdType(storeName) {
    adType[storeName] = adType[storeName] === 'single' ? 'double' : 'single';
    adType = adType; // trigger reactivity
  }

  function unlockCoop(storeName) {
    coopUnlocked[storeName] = !coopUnlocked[storeName];
    coopUnlocked = coopUnlocked; // trigger reactivity
  }

  // Payment plan calculations
  // Standard = base + $1,200 pad + $125 production
  // Co-Op = base + $125 production (no pad)
  function calcPricing(basePrice, isCoop = false) {
    const prod = 125;
    const pad = isCoop ? 0 : 1200;
    const total = basePrice + pad + prod;
    return {
      monthly: (total / 12).toFixed(2),
      monthlyTotal: total.toFixed(2),
      threeMonth: (((( basePrice + pad) * 0.90) + prod) / 3).toFixed(2),
      threeMonthTotal: ((( basePrice + pad) * 0.90) + prod).toFixed(2),
      sixMonth: ((((basePrice + pad) * 0.925) + prod) / 6).toFixed(2),
      sixMonthTotal: (((basePrice + pad) * 0.925) + prod).toFixed(2),
      pif: (((basePrice + pad) * 0.85) + prod).toFixed(2),
      savings: ((basePrice + pad) * 0.15).toFixed(2)
    };
  }

  function handleAddToCart(store, selectedAdType, plan) {
    const base = selectedAdType === 'double' ? store.DoubleAd : store.SingleAd;
    const pricing = calcPricing(base);
    const planLabels = {
      monthly: `$${pricing.monthly}/mo × 12`,
      threeMonth: `$${pricing.threeMonth} × 3`,
      sixMonth: `$${pricing.sixMonth} × 6`,
      pif: `$${pricing.pif} (Paid in Full)`
    };

    addToCart({
      id: `${store.StoreName}-${selectedAdType}-${plan}`,
      type: 'store',
      name: `${store.GroceryChain} - ${store.City}`,
      storeNumber: store.StoreName,
      city: store.City,
      chain: store.GroceryChain,
      adType: selectedAdType === 'double' ? 'Double Ad' : 'Single Ad',
      plan: plan,
      planLabel: planLabels[plan],
      price: plan === 'pif' ? pricing.pif : plan === 'monthly' ? pricing.monthlyTotal : plan === 'threeMonth' ? pricing.threeMonthTotal : pricing.sixMonthTotal
    });
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

  <div class="location-toggle">
    <button
      class="geo-btn"
      on:click={findNearby}
      disabled={$loading}
    >
      📍 Find Nearby Stores
    </button>
    {#if useGeolocation && userLocation}
      <span class="location-indicator">Using your location</span>
    {/if}
  </div>

  {#if $error}
    <div class="error-box">{$error}</div>
  {/if}

  <div class="results">
    {#if $loading}
      <p class="loading">Loading stores...</p>
    {:else if filtered.length === 0 && searchTerm}
      <p class="no-results">
        <span style="font-size: 2rem; margin-bottom: 1rem; display: block;">🔍</span>
        No stores found for "{searchTerm}"<br/>
        <span style="font-size: 0.9rem; color: #999; margin-top: 0.5rem; display: block;">Try searching by:</span>
        <span style="font-size: 0.85rem; color: #999;">Store #, City, Chain, or Address</span>
      </p>
    {:else if filtered.length === 0}
      <p class="hint">Start typing to search for stores</p>
    {:else}
      <div class="store-grid">
        {#each filtered as store (store.StoreName)}
          {@const currentAdType = adType[store.StoreName] || 'single'}
          {@const basePrice = currentAdType === 'double' ? store.DoubleAd : store.SingleAd}
          {@const isCoop = coopUnlocked[store.StoreName] || false}
          {@const stdPricing = calcPricing(basePrice, false)}
          {@const coopPricing = calcPricing(basePrice, true)}
          {@const pricing = isCoop ? coopPricing : stdPricing}
          {@const isExpanded = expandedStore === store.StoreName}
          <div class="store-card" class:expanded={isExpanded} class:coop-active={isCoop}>
            <div class="store-header" on:click={() => toggleExpand(store.StoreName)}>
              <div>
                <h3>{store.GroceryChain}</h3>
                <span class="store-number">{store.StoreName}</span>
              </div>
              <span class="expand-icon">{isExpanded ? '▲' : '▼'}</span>
            </div>
            <div class="store-info">
              <p class="address">{store.Address}</p>
              <p class="city">{store.City}, {store.State} {store.PostalCode}</p>
              <p class="cycle">Cycle: {store.Cycle} | Cases: {store['Case Count']}</p>
              {#if useGeolocation && userLocation && store.latitude && store.longitude}
                <p class="distance">
                  📍 {(calcDistance(userLocation.lat, userLocation.lng, store.latitude, store.longitude)).toFixed(1)} mi away
                </p>
              {/if}
            </div>

            <!-- Ad Type Toggle -->
            <div class="ad-toggle">
              <button
                class="ad-btn"
                class:active={currentAdType === 'single'}
                on:click={() => { adType[store.StoreName] = 'single'; adType = adType; }}
              >Single Ad</button>
              <button
                class="ad-btn"
                class:active={currentAdType === 'double'}
                on:click={() => { adType[store.StoreName] = 'double'; adType = adType; }}
              >Double Ad</button>
            </div>

            <!-- Standard Pricing (always visible) -->
            <div class="pricing-label">{isCoop ? '🤝 Co-Op Pricing' : '💼 Standard Pricing'}</div>
            <div class="pricing">
              <div class="price-row">
                <span class="price-label">Monthly</span>
                <span class="price-value">${pricing.monthly}/mo × 12 = ${pricing.monthlyTotal}</span>
              </div>
              <div class="price-row highlight">
                <span class="price-label">Paid in Full</span>
                <span class="price-value pif">${pricing.pif} (15% off)</span>
              </div>
            </div>

            <!-- Co-Op Unlock Button -->
            <button
              class="coop-btn"
              class:unlocked={isCoop}
              on:click={() => unlockCoop(store.StoreName)}
            >
              {isCoop ? '🔓 Showing Co-Op Pricing — Tap to Reset' : '🔒 Manager Approved Co-Op'}
            </button>

            <!-- Expanded: All 4 Payment Plans -->
            {#if isExpanded}
              <div class="expanded-pricing">
                <h4>All Payment Plans — {currentAdType === 'double' ? 'Double' : 'Single'} Ad {isCoop ? '(Co-Op)' : '(Standard)'}</h4>
                
                <div class="plan-card" on:click={() => handleAddToCart(store, currentAdType, 'monthly')}>
                  <div class="plan-header">
                    <span class="plan-name">📅 Monthly</span>
                    <span class="plan-badge">12 payments</span>
                  </div>
                  <div class="plan-price">${pricing.monthly}<span class="per">/month</span></div>
                  <div class="plan-total">Total: ${pricing.monthlyTotal}</div>
                </div>

                <div class="plan-card" on:click={() => handleAddToCart(store, currentAdType, 'threeMonth')}>
                  <div class="plan-header">
                    <span class="plan-name">📦 3-Month</span>
                    <span class="plan-badge save">Save 10%</span>
                  </div>
                  <div class="plan-price">${pricing.threeMonth}<span class="per"> × 3</span></div>
                  <div class="plan-total">Total: ${pricing.threeMonthTotal}</div>
                </div>

                <div class="plan-card" on:click={() => handleAddToCart(store, currentAdType, 'sixMonth')}>
                  <div class="plan-header">
                    <span class="plan-name">📦 6-Month</span>
                    <span class="plan-badge save">Save 7.5%</span>
                  </div>
                  <div class="plan-price">${pricing.sixMonth}<span class="per"> × 6</span></div>
                  <div class="plan-total">Total: ${pricing.sixMonthTotal}</div>
                </div>

                <div class="plan-card best" on:click={() => handleAddToCart(store, currentAdType, 'pif')}>
                  <div class="plan-header">
                    <span class="plan-name">⭐ Paid in Full</span>
                    <span class="plan-badge best-badge">Best Deal — 15% off</span>
                  </div>
                  <div class="plan-price">${pricing.pif}</div>
                  <div class="plan-total">One payment — Save ${pricing.savings}</div>
                </div>

                <p class="tap-hint">Tap a plan to add to cart</p>
              </div>
            {/if}
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
    border-color: #CC0000;
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
    border-top-color: #CC0000;
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
    border: 2px solid #CC0000;
    color: #CC0000;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 500;
    font-size: 13px;
    transition: all 0.2s;
  }

  .geo-btn:hover:not(:disabled) {
    background: #fff0f0;
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
    background: #ffe0e0;
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
    color: #CC0000;
    font-weight: 500;
    font-size: 13px;
  }

  .pricing {
    background: #f8f9fa;
    border-radius: 6px;
    padding: 10px;
    margin-bottom: 12px;
  }

  .price-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 0;
    font-size: 13px;
  }

  .price-row.highlight {
    border-top: 1px solid #e0e0e0;
    padding-top: 8px;
    margin-top: 4px;
  }

  .price-label {
    color: #666;
    font-weight: 500;
  }

  .price-value {
    color: #333;
    font-weight: 600;
  }

  .price-value.pif {
    color: #CC0000;
    font-weight: 700;
  }

  .address {
    font-size: 13px !important;
  }

  .cycle {
    font-size: 12px !important;
    color: #999 !important;
  }

  .store-header {
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: start;
    margin-bottom: 12px;
  }

  .expand-icon {
    color: #999;
    font-size: 12px;
    padding: 4px;
  }

  .store-card.expanded {
    border: 2px solid #CC0000;
  }

  /* Ad Type Toggle */
  .ad-toggle {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
  }

  .ad-btn {
    flex: 1;
    padding: 8px;
    border: 2px solid #ddd;
    background: white;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .ad-btn.active {
    border-color: #CC0000;
    background: #CC0000;
    color: white;
  }

  /* Expanded Pricing */
  .expanded-pricing {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 2px solid #eee;
  }

  .expanded-pricing h4 {
    margin: 0 0 12px 0;
    font-size: 14px;
    color: #333;
    text-align: center;
  }

  .plan-card {
    background: #f8f9fa;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 8px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .plan-card:hover {
    border-color: #CC0000;
    background: #fff5f5;
  }

  .plan-card.best {
    border-color: #CC0000;
    background: #fff0f0;
  }

  .plan-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
  }

  .plan-name {
    font-weight: 600;
    font-size: 14px;
    color: #333;
  }

  .plan-badge {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 10px;
    background: #e0e0e0;
    color: #666;
  }

  .plan-badge.save {
    background: #e8f5e9;
    color: #2e7d32;
  }

  .plan-badge.best-badge {
    background: #CC0000;
    color: white;
    font-weight: 600;
  }

  .plan-price {
    font-size: 24px;
    font-weight: 700;
    color: #1a1a1a;
    margin: 4px 0;
  }

  .plan-price .per {
    font-size: 14px;
    font-weight: 400;
    color: #666;
  }

  .plan-total {
    font-size: 13px;
    color: #666;
  }

  .pricing-label {
    font-size: 12px;
    font-weight: 600;
    color: #666;
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .coop-btn {
    width: 100%;
    padding: 10px;
    margin-top: 10px;
    border: 1px dashed #999;
    background: #f5f5f5;
    border-radius: 8px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
    color: #666;
    transition: all 0.2s;
    min-height: 44px;
    box-sizing: border-box;
  }

  .coop-btn:hover {
    border-color: #CC0000;
    color: #CC0000;
    background: #fff5f5;
  }

  .coop-btn.unlocked {
    border: 1px solid #2e7d32;
    background: #e8f5e9;
    color: #2e7d32;
  }

  .store-card.coop-active {
    border: 2px solid #2e7d32;
  }

  .tap-hint {
    text-align: center;
    font-size: 12px;
    color: #999;
    margin-top: 8px;
  }

  .add-btn {
    width: 100%;
    padding: 10px;
    background: #CC0000;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
    font-size: 14px;
    transition: background 0.2s;
  }

  .add-btn:hover {
    background: #990000;
  }

  @media (max-width: 640px) {
    .store-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
