<script>
  import { createEventDispatcher } from 'svelte';
  import { currentTab, cart, error } from '../lib/stores.js';
  import StoreSearch from './StoreSearch.svelte';
  import ProspectSearch from './ProspectSearch.svelte';
  import TestimonialSearch from './TestimonialSearch.svelte';
  import Cart from './Cart.svelte';
  import Dashboard from './Dashboard.svelte';
  import ROICalculator from './ROICalculator.svelte';
  import EmailTemplates from './EmailTemplates.svelte';
  import QuickLinks from './QuickLinks.svelte';
  import AuditStore from './AuditStore.svelte';
  import Notepad from './Notepad.svelte';

  const dispatch = createEventDispatcher();

  export let user;

  let cartCount = 0;
  cart.subscribe(items => {
    cartCount = items.length;
  });

  function handleLogout() {
    dispatch('logout');
  }
</script>

<div class="main">
  <header class="header">
    <div class="header-content">
      <h1>IndoorMedia</h1>
      <p class="user-name">Hi, {user.name || user.first_name}</p>
    </div>
    <button class="logout-btn" on:click={handleLogout}>Logout</button>
  </header>

  {#if $error}
    <div class="error-banner">{$error}</div>
  {/if}

  <nav class="tabs">
    <button class="tab {$currentTab === 'search' ? 'active' : ''}" on:click={() => currentTab.set('search')}>🏪 Stores</button>
    <button class="tab {$currentTab === 'prospects' ? 'active' : ''}" on:click={() => currentTab.set('prospects')}>🎯 Prospects</button>
    <button class="tab {$currentTab === 'clients' ? 'active' : ''}" on:click={() => currentTab.set('clients')}>💼 Clients</button>
    <button class="tab {$currentTab === 'tools' ? 'active' : ''}" on:click={() => currentTab.set('tools')}>⚙️ Tools</button>
    <button class="tab {$currentTab === 'dashboard' ? 'active' : ''}" on:click={() => currentTab.set('dashboard')}>📊 Stats</button>
    <button class="tab {$currentTab === 'cart' ? 'active' : ''}" on:click={() => currentTab.set('cart')}>🛒 {cartCount > 0 ? `(${cartCount})` : 'Cart'}</button>
  </nav>

  <div class="content">
    {#if $currentTab === 'search'}
      <StoreSearch />
    {:else if $currentTab === 'prospects'}
      <ProspectSearch />
    {:else if $currentTab === 'clients'}
      <!-- Clients = saved prospects with status -->
      <ProspectSearch />
    {:else if $currentTab === 'tools'}
      <!-- Tools submenu -->
      <div class="tools-grid">
        <button class="tool-card" on:click={() => currentTab.set('roi')}>
          <span class="tool-icon">📊</span>
          <span class="tool-name">ROI Calculator</span>
          <span class="tool-desc">Show customers their return</span>
        </button>
        <button class="tool-card" on:click={() => currentTab.set('testimonials')}>
          <span class="tool-icon">⭐</span>
          <span class="tool-name">Testimonial Search</span>
          <span class="tool-desc">Find social proof</span>
        </button>
        <button class="tool-card" on:click={() => currentTab.set('audit')}>
          <span class="tool-icon">🏪</span>
          <span class="tool-name">Audit Store</span>
          <span class="tool-desc">Track inventory & delivery</span>
        </button>
        <button class="tool-card" on:click={() => currentTab.set('email')}>
          <span class="tool-icon">✉️</span>
          <span class="tool-name">Email Templates</span>
          <span class="tool-desc">Ready-to-send outreach</span>
        </button>
        <button class="tool-card" on:click={() => currentTab.set('notepad')}>
          <span class="tool-icon">📝</span>
          <span class="tool-name">Notepad</span>
          <span class="tool-desc">Quick field notes</span>
        </button>
        <button class="tool-card" on:click={() => currentTab.set('links')}>
          <span class="tool-icon">🔗</span>
          <span class="tool-name">Quick Links</span>
          <span class="tool-desc">MapPoint, Coupons, Drive</span>
        </button>
      </div>
    {:else if $currentTab === 'dashboard'}
      <Dashboard {user} />
    {:else if $currentTab === 'roi'}
      <ROICalculator />
    {:else if $currentTab === 'testimonials'}
      <TestimonialSearch />
    {:else if $currentTab === 'audit'}
      <AuditStore />
    {:else if $currentTab === 'email'}
      <EmailTemplates {user} />
    {:else if $currentTab === 'notepad'}
      <Notepad />
    {:else if $currentTab === 'links'}
      <QuickLinks />
    {:else if $currentTab === 'cart'}
      <Cart />
    {/if}
  </div>
</div>

<style>
  .main {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: #f5f5f5;
  }

  .header {
    background: linear-gradient(135deg, #CC0000 0%, #1a1a1a 100%);
    color: white;
    padding: 20px 20px;
    padding-top: 70px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    min-height: 140px;
  }

  .header-content h1 {
    margin: 0;
    font-size: 24px;
    font-weight: 700;
  }

  .user-name {
    margin: 4px 0 0 0;
    font-size: 13px;
    opacity: 0.9;
  }

  .logout-btn {
    background: rgba(255, 255, 255, 0.2);
    color: white;
    border: 1px solid rgba(255, 255, 255, 0.5);
    padding: 8px 16px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    transition: background 0.2s;
  }

  .logout-btn:hover {
    background: rgba(255, 255, 255, 0.3);
  }

  .error-banner {
    background: #fee;
    color: #c33;
    padding: 12px 20px;
    font-size: 14px;
    border-bottom: 1px solid #fcc;
  }

  .tabs {
    display: flex;
    gap: 0;
    background: white;
    border-bottom: 1px solid #ddd;
    overflow-x: auto;
    margin-bottom: 8px;
  }

  .tab {
    flex: 1;
    min-width: 80px;
    padding: 14px 16px;
    background: none;
    border: none;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    color: #666;
    border-bottom: 3px solid transparent;
    transition: all 0.3s;
    white-space: nowrap;
  }

  .tab:hover {
    color: #CC0000;
    background: #fafafa;
  }

  .tab.active {
    color: #CC0000;
    border-bottom-color: #CC0000;
  }

  .content {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
  }

  .tools-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    max-width: 600px;
    margin: 0 auto;
  }

  .tool-card {
    background: white;
    border: 2px solid #e0e0e0;
    border-radius: 12px;
    padding: 20px 16px;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    transition: all 0.2s;
    text-align: center;
  }

  .tool-card:hover {
    border-color: #CC0000;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  }

  .tool-icon { font-size: 32px; }
  .tool-name { font-size: 14px; font-weight: 700; color: #1a1a1a; }
  .tool-desc { font-size: 11px; color: #999; }

  @media (max-width: 480px) {
    .header {
      padding: 12px 16px;
      min-height: 60px;
    }

    .header-content h1 {
      font-size: 20px;
    }

    .logout-btn {
      padding: 6px 12px;
      font-size: 12px;
    }

    .tab {
      padding: 10px 12px;
      font-size: 12px;
    }

    .content {
      padding: 16px;
    }
  }
</style>
