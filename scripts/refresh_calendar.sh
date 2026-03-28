#!/bin/bash
# Refresh calendar data for PWA
# Run daily via cron or manually

WORKSPACE="/Users/tylervansant/.openclaw/workspace"
PWA_DATA="$WORKSPACE/pwa/public/data/calendar.json"

gog calendar list --from today --to "next monday" --json 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
events = data.get('events', [])
slim = []
for e in events:
    slim.append({
        'title': e.get('summary', ''),
        'start': e.get('start', {}).get('dateTime', e.get('start', {}).get('date', '')),
        'end': e.get('end', {}).get('dateTime', e.get('end', {}).get('date', '')),
        'location': e.get('location', ''),
        'attendees': [a.get('email','').split('@')[0].replace('.', ' ').title() for a in e.get('attendees', []) if not a.get('self')],
        'status': e.get('status', '')
    })
slim.sort(key=lambda x: x['start'])
with open('$PWA_DATA', 'w') as f:
    json.dump(slim, f, indent=2)
print(f'Exported {len(slim)} events')
"

cd "$WORKSPACE/pwa"
if ! git diff --quiet "$PWA_DATA"; then
    git add "$PWA_DATA"
    git commit -m "auto: Refresh calendar events"
    git push origin main
    echo "✅ Calendar updated and pushed"
else
    echo "✅ No calendar changes"
fi
