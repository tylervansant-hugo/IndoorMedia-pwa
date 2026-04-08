<script>
  import { searchResults, loading, error, setLoading, setError, addToCart } from '../lib/stores.js';
  import { onMount } from 'svelte';

  let searchTerm = '';
  let allStores = [];
  let filtered = [];
  let useGeolocation = false;
  let userLocation = null;
  let storeCycleFilter = 'all';

  // Store phone number lookup (cached)
  let storePhones = {};
  const PLACES_KEY = 'AIzaSyBoslNJj8aO6wkQOfkH9e4qTVJZ-G9nOuA';
  
  async function lookupStorePhone(store) {
    const key = store.StoreName;
    if (storePhones[key] !== undefined) return; // already looked up or in progress
    storePhones[key] = 'loading';
    storePhones = storePhones; // trigger reactivity
    try {
      const query = `${store.GroceryChain} ${store.Address} ${store.City} ${store.State}`;
      const res = await fetch('https://places.googleapis.com/v1/places:searchText', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Goog-Api-Key': PLACES_KEY,
          'X-Goog-FieldMask': 'places.nationalPhoneNumber,places.internationalPhoneNumber' },
        body: JSON.stringify({ textQuery: query, maxResultCount: 1 })
      });
      const data = await res.json();
      const phone = data.places?.[0]?.nationalPhoneNumber || data.places?.[0]?.internationalPhoneNumber || '';
      storePhones[key] = phone;
      storePhones = storePhones;
    } catch { storePhones[key] = ''; storePhones = storePhones; }
  }

  // ROI Calculator state
  let roiStore = null;
  let roiInvestment = '0';
  let roiAvgSpend = 50;
  let roiNewCustomers = 10;
  let roiVisitsPerYear = 12;
  let roiCouponDiscount = 0;
  let roiTotalRedemptions = 0;
  let roiCOGS = 0;

  function showROI(totalPrice, store) {
    roiStore = store.StoreName;
    roiInvestment = String(totalPrice).replace('$', '').replace(',', '');
    roiAvgSpend = 50;
    roiNewCustomers = 10;
    roiVisitsPerYear = 12;
    roiCouponDiscount = 0;
    roiTotalRedemptions = 0;
    roiCOGS = 0;
  }

  function exportROI(store) {
    const investment = parseFloat(roiInvestment.replace(/,/g, ''));
    const grossRevenue = roiAvgSpend * roiNewCustomers * 12 * (roiVisitsPerYear || 1);
    const cogsAmount = grossRevenue * ((roiCOGS || 0) / 100);
    const annualRevenue = grossRevenue - cogsAmount;
    const annualRedemptions = (roiTotalRedemptions || 0) * 12;
    const couponRevenue = annualRedemptions ? (roiAvgSpend - (roiCouponDiscount || 0)) * annualRedemptions : 0;
    const couponCOGS = couponRevenue * ((roiCOGS || 0) / 100);
    const totalRevenue = annualRevenue + couponRevenue - couponCOGS;
    const couponCost = (roiCouponDiscount || 0) * annualRedemptions;
    const netRevenue = totalRevenue - couponCost;
    const roiPercent = ((netRevenue - investment) / investment * 100).toFixed(0);
    const monthlyRevenue = roiAvgSpend * roiNewCustomers * (roiVisitsPerYear || 1);
    const netProfit = netRevenue - investment;
    const date = new Date().toLocaleDateString();

    const html = `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ROI Report — ${store.GroceryChain} ${store.City}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 24px; max-width: 600px; margin: 0 auto; background: #fff; }
  .header { background: linear-gradient(135deg, #CC0000, #8B0000); color: white; padding: 24px; border-radius: 12px; margin-bottom: 24px; text-align: center; }
  .header h1 { font-size: 22px; margin-bottom: 4px; }
  .header p { font-size: 14px; opacity: 0.9; }
  .section { margin-bottom: 20px; }
  .section h3 { font-size: 15px; color: #666; margin-bottom: 8px; border-bottom: 2px solid #eee; padding-bottom: 4px; }
  .row { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; background: #f9f9f9; border-radius: 8px; margin-bottom: 6px; }
  .row.highlight { background: #f0fff0; border: 2px solid #2e7d32; }
  .label { font-size: 13px; color: #555; }
  .value { font-size: 16px; font-weight: 700; }
  .green { color: #2e7d32; }
  .red { color: #c33; }
  .big { font-size: 22px; color: #2e7d32; }
  .footer { text-align: center; color: #999; font-size: 12px; margin-top: 30px; padding-top: 16px; border-top: 1px solid #eee; }
  .logo { font-size: 18px; font-weight: 700; color: #CC0000; margin-bottom: 4px; }
  @media print { body { padding: 12px; } .no-print { display: none; } }
</style></head><body>
<div class="header">
  <h1>📊 ROI Analysis Report</h1>
  <p>${store.GroceryChain} — ${store.City}, ${store.State}</p>
  <p>Store: ${store.StoreName} | ${date}</p>
</div>

<div class="section">
  <h3>📋 Inputs</h3>
  <div class="row"><span class="label">Investment</span><span class="value">$${investment.toLocaleString()}</span></div>
  <div class="row"><span class="label">Avg Customer Spend</span><span class="value">$${roiAvgSpend}</span></div>
  <div class="row"><span class="label">New Customers / Month</span><span class="value">${roiNewCustomers}</span></div>
  <div class="row"><span class="label">Visits / Year</span><span class="value">${roiVisitsPerYear}</span></div>
  ${roiCouponDiscount ? `<div class="row"><span class="label">Avg Discount per Coupon</span><span class="value">$${roiCouponDiscount}</span></div>` : ''}
  ${roiTotalRedemptions ? `<div class="row"><span class="label">Monthly Coupon Redemptions</span><span class="value">${roiTotalRedemptions}</span></div>` : ''}
  ${roiCOGS ? `<div class="row"><span class="label">Cost of Goods Sold</span><span class="value">${roiCOGS}%</span></div>` : ''}
</div>

<div class="section">
  <h3>💰 Revenue Analysis</h3>
  <div class="row"><span class="label">Monthly Revenue (New Customers)</span><span class="value green">$${monthlyRevenue.toLocaleString()}/mo</span></div>
  <div class="row"><span class="label">Gross Annual Revenue</span><span class="value green">$${grossRevenue.toLocaleString()}</span></div>
  ${roiCOGS ? `<div class="row"><span class="label">Cost of Goods Sold (${roiCOGS}%)</span><span class="value red">-$${cogsAmount.toLocaleString()}</span></div>
  <div class="row"><span class="label">Net Annual Revenue</span><span class="value green">$${annualRevenue.toLocaleString()}</span></div>` : ''}
  ${roiTotalRedemptions ? `<div class="row"><span class="label">Annual Redemptions (${roiTotalRedemptions}/mo × 12)</span><span class="value">${annualRedemptions.toLocaleString()}</span></div>
  <div class="row"><span class="label">Coupon Redemption Revenue</span><span class="value green">$${couponRevenue.toLocaleString()}</span></div>
  <div class="row"><span class="label">Coupon Discount Cost</span><span class="value red">-$${couponCost.toLocaleString()}</span></div>` : ''}
</div>

<div class="section">
  <h3>📊 Results</h3>
  <div class="row highlight"><span class="label">Return on Investment</span><span class="value big">${roiPercent}% ROI</span></div>
  <div class="row"><span class="label">Net Profit</span><span class="value green">$${netProfit.toLocaleString()}</span></div>
</div>

<div class="footer">
  <div class="logo">imPro — IndoorMedia</div>
  <p>Generated ${date} | Register Tape Advertising</p>
</div>

<div class="no-print" style="text-align:center;margin-top:20px;">
  <button onclick="window.print()" style="padding:12px 32px;background:#CC0000;color:white;border:none;border-radius:8px;font-size:16px;cursor:pointer;">🖨️ Print / Save as PDF</button>
</div>
</body></html>`;

    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const w = window.open(url, '_blank');
    if (!w) {
      // Fallback: download as file
      const a = document.createElement('a');
      a.href = url;
      a.download = `ROI-Report-${store.StoreName}-${new Date().toISOString().slice(0,10)}.html`;
      a.click();
    }
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  }

  function shareROI(store) {
    const investment = parseFloat(roiInvestment.replace(/,/g, ''));
    const cogsRate = (roiCOGS || 0) / 100;
    const annualRedemptions = (roiTotalRedemptions || 0) * 12;
    const couponCost = (roiCouponDiscount || 0) * annualRedemptions;
    const calcSc = (mult) => {
      const c = Math.round(roiNewCustomers * mult);
      const cR = roiAvgSpend * c * 12 * (roiVisitsPerYear || 1);
      const cpR = annualRedemptions ? (roiAvgSpend - (roiCouponDiscount || 0)) * annualRedemptions : 0;
      const tot = cR * (1 - cogsRate) + cpR * (1 - cogsRate) - couponCost;
      const p = Math.round(tot - investment);
      return { profit: p, roi: ((p / investment) * 100).toFixed(0), customers: c * 12 };
    };
    const con = calcSc(0); const bal = calcSc(1); const opt = calcSc(3);

    const text = `📊 ROI Report — ${store.GroceryChain} ${store.City}, ${store.State}
Store: ${store.StoreName}

💰 Investment: $${investment.toLocaleString()}

📊 THREE SCENARIOS:
🟢 Conservative (coupons only): $${con.profit.toLocaleString()} profit / ${con.roi}% ROI
🔵 Balanced (${roiNewCustomers} new/mo): $${bal.profit.toLocaleString()} profit / ${bal.roi}% ROI
🚀 Optimistic (${roiNewCustomers * 3} new/mo): $${opt.profit.toLocaleString()} profit / ${opt.roi}% ROI

*Many shoppers see your ad every visit but never use a coupon — they still become customers.

— IndoorMedia Register Tape Advertising`;

    if (navigator.share) {
      navigator.share({ title: `ROI Report — ${store.GroceryChain}`, text }).catch(() => {});
    } else {
      navigator.clipboard.writeText(text).then(() => alert('📋 ROI report copied to clipboard!')).catch(() => {});
    }
  }

  async function loadStores() {
    try {
      setLoading(true);
      const response = await fetch(import.meta.env.BASE_URL + 'data/stores.json');
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
      (store.State && store.State.toLowerCase().includes(term)) ||
      (store.PostalCode && store.PostalCode.includes(term))
    ).slice(0, 50);

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
    // Lookup phone number when expanding
    if (expandedStore === storeName) {
      const store = filtered.find(s => s.StoreName === storeName) || allStores.find(s => s.StoreName === storeName);
      if (store) lookupStorePhone(store);
    }
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

  let addedToCartMsg = '';

  function handleAddToCart(store, selectedAdType, plan) {
    const isCoop = coopUnlocked[store.StoreName] || false;
    const base = selectedAdType === 'double' ? store.DoubleAd : store.SingleAd;
    const pricing = calcPricing(base, isCoop);
    
    const planNames = {
      monthly: 'Monthly (12 payments)',
      threeMonth: '3-Month (10% off)',
      sixMonth: '6-Month (7.5% off)',
      pif: 'Paid-in-Full (15% off)'
    };

    const priceDisplay = {
      monthly: `$${pricing.monthly}/mo × 12 = $${pricing.monthlyTotal}`,
      threeMonth: `$${pricing.threeMonth} × 3 = $${pricing.threeMonthTotal}`,
      sixMonth: `$${pricing.sixMonth} × 6 = $${pricing.sixMonthTotal}`,
      pif: `$${pricing.pif}`
    };

    const item = {
      id: Date.now(),
      name: `Register Tape — ${isCoop ? 'Co-Op' : 'Standard'}`,
      emoji: '🧾',
      store: `${store.GroceryChain} - ${store.City}`,
      storeNum: store.StoreName,
      storeAddress: store.Address || '',
      storeCycle: store.Cycle || '',
      plan: `${selectedAdType === 'double' ? 'Double' : 'Single'} Ad — ${planNames[plan]}`,
      price: priceDisplay[plan],
      addedAt: new Date().toISOString(),
    };

    // Save to localStorage (same format as Cart.svelte)
    try {
      const cart = JSON.parse(localStorage.getItem('indoormedia_cart') || '[]');
      cart.push(item);
      localStorage.setItem('indoormedia_cart', JSON.stringify(cart));
      addedToCartMsg = `✅ Added ${store.GroceryChain} - ${store.City}`;
      setTimeout(() => { addedToCartMsg = ''; }, 2500);
    } catch (err) {
      console.error('Failed to add to cart:', err);
    }
  }

  onMount(loadStores);
</script>

<div class="search-container">
  <h2>🏪 Store Network</h2>
  <p class="subtitle">Find pricing and delivery info for 7,835+ stores nationwide</p>

  <div class="search-box">
    <input
      type="text"
      placeholder="Search by store name, city, zip code, or number..."
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

  <div class="cycle-filter">
    <button class="cycle-btn" class:active={storeCycleFilter === 'all'} on:click={() => storeCycleFilter = 'all'}>All</button>
    <button class="cycle-btn" class:active={storeCycleFilter === 'A'} on:click={() => storeCycleFilter = 'A'}>Cycle A</button>
    <button class="cycle-btn" class:active={storeCycleFilter === 'B'} on:click={() => storeCycleFilter = 'B'}>Cycle B</button>
    <button class="cycle-btn" class:active={storeCycleFilter === 'C'} on:click={() => storeCycleFilter = 'C'}>Cycle C</button>
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
        {#each filtered.filter(s => storeCycleFilter === 'all' || s.Cycle === storeCycleFilter) as store (store.StoreName)}
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
              {#if storePhones[store.StoreName] && storePhones[store.StoreName] !== 'loading'}
                <p class="store-phone"><a href="tel:{storePhones[store.StoreName]}">📞 {storePhones[store.StoreName]}</a></p>
              {:else if storePhones[store.StoreName] === 'loading'}
                <p class="store-phone" style="color: var(--text-secondary, #999);">📞 Looking up...</p>
              {/if}
              <p class="cycle">Cycle: {store.Cycle} | Cases: {store['Case Count']}{store.InstallDay ? ` | In Stores: ${store.InstallDay}${store.InstallDay == 1 || store.InstallDay == 21 || store.InstallDay == 31 ? 'st' : store.InstallDay == 2 || store.InstallDay == 22 ? 'nd' : store.InstallDay == 3 || store.InstallDay == 23 ? 'rd' : 'th'}` : ''}</p>
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
                <!-- Ad Type Toggle in Expanded View -->
                <div class="expanded-ad-toggle">
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

                <h4>All Payment Plans — {currentAdType === 'double' ? 'Double' : 'Single'} Ad {isCoop ? '(Co-Op)' : '(Standard)'}</h4>
                
                <div class="plan-card" on:click={() => handleAddToCart(store, currentAdType, 'monthly')}>
                  <div class="plan-header">
                    <span class="plan-name">📅 Monthly</span>
                    <span class="plan-badge">12 payments</span>
                  </div>
                  <div class="plan-price">${pricing.monthly}<span class="per">/month</span></div>
                  <div class="plan-total">Total: ${pricing.monthlyTotal}</div>
                  <button class="roi-btn" on:click|stopPropagation={() => showROI(pricing.monthlyTotal, store)}>📊 ROI Calculator</button>
                </div>

                <div class="plan-card" on:click={() => handleAddToCart(store, currentAdType, 'threeMonth')}>
                  <div class="plan-header">
                    <span class="plan-name">📦 3-Month</span>
                    <span class="plan-badge save">Save 10%</span>
                  </div>
                  <div class="plan-price">${pricing.threeMonth}<span class="per"> × 3</span></div>
                  <div class="plan-total">Total: ${pricing.threeMonthTotal}</div>
                  <button class="roi-btn" on:click|stopPropagation={() => showROI(pricing.threeMonthTotal, store)}>📊 ROI Calculator</button>
                </div>

                <div class="plan-card" on:click={() => handleAddToCart(store, currentAdType, 'sixMonth')}>
                  <div class="plan-header">
                    <span class="plan-name">📦 6-Month</span>
                    <span class="plan-badge save">Save 7.5%</span>
                  </div>
                  <div class="plan-price">${pricing.sixMonth}<span class="per"> × 6</span></div>
                  <div class="plan-total">Total: ${pricing.sixMonthTotal}</div>
                  <button class="roi-btn" on:click|stopPropagation={() => showROI(pricing.sixMonthTotal, store)}>📊 ROI Calculator</button>
                </div>

                <div class="plan-card best" on:click={() => handleAddToCart(store, currentAdType, 'pif')}>
                  <div class="plan-header">
                    <span class="plan-name">⭐ Paid in Full</span>
                    <span class="plan-badge best-badge">Best Deal — 15% off</span>
                  </div>
                  <div class="plan-price">${pricing.pif}</div>
                  <div class="plan-total">One payment — Save ${pricing.savings}</div>
                  <button class="roi-btn" on:click|stopPropagation={() => showROI(pricing.pif, store)}>📊 ROI Calculator</button>
                </div>

                <p class="tap-hint">Tap a plan to add to quote</p>

                <!-- ROI Calculator -->
                {#if roiStore === store.StoreName}
                  <div class="roi-calculator">
                    <h4>📊 ROI Calculator</h4>
                    <p class="roi-subtitle">Investment: <strong>${roiInvestment}</strong></p>
                    
                    <div class="roi-field">
                      <label>Average Customer Spend ($)</label>
                      <input type="number" bind:value={roiAvgSpend} placeholder="50" />
                    </div>
                    
                    <div class="roi-field">
                      <label>New Customers per Month</label>
                      <input type="number" bind:value={roiNewCustomers} placeholder="10" />
                    </div>
                    
                    <div class="roi-field">
                      <label>Visits per Year (per customer)</label>
                      <input type="number" bind:value={roiVisitsPerYear} placeholder="12" />
                    </div>

                    <div class="roi-field">
                      <label>Avg Discount per Coupon ($)</label>
                      <input type="number" bind:value={roiCouponDiscount} placeholder="0" />
                    </div>

                    <div class="roi-field">
                      <label>Monthly Coupon Redemptions</label>
                      <input type="number" bind:value={roiTotalRedemptions} placeholder="0" />
                    </div>

                    <div class="roi-field">
                      <label>Cost of Goods Sold (%)</label>
                      <input type="number" bind:value={roiCOGS} placeholder="0" min="0" max="100" />
                    </div>

                    {#if roiAvgSpend && roiNewCustomers}
                      {@const investment = parseFloat(roiInvestment.replace(/,/g, ''))}
                      {@const cogsRate = (roiCOGS || 0) / 100}
                      {@const annualRedemptions = (roiTotalRedemptions || 0) * 12}
                      {@const couponCost = (roiCouponDiscount || 0) * annualRedemptions}
                      {@const scenarioCalc = (custMultiplier) => {
                        const customers = Math.round(roiNewCustomers * custMultiplier);
                        const custRevenue = roiAvgSpend * customers * 12 * (roiVisitsPerYear || 1);
                        const custCogs = custRevenue * cogsRate;
                        const couponRev = annualRedemptions ? (roiAvgSpend - (roiCouponDiscount || 0)) * annualRedemptions : 0;
                        const couponCogs = couponRev * cogsRate;
                        const totalRev = custRevenue - custCogs + couponRev - couponCogs - couponCost;
                        const profit = totalRev - investment;
                        const roi = ((profit / investment) * 100).toFixed(0);
                        return { customers, totalRev: Math.round(totalRev), profit: Math.round(profit), roi, totalNewCustomers: customers * 12 };
                      }}
                      {@const conservative = scenarioCalc(0)}
                      {@const balanced = scenarioCalc(1)}
                      {@const optimistic = scenarioCalc(3)}
                      {@const monthlyRevenue = roiAvgSpend * roiNewCustomers * (roiVisitsPerYear || 1)}
                      
                      <div class="roi-results">
                        <div class="roi-result-card">
                          <span class="roi-label">Monthly Revenue (Balanced)</span>
                          <span class="roi-value green">${monthlyRevenue.toLocaleString()}/mo</span>
                        </div>
                        <div class="roi-result-card highlight">
                          <span class="roi-label">Return on Investment (Balanced)</span>
                          <span class="roi-value big">{balanced.roi}% ROI</span>
                        </div>
                        <div class="roi-result-card">
                          <span class="roi-label">Net Profit (Balanced)</span>
                          <span class="roi-value green">${balanced.profit.toLocaleString()}</span>
                        </div>
                      </div>

                      <div class="scenario-section">
                        <h5>📊 Three Scenarios</h5>
                        <p class="scenario-hint">Many shoppers see your ad but never use a coupon — they still become customers.</p>
                        <div class="scenario-row">
                          <div class="scenario-box conservative">
                            <div class="sc-label">🟢 Conservative</div>
                            <div class="sc-desc">Coupons only</div>
                            <div class="sc-profit">${conservative.profit.toLocaleString()}</div>
                            <div class="sc-roi">{conservative.roi}% ROI</div>
                          </div>
                          <div class="scenario-box balanced">
                            <div class="sc-label">🔵 Balanced</div>
                            <div class="sc-desc">{balanced.customers} new/mo</div>
                            <div class="sc-profit">${balanced.profit.toLocaleString()}</div>
                            <div class="sc-roi">{balanced.roi}% ROI</div>
                          </div>
                          <div class="scenario-box optimistic">
                            <div class="sc-label">🚀 Optimistic</div>
                            <div class="sc-desc">{optimistic.customers} new/mo</div>
                            <div class="sc-profit">${optimistic.profit.toLocaleString()}</div>
                            <div class="sc-roi">{optimistic.roi}% ROI</div>
                          </div>
                        </div>
                      </div>
                    {/if}

                    <div class="roi-action-btns">
                      <button class="roi-export-btn" on:click={() => exportROI(store)}>📄 Export Report</button>
                      <button class="roi-share-btn" on:click={() => shareROI(store)}>📤 Share</button>
                    </div>
                    <button class="roi-close-btn" on:click={() => { roiStore = null; }}>Close Calculator</button>
                  </div>
                {/if}
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  </div>

  {#if addedToCartMsg}
    <div class="cart-toast">{addedToCartMsg}</div>
  {/if}
</div>

<style>
  .search-container {
    max-width: 1200px;
    margin: 0 auto;
  }

  h2 {
    margin: 0 0 0.5rem 0;
    font-size: 24px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .subtitle {
    margin: 0 0 20px 0;
    font-size: 14px;
    color: var(--text-secondary);
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

  .store-phone a { color: #1565C0; text-decoration: none; font-weight: 600; }
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

  .expanded-ad-toggle {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
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

  .roi-btn {
    width: 100%;
    margin-top: 8px;
    padding: 8px;
    background: #f0f0f0;
    color: #CC0000;
    border: 2px solid #CC0000;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .roi-btn:hover {
    background: #CC0000;
    color: white;
  }

  .scenario-section { margin-top: 14px; }
  .scenario-section h5 { font-size: 14px; margin: 0 0 4px; color: var(--text-primary); }
  .scenario-hint { font-size: 11px; color: var(--text-secondary, #888); margin: 0 0 10px; font-style: italic; }
  .scenario-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
  .scenario-box { padding: 10px; border-radius: 8px; text-align: center; border: 2px solid var(--border-color, #e0e0e0); background: var(--card-bg, white); }
  .scenario-box.conservative { border-color: #43A047; }
  .scenario-box.balanced { border-color: #1565C0; }
  .scenario-box.optimistic { border-color: #E65100; }
  .sc-label { font-size: 12px; font-weight: 800; }
  .scenario-box.conservative .sc-label { color: #43A047; }
  .scenario-box.balanced .sc-label { color: #1565C0; }
  .scenario-box.optimistic .sc-label { color: #E65100; }
  .sc-desc { font-size: 10px; color: var(--text-secondary, #888); margin-bottom: 6px; }
  .sc-profit { font-size: 16px; font-weight: 800; color: #2E7D32; }
  .sc-roi { font-size: 12px; font-weight: 700; color: var(--text-secondary, #666); }
  .roi-calculator {
    background: #f9f9f9;
    border: 2px solid #CC0000;
    border-radius: 12px;
    padding: 16px;
    margin-top: 16px;
  }

  .roi-calculator h4 {
    margin: 0 0 4px;
    color: #333;
    font-size: 16px;
  }

  .roi-subtitle {
    margin: 0 0 16px;
    color: #666;
    font-size: 14px;
  }

  .roi-field {
    margin-bottom: 12px;
  }

  .roi-field label {
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: #333;
    margin-bottom: 4px;
  }

  .roi-field input {
    width: 100%;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 6px;
    font-size: 14px;
    box-sizing: border-box;
  }

  .roi-field input:focus {
    outline: none;
    border-color: #CC0000;
    box-shadow: 0 0 0 2px rgba(204, 0, 0, 0.1);
  }

  .roi-results {
    margin-top: 16px;
    display: grid;
    gap: 8px;
  }

  .roi-result-card {
    background: white;
    border-radius: 8px;
    padding: 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border: 1px solid #eee;
  }

  .roi-result-card.highlight {
    background: #f0fff0;
    border: 2px solid #2e7d32;
  }

  .roi-label {
    font-size: 13px;
    color: #555;
  }

  .roi-value {
    font-size: 16px;
    font-weight: 700;
    color: #333;
  }

  .roi-value.green {
    color: #2e7d32;
  }

  .roi-value.big {
    font-size: 20px;
    color: #2e7d32;
  }

  .roi-action-btns {
    display: flex;
    gap: 8px;
    margin-top: 12px;
  }

  .roi-export-btn, .roi-share-btn {
    flex: 1;
    padding: 10px;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .roi-export-btn {
    background: #CC0000;
    color: white;
  }

  .roi-export-btn:hover {
    background: #a00;
  }

  .roi-share-btn {
    background: #2e7d32;
    color: white;
  }

  .roi-share-btn:hover {
    background: #1b5e20;
  }

  .roi-close-btn {
    width: 100%;
    margin-top: 12px;
    padding: 10px;
    background: #999;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    cursor: pointer;
  }

  .roi-close-btn:hover {
    background: #777;
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

  .cart-toast {
    position: fixed;
    bottom: 80px;
    left: 50%;
    transform: translateX(-50%);
    background: #2e7d32;
    color: white;
    padding: 12px 24px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    z-index: 1000;
    animation: slideUp 0.3s ease-out;
  }

  @keyframes slideUp {
    from { transform: translateX(-50%) translateY(20px); opacity: 0; }
    to { transform: translateX(-50%) translateY(0); opacity: 1; }
  }

  @media (max-width: 640px) {
    .store-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
