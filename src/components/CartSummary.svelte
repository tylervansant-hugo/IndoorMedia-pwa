<script>
  import { createEventDispatcher } from 'svelte';

  export let total;
  export let itemCount;

  const dispatch = createEventDispatcher();

  function handleClearCart() {
    dispatch('clearCart');
  }

  function formatPrice(price) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(price);
  }

  // Calculate average per item
  function getAveragePerItem() {
    return itemCount > 0 ? total / itemCount : 0;
  }
</script>

<div class="cart-summary">
  <div class="summary-card">
    <h2>Summary</h2>

    <div class="summary-row">
      <span>Items:</span>
      <strong>{itemCount}</strong>
    </div>

    <div class="summary-row">
      <span>Avg. per item:</span>
      <span>{formatPrice(getAveragePerItem())}</span>
    </div>

    <div class="divider"></div>

    <div class="summary-row total">
      <span>Total:</span>
      <strong>{formatPrice(total)}</strong>
    </div>

    <button class="checkout-btn" on:click={() => alert('Checkout coming soon!')}>
      📋 Proceed to Checkout
    </button>

    <button class="secondary-btn" on:click={handleClearCart}>
      🗑️ Clear Cart
    </button>

    <div class="info-box">
      <p>
        <strong>Need help?</strong>
        <br />
        Contact your IndoorMedia representative for bulk pricing and custom solutions.
      </p>
    </div>
  </div>
</div>

<style>
  .cart-summary {
    position: sticky;
    top: 1rem;
  }

  .summary-card {
    background: white;
    border-radius: 0.6rem;
    padding: 1.5rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    border: 1px solid #e0e0e0;
  }

  .summary-card h2 {
    font-size: 1.1rem;
    font-weight: 700;
    color: #1a1a1a;
    margin: 0 0 1rem 0;
  }

  .summary-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.6rem 0;
    font-size: 0.9rem;
  }

  .summary-row span:first-child {
    color: #666;
    font-weight: 500;
  }

  .summary-row strong,
  .summary-row span:last-child {
    color: #1a1a1a;
    font-weight: 600;
  }

  .summary-row.total {
    font-size: 1.1rem;
    padding: 0.8rem 0;
  }

  .summary-row.total span:first-child {
    font-weight: 700;
    color: #1a1a1a;
  }

  .summary-row.total strong {
    font-size: 1.2rem;
    color: #2c5aa0;
  }

  .divider {
    height: 1px;
    background: #e0e0e0;
    margin: 0.8rem 0;
  }

  .checkout-btn {
    width: 100%;
    padding: 1rem;
    background: #4caf50;
    color: white;
    border: none;
    border-radius: 0.4rem;
    font-size: 0.95rem;
    font-weight: 700;
    cursor: pointer;
    margin-top: 1rem;
    transition: background 0.2s;
  }

  .checkout-btn:hover {
    background: #45a049;
  }

  .secondary-btn {
    width: 100%;
    padding: 0.8rem;
    background: #f5f5f5;
    color: #ff5252;
    border: 1px solid #ddd;
    border-radius: 0.4rem;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    margin-top: 0.5rem;
    transition: all 0.2s;
  }

  .secondary-btn:hover {
    background: #efefef;
    border-color: #ff5252;
  }

  .info-box {
    background: #f0f4f8;
    border-left: 3px solid #2c5aa0;
    padding: 0.8rem;
    border-radius: 0.3rem;
    margin-top: 1rem;
    font-size: 0.8rem;
    line-height: 1.4;
  }

  .info-box p {
    margin: 0;
    color: #333;
  }

  .info-box strong {
    color: #2c5aa0;
  }

  @media (max-width: 768px) {
    .cart-summary {
      position: static;
      margin-top: 1.5rem;
    }

    .summary-card {
      padding: 1.2rem;
    }
  }

  @media (max-width: 480px) {
    .summary-card {
      padding: 1rem;
    }

    .summary-card h2 {
      font-size: 1rem;
    }

    .summary-row {
      font-size: 0.85rem;
    }

    .checkout-btn {
      padding: 0.8rem;
      font-size: 0.9rem;
    }
  }
</style>
