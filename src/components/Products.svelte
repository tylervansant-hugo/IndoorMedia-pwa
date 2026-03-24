<script>
  let view = 'main'; // main, category, product-detail
  let selectedCategory = null;
  let selectedProduct = null;

  const PRODUCT_CATEGORIES = {
    '📋 Register Tape': {
      emoji: '📋',
      products: [
        { id: 1, name: 'Single Ad Register Tape', desc: '2.25" × 50\' roll', price: 'Base pricing varies by store', features: ['Full color', 'Custom design', 'High quality'] },
        { id: 2, name: 'Double Ad Register Tape', desc: '4.5" × 50\' roll', price: 'Base pricing varies by store', features: ['Two-sided', 'Double the impressions', 'Premium stock'] },
        { id: 3, name: 'Specialty Rolls', desc: 'Custom sizes & materials', price: 'Contact for quote', features: ['Thermal paper', 'Glossy finish', 'Custom dimensions'] }
      ]
    },
    '🎁 Promotional Items': {
      emoji: '🎁',
      products: [
        { id: 4, name: 'Custom Bags', desc: 'Branded shopping bags', price: 'Contact sales', features: ['Full color print', 'Multiple sizes', 'Eco-friendly options'] },
        { id: 5, name: 'Stickers & Decals', desc: 'Window & product stickers', price: 'Contact sales', features: ['Weatherproof', 'Custom shapes', 'Bulk discounts'] }
      ]
    },
    '📸 Design Services': {
      emoji: '📸',
      products: [
        { id: 6, name: 'Tape Design', desc: 'Professional design for register tape', price: '$125 production charge', features: ['Free concept', 'Unlimited revisions', '3-day turnaround'] },
        { id: 7, name: 'Brand Consultation', desc: 'Strategic placement advice', price: 'Included with campaigns', features: ['Store profiling', 'Best practices', 'ROI guidance'] }
      ]
    },
    '💰 Payment Plans': {
      emoji: '💰',
      products: [
        { id: 8, name: 'Monthly', desc: 'Flexible budget-friendly option', price: '(Base + $125) ÷ 12', features: ['No long-term commitment', 'Easy to start/stop', 'Great for testing'] },
        { id: 9, name: 'Paid-in-Full', desc: 'Best value discount', price: '15% off + $125 production', features: ['Maximize ROI', 'Best per-unit cost', 'Commitment savings'] }
      ]
    }
  };

  function goBack() {
    if (view === 'product-detail') {
      view = 'category';
      selectedProduct = null;
    } else if (view === 'category') {
      view = 'main';
      selectedCategory = null;
    }
  }

  function selectCategory(cat) {
    selectedCategory = cat;
    view = 'category';
  }

  function selectProduct(product) {
    selectedProduct = product;
    view = 'product-detail';
  }
</script>

<div class="products-container">
  <!-- Main Menu -->
  {#if view === 'main'}
    <h2>📦 Products & Services</h2>
    <p class="subtitle">Everything IndoorMedia offers</p>

    <div class="category-grid">
      {#each Object.entries(PRODUCT_CATEGORIES) as [catName, catData]}
        <button class="category-btn" on:click={() => selectCategory(catName)}>
          <div class="cat-emoji">{catData.emoji}</div>
          <div class="cat-name">{catName}</div>
          <div class="cat-count">{catData.products.length} items</div>
        </button>
      {/each}
    </div>
  {/if}

  <!-- Category View -->
  {#if view === 'category' && selectedCategory}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>{selectedCategory}</h2>

    <div class="product-list">
      {#each PRODUCT_CATEGORIES[selectedCategory].products as product (product.id)}
        <button class="product-card" on:click={() => selectProduct(product)}>
          <h4>{product.name}</h4>
          <p class="product-desc">{product.desc}</p>
          <p class="product-price">{product.price}</p>
          <div class="arrow">→</div>
        </button>
      {/each}
    </div>
  {/if}

  <!-- Product Detail -->
  {#if view === 'product-detail' && selectedProduct}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>{selectedProduct.name}</h2>
    
    <div class="detail-card">
      <p class="detail-desc">{selectedProduct.desc}</p>
      
      <div class="detail-section">
        <h4>Pricing</h4>
        <p class="detail-price">{selectedProduct.price}</p>
      </div>

      <div class="detail-section">
        <h4>Features</h4>
        <ul class="features-list">
          {#each selectedProduct.features as feature}
            <li>✓ {feature}</li>
          {/each}
        </ul>
      </div>

      <button class="action-btn">📧 Request Quote</button>
    </div>
  {/if}
</div>

<style>
  .products-container {
    padding: 20px;
    max-width: 500px;
    margin: 0 auto;
  }

  h2 {
    margin: 0 0 8px;
    font-size: 24px;
    color: #333;
  }

  .subtitle {
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

  .category-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
    margin-top: 20px;
  }

  .category-btn {
    background: white;
    border: 2px solid #eee;
    border-radius: 12px;
    padding: 16px;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s;
  }

  .category-btn:hover {
    border-color: #CC0000;
    background: #fff5f5;
  }

  .cat-emoji {
    font-size: 32px;
    margin-bottom: 8px;
  }

  .cat-name {
    font-weight: 600;
    color: #333;
    font-size: 16px;
    margin-bottom: 4px;
  }

  .cat-count {
    color: #999;
    font-size: 12px;
  }

  .product-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: 15px;
  }

  .product-card {
    background: white;
    border: 1px solid #eee;
    border-radius: 10px;
    padding: 14px;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s;
    position: relative;
  }

  .product-card:hover {
    border-color: #CC0000;
    box-shadow: 0 4px 12px rgba(204, 0, 0, 0.1);
  }

  .product-card h4 {
    margin: 0 0 6px;
    color: #333;
    font-size: 16px;
  }

  .product-desc {
    margin: 0 0 6px;
    color: #666;
    font-size: 13px;
  }

  .product-price {
    margin: 0;
    color: #CC0000;
    font-weight: 600;
    font-size: 14px;
  }

  .arrow {
    position: absolute;
    right: 14px;
    top: 50%;
    transform: translateY(-50%);
    color: #CC0000;
    font-size: 20px;
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
    font-size: 16px;
    line-height: 1.5;
  }

  .detail-section {
    margin-bottom: 20px;
  }

  .detail-section h4 {
    margin: 0 0 10px;
    color: #333;
    font-size: 14px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .detail-price {
    margin: 0;
    color: #CC0000;
    font-weight: 700;
    font-size: 18px;
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
