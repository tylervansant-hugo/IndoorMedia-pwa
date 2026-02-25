#!/usr/bin/env python3
"""
Geocode stores (add latitude/longitude) using Google Geocoding API.
Caches results to avoid repeated API calls.
"""

import json
import os
import sys
from pathlib import Path
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

WORKSPACE = Path(__file__).parent.parent
DATA_DIR = WORKSPACE / "data" / "store-rates"
STORES_FILE = DATA_DIR / "stores.json"
GEOCODE_CACHE = DATA_DIR / "geocode_cache.json"


def load_geocache() -> dict:
    """Load cached geocoding results."""
    if GEOCODE_CACHE.exists():
        with open(GEOCODE_CACHE) as f:
            return json.load(f)
    return {}


def save_geocache(cache: dict):
    """Save geocoding cache."""
    with open(GEOCODE_CACHE, 'w') as f:
        json.dump(cache, f, indent=2)


def geocode_address(address: str, city: str, state: str, api_key: str, cache: dict) -> dict:
    """Geocode an address using Google Geocoding API."""
    try:
        import googlemaps
    except ImportError:
        logger.error("❌ googlemaps library not installed. Run: pip install googlemaps")
        return {}
    
    # Cache key
    cache_key = f"{address}, {city}, {state}"
    if cache_key in cache:
        return cache[cache_key]
    
    try:
        gmaps = googlemaps.Client(key=api_key)
        result = gmaps.geocode(cache_key)
        
        if result:
            location = result[0]['geometry']['location']
            cached_result = {
                'latitude': location['lat'],
                'longitude': location['lng'],
                'formatted_address': result[0].get('formatted_address')
            }
            cache[cache_key] = cached_result
            time.sleep(0.1)  # Rate limiting
            return cached_result
        else:
            logger.warning(f"⚠️ Could not geocode: {cache_key}")
            return {}
    except Exception as e:
        logger.error(f"❌ Geocoding error for {cache_key}: {e}")
        return {}


def main():
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        logger.error("❌ GOOGLE_PLACES_API_KEY not set in .env")
        sys.exit(1)
    
    logger.info("📍 Loading stores for geocoding...")
    with open(STORES_FILE) as f:
        stores = json.load(f)
    
    cache = load_geocache()
    logger.info(f"📦 Loaded {len(cache)} cached geocoding results")
    
    logger.info(f"🌍 Geocoding {len(stores)} stores...")
    
    for i, store in enumerate(stores):
        if store.get('latitude') and store.get('longitude'):
            continue  # Already geocoded
        
        result = geocode_address(
            store['Address'],
            store['City'],
            store['State'],
            api_key,
            cache
        )
        
        if result:
            store['latitude'] = result['latitude']
            store['longitude'] = result['longitude']
            logger.info(f"✅ [{i+1}/{len(stores)}] {store['StoreName']}: {result['latitude']:.4f}, {result['longitude']:.4f}")
        else:
            logger.warning(f"⚠️ [{i+1}/{len(stores)}] {store['StoreName']}: FAILED")
        
        # Save every 50 stores
        if (i + 1) % 50 == 0:
            save_geocache(cache)
    
    # Save final results
    logger.info("💾 Saving geocoded stores...")
    with open(STORES_FILE, 'w') as f:
        json.dump(stores, f, indent=2)
    
    save_geocache(cache)
    logger.info("✅ Geocoding complete!")


if __name__ == "__main__":
    main()
