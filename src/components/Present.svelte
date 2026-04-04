<script>
  import { user } from '../lib/stores.js';
  import MeetingPrep from './MeetingPrep.svelte';

  let view = 'menu'; 

  const VIDEO_LINKS = {
    'register-tape': {
      presentation: 'https://docs.google.com/presentation/d/1Xs60nX3i6MJkC81GgnK-50jBrkWVPu06xRpmv8z4PIc/edit?usp=sharing',
      explainer: 'https://youtu.be/_gdlyEszHfY?si=0_kHou89WrMhvNY_'
    },
    'cartvertising': {
      presentation: 'https://www.youtube.com/watch?v=PduxHWy8sMc',
      explainer: 'https://www.youtube.com/watch?v=PduxHWy8sMc'
    },
    'digitalboost': {
      presentation: 'https://www.youtube.com/watch?v=PduxHWy8sMc',
      explainer: 'https://drive.google.com/file/d/1_QyAlgZRy1bKJSKC1058260d0jPccVTM/view?usp=share_link',
      connectionHub: 'https://drive.google.com/file/d/199IkMptOlSYviHScKNKUlqELQOhWFxnB/view?usp=sharing'
    },
    'findlocal': {
      explainer: 'https://youtu.be/5CvlhJHssMs?si=WSmoTeh6adRlc-YW'
    },
    'reviewboost': {
      explainer: 'https://youtu.be/PBpbUiIoYcM?si=XEGeu1hmbI-zAf7j'
    },
    'loyaltyboost': {
      explainer: 'https://youtu.be/gthLw2eQF1Y?si=9ggkdGIpcqlDHKaP'
    }
  };

  const products = [
    { id: 'register-tape', name: 'Register Tape', icon: '🧾',
      desc: 'Ads printed on grocery store register tape — reaches every customer at checkout',
      features: ['Prints on every receipt', 'Targeted by store location', 'Coupon-style offers', '3-month cycles (A/B/C)'] },
    { id: 'cartvertising', name: 'Cartvertising', icon: '🛒',
      desc: 'Full-color ads displayed on shopping carts — seen throughout the entire shopping trip',
      features: ['Eye-level visibility', 'Full-color printing', 'High impression count', 'Cart-mounted displays'] },
    { id: 'digital', name: 'Digital', icon: '📱',
      desc: 'Digital marketing solutions for local businesses',
      features: ['DigitalBoost — Geofence Ads', 'FindLocal — Directory Listings', 'ReviewBoost — Reputation', 'LoyaltyBoost — Retention'] }
  ];

  // Register Tape tiers
  const tapeTiers = {
    coop: { name: 'Manager Approved Co-Op', emoji: '🎯', desc: 'Pre-approved by store management',
      pricing: { 'Monthly': 'Base + $125', '3-Month': 'Base × 0.90 + $125 (10% off)', '6-Month': 'Base × 0.925 + $125 (7.5% off)', 'Paid-in-Full': 'Base × 0.85 + $125 (15% off)' } },
    exclusive: { name: 'Exclusive Category', emoji: '🏆', desc: 'Sole advertising category protection',
      pricing: { 'Monthly': 'Base + $125', '3-Month': 'Base + $125', '6-Month': 'Base + $125', 'Paid-in-Full': 'Base × 0.95 (5% off, no production)' } },
    contractor: { name: 'Contractors', emoji: '🔧', desc: 'Special contractor pricing',
      pricing: { '3-Month': 'Base + $125', 'Paid-in-Full': 'Base × 0.95 (5% off, no production)' } }
  };

  // Cartvertising packages
  const cartPackages = [
    { name: '20% Front OR Directory', price: '$2,995' },
    { name: '40% (20% Front + 20% Directory)', price: '$4,795' },
    { name: '60% (40% Front + 20% Directory)', price: '$5,995' },
    { name: '80% (40% Front + 40% Directory)', price: '$7,395' },
    { name: '100% (60% Front + 40% Directory)', price: '$8,795' },
    { name: '200% (100% Both Sides)', price: '$12,995' },
    { name: 'Header 50% (Every Other Cart)', price: '$2,995' },
    { name: 'Header 100% (Every Cart)', price: '$4,795' },
  ];

  // Digital products
  const digitalProducts = {
    digitalboost: { name: 'DigitalBoost', emoji: '🚀', desc: 'Geofence pin delivering digital banner ad impressions',
      details: [
        { label: 'Standalone', value: '240,000 impressions (20K/mo × 12)' },
        { label: 'Bundled w/ Tape or Cart', value: '360,000 impressions (30K/mo × 12)' },
        { label: 'Standard Pricing', value: '$3,600/pin + $395 production (up to 5 pins)' },
        { label: 'Co-Op Pricing', value: '$2,400/pin + $395 production (up to 5 pins)' },
      ],
      examples: [
        { pins: 1, standard: '$3,995', coop: '$2,795' },
        { pins: 2, standard: '$7,595', coop: '$5,195' },
        { pins: 3, standard: '$11,195', coop: '$7,595' },
        { pins: 5, standard: '$18,395', coop: '$12,395' },
      ]
    },
    findlocal: { name: 'FindLocal', emoji: '📍', desc: 'Local SEO & listings across 50+ directories',
      price: '$695/location', note: '+$195 if Google profile assistance needed',
      analysisUrl: 'https://www.indoormedia.com/local-listing-management/',
      features: ['50+ business listing submissions', 'NAP optimization', 'Hours, photos, categories management', 'Monthly progress reports', 'Google Business Profile sync'] },
    reviewboost: { name: 'ReviewBoost', emoji: '⭐', desc: 'Automated review request campaign via Email & SMS',
      price: '$695 (4-month campaign)', note: '+$495 per additional 4-month campaign',
      features: ['ReviewKit included', 'Automated 4-month campaign', 'Email & SMS review requests', 'Up to 4,000 contacts per campaign'] },
    loyaltyboost: { name: 'LoyaltyBoost', emoji: '💎', desc: 'Annual loyalty/rewards campaign per location',
      price: '$3,600/year', note: '$495 production fee (−$125 if renewal w/ testimonial)',
      features: ['Annual loyalty campaign', 'Rewards program setup', 'Paid-in-Full: 5% discount', '6-Month or 12-Month payment options'] },
  };

  let selectedTier = null;
  let selectedDigital = null;

  function addToCart(name, price, details) {
    let cart = [];
    try { cart = JSON.parse(localStorage.getItem('indoormedia_cart') || '[]'); } catch {}
    cart.push({ id: Date.now(), name, price, details, addedAt: new Date().toISOString() });
    localStorage.setItem('indoormedia_cart', JSON.stringify(cart));
    alert('Added to cart: ' + name);
  }
</script>

<div class="present">
  {#if view === 'menu'}
    <h2>🎤 Present</h2>
    <p class="subtitle">Choose a product to present to your prospect</p>
    <button class="prep-card" on:click={() => view = 'meeting-prep'}>
      <div class="prep-left">
        <div class="prep-icon">📋</div>
        <div>
          <h3>Meeting Prep</h3>
          <p>Look up a business, find matching testimonials, and prep for your meeting</p>
        </div>
      </div>
      <span class="arrow">→</span>
    </button>

    <div class="product-grid">
      {#each products as p}
        <button class="product-card" on:click={() => view = p.id}>
          <div class="product-icon">{p.icon}</div>
          <h3>{p.name}</h3>
          <p class="product-desc">{p.desc}</p>
          <ul class="product-features">{#each p.features as f}<li>{f}</li>{/each}</ul>
          <span class="tap-hint">Tap to present →</span>
        </button>
      {/each}
    </div>

  <!-- ========== REGISTER TAPE ========== -->
  {:else if view === 'register-tape'}
    <button class="back-btn" on:click={() => { view = selectedTier ? 'register-tape' : 'menu'; selectedTier = null; }}>← {selectedTier ? 'Back to Tiers' : 'Back'}</button>

    {#if !selectedTier}
      <h2>🧾 Register Tape Advertising</h2>

      <div class="video-links">
        <a href={VIDEO_LINKS['register-tape'].presentation} target="_blank" class="video-btn">🎬 Sales Presentation</a>
        <a href={VIDEO_LINKS['register-tape'].explainer} target="_blank" class="video-btn">📹 Explainer Video</a>
      </div>

      <div class="value-props">
        <div class="value-card"><span class="vi">🎯</span><h4>100% Reach</h4><p>Every customer gets a receipt — your ad is seen by every single shopper</p></div>
        <div class="value-card"><span class="vi">📍</span><h4>Hyper-Local</h4><p>Target customers shopping at stores near your business</p></div>
        <div class="value-card"><span class="vi">💰</span><h4>Affordable</h4><p>Fraction of the cost of direct mail, billboards, or digital ads</p></div>
        <div class="value-card"><span class="vi">📊</span><h4>Trackable</h4><p>Coupon codes let you measure exactly how many customers respond</p></div>
      </div>

      <div class="section-divider"><h3>📐 Ad Sizes</h3></div>
      <div class="size-comparison">
        <div class="size-box"><div class="size-preview single-sz"><span>SINGLE</span></div><p><strong>Single Ad</strong></p><p class="dims">2.75" × 1.75"</p></div>
        <div class="size-box"><div class="size-preview double-sz"><span>DOUBLE</span></div><p><strong>Double Ad</strong></p><p class="dims">2.75" × 3.6"</p></div>
      </div>

      <div class="section-divider"><h3>💳 Pricing Tiers</h3></div>
      {#each Object.entries(tapeTiers) as [key, tier]}
        <button class="tier-card" on:click={() => selectedTier = key}>
          <div class="tier-left"><span class="tier-emoji">{tier.emoji}</span><div><h4>{tier.name}</h4><p>{tier.desc}</p></div></div>
          <span class="arrow">→</span>
        </button>
      {/each}
    {:else}
      <h2>{tapeTiers[selectedTier].emoji} {tapeTiers[selectedTier].name}</h2>
      <p class="subtitle">{tapeTiers[selectedTier].desc}</p>
      <div class="pricing-card">
        <h4>Payment Plans</h4>
        {#each Object.entries(tapeTiers[selectedTier].pricing) as [plan, formula]}
          <div class="pricing-row"><span class="plan">{plan}</span><span class="formula">{formula}</span></div>
        {/each}
      </div>
      <button class="cart-btn" on:click={() => addToCart('Register Tape — ' + tapeTiers[selectedTier].name, 'Store-based', selectedTier)}>🛒 Add to Cart</button>
    {/if}
    <div style="height:80px;"></div>

  <!-- ========== CARTVERTISING ========== -->
  {:else if view === 'cartvertising'}
    <button class="back-btn" on:click={() => view = 'menu'}>← Back</button>
    <h2>🛒 Cartvertising</h2>

    <div class="video-links">
      <a href={VIDEO_LINKS['cartvertising'].presentation} target="_blank" class="video-btn">🎬 Sales Presentation</a>
      <a href={VIDEO_LINKS['cartvertising'].explainer} target="_blank" class="video-btn">📹 Explainer Video</a>
    </div>

    <div class="value-props">
      <div class="value-card"><span class="vi">👁️</span><h4>Eye-Level</h4><p>Ads mounted at eye level on shopping carts — impossible to miss</p></div>
      <div class="value-card"><span class="vi">⏱️</span><h4>40+ Minutes</h4><p>Average shopping trip keeps your ad with them the whole time</p></div>
      <div class="value-card"><span class="vi">🎨</span><h4>Full Color</h4><p>High-quality, full-color printing for maximum brand impact</p></div>
      <div class="value-card"><span class="vi">🔄</span><h4>Massive Reach</h4><p>Thousands of shoppers use each cart — huge impression volume</p></div>
    </div>

    <div class="section-divider"><h3>📦 Packages (6-Month Campaigns)</h3></div>
    {#each cartPackages as pkg}
      <div class="package-row">
        <div><h4>{pkg.name}</h4></div>
        <div class="pkg-right"><span class="pkg-price">{pkg.price}</span>
          <button class="cart-sm" on:click={() => addToCart('Cartvertising — ' + pkg.name, pkg.price, '6-month')}>🛒</button>
        </div>
      </div>
    {/each}
    <div style="height:80px;"></div>

  <!-- ========== DIGITAL ========== -->
  {:else if view === 'digital'}
    <button class="back-btn" on:click={() => { if (selectedDigital) { selectedDigital = null; } else { view = 'menu'; } }}>← {selectedDigital ? 'Back to Digital' : 'Back'}</button>

    {#if !selectedDigital}
      <h2>📱 Digital Solutions</h2>
      <div class="digital-grid">
        {#each Object.entries(digitalProducts) as [key, dp]}
          <button class="digital-card" on:click={() => selectedDigital = key}>
            <span class="dp-emoji">{dp.emoji}</span>
            <h4>{dp.name}</h4>
            <p>{dp.desc}</p>
            {#if VIDEO_LINKS[key]?.explainer}
              <span class="vid-badge">📹 Video</span>
            {/if}
          </button>
        {/each}
      </div>

    {:else if selectedDigital === 'digitalboost'}
      <h2>🚀 DigitalBoost</h2>
      <p class="subtitle">Geofence pin delivering digital banner ad impressions</p>
      <div class="video-links">
        <a href={VIDEO_LINKS.digitalboost.presentation} target="_blank" class="video-btn">🎬 Presentation</a>
        <a href={VIDEO_LINKS.digitalboost.explainer} target="_blank" class="video-btn">📹 Video</a>
        <a href={VIDEO_LINKS.digitalboost.connectionHub} target="_blank" class="video-btn">🔗 Hub</a>
      </div>
      <div class="pricing-card">
        {#each digitalProducts.digitalboost.details as d}
          <div class="pricing-row"><span class="plan">{d.label}</span><span class="formula">{d.value}</span></div>
        {/each}
      </div>
      <div class="section-divider"><h3>💰 Pricing Examples</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Pins</th><th>Standard</th><th>Co-Op</th></tr></thead>
        <tbody>{#each digitalProducts.digitalboost.examples as ex}<tr><td>{ex.pins}</td><td>{ex.standard}</td><td>{ex.coop}</td></tr>{/each}</tbody>
      </table></div>
      <button class="cart-btn" on:click={() => addToCart('DigitalBoost', '$3,600/pin', '240K impressions')}>🛒 Add to Cart</button>

    {:else}
      {@const dp = digitalProducts[selectedDigital]}
      <h2>{dp.emoji} {dp.name}</h2>
      <p class="subtitle">{dp.desc}</p>
      {#if VIDEO_LINKS[selectedDigital]?.explainer}
        <div class="video-links">
          <a href={VIDEO_LINKS[selectedDigital].explainer} target="_blank" class="video-btn">📹 Explainer Video</a>
        </div>
      {/if}
      <div class="pricing-card">
        <div class="pricing-row"><span class="plan">Price</span><span class="formula">{dp.price}</span></div>
        {#if dp.note}<div class="pricing-row"><span class="plan">Note</span><span class="formula">{dp.note}</span></div>{/if}
      </div>
      {#if dp.analysisUrl}
        <a href={dp.analysisUrl} target="_blank" class="analysis-btn">🔍 Run Local Listing Analysis</a>
      {/if}
      {#if dp.features}
        <div class="section-divider"><h3>✅ Features</h3></div>
        <ul class="feat-list">{#each dp.features as f}<li>✓ {f}</li>{/each}</ul>
      {/if}
      <button class="cart-btn" on:click={() => addToCart(dp.name, dp.price, dp.desc)}>🛒 Add to Cart</button>
    {/if}
    <div style="height:80px;"></div>

  {:else if view === 'meeting-prep'}
    <MeetingPrep onBack={() => view = 'menu'} />
  {/if}
</div>

<style>
  .present { }
  .subtitle { font-size:14px; color:var(--text-secondary); margin:0 0 16px; }
  .back-btn { background:none; border:none; color:var(--text-secondary); font-size:14px; cursor:pointer; padding:8px 0; }
  
  /* Meeting Prep card */
  .prep-card { display:flex; align-items:center; justify-content:space-between; width:100%; background:var(--card-bg); border:2px solid #CC0000; border-radius:16px; padding:18px; margin-bottom:20px; cursor:pointer; transition:all .2s; text-align:left; }
  .prep-card:hover { transform:translateY(-2px); box-shadow:0 4px 12px rgba(204,0,0,.15); }
  .prep-left { display:flex; align-items:center; gap:14px; }
  .prep-icon { font-size:36px; }
  .prep-card h3 { margin:0 0 4px; font-size:18px; font-weight:800; color:#CC0000; }
  .prep-card p { margin:0; font-size:13px; color:var(--text-secondary); line-height:1.3; }
  .arrow { font-size:20px; color:var(--text-tertiary); }
  
  /* Product cards */
  .product-grid { display:flex; flex-direction:column; gap:16px; }
  .product-card { background:var(--card-bg); border:2px solid var(--border-color); border-radius:16px; padding:20px; text-align:left; cursor:pointer; transition:all .2s; }
  .product-card:hover { border-color:#CC0000; transform:translateY(-2px); box-shadow:0 4px 12px rgba(0,0,0,.1); }
  .product-card:active { transform:scale(.98); }
  .product-icon { font-size:40px; margin-bottom:8px; }
  .product-card h3 { margin:0 0 6px; font-size:20px; font-weight:800; color:var(--text-primary); }
  .product-desc { font-size:13px; color:var(--text-secondary); margin:0 0 10px; line-height:1.4; }
  .product-features { margin:0 0 10px; padding-left:18px; font-size:12px; color:var(--text-tertiary); line-height:1.8; }
  .tap-hint { display:block; text-align:right; font-size:12px; color:var(--text-tertiary); margin-top:8px; }

  /* Video links */
  .video-links { display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap; }
  .video-btn { flex:1; min-width:80px; display:block; padding:10px 8px; background:var(--card-bg); border:2px solid var(--border-color); border-radius:10px; text-align:center; text-decoration:none; color:var(--text-primary); font-size:13px; font-weight:700; transition:all .2s; }
  .video-btn:hover { border-color:#CC0000; color:#CC0000; }

  /* Value props */
  .value-props { display:grid; grid-template-columns:repeat(2,1fr); gap:12px; margin:16px 0; }
  .value-card { background:var(--card-bg); border:2px solid var(--border-color); border-radius:12px; padding:14px; }
  .vi { font-size:28px; }
  .value-card h4 { margin:6px 0 4px; font-size:15px; font-weight:700; color:var(--text-primary); }
  .value-card p { margin:0; font-size:12px; color:var(--text-secondary); line-height:1.4; }

  /* Sizes */
  .section-divider { margin:20px 0 12px; }
  .section-divider h3 { font-size:17px; font-weight:700; }
  .size-comparison { display:flex; gap:16px; justify-content:center; }
  .size-box { text-align:center; flex:1; }
  .size-box p { margin:6px 0 0; font-size:14px; color:var(--text-primary); }
  .dims { font-size:12px !important; color:var(--text-secondary) !important; }
  .size-preview { background:#CC0000; color:#fff; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:14px; border-radius:4px; margin:0 auto; }
  .single-sz { width:140px; height:89px; }
  .double-sz { width:140px; height:183px; }

  /* Tiers */
  .tier-card { display:flex; align-items:center; justify-content:space-between; width:100%; background:var(--card-bg); border:2px solid var(--border-color); border-radius:12px; padding:14px; margin-bottom:10px; cursor:pointer; transition:border-color .2s; text-align:left; }
  .tier-card:hover { border-color:#CC0000; }
  .tier-left { display:flex; align-items:center; gap:12px; }
  .tier-emoji { font-size:28px; }
  .tier-card h4 { margin:0 0 2px; font-size:15px; color:var(--text-primary); }
  .tier-card p { margin:0; font-size:12px; color:var(--text-secondary); }
  .arrow { font-size:18px; color:var(--text-tertiary); }

  /* Pricing */
  .pricing-card { background:var(--card-bg); border:2px solid var(--border-color); border-radius:12px; padding:16px; margin-bottom:16px; }
  .pricing-card h4 { margin:0 0 10px; font-size:15px; color:var(--text-primary); }
  .pricing-row { display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid var(--border-color); gap:8px; }
  .pricing-row:last-child { border-bottom:none; }
  .plan { font-weight:700; font-size:13px; color:var(--text-primary); white-space:nowrap; }
  .formula { font-size:12px; color:var(--text-secondary); text-align:right; }

  /* Cart buttons */
  .cart-btn { width:100%; padding:13px; background:#CC0000; color:#fff; border:none; border-radius:10px; font-size:15px; font-weight:700; cursor:pointer; margin-top:8px; }
  .cart-btn:hover { background:#a00; }

  /* Packages */
  .package-row { display:flex; justify-content:space-between; align-items:center; background:var(--card-bg); border:2px solid var(--border-color); border-radius:10px; padding:12px 14px; margin-bottom:8px; }
  .package-row h4 { margin:0; font-size:13px; color:var(--text-primary); }
  .pkg-right { display:flex; align-items:center; gap:10px; }
  .pkg-price { font-size:15px; font-weight:800; color:#CC0000; }
  .cart-sm { background:#CC0000; color:#fff; border:none; border-radius:6px; padding:6px 10px; cursor:pointer; font-size:14px; }

  /* Digital */
  .digital-grid { display:flex; flex-direction:column; gap:12px; }
  .digital-card { background:var(--card-bg); border:2px solid var(--border-color); border-radius:12px; padding:16px; text-align:left; cursor:pointer; transition:all .2s; }
  .digital-card:hover { border-color:#CC0000; }
  .dp-emoji { font-size:28px; }
  .digital-card h4 { margin:6px 0 4px; font-size:16px; color:var(--text-primary); }
  .digital-card p { margin:0; font-size:13px; color:var(--text-secondary); line-height:1.4; }
  .vid-badge { display:inline-block; margin-top:8px; font-size:11px; font-weight:700; color:#CC0000; background:rgba(204,0,0,.1); padding:2px 8px; border-radius:4px; }

  /* Table */
  .table-wrap { overflow-x:auto; margin-bottom:16px; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th { background:var(--bg-secondary,#f5f5f5); padding:8px; text-align:left; font-weight:700; border-bottom:2px solid var(--border-color); color:var(--text-secondary); }
  td { padding:8px; border-bottom:1px solid var(--border-color); color:var(--text-primary); }

  /* Features */
  .feat-list { padding-left:0; list-style:none; }
  .feat-list li { padding:6px 0; font-size:13px; color:var(--text-primary); border-bottom:1px solid var(--border-color); }
  .feat-list li:last-child { border-bottom:none; }
  .analysis-btn { display:block; width:100%; padding:14px; background:#1565C0; color:#fff; border:none; border-radius:10px; font-size:15px; font-weight:700; text-align:center; text-decoration:none; margin:12px 0; box-sizing:border-box; }
  .analysis-btn:hover { background:#0D47A1; }
</style>
