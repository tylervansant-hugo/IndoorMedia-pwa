#!/usr/bin/env python3
"""
Sync rep activity data to rep_sync.json.
This runs on a schedule to aggregate data from appointments, 
daily goals (submitted via the app), and activity logs.

For now, daily goals are stored per-device in localStorage.
This script generates the shared sync file from available data sources.
"""
import json
import os
from datetime import datetime, timedelta

WORKSPACE = os.path.dirname(os.path.dirname(__file__))
SYNC_FILE = os.path.join(WORKSPACE, 'pwa', 'public', 'data', 'rep_sync.json')
APPOINTMENTS_FILE = os.path.join(WORKSPACE, 'pwa', 'public', 'data', 'appointments.json')
REGISTRY_FILE = os.path.join(WORKSPACE, 'pwa', 'public', 'data', 'rep_registry.json')

def main():
    # Load existing sync data
    try:
        with open(SYNC_FILE) as f:
            sync = json.load(f)
    except:
        sync = {}
    
    # Load registry
    try:
        with open(REGISTRY_FILE) as f:
            registry = json.load(f)
    except:
        registry = {}
    
    # Load appointments
    try:
        with open(APPOINTMENTS_FILE) as f:
            appointments = json.load(f)
    except:
        appointments = []
    
    # Build per-rep appointment counts
    today = datetime.now().strftime('%Y-%m-%d')
    
    for uid, info in registry.items():
        name = info.get('display_name', '')
        if not name:
            continue
        
        rep_key = name.lower().replace(' ', '_')
        if rep_key not in sync:
            sync[rep_key] = {
                'name': name,
                'uid': uid,
                'daily_goals': {},
                'appointments_upcoming': 0,
                'last_sync': today
            }
        
        # Count upcoming appointments for this rep
        upcoming = 0
        for appt in appointments:
            if appt.get('start', '') >= today:
                creator = (appt.get('creator', '') or '').lower()
                attendees = [a.get('email', '').lower() for a in appt.get('attendees', [])]
                rep_lower = name.lower()
                if rep_lower.split()[0] in creator or any(rep_lower.split()[0] in a for a in attendees):
                    upcoming += 1
        
        sync[rep_key]['appointments_upcoming'] = upcoming
        sync[rep_key]['last_sync'] = today
    
    with open(SYNC_FILE, 'w') as f:
        json.dump(sync, f, indent=2)
    
    print(f"Synced {len(sync)} reps to {SYNC_FILE}")

if __name__ == '__main__':
    main()
