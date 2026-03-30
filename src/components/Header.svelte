<script>
  import { appState, currentUser, cartCount } from '../lib/stores.js';
  import { persistSession } from '../lib/stores.js';

  function logout() {
    currentUser.set(null);
    persistSession(null);
  }
</script>

<header class="header">
  <div class="header-content">
    <div class="logo-section" on:click={() => appState.set('home')}>
      <div class="logo">📺</div>
      <h1 class="title">IndoorMedia</h1>
    </div>

    <div class="user-section">
      <span class="user-name">{$currentUser?.display_name}</span>
      <button class="cart-btn" on:click={() => appState.set('cart')}>
        🛒 <span class="cart-count">{$cartCount}</span>
      </button>
      <button class="logout-btn" on:click={logout}>Logout</button>
    </div>
  </div>
</header>

<style>
  .header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-bottom: 3px solid #e74c3c;
    padding: 0;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
    position: sticky;
    top: 0;
    z-index: 100;
  }

  .header-content {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1rem 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .logo-section {
    display: flex;
    align-items: center;
    gap: 1rem;
    cursor: pointer;
    transition: opacity 0.2s;
  }

  .logo-section:hover {
    opacity: 0.8;
  }

  .logo {
    font-size: 2rem;
  }

  .title {
    font-size: 1.5rem;
    color: white;
    font-weight: 700;
    margin: 0;
  }

  .user-section {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .user-name {
    color: #e8ecf1;
    font-weight: 500;
    font-size: 0.95rem;
  }

  .cart-btn {
    background: #e74c3c;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
    font-size: 0.9rem;
    position: relative;
    transition: all 0.2s;
  }

  .cart-btn:hover {
    background: #d63a2a;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(231, 76, 60, 0.3);
  }

  .cart-count {
    background: #16213e;
    color: #e74c3c;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-weight: 700;
    margin-left: 0.5rem;
    min-width: 20px;
    text-align: center;
  }

  .logout-btn {
    background: transparent;
    color: #e8ecf1;
    border: 1px solid #e8ecf1;
    padding: 0.5rem 1rem;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
    font-size: 0.9rem;
    transition: all 0.2s;
  }

  .logout-btn:hover {
    background: #e8ecf1;
    color: #1a1a2e;
  }

  @media (max-width: 640px) {
    .header-content {
      padding: 0.75rem 1rem;
      gap: 0.75rem;
    }

    .title {
      font-size: 1.2rem;
    }

    .logo {
      font-size: 1.5rem;
    }

    .user-name {
      display: none;
    }

    .logout-btn {
      padding: 0.4rem 0.8rem;
      font-size: 0.8rem;
    }
  }
</style>
