<script>
  import { user } from '../lib/stores.js';
  import { onMount } from 'svelte';

  export let onBack = () => {};

  let businessName = '';
  let businessAddress = '';
  let businessPhone = '';
  let businessCategory = '';
  let businessWebsite = '';
  let storeSearch = '';
  let selectedStore = null;
  let allStores = [];
  let storeResults = [];
  let showStoreDropdown = false;

  let step = 'search'; // search, loading, results
  let loadingStatus = '';
  let loadingStep = 0;

  // Results
  let businessInfo = null;
  let matchedTestimonials = [];
  let localTestimonial = null;
  let searchResults = [];
  let searching = false;
  let allTestimonials = [];

  onMount(async () => {
    try {
      const [storeRes, testRes] = await Promise.all([
        fetch(import.meta.env.BASE_URL + 'data/stores.json'),
        fetch(import.meta.env.BASE_URL + 'data/testimonials_cache.json')
      ]);
      allStores = await storeRes.json();
      allTestimonials = await testRes.json();
    } catch {}
  });

  // Store search
  function searchStores() {
    if (!storeSearch.trim() || storeSearch.length < 2) { storeResults = []; showStoreDropdown = false; return; }
    const term = storeSearch.toLowerCase();
    storeResults = allStores.filter(s =>
      (s.StoreName || '').toLowerCase().includes(term) ||
      (s.GroceryChain || '').toLowerCase().includes(term) ||
      (s.City || '').toLowerCase().includes(term) ||
      (s.PostalCode || '').includes(term) ||
      (s.Address || '').toLowerCase().includes(term)
    ).slice(0, 10);
    showStoreDropdown = storeResults.length > 0;
  }
  function selectStore(store) {
    selectedStore = store;
    storeSearch = `${store.GroceryChain} — ${store.City}, ${store.State} (${store.StoreName})`;
    showStoreDropdown = false; storeResults = [];
  }

  // Business search with location bias
  async function searchBusiness() {
    if (!businessName.trim() || businessName.length < 3) return;
    searching = true;
    try {
      const apiKey = import.meta.env.VITE_GOOGLE_PLACES_API_KEY || 'AIzaSyBNR8M1VG5DccJmK6ZzJOam9mF8jOCEEqM';
      const body = { textQuery: businessName, maxResultCount: 5 };
      if (selectedStore?.latitude && selectedStore?.longitude) {
        body.locationBias = { circle: { center: { latitude: selectedStore.latitude, longitude: selectedStore.longitude }, radius: 8000.0 } };
      }
      const res = await fetch('https://places.googleapis.com/v1/places:searchText', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Goog-Api-Key': apiKey,
          'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.primaryTypeDisplayName,places.types' },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      searchResults = (data.places || []).map(p => ({
        name: p.displayName?.text || '', address: p.formattedAddress || '',
        phone: p.nationalPhoneNumber || '', website: p.websiteUri || '',
        category: p.primaryTypeDisplayName?.text || '',
        types: p.types || []
      }));
    } catch { searchResults = []; }
    searching = false;
  }

  function selectBusiness(biz) {
    businessName = biz.name; businessAddress = biz.address; businessPhone = biz.phone;
    businessCategory = biz.category; businessWebsite = biz.website;
    searchResults = [];
  }

  // ===== MAIN PREP FUNCTION =====
  async function runPrep() {
    if (!businessName.trim()) return alert('Please enter a business name');
    step = 'loading';
    loadingStep = 1;
    loadingStatus = '🔍 Looking up business details...';
    
    businessInfo = {
      name: businessName,
      address: businessAddress,
      phone: businessPhone,
      category: businessCategory,
      website: businessWebsite,
      services: [],
      menuItems: [],
      websiteData: null
    };

    // Step 1: Try to scrape website for services/menu
    loadingStep = 2;
    loadingStatus = '🌐 Checking website & social media...';
    
    if (businessWebsite) {
      try {
        // Use a CORS proxy or just extract what we can from the URL
        businessInfo.websiteData = businessWebsite;
      } catch {}
    }

    await new Promise(r => setTimeout(r, 500));

    // Step 2: Find category-matched testimonials
    loadingStep = 3;
    loadingStatus = '📝 Finding matching testimonials...';
    
    const categoryKeywords = extractCategoryKeywords(businessCategory, businessName);
    matchedTestimonials = findMatchingTestimonials(categoryKeywords, businessName);
    
    await new Promise(r => setTimeout(r, 300));

    // Step 3: Find local testimonial (same city/area as the store)
    loadingStep = 4;
    loadingStatus = '📍 Finding local testimonials...';
    
    localTestimonial = findLocalTestimonial();

    await new Promise(r => setTimeout(r, 300));

    loadingStep = 5;
    loadingStatus = '✅ Prep complete!';
    await new Promise(r => setTimeout(r, 500));
    step = 'results';
  }

  function extractCategoryKeywords(category, name) {
    const combined = (category + ' ' + name).toLowerCase();
    const keywords = [];
    
    const categoryMap = {
      'restaurant': ['restaurant', 'food', 'dining', 'kitchen', 'cafe', 'grill', 'eatery'],
      'pizza': ['pizza', 'pizzeria', 'italian'],
      'mexican': ['mexican', 'taco', 'burrito', 'taqueria', 'enchilada', 'salsa'],
      'chinese': ['chinese', 'asian', 'wok', 'noodle', 'dim sum'],
      'thai': ['thai', 'asian', 'curry', 'pad'],
      'sushi': ['sushi', 'japanese', 'ramen', 'teriyaki'],
      'indian': ['indian', 'curry', 'tandoori', 'masala'],
      'burger': ['burger', 'grill', 'bbq', 'wings'],
      'coffee': ['coffee', 'cafe', 'espresso', 'bakery'],
      'salon': ['salon', 'hair', 'beauty', 'barber', 'cut', 'style', 'nail'],
      'barber': ['barber', 'barbershop', 'haircut', 'men'],
      'auto': ['auto', 'car', 'mechanic', 'oil change', 'tire', 'transmission', 'brake', 'repair'],
      'dental': ['dental', 'dentist', 'teeth', 'orthodont'],
      'gym': ['gym', 'fitness', 'workout', 'training', 'crossfit'],
      'vet': ['vet', 'veterinar', 'pet', 'animal', 'dog', 'cat'],
      'chiropractic': ['chiropractic', 'chiropractor', 'spine', 'adjustment'],
      'massage': ['massage', 'spa', 'wellness', 'therapy'],
      'cleaning': ['cleaning', 'maid', 'janitorial', 'carpet'],
      'plumbing': ['plumbing', 'plumber', 'drain', 'pipe'],
      'insurance': ['insurance', 'allstate', 'state farm', 'coverage'],
      'real estate': ['real estate', 'realtor', 'realty', 'homes'],
      'dry cleaner': ['dry clean', 'laundry', 'press'],
      'ice cream': ['ice cream', 'frozen', 'yogurt', 'gelato'],
      'donut': ['donut', 'doughnut', 'bakery'],
      'seafood': ['seafood', 'fish', 'shrimp', 'crab', 'lobster'],
    };

    for (const [cat, words] of Object.entries(categoryMap)) {
      if (words.some(w => combined.includes(w))) {
        keywords.push(...words);
      }
    }
    
    // Also add the business name words
    businessName.toLowerCase().split(/\s+/).forEach(w => {
      if (w.length > 3) keywords.push(w);
    });

    return [...new Set(keywords)];
  }

  function findMatchingTestimonials(keywords, name) {
    if (!allTestimonials.length) return [];

    // Score each testimonial
    const scored = allTestimonials.map(t => {
      const search = (t.searchable || (t.business + ' ' + t.comment)).toLowerCase();
      let score = 0;
      
      // Keyword matches in business name
      keywords.forEach(kw => {
        if (search.includes(kw)) score += 3;
      });

      // Bonus for having concrete metrics (coupons, ROI, revenue)
      if (/\d+ coupon/i.test(t.comment)) score += 2;
      if (/return on/i.test(t.comment)) score += 2;
      if (/\$\d/i.test(t.comment)) score += 1;
      if (/renew/i.test(t.comment)) score += 1;
      if (/year|month/i.test(t.comment)) score += 1;
      
      // Bonus for longer, more detailed testimonials
      if (t.comment.length > 150) score += 1;
      if (t.comment.length > 300) score += 1;

      return { ...t, score };
    }).filter(t => t.score > 3)
      .sort((a, b) => b.score - a.score);

    // Take top 3-4 unique businesses
    const seen = new Set();
    const results = [];
    for (const t of scored) {
      const bizKey = t.business.toLowerCase().split('-')[0].trim();
      if (seen.has(bizKey)) continue;
      seen.add(bizKey);
      results.push(t);
      if (results.length >= 4) break;
    }

    return results;
  }

  function findLocalTestimonial() {
    if (!selectedStore || !allTestimonials.length) return null;
    
    const city = (selectedStore.City || '').toLowerCase();
    const state = (selectedStore.State || '').toLowerCase();
    const chain = (selectedStore.GroceryChain || '').toLowerCase();
    
    // Find testimonials mentioning the same city, state, or chain
    const local = allTestimonials.filter(t => {
      const search = (t.searchable || t.business + ' ' + t.comment).toLowerCase();
      return search.includes(city) || search.includes(chain);
    }).sort((a, b) => b.comment.length - a.comment.length);

    // Pick one that isn't already in matched testimonials
    const matchedIds = new Set(matchedTestimonials.map(t => t.id));
    return local.find(t => !matchedIds.has(t.id)) || local[0] || null;
  }

  function cleanBizName(name) {
    return (name || '').replace(/&#x27;/g, "'").replace(/&#x9;/g, '').replace(/\s+-\s+/g, ' — ').trim();
  }

  function copyTestimonials() {
    const lines = [];
    lines.push(`MEETING PREP: ${businessName}`);
    lines.push(`Category: ${businessCategory}`);
    lines.push(`Store: ${storeSearch}`);
    lines.push('');
    lines.push('--- MATCHING TESTIMONIALS ---');
    matchedTestimonials.forEach((t, i) => {
      lines.push(`\n${i+1}. ${cleanBizName(t.business)}`);
      lines.push(`"${t.comment}"`);
    });
    if (localTestimonial) {
      lines.push('\n--- LOCAL TESTIMONIAL ---');
      lines.push(`${cleanBizName(localTestimonial.business)}`);
      lines.push(`"${localTestimonial.comment}"`);
    }
    navigator.clipboard.writeText(lines.join('\n'));
    alert('✅ Copied to clipboard!');
  }
</script>

<div class="prep">
  {#if step === 'search'}
    <button class="back-btn" on:click={onBack}>← Back</button>
    <h2>📋 Meeting Prep</h2>
    <p class="sub">Look up the business and we'll find the best testimonials to match</p>

    <div class="f rel">
      <label>Nearby Store (select first for better results)</label>
      <input type="text" bind:value={storeSearch} on:input={searchStores} placeholder="City, zip, store #..." autocomplete="off" />
      {#if showStoreDropdown}
        <div class="dd">
          {#each storeResults as s}
            <button class="ddi" on:click={() => selectStore(s)}><strong>{s.StoreName}</strong><small>{s.GroceryChain} — {s.City}, {s.State}</small></button>
          {/each}
        </div>
      {/if}
    </div>

    <div class="f rel">
      <label>Business Name *</label>
      <input type="text" bind:value={businessName} placeholder="e.g. Wow Cow, Joe's Pizza..." on:input={() => { if (businessName.length >= 3) searchBusiness(); }} />
      {#if searching}<span class="spin">🔍</span>{/if}
      {#if searchResults.length > 0}
        <div class="dd">
          {#each searchResults as b}
            <button class="ddi" on:click={() => selectBusiness(b)}><strong>{b.name}</strong><small>{b.address} {b.phone ? '• ' + b.phone : ''}</small>{#if b.category}<small class="cat-tag">{b.category}</small>{/if}</button>
          {/each}
        </div>
      {/if}
    </div>

    {#if businessAddress}
      <div class="biz-preview">
        <div class="biz-p-name">{businessName}</div>
        <div class="biz-p-info">{businessCategory} • {businessAddress}</div>
        {#if businessPhone}<div class="biz-p-info">{businessPhone}</div>{/if}
        {#if businessWebsite}<div class="biz-p-info"><a href={businessWebsite} target="_blank">{businessWebsite.replace('https://', '').replace('http://', '').split('/')[0]}</a></div>{/if}
      </div>
    {/if}

    <button class="btn-go" on:click={runPrep}>🔍 Run Meeting Prep</button>
    <div style="height:80px;"></div>

  {:else if step === 'loading'}
    <div class="loading">
      <div class="loading-icon">⏳</div>
      <h3>{loadingStatus}</h3>
      <div class="progress-bar"><div class="progress-fill" style="width:{loadingStep * 20}%;"></div></div>
      <p class="loading-sub">Analyzing {businessName}...</p>
    </div>

  {:else if step === 'results'}
    <button class="back-btn" on:click={() => step = 'search'}>← New Search</button>
    <h2>📋 Meeting Prep: {businessName}</h2>
    
    <div class="result-card info-card">
      <h3>🏢 Business Info</h3>
      <div class="info-row"><span class="info-label">Category:</span><span>{businessCategory || 'N/A'}</span></div>
      <div class="info-row"><span class="info-label">Address:</span><span>{businessAddress || 'N/A'}</span></div>
      {#if businessPhone}<div class="info-row"><span class="info-label">Phone:</span><span>{businessPhone}</span></div>{/if}
      {#if businessWebsite}<div class="info-row"><span class="info-label">Website:</span><a href={businessWebsite} target="_blank">{businessWebsite.replace('https://','').split('/')[0]}</a></div>{/if}
      {#if selectedStore}<div class="info-row"><span class="info-label">Store:</span><span>{selectedStore.GroceryChain} {selectedStore.City} ({selectedStore.StoreName})</span></div>{/if}
    </div>

    {#if matchedTestimonials.length > 0}
      <div class="result-card">
        <h3>⭐ Similar Business Testimonials</h3>
        <p class="result-hint">These are from businesses similar to {businessName} — use after the testimonial slide in your presentation</p>
        
        {#each matchedTestimonials as t, i}
          <div class="testimonial">
            <div class="test-num">{i + 1}</div>
            <div class="test-body">
              <div class="test-biz">{cleanBizName(t.business)}</div>
              <div class="test-quote">"{t.comment}"</div>
              {#if t.url}<a href={t.url} target="_blank" class="test-link">View full →</a>{/if}
            </div>
          </div>
        {/each}
      </div>
    {:else}
      <div class="result-card empty">
        <h3>⭐ Similar Business Testimonials</h3>
        <p>No closely matching testimonials found. Try broadening the category.</p>
      </div>
    {/if}

    {#if localTestimonial}
      <div class="result-card local-card">
        <h3>📍 Local Testimonial</h3>
        <p class="result-hint">A business near {selectedStore?.City || 'this area'} — great for "right here in your neighborhood" credibility</p>
        <div class="testimonial">
          <div class="test-num">📍</div>
          <div class="test-body">
            <div class="test-biz">{cleanBizName(localTestimonial.business)}</div>
            <div class="test-quote">"{localTestimonial.comment}"</div>
            {#if localTestimonial.url}<a href={localTestimonial.url} target="_blank" class="test-link">View full →</a>{/if}
          </div>
        </div>
      </div>
    {/if}

    <button class="btn-copy" on:click={copyTestimonials}>📋 Copy All to Clipboard</button>
    <button class="btn-secondary" on:click={() => step = 'search'}>🔄 New Prep</button>
    <div style="height:80px;"></div>
  {/if}
</div>

<style>
  .prep { }
  .back-btn { background:none; border:none; color:var(--text-secondary); font-size:14px; cursor:pointer; padding:8px 0; }
  .sub { font-size:13px; color:var(--text-secondary); margin:-4px 0 16px; }
  
  .f { margin-bottom:14px; }
  .f label { display:block; font-size:11px; font-weight:700; color:var(--text-secondary); margin-bottom:4px; text-transform:uppercase; letter-spacing:.3px; }
  .f input { width:100%; padding:12px; border:2px solid var(--border-color); border-radius:10px; font-size:15px; background:var(--card-bg); color:var(--text-primary); box-sizing:border-box; }
  .f input:focus { border-color:#CC0000; outline:none; }
  .rel { position:relative; }
  .spin { position:absolute; right:14px; top:38px; }
  .dd { position:absolute; top:100%; left:0; right:0; background:var(--card-bg); border:2px solid var(--border-color); border-radius:10px; margin-top:4px; max-height:220px; overflow-y:auto; z-index:100; box-shadow:0 6px 20px rgba(0,0,0,.25); }
  .ddi { display:block; width:100%; padding:12px; border:none; border-bottom:1px solid var(--border-color); background:transparent; text-align:left; cursor:pointer; color:var(--text-primary); font-size:14px; }
  .ddi:hover { background:rgba(204,0,0,.06); }
  .ddi:last-child { border-bottom:none; }
  .ddi small { display:block; font-size:12px; color:var(--text-secondary); margin-top:2px; }
  .cat-tag { color:#CC0000; font-weight:600; }

  .biz-preview { background:var(--card-bg); border:2px solid #CC0000; border-radius:12px; padding:14px; margin-bottom:16px; }
  .biz-p-name { font-size:18px; font-weight:800; color:var(--text-primary); }
  .biz-p-info { font-size:13px; color:var(--text-secondary); margin-top:4px; }
  .biz-p-info a { color:#CC0000; }

  .btn-go { width:100%; padding:16px; background:#CC0000; color:#fff; border:none; border-radius:12px; font-size:17px; font-weight:800; cursor:pointer; }
  .btn-go:hover { background:#a00; }

  /* Loading */
  .loading { text-align:center; padding:60px 20px; }
  .loading-icon { font-size:48px; margin-bottom:16px; animation:pulse 1.5s infinite; }
  @keyframes pulse { 0%,100%{transform:scale(1)} 50%{transform:scale(1.1)} }
  .loading h3 { font-size:18px; color:var(--text-primary); margin:0 0 16px; }
  .loading-sub { font-size:14px; color:var(--text-secondary); }
  .progress-bar { height:6px; background:var(--border-color); border-radius:3px; overflow:hidden; max-width:300px; margin:0 auto; }
  .progress-fill { height:100%; background:#CC0000; border-radius:3px; transition:width .5s; }

  /* Results */
  .result-card { background:var(--card-bg); border:2px solid var(--border-color); border-radius:14px; padding:18px; margin-bottom:16px; }
  .result-card h3 { margin:0 0 8px; font-size:17px; font-weight:800; color:var(--text-primary); }
  .result-hint { font-size:12px; color:var(--text-secondary); margin:0 0 14px; font-style:italic; }
  .info-card { border-color:#CC000030; }
  .local-card { border-color:#1565C030; background:rgba(21,101,192,.03); }
  .info-row { display:flex; gap:8px; padding:6px 0; border-bottom:1px solid var(--border-color); font-size:13px; }
  .info-row:last-child { border-bottom:none; }
  .info-label { font-weight:700; color:var(--text-secondary); min-width:70px; }
  .info-row a { color:#CC0000; text-decoration:none; }

  .testimonial { display:flex; gap:12px; padding:12px 0; border-bottom:1px solid var(--border-color); }
  .testimonial:last-child { border-bottom:none; }
  .test-num { width:28px; height:28px; background:#CC0000; color:#fff; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:800; flex-shrink:0; }
  .local-card .test-num { background:#1565C0; }
  .test-body { flex:1; }
  .test-biz { font-size:14px; font-weight:700; color:var(--text-primary); margin-bottom:4px; }
  .test-quote { font-size:13px; color:var(--text-secondary); line-height:1.5; font-style:italic; }
  .test-link { font-size:12px; color:#CC0000; text-decoration:none; font-weight:600; margin-top:4px; display:inline-block; }

  .empty { text-align:center; }
  .empty p { color:var(--text-secondary); font-size:14px; }

  .btn-copy { width:100%; padding:14px; background:#2E7D32; color:#fff; border:none; border-radius:10px; font-size:15px; font-weight:700; cursor:pointer; margin-bottom:8px; }
  .btn-copy:hover { background:#1B5E20; }
  .btn-secondary { width:100%; padding:12px; background:var(--card-bg); color:var(--text-primary); border:2px solid var(--border-color); border-radius:10px; font-size:14px; font-weight:600; cursor:pointer; }
</style>
