<script>
  import { digitalPadAmount } from '../lib/stores.js';

  let view = 'main'; // main, product-detail, tier-detail, digital-menu, digital-detail
  let selectedProduct = null;
  let selectedTier = null;
  let selectedDigitalProduct = null;
  let localDigitalPad = 1200;
  
  // Sync store to local
  digitalPadAmount.subscribe(v => { localDigitalPad = v; });

  // Reactive pricing
  $: dbStandardPerPin = 2400 + localDigitalPad;
  $: dbCoopPerPin = 1200 + localDigitalPad;
  $: lbAnnual = 2400 + localDigitalPad;

  function fmt(n) { return '$' + n.toLocaleString(); }

  // DigitalBoost examples with dynamic padding
  $: dbExamples = [
    { pins: 1, standard: fmt(dbStandardPerPin + 395), coop: fmt(dbCoopPerPin + 395) },
    { pins: 2, standard: fmt(dbStandardPerPin * 2 + 395), coop: fmt(dbCoopPerPin * 2 + 395) },
    { pins: 3, standard: fmt(dbStandardPerPin * 3 + 395), coop: fmt(dbCoopPerPin * 3 + 395) },
    { pins: 5, standard: fmt(dbStandardPerPin * 5 + 395), coop: fmt(dbCoopPerPin * 5 + 395) },
  ];

  function updateDigitalPad(e) {
    const val = parseInt(e.target.value) || 0;
    localDigitalPad = val;
    digitalPadAmount.set(val);
  }

  let repName = '';
  // Load rep name from localStorage
  if (typeof localStorage !== 'undefined') {
    repName = localStorage.getItem('impro_rep_name') || '';
  }
  function saveRepName() {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('impro_rep_name', repName);
    }
  }

  // Product links synced from ProspectBot
  const PRODUCT_LINKS = {
    register_tape: {
      presentation: 'https://docs.google.com/presentation/d/1Xs60nX3i6MJkC81GgnK-50jBrkWVPu06xRpmv8z4PIc/edit?usp=sharing',
      explainer: 'https://youtu.be/_gdlyEszHfY?si=0_kHou89WrMhvNY_'
    },
    cartvertising: {
      presentation: 'https://docs.google.com/presentation/d/1xwIF4CaTp07AKunGaJysCSIGqN7VCdbL4fgOH3XEpl4/edit?usp=sharing',
      explainer: 'https://www.youtube.com/watch?v=PduxHWy8sMc'
    },
    digital: {
      presentation: 'https://docs.google.com/presentation/d/1xwIF4CaTp07AKunGaJysCSIGqN7VCdbL4fgOH3XEpl4/edit?usp=sharing',
      explainer: 'https://www.youtube.com/watch?v=PduxHWy8sMc',
      connectionHub: 'https://drive.google.com/file/d/199IkMptOlSYviHScKNKUlqELQOhWFxnB/view?usp=sharing'
    },
    digitalboost: {
      presentation: 'https://drive.google.com/file/d/1LvPJjBk1tvMYFoRAy-AUSugUXV82hUeM/view?usp=sharing',
      explainer: 'https://drive.google.com/file/d/1_QyAlgZRy1bKJSKC1058260d0jPccVTM/view?usp=share_link'
    },
    findlocal: {
      presentation: 'https://drive.google.com/file/d/1rRdFgRWvuzaPJCwxqKzTqtjDtd642DuS/view?usp=sharing',
      explainer: 'https://youtu.be/5CvlhJHssMs?si=WSmoTeh6adRlc-YW'
    },
    reviewboost: {
      presentation: 'https://drive.google.com/file/d/12hP-Ip7t9vHjBNFctj2X1AiatxS5O1LH/view?usp=sharing',
      explainer: 'https://youtu.be/PBpbUiIoYcM?si=XEGeu1hmbI-zAf7j'
    },
    loyaltyboost: {
      presentation: 'https://drive.google.com/file/d/1BYpsPLnAC2TRfsaQGuMBytaOYAxuNYMK/view?usp=sharing',
      explainer: 'https://youtu.be/gthLw2eQF1Y?si=9ggkdGIpcqlDHKaP'
    }
  };

  let copyFeedback = '';

  function copyProductPackage(productKey, subKey = null, tierKey = null) {
    let text = '';
    const sig = repName ? `\n— ${repName}, IndoorMedia` : '\n— IndoorMedia';

    if (productKey === 'register_tape' && tierKey) {
      const tier = PRODUCTS.register_tape.tiers[tierKey];
      const links = PRODUCT_LINKS.register_tape;
      text = `🧾 Register Tape — ${tier.name}\n${tier.desc}\n\n`;
      text += `💰 Payment Plans:\n`;
      for (const [plan, formula] of Object.entries(tier.pricing)) {
        text += `✅ ${plan.charAt(0).toUpperCase() + plan.slice(1)}: ${formula}\n`;
      }
      text += `\n🎥 See how it works: ${links.explainer}\n📊 Presentation: ${links.presentation}`;
      text += sig;
    } else if (productKey === 'register_tape') {
      const links = PRODUCT_LINKS.register_tape;
      text = `🧾 Register Tape — Checkout Advertising\nHigh-visibility promotional strips seen by every customer at checkout!\n\n`;
      text += `Available Tiers:\n`;
      for (const [k, tier] of Object.entries(PRODUCTS.register_tape.tiers)) {
        text += `✅ ${tier.emoji} ${tier.name} — ${tier.desc}\n`;
      }
      text += `\n🎥 See how it works: ${links.explainer}\n📊 Presentation: ${links.presentation}`;
      text += sig;
    } else if (productKey === 'cartvertising') {
      const links = PRODUCT_LINKS.cartvertising;
      text = `🛒 Cartvertising — Shopping Cart Advertising\nYour brand on every cart, seen by every shopper — 6-month campaigns!\n\n`;
      for (const [k, pkg] of Object.entries(PRODUCTS.cartvertising.packages)) {
        text += `✅ ${pkg.name} — ${pkg.price}\n`;
      }
      text += `\n🎥 See how it works: ${links.explainer}\n📊 Presentation: ${links.presentation}`;
      text += sig;
    } else if (productKey === 'digitalboost') {
      const links = PRODUCT_LINKS.digitalboost;
      text = `🚀 DigitalBoost — Digital Geofencing\nYour ad delivered to phones within a targeted radius of your business!\n\n`;
      text += `✅ 240,000+ ad impressions\n✅ Geofence pin at your location\n✅ Digital banner ads on mobile apps & websites\n✅ Monthly performance reports\n\n`;
      text += `💰 Starting at ${fmt(dbStandardPerPin)} per pin (standard)\n`;
      text += `💰 Co-Op pricing: ${fmt(dbCoopPerPin)} per pin\n`;
      text += `💰 Production: $395 (covers up to 5 pins)\n\n`;
      text += `📊 Pricing Examples:\n`;
      for (const ex of dbExamples) {
        text += `• ${ex.pins} pin${ex.pins > 1 ? 's' : ''}: ${ex.standard} (standard) / ${ex.coop} (co-op)\n`;
      }
      text += `\n🎥 See how it works: ${links.explainer}\n📊 Presentation: ${links.presentation}`;
      text += sig;
    } else if (productKey === 'findlocal') {
      const fl = PRODUCTS.digital.subproducts.findlocal;
      const links = PRODUCT_LINKS.findlocal;
      text = `📍 FindLocal — Local SEO & Listings\nGet found online across 50+ directories!\n\n`;
      for (const f of fl.features) { text += `✅ ${f}\n`; }
      text += `\n💰 ${fl.pricing}\n💰 ${fl.googleProfileAssistance}\n`;
      text += `\n🎥 See how it works: ${links.explainer}\n📊 Presentation: ${links.presentation}`;
      text += sig;
    } else if (productKey === 'reviewboost') {
      const rb = PRODUCTS.digital.subproducts.reviewboost;
      const links = PRODUCT_LINKS.reviewboost;
      text = `⭐ ReviewBoost — Automated Review Requests\nBoost your online reputation with automated Email & SMS review campaigns!\n\n`;
      for (const f of rb.features) { text += `✅ ${f}\n`; }
      text += `\n💰 ${rb.pricing} (${rb.contacts})\n💰 Additional campaigns: ${rb.additional}\n`;
      text += `\n🎥 See how it works: ${links.explainer}\n📊 Presentation: ${links.presentation}`;
      text += sig;
    } else if (productKey === 'loyaltyboost') {
      const links = PRODUCT_LINKS.loyaltyboost;
      text = `💎 LoyaltyBoost — Customer Loyalty Program\nKeep customers coming back with an annual loyalty/rewards campaign!\n\n`;
      text += `✅ Annual loyalty campaign per location\n✅ Rewards program setup\n✅ Customer retention focus\n\n`;
      text += `💰 ${fmt(lbAnnual)}/year\n💰 Production: $495\n\n`;
      text += `Payment Options:\n`;
      const lb = PRODUCTS.digital.subproducts.loyaltyboost;
      for (const o of lb.paymentOptions) { text += `• ${o}\n`; }
      text += `\n🎥 See how it works: ${links.explainer}\n📊 Presentation: ${links.presentation}`;
      text += sig;
    }

    if (!text) return;

    const feedbackKey = productKey + (tierKey || '') + (subKey || '');

    // Try native Share API first (mobile — lets you pick text/email/etc directly)
    if (navigator.share) {
      navigator.share({ text }).then(() => {
        copyFeedback = feedbackKey;
        setTimeout(() => { copyFeedback = ''; }, 2000);
      }).catch((err) => {
        // User cancelled share — that's fine, try clipboard instead
        if (err.name !== 'AbortError') {
          clipboardCopy(text, feedbackKey);
        }
      });
    } else {
      clipboardCopy(text, feedbackKey);
    }
  }

  function clipboardCopy(text, feedbackKey) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        copyFeedback = feedbackKey;
        setTimeout(() => { copyFeedback = ''; }, 2000);
      }).catch(() => textareaCopy(text, feedbackKey));
    } else {
      textareaCopy(text, feedbackKey);
    }
  }

  function textareaCopy(text, feedbackKey) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    ta.style.top = '0';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try { document.execCommand('copy'); } catch {}
    document.body.removeChild(ta);
    copyFeedback = feedbackKey;
    setTimeout(() => { copyFeedback = ''; }, 2000);
  }

  function addToCart(name, price, details) {
    let cart = [];
    try { cart = JSON.parse(localStorage.getItem('indoormedia_cart') || '[]'); } catch {}
    cart.push({ id: Date.now(), name, price, details, addedAt: new Date().toISOString() });
    localStorage.setItem('indoormedia_cart', JSON.stringify(cart));
    try { window.dispatchEvent(new Event('cart-updated')); } catch {}
    alert('Added to cart: ' + name);
  }

  const PRODUCTS = {
    register_tape: {
      name: 'Register Tape',
      emoji: '🧾',
      desc: 'High-visibility promotional strips at checkout',
      tiers: {
        coop: {
          name: 'Manager Approved Co-Op',
          emoji: '🎯',
          desc: 'Pre-approved by store management',
          pricing: {
            monthly: 'Base + $125',
            '3month': 'Base × 0.90 + $125 (10% off)',
            '6month': 'Base × 0.925 + $125 (7.5% off)',
            pif: 'Base × 0.85 + $125 (15% off)'
          }
        },
        exclusive: {
          name: 'Exclusive Category',
          emoji: '🏆',
          desc: 'Sole advertising category protection',
          pricing: {
            monthly: 'Base + $125',
            '3month': 'Base + $125',
            '6month': 'Base + $125',
            pif: 'Base × 0.95 (5% off, no production)'
          }
        },
        contractor: {
          name: 'Contractors',
          emoji: '🔧',
          desc: 'Special contractor pricing',
          pricing: {
            '3month': 'Base + $125',
            pif: 'Base × 0.95 (5% off, no production)'
          }
        }
      }
    },
    cartvertising: {
      name: 'Cartvertising',
      emoji: '🛒',
      desc: 'Shopping cart advertising - 6-month campaigns',
      packages: {
        '20_single': { name: '20% Front OR Directory', price: '$2,995' },
        '40_both': { name: '40% (20% Front + 20% Directory)', price: '$4,795' },
        '60_both': { name: '60% (40% Front + 20% Directory)', price: '$5,995' },
        '80_both': { name: '80% (40% Front + 40% Directory)', price: '$7,395' },
        '100_both': { name: '100% (60% Front + 40% Directory)', price: '$8,795' },
        '200_both': { name: '200% (100% Both Sides)', price: '$12,995' },
        'header_50': { name: 'Header 50% (Every Other Cart)', price: '$2,995' },
        'header_100': { name: 'Header 100% (Every Cart)', price: '$4,795' }
      }
    },
    digital: {
      name: 'Digital Products',
      emoji: '📱',
      desc: 'Online advertising & customer engagement solutions',
      subproducts: {
        digitalboost: {
          name: 'DigitalBoost',
          emoji: '🚀',
          desc: 'Geofence pin delivering digital banner ad impressions',
          impressions_standalone: 240000,
          impressions_bundled: 360000,
          pricing: {
            standard: {
              per_pin: 3600,
              production: 395,
              production_covers: '5 pins'
            },
            coop: {
              per_pin: 2400,
              production: 395,
              production_covers: '5 pins',
              first_pin_total: 2795
            }
          },
          examples: [
            { pins: 1, standard: '$3,995', coop: '$2,795' },
            { pins: 2, standard: '$7,595', coop: '$5,195' },
            { pins: 3, standard: '$11,195', coop: '$7,595' },
            { pins: 5, standard: '$18,395', coop: '$12,395' }
          ]
        },
        findlocal: {
          name: 'FindLocal',
          emoji: '📍',
          desc: 'Local SEO & listings management across 50+ directories',
          pricing: '$695/location',
          googleProfileAssistance: '+$195 if Google profile assistance needed',
          features: [
            '50+ business listing submissions',
            'NAP optimization (name, address, phone)',
            'Hours, photos, categories management',
            'Automated monthly progress reports',
            'Google Business Profile sync'
          ]
        },
        reviewboost: {
          name: 'ReviewBoost',
          emoji: '⭐',
          desc: 'Automated review request campaign via Email & SMS',
          pricing: '$695 for 4-month campaign',
          contacts: 'Up to 4,000 contacts',
          additional: '+$495 per additional 4-month campaign',
          features: [
            'ReviewKit included',
            'Automated 4-month campaign',
            'Email & SMS review requests',
            'Up to 4,000 contacts per campaign'
          ]
        },
        loyaltyboost: {
          name: 'LoyaltyBoost',
          emoji: '💎',
          desc: 'Annual loyalty/rewards campaign per location',
          pricing: '$3,600/year',
          production: '$495 production fee',
          paymentOptions: [
            'Paid-in-Full: 5% discount on package + production',
            '6-Month: 6 equal payments',
            '12-Month: 12 equal payments'
          ],
          features: [
            'Annual loyalty campaign',
            'Rewards program setup',
            'Customer retention focus'
          ]
        }
      }
    }
  };

  function goBack() {
    if (view === 'digital-detail') {
      view = 'digital-menu';
      selectedDigitalProduct = null;
    } else if (view === 'digital-menu') {
      view = 'main';
      selectedProduct = null;
    } else if (view === 'tier-detail') {
      view = 'product-detail';
      selectedTier = null;
    } else if (view === 'product-detail') {
      view = 'main';
      selectedProduct = null;
    }
  }

  function selectProduct(key) {
    selectedProduct = key;
    if (key === 'digital') {
      view = 'digital-menu';
    } else {
      view = 'product-detail';
    }
  }

  function selectTier(tierKey) {
    selectedTier = tierKey;
    view = 'tier-detail';
  }

  function selectDigitalProduct(key) {
    selectedDigitalProduct = key;
    view = 'digital-detail';
  }
</script>

<div class="products-container">
  <!-- Main Menu -->
  {#if view === 'main'}
    <h2>📦 IndoorMedia Products</h2>
    <p class="subtitle">Premium in-store advertising solutions</p>

    <div class="button-grid">
      {#each Object.entries(PRODUCTS) as [key, product]}
        <button class="main-btn" on:click={() => selectProduct(key)}>
          <div class="btn-icon">{product.emoji}</div>
          <div class="btn-text">{product.name}</div>
          <div class="btn-desc">{product.desc}</div>
        </button>
      {/each}
    </div>
  {/if}

  <!-- Register Tape Detail -->
  {#if view === 'product-detail' && selectedProduct === 'register_tape'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>🧾 Register Tape</h2>
    <p class="detail-subtitle">High-visibility promotional strips at checkout</p>

    <div class="links-section">
      <a href={PRODUCT_LINKS.register_tape.presentation} target="_blank" class="link-btn">
        🎬 Sales Presentation
      </a>
      <a href={PRODUCT_LINKS.register_tape.explainer} target="_blank" class="link-btn">
        📹 Explainer Video
      </a>
    </div>

    <button class="share-btn" on:click={() => copyProductPackage('register_tape')}>
      {copyFeedback === 'register_tape' ? '✅ Sent!' : '📩 Send to Customer'}
    </button>

    <div class="tiers-list">
      {#each Object.entries(PRODUCTS.register_tape.tiers) as [tierKey, tier]}
        <button class="tier-card" on:click={() => selectTier(tierKey)}>
          <div class="tier-header">
            <span class="tier-emoji">{tier.emoji}</span>
            <div>
              <h4>{tier.name}</h4>
              <p class="tier-desc">{tier.desc}</p>
            </div>
          </div>
          <div class="arrow-right">→</div>
        </button>
      {/each}
    </div>
  {/if}

  <!-- Register Tape Tier Detail -->
  {#if view === 'tier-detail' && selectedProduct === 'register_tape' && selectedTier}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>{PRODUCTS.register_tape.tiers[selectedTier].name}</h2>

    <div class="detail-card">
      <p class="detail-desc">{PRODUCTS.register_tape.tiers[selectedTier].desc}</p>

      <div class="pricing-section">
        <h4>Payment Plans</h4>
        <div class="pricing-list">
          {#each Object.entries(PRODUCTS.register_tape.tiers[selectedTier].pricing) as [plan, formula]}
            <div class="pricing-item">
              <span class="plan-name">{plan.charAt(0).toUpperCase() + plan.slice(1)}</span>
              <span class="plan-formula">{formula}</span>
            </div>
          {/each}
        </div>
      </div>

      <button class="share-btn" on:click={() => copyProductPackage('register_tape', null, selectedTier)}>
        {copyFeedback === 'register_tape' + selectedTier ? '✅ Sent!' : '📩 Send to Customer'}
      </button>
      <button class="action-btn" on:click={() => addToCart('Register Tape - ' + PRODUCTS.register_tape.tiers[selectedTier].name, 'Store-based', selectedTier)}>🛒 Add to Cart</button>
    </div>
  {/if}

  <!-- Cartvertising Detail -->
  {#if view === 'product-detail' && selectedProduct === 'cartvertising'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>🛒 Cartvertising</h2>
    <p class="detail-subtitle">Shopping cart advertising - 6-month campaigns</p>

    <div class="links-section">
      <a href={PRODUCT_LINKS.cartvertising.presentation} target="_blank" class="link-btn">
        🎬 Sales Presentation
      </a>
      <a href={PRODUCT_LINKS.cartvertising.explainer} target="_blank" class="link-btn">
        📹 Explainer Video
      </a>
    </div>

    <button class="share-btn" on:click={() => copyProductPackage('cartvertising')}>
      {copyFeedback === 'cartvertising' ? '✅ Sent!' : '📩 Send to Customer'}
    </button>

    <div class="packages-list">
      {#each Object.entries(PRODUCTS.cartvertising.packages) as [key, pkg]}
        <div class="package-card">
          <div class="pkg-info">
            <h4>{pkg.name}</h4>
            <p class="package-price">{pkg.price}</p>
          </div>
          <button class="cart-add-btn" on:click={() => addToCart('Cartvertising - ' + pkg.name, pkg.price, '6-month campaign')}>🛒</button>
        </div>
      {/each}
    </div>
  {/if}

  <!-- Digital Products Menu -->
  {#if view === 'digital-menu'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>📱 Digital Products</h2>
    <p class="detail-subtitle">Online advertising & customer engagement solutions</p>

    <div class="settings-bar">
      <div class="setting-item">
        <label>💰 Digital Padding</label>
        <div class="input-row">
          <span>$</span>
          <input type="number" value={localDigitalPad} on:change={updateDigitalPad} min="0" step="100" class="pad-input" />
        </div>
      </div>
      <div class="setting-item">
        <label>👤 Rep Name</label>
        <input type="text" bind:value={repName} on:blur={saveRepName} placeholder="Your name" class="rep-input" />
      </div>
    </div>

    <div class="digital-grid">
      {#each Object.entries(PRODUCTS.digital.subproducts) as [key, product]}
        <button class="digital-card" on:click={() => selectDigitalProduct(key)}>
          <div class="digital-emoji">{product.emoji}</div>
          <h4>{product.name}</h4>
          <p class="digital-desc">{product.desc}</p>
        </button>
      {/each}
    </div>
  {/if}

  <!-- DigitalBoost Detail -->
  {#if view === 'digital-detail' && selectedDigitalProduct === 'digitalboost'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>🚀 DigitalBoost</h2>
    <p class="detail-subtitle">Geofence pin delivering digital banner ad impressions</p>

    <div class="links-section">
      <a href={PRODUCT_LINKS.digitalboost.presentation} target="_blank" class="link-btn">🎬 Sales Presentation</a>
      <a href={PRODUCT_LINKS.digitalboost.explainer} target="_blank" class="link-btn">📹 Explainer Video</a>
      <a href={PRODUCT_LINKS.digital.connectionHub} target="_blank" class="link-btn">🔗 Connection Hub</a>
    </div>

    <div class="detail-card">
      <div class="detail-section">
        <h4>Standalone — 240,000 Total Impressions</h4>
        <p class="detail-value">20,000/mo × 12 months</p>
        <p class="detail-note">or 40,000/mo × 6 months</p>
      </div>

      <div class="detail-section">
        <h4>Bundled with Tape or Cart — 360,000 Total Impressions</h4>
        <p class="detail-value">30,000/mo × 12 months</p>
        <p class="detail-note">or 60,000/mo × 6 months</p>
        <p class="detail-note" style="margin-top: 8px; font-style: italic;">Same total investment regardless of term length</p>
      </div>

      <div class="detail-section">
        <h4>Standard Pricing</h4>
        <p class="pricing-item">{fmt(dbStandardPerPin)} per pin</p>
        <p class="pricing-item">$395 production (covers up to 5 pins)</p>
      </div>

      <div class="detail-section">
        <h4>Manager-Approved Co-Op Pricing</h4>
        <p class="pricing-item">{fmt(dbCoopPerPin)} per pin</p>
        <p class="pricing-item">$395 production (covers up to 5 pins)</p>
      </div>

      <div class="detail-section">
        <h4>Pricing Examples</h4>
        <table class="pricing-table">
          <thead>
            <tr>
              <th>Pins</th>
              <th>Standard</th>
              <th>Co-Op</th>
            </tr>
          </thead>
          <tbody>
            {#each dbExamples as ex}
              <tr>
                <td>{ex.pins}</td>
                <td>{ex.standard}</td>
                <td>{ex.coop}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      
      <button class="share-btn" on:click={() => copyProductPackage('digitalboost')}>
        {copyFeedback === 'digitalboost' ? '✅ Sent!' : '📩 Send to Customer'}
      </button>
      <button class="action-btn" on:click={() => addToCart("DigitalBoost", fmt(dbStandardPerPin) + "/pin", "240K standalone / 360K bundled impressions")}>🛒 Add to Cart</button>
    </div>
  {/if}

  <!-- FindLocal Detail -->
  {#if view === 'digital-detail' && selectedDigitalProduct === 'findlocal'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>📍 FindLocal</h2>
    <p class="detail-subtitle">Local SEO & listings management across 50+ directories</p>

    <div class="links-section">
      <a href={PRODUCT_LINKS.findlocal.presentation} target="_blank" class="link-btn">🎬 Sales Presentation</a>
      <a href={PRODUCT_LINKS.findlocal.explainer} target="_blank" class="link-btn">📹 Explainer Video</a>
    </div>

    <div class="detail-card">
      <div class="detail-section">
        <h4>Pricing</h4>
        <p class="detail-value">$695/location</p>
        <p class="detail-note">+$195 if Google profile assistance needed</p>
      </div>

      <div class="detail-section">
        <h4>Features</h4>
        <ul class="features-list">
          {#each PRODUCTS.digital.subproducts.findlocal.features as feature}
            <li>✓ {feature}</li>
          {/each}
        </ul>
      </div>

      
      <button class="share-btn" on:click={() => copyProductPackage('findlocal')}>
        {copyFeedback === 'findlocal' ? '✅ Sent!' : '📩 Send to Customer'}
      </button>
      <button class="action-btn" on:click={() => addToCart("FindLocal", "$695/location", "50+ directory listings")}>🛒 Add to Cart</button>
    </div>
  {/if}

  <!-- ReviewBoost Detail -->
  {#if view === 'digital-detail' && selectedDigitalProduct === 'reviewboost'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>⭐ ReviewBoost</h2>
    <p class="detail-subtitle">Automated review request campaign via Email & SMS</p>

    <div class="links-section">
      <a href={PRODUCT_LINKS.reviewboost.presentation} target="_blank" class="link-btn">🎬 Sales Presentation</a>
      <a href={PRODUCT_LINKS.reviewboost.explainer} target="_blank" class="link-btn">📹 Explainer Video</a>
    </div>

    <div class="detail-card">
      <div class="detail-section">
        <h4>Base Campaign</h4>
        <p class="detail-value">$695</p>
        <p class="detail-note">4-month campaign, up to 4,000 contacts</p>
      </div>

      <div class="detail-section">
        <h4>Additional Campaigns</h4>
        <p class="detail-value">$495</p>
        <p class="detail-note">Per additional 4-month cycle (up to 4,000 extra contacts)</p>
      </div>

      <div class="detail-section">
        <h4>Includes</h4>
        <ul class="features-list">
          {#each PRODUCTS.digital.subproducts.reviewboost.features as feature}
            <li>✓ {feature}</li>
          {/each}
        </ul>
      </div>

      <button class="share-btn" on:click={() => copyProductPackage('reviewboost')}>
        {copyFeedback === 'reviewboost' ? '✅ Sent!' : '📩 Send to Customer'}
      </button>
      <button class="action-btn" on:click={() => addToCart("ReviewBoost", "$695", "4-month campaign, 4000 contacts")}>🛒 Add to Cart</button>
    </div>
  {/if}

  <!-- LoyaltyBoost Detail -->
  {#if view === 'digital-detail' && selectedDigitalProduct === 'loyaltyboost'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>💎 LoyaltyBoost</h2>
    <p class="detail-subtitle">Annual loyalty/rewards campaign per location</p>

    <div class="links-section">
      <a href={PRODUCT_LINKS.loyaltyboost.presentation} target="_blank" class="link-btn">🎬 Sales Presentation</a>
      <a href={PRODUCT_LINKS.loyaltyboost.explainer} target="_blank" class="link-btn">📹 Explainer Video</a>
    </div>

    <div class="detail-card">
      <div class="detail-section">
        <h4>Annual Campaign</h4>
        <p class="detail-value">{fmt(lbAnnual)}</p>
      </div>

      <div class="detail-section">
        <h4>Production Fee</h4>
        <p class="detail-value">$495</p>
        <p class="detail-note">-$125 if renewal with testimonial letter</p>
      </div>

      <div class="detail-section">
        <h4>Payment Options</h4>
        <ul class="payment-list">
          {#each PRODUCTS.digital.subproducts.loyaltyboost.paymentOptions as option}
            <li>• {option}</li>
          {/each}
        </ul>
      </div>

      <button class="share-btn" on:click={() => copyProductPackage('loyaltyboost')}>
        {copyFeedback === 'loyaltyboost' ? '✅ Sent!' : '📩 Send to Customer'}
      </button>
      <button class="action-btn" on:click={() => addToCart("LoyaltyBoost", fmt(lbAnnual) + "/year", "Annual loyalty campaign")}>🛒 Add to Cart</button>
    </div>
  {/if}
</div>

<style>
  .products-container {
    padding: 20px;
    padding-bottom: 140px;
    max-width: 100%;
    margin: 0 auto;
  }

  h2 {
    margin: 0 0 8px;
    font-size: 22px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .subtitle, .detail-subtitle {
    margin: 0 0 20px;
    color: var(--text-secondary);
    font-size: 14px;
  }

  .back-btn {
    background: none;
    border: none;
    color: #CC0000;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    padding: 10px 0;
    margin-bottom: 15px;
  }

  .back-btn:hover {
    text-decoration: underline;
  }

    .button-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem; width: 100%; }
    @media (min-width: 768px) { .button-grid { grid-template-columns: repeat(3, 1fr); gap: 2rem; } }
    @media (min-width: 1200px) { .button-grid { grid-template-columns: repeat(3, 1fr); gap: 2rem; } }
  .main-btn { background: var(--card-bg); border: 2px solid var(--border-color); border-radius: 16px; padding: 2rem 1.5rem; cursor: pointer; transition: all 0.2s; text-align: center; color: var(--text-primary); min-height: 180px; display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; }
  .main-btn:hover { border-color: #cc0000; box-shadow: 0 4px 12px rgba(204, 0, 0, 0.1); transform: translateY(-2px); }
  .btn-icon { font-size: 2rem; margin-bottom: 0.5rem; }
  .btn-text { font-weight: 600; color: var(--text-primary, #eee); margin-bottom: 0.25rem; }
  .btn-desc { font-size: 0.85rem; color: var(--text-tertiary, #999); }

  .tiers-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: 15px;
  }

  .tier-card {
    background: var(--card-bg, #ffffff);
    border: 1px solid #e8e8e8;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
    padding: 16px;
    text-align: left;
    cursor: pointer;
    transition: box-shadow 0.2s;
    position: relative;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  :global([data-theme='dark']) .tier-card { background: #1e1e1e; border-color: #333; }

  .tier-card:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    border-color: #CC0000;
  }

  .tier-header {
    display: flex;
    gap: 12px;
    flex: 1;
  }

  .tier-emoji {
    font-size: 24px;
    flex-shrink: 0;
  }

  .tier-card h4 {
    margin: 0 0 4px;
    color: var(--text-primary, #333);
    font-size: 15px;
    font-weight: 600;
  }

  .tier-desc {
    margin: 0;
    color: #666;
    font-size: 12px;
  }

  .arrow-right {
    color: #CC0000;
    font-size: 18px;
    flex-shrink: 0;
  }

  .detail-card {
    background: var(--card-bg, #ffffff);
    border-radius: 12px;
    border: 1px solid #e8e8e8;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
    padding: 20px;
    margin-top: 20px;
    transition: box-shadow 0.2s;
  }
  .detail-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
  :global([data-theme='dark']) .detail-card { background: #1e1e1e; border-color: #333; }

  .detail-desc {
    margin: 0 0 20px;
    color: #666;
    font-size: 15px;
    line-height: 1.5;
  }

  .detail-section {
    margin-bottom: 20px;
  }

  .detail-section h4 {
    margin: 0 0 8px;
    color: #333;
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .detail-value {
    margin: 0;
    color: #CC0000;
    font-weight: 700;
    font-size: 20px;
  }

  .pricing-section h4 {
    margin: 0 0 12px;
    color: #333;
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
  }

  .pricing-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 16px;
  }

  .pricing-item {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid #e0e0e0;
  }

  .plan-name {
    font-weight: 600;
    color: #333;
    font-size: 13px;
  }

  .plan-formula {
    color: #666;
    font-size: 12px;
    text-align: right;
  }

  .packages-list {
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;
    margin-top: 15px;
    margin-bottom: 20px;
  }

  .package-card {
    background: var(--card-bg, #ffffff);
    border: 1px solid #e8e8e8;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
    padding: 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: box-shadow 0.2s;
  }
  .package-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
  :global([data-theme='dark']) .package-card { background: #1e1e1e; border-color: #333; }

  .pkg-info { flex: 1; }

  .package-card h4 {
    margin: 0 0 6px;
    color: var(--text-primary, #333);
    font-size: 15px;
    font-weight: 600;
  }

  .cart-add-btn {
    background: #CC0000;
    color: white;
    border: none;
    border-radius: 8px;
    width: 44px;
    height: 44px;
    font-size: 18px;
    cursor: pointer;
    flex-shrink: 0;
  }

  .cart-add-btn:hover { background: #990000; }

  .package-price {
    margin: 0;
    color: #CC0000;
    font-weight: 700;
    font-size: 15px;
  }

  .note {
    margin: 16px 0;
    padding: 12px;
    background: rgba(204, 0, 0, 0.05);
    border-left: 4px solid #CC0000;
    color: #555;
    font-size: 13px;
    border-radius: 4px;
  }

  .share-btn {
    width: 100%;
    background: #1a73e8;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    margin-top: 10px;
    transition: background 0.2s;
  }

  .share-btn:hover {
    background: #1557b0;
  }

  .action-btn {
    width: 100%;
    background: #CC0000;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    margin-top: 10px;
  }

  .action-btn:hover {
    background: #990000;
  }

  .links-section {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    flex-wrap: wrap;
  }

  .link-btn {
    flex: 1;
    min-width: 150px;
    background: #f0f0f0;
    color: #CC0000;
    text-decoration: none;
    border: 2px solid #CC0000;
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 14px;
    font-weight: 600;
    text-align: center;
    transition: all 0.2s;
    cursor: pointer;
  }

  .link-btn:hover {
    background: #CC0000;
    color: white;
  }

  .digital-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-top: 15px;
    width: 100%;
  }

  @media (min-width: 768px) {
    .digital-grid {
      grid-template-columns: repeat(4, 1fr);
    }
  }

  .digital-card {
    background: var(--card-bg, #ffffff);
    border: 1px solid #e8e8e8;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
    padding: 16px;
    text-align: center;
    cursor: pointer;
    transition: box-shadow 0.2s;
  }
  :global([data-theme='dark']) .digital-card { background: #1e1e1e; border-color: #333; }

  .digital-card:hover {
    border-color: #CC0000;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .digital-emoji {
    font-size: 28px;
    margin-bottom: 8px;
  }

  .digital-card h4 {
    margin: 0 0 6px;
    color: var(--text-primary, #333);
    font-size: 15px;
    font-weight: 600;
  }

  .digital-desc {
    margin: 0 0 8px;
    color: #666;
    font-size: 11px;
    line-height: 1.3;
  }

  .digital-price {
    margin: 0;
    color: #CC0000;
    font-weight: 700;
    font-size: 13px;
  }

  .detail-note {
    margin: 4px 0 0;
    color: #666;
    font-size: 12px;
  }

  .features-list {
    margin: 0;
    padding-left: 0;
    list-style: none;
  }

  .features-list li {
    padding: 6px 0;
    color: #555;
    font-size: 13px;
    text-align: left;
  }

  .payment-list {
    margin: 0;
    padding-left: 16px;
    list-style: none;
    color: #555;
    font-size: 13px;
  }

  .payment-list li {
    padding: 6px 0;
  }

  @media (max-width: 600px) {
    .digital-grid {
      grid-template-columns: 1fr;
    }
  }

  .pricing-item {
    margin: 6px 0;
    color: #555;
    font-size: 13px;
  }

  .pricing-table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 13px;
  }

  .pricing-table thead {
    background: #f0f0f0;
  }

  .pricing-table th {
    padding: 10px 8px;
    text-align: left;
    font-weight: 600;
    color: #333;
    border-bottom: 2px solid #ddd;
  }

  .pricing-table td {
    padding: 8px;
    border-bottom: 1px solid #eee;
    color: #555;
  }

  .pricing-table tr:last-child td {
    border-bottom: none;
  }

  .pricing-table td:nth-child(2),
  .pricing-table td:nth-child(3) {
    text-align: right;
    color: #CC0000;
    font-weight: 600;
  }

  .settings-bar {
    display: flex;
    gap: 16px;
    margin-bottom: 20px;
    padding: 14px;
    background: var(--card-bg, #ffffff);
    border: 1px solid #e8e8e8;
    border-radius: 12px;
    flex-wrap: wrap;
  }
  :global([data-theme='dark']) .settings-bar { background: #1e1e1e; border-color: #333; }

  .setting-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
    flex: 1;
    min-width: 120px;
  }

  .setting-item label {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary, #666);
  }

  .input-row {
    display: flex;
    align-items: center;
    gap: 4px;
    color: var(--text-primary, #333);
    font-weight: 600;
  }

  .pad-input, .rep-input {
    border: 1px solid #ddd;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 14px;
    width: 100%;
    background: var(--card-bg, #fff);
    color: var(--text-primary, #333);
  }
  :global([data-theme='dark']) .pad-input,
  :global([data-theme='dark']) .rep-input { background: #2a2a2a; border-color: #444; color: #eee; }

  .pad-input { max-width: 100px; }
</style>

