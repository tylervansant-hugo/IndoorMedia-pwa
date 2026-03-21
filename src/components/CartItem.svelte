<script>
  import { createEventDispatcher } from 'svelte';

  export let item;
  export let subtotal;

  const dispatch = createEventDispatcher();

  function handleRemove() {
    dispatch('remove');
  }

  function handleQuantityChange(e) {
    const newQuantity = parseInt(e.target.value) || 1;
    dispatch('updateQuantity', { quantity: newQuantity });
  }

  function formatPrice(price) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(price);
  }

  function formatDate(dateStr) {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: '2-digit',
    });
  }
</script>

<div class="cart-item">
  <div class="item-header">
    <div class="product-info">
      <h3>{item.productName}</h3>
      <p class="plan-name">{item.planName}</p>
      <p class="added-date">Added: {formatDate(item.addedAt)}</p>
    </div>
    <button class="remove-btn" on:click={handleRemove} title="Remove item">
      ✕
    </button>
  </div>

  <div class="item-details">
    <div class="detail-cell">
      <span class="label">Unit Price</span>
      <span class="value">{formatPrice(item.perUnit)}</span>
    </div>

    <div class="detail-cell">
      <span class="label">Quantity</span>
      <input
        type="number"
        min="1"
        max="100"
        value={item.quantity}
        on:change={handleQuantityChange}
        class="qty-input"
      />
    </div>

    <div class="detail-cell subtotal">
      <span class="label">Subtotal</span>
      <span class="value">{formatPrice(subtotal)}</span>
    </div>
  </div>
</div>

<style>
  .cart-item {
    background: white;
    border-radius: 0.4rem;
    overflow: hidden;
    border: 1px solid #e0e0e0;
    transition: all 0.2s;
  }

  .cart-item:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .item-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 1rem;
    background: linear-gradient(135deg, #f9f9f9 0%, #ffffff 100%);
    border-bottom: 1px solid #eee;
  }

  .product-info {
    flex: 1;
  }

  .product-info h3 {
    font-size: 1rem;
    font-weight: 700;
    color: #1a1a1a;
    margin: 0 0 0.3rem 0;
  }

  .plan-name {
    font-size: 0.85rem;
    color: #666;
    margin: 0 0 0.2rem 0;
    font-weight: 500;
  }

  .added-date {
    font-size: 0.75rem;
    color: #999;
    margin: 0;
  }

  .remove-btn {
    background: #ff5252;
    color: white;
    border: none;
    width: 28px;
    height: 28px;
    border-radius: 0.3rem;
    cursor: pointer;
    font-size: 1rem;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.2s;
    flex-shrink: 0;
    margin-left: 0.5rem;
  }

  .remove-btn:hover {
    background: #ff1744;
  }

  .item-details {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 0;
    padding: 0;
  }

  .detail-cell {
    display: flex;
    flex-direction: column;
    padding: 0.8rem 1rem;
    border-right: 1px solid #eee;
  }

  .detail-cell:last-child {
    border-right: none;
  }

  .detail-cell.subtotal {
    background: #f0f4f8;
  }

  .label {
    font-size: 0.7rem;
    color: #999;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
    margin-bottom: 0.3rem;
  }

  .value {
    font-size: 0.95rem;
    font-weight: 700;
    color: #1a1a1a;
  }

  .detail-cell.subtotal .value {
    color: #2c5aa0;
    font-size: 1.1rem;
  }

  .qty-input {
    width: 50px;
    padding: 0.3rem 0.4rem;
    border: 1px solid #ddd;
    border-radius: 0.3rem;
    font-size: 0.9rem;
    text-align: center;
    font-weight: 600;
  }

  .qty-input:focus {
    outline: none;
    border-color: #2c5aa0;
    box-shadow: 0 0 0 2px rgba(44, 90, 160, 0.1);
  }

  @media (max-width: 600px) {
    .item-header {
      flex-direction: column;
      gap: 0.5rem;
    }

    .item-details {
      grid-template-columns: 1fr 1fr;
    }

    .detail-cell:nth-child(3) {
      grid-column: 1 / -1;
    }

    .detail-cell {
      border-right: none;
      border-bottom: 1px solid #eee;
      padding: 0.6rem 0.8rem;
    }

    .detail-cell:last-child {
      border-bottom: none;
    }
  }

  @media (max-width: 400px) {
    .item-header {
      padding: 0.8rem;
    }

    .product-info h3 {
      font-size: 0.9rem;
    }

    .item-details {
      grid-template-columns: 1fr;
    }

    .detail-cell {
      border-right: none;
      border-bottom: 1px solid #eee;
    }

    .detail-cell:last-child {
      border-bottom: none;
    }
  }
</style>
