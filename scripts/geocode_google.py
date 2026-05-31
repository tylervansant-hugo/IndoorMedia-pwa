#!/usr/bin/env python3
"""Geocode stores using Google Geocoding API (fast, accurate, uses existing API key)."""

import json
import time
import urllib.request
import urllib.parse
import sys
import os
from pathlib import Path

STORES_FILE = Path(__file__).parent.parent / "pwa" / "public" / "data" / "stores.json"
CACHE_FILE = Path(__file__).parent.parent / "data" / "geocode_cache_google.json"
GOOD_ZONES = {'05X', '07X', '07Y', '07Z'}

# Load API key
ENV_FILE = Path(__file__).parent.parent / ".env"
API_KEY = None
if ENV_FILE.exists():
    for line in open(ENV_FILE):
        if line.startswith('GOOGLE_PLACES_API_KEY='):
            API_KEY = line.strip().split('=', 1)[1]
if not API_KEY:
    API_KEY = os.environ.get('GOOGLE_PLACES_API_KEY')
if not API_KEY:
    print("❌ No GOOGLE_PLACES_API_KEY found")
    sys.exit(1)

def geocode(address, city, state, postal):
    """Geocode using Google Geocoding API."""
    query = f"{address}, {city}, {state} {postal}"
    params = urllib.parse.urlencode({
        'address': query,
        'key': API_KEY,
    })
    url = f"https://maps.googleapis.com/maps/api/geocode/json?{params}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get('status') == 'OK' and data.get('results'):
                loc = data['results'][0]['geometry']['location']
                return loc['lat'], loc['lng']
            elif data.get('status') == 'ZERO_RESULTS':
                # Try city-level fallback
                params2 = urllib.parse.urlencode({
                    'address': f"{city}, {state} {postal}",
                    'key': API_KEY,
                })
                url2 = f"https://maps.googleapis.com/maps/api/geocode/json?{params2}"
                with urllib.request.urlopen(urllib.request.Request(url2), timeout=10) as resp2:
                    data2 = json.loads(resp2.read())
                    if data2.get('status') == 'OK' and data2.get('results'):
                        loc = data2['results'][0]['geometry']['location']
                        return loc['lat'], loc['lng']
    except Exception as e:
        print(f"  ⚠️ API error: {e}", flush=True)
    return None, None

def main():
    target_zone = sys.argv[1] if len(sys.argv) > 1 else None
    
    stores = json.load(open(STORES_FILE))
    cache = json.load(open(CACHE_FILE)) if CACHE_FILE.exists() else {}
    
    if target_zone:
        to_geocode = [s for s in stores if s.get('ZoneName') == target_zone]
    else:
        to_geocode = [s for s in stores if s.get('ZoneName') not in GOOD_ZONES]
    
    print(f"Geocoding {len(to_geocode)} stores" + (f" in zone {target_zone}" if target_zone else " (all bad zones)"), flush=True)
    
    updated = 0
    cached_hits = 0
    errors = 0
    
    for i, store in enumerate(to_geocode):
        addr = store.get('Address', '')
        city = store.get('City', '')
        state = store.get('State', '')
        postal = store.get('PostalCode', '')
        cache_key = f"{addr}|{city}|{state}|{postal}"
        
        if cache_key in cache and cache[cache_key][0]:
            lat, lng = cache[cache_key]
            cached_hits += 1
        else:
            lat, lng = geocode(addr, city, state, postal)
            cache[cache_key] = [lat, lng]
            # Google allows 50 req/sec but let's be gentle
            time.sleep(0.05)
            if (i - cached_hits + 1) % 100 == 0:
                with open(CACHE_FILE, 'w') as f:
                    json.dump(cache, f)
        
        if lat and lng:
            store['latitude'] = lat
            store['longitude'] = lng
            updated += 1
        else:
            errors += 1
            print(f"  ❌ {store.get('StoreName')} | {addr}, {city}, {state} {postal}", flush=True)
        
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(to_geocode)} | ✅ {updated} | 📦 {cached_hits} | ❌ {errors}", flush=True)
    
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)
    with open(STORES_FILE, 'w') as f:
        json.dump(stores, f, indent=2)
    
    print(f"\n✅ Done! {updated}/{len(to_geocode)} updated | {cached_hits} cached | {errors} errors", flush=True)

if __name__ == "__main__":
    main()
