<script>
  import { onMount } from 'svelte';
  import { theme, user } from '../lib/stores.js';
  import { get } from 'svelte/store';
  import StoreSearch from './StoreSearch.svelte';
  import ProspectSearch from './ProspectSearch.svelte';
  import Tools from './Tools.svelte';
  import Cart from './Cart.svelte';
  import Products from './Products.svelte';
  import Clients from './Clients.svelte';
  import ManageReps from './ManageReps.svelte';

  let currentTab = 'dashboard';
  let currentTheme = 'light';
  let cartCount = 0;
  let contracts = [];
  let allStores = [];
  let savedProspects = [];

  // Dashboard stats
  let prospectsThisWeek = 0;
  let revenueThisMonth = 0;
  let growthPercent = 0;
  let storesInTerritory = 0;

  function updateCartCount() {
    try { cartCount = JSON.parse(localStorage.getItem('indoormedia_cart') || '[]').length; } catch { cartCount = 0; }
  }

  function computeDashboardStats() {
    const repName = ($user?.name || $user?.first_name || '').toLowerCase();
    const isManager = repName.includes('tyler') || $user?.role === 'manager' || $user?.role === 'admin';
    const now = new Date();
    
    // Saved prospects this week
    try {
      const saved = JSON.parse(localStorage.getItem('saved_prospects') || '[]');
      const weekAgo = new Date(now);
      weekAgo.setDate(weekAgo.getDate() - 7);
      savedProspects = saved;
      prospectsThisWeek = saved.filter(p => {
        const d = new Date(p.savedAt || p.saved_at || 0);
        return d >= weekAgo;
      }).length || saved.length; // fallback to total if no dates
    } catch { prospectsThisWeek = 0; }

    // Revenue this month from contracts
    const thisMonth = now.getMonth();
    const thisYear = now.getFullYear();
    const lastMonth = thisMonth === 0 ? 11 : thisMonth - 1;
    const lastMonthYear = thisMonth === 0 ? thisYear - 1 : thisYear;
    
    const myContracts = isManager ? contracts : contracts.filter(c => {
      const rep = (c.sales_rep || '').toLowerCase();
      return rep.includes(repName.split(' ')[0]);
    });
    
    const thisMonthContracts = myContracts.filter(c => {
      const d = new Date(c.date);
      return d.getMonth() === thisMonth && d.getFullYear() === thisYear;
    });
    const lastMonthContracts = myContracts.filter(c => {
      const d = new Date(c.date);
      return d.getMonth() === lastMonth && d.getFullYear() === lastMonthYear;
    });
    
    revenueThisMonth = thisMonthContracts.reduce((sum, c) => sum + (c.total_amount || 0), 0);
    const lastMonthRevenue = lastMonthContracts.reduce((sum, c) => sum + (c.total_amount || 0), 0);
    growthPercent = lastMonthRevenue > 0 ? Math.round(((revenueThisMonth - lastMonthRevenue) / lastMonthRevenue) * 100) : 0;

    // Stores in territory (based on user's state)
    const userLocation = $user?.base_location || '';
    const userState = userLocation.split(',').pop()?.trim().toUpperCase() || '';
    if (isManager) {
      // Show OR + WA for Tyler
      storesInTerritory = allStores.filter(s => s.State === 'OR' || s.State === 'WA').length;
    } else if (userState) {
      storesInTerritory = allStores.filter(s => s.State === userState).length;
    } else {
      storesInTerritory = allStores.length;
    }
  }

  onMount(async () => {
    theme.subscribe(t => currentTheme = t);
    updateCartCount();
    const interval = setInterval(updateCartCount, 2000);

    try {
      const [contractsRes, storesRes] = await Promise.all([
        fetch('/data/contracts.json'),
        fetch('/data/stores.json')
      ]);
      const contractsData = await contractsRes.json();
      contracts = contractsData.contracts || [];
      allStores = await storesRes.json().catch(() => []);
      computeDashboardStats();
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    }

    return () => clearInterval(interval);
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
    <div class="header-top">
      <div class="header-logo-wrapper">
        <div class="logo-backdrop">
          <img src="/logo.png?v=2" alt="IndoorMedia" class="header-logo-img" />
        </div>
        <div class="header-text">
          <h1 class="portal-title">imPro</h1>
          <p class="portal-subtitle">Sales Portal</p>
        </div>
      </div>

      <div class="header-actions">
        <button class="cart-icon" on:click={() => currentTab = 'cart'} title="Cart">
          🛒
          {#if cartCount > 0}
            <span class="cart-badge">{cartCount}</span>
          {/if}
        </button>
        <button class="theme-toggle" on:click={toggleTheme} title="Toggle theme">
          {currentTheme === 'light' ? '🌙' : '☀️'}
        </button>
        <button class="logout-btn" on:click={handleLogout}>Logout</button>
      </div>
    </div>

    <div class="header-bottom">
      <p class="user-greeting">Welcome, <strong>{$user?.name || $user?.first_name}</strong></p>
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
      class:active={currentTab === 'tools'}
      on:click={() => currentTab = 'tools'}
    >
      🛠️ Tools
    </button>

    <button 
      class="tab" 
      class:active={currentTab === 'products'}
      on:click={() => currentTab = 'products'}
    >
      📦 Products
    </button>
    <button 
      class="tab" 
      class:active={currentTab === 'clients'}
      on:click={() => currentTab = 'clients'}
    >
      💼 Clients
    </button>
    {#if $user?.role === 'manager' || $user?.role === 'admin'}
      <button 
        class="tab" 
        class:active={currentTab === 'manage'}
        on:click={() => currentTab = 'manage'}
      >
        👥 Manage
      </button>
    {/if}
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
            <p class="stat-value">{prospectsThisWeek}</p>
            <p class="stat-label">This Week</p>
          </div>
          <div class="stat-card">
            <div class="stat-icon">💰</div>
            <h3>Revenue</h3>
            <p class="stat-value">${revenueThisMonth.toLocaleString()}</p>
            <p class="stat-label">This Month</p>
          </div>
          <div class="stat-card">
            <div class="stat-icon">📈</div>
            <h3>Growth</h3>
            <p class="stat-value">{growthPercent}%</p>
            <p class="stat-label">vs Last Month</p>
          </div>
          <div class="stat-card">
            <div class="stat-icon">🏪</div>
            <h3>Stores</h3>
            <p class="stat-value">{storesInTerritory.toLocaleString()}</p>
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
            <button class="action-btn" on:click={() => currentTab = 'tools'}>
              <span class="action-icon">🛠️</span>
              <span>Tools & Audit</span>
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
    {:else if currentTab === 'tools'}
      <Tools />
    {:else if currentTab === 'cart'}
      <Cart />
    {:else if currentTab === 'products'}
      <Products />
    {:else if currentTab === 'clients'}
      <Clients />
    {:else if currentTab === 'manage'}
      <ManageReps />
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
    box-shadow: 0 8px 24px rgba(204, 0, 0, 0.2);
  }

  .header-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    gap: 20px;
  }

  .header-logo-wrapper {
    display: flex;
    align-items: center;
    gap: 12px;
    flex: 1;
  }

  .logo-backdrop {
    width: 56px;
    height: 56px;
    background: rgba(255, 255, 255, 0.15);
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.25);
  }

  .header-logo-img {
    width: 44px;
    height: 44px;
    object-fit: contain;
  }

  .header-text {
    margin: 0;
  }

  .portal-title {
    margin: 0;
    font-size: 24px;
    font-weight: 800;
    letter-spacing: -0.5px;
    line-height: 1;
  }

  .portal-subtitle {
    margin: 2px 0 0;
    font-size: 11px;
    font-weight: 500;
    opacity: 0.85;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .header-bottom {
    padding: 0 20px 12px;
    text-align: left;
  }

  .user-greeting {
    margin: 0;
    font-size: 13px;
    opacity: 0.9;
  }

  .user-greeting strong {
    font-weight: 700;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
  }

  .cart-icon {
    background: rgba(255, 255, 255, 0.2);
    border: none;
    color: white;
    font-size: 18px;
    cursor: pointer;
    position: relative;
    padding: 8px 12px;
    border-radius: 8px;
    transition: all 0.2s;
  }

  .cart-icon:hover {
    background: rgba(255, 255, 255, 0.3);
    transform: translateY(-1px);
  }

  .cart-badge {
    position: absolute;
    top: -4px;
    right: -6px;
    background: white;
    color: #CC0000;
    font-size: 11px;
    font-weight: 700;
    min-width: 18px;
    height: 18px;
    border-radius: 9px;
    display: flex;
    align-items: center;
    justify-content: center;
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
    border-bottom: 2px solid transparent;
    color: #666;
    font-weight: 600;
    font-size: 13px;
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
