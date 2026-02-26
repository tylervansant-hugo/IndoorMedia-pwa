# Prospect Pipeline Integration

## Overview

Complete integration between prospect discovery, b2bappointments, and mapping for closing deals.

**Version:** v1.0 (Feb 25, 2026)

---

## The Workflow

```
1. Find Prospects
   ↓ @IndoorMediaProspectBot
   ↓ Query: FME07Z-0236 → Top 10 prospects

2. Qualify & Save
   ↓ [📁 Save to b2b] button
   ↓ Auto-creates contact in b2bappointments
   ↓ City/Store Number folder structure

3. Analyze (Optional)
   ↓ [📊 Analyze] button
   ↓ Opens indoormedia.com/local-listing-management
   ↓ Shows listing health, review gaps, etc.

4. Call & Close
   ↓ Use b2bappointments lead generation tool
   ↓ Call prospects, track status in app

5. Map & Contract
   ↓ [✅ Booked] button when appointment confirmed
   ↓ Bot auto-finds nearby stores
   ↓ Shows 5-store bundle with pricing
   ↓ Opens Mappoint for contract entry
```

---

## Components

### 1. Prospect Bot (`scripts/telegram_prospecting_bot.py`)

**Purpose:** Find high-potential prospects near each store

**Usage:**
```
Send store number: FME07Z-0236
```

**Output:**
- Top 10 prospects ranked 0-100
- Distance, ratings, advertising signals
- Action buttons: [📁 Save] [📊 Analyze] [✅ Booked]

**Integrations:**
- Pulls from Google Places API
- Checks Greet Magazine for advertising
- Uses store database (612 stores)

---

### 2. b2bappointments Automation (`scripts/b2bappointments_automation.py`)

**Purpose:** Auto-create and manage contacts in b2bappointments.net

**Functions:**
- `login()` — Handles b2b login (uses .env.local creds)
- `create_contact(city, store_number, business_name, phone, email, likelihood_score, category)` — Creates contact in City/Store Number folder
- `contact_exists(city, store_number, business_name)` — Checks if already exists
- `update_contact_status(city, store_number, business_name, status)` — Updates status (Contacted, Interested, Appointment Booked, etc.)

**Usage:**
```python
from b2bappointments_automation import B2BAutomation

automation = B2BAutomation()
await automation.launch_browser()

# Create contact
await automation.create_contact(
    city="Klamath Falls",
    store_number="FME07Z-0236",
    business_name="Joe's Pizza",
    phone="541-555-0123",
    email="joe@joespizza.com",
    likelihood_score=85,
    category="Restaurant"
)

# Update status when called
await automation.update_contact_status(
    city="Klamath Falls",
    store_number="FME07Z-0236",
    business_name="Joe's Pizza",
    status="Contacted"
)

await automation.close_browser()
```

**Features:**
- Uses Playwright for reliable web automation
- Persistent session caching to avoid re-login
- Graceful error handling
- Folder auto-creation
- Duplicate detection

**Technology:**
- Playwright (headless Chrome)
- Async/await for non-blocking operations
- Session cache in `data/b2b_session_cache.json`

---

### 3. Nearby Stores Finder (`scripts/nearby_stores_finder.py`)

**Purpose:** When prospect books appointment, find nearby stores + pricing

**Functions:**
- `find_nearby_stores(lat, lon, max_distance, limit)` — Find stores within distance
- `generate_recommendation_bundle(nearby_stores, ad_type)` — Calculate bundle pricing
- `format_for_telegram(business_name, nearby_stores, bundle)` — Format for Telegram

**Usage:**
```python
from nearby_stores_finder import NearbyStoresFinder

finder = NearbyStoresFinder()

# Find stores near prospect location
nearby = finder.find_nearby_stores(
    prospect_lat=45.6872,
    prospect_lon=-122.6151,
    max_distance=3.0,
    limit=10
)

# Generate pricing bundle for top 5
bundle = finder.generate_recommendation_bundle(nearby, ad_type="single")

# Format for Telegram
msg = finder.format_for_telegram(
    business_name="Joe's Pizza",
    nearby_stores=nearby,
    bundle=bundle
)

print(msg)
```

**Output:**
```
🗺️ Nearby Store Opportunities
Joe's Pizza

📍 Top Recommended Stores (5 stores within 3 miles)
1. Fred Meyer - Klamath Falls
   Distance: 1.2mi
   Single: $2,400 | Double: $3,200
...

💰 Total Package Pricing (5-Store Bundle)
Monthly: $1,200/mo × 12 = $14,400
3-Month: $1,000 × 3 = $3,000 (10% off)
6-Month: $900 × 6 = $5,400 (7.5% off)
Paid-in-Full: $8,500 (15% off)

🎯 Ready to enter contracts? Open Mappoint to add this business to your map.
[🗺️ Open Mappoint](https://sales.indoormedia.com/Mappoint)
```

---

## Configuration

### Environment Variables (`.env.local`)

```bash
# b2bappointments.net credentials
B2B_USERNAME=Tyler.vansant@indoormedia.com
B2B_PASSWORD=Zoey2026!

# sales.IndoorMedia.com credentials (for future integration)
SALES_USERNAME=Tyler.VanSant@indoormedia.com
SALES_PASSWORD=Zoey2025!!
```

**Security:**
- `.env.local` is gitignored
- File permissions: 600 (read/write by owner only)
- Never commit credentials

---

## Data Files

```
data/
├── b2b_session_cache.json        # Persistent b2b session cache
├── prospect_tracking.json        # Prospects saved status
└── store-rates/
    ├── stores.json               # 612 stores database
    ├── geocode_cache.json        # Cached coordinates
    └── greet_cache.json          # Greet Magazine results
```

---

## Telegram Bot Status

**Bot:** `@IndoorMediaProspectBot`
**PID:** Check with `ps aux | grep telegram_prospecting_bot`
**Logs:** `logs/telegram_prospecting_bot.log`

**Commands:**
- `/start` — Show help
- `/help` — Show help
- `/examples` — Example store numbers

**Buttons (on each prospect):**
- `[📁 Save to b2b]` — Auto-create in b2bappointments
- `[📊 Analyze]` — Open listing analysis
- `[✅ Booked]` — Mark appointment booked + show nearby stores

---

## Workflow Details

### Step 1: Find Prospects

Field rep sends store number to bot:
```
FME07Z-0236
```

Bot returns:
- 10 prospects ranked by likelihood (0-100)
- Distance, Google rating, advertising signals
- Phone numbers for outreach
- Action buttons below each

### Step 2: Save to b2bappointments

Rep clicks `[📁 Save to b2b]` on prospects they want to follow up

**What happens:**
1. Bot calls `b2bappointments_automation.create_contact()`
2. Auto-creates folder: `Klamath Falls/FME07Z-0236` (if needed)
3. Creates contact with:
   - Business name
   - Phone + email
   - Likelihood score (0-100)
   - Category
   - Timestamp

**Result:** Contact saved in b2bappointments for calling

### Step 3: Analyze Listing (Optional)

Rep clicks `[📊 Analyze]` to check listing health

**Opens:**
```
https://www.indoormedia.com/local-listing-management/?business=Joe's+Pizza
```

**Shows:**
- Google listing completeness
- Review velocity
- Missing platforms
- NAP consistency

### Step 4: Call & Qualify

Rep uses b2bappointments lead gen tool to:
- Call the prospect
- Log notes
- Track follow-ups
- Update status (Contacted, Interested, Callback, etc.)

### Step 5: Book & Map

When appointment is confirmed:

Rep clicks `[✅ Booked]` on the prospect

**What happens:**
1. Bot updates status in b2bappointments to "Appointment Booked"
2. Bot calls `nearby_stores_finder.find_nearby_stores()`
3. Finds 10 stores within 3 miles
4. Generates bundle pricing for top 5
5. Sends Telegram message with:
   - Store list (name, chain, distance, pricing)
   - Bundle pricing (all 4 payment plans)
   - Link to Mappoint

**Rep then:**
1. Opens Mappoint
2. Searches for prospect business
3. Adds location to map
4. Enters contracts for nearby stores
5. Tracks deals through sales pipeline

---

## Testing

### Test b2bappointments Integration

```bash
# Create test contact
python3 scripts/b2bappointments_automation.py create "Klamath Falls" "FME07Z-0236" "Test Pizza Co" "541-555-0123" "test@pizza.com" 85 "Restaurant"

# Check if exists
python3 scripts/b2bappointments_automation.py exists "Klamath Falls" "FME07Z-0236" "Test Pizza Co"

# Update status
python3 scripts/b2bappointments_automation.py update "Klamath Falls" "FME07Z-0236" "Test Pizza Co" "Contacted"
```

### Test Nearby Stores Finder

```bash
# Find stores near Vancouver, WA
python3 scripts/nearby_stores_finder.py 45.6872 -122.6151
```

### Test Bot Locally

```bash
python3 scripts/telegram_prospecting_bot.py
# Send message: FME07Z-0236
```

---

## Future Enhancements

### Phase 2 (Ready to Build)

- [ ] Sync status from b2bappointments back to Telegram (show ✓ if already saved)
- [ ] Auto-pull nearby stores when [✅ Booked] clicked (show in Telegram before user goes to Mappoint)
- [ ] Business card pipeline hook (when rep photographs a card, check if it's in their prospects)
- [ ] Bulk mode for multi-store queries
- [ ] Follow-up reminders ("You contacted Joe's Pizza 3 days ago")
- [ ] Conversion tracking (which prospects → which deals)
- [ ] Regional dashboard (best prospects across OR this week)

### Phase 3 (Nice-to-Have)

- [ ] Automatic callback scheduling
- [ ] Deal size estimation (based on business type + advertising spend)
- [ ] Competitor analysis (who else is advertising here)
- [ ] Territory planning (optimal store coverage by rep)
- [ ] AI deal scoring (predict likelihood to close)

---

## Troubleshooting

### b2bappointments Not Creating Contacts

1. Check `.env.local` has correct credentials
2. Verify account access at https://www.b2bappointments.net
3. Check logs: `tail -50 logs/b2b_automation.log`
4. Clear session cache: `rm data/b2b_session_cache.json`

### Prospect Bot Not Responding

1. Check bot is running: `ps aux | grep telegram_prospecting_bot`
2. Restart: `pkill -f telegram_prospecting_bot && python3 scripts/telegram_prospecting_bot.py &`
3. Check logs: `tail -50 logs/telegram_prospecting_bot.log`

### Nearby Stores Not Showing

1. Verify prospect has valid latitude/longitude
2. Check `data/store-rates/stores.json` is loaded
3. Run: `python3 scripts/nearby_stores_finder.py 45.6872 -122.6151`

---

## Support

For questions or issues, contact: Tyler Van Sant (tyler.vansant@indoormedia.com)

---

_Last updated: Feb 25, 2026 | Pipeline Version: 1.0_
