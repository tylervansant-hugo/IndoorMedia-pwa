<script>
  let selectedProduct = null;

  const PRODUCTS = [
    {
      id: 'register-tape',
      icon: '📜',
      name: 'Register Tape',
      subtitle: 'Coupon-style advertising',
      description: 'Print coupons at checkout registers in grocery stores. High visibility, immediate action.',
      benefits: [
        '✅ Printed at point-of-sale',
        '✅ Impulse-driven offers',
        '✅ Track redemptions',
        '✅ Measurable ROI'
      ],
      pricing: 'Starting at $295/month',
      color: '#FF6B35'
    },
    {
      id: 'cartvertising',
      icon: '🛒',
      name: 'Cartvertising',
      subtitle: 'Shopping cart advertising',
      description: 'Ads on grocery store shopping carts. Prime placement with high frequency.',
      benefits: [
        '✅ 360° visibility',
        '✅ High cart touchpoints',
        '✅ Brand awareness',
        '✅ Flexible designs'
      ],
      pricing: 'Starting at $395/month',
      color: '#4CAF50'
    },
    {
      id: 'digital',
      icon: '📱',
      name: 'Digital Boost',
      subtitle: 'In-store digital displays',
      description: 'Rotating digital ads on in-store displays and kiosks. Modern, dynamic, eye-catching.',
      benefits: [
        '✅ High-impact visuals',
        '✅ Video & animations',
        '✅ Real-time updates',
        '✅ Premium placement'
      ],
      pricing: 'Starting at $595/month',
      color: '#2196F3'
    }
  ];

  function selectProduct(product) {
    selectedProduct = selectedProduct?.id === product.id ? null : product;
  }
</script>

<div class="products-container">
  {#if !selectedProduct}
    <h2>📦 Products</h2>
    <p class="subtitle">Advertising solutions for your business</p>

    <div class="products-grid">
      {#each PRODUCTS as product}
        <button
          class="product-card"
          on:click={() => selectProduct(product)}
          style="border-color: {product.color}"
        >
          <div class="product-icon">{product.icon}</div>
          <h3>{product.name}</h3>
          <p class="product-subtitle">{product.subtitle}</p>
          <span class="product-price">{product.pricing}</span>
          <span class="learn-more">Learn More →</span>
        </button>
      {/each}
    </div>

  {:else}
    <button class="back-btn" on:click={() => selectedProduct = null}>← Back to Products</button>

    <div class="product-detail">
      <div class="product-header">
        <span class="detail-icon">{selectedProduct.icon}</span>
        <h2>{selectedProduct.name}</h2>
      </div>

      <p class="detail-subtitle">{selectedProduct.subtitle}</p>

      <div class="detail-description">
        {selectedProduct.description}
      </div>

      <div class="benefits-section">
        <h3>Why It Works</h3>
        {#each selectedProduct.benefits as benefit}
          <p class="benefit">{benefit}</p>
        {/each}
      </div>

      <div class="pricing-section">
        <span class="pricing-label">Pricing:</span>
        <span class="pricing-value">{selectedProduct.pricing}</span>
      </div>

      <button class="action-btn" style="background: {selectedProduct.color}">
        💰 Get ROI Calculator
      </button>
    </div>
  {/if}
</div>

<style>
  .products-container { max-width: 700px; margin: 0 auto; }
  h2 { margin: 0 0 6px 0; font-size: 20px; }
  .subtitle { margin: 0 0 20px 0; font-size: 13px; color: #999; }

  .products-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
  }

  .product-card {
    background: white;
    border: 3px solid transparent;
    border-radius: 12px;
    padding: 20px;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 8px;
    transition: all 0.2s;
    position: relative;
  }

  .product-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  }

  .product-icon { font-size: 40px; }
  .product-card h3 { margin: 0; font-size: 16px; font-weight: 700; }
  .product-subtitle { margin: 4px 0; font-size: 12px; color: #888; }
  .product-price { font-size: 13px; font-weight: 600; color: #CC0000; margin-top: 6px; }
  .learn-more { font-size: 12px; color: #4CAF50; font-weight: 600; }

  .back-btn {
    padding: 10px 14px;
    background: none;
    border: none;
    color: #CC0000;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    margin-bottom: 20px;
  }

  .product-detail {
    background: white;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  }

  .product-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
  }

  .detail-icon { font-size: 40px; }
  .product-detail h2 { margin: 0; font-size: 24px; }

  .detail-subtitle {
    font-size: 15px;
    color: #666;
    margin: 8px 0 16px 0;
  }

  .detail-description {
    background: #f9f9f9;
    padding: 16px;
    border-radius: 8px;
    font-size: 14px;
    line-height: 1.5;
    margin-bottom: 20px;
    color: #333;
  }

  .benefits-section {
    margin-bottom: 20px;
  }

  .benefits-section h3 {
    margin: 0 0 12px 0;
    font-size: 15px;
    font-weight: 700;
  }

  .benefit {
    margin: 8px 0;
    font-size: 14px;
    color: #333;
  }

  .pricing-section {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #f0f0f0;
    padding: 14px;
    border-radius: 8px;
    margin-bottom: 16px;
  }

  .pricing-label { font-weight: 600; color: #666; }
  .pricing-value { font-size: 16px; font-weight: 700; color: #1a1a1a; }

  .action-btn {
    width: 100%;
    padding: 14px;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
  }

  .action-btn:hover { opacity: 0.9; }

  @media (max-width: 480px) {
    .products-grid { grid-template-columns: 1fr; }
    .product-detail { padding: 16px; }
  }
</style>
