<script>
  import { onMount } from 'svelte';
  import CartItem from './CartItem.svelte';
  import CartSummary from './CartSummary.svelte';

  let cartItems = [];
  let showExportOptions = false;

  onMount(() => {
    loadCart();
  });

  function loadCart() {
    const savedCart = localStorage.getItem('indoormedia_cart');
    if (savedCart) {
      try {
        cartItems = JSON.parse(savedCart);
      } catch (e) {
        cartItems = [];
      }
    }
  }

  function removeItem(itemId) {
    cartItems = cartItems.filter(item => item.id !== itemId);
    saveCart();
  }

  function updateQuantity(itemId, newQuantity) {
    const item = cartItems.find(i => i.id === itemId);
    if (item) {
      item.quantity = Math.max(1, newQuantity);
      cartItems = cartItems;
      saveCart();
    }
  }

  function saveCart() {
    localStorage.setItem('indoormedia_cart', JSON.stringify(cartItems));
  }

  function clearCart() {
    if (confirm('Are you sure you want to clear your entire cart?')) {
      cartItems = [];
      localStorage.removeItem('indoormedia_cart');
    }
  }

  function exportAsJSON() {
    const dataStr = JSON.stringify(cartItems, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    downloadFile(dataBlob, `indoormedia-cart-${new Date().toISOString().split('T')[0]}.json`);
    showExportOptions = false;
  }

  function exportAsCSV() {
    let csv = 'Product,Plan,Unit Price,Quantity,Subtotal,Added Date\n';
    cartItems.forEach(item => {
      const subtotal = item.price * item.quantity;
      const date = new Date(item.addedAt).toLocaleDateString();
      csv += `"${item.productName}","${item.planName}","$${item.perUnit.toFixed(2)}",${item.quantity},"$${subtotal.toFixed(2)}","${date}"\n`;
    });
    const dataBlob = new Blob([csv], { type: 'text/csv' });
    downloadFile(dataBlob, `indoormedia-cart-${new Date().toISOString().split('T')[0]}.csv`);
    showExportOptions = false;
  }

  function downloadFile(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  function shareCart() {
    const subject = 'IndoorMedia Cart - Advertising Campaign Quote';
    const body = encodeURIComponent(
      `Hi,\n\nHere's my IndoorMedia advertising campaign quote:\n\n${cartItems
        .map(
          item =>
            `${item.productName} - ${item.planName}\nQuantity: ${item.quantity}\nTotal: $${(item.price * item.quantity).toFixed(2)}`
        )
        .join('\n\n')}\n\nTotal: $${calculateTotal().toFixed(2)}`
    );
    window.location.href = `mailto:?subject=${subject}&body=${body}`;
  }

  function calculateTotal() {
    return cartItems.reduce((sum, item) => sum + item.price * item.quantity, 0);
  }

  function calculateSubtotal(item) {
    return item.price * item.quantity;
  }
</script>

<div class="shopping-cart">
  <div class="cart-header">
    <h1>Shopping Cart</h1>
    {#if cartItems.length > 0}
      <span class="item-count">{cartItems.length} items</span>
    {/if}
  </div>

  {#if cartItems.length === 0}
    <div class="empty-cart">
      <div class="empty-icon">🛒</div>
      <h2>Your cart is empty</h2>
      <p>Browse our products and add items to your campaign cart.</p>
      <a href="/" class="continue-shopping">Continue Shopping</a>
    </div>
  {:else}
    <div class="cart-content">
      <div class="items-section">
        <h2>Cart Items</h2>
        <div class="items-list">
          {#each cartItems as item (item.id)}
            <CartItem
              {item}
              subtotal={calculateSubtotal(item)}
              on:remove={() => removeItem(item.id)}
              on:updateQuantity={(e) => updateQuantity(item.id, e.detail.quantity)}
            />
          {/each}
        </div>
      </div>

      <CartSummary
        total={calculateTotal()}
        itemCount={cartItems.length}
        on:clearCart={clearCart}
      />
    </div>

    <div class="actions-section">
      <button class="action-btn export-btn" on:click={() => (showExportOptions = !showExportOptions)}>
        ↓ Export Cart
      </button>

      <button class="action-btn share-btn" on:click={shareCart}>
        📧 Share via Email
      </button>

      <a href="/" class="action-btn continue-btn">
        ← Continue Shopping
      </a>
    </div>

    {#if showExportOptions}
      <div class="export-modal">
        <div class="export-content">
          <h3>Export Cart As</h3>
          <button class="export-format-btn json-btn" on:click={exportAsJSON}>
            📄 JSON Format
            <span class="description">Machine-readable data</span>
          </button>
          <button class="export-format-btn csv-btn" on:click={exportAsCSV}>
            📊 CSV Format
            <span class="description">Excel compatible</span>
          </button>
          <button class="export-format-btn cancel-btn" on:click={() => (showExportOptions = false)}>
            Cancel
          </button>
        </div>
      </div>
    {/if}
  {/if}
</div>

<style>
  .shopping-cart {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    background: linear-gradient(135deg, #f5f5f5 0%, #ffffff 100%);
    padding: 1rem;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
      Ubuntu, Cantarell, sans-serif;
  }

  .cart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
    padding: 1rem;
  }

  .cart-header h1 {
    font-size: 1.8rem;
    font-weight: 700;
    color: #1a1a1a;
    margin: 0;
  }

  .item-count {
    font-size: 0.9rem;
    background: #e3f2fd;
    color: #2c5aa0;
    padding: 0.4rem 0.8rem;
    border-radius: 1rem;
    font-weight: 600;
  }

  .empty-cart {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 2rem;
  }

  .empty-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
  }

  .empty-cart h2 {
    font-size: 1.5rem;
    color: #1a1a1a;
    margin: 0 0 0.5rem 0;
  }

  .empty-cart p {
    color: #666;
    margin: 0 0 1.5rem 0;
    font-size: 0.95rem;
  }

  .continue-shopping {
    display: inline-block;
    background: #2c5aa0;
    color: white;
    padding: 0.8rem 1.5rem;
    border-radius: 0.4rem;
    text-decoration: none;
    font-weight: 600;
    transition: background 0.2s;
  }

  .continue-shopping:hover {
    background: #1e3f6f;
  }

  .cart-content {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1.5rem;
    flex: 1;
    margin-bottom: 1.5rem;
  }

  @media (min-width: 768px) {
    .cart-content {
      grid-template-columns: 1fr 350px;
    }
  }

  .items-section h2 {
    font-size: 1.1rem;
    font-weight: 700;
    color: #1a1a1a;
    margin: 0 0 1rem 0;
  }

  .items-list {
    display: flex;
    flex-direction: column;
    gap: 0.8rem;
  }

  .actions-section {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 0.8rem;
    margin-top: 1rem;
  }

  @media (max-width: 600px) {
    .actions-section {
      grid-template-columns: 1fr;
    }
  }

  .action-btn {
    padding: 0.8rem;
    border: none;
    border-radius: 0.4rem;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    text-align: center;
    transition: all 0.2s;
  }

  .export-btn {
    background: #f5f5f5;
    color: #1a1a1a;
    border: 1px solid #ddd;
  }

  .export-btn:hover {
    background: #e8e8e8;
  }

  .share-btn {
    background: #4caf50;
    color: white;
  }

  .share-btn:hover {
    background: #45a049;
  }

  .continue-btn {
    background: #2c5aa0;
    color: white;
  }

  .continue-btn:hover {
    background: #1e3f6f;
  }

  .export-modal {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
    z-index: 100;
  }

  .export-content {
    background: white;
    border-radius: 0.6rem;
    padding: 1.5rem;
    max-width: 400px;
    width: 100%;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  }

  .export-content h3 {
    margin: 0 0 1rem 0;
    font-size: 1.1rem;
    color: #1a1a1a;
  }

  .export-format-btn {
    display: block;
    width: 100%;
    padding: 1rem;
    margin-bottom: 0.8rem;
    border: 1px solid #ddd;
    background: white;
    border-radius: 0.4rem;
    cursor: pointer;
    text-align: left;
    transition: all 0.2s;
  }

  .export-format-btn:hover {
    border-color: #2c5aa0;
    background: #f0f4f8;
  }

  .json-btn {
    color: #2c5aa0;
  }

  .csv-btn {
    color: #4caf50;
  }

  .cancel-btn {
    color: #999;
  }

  .description {
    display: block;
    font-size: 0.75rem;
    color: #999;
    margin-top: 0.3rem;
    font-weight: normal;
  }

  @media (max-width: 480px) {
    .cart-header {
      flex-direction: column;
      text-align: center;
      gap: 0.5rem;
    }

    .cart-header h1 {
      font-size: 1.5rem;
    }
  }
</style>
