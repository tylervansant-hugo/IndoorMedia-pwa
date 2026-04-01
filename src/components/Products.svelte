<script>
  let view = 'main'; // main, product-detail, tier-detail, digital-menu, digital-detail
  let selectedProduct = null;
  let selectedTier = null;
  let selectedDigitalProduct = null;

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
    }
  };

  function addToCart(name, price, details) {
    let cart = [];
    try { cart = JSON.parse(localStorage.getItem('indoormedia_cart') || '[]'); } catch {}
    cart.push({ id: Date.now(), name, price, details, addedAt: new Date().toISOString() });
    localStorage.setItem('indoormedia_cart', JSON.stringify(cart));
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
      <a href={PRODUCT_LINKS.digital.presentation} target="_blank" class="link-btn">🎬 Sales Presentation</a>
      <a href={PRODUCT_LINKS.digital.explainer} target="_blank" class="link-btn">📹 Explainer Video</a>
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
        <p class="pricing-item">$3,600 per pin</p>
        <p class="pricing-item">$395 production (covers up to 5 pins)</p>
      </div>

      <div class="detail-section">
        <h4>Manager-Approved Co-Op Pricing</h4>
        <p class="pricing-item">$2,400 per pin</p>
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
            {#each PRODUCTS.digital.subproducts.digitalboost.examples as ex}
              <tr>
                <td>{ex.pins}</td>
                <td>{ex.standard}</td>
                <td>{ex.coop}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      
      <button class="action-btn" on:click={() => addToCart("DigitalBoost", "$3,600/pin", "240K standalone / 360K bundled impressions")}>🛒 Add to Cart</button>
    </div>
  {/if}

  <!-- FindLocal Detail -->
  {#if view === 'digital-detail' && selectedDigitalProduct === 'findlocal'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>📍 FindLocal</h2>
    <p class="detail-subtitle">Local SEO & listings management across 50+ directories</p>

    <div class="links-section">
      <a href={PRODUCT_LINKS.digital.presentation} target="_blank" class="link-btn">🎬 Sales Presentation</a>
      <a href={PRODUCT_LINKS.digital.explainer} target="_blank" class="link-btn">📹 Explainer Video</a>
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

      
      <button class="action-btn" on:click={() => addToCart("FindLocal", "$695/location", "50+ directory listings")}>🛒 Add to Cart</button>
    </div>
  {/if}

  <!-- ReviewBoost Detail -->
  {#if view === 'digital-detail' && selectedDigitalProduct === 'reviewboost'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>⭐ ReviewBoost</h2>
    <p class="detail-subtitle">Automated review request campaign via Email & SMS</p>

    <div class="links-section">
      <a href={PRODUCT_LINKS.digital.presentation} target="_blank" class="link-btn">🎬 Sales Presentation</a>
      <a href={PRODUCT_LINKS.digital.explainer} target="_blank" class="link-btn">📹 Explainer Video</a>
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

      <button class="action-btn" on:click={() => addToCart("ReviewBoost", "$695", "4-month campaign, 4000 contacts")}>🛒 Add to Cart</button>
    </div>
  {/if}

  <!-- LoyaltyBoost Detail -->
  {#if view === 'digital-detail' && selectedDigitalProduct === 'loyaltyboost'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>💎 LoyaltyBoost</h2>
    <p class="detail-subtitle">Annual loyalty/rewards campaign per location</p>

    <div class="links-section">
      <a href={PRODUCT_LINKS.digital.presentation} target="_blank" class="link-btn">🎬 Sales Presentation</a>
      <a href={PRODUCT_LINKS.digital.explainer} target="_blank" class="link-btn">📹 Explainer Video</a>
    </div>

    <div class="detail-card">
      <div class="detail-section">
        <h4>Annual Campaign</h4>
        <p class="detail-value">$3,600</p>
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

      <button class="action-btn" on:click={() => addToCart("LoyaltyBoost", "$3,600/year", "Annual loyalty campaign")}>🛒 Add to Cart</button>
    </div>
  {/if}
</div>

<style>
  .products-container {
    padding: 20px;
    max-width: 100%;
    margin: 0 auto;
  }

  h2 {
    margin: 0 0 8px;
    font-size: 24px;
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
    background: white;
    border: 1px solid #eee;
    border-radius: 10px;
    padding: 14px;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s;
    position: relative;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .tier-card:hover {
    border-color: #CC0000;
    box-shadow: 0 4px 12px rgba(204, 0, 0, 0.1);
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
    color: #333;
    font-size: 15px;
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
    background: #f5f5f5;
    border-radius: 12px;
    padding: 20px;
    margin-top: 20px;
  }

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
    background: white;
    border: 1px solid #eee;
    border-radius: 8px;
    padding: 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .pkg-info { flex: 1; }

  .package-card h4 {
    margin: 0 0 6px;
    color: #333;
    font-size: 14px;
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
    background: white;
    border: 1px solid #eee;
    border-radius: 10px;
    padding: 14px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
  }

  .digital-card:hover {
    border-color: #CC0000;
    box-shadow: 0 4px 12px rgba(204, 0, 0, 0.1);
  }

  .digital-emoji {
    font-size: 28px;
    margin-bottom: 8px;
  }

  .digital-card h4 {
    margin: 0 0 6px;
    color: #333;
    font-size: 14px;
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
</style>

