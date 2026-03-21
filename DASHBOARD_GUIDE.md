# IndoorMedia Dashboard Implementation Guide

Complete guide to the three-component dashboard system for IndoorMedia's register tape division.

## Quick Start

### 1. Install & Run
```bash
cd /Users/tylervansant/.openclaw/workspace/pwa
npm install
npm run dev:full        # Runs both dev server and backend
```

Then open:
- **Dashboard:** http://localhost:5173?view=dashboard
- **Customers:** http://localhost:5173?view=customers  
- **Audit:** http://localhost:5173?view=audit

### 2. Production Build
```bash
npm run build           # Creates optimized build
npm start              # Runs Express server with compiled assets
```

## Architecture

```
pwa/
├── src/
│   ├── components/
│   │   ├── PerformanceDashboard.svelte   (📊 Metrics & Leaderboard)
│   │   ├── MyCustomers.svelte             (👥 Prospect Management)
│   │   ├── AuditStore.svelte              (🏪 Inventory Tracking)
│   │   └── README.md                      (Component Documentation)
│   ├── lib/
│   │   └── api.js                         (Mock API & Utilities)
│   ├── App.svelte                         (Main Navigation)
│   ├── main.js
│   └── app.css
├── server.js                              (Express Backend)
├── package.json
└── vite.config.js
```

## Component Details

### PerformanceDashboard (📊)

**URL:** `?view=dashboard`

**Real-Time Metrics:**
- Rep searches (prospects found)
- Saved prospects (active pipeline)
- Closed deals (completed sales)
- Team leaderboard (ranked by monthly performance)

**Data Flow:**
```
GET /api/dashboard/metrics
└─ Returns all reps with their metrics from prospect_data.json
```

**Integration with Telegram Bot:**
The dashboard reads from the same data file as the Telegram bot:
- `../data/prospect_data.json` - Prospect lists per rep
- `../data/rep_registry.json` - Rep information

**Example Metric Display:**
```
Tyler Van Sant (Manager)
├─ 48 searches this month
├─ 12 saved prospects
├─ 3 closed deals
└─ Monthly Score: 92/100
```

### MyCustomers (👥)

**URL:** `?view=customers`

**Prospect Statuses:**
- 👀 **Interested** - Initial contact made, showed interest
- 📞 **Follow-up** - Needs follow-up call or email
- 📄 **Proposal** - Proposal sent, awaiting response
- ✅ **Closed** - Deal completed

**Features:**
1. **Search & Filter**
   - Quick filter by name, address, phone
   - Status tabs for pipeline views
   - Shows count per status

2. **Prospect Details Modal**
   - Full contact information
   - Score and interaction history
   - Notes timeline
   - Last contact date

3. **Quick Actions**
   - 📞 Call - Log a call attempt
   - ✉️ Email - Log an email sent
   - 📝 Note - Add timestamped note

**Data Model:**
```javascript
{
  id: "db9193785c0c",
  name: "Autotek International",
  address: "2430 SE Umatilla St, Portland",
  phone: "(503) 454-6141",
  email: "contact@autotek.com",
  contact_name: "John Smith",
  score: 68.8,              // Likelihood of sale (0-100)
  status: "closed",         // interested|follow-up|proposal|closed
  saved_date: "2026-03-03T15:38:19.820599",
  last_contacted: "2026-03-15T10:00:00",
  visit_count: 3,
  notes: [
    { text: "...", date: "2026-03-15T10:00:00" }
  ]
}
```

### AuditStore (🏪)

**URL:** `?view=audit`

**Purpose:** Calculate when register tape inventory will run out and alert Tyler if critical.

**Three-Step Workflow:**

**Step 1: Select Store**
- Shows available stores with location
- Stores defined in server.js (can be moved to database)

**Step 2: Enter Inventory**
```
Store: PDX-001 (Portland Main)

Required:
└─ Next Delivery Date: MM/DD/YYYY

Optional:
├─ Starting Cases: 20 (typical)
├─ Current Rolls on Hand: [user input]
├─ Units per Roll: 4
├─ Sales Cycle: 3/5/7 day
```

**Step 3: View Results**
```
Status: SUFFICIENT ✅

Metrics:
├─ Days Until Runout: 10.5
├─ Days Until Delivery: 5
├─ Daily Usage: 2.5 rolls
└─ Current Inventory: 25 rolls

Decision:
└─ Email alert if INSUFFICIENT status
```

**Status Logic:**
```javascript
if (days_until_runout <= days_until_delivery) {
  status = "INSUFFICIENT"   // 🚨 Email Tyler immediately
} else if (days_until_runout < days_until_delivery + 2) {
  status = "WARNING"        // ⚠️ Monitor closely
} else {
  status = "SUFFICIENT"     // ✅ Normal
}
```

**Email Trigger:**
- INSUFFICIENT status activates red alert button
- Sends email to `tyler.vansant@indoormedia.com`
- Subject: `CRITICAL: Store {num} Low Inventory Alert`
- Includes full audit details

## Data Integration

### Current Setup (Mock Data)
Components use mock data for development/demo:
- Prospects from `../data/prospect_data.json` (real data)
- Reps from `../data/rep_registry.json` (real data)
- Stores hardcoded in `server.js`

### To Connect Real Data

**1. Update Dashboard Endpoint** (`server.js`):
```javascript
app.get('/api/dashboard/metrics', async (req, res) => {
  // Replace with your database query
  const reps = await database.query(`
    SELECT id, name, base_location, role,
           COUNT(*) as searches,
           SUM(CASE WHEN status='closed' THEN 1 ELSE 0 END) as closed_deals
    FROM reps
    LEFT JOIN prospects ON reps.id = prospects.rep_id
    GROUP BY reps.id
  `);
  
  res.json({ reps });
});
```

**2. Update Customers Endpoint:**
```javascript
app.get('/api/customers/prospects', async (req, res) => {
  const prospects = await database.query(`
    SELECT * FROM prospects 
    WHERE rep_id = ? 
    ORDER BY saved_date DESC
  `, [req.query.rep_id || currentUserId]);
  
  res.json({ prospects });
});
```

**3. Update Audit Endpoints:**
```javascript
app.get('/api/audit/stores', async (req, res) => {
  const stores = await database.query(`
    SELECT number, name, location, manager_id FROM stores
    WHERE region IN (?, ?)
  `, [userRegion1, userRegion2]);
  
  res.json({ stores });
});

app.post('/api/audit/email', async (req, res) => {
  const { store_num, audit_result } = req.body;
  
  // Send actual email
  await sendEmail({
    to: 'tyler.vansant@indoormedia.com',
    subject: `CRITICAL: Store ${store_num} Low Inventory`,
    body: formatAuditReport(audit_result)
  });
  
  res.json({ success: true, email_sent: true });
});
```

## Mobile Optimization

All components are **mobile-first**:

### Responsive Breakpoints
- **Mobile** (< 640px) - Full-width cards, stacked modals
- **Tablet** (640-1024px) - 2-column grids, side-by-side layout
- **Desktop** (> 1024px) - Full 3-4 column grids, rich sidebar

### Touch-Friendly Features
- 44px minimum touch targets
- Large status badges on cards
- Bottom sheet modals (swipe to close)
- Simplified navigation on small screens
- Single-column data displays

### PWA Capabilities
To make this a full PWA:

1. **Add Service Worker** (already have workbox-window installed):
```javascript
// src/main.js
import { Workbox } from 'workbox-window';

if ('serviceWorker' in navigator) {
  const wb = new Workbox('/sw.js');
  wb.register();
}
```

2. **Create manifest.json:**
```json
{
  "name": "IndoorMedia Dashboard",
  "short_name": "Dashboard",
  "icons": [
    { "src": "/logo-192.png", "sizes": "192x192", "type": "image/png" }
  ],
  "theme_color": "#667eea",
  "background_color": "#ffffff",
  "display": "standalone"
}
```

3. **Enable offline mode** - Cache API responses, sync when online

## Performance Tips

### 1. Optimize Dashboard Loading
```javascript
// Add pagination to rep list
const pageSize = 50;
const page = req.query.page || 1;
const offset = (page - 1) * pageSize;
```

### 2. Cache Metrics
```javascript
// Cache for 5 minutes
app.get('/api/dashboard/metrics', (req, res) => {
  res.set('Cache-Control', 'public, max-age=300');
  // ... send data
});
```

### 3. Lazy Load Prospects
```javascript
// Use intersection observer for virtual scrolling
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      loadMoreProspects();
    }
  });
});
```

### 4. Compress API Responses
```javascript
import compression from 'compression';
app.use(compression());
```

## Security Considerations

### 1. Authentication
Add user authentication (not included in current build):
```javascript
app.use('/api/*', authenticate); // Middleware to verify user

app.get('/api/dashboard/metrics', (req, res) => {
  // Only return metrics for authenticated user's team
  const reps = await db.getRepsForUser(req.user.id);
  res.json({ reps });
});
```

### 2. Authorization
```javascript
app.post('/api/customers/action', (req, res) => {
  const prospect = await db.getProspect(req.body.prospect_id);
  
  // Only allow rep to modify their own prospects
  if (prospect.rep_id !== req.user.id && req.user.role !== 'manager') {
    return res.status(403).json({ error: 'Unauthorized' });
  }
  
  // Process action...
});
```

### 3. Input Validation
```javascript
app.post('/api/audit/calculate', (req, res) => {
  const { current_rolls, delivery_date } = req.body;
  
  // Validate inputs
  if (!Number.isInteger(parseInt(current_rolls))) {
    return res.status(400).json({ error: 'Invalid rolls value' });
  }
  
  if (new Date(delivery_date) <= new Date()) {
    return res.status(400).json({ error: 'Delivery date must be in future' });
  }
  
  // ... process
});
```

## Deployment

### Local Development
```bash
npm run dev:full        # Dev mode with hot reload
```

### Production
```bash
# Build optimized bundle
npm run build

# Start production server
npm start

# Server listens on PORT (default 3001)
# Access at http://localhost:3001
```

### Docker Deployment
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3001
CMD ["npm", "start"]
```

### Environment Variables
```bash
# .env
PORT=3001
NODE_ENV=production
DATABASE_URL=your_db_connection
SMTP_HOST=mail.indoormedia.com
SMTP_USER=dashboard@indoormedia.com
SMTP_PASS=your_password
TYLER_EMAIL=tyler.vansant@indoormedia.com
```

## Testing

### Manual Testing Checklist
- [ ] Dashboard loads all reps and metrics
- [ ] Customers filter by status works
- [ ] Adding note to prospect saves
- [ ] Audit calculates runout correctly
- [ ] Email alert triggers on INSUFFICIENT
- [ ] Mobile layout responsive (test at 375px, 768px)
- [ ] All buttons are clickable on mobile (44px min)

### Example Test Cases

**Dashboard:**
1. Load dashboard, verify 4 reps appear
2. Toggle monthly/yearly, verify scores update
3. Click leaderboard rows, verify no errors
4. Check pipeline has 15+ prospects total

**Customers:**
1. Search for "Papa" - should find Papa Murphy's
2. Filter by "Closed" - should show 1 prospect
3. Click prospect card, open detail modal
4. Add note, verify timestamp appears
5. Try "Call" action, verify toast notification

**Audit:**
1. Select store PDX-001
2. Enter delivery date 5 days from now
3. Enter 20 rolls, verify calculation
4. Change to 8 rolls, verify INSUFFICIENT alert
5. Click email button, check console for send confirmation

## Troubleshooting

### Issue: "Cannot find module 'express'"
**Solution:**
```bash
npm install express cors
```

### Issue: API returns 404
**Solution:**
1. Verify server is running: `npm run dev:server`
2. Check data files exist: `ls ../data/*.json`
3. Confirm port in server matches client requests

### Issue: Components not rendering
**Solution:**
1. Open browser DevTools (F12)
2. Check Console for errors
3. Clear cache: Ctrl+Shift+Delete
4. Restart Vite: `npm run dev`

### Issue: Mobile layout broken
**Solution:**
1. Verify viewport meta tag in `index.html`:
```html
<meta name="viewport" content="width=device-width, initial-scale=1.0">
```
2. Check media queries in component styles
3. Test in browser DevTools Device Emulation

## FAQ

**Q: How often do metrics update?**
A: Currently on-demand (load page to refresh). Add WebSocket for real-time.

**Q: Can I export reports to PDF?**
A: Not in current build. Use a library like `pdfkit` to add PDF export.

**Q: How many prospects can the dashboard handle?**
A: Currently tested with 100+ prospects. Use virtual scrolling for 1000+.

**Q: Can I customize colors?**
A: Yes, search for `#667eea` (primary purple) in component styles and replace.

**Q: Does it work offline?**
A: Not yet. Add Service Worker caching to enable offline mode.

**Q: How do I add more users?**
A: Update `rep_registry.json` or database, then add authentication middleware.

## Next Steps

1. **Connect to Real Database** - Replace mock data in server.js
2. **Add Authentication** - Implement user login/session management
3. **Enable Email Alerts** - Configure SMTP for critical inventory alerts
4. **Real-Time Updates** - Add WebSocket for live metric refresh
5. **Mobile App** - Package as iOS/Android app using Capacitor
6. **Analytics** - Track user interactions and conversion funnels

## Support

For issues or improvements:
1. Check the component README: `src/components/README.md`
2. Review error logs in browser console
3. Test with mock data first, then real data
4. Open an issue with reproduction steps

---

**Dashboard Version:** 1.0.0  
**Last Updated:** March 21, 2026  
**Maintained by:** IndoorMedia Tech
