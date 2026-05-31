#!/usr/bin/env python3
"""Geocode stores by City+State+PostalCode using Nominatim (free, no API key).
Caches results to avoid re-geocoding. Updates stores.json in-place."""

import json
import time
import urllib.request
import urllib.parse
import os
import sys
from pathlib import Path

STORES_FILE = Path(__file__).parent.parent / "pwa" / "public" / "data" / "stores.json"
CACHE_FILE = Path(__file__).parent.parent / "data" / "geocode_cache.json"
GOOD_ZONES = {'05X', '07X', '07Y', '07Z'}

def geocode(address, city, state, postal_code):
    """Geocode using Nominatim structured search."""
    params = urllib.parse.urlencode({
        'street': address,
        'city': city,
        'state': state,
        'postalcode': postal_code,
        'country': 'US',
        'format': 'json',
        'limit': 1,
    })
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = urllib.request.Request(url, headers={'User-Agent': 'imPro-Sales-Portal/1.0'})
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data:
                return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        pass
    
    # Fallback: city + state only
    params = urllib.parse.urlencode({
        'city': city,
        'state': state,
        'country': 'US',
        'format': 'json',
        'limit': 1,
    })
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = urllib.request.Request(url, headers={'User-Agent': 'imPro-Sales-Portal/1.0'})
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data:
                return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        pass
    
    return None, None

def main():
    stores = json.load(open(STORES_FILE))
    
    # Load cache
    cache = {}
    if CACHE_FILE.exists():
        cache = json.load(open(CACHE_FILE))
    
    # Find stores needing geocoding
    to_geocode = [s for s in stores if s.get('ZoneName') not in GOOD_ZONES]
    print(f"Stores needing geocoding: {len(to_geocode)}")
    
    # Group by address key for deduplication
    updated = 0
    errors = 0
    cached_hits = 0
    
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
            time.sleep(1.1)  # Nominatim rate limit: 1 req/sec
            cache[cache_key] = [lat, lng]
            
            # Save cache every 50 lookups
            if (i - cached_hits) % 50 == 0:
                with open(CACHE_FILE, 'w') as f:
                    json.dump(cache, f)
        
        if lat and lng:
            store['latitude'] = lat
            store['longitude'] = lng
            updated += 1
        else:
            errors += 1
        
        if (i + 1) % 100 == 0:
            print(f"  Progress: {i+1}/{len(to_geocode)} | Updated: {updated} | Cache hits: {cached_hits} | Errors: {errors}")
    
    # Save cache
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)
    
    # Save stores
    with open(STORES_FILE, 'w') as f:
        json.dump(stores, f, indent=2)
    
    print(f"\nDone! Updated: {updated} | Cache hits: {cached_hits} | Errors: {errors}")
    print(f"Saved to {STORES_FILE}")

if __name__ == "__main__":
    main()
