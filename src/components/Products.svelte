<script>
  let view = 'main'; // main, product-detail, tier-detail
  let selectedProduct = null;
  let selectedTier = null;

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
    digitalboost: {
      name: 'DigitalBoost — 1 Pin',
      emoji: '🚀',
      desc: '240,000 monthly impressions on digital displays',
      pricing: {
        monthly: '$3,600/month'
      },
      impressions: '240,000'
    }
  };

  function goBack() {
    if (view === 'tier-detail') {
      view = 'product-detail';
      selectedTier = null;
    } else if (view === 'product-detail') {
      view = 'main';
      selectedProduct = null;
    }
  }

  function selectProduct(key) {
    selectedProduct = key;
    view = 'product-detail';
  }

  function selectTier(tierKey) {
    selectedTier = tierKey;
    view = 'tier-detail';
  }
</script>

<div class="products-container">
  <!-- Main Menu -->
  {#if view === 'main'}
    <h2>📦 IndoorMedia Products</h2>
    <p class="subtitle">Premium in-store advertising solutions</p>

    <div class="product-grid">
      {#each Object.entries(PRODUCTS) as [key, product]}
        <button class="product-btn" on:click={() => selectProduct(key)}>
          <div class="product-emoji">{product.emoji}</div>
          <div class="product-name">{product.name}</div>
          <div class="product-desc">{product.desc}</div>
          <div class="arrow">→</div>
        </button>
      {/each}
    </div>
  {/if}

  <!-- Register Tape Detail -->
  {#if view === 'product-detail' && selectedProduct === 'register_tape'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>🧾 Register Tape</h2>
    <p class="detail-subtitle">High-visibility promotional strips at checkout</p>

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

      <p class="note">💡 Base pricing varies by store and location. Contact sales for specific quotes.</p>
      <button class="action-btn">📧 Request Quote</button>
    </div>
  {/if}

  <!-- Cartvertising Detail -->
  {#if view === 'product-detail' && selectedProduct === 'cartvertising'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>🛒 Cartvertising</h2>
    <p class="detail-subtitle">Shopping cart advertising - 6-month campaigns</p>

    <div class="packages-list">
      {#each Object.entries(PRODUCTS.cartvertising.packages) as [key, pkg]}
        <div class="package-card">
          <h4>{pkg.name}</h4>
          <p class="package-price">{pkg.price}</p>
        </div>
      {/each}
    </div>

    <p class="note">💡 All packages are 6-month campaigns. Volume discounts available.</p>
    <button class="action-btn">📧 Request Quote</button>
  {/if}

  <!-- DigitalBoost Detail -->
  {#if view === 'product-detail' && selectedProduct === 'digitalboost'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>🚀 DigitalBoost — 1 Pin</h2>
    <p class="detail-subtitle">240,000 monthly impressions on digital displays</p>

    <div class="detail-card">
      <div class="detail-section">
        <h4>Monthly Impressions</h4>
        <p class="detail-value">240,000</p>
      </div>

      <div class="detail-section">
        <h4>Monthly Cost</h4>
        <p class="detail-value">$3,600</p>
      </div>

      <p class="note">💡 Digital displays in high-traffic checkout zones. Premium placement guaranteed.</p>
      <button class="action-btn">📧 Request Quote</button>
    </div>
  {/if}
</div>

<style>
  .products-container {
    padding: 20px;
    max-width: 600px;
    margin: 0 auto;
  }

  h2 {
    margin: 0 0 8px;
    font-size: 24px;
    color: #333;
  }

  .subtitle, .detail-subtitle {
    margin: 0 0 20px;
    color: #666;
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

  .product-grid {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: 20px;
  }

  .product-btn {
    background: white;
    border: 2px solid #eee;
    border-radius: 12px;
    padding: 16px;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s;
    position: relative;
    display: flex;
    align-items: flex-start;
    gap: 12px;
  }

  .product-btn:hover {
    border-color: #CC0000;
    background: #fff5f5;
  }

  .product-emoji {
    font-size: 32px;
    flex-shrink: 0;
  }

  .product-name {
    font-weight: 600;
    color: #333;
    font-size: 16px;
    margin-bottom: 4px;
  }

  .product-desc {
    color: #666;
    font-size: 13px;
    margin: 0;
  }

  .arrow {
    position: absolute;
    right: 16px;
    top: 50%;
    transform: translateY(-50%);
    color: #CC0000;
    font-size: 20px;
  }

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
    background: #f9f9f9;
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
  }

  .package-card h4 {
    margin: 0 0 6px;
    color: #333;
    font-size: 14px;
    font-weight: 600;
  }

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
</style>
