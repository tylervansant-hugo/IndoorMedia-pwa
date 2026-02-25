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

## IndoorMediaRatesBot (Live - Feb 24, 2026 - REBUILT)
**Status:** ✅ RUNNING (Case Count Based Pricing)
- **Bot username:** @IndoorMediaRatesBot
- **438+ stores indexed**

**NEW PRICING MODEL (Case Count Based):**
- 8-14 cases: $2,400 + $150/case
- 15-22 cases: $3,300 + $125/case  
- 23-30 cases: $4,300 + $100/case
- 31-40 cases: $5,100 + $75/case
- **Double ads:** Always 1.4X single price

**Payment Plans:**
- Monthly: base + $125
- 3-month: (base × 0.90) + $125
- 6-month: (base × 0.925) + $125
- Paid in full: (base × 0.85) + $125

**Query Format:**
- Store #: `0415 25` (store# case_count)
- City/Chain: `Bend Safeway 20` (city chain case_count)

## Telegram Rates Bot (Live - Feb 20, 2026)
**Status:** ✅ RUNNING
- **Bot username:** @IndoorMediaRatesBot (ask Tyler to confirm actual name)
- **Token:** Stored in `scripts/telegram_rates_bot.py`
- **Script location:** `scripts/telegram_rates_bot.py`
- **Process:** Running in background (pid monitored by OpenClaw)

**Features:**
- Team members query: `"Longview Safeway single"` or `"Bend Fred Meyer double 6-month"`
- Bot replies with all payment plan options + annual totals
- Supports aliases: `monthly`, `3-month`, `6-month`, `paid-in-full` (or `12`, `3`, `6`, `full`)
- `/cities` command lists all 99 available cities
- `/start` for help

**How team uses it:**
1. Open Telegram, find @IndoorMediaRatesBot
2. Send: `Longview Safeway single`
3. Bot replies with pricing for all payment plans

**Rate Calculator Accuracy:**
- Base rates = ANNUAL totals (not monthly)
- Discounts applied: 10% (3-month), 7.5% (6-month), 15% (paid in full)
- Base + $125 production charge included

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
