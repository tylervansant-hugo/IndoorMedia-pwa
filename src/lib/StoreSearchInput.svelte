<script>
  import { createEventDispatcher } from 'svelte';

  export let stores = [];
  export let placeholder = 'Search store, city, zip, or address...';
  export let maxResults = 20;
  export let showGeo = true;

  const dispatch = createEventDispatcher();

  let searchTerm = '';
  let searching = false;
  let filtered = [];
  let showDropdown = false;
  let message = '';
  let debounceTimer = null;

  // Haversine distance in miles
  function calcDistance(lat1, lon1, lat2, lon2) {
    const R = 3959;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  // Detect junk coordinates (state centroids shared by >10 stores)
  let _badCoords = null;
  function isBadCoord(s) {
    if (!s.latitude || !s.longitude) return true;
    if (!_badCoords) {
      const counts = {};
      for (const st of stores) {
        if (!st.latitude || !st.longitude) continue;
        const key = `${st.latitude.toFixed(4)},${st.longitude.toFixed(4)}`;
        counts[key] = (counts[key] || 0) + 1;
      }
      _badCoords = new Set(Object.entries(counts).filter(([, v]) => v > 10).map(([k]) => k));
    }
    return _badCoords.has(`${s.latitude.toFixed(4)},${s.longitude.toFixed(4)}`);
  }

  function smartSortByDistance(lat, lng, hint = '') {
    const good = [];
    const bad = [];
    for (const s of stores) {
      if (!isBadCoord(s)) good.push({ ...s, _dist: calcDistance(lat, lng, s.latitude, s.longitude) });
      else bad.push(s);
    }
    good.sort((a, b) => a._dist - b._dist);
    let results = good.slice(0, maxResults);

    // Supplement with city-matched bad-coord stores
    const refCity = results[0]?.City?.toLowerCase() || hint.toLowerCase();
    if (refCity && bad.length) {
      for (const s of bad) {
        const city = (s.City || '').toLowerCase();
        if (city.includes(refCity) || refCity.includes(city)) {
          if (!results.find(r => r.StoreName === s.StoreName)) {
            results.push({ ...s, _dist: undefined, _approx: true });
          }
        }
        if (results.length >= maxResults * 2) break;
      }
    }
    return results;
  }

  // Detect if input looks like an address (has numbers + words, or is a zip code)
  function looksLikeAddress(term) {
    const t = term.trim();
    // Pure zip code
    if (/^\d{5}(-\d{4})?$/.test(t)) return true;
    // Has a number followed by words (street address pattern)
    if (/^\d+\s+\w/.test(t) && t.length > 8) return true;
    return false;
  }

  function textSearch(term) {
    const q = term.toLowerCase();
    return stores.filter(s =>
      (s.StoreName && s.StoreName.toLowerCase().includes(q)) ||
      (s.GroceryChain && s.GroceryChain.toLowerCase().includes(q)) ||
      (s.City && s.City.toLowerCase().includes(q)) ||
      (s.Address && s.Address.toLowerCase().includes(q)) ||
      (s.State && s.State.toLowerCase().includes(q)) ||
      (s.PostalCode && s.PostalCode.includes(q))
    ).slice(0, maxResults);
  }

  async function geocodeAndSort(term) {
    searching = true;
    message = '';
    try {
      const q = encodeURIComponent(term.trim());
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?q=${q}&format=json&limit=1&countrycodes=us`,
        { headers: { Accept: 'application/json' } }
      );
      const data = await res.json();
      if (data && data.length > 0) {
        const lat = parseFloat(data[0].lat);
        const lng = parseFloat(data[0].lon);
        filtered = smartSortByDistance(lat, lng, term);
        showDropdown = filtered.length > 0;
        dispatch('results', filtered);
        if (filtered.length === 0) message = 'No stores found near that location';
      } else {
        // Geocode failed, fall back to text search
        filtered = textSearch(term);
        showDropdown = filtered.length > 0;
        dispatch('results', filtered);
        if (filtered.length === 0) message = `No stores found for "${term}"`;
      }
    } catch {
      // Network error, fall back to text search
      filtered = textSearch(term);
      showDropdown = filtered.length > 0;
      dispatch('results', filtered);
    } finally {
      searching = false;
    }
  }

  function handleInput() {
    message = '';
    clearTimeout(debounceTimer);

    if (searchTerm.length < 2) {
      filtered = [];
      showDropdown = false;
      dispatch('results', []);
      return;
    }

    // Instant text search first
    filtered = textSearch(searchTerm);
    showDropdown = filtered.length > 0;
    dispatch('results', filtered);

    // If it looks like an address/zip and text search found nothing, try geocoding
    if (filtered.length === 0 && looksLikeAddress(searchTerm)) {
      debounceTimer = setTimeout(() => geocodeAndSort(searchTerm), 600);
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Enter' && searchTerm.trim().length >= 2) {
      // On Enter, always try geocoding if text search has few results
      if (filtered.length <= 3) {
        geocodeAndSort(searchTerm);
      }
    }
  }

  function findNearby() {
    if (!navigator.geolocation) { message = 'Geolocation not supported'; return; }
    searching = true;
    message = '';
    navigator.geolocation.getCurrentPosition(
      pos => {
        searching = false;
        filtered = smartSortByDistance(pos.coords.latitude, pos.coords.longitude);
        showDropdown = filtered.length > 0;
        dispatch('results', filtered);
      },
      () => { searching = false; message = 'Location access denied'; },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  function selectStore(store) {
    dispatch('select', store);
    searchTerm = `${store.GroceryChain} — ${store.City}, ${store.State} (${store.StoreName})`;
    showDropdown = false;
    filtered = [];
  }

  export function clear() {
    searchTerm = '';
    filtered = [];
    showDropdown = false;
    message = '';
  }
</script>

<div class="ssi-wrap">
  <div class="ssi-bar">
    <input
      type="text"
      class="ssi-input"
      {placeholder}
      bind:value={searchTerm}
      on:input={handleInput}
      on:keydown={handleKeydown}
      on:focus={() => { if (filtered.length) showDropdown = true; }}
    />
    {#if searching}
      <span class="ssi-spinner">⏳</span>
    {/if}
    {#if showGeo}
      <button class="ssi-geo" on:click={findNearby} title="Use my location">📍</button>
    {/if}
  </div>

  {#if message}
    <p class="ssi-msg">{message}</p>
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
  .ssi-bar { display: flex; align-items: center; gap: 0; border: 2px solid #ddd; border-radius: 10px; background: white; overflow: hidden; }
  .ssi-bar:focus-within { border-color: #CC0000; box-shadow: 0 0 0 2px rgba(204,0,0,.1); }
  .ssi-input {
    flex: 1; padding: 12px 14px; border: none; font-size: 15px;
    box-sizing: border-box; outline: none; background: transparent; min-width: 0;
  }
  .ssi-spinner { padding: 0 6px; font-size: 16px; }
  .ssi-geo {
    padding: 10px 14px; border: none; border-left: 1px solid #eee;
    background: none; font-size: 18px; cursor: pointer; flex-shrink: 0;
  }
  .ssi-geo:hover { background: #f5f5f5; }
  .ssi-msg { font-size: 12px; color: #999; margin: 4px 0 0; padding-left: 4px; }
  .ssi-dropdown {
    position: absolute; left: 0; right: 0; top: calc(100% + 4px);
    background: #fff; border: 1px solid #ddd; border-radius: 10px;
    max-height: 300px; overflow-y: auto; z-index: 999;
    box-shadow: 0 4px 16px rgba(0,0,0,.12);
  }
  .ssi-option {
    display: block; width: 100%; text-align: left; padding: 10px 14px;
    border: none; border-bottom: 1px solid #f5f5f5; background: none;
    cursor: pointer; font-size: 13px;
  }
  .ssi-option:last-child { border-bottom: none; }
  .ssi-option:hover { background: #fff5f5; }
  .ssi-opt-main { font-size: 14px; }
  .ssi-opt-detail { font-size: 11px; color: #888; margin-top: 2px; }
</style>
