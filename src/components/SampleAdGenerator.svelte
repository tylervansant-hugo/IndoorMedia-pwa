<script>
  import { user } from '../lib/stores.js';
  import { onMount } from 'svelte';

  let step = 'business'; // business, offers, preview
  let businessName = '';
  let businessPhone = '';
  let businessAddress = '';
  let businessCategory = '';
  let businessWebsite = '';
  let businessLogo = null; // future: upload
  
  let offers = [{ text: '', details: '' }];
  let disclaimer = 'Must present coupon. Not valid with other offers. Limit one per visit.';
  let expirationDate = '';
  
  let adSize = 'single'; // single or double
  let selectedStore = '';
  let nearbyStores = [];
  let adColor = '#CC0000'; // default red theme
  let accentColor = '#FFD700'; // gold/yellow for offers

  // Color presets
  const colorPresets = [
    { name: 'Classic Red', primary: '#CC0000', accent: '#FFD700' },
    { name: 'Blue', primary: '#1a237e', accent: '#64B5F6' },
    { name: 'Green', primary: '#2E7D32', accent: '#FFD700' },
    { name: 'Purple', primary: '#6A0DAD', accent: '#E1BEE7' },
    { name: 'Black', primary: '#1a1a1a', accent: '#FF6B35' },
    { name: 'Teal', primary: '#00796B', accent: '#FFFFFF' },
  ];

  // Load stores for dropdown
  onMount(async () => {
    try {
      const res = await fetch(import.meta.env.BASE_URL + 'data/stores.json');
      const allStores = await res.json();
      nearbyStores = allStores.slice(0, 100).map(s => ({
        id: s.StoreName,
        label: `${s.GroceryChain} - ${s.City}, ${s.State} (${s.StoreName})`,
        chain: s.GroceryChain
      }));
    } catch {}

    // Set default expiration 3 months from now
    const exp = new Date();
    exp.setMonth(exp.getMonth() + 3);
    expirationDate = exp.toISOString().slice(0, 10);
  });

  // Search businesses using Google Places (reuses prospect search)
  let searchResults = [];
  let searching = false;

  async function searchBusiness() {
    if (!businessName.trim() || businessName.length < 3) return;
    searching = true;
    try {
      const apiKey = import.meta.env.VITE_GOOGLE_PLACES_API_KEY || 'AIzaSyBNR8M1VG5DccJmK6ZzJOam9mF8jOCEEqM';
      const res = await fetch('https://places.googleapis.com/v1/places:searchText', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Goog-Api-Key': apiKey,
          'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.primaryTypeDisplayName'
        },
        body: JSON.stringify({ textQuery: businessName, maxResultCount: 5 })
      });
      const data = await res.json();
      searchResults = (data.places || []).map(p => ({
        name: p.displayName?.text || '',
        address: p.formattedAddress || '',
        phone: p.nationalPhoneNumber || '',
        website: p.websiteUri || '',
        category: p.primaryTypeDisplayName?.text || ''
      }));
    } catch { searchResults = []; }
    searching = false;
  }

  function selectBusiness(biz) {
    businessName = biz.name;
    businessPhone = biz.phone;
    businessAddress = biz.address;
    businessCategory = biz.category;
    businessWebsite = biz.website;
    searchResults = [];
  }

  function addOffer() {
    if (offers.length < 6) {
      offers = [...offers, { text: '', details: '' }];
    }
  }

  function removeOffer(idx) {
    offers = offers.filter((_, i) => i !== idx);
  }

  function goToOffers() {
    if (!businessName.trim()) return alert('Please enter a business name');
    step = 'offers';
  }

  function goToPreview() {
    if (!offers.some(o => o.text.trim())) return alert('Please add at least one offer');
    step = 'preview';
  }

  function generateTrackingCode() {
    const store = selectedStore ? selectedStore.slice(0, 6).toUpperCase() : 'STORE';
    const rep = ($user?.name || 'REP').split(' ').map(w => w[0]).join('').toUpperCase();
    const month = new Date().toLocaleDateString('en-US', { month: 'short' }).toUpperCase().slice(0, 1);
    return `${store}${rep}${month}`;
  }

  // Download as image using Canvas API
  async function downloadAd() {
    const canvas = document.createElement('canvas');
    const dpi = 3; // 3x for print quality
    
    // Single: 2.75" x 1.75" | Double: 2.75" x 3.6"
    const widthInches = 2.75;
    const heightInches = adSize === 'single' ? 1.75 : 3.6;
    canvas.width = Math.round(widthInches * 96 * dpi);
    canvas.height = Math.round(heightInches * 96 * dpi);
    
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    const s = dpi; // scale factor

    // Background
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, w, h);

    // Border
    ctx.strokeStyle = adColor;
    ctx.lineWidth = 4 * s;
    ctx.strokeRect(4 * s, 4 * s, w - 8 * s, h - 8 * s);
    
    // Inner border
    ctx.strokeStyle = adColor;
    ctx.lineWidth = 1 * s;
    ctx.strokeRect(8 * s, 8 * s, w - 16 * s, h - 16 * s);

    // Header bar with business name
    const headerH = adSize === 'single' ? 38 * s : 48 * s;
    ctx.fillStyle = adColor;
    ctx.fillRect(8 * s, 8 * s, w - 16 * s, headerH);
    
    ctx.fillStyle = '#FFFFFF';
    ctx.font = `bold ${(adSize === 'single' ? 16 : 20) * s}px Arial, Helvetica, sans-serif`;
    ctx.textAlign = 'center';
    ctx.fillText(businessName.toUpperCase(), w / 2, 8 * s + headerH * 0.65);

    // Contact info bar
    const contactY = 8 * s + headerH + 2 * s;
    const contactH = 14 * s;
    ctx.fillStyle = '#f5f5f5';
    ctx.fillRect(8 * s, contactY, w - 16 * s, contactH);
    ctx.fillStyle = '#333';
    ctx.font = `${7 * s}px Arial`;
    ctx.textAlign = 'center';
    const contactText = [businessAddress, businessPhone].filter(Boolean).join(' • ');
    ctx.fillText(contactText, w / 2, contactY + contactH * 0.72);

    // Offers section
    let offerY = contactY + contactH + 8 * s;
    const validOffers = offers.filter(o => o.text.trim());
    
    if (adSize === 'single') {
      // Single: offers side by side or stacked tight
      const offerW = validOffers.length > 1 ? (w - 24 * s) / Math.min(validOffers.length, 3) : w - 24 * s;
      const offerH = 45 * s;
      
      validOffers.slice(0, 3).forEach((offer, i) => {
        const ox = 12 * s + i * offerW;
        
        // Offer box
        ctx.fillStyle = adColor + '15';
        ctx.fillRect(ox, offerY, offerW - 4 * s, offerH);
        ctx.strokeStyle = adColor;
        ctx.lineWidth = 1 * s;
        ctx.strokeRect(ox, offerY, offerW - 4 * s, offerH);
        
        // Offer text (big)
        ctx.fillStyle = adColor;
        ctx.font = `bold ${14 * s}px Arial`;
        ctx.textAlign = 'center';
        ctx.fillText(offer.text.toUpperCase(), ox + (offerW - 4 * s) / 2, offerY + 20 * s);
        
        // Offer details (smaller)
        if (offer.details) {
          ctx.fillStyle = '#333';
          ctx.font = `${7 * s}px Arial`;
          ctx.fillText(offer.details, ox + (offerW - 4 * s) / 2, offerY + 35 * s);
        }
      });
      offerY += offerH + 6 * s;
    } else {
      // Double: offers stacked with more room
      const offerH = 40 * s;
      
      // Two-column layout for offers
      const cols = Math.min(validOffers.length, 2);
      const colW = (w - 24 * s) / cols;
      
      validOffers.forEach((offer, i) => {
        const col = i % 2;
        const row = Math.floor(i / 2);
        const ox = 12 * s + col * colW;
        const oy = offerY + row * (offerH + 6 * s);
        
        // Offer box with accent background
        ctx.fillStyle = accentColor + '30';
        ctx.fillRect(ox, oy, colW - 4 * s, offerH);
        ctx.strokeStyle = adColor;
        ctx.lineWidth = 1.5 * s;
        ctx.strokeRect(ox, oy, colW - 4 * s, offerH);
        
        // Offer text
        ctx.fillStyle = adColor;
        ctx.font = `bold ${16 * s}px Arial`;
        ctx.textAlign = 'center';
        ctx.fillText(offer.text.toUpperCase(), ox + (colW - 4 * s) / 2, oy + 18 * s);
        
        // Details
        if (offer.details) {
          ctx.fillStyle = '#333';
          ctx.font = `${8 * s}px Arial`;
          ctx.fillText(offer.details, ox + (colW - 4 * s) / 2, oy + 32 * s);
        }
      });
      
      const rows = Math.ceil(validOffers.length / 2);
      offerY += rows * (offerH + 6 * s) + 4 * s;
    }

    // Disclaimer / fine print
    ctx.fillStyle = '#666';
    ctx.font = `${5.5 * s}px Arial`;
    ctx.textAlign = 'center';
    const disclaimerText = disclaimer + (expirationDate ? ` Exp: ${new Date(expirationDate + 'T12:00:00').toLocaleDateString('en-US', { month: '2-digit', day: '2-digit', year: '2-digit' })}` : '');
    
    // Word wrap disclaimer
    const maxW = w - 30 * s;
    const words = disclaimerText.split(' ');
    let line = '';
    let lineY = Math.min(offerY + 4 * s, h - 22 * s);
    
    for (const word of words) {
      const test = line + word + ' ';
      if (ctx.measureText(test).width > maxW && line) {
        ctx.fillText(line.trim(), w / 2, lineY);
        line = word + ' ';
        lineY += 8 * s;
      } else {
        line = test;
      }
    }
    if (line.trim()) ctx.fillText(line.trim(), w / 2, lineY);

    // Tracking code (rotated on left edge)
    const code = generateTrackingCode();
    ctx.save();
    ctx.translate(14 * s, h / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillStyle = '#999';
    ctx.font = `${5 * s}px Arial`;
    ctx.textAlign = 'center';
    ctx.fillText(code, 0, 0);
    ctx.restore();

    // Download
    const link = document.createElement('a');
    link.download = `${businessName.replace(/\s+/g, '_')}_${adSize}_ad.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  }
</script>

<div class="ad-generator">
  <button class="back-btn" on:click={() => { if (step === 'business') { /* parent handles */ } else if (step === 'offers') step = 'business'; else step = 'offers'; }}>
    ← {step === 'business' ? 'Back' : step === 'offers' ? 'Edit Business' : 'Edit Offers'}
  </button>

  {#if step === 'business'}
    <h2>📋 Business Info</h2>
    <p class="step-hint">Search for the business or enter details manually</p>
    
    <div class="form-group">
      <label>Business Name *</label>
      <div class="search-row">
        <input type="text" bind:value={businessName} placeholder="e.g. Joe's Pizza" on:input={() => { if (businessName.length >= 3) searchBusiness(); }} />
        {#if searching}<span class="spinner">🔍</span>{/if}
      </div>
      
      {#if searchResults.length > 0}
        <div class="search-dropdown">
          {#each searchResults as biz}
            <button class="search-result" on:click={() => selectBusiness(biz)}>
              <strong>{biz.name}</strong>
              <span class="result-detail">{biz.address} {biz.phone ? '• ' + biz.phone : ''}</span>
            </button>
          {/each}
        </div>
      {/if}
    </div>

    <div class="form-group">
      <label>Phone</label>
      <input type="tel" bind:value={businessPhone} placeholder="(555) 123-4567" />
    </div>

    <div class="form-group">
      <label>Address</label>
      <input type="text" bind:value={businessAddress} placeholder="123 Main St, City, State" />
    </div>

    <div class="form-group">
      <label>Category</label>
      <input type="text" bind:value={businessCategory} placeholder="Restaurant, Auto Repair, Salon..." />
    </div>

    <div class="form-row">
      <div class="form-group half">
        <label>Ad Size</label>
        <select bind:value={adSize}>
          <option value="single">Single (2.75" × 1.75")</option>
          <option value="double">Double (2.75" × 3.6")</option>
        </select>
      </div>
      <div class="form-group half">
        <label>Store</label>
        <select bind:value={selectedStore}>
          <option value="">Select store...</option>
          {#each nearbyStores as store}
            <option value={store.id}>{store.label}</option>
          {/each}
        </select>
      </div>
    </div>

    <button class="next-btn" on:click={goToOffers}>Next: Add Offers →</button>

  {:else if step === 'offers'}
    <h2>🎯 Offers & Coupons</h2>
    <p class="step-hint">Add the offers that will appear on the ad</p>

    {#each offers as offer, i}
      <div class="offer-card">
        <div class="offer-header">
          <span class="offer-num">Offer {i + 1}</span>
          {#if offers.length > 1}
            <button class="remove-btn" on:click={() => removeOffer(i)}>✕</button>
          {/if}
        </div>
        <div class="form-group">
          <label>Offer Text *</label>
          <input type="text" bind:value={offer.text} placeholder="e.g. $5 OFF any purchase of $25+" />
        </div>
        <div class="form-group">
          <label>Details (optional)</label>
          <input type="text" bind:value={offer.details} placeholder="e.g. Any purchase of $25 or more" />
        </div>
      </div>
    {/each}

    {#if offers.length < 6}
      <button class="add-offer-btn" on:click={addOffer}>+ Add Offer</button>
    {/if}

    <div class="form-group">
      <label>Disclaimers / Fine Print</label>
      <textarea bind:value={disclaimer} rows="2" placeholder="Must present coupon. Not valid with other offers."></textarea>
    </div>

    <div class="form-group">
      <label>Expiration Date</label>
      <input type="date" bind:value={expirationDate} />
    </div>

    <h3>🎨 Ad Color</h3>
    <div class="color-presets">
      {#each colorPresets as preset}
        <button class="color-swatch" class:active={adColor === preset.primary} 
                style="background: {preset.primary};" 
                on:click={() => { adColor = preset.primary; accentColor = preset.accent; }}
                title={preset.name}>
          {adColor === preset.primary ? '✓' : ''}
        </button>
      {/each}
    </div>

    <button class="next-btn" on:click={goToPreview}>Preview Ad →</button>

  {:else if step === 'preview'}
    <h2>👁️ Preview</h2>
    
    <div class="preview-wrapper">
      <div class="ad-preview" class:single={adSize === 'single'} class:double={adSize === 'double'} style="--ad-color: {adColor}; --accent-color: {accentColor};">
        <div class="ad-border">
          <div class="ad-header" style="background: {adColor};">
            <span class="ad-biz-name">{businessName.toUpperCase()}</span>
          </div>
          
          <div class="ad-contact">
            {businessAddress}{businessAddress && businessPhone ? ' • ' : ''}{businessPhone}
          </div>

          <div class="ad-offers" class:multi={offers.filter(o => o.text.trim()).length > 1}>
            {#each offers.filter(o => o.text.trim()) as offer}
              <div class="ad-offer-box" style="border-color: {adColor};">
                <div class="ad-offer-text" style="color: {adColor};">{offer.text.toUpperCase()}</div>
                {#if offer.details}
                  <div class="ad-offer-detail">{offer.details}</div>
                {/if}
              </div>
            {/each}
          </div>

          <div class="ad-disclaimer">
            {disclaimer}{expirationDate ? ` Exp: ${new Date(expirationDate + 'T12:00:00').toLocaleDateString('en-US', { month: '2-digit', day: '2-digit', year: '2-digit' })}` : ''}
          </div>
          
          <div class="ad-tracking">{generateTrackingCode()}</div>
        </div>
      </div>
    </div>

    <p class="size-label">{adSize === 'single' ? 'Single' : 'Double'} Size — {adSize === 'single' ? '2.75" × 1.75"' : '2.75" × 3.6"'}</p>
    {#if selectedStore}<p class="store-label">Store: {selectedStore}</p>{/if}

    <div class="preview-actions">
      <button class="download-btn" on:click={downloadAd}>📥 Download Ad Image</button>
      <button class="next-btn" on:click={() => step = 'offers'}>← Edit</button>
    </div>
  {/if}
</div>

<style>
  .ad-generator { padding: 0; }
  .back-btn { background: none; border: none; color: var(--text-secondary); font-size: 14px; cursor: pointer; padding: 8px 0; margin-bottom: 8px; }
  .step-hint { font-size: 13px; color: var(--text-secondary); margin: -4px 0 16px; }
  
  .form-group { margin-bottom: 14px; }
  .form-group label { display: block; font-size: 12px; font-weight: 700; color: var(--text-secondary); margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
  .form-group input, .form-group select, .form-group textarea { width: 100%; padding: 10px 12px; border: 2px solid var(--border-color); border-radius: 8px; font-size: 14px; background: var(--card-bg); color: var(--text-primary); box-sizing: border-box; }
  .form-group textarea { resize: vertical; font-family: inherit; }
  .form-group input:focus, .form-group select:focus { border-color: #CC0000; outline: none; }
  
  .form-row { display: flex; gap: 12px; }
  .form-group.half { flex: 1; }
  
  .search-row { position: relative; }
  .spinner { position: absolute; right: 12px; top: 50%; transform: translateY(-50%); }
  .search-dropdown { background: var(--card-bg); border: 2px solid var(--border-color); border-radius: 8px; margin-top: 4px; overflow: hidden; }
  .search-result { display: block; width: 100%; padding: 10px 12px; border: none; border-bottom: 1px solid var(--border-color); background: transparent; text-align: left; cursor: pointer; color: var(--text-primary); }
  .search-result:hover { background: rgba(204, 0, 0, 0.05); }
  .search-result:last-child { border-bottom: none; }
  .result-detail { display: block; font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
  
  .offer-card { background: var(--card-bg); border: 2px solid var(--border-color); border-radius: 10px; padding: 14px; margin-bottom: 12px; }
  .offer-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
  .offer-num { font-size: 13px; font-weight: 700; color: #CC0000; }
  .remove-btn { background: none; border: none; color: var(--text-secondary); font-size: 18px; cursor: pointer; padding: 0 4px; }
  
  .add-offer-btn { width: 100%; padding: 10px; border: 2px dashed var(--border-color); border-radius: 8px; background: transparent; color: #CC0000; font-size: 14px; font-weight: 600; cursor: pointer; margin-bottom: 16px; }
  .add-offer-btn:hover { border-color: #CC0000; }
  
  .color-presets { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
  .color-swatch { width: 40px; height: 40px; border-radius: 50%; border: 3px solid transparent; cursor: pointer; font-size: 18px; color: white; display: flex; align-items: center; justify-content: center; }
  .color-swatch.active { border-color: var(--text-primary); box-shadow: 0 0 0 2px var(--card-bg), 0 0 0 4px var(--text-primary); }
  
  .next-btn { width: 100%; padding: 12px; background: #CC0000; color: white; border: none; border-radius: 8px; font-size: 15px; font-weight: 700; cursor: pointer; margin-top: 8px; }
  .next-btn:hover { background: #aa0000; }
  
  .download-btn { width: 100%; padding: 14px; background: #2E7D32; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: 700; cursor: pointer; margin-bottom: 8px; }
  .download-btn:hover { background: #1B5E20; }
  
  /* Ad Preview */
  .preview-wrapper { display: flex; justify-content: center; margin: 16px 0; }
  
  .ad-preview { background: white; color: #000; overflow: hidden; }
  .ad-preview.single { width: 275px; height: 175px; }
  .ad-preview.double { width: 275px; height: 360px; }
  
  .ad-border { border: 3px solid var(--ad-color); height: 100%; display: flex; flex-direction: column; position: relative; }
  
  .ad-header { padding: 6px 8px; text-align: center; }
  .ad-biz-name { color: white; font-size: 16px; font-weight: 900; letter-spacing: 1px; }
  .double .ad-biz-name { font-size: 20px; }
  
  .ad-contact { text-align: center; font-size: 8px; color: #333; padding: 3px 6px; background: #f5f5f5; }
  .double .ad-contact { font-size: 9px; padding: 4px 6px; }
  
  .ad-offers { flex: 1; display: flex; flex-wrap: wrap; gap: 4px; padding: 6px; align-content: flex-start; }
  .ad-offers.multi { }
  
  .ad-offer-box { flex: 1; min-width: 45%; border: 1.5px solid; border-radius: 4px; padding: 6px 4px; text-align: center; background: rgba(204, 0, 0, 0.04); }
  .single .ad-offer-box { padding: 4px 3px; }
  
  .ad-offer-text { font-size: 13px; font-weight: 900; line-height: 1.2; }
  .single .ad-offer-text { font-size: 11px; }
  .double .ad-offer-text { font-size: 15px; }
  
  .ad-offer-detail { font-size: 7px; color: #555; margin-top: 2px; }
  .double .ad-offer-detail { font-size: 8px; }
  
  .ad-disclaimer { font-size: 6px; color: #666; text-align: center; padding: 3px 8px; line-height: 1.3; }
  .double .ad-disclaimer { font-size: 7px; padding: 4px 10px; }
  
  .ad-tracking { position: absolute; left: 2px; top: 50%; transform: rotate(-90deg) translateX(-50%); font-size: 5px; color: #999; transform-origin: left center; }
  
  .size-label { text-align: center; font-size: 13px; color: var(--text-secondary); font-weight: 600; }
  .store-label { text-align: center; font-size: 12px; color: var(--text-tertiary); }
  
  .preview-actions { margin-top: 12px; }
</style>
