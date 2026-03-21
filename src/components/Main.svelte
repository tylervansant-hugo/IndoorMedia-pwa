<script>
  import { createEventDispatcher } from 'svelte';
  import { currentTab, cart, error } from '../lib/stores.js';
  import StoreSearch from './StoreSearch.svelte';
  import ProspectSearch from './ProspectSearch.svelte';
  import TestimonialSearch from './TestimonialSearch.svelte';
  import Cart from './Cart.svelte';

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
    <button
      class="tab {$currentTab === 'search' ? 'active' : ''}"
      on:click={() => currentTab.set('search')}
    >
      🏪 Stores
    </button>
    <button
      class="tab {$currentTab === 'prospects' ? 'active' : ''}"
      on:click={() => currentTab.set('prospects')}
    >
      👥 Prospects
    </button>
    <button
      class="tab {$currentTab === 'testimonials' ? 'active' : ''}"
      on:click={() => currentTab.set('testimonials')}
    >
      ⭐ Testimonials
    </button>
    <button
      class="tab {$currentTab === 'cart' ? 'active' : ''}"
      on:click={() => currentTab.set('cart')}
    >
      🛒 Cart {cartCount > 0 ? `(${cartCount})` : ''}
    </button>
  </nav>

  <div class="content">
    {#if $currentTab === 'search'}
      <StoreSearch />
    {:else if $currentTab === 'prospects'}
      <ProspectSearch />
    {:else if $currentTab === 'testimonials'}
      <TestimonialSearch />
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
    background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%);
    color: white;
    padding: 16px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    min-height: 70px;
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
  }

  .tab {
    flex: 1;
    min-width: 80px;
    padding: 12px 16px;
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
    color: #FF6B35;
    background: #fafafa;
  }

  .tab.active {
    color: #FF6B35;
    border-bottom-color: #FF6B35;
  }

  .content {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
  }

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
