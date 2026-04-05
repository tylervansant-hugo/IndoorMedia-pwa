#!/usr/bin/env python3
"""
Generate hot leads for rep stores using Google Places API.
Finds up to 5 businesses near each store in the current selling cycle.
"""

import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from google_places_wrapper import GooglePlacesWrapper

STORES_FILE = os.path.join(os.path.dirname(__file__), "..", "pwa", "public", "data", "stores.json")
CONTRACTS_FILE = os.path.join(os.path.dirname(__file__), "..", "pwa", "public", "data", "contracts.json")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "pwa", "public", "data", "hot_leads.json")

# Categories to search for near stores
SEARCH_CATEGORIES = [
    "restaurant",
    "auto repair",
    "dentist",
    "hair salon",
    "gym",
    "veterinarian",
    "chiropractor",
    "pizza",
    "mexican restaurant",
    "coffee shop",
]

def get_current_selling_cycle():
    """Determine current selling cycle based on date."""
    now = datetime.now()
    month = now.month - 1  # 0-indexed
    day = now.day
    cycle_map = ['A', 'B', 'C']
    install_cycle = cycle_map[month % 3]
    sell_map = {'A': 'C', 'B': 'A', 'C': 'B'}
    
    if day < 11:
        prev_month = (month + 11) % 12
        prev_install = cycle_map[prev_month % 3]
        return sell_map[prev_install]
    else:
        return sell_map[install_cycle]


def get_rep_stores(contracts, stores_lookup, zones=('07Y', '07Z', '07X', '07W')):
    """Find all stores where reps have sold, in specified zones."""
    rep_store_ids = set()
    for c in contracts:
        zone = (c.get('zone', '') or '').strip()
        chain = (c.get('store_name', '') or '').strip()
        num = (c.get('store_number', '') or '').strip()
        if zone in zones and chain and num:
            for sid, s in stores_lookup.items():
                if sid.endswith(num) and s['GroceryChain'].lower().startswith(chain.lower().split()[0]):
                    rep_store_ids.add(sid)
                    break
    return rep_store_ids


def main():
    # Load data
    with open(STORES_FILE) as f:
        all_stores = json.load(f)
    stores_lookup = {s['StoreName']: s for s in all_stores}
    
    with open(CONTRACTS_FILE) as f:
        contracts_data = json.load(f)
    contracts = contracts_data.get('contracts', [])
    
    # Get current selling cycle
    cycle = get_current_selling_cycle()
    print(f"Current selling cycle: {cycle}")
    
    # Get rep stores
    rep_store_ids = get_rep_stores(contracts, stores_lookup)
    print(f"Total rep stores (all zones): {len(rep_store_ids)}")
    
    # Filter to current cycle
    cycle_stores = [stores_lookup[sid] for sid in rep_store_ids 
                    if sid in stores_lookup and stores_lookup[sid].get('Cycle') == cycle]
    print(f"Stores on {cycle} cycle: {len(cycle_stores)}")
    
    # Load existing leads to avoid re-querying
    existing_leads = []
    existing_store_ids = set()
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE) as f:
                existing_leads = json.load(f)
            existing_store_ids = set(l.get('store_id', '') for l in existing_leads)
        except:
            pass
    
    # Only query stores we haven't already generated leads for
    new_stores = [s for s in cycle_stores if s['StoreName'] not in existing_store_ids]
    print(f"New stores to query: {len(new_stores)} (already have {len(existing_store_ids)})")
    
    if not new_stores and '--force' not in sys.argv:
        print("No new stores to process. Use --force to regenerate all.")
        return
    
    if '--force' in sys.argv:
        new_stores = cycle_stores
        existing_leads = []
    
    # Initialize Google Places
    gp = GooglePlacesWrapper()
    if not gp.api_key:
        print("ERROR: GOOGLE_PLACES_API_KEY not set!")
        return
    
    all_leads = list(existing_leads)  # Keep existing leads for other stores
    processed = 0
    max_stores = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else len(new_stores)
    
    for store in new_stores[:max_stores]:
        lat = store.get('latitude')
        lon = store.get('longitude')
        if not lat or not lon:
            continue
        
        store_id = store['StoreName']
        store_chain = store['GroceryChain']
        store_city = store['City']
        store_state = store['State']
        
        print(f"\n  Searching near {store_chain} {store_city} ({store_id})...")
        
        # Pick 2-3 random categories to search
        import random
        cats = random.sample(SEARCH_CATEGORIES, min(3, len(SEARCH_CATEGORIES)))
        
        store_leads = []
        for cat in cats:
            try:
                results = gp.search_nearby(
                    latitude=lat, longitude=lon,
                    keyword=cat,
                    radius=3000,  # 3km radius
                    limit=3
                )
                
                for r in results:
                    # Skip if already in leads
                    if any(l.get('place_id') == r.get('place_id') for l in all_leads):
                        continue
                    if any(l.get('place_id') == r.get('place_id') for l in store_leads):
                        continue
                    
                    lead = {
                        "store_id": store_id,
                        "store_chain": store_chain,
                        "store_city": store_city,
                        "store_state": store_state,
                        "store_cycle": store.get('Cycle', ''),
                        "category": cat.title(),
                        "business_name": r.get('name', ''),
                        "rating": r.get('rating', 0),
                        "reviews": r.get('user_ratings_total', 0),
                        "address": r.get('vicinity', r.get('formatted_address', '')),
                        "phone": r.get('phone', ''),
                        "website": r.get('website', ''),
                        "distance_mi": round(r.get('distance_mi', 0), 1),
                        "place_id": r.get('place_id', ''),
                        "lat": r.get('geometry', {}).get('location', {}).get('lat', 0),
                        "lon": r.get('geometry', {}).get('location', {}).get('lng', 0),
                        "status": "approved",
                        "generated_at": datetime.now().isoformat(),
                    }
                    store_leads.append(lead)
                
                time.sleep(0.3)  # Rate limit
                
            except Exception as e:
                print(f"    Error searching {cat}: {e}")
                continue
        
        # Keep max 5 per store
        store_leads = store_leads[:5]
        all_leads.extend(store_leads)
        processed += 1
        print(f"    Found {len(store_leads)} leads")
        
        # Save periodically
        if processed % 10 == 0:
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(all_leads, f, indent=2)
            print(f"  ... saved {len(all_leads)} total leads so far")
    
    # Final save
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(all_leads, f, indent=2)
    
    print(f"\nDone! {len(all_leads)} total hot leads saved ({processed} stores queried)")


if __name__ == "__main__":
    main()
