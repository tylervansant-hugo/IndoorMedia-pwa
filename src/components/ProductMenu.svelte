<script>
  import { onMount } from 'svelte';
  import ProductCard from './ProductCard.svelte';
  
  let products = [
    {
      id: 'register-tape',
      name: 'Register Tape',
      icon: '🎫',
      description: 'Durable, adhesive-backed promotional strips',
      specs: {
        materials: ['Premium vinyl-backed paper', 'Pressure-sensitive adhesive'],
        sizes: ['Standard: 2.5" x 1.25"', 'Custom sizes available'],
        durability: '90+ days outdoor rated',
        finish: 'Glossy or matte',
      },
      pricingPlans: [
        {
          name: 'Small Bundle',
          quantity: '1,000 units',
          price: 2550,
          perUnit: 2.55,
          details: 'Great for single-location rollout',
        },
        {
          name: 'Standard',
          quantity: '5,000 units',
          price: 3800,
          perUnit: 0.76,
          details: 'Most popular - 50% off per unit',
        },
        {
          name: 'Large Fleet',
          quantity: '10,000+ units',
          price: 5100,
          perUnit: 0.51,
          details: 'Custom pricing available',
        },
      ],
    },
    {
      id: 'cartvertising',
      name: 'Cartvertising',
      icon: '🛒',
      description: 'Shopping cart advertising that moves with customers',
      specs: {
        placement: 'Premium shopping cart placement',
        format: '18" x 24" high-visibility format',
        rotation: 'Bi-weekly creative rotation available',
        coverage: 'Chain-wide deployment',
      },
      pricingPlans: [
        {
          name: 'Single Ad',
          quantity: 'Single store per cycle',
          price: 4050,
          perUnit: 4050,
          details: '4-week campaign',
        },
        {
          name: 'Double Ad',
          quantity: 'Dual creative rotation',
          price: 5670,
          perUnit: 2835,
          details: 'Two different creatives per cycle',
        },
        {
          name: 'Multi-Store Package',
          quantity: '5+ stores',
          price: 22500,
          perUnit: 4500,
          details: '20% volume discount applied',
        },
      ],
    },
    {
      id: 'digital-boost',
      name: 'DigitalBoost',
      icon: '📱',
      description: 'Digital point-of-sale advertising platform',
      specs: {
        screens: 'HD 55" digital displays',
        placement: 'Checkout lanes & high-traffic zones',
        content: '15-second looping content',
        control: 'Remote content management platform',
      },
      pricingPlans: [
        {
          name: 'Single Screen',
          quantity: '1 screen per location',
          price: 7500,
          perUnit: 7500,
          details: 'One 4-week campaign',
        },
        {
          name: 'Checkout Zone',
          quantity: '3-5 screens',
          price: 18000,
          perUnit: 4500,
          details: 'Complete checkout coverage',
        },
        {
          name: 'Network Package',
          quantity: '10+ screens',
          price: 35000,
          perUnit: 3500,
          details: 'Enterprise pricing - full network control',
        },
      ],
    },
  ];

  let selectedProductId = null;
  let cart = [];

  onMount(() => {
    // Load cart from localStorage
    const savedCart = localStorage.getItem('indoormedia_cart');
    if (savedCart) {
      try {
        cart = JSON.parse(savedCart);
      } catch (e) {
        cart = [];
      }
    }
  });

  function selectProduct(productId) {
    selectedProductId = selectedProductId === productId ? null : productId;
  }

  function addToCart(event) {
    const { productId, planName, quantity } = event.detail;
    const product = products.find(p => p.id === productId);
    const plan = product.pricingPlans.find(p => p.name === planName);
    
    const cartItem = {
      id: `${productId}-${planName}-${Date.now()}`,
      productId,
      productName: product.name,
      planName,
      quantity,
      price: plan.price,
      perUnit: plan.perUnit,
      addedAt: new Date().toISOString(),
    };
    
    cart = [...cart, cartItem];
    localStorage.setItem('indoormedia_cart', JSON.stringify(cart));
  }
</script>

<div class="product-menu">
  <div class="header">
    <h1>IndoorMedia Products</h1>
    <p>Premium in-store advertising solutions</p>
  </div>

  <div class="products-grid">
    {#each products as product (product.id)}
      <ProductCard
        {product}
        isSelected={selectedProductId === product.id}
        on:select={() => selectProduct(product.id)}
        on:addToCart={addToCart}
      />
    {/each}
  </div>

  <div class="cart-summary">
    <div class="cart-count">
      {cart.length} items in cart
    </div>
    {#if cart.length > 0}
      <a href="/cart" class="view-cart-btn">View Cart</a>
    {/if}
  </div>
</div>

<style>
  .product-menu {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    background: linear-gradient(135deg, #f5f5f5 0%, #ffffff 100%);
    padding: 1rem;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
      Ubuntu, Cantarell, sans-serif;
  }

  .header {
    text-align: center;
    margin-bottom: 2rem;
    padding: 1rem;
  }

  .header h1 {
    font-size: 1.8rem;
    font-weight: 700;
    color: #1a1a1a;
    margin: 0 0 0.5rem 0;
  }

  .header p {
    font-size: 0.95rem;
    color: #666;
    margin: 0;
  }

  .products-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1rem;
    margin-bottom: 2rem;
    flex: 1;
  }

  @media (min-width: 768px) {
    .products-grid {
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 1.5rem;
    }
  }

  .cart-summary {
    position: sticky;
    bottom: 0;
    background: white;
    padding: 1rem;
    border-top: 1px solid #e0e0e0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);
  }

  .cart-count {
    font-size: 0.95rem;
    font-weight: 600;
    color: #333;
  }

  .view-cart-btn {
    background: #2c5aa0;
    color: white;
    padding: 0.6rem 1.2rem;
    border-radius: 0.4rem;
    text-decoration: none;
    font-weight: 600;
    font-size: 0.9rem;
    transition: background 0.2s;
  }

  .view-cart-btn:hover {
    background: #1e3f6f;
  }
</style>
