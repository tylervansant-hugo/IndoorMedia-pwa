#!/usr/bin/env python3
"""
IndoorMedia Store Rate Calculator - Clean, simple implementation
Pricing formula: base + $125 (production charge), then apply discounts
"""

import json
import sys
from pathlib import Path

# Load data
script_dir = Path(__file__).parent
store_file = script_dir.parent / "references" / "store_data.json"
city_file = script_dir.parent / "references" / "city_chains.json"

with open(store_file) as f:
    stores = json.load(f)["stores"]

with open(city_file) as f:
    city_data = json.load(f)

STORES = {s["code"]: s for s in stores}
CITY_CHAINS = city_data.get("city_chains", {})
STORES_BY_CODE = city_data.get("stores_by_code", {})


def calculate_pricing(base_price):
    """Calculate all payment plans for a given base price."""
    prod_charge = 125.0
    
    return {
        "monthly": {
            "annual": round(base_price + prod_charge, 2),
            "per_month": round((base_price + prod_charge) / 12, 2),
            "installments": 12,
            "desc": "12 monthly payments"
        },
        "3month": {
            "annual": round((base_price * 0.90) + prod_charge, 2),
            "per_month": round(((base_price * 0.90) + prod_charge) / 3, 2),
            "installments": 3,
            "desc": "3 payments (10% off)"
        },
        "6month": {
            "annual": round((base_price * 0.925) + prod_charge, 2),
            "per_month": round(((base_price * 0.925) + prod_charge) / 6, 2),
            "installments": 6,
            "desc": "6 payments (7.5% off)"
        },
        "paid_full": {
            "annual": round((base_price * 0.85) + prod_charge, 2),
            "per_month": round((base_price * 0.85) + prod_charge, 2),
            "installments": 1,
            "desc": "One upfront payment (15% off)"
        }
    }


def find_stores_by_city_chain(city, chain):
    """Find stores by city and chain name."""
    city_title = city.title()
    chain_title = chain.title()
    
    if city_title not in CITY_CHAINS:
        return []
    
    if chain_title not in CITY_CHAINS[city_title]:
        return []
    
    # Find all matching stores
    results = []
    for code, store_info in STORES_BY_CODE.items():
        if store_info["city"] == city_title and store_info["chain"] == chain_title:
            store = STORES.get(code)
            if store:
                results.append(store)
    
    return results


def find_stores_by_street(street):
    """Find stores by street name."""
    street_lower = street.lower()
    results = []
    
    for store in stores:
        city = store.get("city", "").lower()
        address = store.get("address", "").lower()
        
        if street_lower in city or street_lower in address:
            results.append(store)
    
    return results


def format_store_response(store, ad_type="single"):
    """Format store data with pricing for bot."""
    if ad_type == "single":
        base = store["singlead"]
    else:
        base = store["doublead"]
    
    pricing = calculate_pricing(base)
    
    return {
        "code": store["code"],
        "name": store["name"],
        "city": store.get("city", ""),
        "state": store.get("state", ""),
        "tier": store.get("tier", ""),
        "cycle": store.get("cycle", ""),
        "ad_type": ad_type,
        "base_price": base,
        "pricing": pricing
    }


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python rate_calculator.py --search-street STREET")
        print("  python rate_calculator.py CITY CHAIN [single|double] --json")
        print("  python rate_calculator.py --list-cities")
        return 1
    
    # Handle street search
    if sys.argv[1] == "--search-street":
        if len(sys.argv) < 3:
            print(json.dumps([]))
            return 0
        
        street = sys.argv[2]
        results = find_stores_by_street(street)
        
        # Return simplified format for bot
        output = []
        for store in results[:20]:  # Limit to 20
            output.append({
                "code": store["code"],
                "name": store["name"],
                "city": store.get("city", ""),
                "state": store.get("state", ""),
                "singlead": store["singlead"],
                "doublead": store["doublead"]
            })
        
        print(json.dumps(output))
        return 0
    
    # Handle list cities
    if sys.argv[1] == "--list-cities":
        cities = sorted(CITY_CHAINS.keys())
        for city in cities:
            print(city)
        return 0
    
    # Normal lookup: CITY CHAIN [single|double]
    if len(sys.argv) < 3:
        print("Error: Need CITY and CHAIN")
        return 1
    
    city = sys.argv[1]
    chain = sys.argv[2]
    ad_type = "single"
    
    if len(sys.argv) > 3 and sys.argv[3] in ("single", "double"):
        ad_type = sys.argv[3]
    
    # Find stores
    matching = find_stores_by_city_chain(city, chain)
    
    if not matching:
        print(json.dumps({"error": f"No stores found for {city} {chain}"}))
        return 1
    
    # Return first match with pricing
    response = format_store_response(matching[0], ad_type)
    print(json.dumps(response))
    return 0


if __name__ == "__main__":
    sys.exit(main())
