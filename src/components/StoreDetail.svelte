<script>
  import { appState, selectedStore, addToCart } from '../lib/stores.js';
  import { calculatePricingPlans, formatPrice } from '../lib/pricing.js';

  let pricingPlans = {};
  let selectedPlan = 'annualPif';
  let selectedProduct = 'singleAd';
  let quantity = 1;

  // Calculate next install date based on zone install day and cycle
  function getInstallDateDisplay(installDay, cycle) {
    if (!installDay) return '';
    const now = new Date();
    const day = parseInt(installDay);
    
    // Cycle schedule: A/B/C rotate every ~3 months
    // Find next occurrence of this day
    let nextDate = new Date(now.getFullYear(), now.getMonth(), day);
    if (nextDate <= now) {
      nextDate.setMonth(nextDate.getMonth() + 1);
    }
    
    const monthName = nextDate.toLocaleDateString('en-US', { month: 'short' });
    const ordinal = day + (day === 1 || day === 21 || day === 31 ? 'st' : day === 2 || day === 22 ? 'nd' : day === 3 || day === 23 ? 'rd' : 'th');
    return `${ordinal} of each month`;
  }

  $: if ($selectedStore) {
    pricingPlans = calculatePricingPlans(
      $selectedStore.SingleAd,
      $selectedStore.DoubleAd
    );
  }

  function handleAddToCart() {
    const plan = pricingPlans[selectedPlan];
    const price = selectedProduct === 'singleAd' ? plan.singleAd : plan.doubleAd;

    addToCart({
      storeName: $selectedStore.StoreName,
      product: selectedProduct === 'singleAd' ? 'Single Ad' : 'Double Ad',
      planName: plan.name,
      planPeriod: plan.period,
      price,
      quantity,
    });

    alert(`Added to cart: ${quantity}x ${plan.name}`);
  }

  function goBack() {
    appState.set('search');
  }
</script>

{#if $selectedStore}
  <div class="store-detail">
    <div class="detail-header">
      <button class="back-btn" on:click={goBack}>← Back</button>
      <h2>{$selectedStore.StoreName}</h2>
      <div></div>
    </div>

    <div class="detail-content">
      <div class="store-info">
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">Chain</span>
            <span class="info-value">{$selectedStore.GroceryChain}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Address</span>
            <span class="info-value">
              {$selectedStore.Address}
              <br />
              {$selectedStore.City}, {$selectedStore.State} {$selectedStore.PostalCode}
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">Zone</span>
            <span class="info-value">{$selectedStore.ZoneName}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Cases</span>
            <span class="info-value">{$selectedStore['Case Count']}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Cycle</span>
            <span class="info-value">{$selectedStore.Cycle}</span>
          </div>
          {#if $selectedStore.InstallDay}
          <div class="info-item">
            <span class="info-label">In Stores</span>
            <span class="info-value install-date">{getInstallDateDisplay($selectedStore.InstallDay, $selectedStore.Cycle)}</span>
          </div>
          {/if}
        </div>
      </div>

      <div class="pricing-section">
        <h3>💰 Payment Plans</h3>

        <div class="product-selector">
          <label>
            <input type="radio" bind:group={selectedProduct} value="singleAd" />
            Single Ad
          </label>
          <label>
            <input type="radio" bind:group={selectedProduct} value="doubleAd" />
            Double Ad
          </label>
        </div>

        <div class="plans-grid">
          {#each Object.entries(pricingPlans) as [key, plan]}
            <div
              class="plan-card"
              class:selected={selectedPlan === key}
              on:click={() => (selectedPlan = key)}
            >
              <div class="plan-header">
                <h4>{plan.name}</h4>
                {#if plan.isBestDeal}
                  <span class="best-deal">Best Deal</span>
                {/if}
              </div>
              <p class="plan-period">{plan.period}</p>

              <div class="plan-pricing">
                <div class="price-item">
                  <span class="price-label">Single:</span>
                  <span class="price-value">{formatPrice(plan.singleAd)}</span>
                </div>
                <div class="price-item">
                  <span class="price-label">Double:</span>
                  <span class="price-value">{formatPrice(plan.doubleAd)}</span>
                </div>
              </div>

              <div class="plan-total">{formatPrice(selectedProduct === 'singleAd' ? plan.singleAd : plan.doubleAd)}</div>
            </div>
          {/each}
        </div>

        <div class="checkout-section">
          <div class="quantity-selector">
            <label for="qty">Quantity:</label>
            <input
              id="qty"
              type="number"
              min="1"
              max="100"
              bind:value={quantity}
              class="qty-input"
            />
          </div>

          <button class="add-to-cart-btn" on:click={handleAddToCart}>
            🛒 Add to Cart
          </button>
        </div>
      </div>

      <div class="notes-section">
        <h4>📋 Store Details</h4>
        <ul>
          <li>Locations with case counts listed are actively stocked</li>
          <li>Payment plans include all co-op variants</li>
          <li>Annual PIF offers the best pricing</li>
          <li>Review your cart before checkout</li>
        </ul>
      </div>
    </div>
  </div>
{/if}

<style>
  .store-detail {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
  }

  .detail-header {
    padding: 1.5rem;
    background: white;
    border-bottom: 1px solid #e2e8f0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: sticky;
    top: 0;
    z-index: 10;
  }

  .detail-header h2 {
    font-size: 1.4rem;
    color: #1a1a2e;
    margin: 0;
  }

  .back-btn {
    background: transparent;
    border: none;
    color: #1a1a2e;
    font-size: 1rem;
    cursor: pointer;
    padding: 0.5rem;
    font-weight: 600;
  }

  .detail-content {
    flex: 1;
    padding: 1.5rem;
    overflow-y: auto;
    max-width: 900px;
    margin: 0 auto;
    width: 100%;
  }

  .store-info {
    background: white;
    border-radius: 8px;
    padding: 1.5rem;
    margin-bottom: 2rem;
    border-left: 4px solid #e74c3c;
  }

  .info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.5rem;
  }

  .info-item {
    display: flex;
    flex-direction: column;
  }

  .info-label {
    font-weight: 600;
    color: #64748b;
    font-size: 0.85rem;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
  }

  .info-value {
    color: #1a1a2e;
    font-size: 1rem;
  }
  .info-value.install-date {
    color: #CC0000;
    font-weight: 700;
  }

  .pricing-section {
    background: white;
    border-radius: 8px;
    padding: 1.5rem;
    margin-bottom: 2rem;
  }

  .pricing-section h3 {
    margin-top: 0;
    color: #1a1a2e;
    font-size: 1.2rem;
  }

  .product-selector {
    display: flex;
    gap: 2rem;
    margin-bottom: 1.5rem;
  }

  .product-selector label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
    font-weight: 500;
    color: #1a1a2e;
  }

  .product-selector input[type='radio'] {
    cursor: pointer;
    width: 18px;
    height: 18px;
  }

  .plans-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
  }

  .plan-card {
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    padding: 1.25rem;
    cursor: pointer;
    transition: all 0.2s;
    position: relative;
  }

  .plan-card:hover {
    border-color: #e74c3c;
    box-shadow: 0 4px 12px rgba(231, 76, 60, 0.1);
  }

  .plan-card.selected {
    border-color: #e74c3c;
    background: rgba(231, 76, 60, 0.05);
    box-shadow: 0 0 0 3px rgba(231, 76, 60, 0.1);
  }

  .plan-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .plan-header h4 {
    margin: 0;
    color: #1a1a2e;
    font-size: 1rem;
    font-weight: 700;
  }

  .best-deal {
    background: #e74c3c;
    color: white;
    padding: 0.25rem 0.5rem;
    border-radius: 3px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
  }

  .plan-period {
    color: #64748b;
    font-size: 0.85rem;
    margin: 0 0 0.75rem 0;
  }

  .plan-pricing {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-bottom: 1rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #e2e8f0;
  }

  .price-item {
    display: flex;
    justify-content: space-between;
    font-size: 0.9rem;
  }

  .price-label {
    color: #64748b;
  }

  .price-value {
    font-weight: 700;
    color: #1a1a2e;
  }

  .plan-total {
    font-size: 1.2rem;
    font-weight: 700;
    color: #e74c3c;
  }

  .checkout-section {
    display: flex;
    gap: 1rem;
    align-items: flex-end;
    margin-top: 1.5rem;
  }

  .quantity-selector {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .quantity-selector label {
    font-weight: 600;
    color: #1a1a2e;
    font-size: 0.9rem;
  }

  .qty-input {
    padding: 0.5rem;
    border: 2px solid #e2e8f0;
    border-radius: 6px;
    font-size: 1rem;
    width: 80px;
    text-align: center;
  }

  .qty-input:focus {
    outline: none;
    border-color: #e74c3c;
  }

  .add-to-cart-btn {
    flex: 1;
    padding: 0.75rem 1.5rem;
    background: linear-gradient(135deg, #e74c3c 0%, #d63a2a 100%);
    color: white;
    border: none;
    border-radius: 6px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s;
  }

  .add-to-cart-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(231, 76, 60, 0.3);
  }

  .notes-section {
    background: #f5f7fa;
    border-left: 4px solid #5a7fa8;
    padding: 1.5rem;
    border-radius: 8px;
  }

  .notes-section h4 {
    color: #1a1a2e;
    margin-top: 0;
  }

  .notes-section ul {
    margin: 0;
    padding-left: 1.5rem;
    color: #475569;
    line-height: 1.6;
  }

  .notes-section li {
    margin-bottom: 0.5rem;
  }

  @media (max-width: 768px) {
    .detail-header {
      padding: 1rem;
    }

    .detail-header h2 {
      font-size: 1.2rem;
    }

    .detail-content {
      padding: 1rem;
    }

    .plans-grid {
      grid-template-columns: 1fr;
    }

    .checkout-section {
      flex-direction: column;
    }

    .add-to-cart-btn {
      width: 100%;
    }
  }
</style>
