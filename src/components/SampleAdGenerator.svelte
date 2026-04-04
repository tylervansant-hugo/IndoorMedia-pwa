<script>
  import { user } from '../lib/stores.js';
  import { onMount } from 'svelte';

  let step = 'business'; // business, offers, preview
  let businessName = '';
  let businessPhone = '';
  let businessAddress = '';
  let businessCategory = '';
  let businessWebsite = '';
  
  let offers = [{ text: '', details: '' }];
  let disclaimer = 'Must present coupon. Not valid with other offers. Limit one per visit.';
  let expirationDate = '';
  
  let adSize = 'single'; // single or double
  let selectedStore = '';
  let allStores = [];
  let storeSearch = '';
  let storeResults = [];
  let showStoreDropdown = false;
  
  // Color themes matching real ads
  let adTheme = 'red'; // red, green, blue, black, orange
  const themes = {
    red:    { bg: '#CC0000', accent: '#FFD700', text: '#FFFFFF', offerBg: '#FFF5F5', offerText: '#CC0000' },
    green:  { bg: '#2E7D32', accent: '#FFD700', text: '#FFFFFF', offerBg: '#F1F8E9', offerText: '#2E7D32' },
    blue:   { bg: '#1565C0', accent: '#FFD700', text: '#FFFFFF', offerBg: '#E3F2FD', offerText: '#1565C0' },
    black:  { bg: '#1a1a1a', accent: '#FF6B35', text: '#FFFFFF', offerBg: '#F5F5F5', offerText: '#1a1a1a' },
    orange: { bg: '#E65100', accent: '#FFFFFF', text: '#FFFFFF', offerBg: '#FFF3E0', offerText: '#E65100' },
    teal:   { bg: '#00695C', accent: '#FFD54F', text: '#FFFFFF', offerBg: '#E0F2F1', offerText: '#00695C' },
  };

  // Category to stock photo mapping (Unsplash)
  const categoryImages = {
    'restaurant': 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=400&h=250&fit=crop',
    'pizza': 'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=400&h=250&fit=crop',
    'mexican': 'https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=400&h=250&fit=crop',
    'sushi': 'https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=400&h=250&fit=crop',
    'burger': 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400&h=250&fit=crop',
    'coffee': 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=400&h=250&fit=crop',
    'salon': 'https://images.unsplash.com/photo-1560066984-138dadb4c035?w=400&h=250&fit=crop',
    'barber': 'https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=400&h=250&fit=crop',
    'auto': 'https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?w=400&h=250&fit=crop',
    'dental': 'https://images.unsplash.com/photo-1606811841689-23dfddce3e95?w=400&h=250&fit=crop',
    'gym': 'https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=400&h=250&fit=crop',
    'vet': 'https://images.unsplash.com/photo-1548199973-03cce0bbc87b?w=400&h=250&fit=crop',
    'chinese': 'https://images.unsplash.com/photo-1585032226651-759b368d7246?w=400&h=250&fit=crop',
    'thai': 'https://images.unsplash.com/photo-1562565652-a0d8f0c59eb4?w=400&h=250&fit=crop',
    'indian': 'https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=400&h=250&fit=crop',
    'bakery': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&h=250&fit=crop',
    'default': 'https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=400&h=250&fit=crop',
  };

  let customImageUrl = '';

  function getCategoryImage() {
    if (customImageUrl) return customImageUrl;
    const cat = (businessCategory || '').toLowerCase();
    for (const [key, url] of Object.entries(categoryImages)) {
      if (cat.includes(key)) return url;
    }
    return categoryImages.default;
  }

  function searchStores() {
    if (!storeSearch.trim() || storeSearch.length < 2) {
      storeResults = [];
      showStoreDropdown = false;
      return;
    }
    const term = storeSearch.toLowerCase();
    storeResults = allStores.filter(s =>
      (s.StoreName && s.StoreName.toLowerCase().includes(term)) ||
      (s.GroceryChain && s.GroceryChain.toLowerCase().includes(term)) ||
      (s.City && s.City.toLowerCase().includes(term)) ||
      (s.PostalCode && s.PostalCode.includes(term)) ||
      (s.Address && s.Address.toLowerCase().includes(term)) ||
      (s.State && s.State.toLowerCase().includes(term))
    ).slice(0, 10).map(s => ({
      id: s.StoreName,
      label: `${s.GroceryChain} — ${s.City}, ${s.State} (${s.StoreName})`,
      address: s.Address || '',
      zip: s.PostalCode || ''
    }));
    showStoreDropdown = storeResults.length > 0;
  }

  function selectStore(store) {
    selectedStore = store.id;
    storeSearch = store.label;
    showStoreDropdown = false;
    storeResults = [];
  }

  // Search businesses using Google Places
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

  function addOffer() { if (offers.length < 6) offers = [...offers, { text: '', details: '' }]; }
  function removeOffer(idx) { offers = offers.filter((_, i) => i !== idx); }
  function goToOffers() { if (!businessName.trim()) return alert('Please enter a business name'); step = 'offers'; }
  function goToPreview() { if (!offers.some(o => o.text.trim())) return alert('Please add at least one offer'); step = 'preview'; }

  function generateTrackingCode() {
    const store = selectedStore ? selectedStore.replace(/[^A-Z0-9]/gi, '').slice(0, 6).toUpperCase() : 'STORE';
    const rep = ($user?.name || 'REP').split(' ').map(w => w[0]).join('').toUpperCase();
    return `${store}${rep}`;
  }

  // Download using canvas with proper ad design
  async function downloadAd() {
    const t = themes[adTheme];
    const dpi = 3;
    const wIn = 2.75;
    const hIn = adSize === 'single' ? 1.75 : 3.6;
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(wIn * 96 * dpi);
    canvas.height = Math.round(hIn * 96 * dpi);
    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height, s = dpi;

    // White background
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, w, h);

    // Try to load category image
    let img = null;
    try {
      img = await new Promise((resolve, reject) => {
        const i = new Image();
        i.crossOrigin = 'anonymous';
        i.onload = () => resolve(i);
        i.onerror = reject;
        i.src = getCategoryImage();
      });
    } catch { img = null; }

    const validOffers = offers.filter(o => o.text.trim());

    if (adSize === 'double') {
      // DOUBLE: Image top half, offers bottom
      // Outer border
      ctx.strokeStyle = t.bg;
      ctx.lineWidth = 4 * s;
      ctx.strokeRect(2*s, 2*s, w-4*s, h-4*s);

      // Image area (top ~45%)
      const imgH = Math.round(h * 0.42);
      if (img) {
        const aspect = img.width / img.height;
        const drawW = w - 8*s;
        const drawH = imgH;
        ctx.save();
        ctx.beginPath();
        ctx.rect(4*s, 4*s, drawW, drawH);
        ctx.clip();
        ctx.drawImage(img, 4*s, 4*s, drawW, drawH);
        // Dark overlay for text
        ctx.fillStyle = 'rgba(0,0,0,0.45)';
        ctx.fillRect(4*s, 4*s, drawW, drawH);
        ctx.restore();
      } else {
        ctx.fillStyle = t.bg;
        ctx.fillRect(4*s, 4*s, w-8*s, imgH);
      }

      // Business name over image
      ctx.fillStyle = '#FFFFFF';
      ctx.font = `900 ${22*s}px Arial, Helvetica`;
      ctx.textAlign = 'center';
      ctx.fillText(businessName.toUpperCase(), w/2, 4*s + imgH*0.45);

      // Contact info over image
      ctx.font = `bold ${8*s}px Arial`;
      ctx.fillStyle = t.accent;
      const contact = [businessAddress.split(',')[0], businessPhone].filter(Boolean).join(' • ');
      ctx.fillText(contact, w/2, 4*s + imgH*0.7);

      // Offers section
      let oy = 4*s + imgH + 8*s;
      const offerAreaH = h - oy - 30*s;
      const cols = Math.min(validOffers.length, 2);
      const colW = (w - 20*s) / cols;
      const rowH = Math.min(offerAreaH / Math.ceil(validOffers.length / 2), 55*s);

      validOffers.forEach((offer, i) => {
        const col = i % 2;
        const row = Math.floor(i / 2);
        const ox = 10*s + col * colW;
        const ooy = oy + row * (rowH + 4*s);

        // Offer box
        ctx.fillStyle = t.offerBg;
        ctx.fillRect(ox, ooy, colW - 4*s, rowH);
        ctx.strokeStyle = t.bg;
        ctx.lineWidth = 1.5*s;
        ctx.strokeRect(ox, ooy, colW - 4*s, rowH);

        // Offer text BIG
        ctx.fillStyle = t.offerText;
        ctx.font = `900 ${16*s}px Arial`;
        ctx.textAlign = 'center';
        ctx.fillText(offer.text.toUpperCase(), ox + (colW-4*s)/2, ooy + rowH*0.45);

        // Details smaller
        if (offer.details) {
          ctx.fillStyle = '#555';
          ctx.font = `${7*s}px Arial`;
          ctx.fillText(offer.details, ox + (colW-4*s)/2, ooy + rowH*0.75);
        }
      });

      // Disclaimer
      ctx.fillStyle = '#777';
      ctx.font = `${5*s}px Arial`;
      ctx.textAlign = 'center';
      const expStr = expirationDate ? ` Exp: ${new Date(expirationDate+'T12:00:00').toLocaleDateString('en-US',{month:'2-digit',day:'2-digit',year:'2-digit'})}` : '';
      ctx.fillText(disclaimer + expStr, w/2, h - 10*s);

      // Tracking code
      ctx.save();
      ctx.translate(10*s, h/2);
      ctx.rotate(-Math.PI/2);
      ctx.fillStyle = '#bbb';
      ctx.font = `${5*s}px Arial`;
      ctx.fillText(generateTrackingCode(), 0, 0);
      ctx.restore();

    } else {
      // SINGLE: Compact layout
      ctx.strokeStyle = t.bg;
      ctx.lineWidth = 3*s;
      ctx.strokeRect(2*s, 2*s, w-4*s, h-4*s);
      // Inner dashed border
      ctx.setLineDash([4*s, 3*s]);
      ctx.strokeStyle = t.bg + '60';
      ctx.lineWidth = 1*s;
      ctx.strokeRect(6*s, 6*s, w-12*s, h-12*s);
      ctx.setLineDash([]);

      // Left section: image + business name (~40% width)
      const leftW = Math.round(w * 0.38);
      if (img) {
        ctx.save();
        ctx.beginPath();
        ctx.rect(8*s, 8*s, leftW - 4*s, h - 16*s);
        ctx.clip();
        ctx.drawImage(img, 8*s, 8*s, leftW - 4*s, h - 16*s);
        ctx.fillStyle = 'rgba(0,0,0,0.5)';
        ctx.fillRect(8*s, 8*s, leftW - 4*s, h - 16*s);
        ctx.restore();
      } else {
        ctx.fillStyle = t.bg;
        ctx.fillRect(8*s, 8*s, leftW - 4*s, h - 16*s);
      }

      // Business name on left
      ctx.fillStyle = '#FFFFFF';
      ctx.textAlign = 'center';
      ctx.font = `900 ${11*s}px Arial`;
      const nameX = 8*s + (leftW-4*s)/2;
      // Word wrap business name
      const nameWords = businessName.toUpperCase().split(' ');
      let nameLine = '';
      let nameY = h * 0.35;
      const nameMaxW = leftW - 16*s;
      for (const word of nameWords) {
        const test = nameLine + word + ' ';
        if (ctx.measureText(test).width > nameMaxW && nameLine) {
          ctx.fillText(nameLine.trim(), nameX, nameY);
          nameLine = word + ' ';
          nameY += 14*s;
        } else {
          nameLine = test;
        }
      }
      if (nameLine.trim()) ctx.fillText(nameLine.trim(), nameX, nameY);

      // Phone under name
      if (businessPhone) {
        ctx.font = `bold ${7*s}px Arial`;
        ctx.fillStyle = t.accent;
        ctx.fillText(businessPhone, nameX, nameY + 14*s);
      }

      // Right section: offers (~60%)
      const rightX = leftW + 4*s;
      const rightW = w - rightX - 8*s;
      const topPad = 12*s;
      
      // Contact bar at top right
      ctx.fillStyle = t.bg;
      ctx.fillRect(rightX, 8*s, rightW, 14*s);
      ctx.fillStyle = '#FFF';
      ctx.font = `bold ${6*s}px Arial`;
      ctx.textAlign = 'center';
      const shortAddr = businessAddress.split(',')[0] || '';
      ctx.fillText(shortAddr, rightX + rightW/2, 8*s + 10*s);

      // Offers
      let offerY = 8*s + 14*s + 4*s;
      const offerH = Math.min((h - offerY - 24*s) / validOffers.length, 32*s);

      validOffers.forEach((offer, i) => {
        const oy = offerY + i * (offerH + 3*s);
        // Offer background
        ctx.fillStyle = t.offerBg;
        ctx.fillRect(rightX, oy, rightW, offerH);
        ctx.strokeStyle = t.bg;
        ctx.lineWidth = 1*s;
        ctx.strokeRect(rightX, oy, rightW, offerH);

        // Offer text
        ctx.fillStyle = t.offerText;
        ctx.font = `900 ${12*s}px Arial`;
        ctx.textAlign = 'center';
        ctx.fillText(offer.text.toUpperCase(), rightX + rightW/2, oy + offerH*0.5);

        if (offer.details) {
          ctx.fillStyle = '#666';
          ctx.font = `${6*s}px Arial`;
          ctx.fillText(offer.details, rightX + rightW/2, oy + offerH*0.82);
        }
      });

      // Disclaimer at bottom
      ctx.fillStyle = '#888';
      ctx.font = `${4.5*s}px Arial`;
      ctx.textAlign = 'center';
      const expStr = expirationDate ? ` Exp: ${new Date(expirationDate+'T12:00:00').toLocaleDateString('en-US',{month:'2-digit',day:'2-digit',year:'2-digit'})}` : '';
      ctx.fillText((disclaimer + expStr).slice(0, 80), w/2, h - 8*s);

      // Tracking code
      ctx.save();
      ctx.translate(w - 8*s, h/2);
      ctx.rotate(Math.PI/2);
      ctx.fillStyle = '#bbb';
      ctx.font = `${4*s}px Arial`;
      ctx.fillText(generateTrackingCode(), 0, 0);
      ctx.restore();
    }

    const link = document.createElement('a');
    link.download = `${businessName.replace(/\s+/g, '_')}_${adSize}_sample.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  }

  onMount(async () => {
    try {
      const res = await fetch(import.meta.env.BASE_URL + 'data/stores.json');
      allStores = await res.json();
    } catch { allStores = []; }
    const exp = new Date();
    exp.setMonth(exp.getMonth() + 3);
    expirationDate = exp.toISOString().slice(0, 10);
  });
</script>

<div class="ad-generator">
  <button class="back-btn" on:click={() => { if (step === 'offers') step = 'business'; else if (step === 'preview') step = 'offers'; }}>
    ← {step === 'business' ? 'Back' : step === 'offers' ? 'Edit Business' : 'Edit Offers'}
  </button>

  {#if step === 'business'}
    <h2>📋 Business Info</h2>
    <p class="hint">Search for the business or enter manually</p>
    
    <div class="field">
      <label>Business Name *</label>
      <div style="position:relative;">
        <input type="text" bind:value={businessName} placeholder="e.g. Joe's Pizza" on:input={() => { if (businessName.length >= 3) searchBusiness(); }} />
        {#if searching}<span class="searching">🔍</span>{/if}
      </div>
      {#if searchResults.length > 0}
        <div class="dropdown">
          {#each searchResults as biz}
            <button class="dropdown-item" on:click={() => selectBusiness(biz)}>
              <strong>{biz.name}</strong>
              <span class="item-detail">{biz.address}</span>
            </button>
          {/each}
        </div>
      {/if}
    </div>

    <div class="field">
      <label>Phone</label>
      <input type="tel" bind:value={businessPhone} placeholder="(555) 123-4567" />
    </div>
    <div class="field">
      <label>Address</label>
      <input type="text" bind:value={businessAddress} placeholder="123 Main St, City, State" />
    </div>
    <div class="field">
      <label>Category</label>
      <input type="text" bind:value={businessCategory} placeholder="Restaurant, Auto Repair, Salon..." />
    </div>

    <div class="row">
      <div class="field half">
        <label>Ad Size</label>
        <select bind:value={adSize}>
          <option value="single">Single (2.75" × 1.75")</option>
          <option value="double">Double (2.75" × 3.6")</option>
        </select>
      </div>
      <div class="field half" style="position:relative;">
        <label>Store</label>
        <input type="text" bind:value={storeSearch} on:input={searchStores} on:focus={() => { if (storeSearch.length >= 2) searchStores(); }} placeholder="City, zip, store #..." autocomplete="off" />
        {#if showStoreDropdown}
          <div class="dropdown store-drop">
            {#each storeResults as store}
              <button class="dropdown-item" on:click={() => selectStore(store)}>
                <strong>{store.id}</strong>
                <span class="item-detail">{store.label}</span>
              </button>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <button class="primary-btn" on:click={goToOffers}>Next: Add Offers →</button>

  {:else if step === 'offers'}
    <h2>🎯 Offers & Coupons</h2>

    {#each offers as offer, i}
      <div class="offer-card">
        <div class="offer-top">
          <span class="offer-num">Offer {i + 1}</span>
          {#if offers.length > 1}<button class="x-btn" on:click={() => removeOffer(i)}>✕</button>{/if}
        </div>
        <div class="field"><label>Offer *</label><input type="text" bind:value={offer.text} placeholder="$5 OFF purchase of $25+" /></div>
        <div class="field"><label>Details</label><input type="text" bind:value={offer.details} placeholder="Any purchase of $25 or more" /></div>
      </div>
    {/each}

    {#if offers.length < 6}
      <button class="add-btn" on:click={addOffer}>+ Add Offer</button>
    {/if}

    <div class="field"><label>Disclaimers</label><textarea bind:value={disclaimer} rows="2"></textarea></div>
    <div class="field"><label>Expiration</label><input type="date" bind:value={expirationDate} /></div>

    <h3>🎨 Color Theme</h3>
    <div class="themes">
      {#each Object.entries(themes) as [key, t]}
        <button class="theme-btn" class:active={adTheme === key} style="background:{t.bg}; color:{t.accent};" on:click={() => adTheme = key}>
          {adTheme === key ? '✓' : ''}
        </button>
      {/each}
    </div>

    <div class="field">
      <label>Custom Image URL (optional)</label>
      <input type="url" bind:value={customImageUrl} placeholder="https://... (leave blank for auto)" />
    </div>

    <button class="primary-btn" on:click={goToPreview}>Preview Ad →</button>

  {:else if step === 'preview'}
    <h2>👁️ Ad Preview</h2>
    
    <div class="preview-wrap">
      {#if adSize === 'double'}
        <div class="ad double" style="--c:{themes[adTheme].bg}; --a:{themes[adTheme].accent}; --ot:{themes[adTheme].offerText}; --ob:{themes[adTheme].offerBg};">
          <div class="ad-img" style="background-image:url({getCategoryImage()});">
            <div class="ad-img-overlay">
              <h2 class="ad-name">{businessName.toUpperCase()}</h2>
              <p class="ad-contact-over">{[businessAddress.split(',')[0], businessPhone].filter(Boolean).join(' • ')}</p>
            </div>
          </div>
          <div class="ad-offers-area">
            {#each offers.filter(o => o.text.trim()) as offer}
              <div class="ad-offer">
                <div class="ad-offer-main">{offer.text.toUpperCase()}</div>
                {#if offer.details}<div class="ad-offer-sub">{offer.details}</div>{/if}
              </div>
            {/each}
          </div>
          <div class="ad-fine">{disclaimer}{expirationDate ? ` Exp: ${new Date(expirationDate+'T12:00:00').toLocaleDateString('en-US',{month:'2-digit',day:'2-digit',year:'2-digit'})}` : ''}</div>
          <div class="ad-code">{generateTrackingCode()}</div>
        </div>
      {:else}
        <div class="ad single" style="--c:{themes[adTheme].bg}; --a:{themes[adTheme].accent}; --ot:{themes[adTheme].offerText}; --ob:{themes[adTheme].offerBg};">
          <div class="ad-left" style="background-image:url({getCategoryImage()});">
            <div class="ad-left-overlay">
              <h3 class="ad-name-s">{businessName.toUpperCase()}</h3>
              {#if businessPhone}<p class="ad-phone-s">{businessPhone}</p>{/if}
            </div>
          </div>
          <div class="ad-right">
            <div class="ad-addr-bar">{businessAddress.split(',')[0] || ''}</div>
            <div class="ad-offers-s">
              {#each offers.filter(o => o.text.trim()) as offer}
                <div class="ad-offer-s">
                  <div class="ad-offer-main-s">{offer.text.toUpperCase()}</div>
                  {#if offer.details}<div class="ad-offer-sub-s">{offer.details}</div>{/if}
                </div>
              {/each}
            </div>
            <div class="ad-fine-s">{disclaimer.slice(0, 60)}{expirationDate ? ` Exp ${new Date(expirationDate+'T12:00:00').toLocaleDateString('en-US',{month:'2-digit',day:'2-digit',year:'2-digit'})}` : ''}</div>
          </div>
        </div>
      {/if}
    </div>

    <p class="size-info">{adSize === 'single' ? 'Single' : 'Double'} — {adSize === 'single' ? '2.75" × 1.75"' : '2.75" × 3.6"'}{selectedStore ? ` • ${selectedStore}` : ''}</p>

    <div class="actions">
      <button class="download-btn" on:click={downloadAd}>📥 Download Ad Image</button>
      <button class="secondary-btn" on:click={() => step = 'offers'}>← Edit</button>
    </div>
    <div style="height:80px;"></div>
  {/if}
</div>

<style>
  .ad-generator { }
  .back-btn { background:none; border:none; color:var(--text-secondary); font-size:14px; cursor:pointer; padding:8px 0; }
  .hint { font-size:13px; color:var(--text-secondary); margin:-4px 0 14px; }
  .field { margin-bottom:12px; }
  .field label { display:block; font-size:11px; font-weight:700; color:var(--text-secondary); margin-bottom:3px; text-transform:uppercase; letter-spacing:.5px; }
  .field input, .field select, .field textarea { width:100%; padding:10px; border:2px solid var(--border-color); border-radius:8px; font-size:14px; background:var(--card-bg); color:var(--text-primary); box-sizing:border-box; }
  .field textarea { resize:vertical; font-family:inherit; }
  .field input:focus, .field select:focus { border-color:#CC0000; outline:none; }
  .row { display:flex; gap:10px; }
  .field.half { flex:1; }
  .searching { position:absolute; right:12px; top:50%; transform:translateY(-50%); }
  .dropdown { background:var(--card-bg); border:2px solid var(--border-color); border-radius:8px; margin-top:4px; max-height:200px; overflow-y:auto; z-index:100; box-shadow:0 4px 16px rgba(0,0,0,.25); }
  .store-drop { position:absolute; top:100%; left:0; right:0; }
  .dropdown-item { display:block; width:100%; padding:10px; border:none; border-bottom:1px solid var(--border-color); background:transparent; text-align:left; cursor:pointer; color:var(--text-primary); font-size:13px; }
  .dropdown-item:hover { background:rgba(204,0,0,.06); }
  .dropdown-item:last-child { border-bottom:none; }
  .item-detail { display:block; font-size:11px; color:var(--text-secondary); margin-top:2px; }
  
  .offer-card { background:var(--card-bg); border:2px solid var(--border-color); border-radius:10px; padding:12px; margin-bottom:10px; }
  .offer-top { display:flex; justify-content:space-between; margin-bottom:8px; }
  .offer-num { font-size:13px; font-weight:700; color:#CC0000; }
  .x-btn { background:none; border:none; color:var(--text-secondary); font-size:18px; cursor:pointer; }
  .add-btn { width:100%; padding:10px; border:2px dashed var(--border-color); border-radius:8px; background:transparent; color:#CC0000; font-weight:600; cursor:pointer; margin-bottom:14px; }
  .add-btn:hover { border-color:#CC0000; }
  
  .themes { display:flex; gap:10px; margin-bottom:14px; flex-wrap:wrap; }
  .theme-btn { width:42px; height:42px; border-radius:50%; border:3px solid transparent; cursor:pointer; font-size:18px; display:flex; align-items:center; justify-content:center; font-weight:800; }
  .theme-btn.active { border-color:var(--text-primary); box-shadow:0 0 0 2px var(--card-bg), 0 0 0 4px var(--text-primary); }
  
  .primary-btn { width:100%; padding:13px; background:#CC0000; color:#fff; border:none; border-radius:8px; font-size:15px; font-weight:700; cursor:pointer; }
  .primary-btn:hover { background:#a00; }
  .secondary-btn { width:100%; padding:11px; background:var(--card-bg); color:var(--text-primary); border:2px solid var(--border-color); border-radius:8px; font-size:14px; font-weight:600; cursor:pointer; }
  .download-btn { width:100%; padding:14px; background:#2E7D32; color:#fff; border:none; border-radius:8px; font-size:16px; font-weight:700; cursor:pointer; margin-bottom:8px; }
  .download-btn:hover { background:#1B5E20; }
  
  /* --- AD PREVIEW --- */
  .preview-wrap { display:flex; justify-content:center; margin:16px 0; }
  .size-info { text-align:center; font-size:13px; color:var(--text-secondary); font-weight:600; margin-bottom:12px; }
  .actions { }
  
  /* Double ad */
  .ad.double { width:275px; height:360px; border:3px solid var(--c); overflow:hidden; position:relative; background:#fff; }
  .ad-img { width:100%; height:42%; background-size:cover; background-position:center; position:relative; }
  .ad-img-overlay { position:absolute; inset:0; background:rgba(0,0,0,.5); display:flex; flex-direction:column; align-items:center; justify-content:center; padding:8px; }
  .ad-name { color:#fff; font-size:18px; font-weight:900; margin:0; text-align:center; text-shadow:0 2px 4px rgba(0,0,0,.5); letter-spacing:1px; }
  .ad-contact-over { color:var(--a); font-size:8px; font-weight:700; margin:4px 0 0; text-align:center; }
  .ad-offers-area { flex:1; display:flex; flex-wrap:wrap; gap:4px; padding:6px; align-content:flex-start; }
  .ad-offer { flex:1; min-width:45%; border:1.5px solid var(--c); border-radius:4px; padding:8px 4px; text-align:center; background:var(--ob); }
  .ad-offer-main { font-size:14px; font-weight:900; color:var(--ot); line-height:1.2; }
  .ad-offer-sub { font-size:7px; color:#555; margin-top:3px; }
  .ad-fine { font-size:6px; color:#888; text-align:center; padding:2px 6px; line-height:1.3; }
  .ad-code { position:absolute; left:2px; top:50%; transform:rotate(-90deg) translateX(-50%); font-size:5px; color:#bbb; transform-origin:left center; }
  
  /* Single ad */
  .ad.single { width:275px; height:175px; border:3px solid var(--c); overflow:hidden; display:flex; background:#fff; position:relative; }
  .ad-left { width:38%; background-size:cover; background-position:center; position:relative; }
  .ad-left-overlay { position:absolute; inset:0; background:rgba(0,0,0,.55); display:flex; flex-direction:column; align-items:center; justify-content:center; padding:6px; }
  .ad-name-s { color:#fff; font-size:11px; font-weight:900; margin:0; text-align:center; text-shadow:0 1px 3px rgba(0,0,0,.6); line-height:1.2; }
  .ad-phone-s { color:var(--a); font-size:7px; font-weight:700; margin:4px 0 0; }
  .ad-right { width:62%; display:flex; flex-direction:column; }
  .ad-addr-bar { background:var(--c); color:#fff; font-size:6px; font-weight:700; text-align:center; padding:3px 4px; }
  .ad-offers-s { flex:1; display:flex; flex-direction:column; gap:2px; padding:4px; }
  .ad-offer-s { border:1px solid var(--c); border-radius:3px; padding:4px 3px; text-align:center; background:var(--ob); flex:1; display:flex; flex-direction:column; justify-content:center; }
  .ad-offer-main-s { font-size:11px; font-weight:900; color:var(--ot); line-height:1.1; }
  .ad-offer-sub-s { font-size:5.5px; color:#666; margin-top:1px; }
  .ad-fine-s { font-size:4.5px; color:#888; text-align:center; padding:2px 4px; line-height:1.2; }
</style>
