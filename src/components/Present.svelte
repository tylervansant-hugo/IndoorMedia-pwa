<script>
  import SampleAdGenerator from './SampleAdGenerator.svelte';
  import { user } from '../lib/stores.js';

  let view = 'menu'; // menu, register-tape, cartvertising, digital, ad-generator

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
      explainer: 'https://drive.google.com/file/d/1_QyAlgZRy1bKJSKC1058260d0jPccVTM/view?usp=share_link'
    },
    'findlocal': {
      presentation: 'https://youtu.be/5CvlhJHssMs?si=WSmoTeh6adRlc-YW',
      explainer: 'https://youtu.be/5CvlhJHssMs?si=WSmoTeh6adRlc-YW'
    },
    'reviewboost': {
      presentation: 'https://youtu.be/PBpbUiIoYcM?si=XEGeu1hmbI-zAf7j',
      explainer: 'https://youtu.be/PBpbUiIoYcM?si=XEGeu1hmbI-zAf7j'
    },
    'loyaltyboost': {
      presentation: 'https://youtu.be/gthLw2eQF1Y?si=9ggkdGIpcqlDHKaP',
      explainer: 'https://youtu.be/gthLw2eQF1Y?si=9ggkdGIpcqlDHKaP'
    }
  };

  const products = [
    {
      id: 'register-tape',
      name: 'Register Tape',
      icon: '🧾',
      desc: 'Ads printed on grocery store register tape — reaches every customer at checkout',
      features: ['Prints on every receipt', 'Targeted by store location', 'Coupon-style offers', '3-month cycles (A/B/C)'],
      hasAdGen: true
    },
    {
      id: 'cartvertising',
      name: 'Cartvertising',
      icon: '🛒',
      desc: 'Full-color ads displayed on shopping carts — seen throughout the entire shopping trip',
      features: ['Eye-level visibility', 'Full-color printing', 'High impression count', 'Cart-mounted displays'],
      hasAdGen: false
    },
    {
      id: 'digital',
      name: 'Digital',
      icon: '📱',
      desc: 'Digital marketing solutions for local businesses',
      features: ['DigitalBoost — Local SEO', 'FindLocal — Directory listings', 'ReviewBoost — Reputation management', 'LoyaltyBoost — Customer retention'],
      hasAdGen: false
    }
  ];
</script>

<div class="present-container">
  {#if view === 'menu'}
    <h2>🎤 Present</h2>
    <p class="present-subtitle">Choose a product to present to your prospect</p>
    
    <div class="product-grid">
      {#each products as product}
        <button class="product-card" on:click={() => view = product.id}>
          <div class="product-icon">{product.icon}</div>
          <h3>{product.name}</h3>
          <p class="product-desc">{product.desc}</p>
          <ul class="product-features">
            {#each product.features as feature}
              <li>{feature}</li>
            {/each}
          </ul>
          {#if product.hasAdGen}
            <span class="ad-gen-badge">✨ Sample Ad Generator</span>
          {/if}
          <span class="tap-hint">Tap to present →</span>
        </button>
      {/each}
    </div>

  {:else if view === 'register-tape'}
    <button class="back-btn" on:click={() => view = 'menu'}>← Back to Products</button>
    <h2>🧾 Register Tape Advertising</h2>
    
    <div class="product-detail">
      <div class="value-props">
        <div class="value-card">
          <span class="value-icon">🎯</span>
          <h4>100% Reach</h4>
          <p>Every customer gets a receipt — your ad is seen by every single shopper</p>
        </div>
        <div class="value-card">
          <span class="value-icon">📍</span>
          <h4>Hyper-Local</h4>
          <p>Target customers shopping at stores near your business</p>
        </div>
        <div class="value-card">
          <span class="value-icon">💰</span>
          <h4>Affordable</h4>
          <p>Fraction of the cost of direct mail, billboards, or digital ads</p>
        </div>
        <div class="value-card">
          <span class="value-icon">📊</span>
          <h4>Trackable</h4>
          <p>Coupon codes let you measure exactly how many customers respond</p>
        </div>
      </div>

      <div class="video-links">
        <a href={VIDEO_LINKS['register-tape'].presentation} target="_blank" class="video-btn">🎬 Sales Presentation</a>
        <a href={VIDEO_LINKS['register-tape'].explainer} target="_blank" class="video-btn">📹 Explainer Video</a>
      </div>

      <div class="section-divider">
        <h3>📐 Ad Sizes</h3>
        <div class="size-comparison">
          <div class="size-box">
            <div class="size-preview single-size">
              <span>SINGLE</span>
            </div>
            <p><strong>Single Ad</strong></p>
            <p class="size-dims">2.75" × 1.75"</p>
            <p class="size-note">Great for simple offers</p>
          </div>
          <div class="size-box">
            <div class="size-preview double-size">
              <span>DOUBLE</span>
            </div>
            <p><strong>Double Ad</strong></p>
            <p class="size-dims">2.75" × 3.6"</p>
            <p class="size-note">More room for branding & multiple offers</p>
          </div>
        </div>
      </div>

      <button class="cta-btn" on:click={() => view = 'ad-generator'}>
        ✨ Generate Sample Ad for This Client
      </button>
      <div style="height: 80px;"></div>
    </div>

  {:else if view === 'ad-generator'}
    <button class="back-btn" on:click={() => view = 'register-tape'}>← Back to Register Tape</button>
    <h2>✨ Sample Ad Generator</h2>
    <SampleAdGenerator />

  {:else if view === 'cartvertising'}
    <button class="back-btn" on:click={() => view = 'menu'}>← Back to Products</button>
    <h2>🛒 Cartvertising</h2>
    <div class="product-detail">
      <div class="video-links">
        <a href={VIDEO_LINKS['cartvertising'].presentation} target="_blank" class="video-btn">🎬 Sales Presentation</a>
        <a href={VIDEO_LINKS['cartvertising'].explainer} target="_blank" class="video-btn">📹 Explainer Video</a>
      </div>
      <div class="value-props">
        <div class="value-card">
          <span class="value-icon">👁️</span>
          <h4>Eye-Level Visibility</h4>
          <p>Ads mounted at eye level on shopping carts — impossible to miss</p>
        </div>
        <div class="value-card">
          <span class="value-icon">⏱️</span>
          <h4>Extended Exposure</h4>
          <p>Average shopping trip is 40+ minutes — your ad is with them the whole time</p>
        </div>
        <div class="value-card">
          <span class="value-icon">🎨</span>
          <h4>Full Color</h4>
          <p>High-quality, full-color printing for maximum brand impact</p>
        </div>
        <div class="value-card">
          <span class="value-icon">🔄</span>
          <h4>Repeat Impressions</h4>
          <p>Thousands of shoppers use each cart — massive impression volume</p>
        </div>
      </div>
      <div style="height: 80px;"></div>
    </div>

  {:else if view === 'digital'}
    <button class="back-btn" on:click={() => view = 'menu'}>← Back to Products</button>
    <h2>📱 Digital Solutions</h2>
    <div class="product-detail">
      <div class="digital-products">
        <div class="digital-card">
          <h4>🚀 DigitalBoost</h4>
          <p>Local SEO optimization — get found on Google when customers search for your services</p>
          <div class="digital-links">
            <a href={VIDEO_LINKS['digitalboost'].explainer} target="_blank" class="video-btn-sm">📹 Video</a>
            <a href={VIDEO_LINKS['digitalboost'].presentation} target="_blank" class="video-btn-sm">🎬 Present</a>
          </div>
        </div>
        <div class="digital-card">
          <h4>📍 FindLocal</h4>
          <p>Directory listings across 50+ platforms — consistent NAP (Name, Address, Phone) everywhere</p>
          <div class="digital-links">
            <a href={VIDEO_LINKS['findlocal'].explainer} target="_blank" class="video-btn-sm">📹 Video</a>
          </div>
        </div>
        <div class="digital-card">
          <h4>⭐ ReviewBoost</h4>
          <p>Reputation management — generate and respond to reviews automatically</p>
          <div class="digital-links">
            <a href={VIDEO_LINKS['reviewboost'].explainer} target="_blank" class="video-btn-sm">📹 Video</a>
          </div>
        </div>
        <div class="digital-card">
          <h4>🎁 LoyaltyBoost</h4>
          <p>Customer retention program — keep customers coming back with rewards</p>
          <div class="digital-links">
            <a href={VIDEO_LINKS['loyaltyboost'].explainer} target="_blank" class="video-btn-sm">📹 Video</a>
          </div>
        </div>
      </div>
      <div style="height: 80px;"></div>
    </div>
  {/if}
</div>

<style>
  .present-container { padding: 0; }
  .present-subtitle { font-size: 14px; color: var(--text-secondary); margin: -4px 0 20px; }
  
  .back-btn { background: none; border: none; color: var(--text-secondary); font-size: 14px; cursor: pointer; padding: 8px 0; margin-bottom: 8px; }
  
  .product-grid { display: flex; flex-direction: column; gap: 16px; }
  
  .product-card { background: var(--card-bg); border: 2px solid var(--border-color); border-radius: 16px; padding: 20px; text-align: left; cursor: pointer; transition: all 0.2s; position: relative; }
  .product-card:hover { border-color: #CC0000; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
  .product-card:active { transform: scale(0.98); }
  
  .product-icon { font-size: 40px; margin-bottom: 8px; }
  .product-card h3 { margin: 0 0 6px; font-size: 20px; font-weight: 800; color: var(--text-primary); }
  .product-desc { font-size: 13px; color: var(--text-secondary); margin: 0 0 10px; line-height: 1.4; }
  .product-features { margin: 0 0 10px; padding-left: 18px; font-size: 12px; color: var(--text-tertiary); line-height: 1.8; }
  
  .ad-gen-badge { display: inline-block; background: rgba(204, 0, 0, 0.1); color: #CC0000; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 4px; }
  .tap-hint { display: block; text-align: right; font-size: 12px; color: var(--text-tertiary); margin-top: 8px; }
  
  /* Product Detail */
  .product-detail { }
  .value-props { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin: 16px 0; }
  .value-card { background: var(--card-bg); border: 2px solid var(--border-color); border-radius: 12px; padding: 16px; }
  .value-icon { font-size: 28px; }
  .value-card h4 { margin: 8px 0 4px; font-size: 15px; font-weight: 700; color: var(--text-primary); }
  .value-card p { margin: 0; font-size: 12px; color: var(--text-secondary); line-height: 1.4; }
  
  .section-divider { margin: 24px 0; }
  .section-divider h3 { font-size: 18px; font-weight: 700; margin-bottom: 12px; }
  
  .size-comparison { display: flex; gap: 16px; justify-content: center; }
  .size-box { text-align: center; flex: 1; }
  .size-box p { margin: 6px 0 0; font-size: 14px; color: var(--text-primary); }
  .size-dims { font-size: 12px !important; color: var(--text-secondary) !important; }
  .size-note { font-size: 11px !important; color: var(--text-tertiary) !important; }
  
  .size-preview { background: #CC0000; color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 14px; border-radius: 4px; margin: 0 auto; }
  .single-size { width: 140px; height: 86px; }
  .double-size { width: 140px; height: 183px; }
  
  .video-links { display: flex; gap: 10px; margin-bottom: 16px; }
  .video-btn { flex: 1; display: block; padding: 12px; background: var(--card-bg); border: 2px solid var(--border-color); border-radius: 10px; text-align: center; text-decoration: none; color: var(--text-primary); font-size: 14px; font-weight: 700; transition: all 0.2s; }
  .video-btn:hover { border-color: #CC0000; color: #CC0000; }
  
  .digital-links { display: flex; gap: 8px; margin-top: 10px; }
  .video-btn-sm { display: inline-block; padding: 6px 12px; background: rgba(204, 0, 0, 0.1); border-radius: 6px; text-decoration: none; color: #CC0000; font-size: 12px; font-weight: 700; }
  .video-btn-sm:hover { background: rgba(204, 0, 0, 0.2); }
  
  .cta-btn { width: 100%; padding: 14px; background: #CC0000; color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: 700; cursor: pointer; margin-top: 20px; }
  .cta-btn:hover { background: #aa0000; }
  
  /* Digital Products */
  .digital-products { display: flex; flex-direction: column; gap: 12px; margin-top: 16px; }
  .digital-card { background: var(--card-bg); border: 2px solid var(--border-color); border-radius: 12px; padding: 16px; }
  .digital-card h4 { margin: 0 0 6px; font-size: 16px; color: var(--text-primary); }
  .digital-card p { margin: 0; font-size: 13px; color: var(--text-secondary); line-height: 1.4; }
</style>
