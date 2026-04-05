#!/bin/bash
# Hourly calendar sync for PWA
# Syncs Google Calendar → appointments.json → GitHub Pages

WORKSPACE="/Users/tylervansant/.openclaw/workspace"
cd "$WORKSPACE"

echo "[$(date)] Starting hourly calendar sync..."

# Run the main calendar sync
python3 scripts/sync_calendar.py 2>&1

# Build and deploy if appointments changed
cd "$WORKSPACE/pwa"
if ! git diff --quiet public/data/appointments.json 2>/dev/null; then
    npm run build 2>/dev/null
    npx gh-pages -d dist --no-history 2>/dev/null
    git add public/data/appointments.json
    git commit -m "auto: Hourly calendar sync [$(date +%H:%M)]" 2>/dev/null
    git push origin main 2>/dev/null
    echo "[$(date)] ✅ Calendar updated and deployed"
else
    echo "[$(date)] ✅ No calendar changes"
fi
