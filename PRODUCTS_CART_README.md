# Products + Shopping Cart System

Mobile-first Svelte component library for IndoorMedia product browsing and shopping cart management.

## Components

### 1. ProductMenu.svelte
Main products landing page with three core IndoorMedia products.

**Features:**
- Product grid layout (responsive 1-column on mobile, 3-column on desktop)
- Product discovery with expandable details
- Live cart counter in sticky footer
- Direct navigation to shopping cart

**Data Structure:**
Each product includes:
- `id`: Unique identifier
- `name`: Product name
- `icon`: Emoji icon for visual identity
- `description`: Short product pitch
- `specs`: Technical specifications as key-value pairs
- `pricingPlans`: Array of pricing tier options

### 2. ProductCard.svelte
Individual product card with collapsible details section.

**Features:**
- Click to expand/collapse product details
- Specifications display with nested lists
- Integrated pricing selector
- Visual feedback for selected state

**Events:**
- `on:select`: Triggered when card is clicked
- `on:addToCart`: Forwarded from PricingSelector

### 3. PricingSelector.svelte
Plan selection and quantity management for adding items to cart.

**Features:**
- Radio button plan selection
- Quantity input with validation (1-100)
- Real-time order summary calculation
- Formatted currency display
- Add to cart button

**Data Flow:**
- Binds to selected plan and quantity
- Dispatches `addToCart` with productId, planName, quantity
- Auto-resets form after successful add

### 4. ShoppingCart.svelte
Complete shopping cart with management and export features.

**Features:**
- Item listing with individual remove buttons
- Real-time quantity management
- Sticky summary sidebar (desktop)
- Export options (JSON, CSV)
- Email share functionality
- Clear cart confirmation

**Storage:**
- Auto-loads cart from localStorage on mount
- Persists changes after every modification
- Graceful fallback for empty cart

### 5. CartItem.svelte
Individual cart item display component.

**Features:**
- Product and plan name display
- Unit price, quantity, subtotal breakdown
- Quick quantity adjustment
- Remove button
- Added date tracking

**Responsive Layout:**
- 3-column grid on desktop (Unit Price, Qty, Subtotal)
- 2-column on tablet
- Stacked on mobile

### 6. CartSummary.svelte
Order summary sidebar with checkout and support info.

**Features:**
- Item count display
- Average price per item
- Order total
- "Proceed to Checkout" button (placeholder)
- Clear cart action
- Support contact info

**Sticky Behavior:**
- Remains visible while scrolling on desktop
- Static positioning on mobile (<768px)

## Data Storage

### localStorage Key
`indoormedia_cart` - Stores array of cart items

### Cart Item Structure
```javascript
{
  id: string,                    // Unique ID: `${productId}-${planName}-${timestamp}`
  productId: string,             // Reference to product
  productName: string,           // Display name
  planName: string,              // Selected pricing plan
  quantity: number,              // Order quantity
  price: number,                 // Total plan price
  perUnit: number,               // Per-unit price
  addedAt: ISO8601 timestamp     // When item was added
}
```

## Styling

### Colors
- **Primary**: #2c5aa0 (IndoorMedia blue)
- **Accent**: #4caf50 (Green for success actions)
- **Danger**: #ff5252 (Red for remove/clear)
- **Background**: Linear gradient from #f5f5f5 to #ffffff
- **Text**: #1a1a1a (dark), #666 (secondary), #999 (tertiary)

### Typography
- System font stack: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto
- Sizes: 0.75rem - 1.8rem
- Weights: 500 (regular), 600 (bold), 700 (extra bold)

### Responsive Breakpoints
- Mobile: < 480px
- Tablet: 480px - 768px
- Desktop: > 768px

## Usage

### In Parent Component
```svelte
<script>
  import ProductMenu from './components/ProductMenu.svelte';
  import ShoppingCart from './components/ShoppingCart.svelte';
  
  let currentPage = 'products'; // or 'cart'
</script>

{#if currentPage === 'products'}
  <ProductMenu />
{:else}
  <ShoppingCart />
{/if}
```

### Routing Integration
For SPA routing, use a router library:
```
/ → ProductMenu
/cart → ShoppingCart
/checkout → (future implementation)
```

## Export Features

### JSON Export
- Machine-readable format
- Includes cart items and summary
- Useful for system integration
- Filename: `indoormedia-cart-YYYY-MM-DD.json`

### CSV Export
- Excel/Google Sheets compatible
- Columns: Product, Plan, Unit Price, Quantity, Subtotal, Date
- Easy import to spreadsheet tools
- Filename: `indoormedia-cart-YYYY-MM-DD.csv`

### Email Share
- Generates mailto: link with cart summary
- Lists all items with totals
- Ready for discussion with sales rep

## Pricing Plans

### Register Tape
1. **Small Bundle**: 1,000 units @ $2.55/unit = $2,550
2. **Standard**: 5,000 units @ $0.76/unit = $3,800
3. **Large Fleet**: 10,000+ units @ $0.51/unit = $5,100

### Cartvertising
1. **Single Ad**: $4,050/4-week campaign
2. **Double Ad**: $5,670/4-week (dual creative rotation)
3. **Multi-Store**: 5+ stores @ $4,500/store (20% volume discount)

### DigitalBoost
1. **Single Screen**: $7,500/campaign (1 screen)
2. **Checkout Zone**: $18,000/campaign (3-5 screens @ $4,500 each)
3. **Network Package**: $35,000+ (10+ screens @ $3,500 each)

## Future Enhancements

1. **Volume Discounts**
   - Auto-apply discounts based on total cart value
   - Display discount notifications

2. **Payment Integration**
   - Stripe/Square checkout
   - Invoice generation
   - Payment plans

3. **Store Location Integration**
   - Select stores from stores.json
   - Calculate pricing per store
   - Territory-based quotes

4. **Prospect/Contact Binding**
   - Link cart to prospect records
   - Auto-populate contact info
   - Sales rep assignment

5. **Analytics**
   - Track product interest
   - Cart abandonment metrics
   - Popular plan combinations

6. **Advanced Filtering**
   - Filter by geography
   - Filter by store chain
   - Filter by budget

## Testing

### LocalStorage Testing
```javascript
// Clear cart
localStorage.removeItem('indoormedia_cart')

// Check cart
JSON.parse(localStorage.getItem('indoormedia_cart'))

// Simulate data
localStorage.setItem('indoormedia_cart', JSON.stringify([...]))
```

### Mobile Testing
Use browser dev tools to test viewport sizes:
- iPhone SE: 375px wide
- iPhone 12: 390px wide
- iPad: 768px wide
- Desktop: 1024px+

## Accessibility

- Semantic HTML structure
- ARIA labels on interactive elements
- Keyboard navigation support (Tab, Enter, Escape)
- Color contrast ratios meet WCAG AA standards
- Form inputs properly labeled
- Images/icons have alt text or aria-label

## Performance

- Components are lightweight and modular
- No external dependencies (pure Svelte)
- LocalStorage for instant data persistence
- Event delegation for list items
- CSS Grid for modern layout

## Browser Support

- Chrome/Edge: 90+
- Firefox: 88+
- Safari: 14+
- Mobile: iOS 14+, Android 10+

## Integration Notes

1. **Icon Implementation**: Currently using emoji. Replace with SVG icons if needed.
2. **Pricing Data**: Source from stores.json or API. Current implementation hardcoded for demo.
3. **Currency**: Fixed to USD. Make configurable if needed.
4. **Locale**: Uses en-US for date/currency formatting.
5. **Timezone**: Timestamps in browser's local timezone via `new Date()`.

## Support

For questions or issues:
- Check component props and events
- Review data structure in cart localStorage
- Test in browser dev tools
- Verify responsive design at various breakpoints
