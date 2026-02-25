#!/usr/bin/env python3
"""
Search stores by store number, city+chain, street, or cycle.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional

WORKSPACE = Path(__file__).parent.parent
DATA_DIR = WORKSPACE / "data" / "store-rates"
STORES_FILE = DATA_DIR / "stores.json"
INDEX_FILE = DATA_DIR / "indexes.json"


class StoreSearch:
    def __init__(self):
        """Initialize search with stores and indexes."""
        with open(STORES_FILE) as f:
            self.stores_list = json.load(f)
        
        self.stores = {s["StoreName"]: s for s in self.stores_list}
        
        with open(INDEX_FILE) as f:
            self.indexes = json.load(f)
    
    def by_store_number(self, store_num: str) -> Optional[Dict]:
        """Find store by store number (e.g., FME07Y-0165)."""
        store_num = store_num.upper()
        return self.stores.get(store_num)
    
    def by_city_chain(self, city: str, chain: str) -> List[Dict]:
        """Find stores by city and chain name."""
        key = f"{city}-{chain}".lower()
        store_nums = self.indexes["by_city_chain"].get(key, [])
        return [self.stores[num] for num in store_nums if num in self.stores]
    
    def by_cycle(self, cycle: str, city: str) -> List[Dict]:
        """Find stores by cycle (A/B/C) and city."""
        key = f"{cycle}-{city}".lower()
        store_nums = self.indexes["by_cycle"].get(key, [])
        return [self.stores[num] for num in store_nums if num in self.stores]
    
    def by_street(self, street_name: str) -> List[Dict]:
        """Find stores by street name (partial match)."""
        street_lower = street_name.lower()
        results = []
        for store in self.stores_list:
            if street_lower in store["Address"].lower():
                results.append(store)
        return results


if __name__ == "__main__":
    import sys
    
    search = StoreSearch()
    
    if len(sys.argv) < 2:
        print("Usage: store_search.py <query_type> <arg1> [arg2]")
        print("  store_number: <store_num>")
        print("  city_chain: <city> <chain>")
        print("  cycle: <cycle> <city>")
        print("  street: <street_name>")
        sys.exit(1)
    
    query_type = sys.argv[1].lower()
    
    if query_type == "store_number":
        store = search.by_store_number(sys.argv[2])
        if store:
            print(json.dumps([store], indent=2))
        else:
            print(json.dumps([], indent=2))
    
    elif query_type == "city_chain":
        results = search.by_city_chain(sys.argv[2], sys.argv[3])
        print(json.dumps(results, indent=2))
    
    elif query_type == "cycle":
        results = search.by_cycle(sys.argv[2], sys.argv[3])
        print(json.dumps(results, indent=2))
    
    elif query_type == "street":
        results = search.by_street(sys.argv[2])
        print(json.dumps(results, indent=2))
    
    else:
        print(f"Unknown query type: {query_type}")
        sys.exit(1)
