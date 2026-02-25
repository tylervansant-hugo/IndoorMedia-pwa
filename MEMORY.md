# MEMORY.md - Shelldon's Long-Term Memory

## Tyler
- Dad of 4, husband
- Regional manager for IndoorMedia covering Oregon & Washington
- Timezone: Pacific (America/Los_Angeles)
- Values: efficiency, partnership, getting things done

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

## Store Rates Framework (REBUILT Feb 24, 2026)
**New: Store-Specific Pricing** (old case-count model deleted)

**Database:**
- **612 stores** across CA, OR, WA (Safeway, Fred Meyer, Albertsons, Stater Bros., Food 4 Less, Quality Food Center, Haggen, Vons, Ralphs, Saars, Shop N Kart, etc.)
- Each store has unique SingleAd & DoubleAd pricing
- Cycles: A, B, C (store scheduling)
- Zones: 05X (CA), 07X (WA North), 07Y (OR), 07Z (OR/WA South)

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

## IndoorMediaRatesBot v2 (Live - Feb 24, 2026 - STORE-SPECIFIC)
**Status:** ✅ RUNNING (Store-Specific Pricing, 612 stores)
- **Bot username:** @IndoorMediaRatesBot
- **Script:** `scripts/telegram_rates_bot_v2.py`
- **PID:** 80201 (monitored)

**Query Types Supported:**
1. **Store number:** `FME07Y-0165` → Klamath Falls Fred Meyer
2. **City + Chain:** `Klamath Falls Fred Meyer`
3. **Cycle + City:** `A Cycle Beaverton` (store scheduling)
4. **Street search:** `Shasta Way` (finds all stores on that street)
5. **Double ad prefix:** `double Klamath Falls Fred Meyer`

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
