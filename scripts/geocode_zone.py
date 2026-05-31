#!/usr/bin/env python3
"""Geocode stores for a specific zone (or all bad zones). Uses Nominatim with cache."""

import json
import time
import urllib.request
import urllib.parse
import sys
from pathlib import Path

STORES_FILE = Path(__file__).parent.parent / "pwa" / "public" / "data" / "stores.json"
CACHE_FILE = Path(__file__).parent.parent / "data" / "geocode_cache.json"
GOOD_ZONES = {'05X', '07X', '07Y', '07Z'}

def geocode(address, city, state, postal_code):
    """Geocode using Nominatim structured search."""
    # Try full address first
    params = urllib.parse.urlencode({
        'street': address, 'city': city, 'state': state,
        'postalcode': postal_code, 'country': 'US',
        'format': 'json', 'limit': 1,
    })
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = urllib.request.Request(url, headers={'User-Agent': 'imPro-Sales-Portal/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data:
                return float(data[0]['lat']), float(data[0]['lon'])
    except:
        pass
    
    # Fallback: city + state + zip
    params = urllib.parse.urlencode({
        'city': city, 'state': state, 'postalcode': postal_code,
        'country': 'US', 'format': 'json', 'limit': 1,
    })
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = urllib.request.Request(url, headers={'User-Agent': 'imPro-Sales-Portal/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data:
                return float(data[0]['lat']), float(data[0]['lon'])
    except:
        pass
    
    return None, None

def main():
    target_zone = sys.argv[1] if len(sys.argv) > 1 else None
    
    stores = json.load(open(STORES_FILE))
    cache = json.load(open(CACHE_FILE)) if CACHE_FILE.exists() else {}
    
    if target_zone:
        to_geocode = [s for s in stores if s.get('ZoneName') == target_zone]
    else:
        to_geocode = [s for s in stores if s.get('ZoneName') not in GOOD_ZONES]
    
    print(f"Geocoding {len(to_geocode)} stores" + (f" in zone {target_zone}" if target_zone else ""), flush=True)
    
    updated = 0
    cached_hits = 0
    errors = 0
    
    for i, store in enumerate(to_geocode):
        addr = store.get('Address', '')
        city = store.get('City', '')
        state = store.get('State', '')
        postal = store.get('PostalCode', '')
        cache_key = f"{addr}|{city}|{state}|{postal}"
        
        if cache_key in cache:
            lat, lng = cache[cache_key]
            cached_hits += 1
        else:
            lat, lng = geocode(addr, city, state, postal)
            time.sleep(1.05)
            cache[cache_key] = [lat, lng]
            if (i - cached_hits + 1) % 25 == 0:
                with open(CACHE_FILE, 'w') as f:
                    json.dump(cache, f)
        
        if lat and lng:
            store['latitude'] = lat
            store['longitude'] = lng
            updated += 1
        else:
            errors += 1
            print(f"  ⚠️ Failed: {store.get('StoreName')} | {addr}, {city}, {state}", flush=True)
        
        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{len(to_geocode)} | ✅ {updated} | 📦 cache: {cached_hits} | ❌ {errors}", flush=True)
    
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)
    with open(STORES_FILE, 'w') as f:
        json.dump(stores, f, indent=2)
    
    print(f"\nDone! ✅ {updated} updated | 📦 {cached_hits} cached | ❌ {errors} errors", flush=True)

if __name__ == "__main__":
    main()
