<script>
  import { user } from '../lib/stores.js';
  import { onMount } from 'svelte';

  let step = 'business'; // business, offers, preview
  let businessName = '';
  let businessPhone = '';
  let businessAddress = '';
  let businessCategory = '';
  let businessWebsite = '';
  
  let offers = [{ amount: '', unit: 'OFF', condition: '' }];
  let disclaimer = 'Must present coupon. Not valid with other offers. Limit one per visit.';
  let expirationDate = '';
  let styleNotes = '';
  
  let adSize = 'single';
  let adLayout = 'classic'; // classic, centered, banner, bold, minimal
  let selectedStore = '';
  let allStores = [];
  let storeSearch = '';
  let storeResults = [];
  let showStoreDropdown = false;
  
  // Expanded color controls
  let bgColor = '#CC0000';
  let textColor = '#FFFFFF';
  let offerBgColor = '#FFFFFF';
  let offerTextColor = '#CC0000';
  let accentColor = '#FFD700';
  
  // Presets based on real ads
  const colorPresets = [
    { name: 'Classic Red & Gold', bg: '#CC0000', text: '#FFF', offerBg: '#FFF', offerText: '#CC0000', accent: '#FFD700' },
    { name: 'Red & White', bg: '#CC0000', text: '#FFF', offerBg: '#FFEAEA', offerText: '#CC0000', accent: '#FFF' },
    { name: 'Black & Orange', bg: '#1a1a1a', text: '#FFF', offerBg: '#FFF', offerText: '#E65100', accent: '#FF6B35' },
    { name: 'Dark Green', bg: '#1B5E20', text: '#FFD700', offerBg: '#FFF', offerText: '#1B5E20', accent: '#FFD700' },
    { name: 'Blue & Gold', bg: '#0D47A1', text: '#FFF', offerBg: '#E3F2FD', offerText: '#0D47A1', accent: '#FFD700' },
    { name: 'Warm Wood', bg: '#5D4037', text: '#FFF', offerBg: '#EFEBE9', offerText: '#3E2723', accent: '#FFD54F' },
    { name: 'Teal', bg: '#00695C', text: '#FFF', offerBg: '#E0F2F1', offerText: '#004D40', accent: '#FFD54F' },
    { name: 'Purple', bg: '#4A148C', text: '#FFF', offerBg: '#F3E5F5', offerText: '#4A148C', accent: '#CE93D8' },
    { name: 'Orange Burst', bg: '#E65100', text: '#FFF', offerBg: '#FFF3E0', offerText: '#BF360C', accent: '#FFF' },
    { name: 'Clean White', bg: '#FFFFFF', text: '#333', offerBg: '#CC0000', offerText: '#FFF', accent: '#CC0000' },
  ];

  // Category images  
  const catImages = {
    'restaurant': 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600&h=400&fit=crop',
    'pizza': 'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=600&h=400&fit=crop',
    'mexican': 'https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=600&h=400&fit=crop',
    'taco': 'https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=600&h=400&fit=crop',
    'sushi': 'https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=600&h=400&fit=crop',
    'burger': 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600&h=400&fit=crop',
    'coffee': 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=600&h=400&fit=crop',
    'bakery': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600&h=400&fit=crop',
    'salon': 'https://images.unsplash.com/photo-1560066984-138dadb4c035?w=600&h=400&fit=crop',
    'barber': 'https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=600&h=400&fit=crop',
    'hair': 'https://images.unsplash.com/photo-1560066984-138dadb4c035?w=600&h=400&fit=crop',
    'auto': 'https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?w=600&h=400&fit=crop',
    'oil change': 'https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?w=600&h=400&fit=crop',
    'dental': 'https://images.unsplash.com/photo-1606811841689-23dfddce3e95?w=600&h=400&fit=crop',
    'gym': 'https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=600&h=400&fit=crop',
    'fitness': 'https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=600&h=400&fit=crop',
    'vet': 'https://images.unsplash.com/photo-1548199973-03cce0bbc87b?w=600&h=400&fit=crop',
    'chinese': 'https://images.unsplash.com/photo-1585032226651-759b368d7246?w=600&h=400&fit=crop',
    'thai': 'https://images.unsplash.com/photo-1562565652-a0d8f0c59eb4?w=600&h=400&fit=crop',
    'indian': 'https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=600&h=400&fit=crop',
    'italian': 'https://images.unsplash.com/photo-1498579150354-977475b7ea0b?w=600&h=400&fit=crop',
    'seafood': 'https://images.unsplash.com/photo-1615141982883-c7ad0e69fd62?w=600&h=400&fit=crop',
    'bbq': 'https://images.unsplash.com/photo-1529193591184-b1d58069ecdd?w=600&h=400&fit=crop',
    'wings': 'https://images.unsplash.com/photo-1567620832903-9fc6debc209f?w=600&h=400&fit=crop',
    'ice cream': 'https://images.unsplash.com/photo-1497034825429-c343d7c6a68f?w=600&h=400&fit=crop',
    'massage': 'https://images.unsplash.com/photo-1544161515-4ab6ce6db874?w=600&h=400&fit=crop',
    'spa': 'https://images.unsplash.com/photo-1544161515-4ab6ce6db874?w=600&h=400&fit=crop',
    'chiropract': 'https://images.unsplash.com/photo-1519823551278-64ac92734fb1?w=600&h=400&fit=crop',
    'pet': 'https://images.unsplash.com/photo-1548199973-03cce0bbc87b?w=600&h=400&fit=crop',
    'cleaning': 'https://images.unsplash.com/photo-1581578731548-c64695cc6952?w=600&h=400&fit=crop',
    'plumb': 'https://images.unsplash.com/photo-1585704032915-c3400ca199e7?w=600&h=400&fit=crop',
    'default': 'https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=600&h=400&fit=crop',
  };

  let customImageUrl = '';

  function getCategoryImage() {
    if (customImageUrl) return customImageUrl;
    const cat = (businessCategory + ' ' + businessName).toLowerCase();
    for (const [key, url] of Object.entries(catImages)) {
      if (cat.includes(key)) return url;
    }
    return catImages.default;
  }

  // Store search
  function searchStores() {
    if (!storeSearch.trim() || storeSearch.length < 2) { storeResults = []; showStoreDropdown = false; return; }
    const term = storeSearch.toLowerCase();
    storeResults = allStores.filter(s =>
      (s.StoreName || '').toLowerCase().includes(term) ||
      (s.GroceryChain || '').toLowerCase().includes(term) ||
      (s.City || '').toLowerCase().includes(term) ||
      (s.PostalCode || '').includes(term) ||
      (s.Address || '').toLowerCase().includes(term) ||
      (s.State || '').toLowerCase() === term
    ).slice(0, 10).map(s => ({
      id: s.StoreName,
      label: `${s.GroceryChain} — ${s.City}, ${s.State} (${s.StoreName})`,
      address: s.Address || '', zip: s.PostalCode || ''
    }));
    showStoreDropdown = storeResults.length > 0;
  }
  let selectedStoreData = null; // full store object for location biasing

  function selectStore(store) {
    selectedStore = store.id; storeSearch = store.label; showStoreDropdown = false; storeResults = [];
    // Store lat/lng for business search biasing
    const fullStore = allStores.find(s => s.StoreName === store.id);
    selectedStoreData = fullStore || null;
  }

  // Business search — biased to selected store location
  let searchResults = [];
  let searching = false;
  async function searchBusiness() {
    if (!businessName.trim() || businessName.length < 3) return;
    searching = true;
    try {
      const apiKey = import.meta.env.VITE_GOOGLE_PLACES_API_KEY || 'AIzaSyBNR8M1VG5DccJmK6ZzJOam9mF8jOCEEqM';
      const body = { textQuery: businessName, maxResultCount: 5 };
      
      // If a store is selected, bias search to its location
      if (selectedStoreData?.latitude && selectedStoreData?.longitude) {
        body.locationBias = {
          circle: {
            center: { latitude: selectedStoreData.latitude, longitude: selectedStoreData.longitude },
            radius: 8000.0 // 8km (~5 miles)
          }
        };
      }
      
      const res = await fetch('https://places.googleapis.com/v1/places:searchText', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Goog-Api-Key': apiKey,
          'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.primaryTypeDisplayName,places.photos' },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      searchResults = (data.places || []).map(p => ({
        name: p.displayName?.text || '', address: p.formattedAddress || '',
        phone: p.nationalPhoneNumber || '', website: p.websiteUri || '',
        category: p.primaryTypeDisplayName?.text || '',
        photoRef: p.photos?.[0]?.name || ''
      }));
    } catch { searchResults = []; }
    searching = false;
  }
  function selectBusiness(biz) {
    businessName = biz.name; businessPhone = biz.phone; businessAddress = biz.address;
    businessCategory = biz.category; businessWebsite = biz.website; searchResults = [];
  }

  function addOffer() { if (offers.length < 6) offers = [...offers, { amount: '', unit: 'OFF', condition: '' }]; }
  function removeOffer(idx) { offers = offers.filter((_, i) => i !== idx); }
  function goToOffers() { if (!businessName.trim()) return alert('Please enter a business name'); step = 'offers'; }
  function goToPreview() { if (!offers.some(o => o.amount.trim())) return alert('Add at least one offer'); step = 'preview'; }
  function applyPreset(p) { bgColor = p.bg; textColor = p.text; offerBgColor = p.offerBg; offerTextColor = p.offerText; accentColor = p.accent; }

  function genCode() {
    const s = selectedStore ? selectedStore.replace(/[^A-Z0-9]/gi,'').slice(0,6).toUpperCase() : 'STORE';
    const r = ($user?.name || 'REP').split(' ').map(w=>w[0]).join('').toUpperCase();
    return `${s}${r}`;
  }

  // Format offer display like real ads: "$5 OFF" or "BUY ONE GET ONE FREE" or "20% OFF"
  function fmtOffer(o) {
    const amt = o.amount.trim();
    if (!amt) return '';
    // If starts with $ or number, make it big
    return amt.toUpperCase();
  }

  async function downloadAd() {
    const dpi = 3;
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(2.75 * 96 * dpi);
    canvas.height = Math.round((adSize === 'single' ? 1.75 : 3.6) * 96 * dpi);
    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height, S = dpi;

    // Load image
    let img = null;
    try {
      img = await new Promise((res, rej) => {
        const i = new Image(); i.crossOrigin = 'anonymous';
        i.onload = () => res(i); i.onerror = rej;
        i.src = getCategoryImage();
      });
    } catch {}

    const validOffers = offers.filter(o => o.amount.trim());
    const expStr = expirationDate ? `Exp. ${new Date(expirationDate+'T12:00:00').toLocaleDateString('en-US',{month:'numeric',day:'numeric',year:'2-digit'})}` : '';

    ctx.fillStyle = '#FFF';
    ctx.fillRect(0, 0, w, h);

    if (adSize === 'double') {
      // === DOUBLE AD — modeled after Mak Mak Thai / Atilano's ===
      // Full background color
      ctx.fillStyle = bgColor;
      ctx.fillRect(0, 0, w, h);
      
      // Top section: Logo/name area with image
      const topH = Math.round(h * 0.48);
      if (img) {
        ctx.save();
        ctx.beginPath(); ctx.rect(0, 0, w, topH); ctx.clip();
        const iw = w, ih = w / (img.width/img.height);
        ctx.drawImage(img, 0, (topH - ih)/2, iw, ih);
        ctx.restore();
        // Gradient overlay
        const grad = ctx.createLinearGradient(0, topH * 0.3, 0, topH);
        grad.addColorStop(0, 'rgba(0,0,0,0.1)');
        grad.addColorStop(1, bgColor + 'F0');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, w, topH);
      }

      // Business name — BIG stylized
      ctx.fillStyle = textColor;
      ctx.textAlign = 'center';
      ctx.font = `900 ${28*S}px "Georgia", serif`;
      ctx.shadowColor = 'rgba(0,0,0,0.5)'; ctx.shadowBlur = 6*S;
      ctx.fillText(businessName, w/2, topH * 0.55);
      ctx.shadowBlur = 0;

      // Category subtitle
      if (businessCategory) {
        ctx.font = `italic ${10*S}px "Georgia", serif`;
        ctx.fillStyle = accentColor;
        ctx.fillText(businessCategory.toUpperCase(), w/2, topH * 0.55 + 18*S);
      }

      // Address • Phone bar
      ctx.fillStyle = accentColor;
      ctx.font = `bold ${9*S}px Arial`;
      const contactLine = [businessAddress.split(',').slice(0,2).join(',').trim(), businessPhone].filter(Boolean).join(' • ');
      ctx.fillText(contactLine, w/2, topH - 10*S);

      // Bottom: Offer boxes
      const offerY = topH + 8*S;
      const offerAreaH = h - offerY - 28*S;
      const cols = Math.min(validOffers.length, 3);
      const colW = (w - 16*S) / cols;
      const offerH = Math.min(offerAreaH, 65*S);

      validOffers.slice(0, 3).forEach((offer, i) => {
        const ox = 8*S + i * colW;
        // Offer box
        ctx.fillStyle = offerBgColor;
        ctx.fillRect(ox + 2*S, offerY, colW - 4*S, offerH);
        ctx.strokeStyle = offerTextColor + '40';
        ctx.lineWidth = 1.5*S;
        ctx.strokeRect(ox + 2*S, offerY, colW - 4*S, offerH);

        // Dollar amount HUGE
        ctx.fillStyle = offerTextColor;
        ctx.font = `900 ${22*S}px Arial`;
        ctx.textAlign = 'center';
        ctx.fillText(fmtOffer(offer), ox + colW/2, offerY + offerH * 0.45);

        // Condition text
        if (offer.condition) {
          ctx.fillStyle = offerTextColor + 'BB';
          ctx.font = `bold ${7*S}px Arial`;
          ctx.fillText(offer.condition, ox + colW/2, offerY + offerH * 0.72);
        }
      });

      // Disclaimer
      ctx.fillStyle = textColor + '99';
      ctx.font = `${5.5*S}px Arial`;
      ctx.textAlign = 'center';
      ctx.fillText(`${disclaimer} ${expStr} • ${genCode()}`, w/2, h - 8*S);

    } else {
      // === SINGLE AD — modeled after Clippers / K&H / Washington Burrito ===
      // Border
      ctx.strokeStyle = bgColor;
      ctx.lineWidth = 3*S;
      ctx.strokeRect(1.5*S, 1.5*S, w-3*S, h-3*S);

      // Left panel: image + business name (~40%)
      const leftW = Math.round(w * 0.4);
      if (img) {
        ctx.save();
        ctx.beginPath(); ctx.rect(3*S, 3*S, leftW - 3*S, h - 6*S); ctx.clip();
        const ih = h - 6*S, iw = ih * (img.width / img.height);
        ctx.drawImage(img, 3*S, 3*S, Math.max(leftW, iw), ih);
        ctx.restore();
        // Dark overlay
        const grad = ctx.createLinearGradient(3*S, 3*S, 3*S, h-3*S);
        grad.addColorStop(0, bgColor + '90');
        grad.addColorStop(0.5, bgColor + 'DD');
        grad.addColorStop(1, bgColor);
        ctx.fillStyle = grad;
        ctx.fillRect(3*S, 3*S, leftW - 3*S, h - 6*S);
      } else {
        ctx.fillStyle = bgColor;
        ctx.fillRect(3*S, 3*S, leftW - 3*S, h - 6*S);
      }

      // Business name on left
      ctx.fillStyle = textColor;
      ctx.textAlign = 'center';
      const nameX = 3*S + (leftW-3*S)/2;
      // Auto-size name
      let fontSize = 14*S;
      ctx.font = `900 ${fontSize}px Arial`;
      while (ctx.measureText(businessName.toUpperCase()).width > (leftW - 14*S) && fontSize > 7*S) {
        fontSize -= S;
        ctx.font = `900 ${fontSize}px Arial`;
      }
      ctx.shadowColor = 'rgba(0,0,0,0.6)'; ctx.shadowBlur = 4*S;
      // Word wrap
      const words = businessName.toUpperCase().split(' ');
      let line = '', ly = h * 0.33;
      for (const word of words) {
        const test = line + word + ' ';
        if (ctx.measureText(test).width > leftW - 14*S && line) {
          ctx.fillText(line.trim(), nameX, ly); line = word + ' '; ly += fontSize + 3*S;
        } else line = test;
      }
      if (line.trim()) ctx.fillText(line.trim(), nameX, ly);
      ctx.shadowBlur = 0;

      // Phone + address on left bottom
      ctx.font = `bold ${6*S}px Arial`;
      ctx.fillStyle = accentColor;
      if (businessPhone) ctx.fillText(businessPhone, nameX, h - 16*S);
      const shortAddr = businessAddress.split(',')[0] || '';
      if (shortAddr) { ctx.fillStyle = textColor + 'CC'; ctx.font = `${5.5*S}px Arial`; ctx.fillText(shortAddr, nameX, h - 8*S); }

      // Right panel: offers
      const rightX = leftW + 2*S;
      const rightW = w - rightX - 4*S;
      const offerCount = validOffers.length;
      const offerH = Math.min((h - 26*S) / offerCount, 45*S);
      let oy = 6*S;

      validOffers.forEach((offer, i) => {
        // Offer background
        ctx.fillStyle = offerBgColor;
        ctx.fillRect(rightX, oy, rightW, offerH - 2*S);
        ctx.strokeStyle = offerTextColor + '30';
        ctx.lineWidth = 1*S;
        ctx.strokeRect(rightX, oy, rightW, offerH - 2*S);

        // Amount — HUGE
        ctx.fillStyle = offerTextColor;
        ctx.font = `900 ${18*S}px Arial`;
        ctx.textAlign = 'center';
        ctx.fillText(fmtOffer(offer), rightX + rightW/2, oy + (offerH-2*S) * 0.48);

        // Condition
        if (offer.condition) {
          ctx.fillStyle = '#555';
          ctx.font = `bold ${6*S}px Arial`;
          ctx.fillText(offer.condition, rightX + rightW/2, oy + (offerH-2*S) * 0.78);
        }
        oy += offerH;
      });

      // Disclaimer at bottom
      ctx.fillStyle = '#888';
      ctx.font = `${4.5*S}px Arial`;
      ctx.textAlign = 'center';
      ctx.fillText(`${disclaimer.slice(0, 70)} ${expStr}`, w/2, h - 5*S);

      // Tracking code on right edge
      ctx.save();
      ctx.translate(w - 6*S, h/2);
      ctx.rotate(Math.PI/2);
      ctx.fillStyle = '#bbb';
      ctx.font = `${4*S}px Arial`;
      ctx.fillText(genCode(), 0, 0);
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
    const exp = new Date(); exp.setMonth(exp.getMonth() + 3);
    expirationDate = exp.toISOString().slice(0, 10);
  });
</script>

<div class="gen">
  {#if step !== 'business'}
    <button class="back" on:click={() => { if (step === 'offers') step = 'business'; else step = 'offers'; }}>
      ← {step === 'offers' ? 'Business Info' : 'Offers'}
    </button>
  {/if}

  {#if step === 'business'}
    <h2>📋 Business Info</h2>
    <p class="sub">Search or enter business details</p>
    
    <div class="f">
      <label>Business Name *</label>
      <div class="rel">
        <input type="text" bind:value={businessName} placeholder="e.g. Joe's Pizza" on:input={() => { if (businessName.length >= 3) searchBusiness(); }} />
        {#if searching}<span class="spin">🔍</span>{/if}
      </div>
      {#if searchResults.length > 0}
        <div class="dd">
          {#each searchResults as b}
            <button class="ddi" on:click={() => selectBusiness(b)}><strong>{b.name}</strong><small>{b.address}</small></button>
          {/each}
        </div>
      {/if}
    </div>
    <div class="f"><label>Phone</label><input type="tel" bind:value={businessPhone} placeholder="(555) 123-4567" /></div>
    <div class="f"><label>Address</label><input type="text" bind:value={businessAddress} placeholder="123 Main St, City, State" /></div>
    <div class="f"><label>Category</label><input type="text" bind:value={businessCategory} placeholder="Restaurant, Auto, Salon..." /></div>

    <div class="row">
      <div class="f half">
        <label>Ad Size</label>
        <select bind:value={adSize}>
          <option value="single">Single (2.75" × 1.75")</option>
          <option value="double">Double (2.75" × 3.6")</option>
        </select>
      </div>
      <div class="f half rel">
        <label>Store</label>
        <input type="text" bind:value={storeSearch} on:input={searchStores} on:focus={() => { if (storeSearch.length >= 2) searchStores(); }} placeholder="City, zip, store #..." autocomplete="off" />
        {#if showStoreDropdown}
          <div class="dd pos">
            {#each storeResults as s}
              <button class="ddi" on:click={() => selectStore(s)}><strong>{s.id}</strong><small>{s.label}</small></button>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <button class="btn-primary" on:click={goToOffers}>Next: Add Offers →</button>

  {:else if step === 'offers'}
    <h2>🎯 Offers</h2>
    <p class="sub">Enter each offer — the amount will appear large like real ads</p>

    {#each offers as offer, i}
      <div class="ocard">
        <div class="otop">
          <span class="onum">Offer {i + 1}</span>
          {#if offers.length > 1}<button class="xbtn" on:click={() => removeOffer(i)}>✕</button>{/if}
        </div>
        <div class="f"><label>Offer Amount/Text * (e.g. "$5 OFF", "BOGO FREE", "20% OFF")</label><input type="text" bind:value={offer.amount} placeholder="$5 OFF" /></div>
        <div class="f"><label>Condition (e.g. "Purchase of $25 or more")</label><input type="text" bind:value={offer.condition} placeholder="Any purchase of $25+" /></div>
      </div>
    {/each}
    {#if offers.length < 6}<button class="add-btn" on:click={addOffer}>+ Add Offer</button>{/if}

    <div class="f"><label>Disclaimers</label><textarea bind:value={disclaimer} rows="2"></textarea></div>
    <div class="f"><label>Expiration Date</label><input type="date" bind:value={expirationDate} /></div>

    <div class="f">
      <label>Style Notes (optional — describe the look you want)</label>
      <textarea bind:value={styleNotes} rows="2" placeholder="e.g. Bold and eye-catching, warm tones, professional look, food-focused..."></textarea>
    </div>

    <h3>🎨 Color Theme</h3>
    <div class="presets">
      {#each colorPresets as p}
        <button class="preset" class:active={bgColor === p.bg && offerBgColor === p.offerBg} style="background:{p.bg}; color:{p.accent}; border-color:{bgColor === p.bg && offerBgColor === p.offerBg ? 'var(--text-primary)' : 'transparent'}" on:click={() => applyPreset(p)} title={p.name}>
          <span style="font-size:10px; font-weight:800;">{p.name.split(' ')[0]}</span>
        </button>
      {/each}
    </div>

    <details class="custom-colors">
      <summary>🎨 Custom Colors</summary>
      <div class="color-grid">
        <div class="f"><label>Background</label><input type="color" bind:value={bgColor} /></div>
        <div class="f"><label>Text</label><input type="color" bind:value={textColor} /></div>
        <div class="f"><label>Offer Box</label><input type="color" bind:value={offerBgColor} /></div>
        <div class="f"><label>Offer Text</label><input type="color" bind:value={offerTextColor} /></div>
        <div class="f"><label>Accent</label><input type="color" bind:value={accentColor} /></div>
      </div>
    </details>

    <h3>📐 Layout Style</h3>
    <div class="layouts">
      <button class="layout-btn" class:active={adLayout === 'classic'} on:click={() => adLayout = 'classic'}>
        <span class="layout-icon">📰</span><span>Classic</span>
      </button>
      <button class="layout-btn" class:active={adLayout === 'centered'} on:click={() => adLayout = 'centered'}>
        <span class="layout-icon">🎯</span><span>Centered</span>
      </button>
      <button class="layout-btn" class:active={adLayout === 'banner'} on:click={() => adLayout = 'banner'}>
        <span class="layout-icon">🏷️</span><span>Banner</span>
      </button>
      <button class="layout-btn" class:active={adLayout === 'bold'} on:click={() => adLayout = 'bold'}>
        <span class="layout-icon">💥</span><span>Bold</span>
      </button>
      <button class="layout-btn" class:active={adLayout === 'minimal'} on:click={() => adLayout = 'minimal'}>
        <span class="layout-icon">✨</span><span>Clean</span>
      </button>
    </div>

    <div class="f">
      <label>Custom Image URL (optional)</label>
      <input type="url" bind:value={customImageUrl} placeholder="https://... or leave blank for auto" />
    </div>

    <button class="btn-primary" on:click={goToPreview}>Preview Ad →</button>

  {:else if step === 'preview'}
    <h2>👁️ Ad Preview</h2>
    
    {@const vo = offers.filter(o => o.amount.trim())}
    {@const expTxt = expirationDate ? `Exp. ${new Date(expirationDate+'T12:00:00').toLocaleDateString('en-US',{month:'numeric',day:'numeric',year:'2-digit'})}` : ''}
    {@const contact = [businessAddress.split(',').slice(0,2).join(',').trim(), businessPhone].filter(Boolean).join(' • ')}
    {@const shortAddr = businessAddress.split(',')[0] || ''}
    {@const imgUrl = getCategoryImage()}
    <div class="preview-center">

      <div class="ad {adSize}" style="--bg:{bgColor}; --tx:{textColor}; --ob:{offerBgColor}; --ot:{offerTextColor}; --ac:{accentColor};">

        {#if adLayout === 'classic'}
          <!-- CLASSIC: Image left/top, offers right/bottom -->
          {#if adSize === 'double'}
            <div class="img-zone" style="background-image:url({imgUrl}); height:45%;">
              <div class="img-grad" style="background:linear-gradient(to bottom, transparent 20%, {bgColor}ee);">
                <div class="img-content bottom">
                  <div class="biz-name lg">{businessName}</div>
                  <div class="biz-contact">{contact}</div>
                </div>
              </div>
            </div>
            <div class="offers-grid">
              {#each vo as o}<div class="offer-box"><div class="offer-amt">{fmtOffer(o)}</div>{#if o.condition}<div class="offer-det">{o.condition}</div>{/if}</div>{/each}
            </div>
          {:else}
            <div class="split-left" style="background-image:url({imgUrl});">
              <div class="img-grad-full" style="background:linear-gradient(135deg, {bgColor}dd, {bgColor}ee);">
                <div class="biz-name sm">{businessName.toUpperCase()}</div>
                <div class="biz-phone">{businessPhone}</div>
                <div class="biz-addr">{shortAddr}</div>
              </div>
            </div>
            <div class="split-right">
              {#each vo as o}<div class="offer-row"><div class="offer-amt-s">{fmtOffer(o)}</div>{#if o.condition}<div class="offer-det-s">{o.condition}</div>{/if}</div>{/each}
            </div>
          {/if}

        {:else if adLayout === 'centered'}
          <!-- CENTERED: Full background image, everything centered -->
          <div class="full-img" style="background-image:url({imgUrl});">
            <div class="full-overlay" style="background:radial-gradient(ellipse at center, {bgColor}ee 30%, {bgColor}cc 100%);">
              <div class="biz-name {adSize === 'double' ? 'xl' : 'md'}">{businessName}</div>
              {#if businessCategory && adSize === 'double'}<div class="biz-tag">{businessCategory.toUpperCase()}</div>{/if}
              <div class="center-offers">
                {#each vo as o}
                  <div class="center-offer">
                    <span class="center-amt">{fmtOffer(o)}</span>
                    {#if o.condition}<span class="center-cond">{o.condition}</span>{/if}
                  </div>
                {/each}
              </div>
              <div class="biz-contact">{contact}</div>
            </div>
          </div>

        {:else if adLayout === 'banner'}
          <!-- BANNER: Color bars with offers, image as accent -->
          {#if adSize === 'double'}
            <div class="banner-top" style="background:{bgColor};">
              <div class="biz-name lg">{businessName}</div>
              <div class="biz-contact">{contact}</div>
            </div>
            <div class="banner-img" style="background-image:url({imgUrl});"></div>
            {#each vo as o}
              <div class="banner-offer"><span class="banner-amt">{fmtOffer(o)}</span>{#if o.condition}<span class="banner-det">{o.condition}</span>{/if}</div>
            {/each}
          {:else}
            <div class="banner-bar" style="background:{bgColor};"><div class="biz-name xs">{businessName.toUpperCase()}</div><div class="biz-phone" style="font-size:6px;">{businessPhone}</div></div>
            <div class="banner-body">
              {#each vo as o}<div class="banner-offer-s"><span class="banner-amt-s">{fmtOffer(o)}</span>{#if o.condition}<span class="banner-det-s">{o.condition}</span>{/if}</div>{/each}
            </div>
            <div class="banner-img-s" style="background-image:url({imgUrl});"></div>
          {/if}

        {:else if adLayout === 'bold'}
          <!-- BOLD: Giant offer text dominates, minimal image -->
          <div class="full-img" style="background-image:url({imgUrl});">
            <div class="bold-overlay" style="background:{bgColor}dd;">
              {#if vo.length > 0}
                <div class="bold-amt">{fmtOffer(vo[0])}</div>
                {#if vo[0].condition}<div class="bold-cond">{vo[0].condition}</div>{/if}
              {/if}
              <div class="bold-biz">{businessName}</div>
              <div class="biz-contact">{contact}</div>
              {#if vo.length > 1}
                <div class="bold-extras">
                  {#each vo.slice(1) as o}<span class="bold-extra">{fmtOffer(o)}{o.condition ? ' — ' + o.condition : ''}</span>{/each}
                </div>
              {/if}
            </div>
          </div>

        {:else if adLayout === 'minimal'}
          <!-- MINIMAL: Clean, white-focused, modern -->
          <div class="min-layout">
            <div class="min-header" style="border-bottom:3px solid {bgColor};">
              <div class="min-name" style="color:{bgColor};">{businessName}</div>
              <div class="min-contact">{contact}</div>
            </div>
            <div class="min-offers">
              {#each vo as o}
                <div class="min-offer" style="border-left:4px solid {bgColor};">
                  <div class="min-amt" style="color:{offerTextColor};">{fmtOffer(o)}</div>
                  {#if o.condition}<div class="min-cond">{o.condition}</div>{/if}
                </div>
              {/each}
            </div>
            <div class="min-img" style="background-image:url({imgUrl});"></div>
          </div>
        {/if}

        <div class="ad-fine">{disclaimer.slice(0, adSize === 'single' ? 60 : 120)} {expTxt} • {genCode()}</div>
      </div>
    </div>

    <p class="info">{adSize === 'single' ? 'Single — 2.75" × 1.75"' : 'Double — 2.75" × 3.6"'}{selectedStore ? ` • ${selectedStore}` : ''}</p>
    {#if styleNotes}<p class="style-note">📝 Style notes: {styleNotes}</p>{/if}

    <button class="btn-download" on:click={downloadAd}>📥 Download Ad Image</button>
    <button class="btn-secondary" on:click={() => step = 'offers'}>← Edit Offers</button>
    <button class="btn-secondary" on:click={() => step = 'business'}>← Edit Business</button>
    <div style="height:100px;"></div>
  {/if}
</div>

<style>
  .gen { }
  .back { background:none; border:none; color:var(--text-secondary); font-size:14px; cursor:pointer; padding:8px 0; }
  .sub { font-size:13px; color:var(--text-secondary); margin:-4px 0 14px; }
  .f { margin-bottom:12px; }
  .f label { display:block; font-size:11px; font-weight:700; color:var(--text-secondary); margin-bottom:3px; text-transform:uppercase; letter-spacing:.3px; }
  .f input, .f select, .f textarea { width:100%; padding:10px; border:2px solid var(--border-color); border-radius:8px; font-size:14px; background:var(--card-bg); color:var(--text-primary); box-sizing:border-box; }
  .f input[type="color"] { height:40px; padding:2px; cursor:pointer; }
  .f textarea { resize:vertical; font-family:inherit; }
  .f input:focus, .f select:focus { border-color:#CC0000; outline:none; }
  .row { display:flex; gap:10px; }
  .half { flex:1; }
  .rel { position:relative; }
  .spin { position:absolute; right:12px; top:50%; transform:translateY(-50%); }
  .dd { background:var(--card-bg); border:2px solid var(--border-color); border-radius:8px; margin-top:4px; max-height:200px; overflow-y:auto; z-index:100; box-shadow:0 4px 16px rgba(0,0,0,.25); }
  .dd.pos { position:absolute; top:100%; left:0; right:0; }
  .ddi { display:block; width:100%; padding:10px; border:none; border-bottom:1px solid var(--border-color); background:transparent; text-align:left; cursor:pointer; color:var(--text-primary); font-size:13px; }
  .ddi:hover { background:rgba(204,0,0,.06); }
  .ddi:last-child { border-bottom:none; }
  .ddi small { display:block; font-size:11px; color:var(--text-secondary); margin-top:2px; }
  
  .ocard { background:var(--card-bg); border:2px solid var(--border-color); border-radius:10px; padding:12px; margin-bottom:10px; }
  .otop { display:flex; justify-content:space-between; margin-bottom:8px; }
  .onum { font-size:13px; font-weight:700; color:#CC0000; }
  .xbtn { background:none; border:none; color:var(--text-secondary); font-size:18px; cursor:pointer; }
  .add-btn { width:100%; padding:10px; border:2px dashed var(--border-color); border-radius:8px; background:transparent; color:#CC0000; font-weight:600; cursor:pointer; margin-bottom:14px; }
  
  .presets { display:flex; gap:8px; margin-bottom:14px; flex-wrap:wrap; }
  .preset { width:56px; height:40px; border-radius:8px; border:3px solid transparent; cursor:pointer; display:flex; align-items:center; justify-content:center; transition:all .15s; }
  .preset.active, .preset:hover { transform:scale(1.1); }
  
  .custom-colors { margin-bottom:14px; }
  .custom-colors summary { font-size:13px; font-weight:600; cursor:pointer; color:var(--text-secondary); }
  .color-grid { display:grid; grid-template-columns:repeat(5, 1fr); gap:8px; margin-top:8px; }
  
  .btn-primary { width:100%; padding:13px; background:#CC0000; color:#fff; border:none; border-radius:8px; font-size:15px; font-weight:700; cursor:pointer; margin-top:8px; }
  .btn-secondary { width:100%; padding:11px; background:var(--card-bg); color:var(--text-primary); border:2px solid var(--border-color); border-radius:8px; font-size:14px; font-weight:600; cursor:pointer; margin-top:6px; }
  .btn-download { width:100%; padding:14px; background:#2E7D32; color:#fff; border:none; border-radius:8px; font-size:16px; font-weight:700; cursor:pointer; }
  
  .layouts { display:flex; gap:6px; margin-bottom:14px; flex-wrap:wrap; }
  .layout-btn { display:flex; flex-direction:column; align-items:center; gap:2px; padding:8px 10px; border:2px solid var(--border-color); border-radius:8px; background:var(--card-bg); cursor:pointer; font-size:10px; font-weight:700; color:var(--text-secondary); flex:1; min-width:50px; }
  .layout-btn.active { border-color:#CC0000; color:#CC0000; }
  .layout-icon { font-size:20px; }

  .preview-center { display:flex; justify-content:center; margin:16px 0; }
  .info { text-align:center; font-size:13px; color:var(--text-secondary); font-weight:600; margin-bottom:4px; }
  .style-note { text-align:center; font-size:12px; color:var(--text-tertiary); font-style:italic; margin-bottom:12px; }

  /* ===== AD BASE ===== */
  .ad { border:3px solid var(--bg); overflow:hidden; position:relative; background:var(--bg); }
  .ad.single { width:275px; height:175px; display:flex; }
  .ad.double { width:275px; height:360px; display:flex; flex-direction:column; }
  .ad-fine { font:5px/1.2 Arial; color:var(--tx); opacity:.5; text-align:center; padding:2px 6px; position:absolute; bottom:2px; left:0; right:0; }

  /* Shared elements */
  .biz-name { color:var(--tx); text-align:center; text-shadow:0 2px 6px rgba(0,0,0,.5); font-family:"Georgia",serif; font-weight:900; }
  .biz-name.xl { font-size:22px; }
  .biz-name.lg { font-size:18px; }
  .biz-name.md { font-size:14px; }
  .biz-name.sm { font-size:11px; line-height:1.2; word-break:break-word; }
  .biz-name.xs { font-size:10px; }
  .biz-contact { color:var(--ac); font:bold 7px/1 Arial; text-align:center; margin-top:4px; }
  .biz-phone { color:var(--ac); font:bold 7px/1 Arial; text-align:center; margin-top:4px; }
  .biz-addr { color:var(--tx); opacity:.7; font:5.5px/1 Arial; text-align:center; margin-top:2px; }
  .biz-tag { color:var(--ac); font:italic 8px/1 Georgia,serif; text-align:center; letter-spacing:2px; margin-top:2px; }

  /* Image zones */
  .img-zone { background-size:cover; background-position:center; position:relative; }
  .img-grad { position:absolute; inset:0; display:flex; flex-direction:column; justify-content:flex-end; padding:10px; }
  .img-grad-full { position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:6px; }
  .img-content.bottom { }
  .full-img { width:100%; height:100%; background-size:cover; background-position:center; position:relative; }
  .full-overlay { position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:10px; }

  /* CLASSIC */
  .split-left { width:40%; height:100%; background-size:cover; background-position:center; position:relative; }
  .split-right { width:60%; display:flex; flex-direction:column; height:100%; }
  .single .split-left, .single .split-right { float:left; }
  .single { display:flex; }
  .offers-grid { display:flex; flex-wrap:wrap; gap:3px; padding:6px; flex:1; align-content:flex-start; }
  .offer-box { flex:1; min-width:45%; background:var(--ob); border:1.5px solid var(--ot)40; border-radius:3px; padding:8px 4px; text-align:center; }
  .offer-amt { font:900 16px/1.1 Arial; color:var(--ot); }
  .offer-det { font:600 6.5px/1.2 Arial; color:#555; margin-top:3px; }
  .offer-row { flex:1; background:var(--ob); display:flex; flex-direction:column; align-items:center; justify-content:center; padding:3px; border-bottom:1px solid var(--ot)15; }
  .offer-amt-s { font:900 15px/1.1 Arial; color:var(--ot); }
  .offer-det-s { font:600 6px/1.2 Arial; color:#555; margin-top:2px; }

  /* CENTERED */
  .center-offers { display:flex; flex-direction:column; gap:6px; margin:8px 0; width:100%; align-items:center; }
  .center-offer { text-align:center; }
  .center-amt { font:900 20px/1.1 Arial; color:var(--ac); display:block; text-shadow:0 1px 3px rgba(0,0,0,.3); }
  .single .center-amt { font-size:16px; }
  .center-cond { font:600 7px/1 Arial; color:var(--tx); opacity:.8; display:block; margin-top:2px; }
  .single .center-cond { font-size:6px; }

  /* BANNER */
  .banner-top { padding:10px; text-align:center; }
  .banner-img { height:35%; background-size:cover; background-position:center; }
  .banner-offer { background:var(--ob); padding:6px 8px; display:flex; align-items:center; justify-content:center; gap:8px; border-bottom:1px solid var(--ot)20; }
  .banner-amt { font:900 18px/1 Arial; color:var(--ot); }
  .banner-det { font:600 7px/1 Arial; color:#555; }
  .banner-bar { padding:6px; text-align:center; }
  .banner-body { flex:1; display:flex; flex-direction:column; }
  .banner-offer-s { flex:1; background:var(--ob); display:flex; align-items:center; justify-content:center; gap:6px; padding:2px 4px; border-bottom:1px solid var(--ot)15; }
  .banner-amt-s { font:900 14px/1 Arial; color:var(--ot); }
  .banner-det-s { font:600 5.5px/1 Arial; color:#555; }
  .banner-img-s { width:30%; background-size:cover; background-position:center; position:absolute; right:0; top:0; bottom:0; }
  .single .banner-body { width:70%; }

  /* BOLD */
  .bold-overlay { position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:8px; text-align:center; }
  .bold-amt { font:900 36px/1 Arial; color:var(--ac); text-shadow:0 2px 8px rgba(0,0,0,.4); }
  .single .bold-amt { font-size:28px; }
  .bold-cond { font:bold 9px/1 Arial; color:var(--tx); margin-top:4px; }
  .single .bold-cond { font-size:7px; }
  .bold-biz { font:900 14px/1 Georgia,serif; color:var(--tx); margin-top:8px; text-shadow:0 1px 4px rgba(0,0,0,.4); }
  .single .bold-biz { font-size:11px; margin-top:4px; }
  .bold-extras { margin-top:6px; display:flex; flex-wrap:wrap; gap:4px; justify-content:center; }
  .bold-extra { font:bold 8px/1 Arial; color:var(--ac); background:rgba(0,0,0,.3); padding:3px 6px; border-radius:3px; }
  .single .bold-extra { font-size:6px; }

  /* MINIMAL */
  .min-layout { display:flex; flex-direction:column; height:100%; background:#fff; }
  .min-header { padding:8px 10px 6px; }
  .min-name { font:900 16px/1.1 Georgia,serif; }
  .single .min-name { font-size:12px; }
  .min-contact { font:11px/1 Arial; color:#888; margin-top:3px; }
  .single .min-contact { font-size:7px; }
  .min-offers { flex:1; padding:6px 10px; display:flex; flex-direction:column; gap:4px; }
  .min-offer { padding:4px 8px; }
  .min-amt { font:900 18px/1.1 Arial; }
  .single .min-amt { font-size:14px; }
  .min-cond { font:11px/1.2 Arial; color:#666; margin-top:2px; }
  .single .min-cond { font-size:6px; }
  .min-img { height:30%; background-size:cover; background-position:center; }
  .single .min-img { height:0; display:none; }
  .min-layout .ad-fine { color:#888; }
</style>
