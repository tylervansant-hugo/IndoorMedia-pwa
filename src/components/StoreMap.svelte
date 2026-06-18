<script>
  import { onMount, onDestroy } from 'svelte';
  import { sharedUserLocation } from '../lib/stores.js';
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

  // Rep location beacons
  let showBeacons = true;
  let repBeaconLayers = [];
  const REP_COLORS = [
    '#e63946', '#457b9d', '#2a9d8f', '#e9c46a', '#f4a261',
    '#264653', '#8338ec', '#ff006e', '#3a86ff', '#fb5607',
    '#606c38', '#023e8a', '#d62828', '#6a4c93', '#1d3557',
    '#f77f00', '#7209b7', '#4cc9f0', '#80b918', '#dc2f02'
  ];

  // Fullscreen state
  let isFullscreen = false;

  // Geolocation state
  let userLatLng = null;
  let userAccuracy = null;
  let userLocationLayers = [];
  let geoWatchId = null;

  // Popup timing for mobile fix
  let lastPopupOpenTime = 0;

  function toggleFullscreen() {
    isFullscreen = !isFullscreen;
    // Let Svelte update the DOM, then invalidate map size
    setTimeout(() => {
      if (map) map.invalidateSize();
    }, 50);
  }

  function handleEscKey(e) {
    if (e.key === 'Escape' && isFullscreen) {
      isFullscreen = false;
      setTimeout(() => {
        if (map) map.invalidateSize();
      }, 50);
    }
  }

  function centerOnUserLocation() {
    if (userLatLng && map) {
      map.setView(userLatLng, 14);
    }
  }

  // --- Map location search (address / city / ZIP / POI / store number) ---
  let mapSearchTerm = '';
  let mapSearchLoading = false;
  let mapSearchError = '';
  let searchMarker = null;

  function clearSearchMarker() {
    if (searchMarker && map) {
      map.removeLayer(searchMarker);
      searchMarker = null;
    }
  }

  function flyToLocation(lat, lng, label, zoom = 14) {
    if (!map) return;
    clearSearchMarker();
    searchMarker = L.marker([lat, lng], {
      icon: L.divIcon({
        className: 'map-search-pin',
        html: '<div class="search-pin-inner">📍</div>',
        iconSize: [32, 32],
        iconAnchor: [16, 32],
      }),
    }).addTo(map);
    if (label) {
      searchMarker.bindPopup(`<div class="store-map-popup"><strong>${label}</strong></div>`).openPopup();
    }
    map.setView([lat, lng], zoom, { animate: true });
  }

  async function runMapSearch() {
    const term = (mapSearchTerm || '').trim();
    if (!term) return;
    mapSearchError = '';

    // 1) Try matching a store number / store name directly (instant, local)
    const upper = term.toUpperCase();
    const matchStore = allStores.find(s =>
      (s.StoreName || '').toUpperCase() === upper ||
      (s.StoreName || '').toUpperCase().replace(/\s+/g, '') === upper.replace(/\s+/g, '')
    ) || allStores.find(s => (s.StoreName || '').toUpperCase().includes(upper) && upper.length >= 4);
    if (matchStore && matchStore.Latitude && matchStore.Longitude) {
      flyToLocation(
        parseFloat(matchStore.Latitude),
        parseFloat(matchStore.Longitude),
        `${matchStore.StoreName} — ${matchStore.GroceryChain || ''}`,
        15
      );
      return;
    }

    // 2) Geocode anything else (address, city, ZIP, point of interest)
    mapSearchLoading = true;
    try {
      const q = encodeURIComponent(term);
      const res = await fetch(`https://nominatim.openstreetmap.org/search?q=${q}&format=json&limit=1&countrycodes=us`, {
        headers: { 'Accept': 'application/json' },
      });
      const data = await res.json();
      if (!data || data.length === 0) {
        mapSearchError = `No location found for “${term}”`;
        return;
      }
      const lat = parseFloat(data[0].lat);
      const lng = parseFloat(data[0].lon);
      const label = data[0].display_name ? data[0].display_name.split(',').slice(0, 3).join(', ') : term;
      // ZIP/city get a wider zoom; specific addresses zoom in tighter
      const isBroad = /^\d{5}$/.test(term) || data[0].type === 'city' || data[0].type === 'administrative';
      flyToLocation(lat, lng, label, isBroad ? 12 : 15);
    } catch (err) {
      mapSearchError = 'Search failed — check connection and try again.';
    } finally {
      mapSearchLoading = false;
    }
  }

  function clearMapSearch() {
    mapSearchTerm = '';
    mapSearchError = '';
    clearSearchMarker();
  }

  function updateUserLocationMarker() {
    if (!map) return;
    // Remove old location layers
    userLocationLayers.forEach(l => map.removeLayer(l));
    userLocationLayers = [];

    if (!userLatLng) return;

    // Accuracy circle
    const accuracyCircle = L.circle(userLatLng, {
      radius: userAccuracy || 50,
      fillColor: '#4285F4',
      fillOpacity: 0.12,
      color: '#4285F4',
      weight: 1,
      opacity: 0.3,
      interactive: false,
    }).addTo(map);

    // Blue pulsing dot
    const blueDot = L.circleMarker(userLatLng, {
      radius: 9,
      fillColor: '#4285F4',
      color: '#fff',
      weight: 3,
      fillOpacity: 1,
      interactive: false,
      className: 'user-location-pulse',
    }).addTo(map);

    userLocationLayers.push(accuracyCircle, blueDot);
  }

  function initGeolocation() {
    if (!navigator.geolocation) return;

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        userLatLng = [pos.coords.latitude, pos.coords.longitude];
        userAccuracy = pos.coords.accuracy;
        updateUserLocationMarker();
      },
      () => { /* permission denied or error — silently ignore */ },
      { enableHighAccuracy: true, timeout: 10000 }
    );

    geoWatchId = navigator.geolocation.watchPosition(
      (pos) => {
        userLatLng = [pos.coords.latitude, pos.coords.longitude];
        userAccuracy = pos.coords.accuracy;
        updateUserLocationMarker();
      },
      () => {},
      { enableHighAccuracy: true, maximumAge: 15000 }
    );
  }

  // Chain name → prefix mapping (built from stores data)
  let chainToPrefix = {};

  function buildChainPrefixMap(stores) {
    const map = {};
    stores.forEach(s => {
      const name = s.StoreName || '';
      const chain = s.GroceryChain || '';
      const prefix = name.split(/\d/)[0]; // e.g. "SAF" from "SAF07Z-0424"
      if (prefix && chain && !map[chain]) {
        map[chain] = prefix;
      }
    });
    return map;
  }

  function buildContractMap(contracts) {
    // Key by "PREFIX + storeNumber" to avoid cross-chain collisions
    // e.g. store_name="Safeway" + store_number="0424" → key "SAF-0424"
    const map = {};
    contracts.forEach(c => {
      const sn = (c.store_number || '').replace(/^0+/, '');
      if (!sn) return;
      const chainName = c.store_name || '';
      const prefix = chainToPrefix[chainName] || '';
      // Store with chain-qualified key
      const qualifiedKey = prefix ? `${prefix}-${sn}` : sn;
      if (!map[qualifiedKey]) map[qualifiedKey] = [];
      map[qualifiedKey].push(c);
      // Also keep a bare number fallback for stores without chain match
      if (!map[sn]) map[sn] = [];
      map[sn].push(c);
    });
    return map;
  }

  function getStoreKey(storeName) {
    // "SAF07Z-0424" → prefix "SAF", number "0424" → "SAF-0424"
    if (!storeName) return '';
    const parts = storeName.split('-');
    if (parts.length < 2) return '';
    const prefix = parts[0].replace(/\d+[A-Z]*$/, ''); // "SAF07Z" → "SAF"
    const num = parts[1].replace(/^0+/, '');
    return `${prefix}-${num}`;
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
      // Only show stores where this rep has contracts
      stores = stores.filter(s => storeHasContractForRep(s.StoreName, selectedRep));
    }

    return stores;
  }

  function storeHasContractForRep(storeName, rep) {
    const key = getStoreKey(storeName);
    const contracts = contractsByStore[key] || [];
    if (!rep) return contracts.length > 0;
    return contracts.some(c => c.sales_rep === rep);
  }

  function getStoreContracts(storeName) {
    const key = getStoreKey(storeName);
    return contractsByStore[key] || [];
  }

  function updateMap() {
    if (!map || !markerClusterGroup) return;

    markerClusterGroup.clearLayers();

    const filtered = getFilteredStores();
    let withContracts = 0;

    filtered.forEach(store => {
      if (!store.latitude || !store.longitude) return;

      const hasContract = selectedRep
        ? storeHasContractForRep(store.StoreName, selectedRep)
        : storeHasContractForRep(store.StoreName, '');

      if (hasContract) withContracts++;

      // Purple for rep-filtered stores, green for contracted, red for open
      const isRepFiltered = !!selectedRep;
      const color = isRepFiltered ? '#8b5cf6' : (hasContract ? '#22c55e' : '#ef4444');
      const borderColor = isRepFiltered ? '#5b21b6' : (hasContract ? '#166534' : '#991b1b');
      const fillOpacity = hasContract ? 0.9 : 0.6;

      const marker = L.circleMarker([store.latitude, store.longitude], {
        radius: 10,
        fillColor: color,
        color: borderColor,
        weight: 1.5,
        fillOpacity: fillOpacity,
        interactive: true,
        bubblingMouseEvents: false,
      });

      // Build popup
      const contracts = getStoreContracts(store.StoreName);
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

      // Action buttons — Prospect & Rates
      const safeStoreName = store.StoreName.replace(/'/g, "\\'");
      const navAddr = encodeURIComponent(`${store.Address || ''}, ${store.City || ''}, ${store.State || ''} ${store.PostalCode || ''}`);
      popupHtml += `
        <div class="popup-actions">
          <button onclick="document.dispatchEvent(new CustomEvent('map-action', {detail: {action: 'prospect', store: '${safeStoreName}'}}))"
            class="popup-action-btn popup-action-prospect">🎯 Prospect</button>
          <button onclick="document.dispatchEvent(new CustomEvent('map-action', {detail: {action: 'rates', store: '${safeStoreName}'}}))"
            class="popup-action-btn popup-action-rates">📊 Rates</button>
        </div>
        <a href="https://maps.apple.com/?daddr=${navAddr}" target="_blank" class="popup-nav-btn">🗺️ Navigate to Store</a>
      `;
      popupHtml += `</div>`;
      marker.bindPopup(popupHtml, {
        maxWidth: 300,
        minWidth: 250,
        className: 'store-map-popup',
        autoPan: true,
        autoClose: true,      // Close when another popup opens
        closeOnClick: false,   // Don't close on map click
      });

      markerClusterGroup.addLayer(marker);
    });

    showingCount = filtered.filter(s => s.latitude && s.longitude).length;
    contractCount = withContracts;
  }

  async function updateBeacons() {
    if (!map) return;
    // Remove old beacons
    repBeaconLayers.forEach(l => map.removeLayer(l));
    repBeaconLayers = [];

    if (!showBeacons) return;

    try {
      // Try to load from seed data first, fall back to localStorage
      let beaconData = JSON.parse(localStorage.getItem('repLastLocations') || '{}');
      
      // If no localStorage data, try to load seed beacons from JSON
      if (Object.keys(beaconData).length === 0) {
        try {
          const seedRes = await fetch(import.meta.env.BASE_URL + 'data/rep_location_beacons.json?t=' + Date.now());
          if (seedRes.ok) {
            const seedData = await seedRes.json();
            // Convert seed format to localStorage format
            seedData.beacons.forEach(beacon => {
              beaconData[beacon.rep_name] = {
                lat: beacon.latitude,
                lng: beacon.longitude,
                timestamp: beacon.timestamp
              };
            });
          }
        } catch (e) { /* seed data not available yet */ }
      }

      const repNames = Object.keys(beaconData);
      if (repNames.length === 0) return;

      repNames.forEach((repName, idx) => {
        const loc = beaconData[repName];
        if (!loc || !loc.lat || !loc.lng) return;

        // Skip if filtering by rep and this isn't the selected rep
        if (selectedRep && repName !== selectedRep) return;

        const color = REP_COLORS[idx % REP_COLORS.length];
        const timeSince = loc.timestamp ? getTimeSince(loc.timestamp) : 'Unknown';

        // Pulsing beacon — outer ring
        const outerRing = L.circleMarker([loc.lat, loc.lng], {
          radius: 18,
          fillColor: color,
          color: color,
          weight: 2,
          fillOpacity: 0.15,
          className: 'beacon-pulse'
        }).addTo(map);

        // Inner dot
        const innerDot = L.circleMarker([loc.lat, loc.lng], {
          radius: 8,
          fillColor: color,
          color: '#fff',
          weight: 2.5,
          fillOpacity: 1,
        }).addTo(map);

        innerDot.bindPopup(`
          <div class="store-popup">
            <div class="popup-header" style="color:${color}">📍 ${repName}</div>
            <div class="popup-detail">Last "Near Me" search</div>
            <div class="popup-detail">${timeSince}</div>
            <div class="popup-detail" style="font-size:11px;color:#999;">${loc.lat.toFixed(4)}, ${loc.lng.toFixed(4)}</div>
          </div>
        `, { maxWidth: 250, className: 'store-map-popup' });

        repBeaconLayers.push(outerRing, innerDot);
      });
    } catch (e) { /* ignore */ }
  }

  function getTimeSince(timestamp) {
    const diff = Date.now() - new Date(timestamp).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  }

  function handlePrint() {
    window.print();
  }

  onMount(async () => {
    // Listen for ESC key to exit fullscreen
    window.addEventListener('keydown', handleEscKey);

    try {
      const [storesRes, contractsRes] = await Promise.all([
        fetch(import.meta.env.BASE_URL + 'data/stores.json?t=' + Date.now()),
        fetch(import.meta.env.BASE_URL + 'data/contracts.json?t=' + Date.now()),
      ]);

      allStores = await storesRes.json();
      const contractsData = await contractsRes.json();
      allContracts = contractsData.contracts || contractsData;
      chainToPrefix = buildChainPrefixMap(allStores);
      contractsByStore = buildContractMap(allContracts);
      totalCount = allStores.length;

      // Build filter options
      uniqueReps = [...new Set(allContracts.map(c => c.sales_rep).filter(Boolean))].sort();
      uniqueZones = [...new Set(allStores.map(s => s.ZoneName).filter(Boolean))].sort();
      uniqueCycles = [...new Set(allStores.map(s => s.Cycle).filter(Boolean))].sort();
      uniqueChains = [...new Set(allStores.map(s => s.GroceryChain).filter(Boolean))].sort();

      // Init map — closeOnClick: false prevents popups from vanishing on mobile
      map = L.map(mapContainer, {
        center: [45.5, -122.5],
        zoom: 7,
        zoomControl: true,
        closePopupOnClick: false,
        scrollWheelZoom: false,   // Disable scroll-to-zoom (trackpad two-finger scroll)
        touchZoom: true,          // Keep pinch-to-zoom on touch devices
      });

      // Popups close only via X button or by opening another popup
      // No map-click-to-close — prevents accidental dismissal on mobile

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
      updateBeacons();

      // Use shared location from Rates/Prospects if available, otherwise init geolocation
      const sharedLoc = $sharedUserLocation;
      if (sharedLoc && sharedLoc.lat && sharedLoc.lng) {
        userLatLng = [sharedLoc.lat, sharedLoc.lng];
        map.setView(userLatLng, 12);
        showUserLocation();
      }
      initGeolocation();
    } catch (err) {
      console.error('StoreMap init error:', err);
    }
  });

  onDestroy(() => {
    window.removeEventListener('keydown', handleEscKey);
    if (geoWatchId !== null) {
      navigator.geolocation.clearWatch(geoWatchId);
      geoWatchId = null;
    }
    if (map) {
      map.remove();
      map = null;
    }
  });

  // Reactively update map when filters change
  $: if (map) {
    selectedRep, selectedZone, selectedCycle, selectedChain, showBeacons;
    updateMap();
    updateBeacons();
  }
</script>

<div class="store-map-wrapper" class:fullscreen={isFullscreen}>
  {#if !isFullscreen}
    <!-- Normal mode: full filter bar -->
    <div class="filter-bar no-print">
      <div class="map-search-row">
        <span class="map-search-icon">🔍</span>
        <input
          type="text"
          class="map-search-input"
          bind:value={mapSearchTerm}
          on:keydown={(e) => e.key === 'Enter' && runMapSearch()}
          placeholder="Search address, city, ZIP, place, or store #…"
        />
        {#if mapSearchTerm}
          <button class="map-search-clear" on:click={clearMapSearch} title="Clear">✕</button>
        {/if}
        <button class="map-search-go" on:click={runMapSearch} disabled={mapSearchLoading || !mapSearchTerm.trim()}>
          {mapSearchLoading ? '⏳' : 'Go'}
        </button>
      </div>
      {#if mapSearchError}<div class="map-search-error">{mapSearchError}</div>{/if}
      <div class="filter-grid">
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
      </div>

      <div class="map-toolbar">
        <button class="tb-btn" on:click={handlePrint} title="Print">🖨️</button>
        <button class="tb-btn" on:click={toggleFullscreen} title="Fullscreen">⛶</button>
        <button class="tb-btn" on:click={centerOnUserLocation} title="My location" disabled={!userLatLng}>📍</button>
        <label class="tb-toggle">
          <input type="checkbox" bind:checked={showBeacons} />
          📍 Reps
        </label>
        <span class="tb-status">
          <strong>{showingCount}</strong>/{totalCount} stores · <strong>{contractCount}</strong> contracted
        </span>
      </div>
    </div>
  {:else}
    <!-- Fullscreen mode: compact toolbar -->
    <div class="fs-toolbar">
      <button class="fs-btn fs-exit" on:click={toggleFullscreen}>✕</button>
      <input
        type="text"
        class="fs-search-input"
        bind:value={mapSearchTerm}
        on:keydown={(e) => e.key === 'Enter' && runMapSearch()}
        placeholder="Search address, city, ZIP, store #…"
      />
      <button class="fs-btn" on:click={runMapSearch} disabled={mapSearchLoading || !mapSearchTerm.trim()}>{mapSearchLoading ? '⏳' : '🔍'}</button>
      <button class="fs-btn" on:click={centerOnUserLocation} disabled={!userLatLng}>📍</button>
      <select bind:value={selectedZone} class="fs-select">
        <option value="">Zone</option>
        {#each uniqueZones as zone}<option value={zone}>{zone}</option>{/each}
      </select>
      <select bind:value={selectedCycle} class="fs-select">
        <option value="">Cycle</option>
        {#each uniqueCycles as cycle}<option value={cycle}>{cycle}</option>{/each}
      </select>
      <select bind:value={selectedRep} class="fs-select">
        <option value="">Rep</option>
        {#each uniqueReps as rep}<option value={rep}>{rep.split(' ')[0]}</option>{/each}
      </select>
      <div class="fs-status">{showingCount} stores</div>
    </div>
  {/if}

  <div class="map-container" bind:this={mapContainer}></div>
</div>

<style>
  .store-map-wrapper {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 180px);
    min-height: 400px;
    position: relative;
  }

  /* Map location search */
  .map-search-row {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 8px;
    background: var(--input-bg, #fff);
    border: 1px solid var(--border-color, #ddd);
    border-radius: 10px;
    padding: 4px 8px;
  }
  .map-search-icon { font-size: 14px; opacity: 0.7; }
  .map-search-input {
    flex: 1;
    border: none;
    outline: none;
    background: transparent;
    font-size: 15px;
    padding: 8px 2px;
    color: var(--text-primary, #222);
    min-width: 0;
  }
  .map-search-clear {
    border: none;
    background: transparent;
    color: #999;
    font-size: 16px;
    cursor: pointer;
    padding: 2px 6px;
  }
  .map-search-go {
    border: none;
    background: #CC0000;
    color: #fff;
    font-weight: 700;
    font-size: 14px;
    border-radius: 8px;
    padding: 8px 16px;
    cursor: pointer;
  }
  .map-search-go:disabled { opacity: 0.5; cursor: default; }
  .map-search-error {
    color: #c33;
    font-size: 13px;
    margin: -4px 0 8px;
    padding-left: 4px;
  }
  .fs-search-input {
    flex: 1;
    min-width: 0;
    border: 1px solid rgba(255,255,255,0.4);
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 14px;
    background: rgba(255,255,255,0.95);
    color: #222;
  }
  :global(.map-search-pin .search-pin-inner) {
    font-size: 28px;
    line-height: 1;
    filter: drop-shadow(0 2px 3px rgba(0,0,0,0.4));
  }

  .store-map-wrapper.fullscreen {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 9999;
    height: 100vh !important;
    height: 100dvh !important;
    border-radius: 0;
    background: white;
    padding: 0;
  }

  /* Fullscreen compact toolbar */
  .fs-toolbar {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 10px;
    padding-top: calc(8px + env(safe-area-inset-top, 0px));
    background: rgba(255,255,255,0.95);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border-bottom: 1px solid #e0e0e0;
    z-index: 10001;
    flex-shrink: 0;
  }
  .fs-btn {
    width: 36px; height: 36px; border-radius: 8px; border: 1px solid #ddd;
    background: #fff; font-size: 16px; cursor: pointer; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
  }
  .fs-btn:active { background: #eee; }
  .fs-exit { background: #CC0000; color: white; border-color: #CC0000; font-weight: 700; }
  .fs-exit:active { background: #990000; }
  .fs-select {
    flex: 1; min-width: 0; padding: 6px 4px; border: 1px solid #ddd; border-radius: 8px;
    background: #fff; font-size: 12px; font-weight: 600; appearance: auto;
  }
  .fs-status {
    font-size: 11px; color: #666; white-space: nowrap; flex-shrink: 0;
  }

  .filter-bar {
    background: var(--bg-secondary, #f9f9f9);
    border: 1px solid var(--border-color, #e0e0e0);
    border-radius: 10px;
    padding: 10px 12px;
    margin-bottom: 8px;
    z-index: 10000;
    position: relative;
  }



  /* Filters + toolbar in one compact row each */
  .filter-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px;
    margin-bottom: 6px;
  }

  .filter-select {
    flex: 1;
    min-width: 0;
    padding: 6px 4px;
    border: 1px solid var(--border-color, #ddd);
    border-radius: 8px;
    background: var(--input-bg, #fff);
    color: var(--text-primary, #333);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    appearance: auto;
    box-sizing: border-box;
  }

  .filter-select:focus {
    outline: none;
    border-color: #CC0000;
  }

  /* Toolbar: buttons + status all in one horizontal line */
  .map-toolbar {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .tb-btn {
    width: 32px; height: 32px; border-radius: 8px;
    border: 1px solid var(--border-color, #ddd);
    background: var(--card-bg, #fff);
    cursor: pointer; font-size: 14px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    padding: 0;
  }
  .tb-btn:active { background: var(--hover-bg, #eee); }
  .tb-btn:disabled { opacity: 0.4; cursor: default; }

  .tb-toggle {
    display: flex; align-items: center; gap: 3px;
    font-size: 11px; font-weight: 600; cursor: pointer;
    padding: 4px 6px; border-radius: 6px;
    background: var(--bg-primary, #fff);
    border: 1px solid var(--border-color, #ddd);
    white-space: nowrap; flex-shrink: 0;
  }
  .tb-toggle input { margin: 0; width: 14px; height: 14px; }

  .tb-status {
    font-size: 10px; color: var(--text-secondary, #666);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    flex: 1; text-align: right;
  }
  .tb-status strong { color: var(--text-primary, #333); }

  :global(.beacon-pulse) {
    animation: pulse-beacon 2s ease-in-out infinite;
  }
  @keyframes pulse-beacon {
    0%, 100% { opacity: 0.15; }
    50% { opacity: 0.4; }
  }

  /* User location pulse */
  :global(.user-location-pulse) {
    animation: pulse-user-loc 1.5s ease-in-out infinite;
  }
  @keyframes pulse-user-loc {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
  }

  .map-container {
    flex: 1;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid var(--border-color, #e0e0e0);
    min-height: 300px;
  }

  .fullscreen .map-container {
    border-radius: 0;
    border: none;
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

  :global(.popup-actions) {
    display: flex; gap: 8px; margin-top: 10px; padding-top: 10px; border-top: 1px solid #e0e0e0;
  }
  :global(.popup-action-btn) {
    flex: 1; padding: 8px 6px; border: none; border-radius: 8px;
    font-size: 13px; font-weight: 700; cursor: pointer; text-align: center;
  }
  :global(.popup-action-prospect) { background: #CC0000; color: white; }
  :global(.popup-action-prospect:active) { background: #990000; }
  :global(.popup-action-rates) { background: #1a73e8; color: white; }
  :global(.popup-action-rates:active) { background: #0d47a1; }
  :global(.popup-nav-btn) {
    display: block; text-align: center; margin-top: 8px; padding: 8px;
    background: #34a853; color: white; border-radius: 8px; font-size: 13px;
    font-weight: 700; text-decoration: none; cursor: pointer;
  }
  :global(.popup-nav-btn:active) { background: #2d8a46; }

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
