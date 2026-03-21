<script>
  import { appState, currentUser } from '../lib/stores.js';
</script>

<div class="home-container">
  <div class="welcome-section">
    <h2 class="welcome-title">Welcome, {$currentUser?.display_name}!</h2>
    <p class="welcome-subtitle">
      {$currentUser?.base_location ? `Based in ${$currentUser.base_location}` : 'Select stores and manage your inventory'}
    </p>
  </div>

  <div class="menu-grid">
    <button
      class="menu-card"
      on:click={() => appState.set('search')}
    >
      <div class="card-icon">🔍</div>
      <h3>Search Stores</h3>
      <p>Find stores by name, city, or number</p>
    </button>

    <button
      class="menu-card"
      on:click={() => appState.set('cart')}
    >
      <div class="card-icon">🛒</div>
      <h3>Shopping Cart</h3>
      <p>Review and manage your orders</p>
    </button>

    <button class="menu-card coming-soon">
      <div class="card-icon">📊</div>
      <h3>Reports</h3>
      <p>View performance metrics</p>
    </button>

    <button class="menu-card coming-soon">
      <div class="card-icon">⭐</div>
      <h3>Testimonials</h3>
      <p>Success stories & case studies</p>
    </button>
  </div>

  <div class="info-section">
    <div class="info-card">
      <h4>Quick Start</h4>
      <ol>
        <li>Use Search Stores to find locations</li>
        <li>View pricing and payment plan options</li>
        <li>Add items to cart</li>
        <li>Review and checkout</li>
      </ol>
    </div>
  </div>
</div>

<style>
  .home-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem 1.5rem;
    width: 100%;
  }

  .welcome-section {
    text-align: center;
    margin-bottom: 2.5rem;
    padding-bottom: 1.5rem;
    border-bottom: 2px solid rgba(231, 76, 60, 0.2);
  }

  .welcome-title {
    font-size: 2rem;
    color: #1a1a2e;
    margin: 0 0 0.5rem 0;
    font-weight: 700;
  }

  .welcome-subtitle {
    font-size: 1rem;
    color: #64748b;
    margin: 0;
  }

  .menu-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
  }

  .menu-card {
    background: white;
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    padding: 2rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
  }

  .menu-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(231, 76, 60, 0.1), transparent);
    transition: left 0.5s;
  }

  .menu-card:hover:not(.coming-soon)::before {
    left: 100%;
  }

  .menu-card:hover:not(.coming-soon) {
    border-color: #e74c3c;
    box-shadow: 0 10px 30px rgba(231, 76, 60, 0.15);
    transform: translateY(-4px);
  }

  .card-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
  }

  .menu-card h3 {
    font-size: 1.2rem;
    color: #1a1a2e;
    margin: 0 0 0.5rem 0;
    font-weight: 700;
  }

  .menu-card p {
    font-size: 0.9rem;
    color: #64748b;
    margin: 0;
  }

  .menu-card.coming-soon {
    opacity: 0.6;
    cursor: default;
  }

  .menu-card.coming-soon::after {
    content: 'Coming Soon';
    position: absolute;
    top: 10px;
    right: 10px;
    background: #e74c3c;
    color: white;
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 700;
  }

  .info-section {
    margin-top: 2rem;
  }

  .info-card {
    background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
    border-left: 4px solid #e74c3c;
    padding: 1.5rem;
    border-radius: 8px;
  }

  .info-card h4 {
    color: #1a1a2e;
    margin: 0 0 1rem 0;
    font-size: 1.1rem;
  }

  .info-card ol {
    margin: 0;
    padding-left: 1.5rem;
    color: #475569;
    line-height: 1.8;
  }

  .info-card li {
    margin-bottom: 0.5rem;
  }

  @media (max-width: 768px) {
    .home-container {
      padding: 1.5rem 1rem;
    }

    .welcome-title {
      font-size: 1.5rem;
    }

    .menu-grid {
      grid-template-columns: 1fr;
      gap: 1rem;
    }

    .menu-card {
      padding: 1.5rem;
    }

    .card-icon {
      font-size: 2.5rem;
      margin-bottom: 0.75rem;
    }

    .menu-card h3 {
      font-size: 1.05rem;
    }
  }
</style>
