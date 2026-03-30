<script>
  import { createEventDispatcher } from 'svelte';
  import PricingSelector from './PricingSelector.svelte';

  export let product;
  export let isSelected = false;

  const dispatch = createEventDispatcher();

  function handleSelect() {
    dispatch('select');
  }

  function handleAddToCart(event) {
    dispatch('addToCart', event.detail);
  }
</script>

<div class="card" class:selected={isSelected}>
  <div class="card-header" on:click={handleSelect}>
    <div class="icon">{product.icon}</div>
    <div class="title-section">
      <h2>{product.name}</h2>
      <p class="description">{product.description}</p>
    </div>
    <div class="expand-icon">
      {#if isSelected}
        <span>▼</span>
      {:else}
        <span>▶</span>
      {/if}
    </div>
  </div>

  {#if isSelected}
    <div class="card-details">
      <div class="specs">
        <h3>Product Specifications</h3>
        <ul>
          {#each Object.entries(product.specs) as [key, value]}
            <li>
              <strong>{key.replace(/_/g, ' ')}:</strong>
              {#if Array.isArray(value)}
                <ul class="nested">
                  {#each value as item}
                    <li>{item}</li>
                  {/each}
                </ul>
              {:else}
                {value}
              {/if}
            </li>
          {/each}
        </ul>
      </div>

      <div class="pricing">
        <h3>Pricing Plans</h3>
        <PricingSelector
          productId={product.id}
          plans={product.pricingPlans}
          on:addToCart={handleAddToCart}
        />
      </div>
    </div>
  {/if}
</div>

<style>
  .card {
    background: white;
    border-radius: 0.6rem;
    overflow: hidden;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
  }

  .card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  .card.selected {
    box-shadow: 0 4px 16px rgba(44, 90, 160, 0.25);
    border: 2px solid #2c5aa0;
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1.2rem;
    cursor: pointer;
    background: linear-gradient(135deg, #f9f9f9 0%, #ffffff 100%);
    border-bottom: 1px solid #eee;
  }

  .card-header:hover {
    background: linear-gradient(135deg, #f0f0f0 0%, #f9f9f9 100%);
  }

  .icon {
    font-size: 2.5rem;
    flex-shrink: 0;
  }

  .title-section {
    flex: 1;
  }

  .card-header h2 {
    font-size: 1.2rem;
    font-weight: 700;
    color: #1a1a1a;
    margin: 0 0 0.3rem 0;
  }

  .description {
    font-size: 0.85rem;
    color: #666;
    margin: 0;
    line-height: 1.3;
  }

  .expand-icon {
    font-size: 1rem;
    color: #2c5aa0;
    flex-shrink: 0;
    transition: transform 0.3s;
  }

  .card.selected .expand-icon {
    color: #2c5aa0;
  }

  .card-details {
    padding: 1.5rem;
    background: #fafafa;
    border-top: 1px solid #eee;
  }

  .specs h3,
  .pricing h3 {
    font-size: 1rem;
    font-weight: 700;
    color: #1a1a1a;
    margin: 0 0 1rem 0;
  }

  .specs {
    margin-bottom: 1.5rem;
  }

  .specs ul {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  .specs li {
    font-size: 0.9rem;
    color: #333;
    padding: 0.5rem 0;
    line-height: 1.5;
  }

  .specs strong {
    color: #2c5aa0;
    font-weight: 600;
  }

  .specs .nested {
    list-style: disc;
    padding-left: 1.5rem;
    margin: 0.5rem 0 0 0;
  }

  .specs .nested li {
    padding: 0.2rem 0;
  }

  @media (max-width: 480px) {
    .card-header {
      gap: 0.8rem;
      padding: 1rem;
    }

    .icon {
      font-size: 2rem;
    }

    .card-header h2 {
      font-size: 1rem;
    }

    .card-details {
      padding: 1rem;
    }
  }
</style>
