#!/usr/bin/env python3
"""
Daily business discovery routine
Finds potential sales targets within 1 mile of IndoorMedia store locations
Uses free OpenStreetMap + Overpass API (no keys required)
"""

import requests
import pdfplumber
import csv
import json
from datetime import datetime
from pathlib import Path
import time

WORKSPACE = Path("/Users/tylervansant/.openclaw/workspace")
STORES_PDF = Path("/Users/tylervansant/.openclaw/media/inbound/file_3---a01472b4-7818-4fe0-a64c-0aa01e51ce04.pdf")
OUTPUT_DIR = WORKSPACE / "business_targets"
TRACKING_FILE = OUTPUT_DIR / "discovered_businesses.json"
DAILY_REPORT = OUTPUT_DIR / f"targets_{datetime.now().strftime('%Y-%m-%d')}.csv"

# Business categories to target (Overpass API queries)
CATEGORIES = {
    "restaurants": ["restaurant", "cafe", "pizza", "burger", "diner"],
    "services": ["salon", "gym", "laundry", "dry_cleaning"],
    "retail": ["supermarket", "convenience", "shop"],
    "entertainment": ["cinema", "bar", "pub"],
}

def extract_stores_from_pdf(pdf_path):
    """Extract store names, addresses, and coordinates from PDF."""
    stores = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # PDF contains table data
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table[2:]:  # Skip headers (rows 0-1)
                            # Row format: [None, StoreID, StoreName, Chain, Cycle, Address, City, State, Country, ZIP, ...]
                            if row and len(row) >= 9 and row[1] and row[6] and row[7]:
                                stores.append({
                                    "store_id": row[1],
                                    "name": row[2],
                                    "address": f"{row[5]}, {row[6]}, {row[7]} {row[9]}",
                                    "city": row[6],
                                    "state": row[7],
                                    "zip": row[9],
                                })
        print(f"✅ Extracted {len(stores)} store locations")
        return stores
    except Exception as e:
        print(f"❌ Error extracting PDF: {e}")
        import traceback
        traceback.print_exc()
        return []

def geocode_address(address):
    """Use Nominatim (OSM) to get lat/lon. Free, no API key needed."""
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": address, "format": "json", "limit": 1}
        headers = {"User-Agent": "IndoorMedia-BusinessDiscovery/1.0"}
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        
        if response.json():
            result = response.json()[0]
            return float(result["lat"]), float(result["lon"])
        return None
    except Exception as e:
        print(f"  ⚠️  Geocode failed for {address}: {e}")
        return None

def query_nearby_businesses(lat, lon, radius_m=1609):
    """Query Overpass API for businesses within radius (default 1 mile ~1609m)."""
    businesses = []
    try:
        # Overpass API query: find all amenities/shops within bbox
        query = f"""
        [bbox:{lat-0.01},{lon-0.01},{lat+0.01},{lon+0.01}];
        (
            node["amenity"~"restaurant|cafe|bar|pub"];
            node["shop"~"supermarket|convenience|salon"];
            node["leisure"~"fitness_centre"];
        );
        out center;
        """
        
        url = "https://overpass-api.de/api/interpreter"
        response = requests.post(url, data=query, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if "elements" in data:
            for elem in data["elements"]:
                if "center" in elem:
                    c = elem["center"]
                    businesses.append({
                        "name": elem["tags"].get("name", "Unknown"),
                        "type": elem["tags"].get("amenity") or elem["tags"].get("shop"),
                        "lat": c["lat"],
                        "lon": c["lon"],
                    })
        
        return businesses
    except Exception as e:
        print(f"  ⚠️  Overpass query failed: {e}")
        return []

def load_tracking():
    """Load previously discovered businesses to avoid duplicates."""
    if TRACKING_FILE.exists():
        with open(TRACKING_FILE) as f:
            return json.load(f)
    return {"last_run": None, "discovered": {}}

def save_tracking(data):
    """Save tracking data."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(TRACKING_FILE, "w") as f:
        json.dump(data, f, indent=2)

def main():
    print("🚀 IndoorMedia Daily Business Discovery")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Extract stores
    stores = extract_stores_from_pdf(STORES_PDF)
    if not stores:
        print("❌ No stores found in PDF. Check file path.")
        return
    
    # Load tracking
    tracking = load_tracking()
    new_businesses = []
    
    print(f"\n🏪 Scanning {len(stores)} store locations...\n")
    
    for i, store in enumerate(stores[:10], 1):  # Start with first 10 to test
        print(f"[{i}/{min(10, len(stores))}] {store['name']} - {store['address']}")
        
        # Geocode
        coords = geocode_address(store['address'])
        if not coords:
            print(f"    ⚠️  Could not geocode")
            continue
        
        lat, lon = coords
        print(f"    📍 {lat:.4f}, {lon:.4f}")
        
        # Query businesses
        businesses = query_nearby_businesses(lat, lon)
        print(f"    🎯 Found {len(businesses)} nearby businesses")
        
        for biz in businesses:
            key = f"{biz['name']}_{biz['lat']:.4f}_{biz['lon']:.4f}"
            if key not in tracking["discovered"]:
                tracking["discovered"][key] = biz
                new_businesses.append({
                    **biz,
                    "near_store": store['name'],
                    "store_id": store['store_id'],
                    "discovered_at": datetime.now().isoformat()
                })
        
        time.sleep(1)  # Be nice to the API
    
    # Save results
    if new_businesses:
        print(f"\n✅ Found {len(new_businesses)} NEW potential targets!")
        with open(DAILY_REPORT, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "type", "lat", "lon", "near_store", "discovered_at"])
            writer.writeheader()
            writer.writerows(new_businesses)
        print(f"📄 Report: {DAILY_REPORT}")
    else:
        print("\n✓ No new businesses found today.")
    
    # Update tracking
    tracking["last_run"] = datetime.now().isoformat()
    save_tracking(tracking)
    
    print(f"\n📊 Total tracked businesses: {len(tracking['discovered'])}")

if __name__ == "__main__":
    main()
