<script>
  import { cart, removeFromCart, clearCart, error, setError } from '../lib/stores.js';

  let cartItems = [];
  cart.subscribe(items => {
    cartItems = items;
  });

  function handleRemove(id, type) {
    removeFromCart(id, type);
    setError('Item removed');
  }

  function handleExport() {
    if (cartItems.length === 0) {
      setError('Cart is empty');
      return;
    }

    // Create CSV data
    const csv = [
      ['Store #', 'Name', 'City', 'Ad Type', 'Plan', 'Price'].join(','),
      ...cartItems.map(item =>
        [
          item.storeNumber || '',
          item.name,
          item.city || '',
          item.adType || '',
          item.planLabel || '',
          item.price || ''
        ].map(cell => `"${cell}"`).join(',')
      )
    ].join('\n');

    // Trigger download
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `cart_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);

    setError('Cart exported!');
  }

  function handleClear() {
    if (confirm('Clear entire cart?')) {
      clearCart();
      setError('Cart cleared');
    }
  }
</script>

<div class="cart-container">
  {#if cartItems.length === 0}
    <div class="empty-cart">
      <div class="empty-icon">🛒</div>
      <p>Your cart is empty</p>
      <p class="empty-hint">Add stores, prospects, or testimonials from the other tabs</p>
    </div>
  {:else}
    <div class="cart-summary">
      <h2>Cart ({cartItems.length} items)</h2>
      <div class="cart-actions">
        <button class="action-btn export" on:click={handleExport}>
          📥 Export
        </button>
        <button class="action-btn clear" on:click={handleClear}>
          🗑️ Clear
        </button>
      </div>
    </div>

    <div class="cart-items">
      {#each cartItems as item (item.id + item.type)}
        <div class="cart-item">
          <div class="item-header">
            <span class="item-type">
              {#if item.type === 'store'}
                🏪
              {:else if item.type === 'prospect'}
                👥
              {:else}
                ⭐
              {/if}
              {item.name}
            </span>
            <button
              class="remove-btn"
              on:click={() => handleRemove(item.id, item.type)}
              title="Remove item"
            >
              ✕
            </button>
          </div>

          {#if item.type === 'store'}
            <p class="item-detail">
              {item.storeNumber || ''} — {item.city}, {item.chain}
            </p>
            {#if item.adType}
              <p class="item-detail">{item.adType} • {item.planLabel || ''}</p>
            {/if}
            {#if item.price}
              <p class="item-price">${item.price}</p>
            {/if}
          {:else if item.type === 'prospect'}
            <p class="item-detail">
              {item.address || item.business || ''}
            </p>
          {/if}

          {#if item.quantity > 1}
            <p class="item-quantity">Qty: {item.quantity}</p>
          {/if}
        </div>
      {/each}
    </div>

    <div class="cart-footer">
      <p class="item-count">Total items: <strong>{cartItems.length}</strong></p>
      <p class="hint">Export your cart as CSV to use in Excel or other tools</p>
    </div>
  {/if}
</div>

<style>
  .cart-container {
    max-width: 900px;
    margin: 0 auto;
  }

  .empty-cart {
    text-align: center;
    padding: 60px 20px;
    color: #999;
  }

  .empty-icon {
    font-size: 64px;
    margin-bottom: 16px;
  }

  .empty-cart p {
    margin: 8px 0;
    font-size: 14px;
  }

  .empty-hint {
    color: #bbb;
  }

  .cart-summary {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding: 16px;
    background: white;
    border-radius: 12px;
    border: 1px solid #e0e0e0;
    box-shadow: none;
  }

  .cart-summary h2 {
    margin: 0;
    font-size: 18px;
    color: #333;
    font-weight: 700;
  }

  .cart-actions {
    display: flex;
    gap: 8px;
  }

  .action-btn {
    padding: 8px 14px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.2s;
  }

  .action-btn.export {
    background: #CC0000;
    color: white;
  }

  .action-btn.export:hover {
    background: #990000;
  }

  .action-btn.clear {
    background: #f5f5f5;
    color: #666;
  }

  .action-btn.clear:hover {
    background: #eee;
    color: #333;
  }

  .cart-items {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 20px;
  }

  .cart-item {
    background: white;
    border-radius: 8px;
    padding: 14px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }

  .item-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .item-type {
    font-size: 16px;
    font-weight: 600;
    color: #1a1a1a;
    flex: 1;
  }

  .remove-btn {
    background: none;
    border: none;
    color: #999;
    cursor: pointer;
    font-size: 20px;
    padding: 0;
    margin-left: 12px;
    transition: color 0.2s;
  }

  .remove-btn:hover {
    color: #c33;
  }

  .item-detail {
    margin: 4px 0 0 0;
    font-size: 13px;
    color: #666;
  }

  .item-quantity {
    margin: 6px 0 0 0;
    font-size: 12px;
    color: #999;
    font-weight: 500;
  }

  .cart-footer {
    background: white;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    text-align: center;
  }

  .item-count {
    margin: 0 0 8px 0;
    font-size: 14px;
    color: #333;
  }

  .hint {
    margin: 0;
    font-size: 12px;
    color: #999;
  }

  @media (max-width: 640px) {
    .cart-summary {
      flex-direction: column;
      align-items: flex-start;
      gap: 12px;
    }
  }
</style>
