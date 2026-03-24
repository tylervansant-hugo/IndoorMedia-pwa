<script>
  import { onMount } from 'svelte';

  let cartItems = [];

  onMount(loadCart);

  function loadCart() {
    try {
      cartItems = JSON.parse(localStorage.getItem('indoormedia_cart') || '[]');
    } catch { cartItems = []; }
  }

  function removeItem(index) {
    cartItems.splice(index, 1);
    cartItems = [...cartItems];
    localStorage.setItem('indoormedia_cart', JSON.stringify(cartItems));
  }

  function clearCart() {
    if (confirm('Clear entire cart?')) {
      cartItems = [];
      localStorage.setItem('indoormedia_cart', JSON.stringify([]));
    }
  }

  function exportCSV() {
    if (cartItems.length === 0) return;
    const rows = [
      ['Product', 'Price', 'Details', 'Added'].join(','),
      ...cartItems.map(item =>
        [item.name, item.price, item.details || '', item.addedAt?.split('T')[0] || '']
          .map(c => `"${c}"`).join(',')
      )
    ].join('\n');

    const blob = new Blob([rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `IndoorMedia_Quote_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }
</script>

<div class="cart-container">
  {#if cartItems.length === 0}
    <div class="empty-cart">
      <p class="empty-icon">🛒</p>
      <p>Your cart is empty</p>
      <p class="empty-hint">Add products from the Products tab to build a quote</p>
    </div>
  {:else}
    <div class="cart-header">
      <h2>Quote Builder ({cartItems.length} items)</h2>
      <div class="cart-actions">
        <button class="export-btn" on:click={exportCSV}>📥 Export CSV</button>
        <button class="clear-btn" on:click={clearCart}>🗑️ Clear</button>
      </div>
    </div>

    <div class="cart-items">
      {#each cartItems as item, i}
        <div class="cart-item">
          <div class="item-main">
            <h4>{item.name}</h4>
            <p class="item-price">{item.price}</p>
            {#if item.details}
              <p class="item-details">{item.details}</p>
            {/if}
          </div>
          <button class="remove-btn" on:click={() => removeItem(i)}>✕</button>
        </div>
      {/each}
    </div>

    <div class="cart-footer">
      <p>{cartItems.length} item{cartItems.length > 1 ? 's' : ''} in quote</p>
      <button class="export-btn full" on:click={exportCSV}>📥 Export Quote as CSV</button>
    </div>
  {/if}
</div>

<style>
  .cart-container { max-width: 600px; margin: 0 auto; padding: 20px; }

  .empty-cart { text-align: center; padding: 60px 20px; color: #999; }
  .empty-icon { font-size: 64px; margin: 0 0 16px; }
  .empty-cart p { margin: 8px 0; font-size: 14px; }
  .empty-hint { color: #bbb; font-size: 13px; }

  .cart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
  .cart-header h2 { margin: 0; font-size: 22px; font-weight: 700; color: #333; }
  .cart-actions { display: flex; gap: 8px; }

  .export-btn { background: #CC0000; color: white; border: none; border-radius: 8px; padding: 10px 16px; font-size: 13px; font-weight: 600; cursor: pointer; }
  .export-btn:hover { background: #990000; }
  .export-btn.full { width: 100%; margin-top: 12px; }

  .clear-btn { background: #f5f5f5; color: #666; border: 1px solid #e0e0e0; border-radius: 8px; padding: 10px 16px; font-size: 13px; font-weight: 600; cursor: pointer; }
  .clear-btn:hover { background: #eee; }

  .cart-items { display: flex; flex-direction: column; gap: 12px; }

  .cart-item { background: white; border: 1px solid #e0e0e0; border-radius: 12px; padding: 16px; display: flex; justify-content: space-between; align-items: flex-start; }
  .item-main { flex: 1; }
  .cart-item h4 { margin: 0 0 4px; font-size: 15px; font-weight: 700; color: #333; }
  .item-price { margin: 0 0 4px; font-size: 15px; font-weight: 600; color: #CC0000; }
  .item-details { margin: 0; font-size: 12px; color: #888; }

  .remove-btn { background: none; border: none; color: #ccc; font-size: 20px; cursor: pointer; padding: 0; margin-left: 12px; }
  .remove-btn:hover { color: #CC0000; }

  .cart-footer { margin-top: 20px; padding: 16px; background: #f5f5f5; border-radius: 12px; text-align: center; }
  .cart-footer p { margin: 0; font-size: 14px; color: #666; font-weight: 600; }
</style>
