<script>
  let stores = [];
  let selectedStore = null;
  let searchQuery = '';

  async function loadStores() {
    try {
      const res = await fetch(import.meta.env.BASE_URL + 'data/stores.json?t=' + Date.now());
      stores = await res.json();
    } catch (err) {
      console.error('Failed to load stores:', err);
    }
  }

  $: filteredStores = selectedStore 
    ? stores.filter(s => s.StoreName === selectedStore)
    : [];

  import { onMount } from 'svelte';
  onMount(loadStores);
</script>

<div class="inventory-container">
  <h2>📦 Inventory Management</h2>
  <p class="subtitle">Check supply levels and reorder status</p>

  <div class="search-section">
    <input 
      type="text" 
      placeholder="Search stores..." 
      bind:value={searchQuery}
      class="search-input"
    />
  </div>

  <div class="stores-list">
    {#each stores as store}
      <button class="store-item" on:click={() => selectedStore = store.StoreName}>
        <div class="store-name">{store.GroceryChain} - {store.City}</div>
        <div class="store-num">{store.StoreName}</div>
      </button>
    {/each}
  </div>

  {#if selectedStore && filteredStores.length > 0}
    <div class="inventory-detail">
      <h3>Store Inventory</h3>
      <div class="inventory-grid">
        <div class="inv-card">
          <div class="inv-label">Last Shipment</div>
          <div class="inv-value">—</div>
        </div>
        <div class="inv-card">
          <div class="inv-label">Current Stock</div>
          <div class="inv-value">—</div>
        </div>
        <div class="inv-card">
          <div class="inv-label">Days Until Reorder</div>
          <div class="inv-value">—</div>
        </div>
        <div class="inv-card">
          <div class="inv-label">Status</div>
          <div class="inv-value">✅ Healthy</div>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .inventory-container {
    max-width: 1000px;
    margin: 0 auto;
  }

  h2 {
    margin: 0 0 8px;
    font-size: 24px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .subtitle {
    margin: 0 0 24px;
    color: var(--text-secondary);
    font-size: 14px;
  }

  .search-section {
    margin-bottom: 24px;
  }

  .search-input {
    width: 100%;
    padding: 12px 14px;
    border: 2px solid var(--border-color);
    border-radius: 10px;
    font-size: 14px;
    background: var(--input-bg);
    color: var(--text-primary);
    transition: border-color 0.2s;
  }

  .search-input:focus {
    outline: none;
    border-color: #CC0000;
  }

  .stores-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
  }

  .store-item {
    background: var(--card-bg);
    border: 2px solid var(--border-color);
    border-radius: 10px;
    padding: 16px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .store-item:hover {
    border-color: #CC0000;
    box-shadow: 0 4px 12px var(--card-shadow);
  }

  .store-name {
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 4px;
  }

  .store-num {
    font-size: 12px;
    color: var(--text-secondary);
  }

  .inventory-detail {
    background: var(--card-bg);
    border: 2px solid var(--border-color);
    border-radius: 12px;
    padding: 24px;
  }

  .inventory-detail h3 {
    margin: 0 0 16px;
    font-size: 18px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .inventory-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
  }

  .inv-card {
    background: var(--bg-secondary);
    border-radius: 8px;
    padding: 16px;
    text-align: center;
  }

  .inv-label {
    font-size: 12px;
    color: var(--text-secondary);
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .inv-value {
    font-size: 20px;
    font-weight: 700;
    color: var(--text-primary);
  }
</style>
