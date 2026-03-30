# PWA Feature Checklist - vs Telegram Bot
**Testing Store: FME07Z-0236**
**Date: March 22, 2026**

## 🏪 STORE SEARCH

### Search Methods
- [ ] Search by store number (FME07Z-0236) — Should find exact store
- [ ] Search by city (Portland) — Should list all stores in city
- [ ] Search by chain (Fred Meyer) — Should list all Fred Meyer stores
- [ ] Search by address — Should find stores on that street
- [ ] Find Nearby — Should find nearest store to rep's location

### Store Display
- [ ] Store number displayed
- [ ] Store name displayed
- [ ] Address displayed
- [ ] City, State displayed
- [ ] Grocery chain displayed
- [ ] Case count displayed
- [ ] Cycle (A/B/C) displayed

### Pricing Display
- [ ] Single Ad pricing shown
- [ ] Double Ad pricing shown
- [ ] All 4 payment plans shown:
  - [ ] Monthly (base + $125) ÷ 12
  - [ ] 3-month (10% off + $125) ÷ 3
  - [ ] 6-month (7.5% off + $125) ÷ 6
  - [ ] Paid-in-Full (15% off, one payment)
- [ ] Standard pricing (with $1200 pad) shown first
- [ ] Co-Op pricing available (unlock button)
- [ ] Accurate math for FME07Z-0236

### Store Actions
- [ ] Add to cart (Single Ad option)
- [ ] Add to cart (Double Ad option)
- [ ] Find nearby prospects from this store
- [ ] View nearby testimonials
- [ ] Audit this store

---

## 🎯 PROSPECTS

### Search Flow
- [ ] "Near Me" finds nearest grocery store to rep
- [ ] Shows store name + distance in miles
- [ ] Category selection shows all 9 categories
- [ ] Subcategory selection shows all subcategories
- [ ] Search returns nearby businesses (within 5 miles)

### Prospect Card Display
- [ ] Business name
- [ ] Full address
- [ ] Distance in miles
- [ ] Google rating (e.g., 4.5 stars)
- [ ] Review count (e.g., "127 reviews")
- [ ] Likelihood score (0-100%)
- [ ] Open/Closed badge (green/red)
- [ ] Open hours (if available)

### Prospect Actions (Expandable)
- [ ] 📞 Call button (tel: link)
- [ ] 🌐 Website button (http link)
- [ ] 💾 Save prospect (to database)
- [ ] 📝 Notes (add/edit prospect notes)
- [ ] 📅 Calendar (create Google Calendar event)
- [ ] 📧 Email (draft personalized email)
- [ ] 📍 Maps (Google Maps link)
- [ ] 🗺️ MapPoint (IndoorMedia MapPoint link)

### Saved Prospects
- [ ] Database stores saved prospects
- [ ] Status tracking (New → Contacted → Proposal → Closed)
- [ ] Notes persisted with timestamps
- [ ] Can search saved prospects
- [ ] Can filter by status
- [ ] Can delete prospect

### Advertising Signals
- [ ] Greet Magazine detection (if on Greet, show badge)
- [ ] Facebook Ads detection (if running ads, show badge)
- [ ] Boost likelihood score if advertising signals found

---

## 📦 PRODUCTS

### Product Listing
- [ ] Register Tape (📜)
- [ ] Cartvertising (🛒)
- [ ] Connection (🔌) - WiFi splash pages
- [ ] Digital Hub (🖥️) - In-store kiosks
- [ ] Digital Boost (📱) - Digital displays
- [ ] Find Local (📍) - Geo-targeted mobile
- [ ] Loyalty Boost (💳) - Loyalty programs

### Product Detail View
- [ ] Description displayed
- [ ] Benefits listed (4-5 per product)
- [ ] 📊 View Presentation link (Google Slides)
- [ ] 🎥 Watch Explainer Video link (YouTube)
- [ ] NO PRICING DISPLAYED
- [ ] ROI Calculator link

---

## 🛒 CART

### Cart Functionality
- [ ] Add stores with ad type selection (Single/Double)
- [ ] Add stores with payment plan selection
- [ ] Show per-item pricing (ad type + plan + final price)
- [ ] Calculate total correctly
- [ ] Remove items
- [ ] Clear all
- [ ] Export to CSV with all details

### CSV Export Contains
- [ ] Store number
- [ ] Store name
- [ ] Chain name
- [ ] Address
- [ ] Ad type (Single/Double)
- [ ] Payment plan (Monthly/3-mo/6-mo/PIF)
- [ ] Price per installment (if applicable)
- [ ] Total price
- [ ] Quantity

---

## ⚙️ TOOLS

### ROI Calculator
- [ ] Shows store pre-selected (from store search)
- [ ] Adjustable sliders:
  - [ ] Monthly redemptions (default 30)
  - [ ] Avg ticket ($, default $50)
  - [ ] Coupon value ($, default $10)
  - [ ] COGS % (default 35%)
- [ ] Real-time calculation:
  - [ ] Monthly revenue
  - [ ] Monthly profit
  - [ ] Monthly ad cost
  - [ ] Monthly net
  - [ ] ROI %
- [ ] All 4 payment plans shown with prices
- [ ] Link back to store

### Email Templates
- [ ] 5 template types available:
  - [ ] Initial Appointment
  - [ ] ROI/Value Focused
  - [ ] Follow-up
  - [ ] Re-engagement
  - [ ] Limited Time
- [ ] Category-specific social proof
- [ ] Auto-fills business name
- [ ] Auto-fills category
- [ ] mailto: link to send

### Testimonials
- [ ] Keyword search (finds testimonials)
- [ ] Category filter
- [ ] Location filter (nearby testimonials from store)
- [ ] 500+ real testimonials
- [ ] Links to IndoorMedia testimonials site

### Audit Store
- [ ] Select store from dropdown
- [ ] Enter current inventory level
- [ ] Calculate days until runout
- [ ] Email alert to Tyler if low stock
- [ ] Show last delivery date
- [ ] Track UPS/shipping if in transit

### Counter Sign Generator
- [ ] Select store chain
- [ ] Upload business card image
- [ ] Upload ad proof image
- [ ] Enter landing page URL
- [ ] Generate QR code for URL
- [ ] Choose sign style (4 options)
- [ ] Choose sign size (3 options)
- [ ] Live preview
- [ ] Download PNG

### Notepad
- [ ] Create field notes
- [ ] Persistent storage
- [ ] Date/time stamps
- [ ] Edit notes
- [ ] Delete notes

### Quick Links
- [ ] MapPoint (external link)
- [ ] Coupons (external link)
- [ ] Google Drive (external link)
- [ ] Sales Portal (external link)
- [ ] Testimonials (external link)
- [ ] All working external links

---

## 📊 DASHBOARD

### Rep Metrics
- [ ] Total prospects
- [ ] Prospects interested
- [ ] Prospects contacted
- [ ] Prospects closed
- [ ] Win rate %

### Monthly Leaderboard
- [ ] Top reps by revenue
- [ ] Current month shown
- [ ] Previous months clickable
- [ ] Shows: Rank, Name, Revenue, %, Count, Avg Deal

### Pipeline Visualization
- [ ] Shows prospect distribution:
  - [ ] New (count)
  - [ ] Contacted (count)
  - [ ] Proposal (count)
  - [ ] Closed (count)

---

## 🔐 AUTHENTICATION

- [ ] Login dropdown shows all 18 reps
- [ ] Rep names only (no locations, no stars)
- [ ] Session persists
- [ ] Logout works
- [ ] Wrong rep selection prevented

---

## 🎨 UI/UX

### Theme
- [ ] Light mode works perfectly
- [ ] Dark mode works perfectly
- [ ] Toggle button in header
- [ ] Preference persisted to localStorage
- [ ] All components respect theme

### Responsive Design
- [ ] iPhone (portrait) optimized
- [ ] iPhone (landscape) optimized
- [ ] iPad (portrait) optimized
- [ ] iPad (landscape) optimized
- [ ] Android phone optimized
- [ ] Android tablet optimized

### Colors
- [ ] Red primary color (#CC0000)
- [ ] Dark red hover (#990000)
- [ ] IndoorMedia logo in header
- [ ] Professional, clean design

### Navigation
- [ ] 6-tab layout (Stores, Prospects, Products, Tools, Stats, Cart)
- [ ] Tabs responsive on mobile
- [ ] Back buttons work correctly
- [ ] Home button returns to main menu

---

## TESTING NOTES

**Test Store: FME07Z-0236**
- Chain: Fred Meyer
- City: Unclear (need to verify in stores.json)
- GPS: Need to verify coordinates

**Expected Results:**
- Should find store instantly by number
- Should show accurate pricing for this store
- Should find prospects near this store's location
- Should calculate ROI correctly for this store

---

## PRIORITY FIXES NEEDED

1. [ ] Store not found error (use default store or search tips)
2. [ ] Missing business data fields
3. [ ] Prospect search not returning results
4. [ ] Email template personalization
5. [ ] Google Calendar event creation
6. [ ] Audit store email alerts
7. [ ] Greet Magazine detection
8. [ ] Facebook Ads detection
9. [ ] UPS tracking link in Audit
10. [ ] CSV export formatting

