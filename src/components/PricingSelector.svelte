<script>
  import { createEventDispatcher } from 'svelte';

  export let productId;
  export let plans;

  const dispatch = createEventDispatcher();

  let selectedPlan = plans[0].name;
  let quantity = 1;

  function handleAddToCart() {
    dispatch('addToCart', {
      productId,
      planName: selectedPlan,
      quantity,
    });

    // Reset form
    selectedPlan = plans[0].name;
    quantity = 1;
  }

  function formatPrice(price) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(price);
  }

  $: selectedPlanData = plans.find(p => p.name === selectedPlan);
</script>

<div class="pricing-selector">
  <div class="plan-options">
    {#each plans as plan (plan.name)}
      <label class="plan-option" class:selected={selectedPlan === plan.name}>
        <input
          type="radio"
          name="pricing-plan"
          value={plan.name}
          bind:group={selectedPlan}
        />
        <div class="plan-content">
          <div class="plan-name">{plan.name}</div>
          <div class="plan-quantity">{plan.quantity}</div>
          <div class="plan-price">{formatPrice(plan.price)}</div>
          {#if plan.perUnit !== plan.price}
            <div class="per-unit">${plan.perUnit.toFixed(2)}/unit</div>
          {/if}
          <div class="plan-details">{plan.details}</div>
        </div>
      </label>
    {/each}
  </div>

  {#if selectedPlanData}
    <div class="selected-plan-summary">
      <div class="summary-header">
        <h4>Order Summary</h4>
      </div>
      <div class="summary-details">
        <div class="detail-row">
          <span>Plan:</span>
          <strong>{selectedPlanData.name}</strong>
        </div>
        <div class="detail-row">
          <span>Quantity:</span>
          <input
            type="number"
            min="1"
            max="100"
            bind:value={quantity}
            class="qty-input"
          />
        </div>
        <div class="detail-row total">
          <span>Total:</span>
          <strong>{formatPrice(selectedPlanData.price * quantity)}</strong>
        </div>
      </div>

      <button class="add-to-cart-btn" on:click={handleAddToCart}>
        Add to Cart
      </button>
    </div>
  {/if}
</div>

<style>
  .pricing-selector {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .plan-options {
    display: grid;
    gap: 0.8rem;
  }

  .plan-option {
    position: relative;
    cursor: pointer;
  }

  .plan-option input {
    display: none;
  }

  .plan-option input:checked + .plan-content {
    border-color: #2c5aa0;
    background: #f0f4f8;
  }

  .plan-content {
    padding: 1rem;
    border: 2px solid #ddd;
    border-radius: 0.4rem;
    transition: all 0.2s;
    background: white;
  }

  .plan-option:hover .plan-content {
    border-color: #2c5aa0;
  }

  .plan-name {
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 0.3rem;
    font-size: 0.95rem;
  }

  .plan-quantity {
    font-size: 0.8rem;
    color: #666;
    margin-bottom: 0.3rem;
  }

  .plan-price {
    font-size: 1.2rem;
    font-weight: 700;
    color: #2c5aa0;
    margin-bottom: 0.2rem;
  }

  .per-unit {
    font-size: 0.75rem;
    color: #999;
    margin-bottom: 0.3rem;
  }

  .plan-details {
    font-size: 0.75rem;
    color: #666;
    font-style: italic;
    line-height: 1.3;
  }

  .selected-plan-summary {
    padding: 1.2rem;
    background: #f0f4f8;
    border-radius: 0.4rem;
    border-left: 4px solid #2c5aa0;
  }

  .summary-header h4 {
    margin: 0 0 0.8rem 0;
    font-size: 0.95rem;
    font-weight: 700;
    color: #1a1a1a;
  }

  .summary-details {
    display: flex;
    flex-direction: column;
    gap: 0.8rem;
    margin-bottom: 1rem;
  }

  .detail-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.9rem;
  }

  .detail-row span {
    color: #666;
    font-weight: 500;
  }

  .detail-row strong {
    color: #1a1a1a;
    font-weight: 700;
  }

  .detail-row.total {
    padding-top: 0.8rem;
    border-top: 1px solid #ddd;
    font-size: 1rem;
  }

  .detail-row.total span {
    font-weight: 700;
    color: #1a1a1a;
  }

  .qty-input {
    width: 60px;
    padding: 0.3rem 0.4rem;
    border: 1px solid #ddd;
    border-radius: 0.3rem;
    font-size: 0.9rem;
    text-align: center;
  }

  .add-to-cart-btn {
    width: 100%;
    padding: 0.8rem;
    background: #2c5aa0;
    color: white;
    border: none;
    border-radius: 0.4rem;
    font-size: 0.95rem;
    font-weight: 700;
    cursor: pointer;
    transition: background 0.2s;
  }

  .add-to-cart-btn:hover {
    background: #1e3f6f;
  }

  .add-to-cart-btn:active {
    transform: scale(0.98);
  }

  @media (max-width: 480px) {
    .pricing-selector {
      gap: 1rem;
    }

    .plan-content {
      padding: 0.8rem;
    }

    .plan-price {
      font-size: 1.1rem;
    }

    .selected-plan-summary {
      padding: 1rem;
    }
  }
</style>
