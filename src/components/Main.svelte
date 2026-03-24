<script>
  import { onMount } from 'svelte';
  import { theme, user } from '../lib/stores.js';
  import { get } from 'svelte/store';
  import StoreSearch from './StoreSearch.svelte';
  import ProspectSearch from './ProspectSearch.svelte';
  import Inventory from './Inventory.svelte';
  import Cart from './Cart.svelte';
  import CounterSignGenerator from './CounterSignGenerator.svelte';

  let currentTab = 'dashboard';
  let currentTheme = 'light';

  onMount(() => {
    theme.subscribe(t => currentTheme = t);
  });

  function toggleTheme() {
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    theme.set(newTheme);
    localStorage.setItem('theme', newTheme);
  }

  function handleLogout() {
    if (confirm('Sign out?')) {
      localStorage.removeItem('user');
      window.location.reload();
    }
  }
</script>

<div class="main" data-theme={currentTheme}>
  <!-- Header -->
  <header class="header">
    <div class="header-logo-section">
      <img src="/logo.png?v=2" alt="IndoorMedia" class="header-logo-img" />
    </div>

    <div class="header-bottom">
      <div class="header-info">
        <h1>imPro Sales Portal</h1>
        <p class="user-name">👤 {$user?.name || $user?.first_name}</p>
      </div>

      <div class="header-actions">
        <button class="theme-toggle" on:click={toggleTheme} title="Toggle theme">
          {currentTheme === 'light' ? '🌙' : '☀️'}
        </button>
        <button class="logout-btn" on:click={handleLogout}>Logout</button>
      </div>
    </div>
  </header>

  <!-- Tabs -->
  <nav class="tabs">
    <button 
      class="tab" 
      class:active={currentTab === 'dashboard'}
      on:click={() => currentTab = 'dashboard'}
    >
      📊 Dashboard
    </button>
    <button 
      class="tab" 
      class:active={currentTab === 'prospects'}
      on:click={() => currentTab = 'prospects'}
    >
      🎯 Prospects
    </button>
    <button 
      class="tab" 
      class:active={currentTab === 'stores'}
      on:click={() => currentTab = 'stores'}
    >
      🏪 Stores
    </button>
    <button 
      class="tab" 
      class:active={currentTab === 'inventory'}
      on:click={() => currentTab = 'inventory'}
    >
      📦 Inventory
    </button>
    <button 
      class="tab" 
      class:active={currentTab === 'cart'}
      on:click={() => currentTab = 'cart'}
    >
      🛒 Cart
    </button>
  </nav>

  <!-- Content -->
  <div class="content">
    {#if currentTab === 'dashboard'}
      <div class="dashboard">
        <h2>Welcome, {$user?.name || $user?.first_name}!</h2>
        {#if $user?.base_location}
          <p class="location-badge">📍 Territory: {$user.base_location}</p>
        {/if}
        <div class="dashboard-grid">
          <div class="stat-card">
            <div class="stat-icon">🎯</div>
            <h3>Prospects</h3>
            <p class="stat-value">0</p>
            <p class="stat-label">This Week</p>
          </div>
          <div class="stat-card">
            <div class="stat-icon">💰</div>
            <h3>Revenue</h3>
            <p class="stat-value">$0</p>
            <p class="stat-label">This Month</p>
          </div>
          <div class="stat-card">
            <div class="stat-icon">📈</div>
            <h3>Growth</h3>
            <p class="stat-value">0%</p>
            <p class="stat-label">vs Last Month</p>
          </div>
          <div class="stat-card">
            <div class="stat-icon">🏪</div>
            <h3>Stores</h3>
            <p class="stat-value">0</p>
            <p class="stat-label">In Territory</p>
          </div>
        </div>

        <div class="quick-actions">
          <h3>Quick Actions</h3>
          <div class="action-buttons">
            <button class="action-btn" on:click={() => currentTab = 'prospects'}>
              <span class="action-icon">🎯</span>
              <span>Find Prospects</span>
            </button>
            <button class="action-btn" on:click={() => currentTab = 'stores'}>
              <span class="action-icon">🏪</span>
              <span>Search Stores</span>
            </button>
            <button class="action-btn" on:click={() => currentTab = 'inventory'}>
              <span class="action-icon">📦</span>
              <span>Check Inventory</span>
            </button>
            <button class="action-btn" on:click={() => currentTab = 'cart'}>
              <span class="action-icon">🛒</span>
              <span>View Cart</span>
            </button>
          </div>
        </div>
      </div>
    {:else if currentTab === 'prospects'}
      <ProspectSearch />
    {:else if currentTab === 'stores'}
      <StoreSearch />
    {:else if currentTab === 'inventory'}
      <Inventory />
    {:else if currentTab === 'cart'}
      <Cart />
    {/if}
  </div>
</div>

<style>
  :global([data-theme='light']) {
    --bg-primary: #ffffff;
    --bg-secondary: #f9f9f9;
    --text-primary: #1a1a1a;
    --text-secondary: #666666;
    --text-tertiary: #999999;
    --border-color: #e0e0e0;
    --card-bg: #ffffff;
    --card-shadow: rgba(0, 0, 0, 0.08);
    --hover-bg: #f5f5f5;
    --input-bg: #ffffff;
  }

  :global([data-theme='dark']) {
    --bg-primary: #1a1a1a;
    --bg-secondary: #242424;
    --text-primary: #ffffff;
    --text-secondary: #aaaaaa;
    --text-tertiary: #777777;
    --border-color: #333333;
    --card-bg: #2a2a2a;
    --card-shadow: rgba(0, 0, 0, 0.3);
    --hover-bg: #333333;
    --input-bg: #2a2a2a;
  }

  .main {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--bg-primary);
    color: var(--text-primary);
  }

  /* Header */
  .header {
    background: linear-gradient(135deg, #CC0000 0%, #990000 100%);
    color: white;
    padding: 0;
    padding-top: calc(env(safe-area-inset-top, 0px));
    display: flex;
    flex-direction: column;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  .header-logo-section {
    padding: 40px 20px 20px;
    text-align: center;
  }

  .header-logo-img {
    width: 120px;
    height: 120px;
    object-fit: contain;
    display: block;
    margin: 0 auto;
  }

  .header-bottom {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    padding: 12px 20px 20px;
    gap: 16px;
  }

  .header-info {
    margin: 0;
  }

  .header-info h1 {
    margin: 0;
    font-size: 22px;
    font-weight: 700;
    line-height: 1.2;
  }

  .user-name {
    margin: 4px 0 0;
    font-size: 12px;
    opacity: 0.9;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
  }

  .theme-toggle, .logout-btn {
    background: rgba(255, 255, 255, 0.2);
    color: white;
    border: none;
    padding: 8px 12px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
    transition: all 0.2s;
  }

  .theme-toggle:hover, .logout-btn:hover {
    background: rgba(255, 255, 255, 0.3);
    transform: translateY(-1px);
  }

  /* Tabs */
  .tabs {
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    display: flex;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    padding: 0 4px;
  }

  .tab {
    flex: 1;
    min-width: fit-content;
    padding: 12px 16px;
    background: none;
    border: none;
    border-bottom: 3px solid transparent;
    color: var(--text-secondary);
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
  }

  .tab:hover {
    color: var(--text-primary);
  }

  .tab.active {
    color: #CC0000;
    border-bottom-color: #CC0000;
  }

  /* Content */
  .content {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
  }

  /* Dashboard */
  .dashboard {
    max-width: 1200px;
    margin: 0 auto;
  }

  .dashboard h2 {
    margin: 0 0 8px;
    color: var(--text-primary);
    font-size: 24px;
  }

  .location-badge {
    margin: 0 0 24px;
    padding: 8px 12px;
    background: rgba(204, 0, 0, 0.1);
    color: #CC0000;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    display: inline-block;
  }

  .dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
  }

  .stat-card {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
  }

  .stat-icon {
    font-size: 32px;
    margin-bottom: 8px;
  }

  .stat-card h3 {
    margin: 0 0 8px;
    font-size: 14px;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .stat-value {
    margin: 0 0 4px;
    font-size: 28px;
    font-weight: 700;
    color: #CC0000;
  }

  .stat-label {
    margin: 0;
    font-size: 12px;
    color: var(--text-tertiary);
  }

  .quick-actions {
    margin-top: 32px;
  }

  .quick-actions h3 {
    margin: 0 0 16px;
    color: var(--text-primary);
    font-size: 16px;
  }

  .action-buttons {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px;
  }

  .action-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 16px;
    background: var(--card-bg);
    border: 2px solid var(--border-color);
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.2s;
    color: var(--text-primary);
    font-weight: 600;
    font-size: 13px;
  }

  .action-btn:hover {
    border-color: #CC0000;
    background: rgba(204, 0, 0, 0.05);
  }

  .action-icon {
    font-size: 24px;
  }

  @media (max-width: 768px) {
    .header-logo-section {
      padding: 32px 16px 16px;
    }

    .header-bottom {
      padding: 10px 16px 16px;
      flex-direction: column;
      align-items: flex-start;
    }

    .header-info h1 {
      font-size: 20px;
    }

    .content {
      padding: 16px;
    }

    .dashboard-grid {
      grid-template-columns: repeat(2, 1fr);
    }

    .action-buttons {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (max-width: 480px) {
    .header-logo-section {
      padding: 24px 12px 12px;
    }

    .header-logo-svg {
      max-width: 280px;
    }

    .header-bottom {
      padding: 8px 12px 12px;
    }

    .header-info h1 {
      font-size: 18px;
    }

    .tabs {
      padding: 0;
    }

    .tab {
      padding: 10px 12px;
      font-size: 12px;
    }

    .dashboard h2 {
      font-size: 20px;
    }

    .dashboard-grid, .action-buttons {
      grid-template-columns: 1fr;
    }
  }
</style>
