# Business Discovery System

Free, location-based sales target discovery for IndoorMedia.

## What's Here

- **all_stores.csv** — Your 240 store locations (OR & WA)
  - 167 in Oregon
  - 73 in Washington

## How It Works

### Phase 1 ✅ (Currently Active)
Extract store reference data from your PDF rate card.

```bash
python3 scripts/discover_targets.py  # Run anytime
```

### Phase 2 (Coming Soon)
Geofence-triggered business discovery:
- When you enter a grocery store (with Meta glasses), grab nearby businesses
- Restaurants, gyms, salons, retail — within 1 mile radius
- Free API: OpenStreetMap + Overpass

### Phase 3 (Roadmap)
- Daily reports of new prospects
- Accountability tracker integration
- Automatic CRM sync

## APIs Used

- **Nominatim (OpenStreetMap)** — Free address-to-coordinates lookup
- **Overpass** — Free business discovery within radius
- No API keys, no billing

## Setup for Daily Runs

Via cron:

```bash
crontab -e

# Add this line to run daily at 8:00 AM:
0 8 * * * cd /Users/tylervansant/.openclaw/workspace && source .venv/bin/activate && python3 scripts/discover_targets.py >> business_targets/discovery.log 2>&1
```

Or via OpenClaw cron:

```bash
# (Already set up — check MEMORY.md for job ID)
```

## Next: Tell Me When You're Ready

1. **Ready for geofence discovery?** → Let me know when you have Meta glasses paired
2. **Want daily summaries?** → I'll send reports to Telegram/email
3. **Integration with accountability tracker?** → Can sync with your team spreadsheet

---

*Built for Tyler at IndoorMedia. Free, local-first, no tracking.* 🐚
