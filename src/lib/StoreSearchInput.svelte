<script>
  import { createEventDispatcher } from 'svelte';

  export let stores = [];
  export let placeholder = 'Search by name, city, zip, chain, or store #...';
  export let maxResults = 20;
  export let showGeo = true;

  const dispatch = createEventDispatcher();

  let searchTerm = '';
  let addressSearch = '';
  let addressSearching = false;
  let filtered = [];
  let showDropdown = false;
  let geoMessage = '';

  $: {
    if (searchTerm.length >= 2) {
      const q = searchTerm.toLowerCase();
      filtered = stores.filter(s =>
        (s.StoreName && s.StoreName.toLowerCase().includes(q)) ||
        (s.GroceryChain && s.GroceryChain.toLowerCase().includes(q)) ||
        (s.City && s.City.toLowerCase().includes(q)) ||
        (s.Address && s.Address.toLowerCase().includes(q)) ||
        (s.State && s.State.toLowerCase().includes(q)) ||
        (s.PostalCode && s.PostalCode.includes(q))
      ).slice(0, maxResults);
      showDropdown = filtered.length > 0;
      dispatch('results', filtered);
    } else {
      filtered = [];
      showDropdown = false;
      dispatch('results', []);
    }
  }

  function selectStore(store) {
    dispatch('select', store);
    searchTerm = `${store.GroceryChain} — ${store.City}, ${store.State} (${store.StoreName})`;
    showDropdown = false;
    filtered = [];
  }

  /**
   * Haversine distance in miles
   */
  function calcDistance(lat1, lon1, lat2, lon2) {
    const R = 3959;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  /**
   * Detect stores with "junk" coordinates (many stores sharing the exact same lat/lng = state centroid).
   * Build a Set of bad coordinate pairs on first call.
   */
  let _badCoords = null;
  function getBadCoords() {
    if (_badCoords) return _badCoords;
    const counts = {};
    for (const s of stores) {
      if (!s.latitude || !s.longitude) continue;
      const key = `${s.latitude.toFixed(4)},${s.longitude.toFixed(4)}`;
      counts[key] = (counts[key] || 0) + 1;
    }
    _badCoords = new Set(Object.entries(counts).filter(([, v]) => v > 10).map(([k]) => k));
    return _badCoords;
  }

  function hasGoodCoords(s) {
    if (!s.latitude || !s.longitude) return false;
    const key = `${s.latitude.toFixed(4)},${s.longitude.toFixed(4)}`;
    return !getBadCoords().has(key);
  }

  function sortByDistance(lat, lng) {
    // Split into stores with good coords vs bad coords
    const withCoords = [];
    const withoutCoords = [];

    for (const s of stores) {
      if (hasGoodCoords(s)) {
        withCoords.push({ ...s, _dist: calcDistance(lat, lng, s.latitude, s.longitude) });
      } else {
        withoutCoords.push(s);
      }
    }

    // Sort good-coord stores by distance
    withCoords.sort((a, b) => a._dist - b._dist);

    // For bad-coord stores, do a reverse-geocode city match:
    // Get the city/state from the geocoded point and match stores in that area
    let nearby = withCoords.slice(0, maxResults);

    // If we got fewer than maxResults from coords, supplement with city-matched stores
    if (nearby.length < maxResults && withoutCoords.length > 0) {
      // Use the closest good-coord store's city as a reference, or fall back to address search text
      const refCity = nearby.length > 0 ? nearby[0].City?.toLowerCase() : addressSearch?.toLowerCase() || '';
      const refState = nearby.length > 0 ? nearby[0].State?.toLowerCase() : '';

      const cityMatches = withoutCoords.filter(s => {
        const city = (s.City || '').toLowerCase();
        const state = (s.State || '').toLowerCase();
        return (refCity && city.includes(refCity)) || (refCity && refCity.includes(city)) ||
               (refState && state === refState && city === refCity);
      });

      // Add city-matched stores (mark distance as approximate)
      for (const s of cityMatches) {
        if (nearby.length >= maxResults * 2) break;
        if (!nearby.find(n => n.StoreName === s.StoreName)) {
          nearby.push({ ...s, _dist: undefined, _approx: true });
        }
      }
    }

    filtered = nearby.slice(0, maxResults * 2); // Show more results to be helpful
    showDropdown = filtered.length > 0;
    dispatch('results', filtered);
  }

  function findNearby() {
    if (!navigator.geolocation) {
      geoMessage = 'Geolocation not supported';
      return;
    }
    geoMessage = 'Locating...';
    navigator.geolocation.getCurrentPosition(
      pos => {
        geoMessage = '';
        searchTerm = '';
        sortByDistance(pos.coords.latitude, pos.coords.longitude);
      },
      () => { geoMessage = 'Location access denied'; },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  async function findByAddress() {
    if (!addressSearch.trim()) return;
    addressSearching = true;
    geoMessage = '';
    try {
      const q = encodeURIComponent(addressSearch.trim());
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?q=${q}&format=json&limit=1&countrycodes=us`,
        { headers: { Accept: 'application/json' } }
      );
      const data = await res.json();
      if (!data || data.length === 0) {
        geoMessage = `Could not find "${addressSearch}". Try a full address, city, or zip.`;
        addressSearching = false;
        return;
      }
      const lat = parseFloat(data[0].lat);
      const lng = parseFloat(data[0].lon);
      searchTerm = '';
      sortByDistance(lat, lng);
    } catch (err) {
      geoMessage = 'Address lookup failed: ' + err.message;
    } finally {
      addressSearching = false;
    }
  }

  /** Allow parent to clear / reset the input */
  export function clear() {
    searchTerm = '';
    addressSearch = '';
    filtered = [];
    showDropdown = false;
    geoMessage = '';
  }
</script>

<div class="ssi-wrap">
  <input
    type="text"
    class="ssi-input"
    {placeholder}
    bind:value={searchTerm}
    on:focus={() => { if (filtered.length) showDropdown = true; }}
  />

  {#if showGeo}
    <div class="ssi-geo-row">
      <input
        type="text"
        class="ssi-addr"
        placeholder="Enter any address to find closest stores..."
        bind:value={addressSearch}
        on:keydown={e => { if (e.key === 'Enter') findByAddress(); }}
      />
      <button class="ssi-addr-btn" on:click={findByAddress} disabled={addressSearching || !addressSearch.trim()}>
        {addressSearching ? '⏳' : '📍'} Find
      </button>
      <button class="ssi-geo-btn" on:click={findNearby}>📍 Near Me</button>
    </div>
  {/if}

  {#if geoMessage}
    <p class="ssi-msg">{geoMessage}</p>
  {/if}

  {#if showDropdown && filtered.length > 0}
    <div class="ssi-dropdown">
      {#each filtered as store (store.StoreName)}
        <button class="ssi-option" on:click={() => selectStore(store)}>
          <div class="ssi-opt-main">
            <strong>{store.GroceryChain}</strong> — {store.City}, {store.State}
          </div>
          <div class="ssi-opt-detail">
            {store.Address || ''} · {store.StoreName} · Cycle {store.Cycle || '?'}
            {#if store._dist !== undefined} · 📍 {store._dist.toFixed(1)} mi{:else if store._approx} · 📍 Nearby{/if}
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .ssi-wrap { position: relative; width: 100%; }
  .ssi-input {
    width: 100%; padding: 10px 12px; border: 1px solid #ddd; border-radius: 8px;
    font-size: 14px; box-sizing: border-box;
  }
  .ssi-input:focus { border-color: #CC0000; outline: none; box-shadow: 0 0 0 2px rgba(204,0,0,.15); }
  .ssi-geo-row { display: flex; gap: 6px; margin-top: 6px; }
  .ssi-addr {
    flex: 1; padding: 8px 10px; border: 1px solid #ddd; border-radius: 8px;
    font-size: 13px; box-sizing: border-box;
  }
  .ssi-addr:focus { border-color: #1565C0; outline: none; }
  .ssi-addr-btn, .ssi-geo-btn {
    white-space: nowrap; padding: 8px 12px; border: none; border-radius: 8px;
    font-size: 13px; cursor: pointer; font-weight: 600;
  }
  .ssi-addr-btn { background: #1565C0; color: #fff; }
  .ssi-addr-btn:disabled { opacity: .5; cursor: default; }
  .ssi-geo-btn { background: #e8f5e9; color: #2e7d32; }
  .ssi-msg { font-size: 12px; color: #c33; margin: 4px 0 0; }
  .ssi-dropdown {
    position: absolute; left: 0; right: 0; top: 100%;
    background: #fff; border: 1px solid #ddd; border-radius: 8px;
    max-height: 280px; overflow-y: auto; z-index: 999;
    box-shadow: 0 4px 12px rgba(0,0,0,.12);
  }
  .ssi-option {
    display: block; width: 100%; text-align: left; padding: 10px 12px;
    border: none; border-bottom: 1px solid #f0f0f0; background: none;
    cursor: pointer; font-size: 13px;
  }
  .ssi-option:last-child { border-bottom: none; }
  .ssi-option:hover { background: #f5f5f5; }
  .ssi-opt-main { font-size: 14px; }
  .ssi-opt-detail { font-size: 11px; color: #888; margin-top: 2px; }
</style>
