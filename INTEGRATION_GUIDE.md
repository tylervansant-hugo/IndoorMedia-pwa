# Products + Cart System Integration Guide

## Quick Start

### 1. Add to Your Router
If using SvelteKit or another router:

```svelte
<!-- routes/products/+page.svelte -->
<script>
  import ProductMenu from '../../components/ProductMenu.svelte';
</script>

<ProductMenu />
```

```svelte
<!-- routes/cart/+page.svelte -->
<script>
  import ShoppingCart from '../../components/ShoppingCart.svelte';
</script>

<ShoppingCart />
```

### 2. Simple Client-Side Navigation
If using a simple client component:

```svelte
<script>
  import ProductMenu from './components/ProductMenu.svelte';
  import ShoppingCart from './components/ShoppingCart.svelte';
  
  let currentPage = 'products'; // 'products' | 'cart'
</script>

<svelte:window on:hashchange={() => {
  currentPage = window.location.hash === '#cart' ? 'cart' : 'products';
}} />

{#if currentPage === 'products'}
  <ProductMenu />
{:else}
  <ShoppingCart />
{/if}
```

## Component Hierarchy

```
App
├── ProductMenu
│   ├── ProductCard (×3)
│   │   └── PricingSelector
│   └── Cart Counter (footer)
└── ShoppingCart
    ├── CartItem (×n)
    ├── CartSummary (sidebar)
    ├── Export Modal
    └── Email Share
```

## Data Flow

### Adding Items to Cart
```
ProductCard.svelte
  ↓ (on:addToCart event)
ProductMenu.svelte (aggregates event)
  ↓ (dispatches addToCart detail)
Parent Component (listens to event)
  ↓ (updates localStorage)
cart = [...cart, newItem]
```

### Managing Cart
```
ShoppingCart.svelte (loads from localStorage on mount)
  ↓ (user actions: remove, update qty)
CartItem.svelte (dispatches events)
  ↓ (cart array updates)
ShoppingCart.svelte (re-renders)
  ↓ (persists to localStorage)
localStorage.setItem('indoormedia_cart', JSON.stringify(cart))
```

## API Reference

### ProductMenu Props
None - uses internal state.

### ProductCard Props
- `product`: Object with id, name, icon, description, specs, pricingPlans
- `isSelected`: Boolean - whether card is expanded

### ProductCard Events
- `on:select`: Card header clicked
- `on:addToCart`: Forwarded from PricingSelector

### PricingSelector Props
- `productId`: String - product identifier
- `plans`: Array of pricing plan objects

### PricingSelector Events
- `on:addToCart`: Event detail contains { productId, planName, quantity }

### ShoppingCart Props
None - manages its own state from localStorage.

### CartItem Props
- `item`: Cart item object
- `subtotal`: Calculated price * quantity

### CartItem Events
- `on:remove`: Remove item from cart
- `on:updateQuantity`: Qty changed - event.detail.quantity

### CartSummary Props
- `total`: Number - total cart value
- `itemCount`: Number - number of items in cart

### CartSummary Events
- `on:clearCart`: Clear all items button clicked

## Storage Integration

### Current Implementation
Uses browser `localStorage` with key `indoormedia_cart`.

### Migration to Backend
To persist to a server:

```javascript
// In ProductMenu.svelte - replace localStorage.setItem
async function saveCart(cart) {
  const response = await fetch('/api/cart', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cart),
  });
  return response.json();
}

// In ShoppingCart.svelte - replace localStorage.getItem
async function loadCart() {
  const response = await fetch('/api/cart');
  cartItems = await response.json();
}
```

### With User Authentication
Add user ID to requests:

```javascript
const userId = getUserId(); // from auth system
const response = await fetch(`/api/carts/${userId}`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getToken()}`,
  },
  body: JSON.stringify(cart),
});
```

## Pricing Data Integration

### Current: Hardcoded Pricing
Product pricing is hardcoded in ProductMenu.svelte.

### Option 1: Load from stores.json
```javascript
import storeData from '../data/stores.json';

// Calculate pricing from store data
let products = [
  {
    id: 'register-tape',
    name: 'Register Tape',
    pricingPlans: [
      {
        name: 'Small',
        quantity: '1,000',
        price: calculateFromStores(storeData, 'single'),
      },
      // ...
    ],
  },
];
```

### Option 2: Load from API
```javascript
onMount(async () => {
  const response = await fetch('/api/products');
  products = await response.json();
});
```

## Styling Customization

### Override Colors
Create `src/styles/theme.css`:

```css
:root {
  --primary-color: #2c5aa0;
  --accent-color: #4caf50;
  --danger-color: #ff5252;
  --bg-primary: #ffffff;
  --bg-secondary: #f5f5f5;
  --text-primary: #1a1a1a;
  --text-secondary: #666;
}
```

Then in components:
```svelte
<style>
  .btn {
    background: var(--primary-color);
  }
</style>
```

### Dark Mode
Add media query wrapper:

```css
@media (prefers-color-scheme: dark) {
  :root {
    --bg-primary: #1a1a1a;
    --bg-secondary: #2d2d2d;
    --text-primary: #ffffff;
    --text-secondary: #ccc;
  }
}
```

## Analytics Integration

### Track Product Views
```javascript
// In ProductCard.svelte
function handleSelect() {
  trackEvent('product_viewed', {
    product_id: product.id,
    product_name: product.name,
  });
  dispatch('select');
}
```

### Track Add to Cart
```javascript
// In PricingSelector.svelte
function handleAddToCart() {
  trackEvent('add_to_cart', {
    product_id: productId,
    plan_name: selectedPlan,
    quantity,
    value: selectedPlanData.price * quantity,
  });
  dispatch('addToCart', { productId, planName: selectedPlan, quantity });
}
```

### Track Cart Checkout
```javascript
// In CartSummary.svelte
function handleCheckout() {
  trackEvent('begin_checkout', {
    items: itemCount,
    value: total,
  });
  // proceed to checkout...
}
```

## Form Validation

### Add to PricingSelector
```javascript
function validatePlan() {
  if (!selectedPlan) {
    error = 'Please select a plan';
    return false;
  }
  if (quantity < 1 || quantity > 100) {
    error = 'Quantity must be between 1 and 100';
    return false;
  }
  return true;
}

function handleAddToCart() {
  if (!validatePlan()) return;
  // proceed...
}
```

## Accessibility Enhancements

### Add ARIA Labels
```svelte
<button 
  aria-label="Remove {item.productName} from cart"
  on:click={handleRemove}
>
  ✕
</button>
```

### Add Form Labels
```svelte
<label for="qty-{item.id}">
  Quantity for {item.productName}
</label>
<input id="qty-{item.id}" type="number" bind:value={item.quantity} />
```

### Add Landmarks
```svelte
<nav aria-label="Product categories">
  <ProductMenu />
</nav>

<main aria-label="Shopping cart">
  <ShoppingCart />
</main>
```

## Mobile Optimization

### Test Responsive Design
```javascript
// Test at these breakpoints
const breakpoints = {
  mobile: 375,    // iPhone SE
  tablet: 768,    // iPad
  desktop: 1024,  // Desktop
};
```

### Touch-Friendly Buttons
All buttons already have:
- 44px minimum height (mobile touch target)
- 44px minimum width
- Clear visual feedback on press

### Optimized Inputs
- Number inputs with easy +/- controls
- Large tap targets for radio buttons
- Sticky footer keeps cart visible

## Error Handling

### Add Error Boundary
```svelte
<script>
  let error = null;

  onMount(() => {
    try {
      loadCart();
    } catch (e) {
      error = 'Failed to load cart. Please refresh the page.';
      console.error(e);
    }
  });
</script>

{#if error}
  <div class="error-banner">{error}</div>
{/if}
```

### Fallback Content
```svelte
{#if error}
  <div class="error">
    <p>Something went wrong.</p>
    <button on:click={() => location.reload()}>Reload Page</button>
  </div>
{:else if loading}
  <div class="loading">Loading...</div>
{:else}
  <!-- normal content -->
{/if}
```

## Performance Tips

1. **Lazy Load Components**
   - Use `<svelte:component>` with dynamic imports
   - Load CartPage only when needed

2. **Memoize Calculations**
   - Cache total calculations
   - Use derived stores for totals

3. **Debounce Quantity Input**
   - Don't save on every keystroke
   - Use debounced save on blur

4. **Image Optimization**
   - Replace emoji icons with optimized SVG
   - Compress any product images

5. **Code Splitting**
   - Separate product menu and cart page
   - Load page modules only when routed

## Next Steps

1. **Add Checkout Page** - Implement payment processing
2. **Add User Accounts** - Save carts per user
3. **Add Admin Dashboard** - Manage pricing, inventory
4. **Add Real-Time Sync** - WebSocket for live cart updates
5. **Add Email Notifications** - Confirm orders, track shipments

## Support & Questions

Refer to `PRODUCTS_CART_README.md` for:
- Full component documentation
- Data structure details
- Styling guide
- Testing procedures
