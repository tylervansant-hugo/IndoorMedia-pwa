# IndoorMedia Dashboard Components

Three core Svelte components for performance tracking, customer management, and inventory auditing.

## Components

### 1. PerformanceDashboard.svelte 📊

**Purpose:** Real-time rep metrics and team leaderboard

**Features:**
- **Key Metrics Cards** - Displays total searches, saved prospects, closed deals, and team size
- **Sales Pipeline Status** - Visual breakdown of prospects in each stage (Interested → Follow-up → Proposal → Closed)
- **Team Leaderboard** - Ranked view of reps with individual metrics
- **Timeframe Toggle** - Switch between monthly and yearly performance views
- **Mobile-First Design** - Responsive grid layouts that adapt to screen size

**Data Source:** `/api/dashboard/metrics`

**Key Metrics Displayed:**
- Individual searches per rep
- Number of saved prospects
- Closed deals count
- Location/base territory
- Monthly and yearly performance scores
- Pipeline stage distribution

**API Response Structure:**
```json
{
  "reps": [
    {
      "id": "8548368719",
      "name": "Tyler Van Sant",
      "base_location": "Ridgefield, WA",
      "searches": 48,
      "saved_prospects": 12,
      "closed_deals": 3,
      "monthly_score": 92,
      "yearly_score": 87
    }
  ]
}
```

### 2. MyCustomers.svelte 👥

**Purpose:** Manage saved prospects and customer pipeline

**Features:**
- **Search Functionality** - Filter prospects by name, address, or phone
- **Status Filtering** - Quick tabs for Interested, Follow-up, Proposal, Closed
- **Prospect Cards** - Quick preview with key info and status badge
- **Detailed Modal** - Full prospect information with contact details
- **Quick Actions** - Call, Email, Add Note buttons
- **Notes Management** - Add and view timestamped notes
- **Real-time Updates** - Status tracking and last contact info

**Data Source:** `/api/customers/prospects`

**Status Badges:**
- 👀 **Interested** (Orange) - Initial interest shown
- 📞 **Follow-up** (Blue) - Needs follow-up contact
- 📄 **Proposal** (Purple) - Proposal sent, awaiting response
- ✅ **Closed** (Green) - Deal closed/completed

**Prospect Properties:**
```json
{
  "id": "db9193785c0c",
  "name": "Autotek International",
  "address": "2430 SE Umatilla St, Portland",
  "phone": "(503) 454-6141",
  "email": "contact@autotek.com",
  "contact_name": "John Smith",
  "score": 68.8,
  "status": "closed",
  "saved_date": "2026-03-03T15:38:19.820599",
  "last_contacted": "2026-03-15T10:00:00",
  "visit_count": 3,
  "notes": [
    {
      "text": "Successfully closed deal on March 15",
      "date": "2026-03-15T10:00:00"
    }
  ]
}
```

**API Endpoints:**
- `GET /api/customers/prospects` - Get all prospects
- `POST /api/customers/note` - Add note to prospect
- `POST /api/customers/action` - Perform quick action (call/email)

### 3. AuditStore.svelte 🏪

**Purpose:** Track inventory levels and calculate days until runout

**Features:**
- **Store Selection** - Choose from available store locations
- **Inventory Input** - Log current rolls, delivery dates, and cycle info
- **Runout Calculation** - Automatic calculation of days until inventory runs out
- **Status Alerts** - Visual indicators for SUFFICIENT/WARNING/INSUFFICIENT stock
- **Critical Alerts** - Email notification to Tyler if stock is critical
- **Mobile Optimized** - Step-by-step form on mobile devices

**Audit Workflow:**
1. **Select Store** - Choose store from available locations
2. **Enter Inventory** - Input:
   - Next delivery date
   - Starting cases on shelf
   - Current rolls on hand
   - Units per roll
   - Sales cycle (3/5/7 day)
3. **View Results** - See:
   - Days until runout
   - Days until delivery
   - Status (SUFFICIENT/WARNING/INSUFFICIENT)
   - Recommendation and optional email alert

**Status Definitions:**
- 🟢 **SUFFICIENT** - Inventory covers delivery cycle
- 🟡 **WARNING** - Tight inventory, monitor closely
- 🔴 **INSUFFICIENT** - Runout before delivery, immediate action needed

**Store Model:**
```json
{
  "number": "PDX-001",
  "name": "Portland Main",
  "location": "Portland, OR",
  "manager": "Tyler Van Sant"
}
```

**Audit Result:**
```json
{
  "status": "SUFFICIENT|WARNING|INSUFFICIENT",
  "message": "Description of current status",
  "total_rolls": 25,
  "total_units": 100,
  "daily_usage": 2.5,
  "days_until_runout": 10,
  "days_until_delivery": 5,
  "store_num": "PDX-001",
  "email_sent": false
}
```

**API Endpoints:**
- `GET /api/audit/stores` - Get available stores
- `POST /api/audit/calculate` - Calculate runout based on inventory
- `POST /api/audit/email` - Send critical alert email

## Installation & Setup

### Prerequisites
- Node.js v16+
- npm or yarn

### Install Dependencies
```bash
cd pwa
npm install
```

### Development Server
```bash
# Run Vite dev server (components)
npm run dev

# Run Express backend (in another terminal)
npm run dev:server

# Or run both together
npm run dev:full
```

### Production Build
```bash
npm run build
npm start
```

Server runs on `http://localhost:3001` by default.

## Data Integration

### Current Data Sources
- **Prospects:** `../data/prospect_data.json`
- **Reps:** `../data/rep_registry.json`
- **Stores:** Hardcoded in server (can be moved to database)

### Connecting to Real Data

The server (`server.js`) loads data from prospect_data.json and rep_registry.json. To integrate with your database:

1. **Dashboard metrics** - Update the `/api/dashboard/metrics` endpoint to query your database
2. **Customer prospects** - Modify `/api/customers/prospects` to fetch from your prospect storage
3. **Audit stores** - Update `/api/audit/stores` to load from your store management system

Example modification:
```javascript
app.get('/api/dashboard/metrics', async (req, res) => {
  // Replace file loading with database query
  const reps = await db.getReps(); // Your database call
  res.json({ reps });
});
```

## Mobile-First Design

All components are designed mobile-first with responsive breakpoints at:
- **640px** - Tablet transitions
- **768px** - Large tablet/small desktop
- **1024px** - Desktop layouts

Key mobile optimizations:
- Stacked layouts on small screens
- Touch-friendly button sizes (min 44px)
- Simplified navigation (collapsed tabs)
- Gesture-friendly modals (swipe to close)
- Optimized data display (cards vs tables)

## Real-Time Updates

Currently using mock data with simulated delays. To implement real-time updates:

1. **WebSocket Connection:**
```javascript
// In component onMount
const ws = new WebSocket('ws://localhost:3001/ws');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Update component state
};
```

2. **Server-Sent Events (SSE):**
```javascript
const es = new EventSource('/api/stream/metrics');
es.onmessage = (event) => {
  // Update dashboard with new metrics
};
```

3. **Polling** (fallback):
```javascript
setInterval(async () => {
  const data = await fetch('/api/dashboard/metrics').then(r => r.json());
  // Update component state
}, 30000); // Every 30 seconds
```

## Styling

- **Colors** - Purple gradient (#667eea → #764ba2) for primary actions
- **Shadows** - Subtle shadows for depth (0 2px 8px rgba(0,0,0,0.1))
- **Spacing** - 8px base unit system
- **Typography** - System fonts for performance
- **Animations** - Smooth 0.3s transitions, no jarring effects

## Accessibility

- Semantic HTML structure
- ARIA labels for interactive elements
- Keyboard navigation support (Tab, Enter, Escape)
- Color contrast ratios meet WCAG AA standards
- Focus visible states on all interactive elements

## Performance Tips

1. **Lazy Load Components** - Use dynamic imports for route-based splitting
2. **Optimize Re-renders** - Use Svelte stores for shared state
3. **Image Optimization** - Use SVG icons instead of images
4. **API Caching** - Cache dashboard metrics for 5 minutes
5. **Virtual Scrolling** - For long prospect lists (>100 items)

## Troubleshooting

### Components Not Loading
- Check browser console for errors
- Verify all dependencies installed: `npm install`
- Clear node_modules: `rm -rf node_modules && npm install`

### API Errors
- Ensure server is running: `npm run dev:server`
- Check that data files exist in `../data/`
- Verify CORS is enabled (should be automatic with Express CORS middleware)

### Mobile Layout Issues
- Test with browser DevTools device emulation
- Check that viewport meta tag is in index.html
- Ensure CSS media queries are correct

## Future Enhancements

1. **Real-Time Sync** - WebSocket updates for live metrics
2. **Export to PDF** - Generate audit reports
3. **Email Integration** - Direct email from dashboard
4. **Chart Library** - Add Chart.js for trend visualizations
5. **Offline Support** - Service Worker caching for PWA
6. **Dark Mode** - Theme toggle for night viewing
7. **Role-Based Access** - Different views for managers vs reps
8. **Analytics** - Track user interactions and conversion funnels

## License

© 2026 IndoorMedia. All rights reserved.
