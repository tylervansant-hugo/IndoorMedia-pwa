#!/usr/bin/env python3
"""Geocode stores using free-text Nominatim search (more forgiving than structured)."""

import json
import time
import urllib.request
import urllib.parse
import sys
from pathlib import Path

STORES_FILE = Path(__file__).parent.parent / "pwa" / "public" / "data" / "stores.json"
CACHE_FILE = Path(__file__).parent.parent / "data" / "geocode_cache_v2.json"
GOOD_ZONES = {'05X', '07X', '07Y', '07Z'}

def geocode_freetext(query):
    """Geocode using Nominatim free-text search (more forgiving)."""
    params = urllib.parse.urlencode({
        'q': query,
        'format': 'json',
        'limit': 1,
        'countrycodes': 'us',
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

def geocode_store(store):
    """Try multiple query strategies."""
    addr = store.get('Address', '')
    city = store.get('City', '')
    state = store.get('State', '')
    postal = store.get('PostalCode', '')
    
    # Strategy 1: Full address + city + state + zip
    query = f"{addr}, {city}, {state} {postal}"
    lat, lng = geocode_freetext(query)
    if lat:
        return lat, lng
    time.sleep(1.05)
    
    # Strategy 2: City + State + Zip only
    query = f"{city}, {state} {postal}"
    lat, lng = geocode_freetext(query)
    if lat:
        return lat, lng
    time.sleep(1.05)
    
    # Strategy 3: City + State
    query = f"{city}, {state}"
    lat, lng = geocode_freetext(query)
    return lat, lng

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
        
        if cache_key in cache and cache[cache_key][0]:
            lat, lng = cache[cache_key]
            cached_hits += 1
        else:
            lat, lng = geocode_store(store)
            time.sleep(1.05)
            cache[cache_key] = [lat, lng]
            if (i - cached_hits + 1) % 20 == 0:
                with open(CACHE_FILE, 'w') as f:
                    json.dump(cache, f)
        
        if lat and lng:
            store['latitude'] = lat
            store['longitude'] = lng
            updated += 1
        else:
            errors += 1
            print(f"  ❌ {store.get('StoreName')} | {addr}, {city}, {state} {postal}", flush=True)
        
        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{len(to_geocode)} | ✅ {updated} | 📦 {cached_hits} | ❌ {errors}", flush=True)
    
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)
    with open(STORES_FILE, 'w') as f:
        json.dump(stores, f, indent=2)
    
    print(f"\n✅ Done! {updated} updated | {cached_hits} cached | {errors} errors", flush=True)

if __name__ == "__main__":
    main()
