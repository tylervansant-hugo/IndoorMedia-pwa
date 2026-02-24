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

## Store Rates Skill (Updated Feb 24, 2026)
Custom skill for IndoorMedia store rates database. Features:
- **438+ stores across 332 cities** (CA, OR, WA) — Fred Meyer, Safeway, Albertsons, Stater Bros., Ralphs, Food 4 Less, Vons, Haggen, Saars, Quality Food Center, etc.
- **Pricing Structure** (Standard for all stores):
  * **Monthly (12 payments):** base + $125
  * **3-month prepaid (3 payments):** (base × 0.90) + $125 = 10% off
  * **6-month prepaid (6 payments):** (base × 0.925) + $125 = 7.5% off
  * **Paid in full:** (base × 0.85) + $125 = 15% off
  - $125 = production charge (nonnegotiable)
  - Discounts apply to base annual price only, then add $125
- **Zones:**
  - **05X** = California stores (added Feb 24, 2026)
  - **07X** = Washington/Northern states (added Feb 24, 2026)
  - **07Y** = Oregon stores
  - **07Z** = Washington stores
- **CLI Usage:**
  - `python skills/store-rates/scripts/rate_calculator.py Chehalis Safeway`
- **Data persisted to git** — survives session boundaries
- Location: `/Users/tylervansant/.openclaw/workspace/skills/store-rates/`

## IndoorMediaRatesBot (Live - Feb 24, 2026)
**Status:** ✅ RUNNING
- **Bot username:** @IndoorMediaRatesBot
- **438+ stores ready to query**
- **Features:**
  - Query by store number: `0415`
  - Query by city+chain: `Longview Safeway`
  - Automatic single & double ad pricing
  - Button-based plan switching (no retyping)

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
