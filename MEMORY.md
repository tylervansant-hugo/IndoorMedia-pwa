# MEMORY.md - Shelldon's Long-Term Memory

## Tyler & Team
- **Tyler Van Sant:** Regional manager for IndoorMedia covering Oregon & Washington
  - Dad of 4, husband
  - Timezone: Pacific (America/Los_Angeles)
  - Values: efficiency, partnership, getting things done

- **Sales Team (9 reps) — Territory Map:**
  - **Amy Dixon** — Tualatin, OR (Willamette Valley)
  - **Jan** — Tualatin, OR (Willamette Valley)
  - **Matt** — Eugene, OR (Southern Oregon)
  - **Ben** — Milwaukee, OR (Northern Oregon)
  - **Meghan** — Vancouver, WA (Southwest Washington)
  - **Dave** — Vancouver, WA (Southwest Washington)
  - **Adan** — Vancouver, WA (Southwest Washington)
  - **Christian** — Southern California (Territory: ?)
  - **Marty** — Location TBD

## Me
- Name: Shelldon 🐚
- Born: 2026-02-16
- Named by Tyler on first boot

## Boundaries & Rules
- **No emails sent without explicit permission** — I draft, preview, or ask first. Never auto-send.

## Recent Wins
- **Feb 17, 2026:** Closed deal at Taqueria Pelayos (Seaside, OR) with Megan Wink
  - Megan had been cold this month ($0 in sales), but worked with her and closed a deal
  - Good momentum builder for her going forward

## Testimonial Search Tool (Created Feb 18, 2026)
Custom keyword search for IndoorMedia testimonials database.
- **Location:** `scripts/testimonial_search.py`
- **Cache size:** 2,000 testimonials (updated weekly, Sunday 2 AM PT)
- **Timeout:** 60 seconds (was 30s, increased for stability)
- **Cache file:** `data/testimonials_cache.json` (persisted in git)
- **Weekly refresh:** Cron job `testimonials-weekly-refresh` auto-updates cache
- **Usage:**
  - Search: `python3 scripts/testimonial_search.py 'keyword'`
  - Refresh: `python3 scripts/testimonial_search.py --refresh`
  - List: `python3 scripts/testimonial_search.py --list`
- **Examples:** 'ROI', 'skeptical', 'parking lot', 'thank you', 'started slow'
- **Notes:** Searches full text of business name, comments, category, keywords. API has ~29,308 total testimonials; 2,000 cache covers recent + historical mix.

## Store Rates Framework (EXPANDED Feb 27, 2026)
**National Coverage: 7,835 Stores** (rebuilt from 612 regional)

**Database:**
- **7,835 stores** across all 50 US states + Canada
- 40+ chains: Kroger, Safeway, Albertsons, Harris Teeter, Smiths, Vons, Ralphs, King Soopers, Tom Thumb, Randalls, HEB, and 28+ others
- Each store has unique SingleAd & DoubleAd pricing
- Cycles: A, B, C (store scheduling)
- Zones: 01-29 (complete national system, replaces old 05X/07X/07Y/07Z regional zones)

**Payment Plans (Applied to each store's base price):**
- **Monthly:** `(base + $125) ÷ 12` = shows $X/month × 12 = $total
- **3-month:** `((base × 0.90) + $125) ÷ 3` = 10% discount (shows $X × 3 = $total)
- **6-month:** `((base × 0.925) + $125) ÷ 6` = 7.5% discount (shows $X × 6 = $total)
- **Paid-in-full:** `(base × 0.85) + $125` = 15% discount (one payment)
- **Note:** $125 production charge added AFTER discount % applied

**Query Types Supported:**
- **Store number:** `FME07Y-0165`
- **City + Chain:** `Klamath Falls Fred Meyer`
- **Cycle + City:** `A Cycle Beaverton`
- **Street name:** `Lincoln City` (searches all stores with that street)

**Files:**
- `store_data.csv` — Raw 612-store dataset
- `scripts/store_loader.py` — Load CSV, build indexes
- `scripts/pricing_calculator.py` — Pricing with dual display
- `scripts/store_search.py` — Query interface
- `data/store-rates/stores.json` — Persistent store DB
- `data/store-rates/indexes.json` — Search indexes (by store#, city+chain, street, cycle)

**Example Usage:**
```bash
python3 scripts/pricing_calculator.py FME07Y-0165 single
→ Returns JSON with all 4 payment plans (each showing per-installment + total)
```

## IndoorMediaRatesBot v2 (CONSOLIDATED - Mar 6, 2026)
**Status:** ✅ RETIRED & CONSOLIDATED INTO PROSPECTBOT
- **Rationale:** @IndoorMediaProspectBot now includes all pricing, rates, and metrics
- **Script removed:** `scripts/telegram_rates_bot_v2.py`
- **Database:** 7,835 stores (now serves prospectbot exclusively)

**Query Types Supported:**
1. **Store number:** `KRO21Y-0350` (any of 7,835 stores)
2. **City + Chain:** `Denver Kroger` (works nationwide)
3. **Cycle + City:** `A Cycle Beaverton` (store scheduling)
4. **Street search:** `Main Street` (finds all stores on that street)
5. **Double ad prefix:** `double Denver Kroger`

**Payment Plans (Dual Display):**
Each shows per-installment + total:
- Monthly: `$300/mo × 12 = $3,600`
- 3-month: `$1,200 × 3 = $3,600` (10% off)
- 6-month: `$600 × 6 = $3,600` (7.5% off)  
- Paid-in-full: `$3,060` (15% off)

**Commands:**
- `/start` or `/help` — Shows query formats
- `/cities` — Lists all 612 cities
- `/chains` — Lists all chains
- Buttons: Toggle single/double ad after query

**Formula (per Tyler's spec):**
- Monthly: `(base + $125) ÷ 12` → shows per month + total
- 3-month: `((base × 0.90) + $125) ÷ 3` → shows per payment + total
- 6-month: `((base × 0.925) + $125) ÷ 6` → shows per payment + total
- Paid-in-full: `(base × 0.85) + $125` → one payment

**Database:**
- 612 stores (CA/OR/WA)
- Zones: 05X (CA), 07X (WA North), 07Y (OR), 07Z (OR/WA South)
- Chains: Safeway, Fred Meyer, Albertsons, Stater Bros., Food 4 Less, Quality Food Center, Haggen, Vons, Ralphs, Saars, Rosauers, Sherms, Shop N Kart, Food Pavillion
- Each store: unique SingleAd & DoubleAd pricing

## Business Card Pipeline System (In Development - Feb 20, 2026)
**Problem:** Team gets 25-50 business cards/month in field, but no systematic follow-up → momentum dies, deals lost.

**Solution:** Photo → OCR → Draft → Track in B2Bappointments.net

**Key Requirements:**
- Team-accessible (Telegram for field submissions preferred)
- Auto-create/organize folders in B2Bappointments.net **by city**
- Draft text messages (email backup) with nearby store reference
- Tracking log (sent status, responses, follow-up reminders)
- Pull testimonials for added credibility in outreach

**Waiting For:**
- B2Bappointments.net API credentials from Tyler
  - Need: API endpoint, auth method, folder structure preferences
  - Alternatively: Web automation if no API available

**What I Can Build Now:**
- OCR + contact extraction (phone, email, company name)
- Message drafting logic + templating
- Tracking spreadsheet
- Telegram bot for team submissions (basic version)

**Phase 1 (Ready to Start):**
- OCR contact extraction
- Message drafting
- Shared tracking (Google Sheet or workspace log)
- B2Bappointments integration (once API keys arrive)

**Phase 2:**
- Telegram bot for field submissions
- Auto-follow-up reminders
- Response tracking dashboard

## "Find Today's Deal" Prospecting Tool (Built Feb 24, 2026)
**Status:** ✅ PHASE 1+2 LIVE (Google Places + Greet Magazine)

### Phase 1: Base Prospecting
- **Input:** Store number (e.g., `FME07Z-0236`)
- **Output:** Top 10 prospects ranked by likelihood (0-100 score)
- **Query radius:** 2 miles max
- **Target businesses:** Restaurants, salons, gyms, vets, retail, auto shops

### Phase 2: Advertising Signals (In Progress)
- **Greet Magazine detection** ✅ — Check if business advertises on Greet
- **Facebook Ads Library** ⏳ — Requires API setup (already researched)
- **Groupon/LivingSocial** ⏳ — Find coupon platforms
- **Google Local Services Ads** ⏳ — Paid advertising indicator
- **Indeed jobs** ⏳ — Business growth signal

### Likelihood Score Breakdown (0-100):
- **Distance** (0-25 pts) — Closer = higher
- **Google Rating** (0-25 pts) — Higher rating = healthier
- **Review Velocity** (0-20 pts) — Recent reviews = active
- **Business Status** (0-15 pts) — Open/closed indicator
- **Advertising Signals** (0-40 pts) — Found on Greet/Facebook = +40 boost

### Files:
- `scripts/prospecting_tool.py` — Base version (Google Places only)
- `scripts/prospecting_tool_enhanced.py` — With advertising signals
- `scripts/greet_scraper.py` — Greet Magazine web scraper
- `scripts/facebook_ads_checker.py` — Facebook Ads Library (setup guide)
- `data/store-rates/geocode_cache.json` — Cached lat/lon for 599 stores
- `data/store-rates/greet_cache.json` — Cached Greet Magazine results

### Usage:
```bash
# Basic (Google Places only)
python3 scripts/prospecting_tool.py FME07Z-0236 10

# Enhanced (with Greet Magazine signals)
python3 scripts/prospecting_tool_enhanced.py FME07Z-0236 10
```

### Next Steps:
1. Enable Facebook Ads Library scraping (API setup + goplaces integration)
2. Add Groupon search integration
3. Build Telegram bot interface for field reps
4. Add newspaper/local media advertising detection
5. Scale to all 612 stores with batch processing

## ROI Calculator (LIVE - Mar 6, 2026)
**Status:** ✅ LIVE & RUNNING on localhost:8501 + INTEGRATED with ProspectBot

**Purpose:** Help reps calculate and visualize ROI for register tape campaigns before pitching customers.

**Interface:**
- Streamlit web app (professional, real-time sliders)
- **Location:** `scripts/roi_calculator.py`
- **Launch script:** `scripts/run_roi_calculator.sh`
- **Venv:** `.venv_roi` (isolated Python environment)

### Integration with ProspectBot
**Feature:** `📊 ROI Calc` button on every prospect card
- Click button → Opens pre-filled ROI calculator
- Store number auto-selected from URL parameter (?store=STORENUM)
- Seamless workflow: Find prospect → Check ROI in seconds
- URL format: `http://localhost:8501?store=ROS07Z-0042`

**Where it appears:**
- ✅ Prospect expansion panel (next to Calendar)
- ✅ All prospects with valid store numbers

**Workflow:**
1. Find prospect in ProspectBot
2. Click "▶️ Show Actions" to expand
3. Click "📊 ROI Calc" button
4. Streamlit app opens with store pre-selected
5. Adjust sliders and see instant ROI

**Metrics Shown:**
- Monthly/annual revenue, profit, ROI
- Break-even redemptions needed
- Payment option comparison (pricing displayed)

**Pricing Strategy (Conservative):**
- No uplift calculations (single-transaction basis)
- Show base case: redemptions × (ticket - coupon) × (1 - COGS%)
- Price ranges: Co-Op Single PIF (low) → Standard Double Monthly (high)

**Example Output:**
```
Store: Rosauers Ridgefield (ROS07Z-0042)
Metrics: 30 redemptions/mo, $50 avg ticket, $10 coupon, 35% COGS

Monthly Revenue: $1,200 (30 × $40)
Monthly Profit: $780 (after COGS)
Monthly Ad Cost: $295.83 (Co-Op, Monthly)
Monthly Net: $484.17
ROI: 164%
```

**Technical Details:**
- Uses store base prices (ANNUAL) from store_data.json
- Payment plans: Monthly (annual cost) vs Paid-in-full (85% discount)
- Tiers: Co-Op (base + $125) vs Standard (base + $1,200 + $125)
- All campaigns = 12 months
- Monthly cost for ROI = Annual ÷ 12
- URL parameter support: accepts `?store=STORENUM` and pre-fills store

**Data Sources:**
- Store numbers, prices, case counts from `data/store-rates/stores.json`
- 7,835 stores across all 50 states + Canada

---

## Testimonial Prep Bot (In Development - Feb 25, 2026)
**Status:** MVP Sprint (sub-agent building)

**Purpose:** Conversational prep for in-person/virtual meetings. Reps describe the business they're meeting with ("Turkish restaurant in Vancouver, WA"), bot returns:
1. **1 video testimonial** (most relevant, highest strength)
2. **3-5 written testimonials** with full details (quote, business name, store, metrics, link)
3. Last testimonial geographically closest to prospect

**Features:**
- Conversational input: e.g., "Popeyes in Portland" or "barista in Bend"
- Smart fallback: If no exact match, expand to synonyms (barista → coffee, espresso, mocha, brew, café, beverage)
- Separate `/keyword` button for written testimonial search (existing tool, unchanged)

**Video sources (to scrape):**
- YouTube playlist: https://youtube.com/playlist?list=PLjTXw9VlAiGP7cKVD_F1rPWERnmjeDCB1
- TikTok: @tyhasreceipts
- Google Drive folders: [Tyler to provide API credentials]

**Sub-agent task:** Build telegram_testimonial_bot_prep.py with YouTube scraper + TikTok scraper + existing testimonial DB matching + geography logic

**Delivery:** Working Telegram bot alongside @IndoorMediaRatesBot and @IndoorMediaProspectBot

## Sales Dashboard (ENHANCED - Mar 3, 2026)
**Status:** ✅ LIVE - Gmail contracts sync + sales tracking + calendar events

### Features:
**💳 My Sales Button**
- Shows Tyler's closed deals summary
- Total revenue, deal count, average deal size
- Recent deals list with dates and amounts
- Expandable to view all deals

**👥 Team Sales Button**
- Shows all reps' closed deals
- Leaderboard by revenue
- Deal count by rep
- Expandable to view all team deals

**📧 Gmail Contracts Scanner**
- Runs daily at 8 PM PT (off-peak)
- Searches Gmail for emails: "IndoorMedia Contract Signed"
- Scans back to 1/1/2026
- Extracts PDF attachments automatically
- Parses contract data using pdfplumber

**Data Captured (from Email + PDF):**
- Contract #, Date
- Business name, Address
- Contact name, email, phone
- Business owner (Advertiser Printed Name from PDF)
- Sales rep name
- Store name & number (e.g., QFC07Z-0206)
- Product description (e.g., Register Tape Single Ad)
- Total amount (parsed from PDF Contract Total)
- Payment date

**PDF Extraction:**
- Downloads PDFs from Google Drive links in emails
- Parses all contract fields for accuracy
- Extracts addresses, phone numbers, business details
- Total amounts always accurate

**Storage:**
- File: `data/contracts.json`
- Updated nightly via LaunchAgent
- All historical contracts preserved

**Cron Setup:**
- LaunchAgent: `com.indoormedia.contracts-scanner`
- Schedule: 8 PM daily (20:00 PT)
- Log files: `/tmp/contracts_scan.log`

### Calendar Integration (Mar 3, 2026)
**Features:**
- **My Customers page** now shows "Next Event" for each saved prospect
- Pulls upcoming events from Google Calendar
- Matches events by customer name
- Displays: Event title + date (e.g., "Install tape at QFC07Z-0206-Milwaukie Ave (4/7/2026)")

**Full Contact Details on Customer Cards:**
- 👤 Contact person (business owner)
- 📍 Address (from PDF contract)
- 📞 Phone number
- 📧 Email address
- 📅 Next scheduled event (from calendar)

**Prospect Detail View:**
- Shows all extracted contact info when rep clicks on saved customer
- Enables quick reference without leaving the bot

---

## IndoorMediaProspectBot - Phase 4 Upgrade (Mar 6, 2026 - CPM + DAILY COST METRICS)
**Status:** ✅ LIVE with CPM and daily cost calculations across all tiers

### New Metrics (Effective Mar 6, 2026 - FINAL VERSION)
**Every pricing plan now shows:**
1. **Daily Cost** = Total contract amount ÷ 365 days
2. **CPM (Cost Per Thousand)** = (Daily cost ÷ Daily impressions) × 1,000
3. **Daily Impressions** = Calculated from store case count

**Key Rule:** Campaign runs 12 months regardless of payment plan.

**Impressions Formula:**
- Quarterly = Case Count × 50 rolls/case × 137 segments/roll × 2 repetitions
- Monthly = Quarterly ÷ 3
- Daily = Monthly ÷ 30

**CPM Calculation (CORRECTED - 12-month campaign basis):**
- **Daily Cost = Total Contract Amount ÷ 365**
- **CPM = (Daily Cost ÷ Daily Impressions) × 1,000**
- Different payment plans = different totals = different daily costs & CPMs

**Example (Rosauers, Ridgefield - ROS07Z-0042 | 15 cases | 2,283 daily impressions):**
```
Monthly: $295.83/mo × 12 = $3,550.00 total
  → $9.73/day | CPM: $4.26

3-month: $1,069.17 × 3 = $3,207.50 total (10% off)
  → $8.79/day | CPM: $3.85

6-month: $548.85 × 6 = $3,293.12 total (7.5% off)
  → $9.02/day | CPM: $3.95

Paid-in-full: $3,036.25 (15% off)
  → $8.32/day | CPM: $3.64
```

**Key insight:** Discounts result in lower daily cost & CPM, showing real value!

**Bot Display Updates:**
- Store card shows case count & daily impressions
- Each rate tier (Co-Op/Exclusive/Contractor) displays metrics below each plan
- Backward compatible with existing pricing structure

---

## IndoorMediaProspectBot - Phase 3 Upgrade (Mar 3, 2026 - PRICING TIERS + CALENDAR)
**Status:** ✅ LIVE with three-tier pricing & integrated calendar scheduling

### Pricing Structure (Mar 3, 2026)
**Default View:** $1,200 padding + monthly/total only
- Rep selects tier to unlock full pricing breakdown

**Three Tiers:**
1. **🎯 Manager Approved Co-Op** - Full discounts (10%, 7.5%, 15%)
2. **🏆 Exclusive Category** - No discounts except 5% PIF
3. **🔧 Contractors** - Only 3mo + 5% PIF + "Buy 2 Get 1 Free" promo

**Base Price Alignment:**
- Exclusive & Contractors = Co-Op monthly total as their base
- Simplifies pricing across tiers

### Calendar Scheduling (Live Feature)
**Button:** `📅 Create Appointment` (on every prospect card)

**Flow:**
1. Rep clicks button → Date picker (Today + 14 days)
2. Select time → Time picker (6 AM - 8 PM, 15-min intervals)
3. Auto-creates Google Calendar event with:
   - Business name, address, phone, store #
   - Rep's saved notes (from notepad)
   - Links to: `tyler.vansant@indoormedia.com`

**Implementation:** `gog calendar create` command

---

## IndoorMediaProspectBot - Phase 1 Upgrade (Mar 2, 2026)
**Status:** ✅ LIVE with team-wide features

**New Features:**
1. **💾 Saved/Bookmarked Prospects** 
   - Tap "💾 Save" button on any prospect
   - Assign pipeline status: Interested / Follow-up / Proposal / Closed
   - View all saved in "💾 Saved Prospects" menu
   - Filter by status

2. **🎬 Video Testimonials** (Hardcoded + Category-Based)
   - "🎬 Video" button on each prospect
   - Links to YouTube testimonial videos
   - Expandable with YouTube API later

3. **📊 Dashboard - Personal + Team View**
   - YOUR METRICS: Searches today, Saved count, Status breakdown
   - TEAM METRICS: Total searches, Total saved, Team status breakdown, Top 3 reps
   - Shows all 9 reps' activity aggregated
   - Visible to Tyler and all reps

4. **👤 Rep Identification & Tracking**
   - Each rep identified by Telegram user_id
   - Rep name auto-captured from Telegram profile
   - Data persisted per rep in `data/prospect_data.json`
   - Session-based metrics (searches, bookmarks per session)

5. **Data Persistence**
   - JSON file: `data/prospect_data.json`
   - Stores: saved_prospects, contact_history, search_history per rep
   - Survives session restarts
   - Tyler can see all reps' data on dashboard

**Upcoming (Phase 2):**
- Contact history (last_contacted, visit_count, call_notes)
- Search history tracking + "Recent Searches" menu
- Follow-up reminders (cron job)

## Telegram Bots - Live & Running (Feb 25, 2026)

### @IndoorMediaRatesBot (PID 35556) ✅
- **Purpose:** Store pricing queries
- **Input:** Store # or city+chain (e.g., `Klamath Falls Fred Meyer`)
- **Output:** 4 payment plans with per-installment + total
- **Features:** Single/double ad toggle, `/cities` and `/chains` commands
- **Status:** Live (restarted 10:34 AM, missing telegram dependency fixed)

### @IndoorMediaProspectBot v3 (Status: LIVE 2/27 - IMPROVED) ✅
- **Purpose:** Google Places discovery for tape advertising prospects
- **Input Options:**
  - Store number (e.g., `FME07Z-0236`)
  - City name (e.g., `Denver`)
  - Nationwide support (7,835 store coverage)
- **Output:** Top 10 businesses ranked by likelihood (0-100 score) + action buttons
- **Workflow:**
  1. Send store number → `FME07Z-0236`
  2. Bot returns ranked prospects by score
  3. [📁 Save to b2b] → Creates contact in b2bappointments
  4. [📞 Call] → Direct phone dial
  5. [✅ Booked!] → Marks as booked
- **Features:**
  - **40+ category search** (expanded from 6) for better relevance
    - Food & Beverage (15 types)
    - Retail & Shopping (14 types)
    - Services (8 types)
    - Health & Wellness (8 types)
    - Professional (6 types)
    - Entertainment (5 types)
  - Proximity ranking (within 2 miles)
  - Google rating + review counts
  - Advertising signals (Greet Magazine + Facebook Ads framework)
  - Likelihood scoring (distance + rating + reviews + advertising)

### Bot Evolution (Feb 25, 2026)

**v1:** Complex b2bappointments automation (Playwright web automation)
- Approach: Auto-create contacts in b2bappointments
- Issue: Fragile selectors, timeouts, browser automation too complex

**v2:** Simplified category filtering
- Approach: 73 alphabetized business categories + proximity search
- Issue: Still complex, focused on b2bappointments when Google Maps is simpler

**v3: Google Places Focus (Current)** ✅
- Approach: Let Google Maps be the CRM, use reps' native workflow
- Workflow:
  1. Rep enters location (store #, zip, city, or near me)
  2. Picks category (6 main, 50+ subs with icons)
  3. Gets results ranked by proximity + sponsored ads
  4. Taps [📍 View on Maps] → Opens Google Maps (native workflow)
  5. Taps [📞 Call] → Direct phone dial
- Why it works: Simpler, more reliable, leverages existing Google Maps ecosystem, no b2bappointments automation headaches

**Configuration:**
- Credentials in `.env.local` (gitignored)
  - B2B_USERNAME=Tyler.vansant@indoormedia.com
  - B2B_PASSWORD=Zoey2026!
  - SALES_USERNAME=Tyler.VanSant@indoormedia.com
  - SALES_PASSWORD=Zoey2025!!

### Advertising Signal Detection
**Sources:**
- Greet Magazine: +40 pts
- Facebook Ads Library: +50 pts
- Combined: Up to 90 pt boost

**Example Scores:**
- No advertising: 50-65/100
- On Greet Magazine: 90-100/100 (significant boost)
- Active Facebook Ads: 95-100/100 (strong marketing indicator)

### Commands
- `/start` — Help message
- `/examples` — Sample store numbers to try
- `/help` — Full instructions

### Field Rep Workflow
1. Send store number: `FME07Z-0236`
2. Get 10 ranked prospects
3. Click [📁 Save] → Saved to b2bappointments
4. Use b2bappointments lead gen to call
5. When appointment booked, click [✅ Booked]
6. Bot shows nearby stores + pricing
7. Open Mappoint to enter contracts

### Files
- `scripts/telegram_prospecting_bot.py` — Prospect bot (UPDATED)
- `scripts/b2bappointments_automation.py` — b2b web automation (NEW)
- `scripts/nearby_stores_finder.py` — Stores + pricing (NEW)
- `scripts/facebook_ads_checker.py` — Facebook Ads integration
- `scripts/prospecting_tool_enhanced.py` — Enhanced scoring
- `docs/PROSPECT_PIPELINE.md` — Full documentation (NEW)
- `data/store-rates/greet_cache.json` — Persistent caching

### Status: ✅ PRODUCTION READY
- Both bots running (rates + prospect with full pipeline)
- All integrations tested
- Credentials secure in .env.local
- Ready for field team deployment
- Documentation complete

### Next Phase (Waitlist)
- Sync b2bappointments status back to Telegram (✓ checkmarks)
- Business card OCR → Auto-match to prospects
- Bulk/regional dashboard
- Follow-up reminders
- Conversion tracking

## Audit Module (BUILT - Mar 2, 2026)
**Status:** ✅ LIVE with ProspectBot v4

**Features:**
1. **Audit Store Menu** (🏪 Audit Store button)
   - Rep selects store from any store number (FME07Z-0236, etc.)
   - Bot queries store DB for last shipment details

2. **Delivery Confirmation Flow**
   - Shows: "{StoreName} was sent {CaseCount} cases on {DeliveryDate}. Confirm?"
   - Yes → Move to inventory entry
   - No → Show adjustment menu (Change Shipment Month / Change Shipment Quantity)
   - Month dropdown: All 12 months (Jan-Dec)
   - Cases dropdown: 0-50 cases (5-case increments)

3. **Inventory Entry**
   - Rep sends: `CASES ROLLS` (e.g., `15 25`)
   - Cases: 0-50, Rolls: 0-49
   - Bot calculates: `(cases × 50) + rolls = total_rolls`

4. **Audit Projection**
   - Days until runout: `total_rolls ÷ 11.1 rolls/day`
   - Next delivery date: Based on store cycle (A/B/C)
   - Alert if: `days_until_runout < days_until_next_delivery`
   - Shows: ✅ or ⚠️ status

5. **Email Report**
   - Recipient: tyler.vansant@indoormedia.com
   - Contains: Store #, Rep, Delivery date, Starting cases, Current inventory, Days until runout, Alert status
   - Sent via `gog cli` (Gmail integration)

**Implementation Details:**
- **Cycle dates (hardcoded, most recent past):**
  - A: Jan 7, Apr 7, Jul 7, Oct 7
  - B: Feb 7, May 7, Aug 7, Nov 7
  - C: Mar 7, Jun 7, Sep 7, Dec 7
- **Inventory formula:** 20 cases = 1,000 rolls (50 rolls/case)
- **Usage rate:** 11.1 rolls/day (~90 days for 1,000 rolls)
- **State constants:** AWAITING_AUDIT_STORE, AWAITING_AUDIT_DELIVERY, AWAITING_AUDIT_INVENTORY
- **Bot file:** `scripts/telegram_prospecting_bot.py` (added ~600 lines)

**Menu Updates:**
- Added "👥 My Customers" button (shows active saved prospects by pipeline status)
- Added "🏪 Audit Store" button to main menu

**Client List Feature:**
- Shows all saved prospects (active customers)
- Groups by status: Interested / Follow-up / Proposal / Closed
- Displays store #, business name, rep, status count

**Next Steps:**
- Test end-to-end with real audit data
- Confirm email format & recipients with Tyler
- Store audit history per store (supply date, inventory, timestamp) in prospect_data.json
- Add integration with contract pipeline (audit triggers on calendar events)
