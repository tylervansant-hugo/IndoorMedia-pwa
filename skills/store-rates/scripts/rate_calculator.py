#!/usr/bin/env python3
"""
IndoorMedia Rate Calculator - Case Count Based Pricing
Simple formula: base price per case count + discounts + $125 production
"""

import json
import sys
from pathlib import Path

# Case count pricing tiers for SINGLE ads
CASE_PRICING = {
    8: 2400,
    9: 2550,
    10: 2700,
    11: 2850,
    12: 3000,
    13: 3150,
    14: 3300,
    15: 3425,
    16: 3550,
    17: 3675,
    18: 3800,
    19: 3925,
    20: 4050,
    21: 4175,
    22: 4300,
    23: 4400,
    24: 4500,
    25: 4600,
    26: 4700,
    27: 4800,
    28: 4900,
    29: 5000,
    30: 5100,
    31: 5175,
    32: 5250,
    33: 5325,
    34: 5400,
    35: 5475,
    36: 5550,
    37: 5625,
    38: 5700,
    39: 5775,
    40: 5850,
}

# Load store data
script_dir = Path(__file__).parent
store_file = script_dir.parent / "references" / "store_data.json"
city_file = script_dir.parent / "references" / "city_chains.json"

try:
    with open(store_file) as f:
        STORES = {s["code"]: s for s in json.load(f)["stores"]}
    
    with open(city_file) as f:
        data = json.load(f)
        CITY_CHAINS = data.get("city_chains", {})
        STORES_BY_CODE = data.get("stores_by_code", {})
except Exception as e:
    print(f"Error loading data: {e}")
    STORES = {}
    CITY_CHAINS = {}
    STORES_BY_CODE = {}


def get_single_price(case_count):
    """Get base annual price for single ad by case count."""
    return CASE_PRICING.get(case_count, None)


def get_double_price(case_count):
    """Get base annual price for double ad by case count (1.4X single)."""
    single = get_single_price(case_count)
    if single:
        return round(single * 1.4, 2)
    return None


def calculate_plans(base_price):
    """Calculate all payment plans. $125 added AFTER discounts."""
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
    """Find stores by city and chain."""
    city_title = city.title()
    chain_title = chain.title()
    
    if city_title not in CITY_CHAINS or chain_title not in CITY_CHAINS[city_title]:
        return []
    
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
    
    for store in STORES.values():
        city = store.get("city", "").lower()
        address = store.get("address", "").lower()
        
        if street_lower in city or street_lower in address:
            results.append(store)
    
    return results


def format_response(store, case_count, ad_type="single"):
    """Format store response with pricing."""
    if ad_type == "single":
        base = get_single_price(case_count)
    else:
        base = get_double_price(case_count)
    
    if not base:
        return None
    
    planning = calculate_plans(base)
    
    return {
        "code": store["code"],
        "name": store["name"],
        "city": store.get("city", ""),
        "state": store.get("state", ""),
        "case_count": case_count,
        "ad_type": ad_type,
        "base_price": base,
        "pricing": planning
    }


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python rate_calculator.py CITY CHAIN CASE_COUNT [single|double]")
        print("  python rate_calculator.py --search-street STREET")
        print("  python rate_calculator.py --list-cities")
        return 1
    
    # List cities
    if sys.argv[1] == "--list-cities":
        for city in sorted(CITY_CHAINS.keys()):
            print(city)
        return 0
    
    # Search street
    if sys.argv[1] == "--search-street":
        if len(sys.argv) < 3:
            print(json.dumps([]))
            return 0
        
        results = find_stores_by_street(sys.argv[2])
        output = [
            {
                "code": s["code"],
                "name": s["name"],
                "city": s.get("city", ""),
                "state": s.get("state", "")
            }
            for s in results[:20]
        ]
        print(json.dumps(output))
        return 0
    
    # Normal lookup: CITY CHAIN CASE_COUNT [single|double]
    if len(sys.argv) < 4:
        print(json.dumps({"error": "Need CITY, CHAIN, and CASE_COUNT"}))
        return 1
    
    city = sys.argv[1]
    chain = sys.argv[2]
    
    try:
        case_count = int(sys.argv[3])
    except ValueError:
        print(json.dumps({"error": "CASE_COUNT must be a number"}))
        return 1
    
    ad_type = "single"
    if len(sys.argv) > 4 and sys.argv[4] in ("single", "double"):
        ad_type = sys.argv[4]
    
    # Find stores
    matching = find_stores_by_city_chain(city, chain)
    if not matching:
        print(json.dumps({"error": f"No stores found for {city} {chain}"}))
        return 1
    
    # Use first match
    response = format_response(matching[0], case_count, ad_type)
    if response:
        print(json.dumps(response))
    else:
        print(json.dumps({"error": f"Invalid case count: {case_count}"}))
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
