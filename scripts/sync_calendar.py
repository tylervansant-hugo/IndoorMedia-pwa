#!/usr/bin/env python3
"""
Sync Google Calendar events to PWA appointments.json
Pulls upcoming events from Tyler's calendar, scopes by rep.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta

ACCOUNT = "tyler.vansant@indoormedia.com"
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "pwa", "public", "data", "appointments.json")


def get_calendar_events(days_ahead=30):
    """Fetch upcoming calendar events."""
    now = datetime.now()
    from_date = now.strftime("%Y-%m-%dT00:00:00")
    to_date = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%dT23:59:59")
    
    cmd = [
        "gog", "calendar", "events", "primary",
        "--from", from_date,
        "--to", to_date,
        "--account", ACCOUNT,
        "--json", "--no-input"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        print(f"Error fetching calendar: {result.stderr}", file=sys.stderr)
        return []
    
    try:
        data = json.loads(result.stdout)
        return data.get("events", data) if isinstance(data, dict) else data
    except json.JSONDecodeError:
        print(f"Failed to parse calendar data", file=sys.stderr)
        return []


def parse_event(event):
    """Parse a calendar event into appointment format."""
    summary = event.get("summary", "")
    description = event.get("description", "")
    location = event.get("location", "")
    start = event.get("start", {})
    end = event.get("end", {})
    event_id = event.get("id", "")
    
    start_dt = start.get("dateTime", start.get("date", ""))
    end_dt = end.get("dateTime", end.get("date", ""))
    
    # Extract attendees
    attendees = []
    for a in event.get("attendees", []):
        attendees.append({
            "email": a.get("email", ""),
            "name": a.get("displayName", ""),
            "status": a.get("responseStatus", ""),
        })
    
    # Try to extract rep name from description or attendees
    rep = ""
    # Check description for rep info
    rep_match = re.search(r'Rep:\s*(.+)', description or "")
    if rep_match:
        rep = rep_match.group(1).strip()
    
    # Check for prospect info in description
    prospect_name = ""
    phone = ""
    address = ""
    store = ""
    
    for line in (description or "").split('\n'):
        line = line.strip()
        if line.startswith('Prospect:'):
            prospect_name = line.replace('Prospect:', '').strip()
        elif line.startswith('Phone:'):
            phone = line.replace('Phone:', '').strip()
        elif line.startswith('Address:'):
            address = line.replace('Address:', '').strip()
        elif line.startswith('Store:'):
            store = line.replace('Store:', '').strip()
    
    # If summary starts with "Visit:" it's a prospect visit
    is_prospect_visit = summary.startswith('Visit:') or summary.startswith('📦')
    
    return {
        "event_id": event_id,
        "title": summary,
        "start": start_dt,
        "end": end_dt,
        "location": location,
        "description": description,
        "prospect_name": prospect_name,
        "phone": phone,
        "address": address,
        "store": store,
        "rep": rep,
        "attendees": attendees,
        "is_prospect_visit": is_prospect_visit,
        "creator": event.get("creator", {}).get("email", ""),
    }


def main():
    print("Fetching calendar events (next 30 days)...")
    events = get_calendar_events(30)
    print(f"Found {len(events)} events")
    
    appointments = []
    for event in events:
        appt = parse_event(event)
        appointments.append(appt)
    
    # Sort by start date
    appointments.sort(key=lambda a: a.get("start", ""))
    
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, 'w') as f:
        json.dump(appointments, f, indent=2)
    
    print(f"Saved {len(appointments)} appointments to {OUTPUT}")


if __name__ == "__main__":
    main()
