<script>
  import Products from './Products.svelte';
  import { user } from '../lib/stores.js';

  // Present tab wraps Products with the presentation-focused UI
  // All pricing, tiers, videos, and product details come from Products.svelte
</script>

<div class="present-container">
  <Products />
</div>

<style>
  .present-container { padding: 0; }
</style>
