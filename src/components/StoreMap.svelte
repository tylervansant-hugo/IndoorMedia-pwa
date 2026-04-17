<script>
  import { onMount, onDestroy } from 'svelte';
  import L from 'leaflet';
  import 'leaflet/dist/leaflet.css';
  import 'leaflet.markercluster';
  import 'leaflet.markercluster/dist/MarkerCluster.css';
  import 'leaflet.markercluster/dist/MarkerCluster.Default.css';

  let map;
  let mapContainer;
  let markerClusterGroup;
  let allStores = [];
  let allContracts = [];
  let contractsByStore = {};

  // Filter state
  let selectedRep = '';
  let selectedZone = '';
  let selectedCycle = '';
  let selectedChain = '';

  // Derived lists
  let uniqueReps = [];
  let uniqueZones = [];
  let uniqueCycles = [];
  let uniqueChains = [];

  // Counts
  let showingCount = 0;
  let totalCount = 0;
  let contractCount = 0;

  function extractStoreNumber(storeName) {
    if (!storeName) return '';
    const parts = storeName.split('-');
    return parts.length > 1 ? parts[1] : '';
  }

  function buildContractMap(contracts) {
    const map = {};
    contracts.forEach(c => {
      const sn = (c.store_number || '').replace(/^0+/, '');
      if (!sn) return;
      if (!map[sn]) map[sn] = [];
      map[sn].push(c);
    });
    return map;
  }

  function getFilteredStores() {
    let stores = allStores;

    if (selectedZone) {
      stores = stores.filter(s => s.ZoneName === selectedZone);
    }
    if (selectedCycle) {
      stores = stores.filter(s => s.Cycle === selectedCycle);
    }
    if (selectedChain) {
      stores = stores.filter(s => s.GroceryChain === selectedChain);
    }
    if (selectedRep) {
      // Show all stores matching other filters, but only those with contracts from this rep get green
      // We still show all stores but the color logic handles rep filtering
    }

    return stores;
  }

  function storeHasContractForRep(storeNumber, rep) {
    const normalized = storeNumber.replace(/^0+/, '');
    const contracts = contractsByStore[normalized] || [];
    if (!rep) return contracts.length > 0;
    return contracts.some(c => c.sales_rep === rep);
  }

  function getStoreContracts(storeNumber) {
    const normalized = storeNumber.replace(/^0+/, '');
    return contractsByStore[normalized] || [];
  }

  function updateMap() {
    if (!map || !markerClusterGroup) return;

    markerClusterGroup.clearLayers();

    const filtered = getFilteredStores();
    let withContracts = 0;

    filtered.forEach(store => {
      if (!store.latitude || !store.longitude) return;

      const storeNum = extractStoreNumber(store.StoreName);
      const hasContract = selectedRep
        ? storeHasContractForRep(storeNum, selectedRep)
        : storeHasContractForRep(storeNum, '');

      if (hasContract) withContracts++;

      const color = hasContract ? '#22c55e' : '#ef4444';
      const fillOpacity = hasContract ? 0.9 : 0.6;

      const marker = L.circleMarker([store.latitude, store.longitude], {
        radius: 7,
        fillColor: color,
        color: hasContract ? '#166534' : '#991b1b',
        weight: 1.5,
        fillOpacity: fillOpacity,
      });

      // Build popup
      const contracts = getStoreContracts(storeNum);
      let popupHtml = `
        <div class="store-popup">
          <div class="popup-header">${store.StoreName}</div>
          <div class="popup-chain">${store.GroceryChain || ''}</div>
          <div class="popup-address">${store.Address || ''}<br>${store.City || ''}, ${store.State || ''} ${store.PostalCode || ''}</div>
          <div class="popup-details">
            <span><strong>Zone:</strong> ${store.ZoneName || ''}</span>
            <span><strong>Cycle:</strong> ${store.Cycle || ''}</span>
            <span><strong>Install Day:</strong> ${store.InstallDay || ''}</span>
          </div>
          <div class="popup-details">
            <span><strong>Single Ad:</strong> $${(store.SingleAd || 0).toLocaleString()}</span>
            <span><strong>Double Ad:</strong> $${(store.DoubleAd || 0).toLocaleString()}</span>
          </div>
          <div class="popup-cases"><strong>Case Count:</strong> ${store['Case Count'] || 0}</div>
      `;

      if (contracts.length > 0) {
        popupHtml += `<div class="popup-contracts"><strong>Contracts (${contracts.length}):</strong>`;
        contracts.forEach(c => {
          popupHtml += `
            <div class="popup-contract-item">
              <span class="contract-biz">${c.business_name || 'Unknown'}</span>
              <span class="contract-meta">${c.sales_rep || ''} · $${(c.total_amount || 0).toLocaleString()}</span>
            </div>
          `;
        });
        popupHtml += `</div>`;
      } else {
        popupHtml += `<div class="popup-open">🔴 No active contracts — Open for sales!</div>`;
      }

      popupHtml += `</div>`;
      marker.bindPopup(popupHtml, { maxWidth: 300, className: 'store-map-popup' });

      markerClusterGroup.addLayer(marker);
    });

    showingCount = filtered.filter(s => s.latitude && s.longitude).length;
    contractCount = withContracts;
  }

  function handlePrint() {
    window.print();
  }

  onMount(async () => {
    try {
      const [storesRes, contractsRes] = await Promise.all([
        fetch(import.meta.env.BASE_URL + 'data/stores.json'),
        fetch(import.meta.env.BASE_URL + 'data/contracts.json'),
      ]);

      allStores = await storesRes.json();
      const contractsData = await contractsRes.json();
      allContracts = contractsData.contracts || contractsData;
      contractsByStore = buildContractMap(allContracts);
      totalCount = allStores.length;

      // Build filter options
      uniqueReps = [...new Set(allContracts.map(c => c.sales_rep).filter(Boolean))].sort();
      uniqueZones = [...new Set(allStores.map(s => s.ZoneName).filter(Boolean))].sort();
      uniqueCycles = [...new Set(allStores.map(s => s.Cycle).filter(Boolean))].sort();
      uniqueChains = [...new Set(allStores.map(s => s.GroceryChain).filter(Boolean))].sort();

      // Init map
      map = L.map(mapContainer, {
        center: [45.5, -122.5],
        zoom: 7,
        zoomControl: true,
      });

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(map);

      markerClusterGroup = L.markerClusterGroup({
        chunkedLoading: true,
        maxClusterRadius: 50,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        iconCreateFunction: function(cluster) {
          const count = cluster.getChildCount();
          let size = 'small';
          let dim = 36;
          if (count > 100) { size = 'large'; dim = 50; }
          else if (count > 10) { size = 'medium'; dim = 42; }
          return L.divIcon({
            html: `<div class="cluster-icon cluster-${size}"><span>${count}</span></div>`,
            className: 'custom-cluster',
            iconSize: L.point(dim, dim),
          });
        }
      });
      map.addLayer(markerClusterGroup);

      updateMap();
    } catch (err) {
      console.error('StoreMap init error:', err);
    }
  });

  onDestroy(() => {
    if (map) {
      map.remove();
      map = null;
    }
  });

  // Reactively update map when filters change
  $: if (map) {
    selectedRep, selectedZone, selectedCycle, selectedChain;
    updateMap();
  }
</script>

<div class="store-map-wrapper">
  <div class="filter-bar no-print">
    <div class="filter-row">
      <select bind:value={selectedRep} class="filter-select">
        <option value="">All Reps</option>
        {#each uniqueReps as rep}
          <option value={rep}>{rep}</option>
        {/each}
      </select>

      <select bind:value={selectedZone} class="filter-select">
        <option value="">All Zones</option>
        {#each uniqueZones as zone}
          <option value={zone}>{zone}</option>
        {/each}
      </select>

      <select bind:value={selectedCycle} class="filter-select">
        <option value="">All Cycles</option>
        {#each uniqueCycles as cycle}
          <option value={cycle}>Cycle {cycle}</option>
        {/each}
      </select>

      <select bind:value={selectedChain} class="filter-select">
        <option value="">All Chains</option>
        {#each uniqueChains as chain}
          <option value={chain}>{chain}</option>
        {/each}
      </select>

      <button class="print-btn" on:click={handlePrint} title="Print map">🖨️</button>
    </div>

    <div class="filter-status">
      Showing <strong>{showingCount}</strong> of <strong>{totalCount}</strong> stores
      (<strong>{contractCount}</strong> with contracts)
    </div>
  </div>

  <div class="map-container" bind:this={mapContainer}></div>
</div>

<style>
  .store-map-wrapper {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 180px);
    min-height: 400px;
  }

  .filter-bar {
    background: var(--bg-secondary, #f9f9f9);
    border: 1px solid var(--border-color, #e0e0e0);
    border-radius: 10px;
    padding: 10px 12px;
    margin-bottom: 8px;
  }

  .filter-row {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
  }

  .filter-select {
    flex: 1;
    min-width: 120px;
    padding: 8px 10px;
    border: 1px solid var(--border-color, #ddd);
    border-radius: 8px;
    background: var(--input-bg, #fff);
    color: var(--text-primary, #333);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    appearance: auto;
  }

  .filter-select:focus {
    outline: none;
    border-color: #CC0000;
  }

  .print-btn {
    padding: 8px 12px;
    background: var(--card-bg, #fff);
    border: 1px solid var(--border-color, #ddd);
    border-radius: 8px;
    cursor: pointer;
    font-size: 16px;
    transition: background 0.2s;
  }

  .print-btn:hover {
    background: var(--hover-bg, #f0f0f0);
  }

  .filter-status {
    margin-top: 6px;
    font-size: 12px;
    color: var(--text-secondary, #666);
    text-align: center;
  }

  .filter-status strong {
    color: var(--text-primary, #333);
  }

  .map-container {
    flex: 1;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid var(--border-color, #e0e0e0);
    min-height: 300px;
  }

  /* Cluster icons */
  :global(.custom-cluster) {
    background: transparent !important;
  }

  :global(.cluster-icon) {
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    color: white;
    font-weight: 700;
    font-size: 13px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
  }

  :global(.cluster-small) {
    background: rgba(204, 0, 0, 0.75);
    width: 36px;
    height: 36px;
  }

  :global(.cluster-medium) {
    background: rgba(204, 0, 0, 0.85);
    width: 42px;
    height: 42px;
    font-size: 14px;
  }

  :global(.cluster-large) {
    background: rgba(204, 0, 0, 0.95);
    width: 50px;
    height: 50px;
    font-size: 15px;
  }

  /* Popup styles */
  :global(.store-map-popup .leaflet-popup-content-wrapper) {
    border-radius: 10px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  }

  :global(.store-map-popup .leaflet-popup-content) {
    margin: 0;
    padding: 0;
  }

  :global(.store-popup) {
    padding: 12px 14px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 13px;
    color: #333;
    min-width: 220px;
  }

  :global(.popup-header) {
    font-size: 16px;
    font-weight: 800;
    color: #1a1a1a;
    margin-bottom: 2px;
  }

  :global(.popup-chain) {
    font-size: 13px;
    font-weight: 600;
    color: #CC0000;
    margin-bottom: 6px;
  }

  :global(.popup-address) {
    font-size: 12px;
    color: #555;
    margin-bottom: 8px;
    line-height: 1.4;
  }

  :global(.popup-details) {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 6px;
    font-size: 12px;
    color: #444;
  }

  :global(.popup-cases) {
    font-size: 12px;
    color: #444;
    margin-bottom: 8px;
  }

  :global(.popup-contracts) {
    border-top: 1px solid #e0e0e0;
    padding-top: 8px;
    margin-top: 4px;
  }

  :global(.popup-contracts strong) {
    color: #166534;
    font-size: 12px;
  }

  :global(.popup-contract-item) {
    display: flex;
    flex-direction: column;
    padding: 4px 0;
    border-bottom: 1px solid #f0f0f0;
  }

  :global(.popup-contract-item:last-child) {
    border-bottom: none;
  }

  :global(.contract-biz) {
    font-weight: 600;
    font-size: 13px;
    color: #1a1a1a;
  }

  :global(.contract-meta) {
    font-size: 11px;
    color: #666;
  }

  :global(.popup-open) {
    margin-top: 8px;
    padding: 6px 8px;
    background: #FFF3E0;
    border-radius: 6px;
    font-size: 12px;
    color: #E65100;
    font-weight: 600;
    text-align: center;
  }

  /* Print styles */
  @media print {
    .no-print {
      display: none !important;
    }

    .store-map-wrapper {
      height: 100vh !important;
    }

    .map-container {
      height: 100% !important;
      border: none !important;
      border-radius: 0 !important;
    }
  }

  /* Mobile responsive */
  @media (max-width: 600px) {
    .filter-row {
      flex-direction: column;
    }

    .filter-select {
      min-width: 100%;
    }

    .store-map-wrapper {
      height: calc(100vh - 220px);
    }
  }
</style>
