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
  import HotLeadsSubmit from './HotLeadsSubmit.svelte';

  let currentTab = 'dashboard';
  let currentTheme = 'light';
  let cartCount = 0;
  let contracts = [];
  let allStores = [];
  let savedProspects = [];
  let analyticsView = 'year';
  let analyticsZone = 'all';

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
    
    // Saved prospects this week (check both key formats)
    try {
      const saved1 = JSON.parse(localStorage.getItem('savedProspects') || '[]');
      const saved2 = JSON.parse(localStorage.getItem('saved_prospects') || '[]');
      const saved = saved1.length > saved2.length ? saved1 : saved2;
      const weekAgo = new Date(now);
      weekAgo.setDate(weekAgo.getDate() - 7);
      savedProspects = saved;
      
      // Count saved prospects this week
      const savedThisWeek = saved.filter(p => {
        const d = new Date(p.savedAt || p.saved_at || 0);
        return d >= weekAgo;
      }).length;
      
      // Count searches this week
      const searches = JSON.parse(localStorage.getItem('impro_searches') || '[]');
      const searchesThisWeek = searches.filter(s => new Date(s.date) >= weekAgo).length;
      
      // Count phone clicks this week
      const phoneCalls = JSON.parse(localStorage.getItem('impro_phone_clicks') || '[]');
      const callsThisWeek = phoneCalls.filter(c => new Date(c.date) >= weekAgo).length;
      
      // Total activity = saved + searches + phone clicks
      prospectsThisWeek = savedThisWeek + searchesThisWeek + callsThisWeek;
      if (prospectsThisWeek === 0) prospectsThisWeek = saved.length; // fallback to total saved
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
        fetch(import.meta.env.BASE_URL + 'data/contracts.json'),
        fetch(import.meta.env.BASE_URL + 'data/stores.json')
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

  function getFilteredContracts() {
    if (analyticsZone === 'all') return contracts;
    return contracts.filter(c => (c.zone || '') === analyticsZone);
  }

  function getAvailableZones() {
    const zones = new Set();
    contracts.forEach(c => { if (c.zone) zones.add(c.zone); });
    return Array.from(zones).sort();
  }

  function getYearlyStats() {
    const filtered = getFilteredContracts();
    const byYear = {};
    filtered.forEach(c => {
      const date = c.date || '';
      if (!date) return;
      try {
        const year = date.includes('/') ? new Date(date).getFullYear() : parseInt(date.substring(0, 4));
        if (!byYear[year]) byYear[year] = { year, total: 0, count: 0 };
        byYear[year].total += c.total_amount || 0;
        byYear[year].count += 1;
      } catch {}
    });
    const sorted = Object.values(byYear).sort((a, b) => b.year - a.year);
    sorted.forEach((stat, i) => {
      const prior = sorted[i + 1];
      stat.change = prior ? ((stat.total - prior.total) / prior.total) * 100 : null;
    });
    return sorted;
  }

  function getMonthlyStats() {
    const filtered = getFilteredContracts();
    const byMonth = {};
    filtered.forEach(c => {
      const date = c.date || '';
      if (!date) return;
      try {
        const d = date.includes('/') ? new Date(date) : new Date(date.substring(0, 10));
        const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
        if (!byMonth[key]) byMonth[key] = { key, total: 0, count: 0 };
        byMonth[key].total += c.total_amount || 0;
        byMonth[key].count += 1;
      } catch {}
    });
    return Object.values(byMonth).sort((a, b) => b.key.localeCompare(a.key)).map(m => ({
      ...m,
      label: new Date(m.key + '-01').toLocaleDateString('en-US', { year: 'numeric', month: 'short' })
    }));
  }

  function getRepStats() {
    const filtered = getFilteredContracts();
    const byRep = {};
    filtered.forEach(c => {
      const rep = c.sales_rep || 'Unknown';
      const date = c.date || '';
      let year = 0;
      try {
        year = date.includes('/') ? new Date(date).getFullYear() : parseInt(date.substring(0, 4));
      } catch {}
      if (!byRep[rep]) byRep[rep] = { rep, y2025: 0, y2026: 0, total: 0, count: 0 };
      const amt = c.total_amount || 0;
      byRep[rep].total += amt;
      byRep[rep].count += 1;
      if (year === 2025) byRep[rep].y2025 += amt;
      if (year === 2026) byRep[rep].y2026 += amt;
    });
    return Object.values(byRep).sort((a, b) => b.total - a.total);
  }

  function toggleTheme() {
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    theme.set(newTheme);
    localStorage.setItem('theme', newTheme);
  }

  function handleLogout() {
    if (confirm('Sign out?')) {
      localStorage.removeItem('user');
      localStorage.removeItem('roogleCredentials');
      window.location.reload();
    }
  }

  function forgetRoogleCredentials() {
    if (confirm('Forget saved Roogle credentials?')) {
      localStorage.removeItem('roogleCredentials');
      alert('✅ Credentials cleared. You\'ll need to enter them again next time.');
    }
  }
</script>

<div class="main" data-theme={currentTheme}>
  <!-- Header -->
  <header class="header">
    <div class="header-top">
      <div class="header-logo-wrapper">
        <div class="logo-backdrop">
          <img src="{import.meta.env.BASE_URL}logo.png?v=2" alt="IndoorMedia" class="header-logo-img" />
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
        <button class="logout-btn" on:click={forgetRoogleCredentials} title="Clear Roogle login">🔑</button>
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
    <button 
      class="tab" 
      class:active={currentTab === 'analytics'}
      on:click={() => currentTab = 'analytics'}
    >
      📊 Analytics
    </button>
    <button 
      class="tab" 
      class:active={currentTab === 'addlead'}
      on:click={() => currentTab = 'addlead'}
    >
      ➕ Add Lead
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
    {:else if currentTab === 'analytics'}
      <div class="analytics-container">
        <h2>📊 Sales Analytics</h2>
        
        <!-- View selector -->
        <div class="period-selector">
          <button class="period-btn" class:active={analyticsView === 'year'} on:click={() => analyticsView = 'year'}>By Year</button>
          <button class="period-btn" class:active={analyticsView === 'month'} on:click={() => analyticsView = 'month'}>By Month</button>
          <button class="period-btn" class:active={analyticsView === 'rep'} on:click={() => analyticsView = 'rep'}>By Rep</button>
        </div>

        <!-- Zone filter -->
        <div class="zone-filter">
          <span class="zone-label">Zone:</span>
          <button class="zone-btn" class:active={analyticsZone === 'all'} on:click={() => analyticsZone = 'all'}>All</button>
          {#each getAvailableZones() as zone}
            <button class="zone-btn" class:active={analyticsZone === zone} on:click={() => analyticsZone = zone}>{zone}</button>
          {/each}
        </div>

        {#if analyticsZone !== 'all'}
          <p class="zone-active-label">Filtered: Zone {analyticsZone} ({getFilteredContracts().length} contracts, ${getFilteredContracts().reduce((s,c) => s + (c.total_amount||0), 0).toLocaleString()})</p>
        {/if}

        {#if analyticsView === 'year'}
          <div class="analytics-cards">
            {#each getYearlyStats() as stat}
              <div class="analytics-card">
                <div class="analytics-year">{stat.year}</div>
                <div class="analytics-amount">${(stat.total / 1000).toFixed(0)}K</div>
                <div class="analytics-count">{stat.count} contracts</div>
                {#if stat.change !== null}
                  <div class="analytics-change" class:positive={stat.change > 0} class:negative={stat.change < 0}>
                    {stat.change > 0 ? '↑' : '↓'} {Math.abs(stat.change).toFixed(1)}%
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        {:else if analyticsView === 'month'}
          <div class="month-table">
            <table>
              <thead><tr><th>Month</th><th>Revenue</th><th>Contracts</th><th>Avg Deal</th></tr></thead>
              <tbody>
                {#each getMonthlyStats() as stat}
                  <tr>
                    <td>{stat.label}</td>
                    <td>${stat.total.toLocaleString()}</td>
                    <td>{stat.count}</td>
                    <td>${(stat.total / stat.count).toLocaleString(undefined, {maximumFractionDigits: 0})}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {:else if analyticsView === 'rep'}
          <div class="rep-table">
            <table>
              <thead><tr><th>Rep</th><th>2025</th><th>2026 YTD</th><th>Total</th><th>Deals</th></tr></thead>
              <tbody>
                {#each getRepStats() as stat}
                  <tr>
                    <td>{stat.rep}</td>
                    <td>${stat.y2025.toLocaleString()}</td>
                    <td>${stat.y2026.toLocaleString()}</td>
                    <td>${stat.total.toLocaleString()}</td>
                    <td>{stat.count}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>
    {:else if currentTab === 'addlead'}
      <HotLeadsSubmit
        user={$user}
        onLeadSubmitted={() => {
          // Optional: show confirmation or navigate back to prospects
          currentTab = 'prospects';
        }}
      />
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
    margin: 0;
    margin-left: calc(-1 * env(safe-area-inset-left));
    margin-right: calc(-1 * env(safe-area-inset-right));
    padding-top: calc(16px + env(safe-area-inset-top));
    padding-left: calc(20px + env(safe-area-inset-left));
    padding-right: calc(20px + env(safe-area-inset-right));
    padding-bottom: 16px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 8px 24px rgba(204, 0, 0, 0.2);
  }

  .header-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0;
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
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    overflow: hidden;
  }

  .header-logo-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
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
    padding: 0;
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
  /* Analytics */
  .analytics-container { padding: 16px; max-width: 900px; margin: 0 auto; }
  .period-selector { display: flex; gap: 8px; margin-bottom: 12px; }
  .zone-filter { display: flex; align-items: center; gap: 6px; margin-bottom: 16px; overflow-x: auto; white-space: nowrap; padding-bottom: 4px; }
  .zone-label { font-size: 12px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; flex-shrink: 0; }
  .zone-btn { padding: 5px 12px; border: 1px solid var(--border-color); border-radius: 16px; background: var(--card-bg); font-size: 12px; font-weight: 600; cursor: pointer; color: var(--text-secondary); transition: all 0.2s; flex-shrink: 0; }
  .zone-btn.active { background: #1a237e; color: white; border-color: #1a237e; }
  .zone-btn:hover:not(.active) { border-color: #1a237e; color: #1a237e; }
  .zone-active-label { font-size: 13px; color: #1a237e; font-weight: 600; margin-bottom: 16px; }
  .period-btn { padding: 8px 16px; border: 1px solid var(--border-color); border-radius: 20px; background: var(--card-bg); color: var(--text-secondary); font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
  .period-btn.active { background: #CC0000; color: white; border-color: #CC0000; }
  .analytics-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; }
  .analytics-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 16px; text-align: center; }
  .analytics-year { font-size: 18px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px; }
  .analytics-amount { font-size: 28px; font-weight: 800; color: #CC0000; margin-bottom: 4px; }
  .analytics-count { font-size: 12px; color: var(--text-secondary); margin-bottom: 8px; }
  .analytics-change { font-size: 14px; font-weight: 600; padding: 4px 8px; border-radius: 8px; display: inline-block; }
  .analytics-change.positive { background: #e8f5e9; color: #2e7d32; }
  .analytics-change.negative { background: #ffebee; color: #c62828; }
  .month-table, .rep-table { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; overflow: hidden; }
  .month-table table, .rep-table table { width: 100%; border-collapse: collapse; }
  .month-table th, .rep-table th { background: var(--bg-secondary); padding: 12px; text-align: left; font-weight: 700; font-size: 12px; color: var(--text-secondary); text-transform: uppercase; border-bottom: 1px solid var(--border-color); }
  .month-table td, .rep-table td { padding: 12px; border-bottom: 1px solid var(--border-color); color: var(--text-primary); }
  .month-table tr:last-child td, .rep-table tr:last-child td { border-bottom: none; }
  .month-table tr:hover, .rep-table tr:hover { background: var(--bg-secondary); }
</style>
