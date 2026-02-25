#!/usr/bin/env python3
"""
Load IndoorMedia store data from CSV and create searchable indexes.
"""

import csv
import json
from pathlib import Path
from typing import Dict, List, Optional

# Paths
WORKSPACE = Path(__file__).parent.parent
CSV_PATH = WORKSPACE / "store_data.csv"
OUTPUT_DIR = WORKSPACE / "data" / "store-rates"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STORES_FILE = OUTPUT_DIR / "stores.json"
INDEX_FILE = OUTPUT_DIR / "indexes.json"


def load_csv() -> List[Dict]:
    """Load CSV and return list of store dicts."""
    stores = []
    with open(CSV_PATH) as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Clean numeric fields
            row["Case Count"] = int(row["Case Count"])
            row["SingleAd"] = float(row["SingleAd"])
            row["DoubleAd"] = float(row["DoubleAd"])
            stores.append(row)
    return stores


def build_indexes(stores: List[Dict]) -> Dict:
    """Build search indexes for stores."""
    indexes = {
        "by_store_number": {},  # StoreName → store
        "by_city_chain": {},    # "City-Chain" → [stores]
        "by_street": {},        # street name → [stores]
        "by_cycle": {},         # "Cycle-City" → [stores]
    }
    
    for store in stores:
        store_num = store["StoreName"]
        city = store["City"]
        chain = store["GroceryChain"]
        street = store["Address"]
        cycle = store["Cycle"]
        
        # By store number
        indexes["by_store_number"][store_num] = store
        
        # By city + chain (case-insensitive)
        key = f"{city}-{chain}".lower()
        if key not in indexes["by_city_chain"]:
            indexes["by_city_chain"][key] = []
        indexes["by_city_chain"][key].append(store)
        
        # By street (first word for quick lookup)
        street_lower = street.lower()
        if street_lower not in indexes["by_street"]:
            indexes["by_street"][street_lower] = []
        indexes["by_street"][street_lower].append(store)
        
        # By cycle + city
        cycle_key = f"{cycle}-{city}".lower()
        if cycle_key not in indexes["by_cycle"]:
            indexes["by_cycle"][cycle_key] = []
        indexes["by_cycle"][cycle_key].append(store)
    
    return indexes


def save_data(stores: List[Dict], indexes: Dict):
    """Save stores and indexes to JSON files."""
    # Convert stores for JSON serialization
    stores_json = []
    for store in stores:
        s = store.copy()
        stores_json.append(s)
    
    with open(STORES_FILE, "w") as f:
        json.dump(stores_json, f, indent=2)
    
    # Save indexes (but store references → use store numbers instead)
    indexes_json = {
        "by_store_number": list(indexes["by_store_number"].keys()),
        "by_city_chain": {k: [s["StoreName"] for s in v] for k, v in indexes["by_city_chain"].items()},
        "by_street": {k: [s["StoreName"] for s in v] for k, v in indexes["by_street"].items()},
        "by_cycle": {k: [s["StoreName"] for s in v] for k, v in indexes["by_cycle"].items()},
    }
    
    with open(INDEX_FILE, "w") as f:
        json.dump(indexes_json, f, indent=2)
    
    print(f"✅ Saved {len(stores)} stores to {STORES_FILE}")
    print(f"✅ Saved indexes to {INDEX_FILE}")


if __name__ == "__main__":
    print("📦 Loading store data...")
    stores = load_csv()
    print(f"✅ Loaded {len(stores)} stores")
    
    print("🔍 Building indexes...")
    indexes = build_indexes(stores)
    print(f"✅ Built indexes")
    
    print("💾 Saving data...")
    save_data(stores, indexes)
    print("✅ Done!")
