<script>
  import { createEventDispatcher } from 'svelte';
  import { currentTab, cart, error } from '../lib/stores.js';
  import { theme, toggleTheme } from '../lib/theme.js';
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
  import Products from './Products.svelte';
  import CounterSignGenerator from './CounterSignGenerator.svelte';

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
      <div class="logo-container">
        <img src="/logo.svg" alt="IndoorMedia" class="header-logo" onerror="this.src='/indoormedia-logo.png'" />
        <span class="pro-badge">Pro</span>
      </div>
      <p class="user-name">Hi, {user.name || user.first_name}</p>
    </div>
    <div class="header-actions">
      <button class="theme-toggle" on:click={toggleTheme} title="Toggle theme">
        {$theme === 'light' ? '🌙' : '☀️'}
      </button>
      <button class="logout-btn" on:click={handleLogout}>Logout</button>
    </div>
  </header>

  {#if $error}
    <div class="error-banner">{$error}</div>
  {/if}

  <nav class="tabs">
    <button class="tab {$currentTab === 'search' ? 'active' : ''}" on:click={() => currentTab.set('search')}>🏪 Stores</button>
    <button class="tab {$currentTab === 'prospects' ? 'active' : ''}" on:click={() => currentTab.set('prospects')}>🎯 Prospects</button>
    <button class="tab {$currentTab === 'products' ? 'active' : ''}" on:click={() => currentTab.set('products')}>📦 Products</button>
    <button class="tab {$currentTab === 'tools' ? 'active' : ''}" on:click={() => currentTab.set('tools')}>⚙️ Tools</button>
    <button class="tab {$currentTab === 'dashboard' ? 'active' : ''}" on:click={() => currentTab.set('dashboard')}>📊 Stats</button>
    <button class="tab {$currentTab === 'cart' ? 'active' : ''}" on:click={() => currentTab.set('cart')}>🛒 {cartCount > 0 ? `(${cartCount})` : 'Cart'}</button>
  </nav>

  <div class="content">
    {#if $currentTab === 'search'}
      <StoreSearch />
    {:else if $currentTab === 'prospects'}
      <ProspectSearch />
    {:else if $currentTab === 'products'}
      <Products />
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
        <button class="tool-card" on:click={() => currentTab.set('countersign')}>
          <span class="tool-icon">🏷️</span>
          <span class="tool-name">Counter Signs</span>
          <span class="tool-desc">In-store signage</span>
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
    {:else if $currentTab === 'countersign'}
      <CounterSignGenerator />
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
    padding: 20px 20px 16px 20px;
    padding-top: calc(env(safe-area-inset-top, 50px) + 20px);
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .logo-container {
    position: relative;
    display: flex;
    align-items: center;
    height: 64px;
    margin-bottom: 8px;
  }

  .header-logo {
    height: 64px;
    width: auto;
  }

  .pro-badge {
    position: absolute;
    top: -5px;
    right: -15px;
    background: #FF6B35;
    color: white;
    font-weight: bold;
    font-size: 11px;
    padding: 3px 7px;
    border-radius: 10px;
    border: 2px solid white;
    letter-spacing: 0.5px;
  }

  .user-name {
    margin: 4px 0 0 0;
    font-size: 13px;
    opacity: 0.9;
  }

  .header-actions {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .theme-toggle {
    background: rgba(255, 255, 255, 0.2);
    color: white;
    border: 1px solid rgba(255, 255, 255, 0.5);
    padding: 8px 12px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 18px;
    line-height: 1;
    transition: background 0.2s;
  }

  .theme-toggle:hover {
    background: rgba(255, 255, 255, 0.3);
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
    border-bottom: 2px solid #eee;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    padding: 0 4px;
  }

  .tabs::-webkit-scrollbar { display: none; }

  .tab {
    flex: 0 0 auto;
    padding: 14px 18px;
    background: none;
    border: none;
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
    color: #888;
    border-bottom: 3px solid transparent;
    transition: all 0.2s;
    white-space: nowrap;
    letter-spacing: 0.3px;
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
      padding: 16px 16px 14px 16px;
      padding-top: calc(env(safe-area-inset-top, 50px) + 16px);
    }

    .header-content h1 {
      font-size: 20px;
    }

    .logout-btn {
      padding: 6px 12px;
      font-size: 12px;
    }

    .tab {
      padding: 12px 14px;
      font-size: 12px;
    }

    .content {
      padding: 16px;
    }

    .tools-grid {
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
    }
  }
</style>
