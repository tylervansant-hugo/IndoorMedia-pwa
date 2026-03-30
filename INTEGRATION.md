# Component Integration Guide

Quick setup for integrating the three new Svelte components into your IndoorMedia PWA.

## Files Created

```
pwa/src/components/
├── TestimonialSearch.svelte      (9.4 KB)
├── AdminPanel.svelte             (16 KB)
├── ShippingStatus.svelte         (13.7 KB)
└── README.md                     (8.5 KB)

pwa/src/lib/
└── api.js                        (8.1 KB - data service)

pwa/src/routes/api/
├── testimonials/
│   └── +server.js
├── admin/
│   ├── reps/
│   │   └── +server.js
│   ├── stats/
│   │   └── +server.js
│   └── allocations/
│       └── +server.js
└── shipping/
    └── status/
        └── +server.js
```

## Setup Steps

### 1. Verify Data Files Exist

Components rely on cached data files. Ensure these exist in your workspace:

```bash
ls -la /Users/tylervansant/.openclaw/workspace/data/
  - testimonials_cache.json
  - rep_registry.json
  - prospect_data.json
  - shipping_delivery_report.json
```

If missing, the bot should populate them:

```bash
cd /Users/tylervansant/.openclaw/workspace/scripts
python3 telegram_prospecting_bot.py  # Generates cache files
```

### 2. Create Routes

Add these pages to your SvelteKit app:

**`src/routes/testimonials/+page.svelte`**
```svelte
<script>
  import TestimonialSearch from '$lib/components/TestimonialSearch.svelte';
</script>

<TestimonialSearch />
```

**`src/routes/admin/+page.svelte`**
```svelte
<script>
  import AdminPanel from '$lib/components/AdminPanel.svelte';
</script>

<AdminPanel />
```

**`src/routes/shipping/+page.svelte`**
```svelte
<script>
  import ShippingStatus from '$lib/components/ShippingStatus.svelte';
</script>

<ShippingStatus />
```

### 3. Add Navigation

Update your main layout or nav component:

```svelte
<nav class="main-nav">
  <a href="/testimonials">💬 Testimonials</a>
  <a href="/admin">⚙️ Admin Dashboard</a>
  <a href="/shipping">🚚 Shipping Status</a>
</nav>
```

### 4. Environment Variable

Ensure `WORKSPACE` is set (components default to `/Users/tylervansant/.openclaw/workspace`):

```bash
# In .env or .env.local
WORKSPACE=/Users/tylervansant/.openclaw/workspace
```

## Component Configuration

### TestimonialSearch
- Loads all testimonials from cache
- Performs client-side filtering/search
- Responsive grid: 1 col (mobile) → 2 cols (tablet) → 3 cols (desktop)

### AdminPanel
- Multi-tab interface: Overview, Reps, Allocations, Settings
- Loads rep registry + prospect stats
- Shows performance metrics per rep
- Drill-down to individual rep details

### ShippingStatus
- Real-time shipping data visualization
- Color-coded alerts (red/yellow/green)
- Sortable & filterable store list
- Direct UPS tracking links for in-transit shipments

## API Endpoints

All endpoints return JSON and are served from your SvelteKit app:

```
GET /api/testimonials
  Returns: Array of testimonials with full data

GET /api/admin/reps
  Returns: Array of reps with base stats

GET /api/admin/stats
  Returns: Object mapping rep ID → stats

GET /api/admin/allocations
  Returns: Array of store allocations per rep

GET /api/shipping/status
  Returns: { shipments: [...], summary: {...} }
```

## Data Refresh

Components fetch data on mount. To refresh:

1. **Manual**: User navigates away and back to page
2. **Periodic**: Add polling (e.g., every 5 minutes):

```svelte
<script>
  import { onMount } from 'svelte';
  
  onMount(() => {
    // Refresh every 5 minutes
    const interval = setInterval(() => {
      // Refetch from API
    }, 5 * 60 * 1000);
    
    return () => clearInterval(interval);
  });
</script>
```

3. **Real-time**: Implement WebSocket for shipping status

## Styling

All components use **mobile-first** CSS with no external dependencies:

- No Tailwind, Bootstrap, or Material UI
- Standard CSS in `<style>` blocks
- Responsive grid/flex layouts
- Accessible color contrast (WCAG AA)

To customize colors, update the color values in each component's `<style>` section:

```css
--primary-color: #3498db;
--success-color: #27ae60;
--warning-color: #f39c12;
--critical-color: #e74c3c;
```

## Performance Tips

1. **Lazy-load routes** - Use SvelteKit's route-level code splitting
2. **Cache API responses** - Browser caching for 5-10 minutes
3. **Virtualize long lists** - If >100 testimonials, use virtual scrolling
4. **Optimize images** - If you add brand logos/photos

## Accessibility

Components follow WCAG 2.1 Level AA:

- ✅ Semantic HTML (`<header>`, `<nav>`, `<section>`)
- ✅ Clear focus states on interactive elements
- ✅ Color + text for status (not just emoji)
- ✅ Form labels associated with inputs
- ✅ Keyboard navigation (Tab, Enter, Escape)
- ✅ Sufficient color contrast ratios

## Testing

### Manual Testing
1. Navigate to each page
2. Test filters/search functionality
3. Click deep-links (rep details, tracking links)
4. Test on mobile (use Chrome DevTools device emulation)

### Automated Testing
Add Svelte component tests:

```javascript
// __tests__/TestimonialSearch.test.js
import { render } from '@testing-library/svelte';
import TestimonialSearch from '../TestimonialSearch.svelte';

it('renders testimonial search', () => {
  const { getByText } = render(TestimonialSearch);
  expect(getByText('💬 Testimonials & Social Proof')).toBeTruthy();
});
```

## Troubleshooting

### "Data not loading"
- Check browser Network tab for failed API requests
- Verify `WORKSPACE` env var is set
- Confirm data files exist in `data/` directory

### "Components not rendering"
- Check browser console for errors
- Verify Svelte components are imported correctly
- Ensure SvelteKit routes are created

### "Styling looks weird on mobile"
- Check viewport meta tag: `<meta name="viewport" content="width=device-width, initial-scale=1">`
- Clear browser cache (Cmd+Shift+R)
- Test in Chrome DevTools device emulation

### "Slow performance"
- Check API response times in Network tab
- Reduce data file size (archive old testimonials)
- Enable gzip compression on server

## Deployment

### SvelteKit Static
If deploying as static site:

```bash
npm run build
# Outputs to 'build/' directory
```

API routes won't work statically. Use:
- Separate API server (Node.js, Python, etc.)
- Serverless functions (Vercel, AWS Lambda)
- Headless CMS with REST API

### SvelteKit Adapter
For full dynamic deployment:

```javascript
// svelte.config.js
import adapter from '@sveltejs/adapter-auto';

export default {
  kit: {
    adapter: adapter()
  }
};
```

## Security Notes

- ⚠️ API endpoints expose rep data. Consider adding auth middleware.
- ⚠️ Shipping data may contain PII. Audit access controls.
- ⚠️ Validate all query parameters in API routes.

Example: Add role-based access control (RBAC)

```javascript
// src/routes/api/admin/reps/+server.js
import { error } from '@sveltejs/kit';

export async function GET({ request }) {
  const user = await authenticate(request);
  
  if (user.role !== 'manager') {
    throw error(403, 'Forbidden');
  }
  
  // Return data...
}
```

## Next Steps

1. ✅ Deploy components to your PWA
2. ✅ Test each page thoroughly
3. ✅ Gather user feedback from reps/managers
4. ✅ Add any missing features (charts, exports, etc.)
5. ✅ Set up monitoring/logging for APIs
6. ✅ Document for your team

## Support

For issues or questions:
- Review `/src/components/README.md` for component details
- Check `/src/lib/api.js` for data service functions
- Look at route handlers in `/src/routes/api/` for API structure

---

**Last Updated:** 2026-03-21  
**Components Ready:** ✅ TestimonialSearch, AdminPanel, ShippingStatus  
**API Routes Ready:** ✅ All 5 endpoints implemented  
**Styling:** ✅ Mobile-first, no dependencies  
**Status:** Ready for integration & deployment
