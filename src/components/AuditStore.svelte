<script>
  import { onMount } from 'svelte';
  
  let allStores = [];
  let searchTerm = '';
  let filteredStores = [];
  let selectedStore = null;
  let inventoryCount = '';
  let lastShipment = '';
  let auditNotes = '';
  let auditSubmitted = false;
  
  onMount(async () => {
    try {
      const res = await fetch(import.meta.env.BASE_URL + 'data/stores.json');
      allStores = await res.json();
    } catch (err) {
      console.error('Failed to load stores:', err);
    }
  });
  
  function searchStores() {
    if (!searchTerm.trim()) {
      filteredStores = [];
      return;
    }
    const term = searchTerm.toLowerCase();
    filteredStores = allStores.filter(s =>
      s.StoreName?.toLowerCase().includes(term) ||
      s.City?.toLowerCase().includes(term) ||
      s.GroceryChain?.toLowerCase().includes(term)
    ).slice(0, 10);
  }
  
  function selectStore(store) {
    selectedStore = store;
    filteredStores = [];
    searchTerm = `${store.GroceryChain} - ${store.City} (${store.StoreName})`;
  }
  
  function calcRunout() {
    if (!inventoryCount || inventoryCount <= 0) return null;
    const casesPerWeek = (selectedStore?.['Case Count'] || 10) / 4;
    const weeksLeft = Math.floor(inventoryCount / casesPerWeek);
    return { weeksLeft, daysLeft: weeksLeft * 7 };
  }
  
  function submitAudit() {
    const runout = calcRunout();
    const audit = {
      store: selectedStore?.StoreName,
      chain: selectedStore?.GroceryChain,
      city: selectedStore?.City,
      inventory: inventoryCount,
      lastShipment,
      notes: auditNotes,
      runout: runout?.daysLeft,
      timestamp: new Date().toISOString()
    };
    
    // Save to localStorage
    const audits = JSON.parse(localStorage.getItem('audits') || '[]');
    audits.push(audit);
    localStorage.setItem('audits', JSON.stringify(audits));
    
    auditSubmitted = true;
    setTimeout(() => { auditSubmitted = false; }, 3000);
  }
  
  $: runout = selectedStore ? calcRunout() : null;
</script>

<div class="audit-container">
  <h2>🏪 Audit Store</h2>
  <p class="subtitle">Track inventory and delivery status</p>
  
  <div class="form-section">
    <label>Select Store</label>
    <input
      type="text"
      placeholder="Search by store name or city..."
      bind:value={searchTerm}
      on:input={searchStores}
    />
    
    {#if filteredStores.length > 0}
      <div class="store-dropdown">
        {#each filteredStores as store}
          <button class="store-option" on:click={() => selectStore(store)}>
            {store.GroceryChain} — {store.City}, {store.State} ({store.StoreName})
          </button>
        {/each}
      </div>
    {/if}
  </div>
  
  {#if selectedStore}
    <div class="store-detail">
      <h3>{selectedStore.GroceryChain} — {selectedStore.City}</h3>
      <p>{selectedStore.Address}, {selectedStore.State} {selectedStore.PostalCode}</p>
      <p>Store #: {selectedStore.StoreName} | Cycle: {selectedStore.Cycle} | Cases: {selectedStore['Case Count']}</p>
    </div>
    
    <div class="form-section">
      <label>Current Inventory (cases on shelf)</label>
      <input type="number" placeholder="e.g., 12" bind:value={inventoryCount} min="0" />
    </div>
    
    <div class="form-section">
      <label>Last Shipment Date</label>
      <input type="date" bind:value={lastShipment} />
    </div>
    
    <div class="form-section">
      <label>Notes</label>
      <textarea placeholder="Any observations..." bind:value={auditNotes} rows="3"></textarea>
    </div>
    
    {#if runout}
      <div class="runout-card" class:critical={runout.daysLeft < 14} class:warning={runout.daysLeft >= 14 && runout.daysLeft < 30} class:ok={runout.daysLeft >= 30}>
        <div class="runout-icon">
          {#if runout.daysLeft < 14}🚨
          {:else if runout.daysLeft < 30}⚠️
          {:else}✅{/if}
        </div>
        <div class="runout-info">
          <strong>{runout.daysLeft} days</strong> until estimated runout
          <br><span>({runout.weeksLeft} weeks at current pace)</span>
        </div>
      </div>
    {/if}
    
    <button class="submit-btn" on:click={submitAudit} disabled={!inventoryCount}>
      {auditSubmitted ? '✅ Audit Saved!' : '📋 Submit Audit'}
    </button>
  {/if}
</div>

<style>
  .audit-container { max-width: 600px; margin: 0 auto; }
  h2 { margin: 0; font-size: 20px; }
  h3 { margin: 0 0 4px 0; font-size: 16px; }
  .subtitle { color: #666; font-size: 14px; margin: 4px 0 20px 0; }
  
  .form-section { margin-bottom: 16px; position: relative; }
  
  label {
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: #333;
    margin-bottom: 6px;
  }
  
  input, textarea {
    width: 100%;
    padding: 12px 14px;
    border: 2px solid #ddd;
    border-radius: 8px;
    font-size: 15px;
    font-family: inherit;
  }
  
  input:focus, textarea:focus {
    outline: none;
    border-color: #CC0000;
  }
  
  .store-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: white;
    border: 2px solid #CC0000;
    border-top: none;
    border-radius: 0 0 8px 8px;
    z-index: 10;
    max-height: 200px;
    overflow-y: auto;
  }
  
  .store-option {
    display: block;
    width: 100%;
    padding: 10px 14px;
    background: none;
    border: none;
    border-bottom: 1px solid #f0f0f0;
    text-align: left;
    font-size: 14px;
    cursor: pointer;
  }
  
  .store-option:hover { background: #fff5f5; }
  
  .store-detail {
    background: white;
    padding: 14px;
    border-radius: 8px;
    margin-bottom: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }
  
  .store-detail p { margin: 4px 0; font-size: 13px; color: #666; }
  
  .runout-card {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px;
    border-radius: 8px;
    margin-bottom: 16px;
  }
  
  .runout-card.critical { background: #fce4ec; border: 2px solid #c62828; }
  .runout-card.warning { background: #fff3e0; border: 2px solid #e65100; }
  .runout-card.ok { background: #e8f5e9; border: 2px solid #2e7d32; }
  
  .runout-icon { font-size: 28px; }
  .runout-info { font-size: 14px; color: #333; }
  .runout-info span { font-size: 12px; color: #666; }
  
  .submit-btn {
    width: 100%;
    padding: 14px;
    background: #CC0000;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 700;
    cursor: pointer;
  }
  
  .submit-btn:hover { background: #990000; }
  .submit-btn:disabled { background: #ccc; cursor: not-allowed; }
</style>
