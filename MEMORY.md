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
