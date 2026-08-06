<script>
  // Universal homepage search — one bar to find stores, prospects/leads,
  // existing clients (contracts), testimonials, and more. Selecting a result
  // navigates to the right tab/view via CustomEvents (handled by the target
  // components) or opens an external testimonial page.
  import { onMount, createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();

  export let allStores = [];       // shared from Main (already loaded)
  export let savedProspects = [];  // shared from Main (localStorage-backed)

  let query = '';
  let open = false;      // results dropdown open
  let inputEl;

  // Lazily-loaded data
  let contracts = [];          // existing clients
  let testimonials = [];       // full testimonial list (normalized)
  let prospectData = [];       // researched prospect_data.json (optional)
  let loaded = false;
  let loading = false;

  function decodeEnt(str) {
    if (!str) return '';
    const el = document.createElement('textarea');
    el.innerHTML = String(str);
    return el.value.replace(/\s+/g, ' ').trim();
  }

  async function ensureData() {
    if (loaded || loading) return;
    loading = true;
    const base = import.meta.env.BASE_URL;
    try {
      const [cRes, tRes, pRes] = await Promise.all([
        fetch(base + 'data/contracts.json?t=' + Date.now()).catch(() => null),
        fetch(base + 'data/testimonials_slim.json?t=' + Date.now()).catch(() => null),
        fetch(base + 'data/prospect_data.json?t=' + Date.now()).catch(() => null),
      ]);
      if (cRes && cRes.ok) {
        const cd = await cRes.json();
        contracts = cd.contracts || cd || [];
      }
      if (tRes && tRes.ok) {
        const td = await tRes.json();
        const arr = Array.isArray(td) ? td : (td.testimonials || []);
        testimonials = arr.map((t, i) => ({
          id: t.id != null ? t.id : i,
          business: decodeEnt(t.biz || t.b || t.business || ''),
          comment: decodeEnt(t.c || t.comment || ''),
          url: t.u || t.url || '',
        })).filter(t => t.comment);
      }
      if (pRes && pRes.ok) {
        const pd = await pRes.json();
        if (Array.isArray(pd)) {
          prospectData = pd;
        } else if (pd && pd.reps) {
          // prospect_data.json is keyed reps -> saved_prospects{}. Flatten it,
          // tagging each with the owning rep for context.
          const flat = [];
          for (const rid in pd.reps) {
            const rep = pd.reps[rid] || {};
            const sp = rep.saved_prospects || {};
            for (const k in sp) {
              flat.push({ ...sp[k], _repName: rep.name || '' });
            }
          }
          prospectData = flat;
        } else {
          prospectData = pd.prospects || pd.data || [];
        }
      }
    } catch (e) {
      console.warn('[UniversalSearch] data load failed:', e);
    }
    loaded = true;
    loading = false;
    runSearch();
  }

  // Result groups
  let results = { stores: [], clients: [], prospects: [], testimonials: [] };
  let totalCount = 0;

  function runSearch() {
    const q = query.trim().toLowerCase();
    if (q.length < 2) {
      results = { stores: [], clients: [], prospects: [], testimonials: [] };
      totalCount = 0;
      return;
    }
    const matchStr = (v) => v && String(v).toLowerCase().includes(q);

    // Stores
    const stores = (allStores || []).filter(s =>
      matchStr(s.StoreName) || matchStr(s.GroceryChain) || matchStr(s.City) ||
      matchStr(s.Address) || matchStr(s.State) || matchStr(s.PostalCode) || matchStr(s.ZoneName)
    ).slice(0, 6);

    // Existing clients (contracts)
    const clients = (contracts || []).filter(c =>
      matchStr(c.business_name) || matchStr(c.contact_name) || matchStr(c.contact_email) ||
      matchStr(c.contact_phone) || matchStr(c.store_name) || matchStr(c.sales_rep) ||
      matchStr(c.address) || matchStr(c.contract_number)
    ).slice(0, 6);

    // Saved prospects / leads (from localStorage + researched prospect_data)
    const seen = new Set();
    const prospects = [];
    for (const p of (savedProspects || [])) {
      if (matchStr(p.name) || matchStr(p.businessName) || matchStr(p.contactName) ||
          matchStr(p.contact) || matchStr(p.phone) || matchStr(p.email) ||
          matchStr(p.address) || matchStr(p.city) || matchStr(p.category) || matchStr(p.subcategory)) {
        const key = (p.name || p.businessName || '') + (p.address || '');
        if (!seen.has(key)) { seen.add(key); prospects.push({ ...p, _src: 'saved' }); }
      }
      if (prospects.length >= 6) break;
    }
    if (prospects.length < 6) {
      for (const p of (prospectData || [])) {
        const name = p.name || p.business_name || p.businessName || '';
        if (matchStr(name) || matchStr(p.contact_name) || matchStr(p.phone) ||
            matchStr(p.email) || matchStr(p.address) || matchStr(p.city) || matchStr(p.category)) {
          const key = name + (p.address || '');
          if (!seen.has(key)) { seen.add(key); prospects.push({ ...p, name, _src: 'data' }); }
        }
        if (prospects.length >= 6) break;
      }
    }

    // Testimonials
    const testis = (testimonials || []).filter(t =>
      matchStr(t.business) || matchStr(t.comment)
    ).slice(0, 5);

    results = { stores, clients, prospects, testimonials: testis };
    totalCount = stores.length + clients.length + prospects.length + testis.length;
  }

  function onInput() {
    open = true;
    if (!loaded) { ensureData(); return; }
    runSearch();
  }

  function clearSearch() {
    query = '';
    results = { stores: [], clients: [], prospects: [], testimonials: [] };
    totalCount = 0;
    open = false;
  }

  // ── Navigation ──────────────────────────────────────────────
  function goStore(store) {
    dispatch('navigate', { tab: 'stores', storesView: 'rates' });
    setTimeout(() => document.dispatchEvent(new CustomEvent('universal-store-search',
      { detail: { term: store.StoreName || store.City || query, storeName: store.StoreName } })), 260);
    clearSearch();
  }
  function goClient(client) {
    dispatch('navigate', { tab: 'clients' });
    setTimeout(() => document.dispatchEvent(new CustomEvent('universal-client-search',
      { detail: { term: client.business_name || client.contact_name || query } })), 260);
    clearSearch();
  }
  function goProspect(p) {
    dispatch('navigate', { tab: 'stores', storesView: 'prospects' });
    setTimeout(() => document.dispatchEvent(new CustomEvent('universal-prospect-search',
      { detail: { term: p.name || p.businessName || query } })), 260);
    clearSearch();
  }
  function goTestimonial(t) {
    if (t.url) window.open(t.url, '_blank');
  }

  // Close dropdown when clicking outside.
  function onDocClick(e) {
    if (inputEl && !inputEl.closest('.usearch-wrap').contains(e.target)) open = false;
  }
  onMount(() => {
    document.addEventListener('click', onDocClick);
    return () => document.removeEventListener('click', onDocClick);
  });

  function highlightLabel(store) {
    // Friendly store label: Chain + City (StoreName code as sub)
    const chain = store.GroceryChain || 'Store';
    const city = store.City ? ` · ${store.City}${store.State ? ', ' + store.State : ''}` : '';
    return `${chain}${city}`;
  }
</script>

<div class="usearch-wrap">
  <div class="usearch-box" class:active={open && query.trim().length >= 2}>
    <span class="usearch-icon">🔎</span>
    <input
      bind:this={inputEl}
      type="text"
      class="usearch-input"
      placeholder="Search everything — stores, businesses, contacts, clients, testimonials…"
      bind:value={query}
      on:input={onInput}
      on:focus={() => { open = true; if (!loaded) ensureData(); }}
    />
    {#if query}
      <button class="usearch-clear" on:click={clearSearch} title="Clear">✕</button>
    {/if}
  </div>

  {#if open && query.trim().length >= 2}
    <div class="usearch-results">
      {#if loading && !loaded}
        <p class="usearch-hint">Loading…</p>
      {:else if totalCount === 0}
        <p class="usearch-hint">No matches for “{query}”. Try a business, contact, city, or store.</p>
      {:else}
        {#if results.stores.length}
          <div class="usearch-group">
            <div class="usearch-group-head">🏪 Stores</div>
            {#each results.stores as s}
              <button class="usearch-item" on:click={() => goStore(s)}>
                <span class="usearch-item-title">{highlightLabel(s)}</span>
                <span class="usearch-item-sub">{s.StoreName}{s.Address ? ' · ' + s.Address : ''}</span>
              </button>
            {/each}
          </div>
        {/if}

        {#if results.clients.length}
          <div class="usearch-group">
            <div class="usearch-group-head">🤝 Clients</div>
            {#each results.clients as c}
              <button class="usearch-item" on:click={() => goClient(c)}>
                <span class="usearch-item-title">{c.business_name || c.contact_name || 'Client'}</span>
                <span class="usearch-item-sub">
                  {[c.contact_name, c.store_name, c.sales_rep && ('Rep: ' + c.sales_rep)].filter(Boolean).join(' · ')}
                </span>
              </button>
            {/each}
          </div>
        {/if}

        {#if results.prospects.length}
          <div class="usearch-group">
            <div class="usearch-group-head">🎯 Prospects &amp; Leads</div>
            {#each results.prospects as p}
              <button class="usearch-item" on:click={() => goProspect(p)}>
                <span class="usearch-item-title">{p.name || p.businessName || 'Prospect'}</span>
                <span class="usearch-item-sub">
                  {[p.contactName || p.contact_name, p.city, p.category || p.subcategory].filter(Boolean).join(' · ') || 'Saved lead'}
                </span>
              </button>
            {/each}
          </div>
        {/if}

        {#if results.testimonials.length}
          <div class="usearch-group">
            <div class="usearch-group-head">⭐ Testimonials</div>
            {#each results.testimonials as t}
              <button class="usearch-item" on:click={() => goTestimonial(t)}>
                <span class="usearch-item-title">{t.business || 'IndoorMedia Advertiser'}</span>
                <span class="usearch-item-sub">“{t.comment}”</span>
              </button>
            {/each}
          </div>
        {/if}
      {/if}
    </div>
  {/if}
</div>

<style>
  .usearch-wrap { position: relative; margin-bottom: 14px; }
  .usearch-box {
    display: flex; align-items: center; gap: 8px;
    background: var(--card-bg, #fff);
    border: 1.5px solid var(--border-color, #e0e0e0);
    border-radius: 12px;
    padding: 11px 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    transition: border-color 0.15s, box-shadow 0.15s;
  }
  .usearch-box.active { border-color: #CC0000; box-shadow: 0 2px 10px rgba(204,0,0,0.12); }
  .usearch-icon { font-size: 16px; opacity: 0.8; }
  .usearch-input {
    flex: 1; border: none; outline: none; background: transparent;
    font-size: 15px; color: var(--text-primary, #222);
    min-width: 0;
  }
  .usearch-input::placeholder { color: var(--text-secondary, #999); }
  .usearch-clear {
    background: none; border: none; cursor: pointer; font-size: 14px;
    color: var(--text-secondary, #999); padding: 2px 6px; line-height: 1;
  }
  .usearch-results {
    position: absolute; top: calc(100% + 6px); left: 0; right: 0; z-index: 50;
    background: var(--card-bg, #fff);
    border: 1px solid var(--border-color, #e0e0e0);
    border-radius: 12px;
    box-shadow: 0 8px 28px rgba(0,0,0,0.18);
    max-height: 60vh; overflow-y: auto;
    padding: 6px;
  }
  .usearch-hint { font-size: 13px; color: var(--text-secondary, #999); padding: 12px 10px; margin: 0; }
  .usearch-group { padding: 4px 0; }
  .usearch-group + .usearch-group { border-top: 1px solid var(--border-color, #eee); }
  .usearch-group-head {
    font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.4px;
    color: #CC0000; padding: 6px 10px 4px;
  }
  .usearch-item {
    display: flex; flex-direction: column; gap: 2px; width: 100%;
    text-align: left; background: none; border: none; cursor: pointer;
    padding: 8px 10px; border-radius: 8px;
  }
  .usearch-item:hover, .usearch-item:active { background: var(--bg-secondary, #f6f6f6); }
  .usearch-item-title { font-size: 14px; font-weight: 700; color: var(--text-primary, #222); }
  .usearch-item-sub {
    font-size: 12px; color: var(--text-secondary, #888); line-height: 1.35;
    display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden;
  }
</style>
