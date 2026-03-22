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
      color: '#CC0000',
      presentationUrl: 'https://docs.google.com/presentation/d/1Xs60nX3i6MJkC81GgnK-50jBrkWVPu06xRpmv8z4PIc/edit?usp=sharing',
      videoUrl: 'https://youtu.be/_gdlyEszHfY?si=0_kHou89WrMhvNY_'
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
      color: '#4CAF50',
      presentationUrl: 'https://docs.google.com/presentation/d/1Xs60nX3i6MJkC81GgnK-50jBrkWVPu06xRpmv8z4PIc/edit?usp=sharing',
      videoUrl: 'https://youtu.be/_gdlyEszHfY?si=0_kHou89WrMhvNY_'
    },
    {
      id: 'digital-connection',
      icon: '🔌',
      name: 'Connection',
      subtitle: 'WiFi splash page advertising',
      description: 'Reach customers through store WiFi landing pages. Capture attention when customers connect.',
      benefits: [
        '✅ High engagement rate',
        '✅ Digital tracking',
        '✅ Mobile-friendly',
        '✅ Instant visibility'
      ],
      pricing: 'Starting at $395/month',
      color: '#2196F3',
      presentationUrl: 'https://docs.google.com/presentation/d/1Xs60nX3i6MJkC81GgnK-50jBrkWVPu06xRpmv8z4PIc/edit?usp=sharing',
      videoUrl: 'https://youtu.be/_gdlyEszHfY?si=0_kHou89WrMhvNY_'
    },
    {
      id: 'digital-hub',
      icon: '🖥️',
      name: 'Digital Hub',
      subtitle: 'In-store digital kiosks',
      description: 'Interactive digital displays at high-traffic store locations. Dynamic content, real-time updates.',
      benefits: [
        '✅ Eye-catching video content',
        '✅ Multiple ad rotations',
        '✅ Premium in-store placement',
        '✅ Real-time campaign updates'
      ],
      pricing: 'Starting at $495/month',
      color: '#2196F3',
      presentationUrl: 'https://docs.google.com/presentation/d/1Xs60nX3i6MJkC81GgnK-50jBrkWVPu06xRpmv8z4PIc/edit?usp=sharing',
      videoUrl: 'https://youtu.be/_gdlyEszHfY?si=0_kHou89WrMhvNY_'
    },
    {
      id: 'digital-boost',
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
      color: '#2196F3',
      presentationUrl: 'https://docs.google.com/presentation/d/1Xs60nX3i6MJkC81GgnK-50jBrkWVPu06xRpmv8z4PIc/edit?usp=sharing',
      videoUrl: 'https://youtu.be/_gdlyEszHfY?si=0_kHou89WrMhvNY_'
    },
    {
      id: 'find-local',
      icon: '📍',
      name: 'Find Local',
      subtitle: 'Geo-targeted mobile ads',
      description: 'Target customers near store locations with mobile ads. Drive foot traffic with precise targeting.',
      benefits: [
        '✅ Geo-fencing technology',
        '✅ Mobile-first design',
        '✅ Real-time analytics',
        '✅ Drive in-store visits'
      ],
      pricing: 'Starting at $495/month',
      color: '#FF9800',
      presentationUrl: 'https://docs.google.com/presentation/d/1Xs60nX3i6MJkC81GgnK-50jBrkWVPu06xRpmv8z4PIc/edit?usp=sharing',
      videoUrl: 'https://youtu.be/_gdlyEszHfY?si=0_kHou89WrMhvNY_'
    },
    {
      id: 'loyalty-boost',
      icon: '💳',
      name: 'Loyalty Boost',
      subtitle: 'Loyalty program integration',
      description: 'Promote your business through store loyalty programs and apps. Reach engaged, repeat customers.',
      benefits: [
        '✅ Access loyalty app users',
        '✅ Highly engaged audience',
        '✅ Repeat customer targeting',
        '✅ Digital coupon delivery'
      ],
      pricing: 'Starting at $595/month',
      color: '#9C27B0',
      presentationUrl: 'https://docs.google.com/presentation/d/1Xs60nX3i6MJkC81GgnK-50jBrkWVPu06xRpmv8z4PIc/edit?usp=sharing',
      videoUrl: 'https://youtu.be/_gdlyEszHfY?si=0_kHou89WrMhvNY_'
    }
  ];

  function selectProduct(product) {
    selectedProduct = selectedProduct?.id === product.id ? null : product;
  }
</script>

<div class="products-container">
  {#if !selectedProduct}
    <h2>📦 Products</h2>
    <p class="subtitle">IndoorMedia advertising solutions</p>

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
        <ul>
          {#each selectedProduct.benefits as benefit}
            <li>{benefit}</li>
          {/each}
        </ul>
      </div>

      <div class="pricing-section">
        <h3>Investment</h3>
        <p class="price-highlight">{selectedProduct.pricing}</p>
      </div>

      <div class="resources-section">
        <h3>Learn More</h3>
        <div class="resource-buttons">
          <a href={selectedProduct.presentationUrl} target="_blank" rel="noopener noreferrer" class="resource-btn presentation">
            📊 View Presentation
          </a>
          <a href={selectedProduct.videoUrl} target="_blank" rel="noopener noreferrer" class="resource-btn video">
            🎥 Watch Explainer Video
          </a>
        </div>
      </div>

      <div class="cta-section">
        <a href="https://indoor-media-pwa.vercel.app" class="cta-btn">
          📊 Calculate ROI
        </a>
      </div>
    </div>
  {/if}
</div>

<style>
  .products-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1rem;
  }

  h2 {
    margin: 0 0 0.5rem 0;
    font-size: 1.5rem;
    color: #1a1a1a;
  }

  .subtitle {
    margin: 0 0 2rem 0;
    color: #666;
    font-size: 0.95rem;
  }

  .products-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1.5rem;
  }

  .product-card {
    background: white;
    border: 3px solid;
    border-radius: 12px;
    padding: 1.5rem;
    cursor: pointer;
    transition: all 0.2s;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }

  .product-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 20px rgba(0,0,0,0.15);
  }

  .product-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
  }

  h3 {
    margin: 0.5rem 0;
    font-size: 1.25rem;
    color: #1a1a1a;
  }

  .product-subtitle {
    display: block;
    margin: 0.5rem 0 1rem 0;
    color: #666;
    font-size: 0.9rem;
  }

  .product-price {
    display: block;
    margin: 1rem 0 0.5rem 0;
    font-weight: bold;
    color: #CC0000;
    font-size: 1.1rem;
  }

  .learn-more {
    display: inline-block;
    margin-top: 0.5rem;
    color: #2196F3;
    font-weight: 600;
    font-size: 0.9rem;
  }

  /* Product Detail View */
  .back-btn {
    background: none;
    border: none;
    color: #CC0000;
    font-weight: 600;
    font-size: 1rem;
    cursor: pointer;
    margin-bottom: 1.5rem;
    padding: 0.5rem 0;
  }

  .product-detail {
    background: white;
    border-radius: 12px;
    padding: 2rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  }

  .product-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1rem;
  }

  .detail-icon {
    font-size: 3rem;
  }

  .detail-subtitle {
    color: #666;
    font-size: 1.1rem;
    margin-bottom: 1.5rem;
  }

  .detail-description {
    font-size: 1rem;
    line-height: 1.6;
    color: #333;
    margin-bottom: 2rem;
  }

  .benefits-section,
  .pricing-section,
  .resources-section,
  .cta-section {
    margin-bottom: 2rem;
  }

  .benefits-section h3,
  .pricing-section h3,
  .resources-section h3 {
    font-size: 1.25rem;
    margin-bottom: 1rem;
    color: #1a1a1a;
  }

  .benefits-section ul {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  .benefits-section li {
    padding: 0.5rem 0;
    font-size: 1rem;
    color: #333;
  }

  .price-highlight {
    font-size: 1.5rem;
    font-weight: bold;
    color: #CC0000;
    margin: 0;
  }

  .resource-buttons {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .resource-btn {
    display: block;
    padding: 1rem;
    border-radius: 8px;
    text-decoration: none;
    font-weight: 600;
    text-align: center;
    transition: all 0.2s;
  }

  .resource-btn.presentation {
    background: #2196F3;
    color: white;
  }

  .resource-btn.presentation:hover {
    background: #1976D2;
    transform: translateY(-2px);
  }

  .resource-btn.video {
    background: #CC0000;
    color: white;
  }

  .resource-btn.video:hover {
    background: #990000;
    transform: translateY(-2px);
  }

  .cta-btn {
    display: block;
    padding: 1.25rem;
    background: linear-gradient(135deg, #CC0000, #990000);
    color: white;
    border-radius: 8px;
    text-decoration: none;
    font-weight: bold;
    font-size: 1.1rem;
    text-align: center;
    transition: all 0.2s;
  }

  .cta-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(204, 0, 0, 0.3);
  }

  @media (max-width: 768px) {
    .products-grid {
      grid-template-columns: 1fr;
    }

    .product-detail {
      padding: 1.5rem;
    }

    .resource-buttons {
      gap: 0.75rem;
    }
  }
</style>
