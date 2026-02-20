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

## Store Rates Skill (Updated Feb 18, 2026)
Custom skill for IndoorMedia store rates database. Features:
- **245 stores across 99 cities** (OR/WA) — Fred Meyer, Safeway, Albertsons, Quality Food Center, etc.
- **Pricing Model:** $1,325 cushion = $1,200 negotiable padding + $125 nonnegotiable production charge
  - **Standard (base rates)**: SingleAd/DoubleAd + $1,325 cushion, minimums at base only
  - **Lowest price** (--lowest): monthly minimum, apply discounts, add $125 production:
    * Month-to-month: base + $125
    * 6-month prepaid: base × 0.925 + $125 (7.5% off)
    * 3-month prepaid: base × 0.90 + $125 (10% off)
    * Paid in full: base × 0.85 + $125 (15% off)
- **CLI Usage:**
  - Standard: `python skills/store-rates/scripts/rate_calculator.py Chehalis Safeway`
  - Lowest: `python skills/store-rates/scripts/rate_calculator.py Chehalis Safeway --lowest`
- **Data persisted to git** — survives session boundaries
- Location: `/Users/tylervansant/.openclaw/workspace/skills/store-rates/`

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
