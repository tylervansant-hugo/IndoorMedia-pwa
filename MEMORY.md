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

## Store Rates Skill (Updated Feb 18, 2026)
Custom skill for IndoorMedia store rates database. Features:
- **245 stores across 99 cities** (OR/WA) — Fred Meyer, Safeway, Albertsons, Quality Food Center, etc.
- **Pricing Model:**
  - **Base rates** = per-ad rates WITH $1,325 cushion + $125 minimum floor (default display)
  - **Lowest price** = monthly minimum WITHOUT cushion, then apply discount tiers, then +$125:
    * Month-to-month: base + $125
    * 6-month prepaid: base × 0.925 + $125 (7.5% off)
    * 3-month prepaid: base × 0.90 + $125 (10% off)
    * Paid in full: base × 0.85 + $125 (15% off)
- **CLI Usage:**
  - Standard (base rates): `python skills/store-rates/scripts/rate_calculator.py <city> [chain]`
  - Lowest prices: `python skills/store-rates/scripts/rate_calculator.py <city> [chain] --lowest`
  - Example: `python skills/store-rates/scripts/rate_calculator.py Chehalis Safeway --lowest`
- **Data persisted to git** — survives session boundaries
- Location: `/Users/tylervansant/.openclaw/workspace/skills/store-rates/`
