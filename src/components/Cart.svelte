<script>
  import { onMount } from 'svelte';

  let cartItems = [];
  let allStores = [];
  let showAddProduct = false;
  let addStep = 'type'; // type, store, plan, confirm
  let newItem = { type: '', store: null, plan: '', pins: 1, price: '' };
  let storeSearch = '';

  // Zone 07 cycle launch dates (7th of each month)
  const CYCLE_MONTHS = { 'A': [0,3,6,9], 'B': [1,4,7,10], 'C': [2,5,8,11] };

  function getNextLaunch(cycle) {
    const months = CYCLE_MONTHS[cycle?.toUpperCase()];
    if (!months) return '';
    const now = new Date();
    for (let offset = 0; offset < 12; offset++) {
      const m = (now.getMonth() + offset) % 12;
      if (months.includes(m)) {
        const y = now.getFullYear() + Math.floor((now.getMonth() + offset) / 12);
        const d = new Date(y, m, 7);
        if (d > now || (d.getMonth() === now.getMonth() && d.getDate() >= now.getDate())) {
          return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        }
      }
    }
    return '';
  }

  const PRODUCT_TYPES = [
    { id: 'tape_coop', name: 'Register Tape — Co-Op', emoji: '🧾', needsStore: true },
    { id: 'tape_exclusive', name: 'Register Tape — Exclusive', emoji: '🧾', needsStore: true },
    { id: 'tape_contractor', name: 'Register Tape — Contractors', emoji: '🧾', needsStore: true },
    { id: 'cart_20_single', name: 'Cartvertising — 20% Front OR Directory', emoji: '🛒', price: '$2,995', needsStore: true, skipPlan: true },
    { id: 'cart_40_both', name: 'Cartvertising — 40% (20%+20%)', emoji: '🛒', price: '$4,795', needsStore: true, skipPlan: true },
    { id: 'cart_60_both', name: 'Cartvertising — 60% (40%+20%)', emoji: '🛒', price: '$5,995', needsStore: true, skipPlan: true },
    { id: 'cart_80_both', name: 'Cartvertising — 80% (40%+40%)', emoji: '🛒', price: '$7,395', needsStore: true, skipPlan: true },
    { id: 'cart_100_both', name: 'Cartvertising — 100% (60%+40%)', emoji: '🛒', price: '$8,795', needsStore: true, skipPlan: true },
    { id: 'cart_200_both', name: 'Cartvertising — 200% (100% Both)', emoji: '🛒', price: '$12,995', needsStore: true, skipPlan: true },
    { id: 'cart_header_50', name: 'Cartvertising — Header 50%', emoji: '🛒', price: '$2,995', needsStore: true, skipPlan: true },
    { id: 'cart_header_100', name: 'Cartvertising — Header 100%', emoji: '🛒', price: '$4,795', needsStore: true, skipPlan: true },
    { id: 'digitalboost', name: 'DigitalBoost', emoji: '🚀', price: '$3,600/pin', needsStore: true, skipPlan: true, hasPins: true, hasMap: true },
    { id: 'findlocal', name: 'FindLocal', emoji: '📍', price: '$695/location', needsStore: true, skipPlan: true, hasMap: true },
    { id: 'reviewboost', name: 'ReviewBoost', emoji: '⭐', price: '$695', needsStore: true, skipPlan: true },
    { id: 'loyaltyboost', name: 'LoyaltyBoost', emoji: '💎', price: '$3,600/year', needsStore: true, skipPlan: true },
  ];

  const PAYMENT_PLANS = {
    tape_coop: [
      { id: 'monthly', name: 'Monthly (12 payments)', calc: (base) => ((base + 125) / 12).toFixed(2) + '/mo × 12 = $' + (base + 125).toFixed(2) },
      { id: '3month', name: '3-Month (10% off)', calc: (base) => (((base * 0.90) + 125) / 3).toFixed(2) + '/payment × 3 = $' + ((base * 0.90) + 125).toFixed(2) },
      { id: '6month', name: '6-Month (7.5% off)', calc: (base) => (((base * 0.925) + 125) / 6).toFixed(2) + '/payment × 6 = $' + ((base * 0.925) + 125).toFixed(2) },
      { id: 'pif', name: 'Paid-in-Full (15% off)', calc: (base) => '$' + ((base * 0.85) + 125).toFixed(2) },
    ],
    tape_exclusive: [
      { id: 'monthly', name: 'Monthly', calc: (base) => ((base + 125) / 12).toFixed(2) + '/mo × 12 = $' + (base + 125).toFixed(2) },
      { id: 'pif', name: 'Paid-in-Full (5% off)', calc: (base) => '$' + (base * 0.95).toFixed(2) },
    ],
    tape_contractor: [
      { id: '3month', name: '3-Month', calc: (base) => (((base) + 125) / 3).toFixed(2) + '/payment × 3 = $' + ((base) + 125).toFixed(2) },
      { id: 'pif', name: 'Paid-in-Full (5% off)', calc: (base) => '$' + (base * 0.95).toFixed(2) },
    ],
  };

  onMount(async () => {
    loadCart();
    try {
      const res = await fetch(import.meta.env.BASE_URL + 'data/stores.json');
      allStores = await res.json();
    } catch {}
  });

  function loadCart() {
    try { cartItems = JSON.parse(localStorage.getItem('indoormedia_cart') || '[]'); } catch { cartItems = []; }
  }

  function saveCart() {
    localStorage.setItem('indoormedia_cart', JSON.stringify(cartItems));
  }

  function removeItem(index) {
    cartItems.splice(index, 1);
    cartItems = [...cartItems];
    saveCart();
  }

  function updateItemPrice(index, newPrice) {
    cartItems[index].price = newPrice;
    cartItems = [...cartItems];
    saveCart();
  }

  function clearCart() {
    if (confirm('Clear entire quote?')) {
      cartItems = [];
      saveCart();
    }
  }

  $: filteredStores = storeSearch
    ? allStores.filter(s =>
        s.StoreName?.toLowerCase().includes(storeSearch.toLowerCase()) ||
        s.GroceryChain?.toLowerCase().includes(storeSearch.toLowerCase()) ||
        s.City?.toLowerCase().includes(storeSearch.toLowerCase())
      ).slice(0, 15)
    : [];

  function startAdd() {
    showAddProduct = true;
    addStep = 'type';
    newItem = { type: '', store: null, plan: '', pins: 1, price: '' };
    storeSearch = '';
  }

  function selectType(type) {
    newItem.type = type.id;
    newItem.typeName = type.name;
    newItem.emoji = type.emoji;
    newItem.price = type.price || '';
    newItem.hasPins = type.hasPins || false;
    newItem.skipPlan = type.skipPlan || false;
    newItem.hasMap = type.hasMap || false;

    if (type.needsStore) {
      addStep = 'store';
    } else if (type.hasPins) {
      addStep = 'pins';
    } else {
      addItem();
    }
  }

  function selectStore(store) {
    newItem.store = store;
    newItem.storeNum = store.StoreName;
    newItem.storeAddress = store.Address || '';
    newItem.storeCycle = store.Cycle || '?';
    newItem.storeName = store.GroceryChain + ' - ' + store.City;

    if (newItem.hasPins) {
      addStep = 'pins';
    } else if (newItem.skipPlan) {
      addItem();
    } else {
      addStep = 'plan';
    }
  }

  function useMapArea() {
    // Open Google Maps for area selection, then continue without a specific store
    newItem.store = null;
    newItem.storeNum = 'MAP AREA';
    newItem.storeAddress = 'Custom map area';
    newItem.storeCycle = '-';
    newItem.storeName = 'Custom Area (see map)';
    
    if (newItem.hasPins) {
      addStep = 'pins';
    } else {
      addItem();
    }
  }

  function selectPlan(plan) {
    const base = newItem.store?.SingleAd || 0;
    newItem.plan = plan.name;
    newItem.planCalc = plan.calc(base);
    newItem.priceText = plan.calc(base); // Display version
    addStep = 'confirm';
  }

  function confirmPlan() {
    newItem.price = newItem.priceText;
    addItem();
  }

  function addItem() {
    const item = {
      id: Date.now(),
      name: newItem.typeName,
      emoji: newItem.emoji,
      store: newItem.storeName || '',
      storeNum: newItem.storeNum || '',
      storeAddress: newItem.storeAddress || '',
      storeCycle: newItem.storeCycle || '',
      plan: newItem.plan || '',
      price: newItem.price,
      pins: newItem.hasPins ? newItem.pins : null,
      addedAt: new Date().toISOString(),
    };

    if (newItem.hasPins) {
      const pinPrice = newItem.type === 'digitalboost' ? 3600 : 0;
      const production = 395;
      const total = (pinPrice * newItem.pins) + production;
      item.price = `$${total.toLocaleString()} (${newItem.pins} pin${newItem.pins > 1 ? 's' : ''} + $395 production)`;
      item.name = `DigitalBoost — ${newItem.pins} Pin${newItem.pins > 1 ? 's' : ''}`;
    }

    cartItems = [...cartItems, item];
    saveCart();
    showAddProduct = false;
    addStep = 'type';
  }

  function exportCSV() {
    if (cartItems.length === 0) return;
    const rows = [
      ['Product', 'Store', 'Store #', 'Address', 'Cycle', 'Plan', 'Price', 'Date'].join(','),
      ...cartItems.map(item =>
        [item.name, item.store || '', item.storeNum || '', item.storeAddress || '', item.storeCycle || '', item.plan || '', item.price, item.addedAt?.split('T')[0] || '']
          .map(c => `"${c}"`).join(',')
      )
    ].join('\n');

    const blob = new Blob([rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `IndoorMedia_Quote_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }
</script>

<div class="quote-container">
  <h2>Build Quote</h2>
  <p class="subtitle">Add products to build a customer quote</p>

  <button class="add-btn" on:click={startAdd}>+ Add Product</button>

  {#if showAddProduct}
    <div class="add-modal">
      {#if addStep === 'type'}
        <h3>Select Product</h3>
        <div class="type-list">
          {#each PRODUCT_TYPES as type}
            <button class="type-btn" on:click={() => selectType(type)}>
              <span class="type-emoji">{type.emoji}</span>
              <span class="type-name">{type.name}</span>
              {#if type.price}<span class="type-price">{type.price}</span>{/if}
            </button>
          {/each}
        </div>
        <button class="cancel-btn" on:click={() => showAddProduct = false}>Cancel</button>
      {/if}

      {#if addStep === 'store'}
        <h3>Select Store</h3>
        {#if newItem.hasMap}
          <button class="map-btn" on:click={useMapArea}>🗺️ Choose Area on Map Instead</button>
        {/if}
        <input type="text" placeholder="Search store by name, city, or number..." bind:value={storeSearch} class="search-input" />
        <div class="store-list">
          {#each filteredStores as store}
            <button class="store-btn" on:click={() => selectStore(store)}>
              <div class="store-top">
                <span class="store-name">{store.GroceryChain} - {store.City}, {store.State}</span>
                <span class="store-cycle">Cycle {store.Cycle || '?'}</span>
              </div>
              <span class="store-addr">{store.Address || ''}</span>
              <div class="store-bottom">
                <span class="store-num">{store.StoreName}</span>
                <span class="store-price">Single: ${store.SingleAd?.toLocaleString()} | Double: ${store.DoubleAd?.toLocaleString()}</span>
              </div>
              {#if store.Cycle}
                <span class="store-launch">Next launch: {getNextLaunch(store.Cycle)}</span>
              {/if}
            </button>
          {/each}
        </div>
        <button class="cancel-btn" on:click={() => { addStep = 'type'; storeSearch = ''; }}>Back</button>
      {/if}

      {#if addStep === 'plan'}
        <h3>Payment Plan</h3>
        <p class="plan-store">{newItem.storeName} ({newItem.storeNum})</p>
        <div class="plan-list">
          {#each PAYMENT_PLANS[newItem.type] || [] as plan}
            <button class="plan-btn" on:click={() => selectPlan(plan)}>
              <span class="plan-name">{plan.name}</span>
              <span class="plan-price">{plan.calc(newItem.store?.SingleAd || 0)}</span>
            </button>
          {/each}
        </div>
        <button class="cancel-btn" on:click={() => { addStep = 'store'; }}>Back</button>
      {/if}

      {#if addStep === 'confirm'}
        <h3>Confirm & Customize Price</h3>
        <div class="confirm-box">
          <p class="confirm-label">Product</p>
          <p class="confirm-value">{newItem.typeName}</p>
          <p class="confirm-label">Store</p>
          <p class="confirm-value">{newItem.storeName}</p>
          <p class="confirm-label">Plan</p>
          <p class="confirm-value">{newItem.plan}</p>
          <p class="confirm-label">Price</p>
          <input type="text" bind:value={newItem.priceText} class="price-input" />
        </div>
        <button class="add-confirm-btn" on:click={confirmPlan}>Add to Quote</button>
        <button class="cancel-btn" on:click={() => { addStep = 'plan'; }}>Back</button>
      {/if}

      {#if addStep === 'pins'}
        <h3>DigitalBoost — How Many Pins?</h3>
        <div class="pins-grid">
          {#each [1,2,3,4,5] as n}
            <button class="pin-btn" class:selected={newItem.pins === n} on:click={() => { newItem.pins = n; }}>
              {n} Pin{n > 1 ? 's' : ''}
              <span class="pin-price">${((n * 3600) + 395).toLocaleString()}</span>
            </button>
          {/each}
        </div>
        <button class="add-confirm-btn" on:click={addItem}>Add to Quote</button>
        <button class="cancel-btn" on:click={() => { addStep = 'type'; }}>Back</button>
      {/if}
    </div>
  {/if}

  {#if cartItems.length > 0}
    <div class="quote-items">
      {#each cartItems as item, i}
        <div class="quote-item">
          <div class="item-info">
            <h4>{item.emoji || ''} {item.name}</h4>
            {#if item.store}<p class="item-store">{item.store} ({item.storeNum}){#if item.storeCycle} — Cycle {item.storeCycle}{/if}</p>{/if}
            {#if item.storeAddress}<p class="item-addr">{item.storeAddress}</p>{/if}
            {#if item.storeCycle}<p class="item-launch">Next launch: {getNextLaunch(item.storeCycle)}</p>{/if}
            {#if item.plan}<p class="item-plan">{item.plan}</p>{/if}
            <div class="price-edit">
              <label>Price</label>
              <input type="text" value={item.price} on:change={(e) => updateItemPrice(i, e.target.value)} class="price-field" />
            </div>
          </div>
          <button class="remove-btn" on:click={() => removeItem(i)}>✕</button>
        </div>
      {/each}
    </div>

    <div class="quote-footer">
      <div class="footer-actions">
        <button class="export-btn" on:click={exportCSV}>📥 Export Quote</button>
        <button class="clear-btn" on:click={clearCart}>🗑️ Clear</button>
      </div>
    </div>
  {:else if !showAddProduct}
    <div class="empty">
      <p>No products in quote yet</p>
      <p class="hint">Tap "+ Add Product" to start building</p>
    </div>
  {/if}
</div>

<style>
  .quote-container { padding: 20px; max-width: 600px; margin: 0 auto; }
  h2 { margin: 0 0 6px; font-size: 24px; font-weight: 700; color: var(--text-primary); }
  h3 { margin: 0 0 12px; font-size: 18px; font-weight: 700; color: #333; }
  .subtitle { margin: 0 0 16px; color: var(--text-secondary); font-size: 14px; }

  .add-btn { width: 100%; padding: 14px; background: #CC0000; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: 700; cursor: pointer; margin-bottom: 16px; }
  .add-btn:hover { background: #990000; }

  .add-modal { background: #f5f5f5; border-radius: 12px; padding: 16px; margin-bottom: 16px; }

  .type-list { display: flex; flex-direction: column; gap: 8px; max-height: 400px; overflow-y: auto; }
  .type-btn { display: flex; align-items: center; gap: 10px; padding: 12px; background: white; border: 1px solid #e0e0e0; border-radius: 8px; cursor: pointer; text-align: left; }
  .type-btn:hover { border-color: #CC0000; }
  .type-emoji { font-size: 20px; }
  .type-name { flex: 1; font-weight: 600; font-size: 13px; color: #333; }
  .type-price { font-size: 12px; color: #CC0000; font-weight: 600; }

  .search-input { width: 100%; padding: 12px; border: 1px solid #e0e0e0; border-radius: 8px; font-size: 14px; margin-bottom: 12px; box-sizing: border-box; }

  .store-list { display: flex; flex-direction: column; gap: 8px; max-height: 300px; overflow-y: auto; }
  .store-btn { display: flex; flex-direction: column; padding: 10px; background: white; border: 1px solid #e0e0e0; border-radius: 8px; cursor: pointer; text-align: left; }
  .store-btn:hover { border-color: #CC0000; }
  .store-top { display: flex; justify-content: space-between; align-items: center; }
  .store-name { font-weight: 600; font-size: 14px; color: #333; }
  .store-cycle { font-size: 11px; font-weight: 600; color: #CC0000; background: #fff5f5; padding: 2px 8px; border-radius: 4px; }
  .store-addr { font-size: 12px; color: #888; margin-top: 2px; }
  .store-bottom { display: flex; justify-content: space-between; align-items: center; margin-top: 4px; }
  .store-num { font-size: 12px; color: #666; }
  .store-price { font-size: 11px; color: #CC0000; font-weight: 600; }

  .map-btn { width: 100%; padding: 14px; background: #1565c0; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; margin-bottom: 12px; }
  .map-btn:hover { background: #0d47a1; }

  .item-addr { margin: 0 0 2px; font-size: 11px; color: #999; }
  .item-launch { margin: 0 0 2px; font-size: 11px; color: #2e7d32; font-weight: 600; }
  .store-launch { font-size: 11px; color: #2e7d32; font-weight: 600; margin-top: 4px; }

  .plan-store { margin: 0 0 12px; font-size: 13px; color: #666; }
  .plan-list { display: flex; flex-direction: column; gap: 8px; }
  .plan-btn { display: flex; flex-direction: column; padding: 12px; background: white; border: 1px solid #e0e0e0; border-radius: 8px; cursor: pointer; text-align: left; }
  .plan-btn:hover { border-color: #CC0000; }
  .plan-name { font-weight: 600; font-size: 14px; color: #333; }
  .plan-price { font-size: 13px; color: #CC0000; margin-top: 4px; }

  .pins-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px; }
  .pin-btn { padding: 16px; background: white; border: 2px solid #e0e0e0; border-radius: 8px; cursor: pointer; text-align: center; font-weight: 700; font-size: 15px; color: #333; }
  .pin-btn.selected { border-color: #CC0000; background: #fff5f5; }
  .pin-price { display: block; font-size: 12px; color: #CC0000; margin-top: 4px; }

  .add-confirm-btn { width: 100%; padding: 14px; background: #CC0000; color: white; border: none; border-radius: 8px; font-size: 15px; font-weight: 700; cursor: pointer; margin-bottom: 8px; }

  .cancel-btn { width: 100%; padding: 10px; background: none; border: 1px solid #e0e0e0; border-radius: 8px; color: #666; font-size: 13px; cursor: pointer; margin-top: 8px; }

  .quote-items { display: flex; flex-direction: column; gap: 12px; margin-bottom: 16px; }
  .quote-item { display: flex; justify-content: space-between; align-items: flex-start; background: white; border: 1px solid #e0e0e0; border-radius: 12px; padding: 16px; }
  .item-info { flex: 1; }
  .quote-item h4 { margin: 0 0 4px; font-size: 15px; font-weight: 700; color: #333; }
  .item-store { margin: 0 0 2px; font-size: 12px; color: #666; }
  .item-plan { margin: 0 0 2px; font-size: 12px; color: #888; }
  .price-edit { margin-top: 8px; }
  .price-edit label { display: block; font-size: 11px; font-weight: 700; color: #666; margin-bottom: 4px; }
  .price-field { width: 100%; padding: 8px; border: 1px solid #CC0000; border-radius: 6px; font-size: 14px; font-weight: 700; color: #CC0000; box-sizing: border-box; }
  .price-field:focus { outline: none; border-color: #990000; }

  .confirm-box { background: white; border-radius: 8px; padding: 16px; margin-bottom: 16px; border: 1px solid #e0e0e0; }
  .confirm-label { font-size: 11px; font-weight: 700; color: #888; text-transform: uppercase; margin: 12px 0 4px; }
  .confirm-value { margin: 0; font-size: 14px; color: #333; font-weight: 600; }
  .price-input { width: 100%; padding: 10px; border: 1px solid #CC0000; border-radius: 6px; font-size: 16px; font-weight: 700; color: #CC0000; box-sizing: border-box; }

  .remove-btn { background: none; border: none; color: #ccc; font-size: 20px; cursor: pointer; }
  .remove-btn:hover { color: #CC0000; }

  .quote-footer { padding: 16px; background: #f5f5f5; border-radius: 12px; }
  .footer-actions { display: flex; gap: 8px; }
  .export-btn { flex: 1; padding: 12px; background: #CC0000; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; }
  .export-btn:hover { background: #990000; }
  .clear-btn { padding: 12px; background: white; border: 1px solid #e0e0e0; border-radius: 8px; color: #666; font-size: 14px; cursor: pointer; }

  .empty { text-align: center; padding: 40px 20px; color: #999; }
  .hint { font-size: 13px; color: #bbb; }
</style>
