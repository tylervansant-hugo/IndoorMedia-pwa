#!/usr/bin/env python3
"""
Store Rate Calculator - Query store rates and apply pricing adjustments
"""

import json
import sys
import os
from pathlib import Path

# Load store data from reference file
script_dir = Path(__file__).parent
data_file = script_dir.parent / "references" / "store_data.json"

with open(data_file, 'r') as f:
    data = json.load(f)

STORES = data["stores"]
PRICING = data["pricing_adjustments"]


def find_stores_by_city_and_chain(city: str, chain_name: str = None) -> list:
    """Find stores by city and optionally by chain name."""
    city_lower = city.lower()
    results = []
    
    for store in STORES:
        if store["city"].lower() == city_lower:
            if chain_name is None or chain_name.lower() in store["name"].lower():
                results.append(store)
    
    return results


def calculate_adjusted_rates(store: dict, paid_in_full: bool = False) -> dict:
    """
    Calculate adjusted rates for a store with cushions and optional discount.
    
    Returns dict with:
    - singlead_base: base rate
    - singlead_adjusted: base + cushion
    - doublead_base: base rate
    - doublead_adjusted: base + cushion
    - singlemin_base: base minimum
    - singlemin_adjusted: base + $125
    - doublemin_base: base minimum
    - doublemin_adjusted: base + $125
    - paid_in_full_discount_pct: 5% if paid_in_full else 0%
    - (all above prices with _final suffix if paid_in_full is True)
    """
    
    result = {
        "store_code": store["code"],
        "store_name": store["name"],
        "city": store["city"],
        "state": store["state"],
        "tier": store["tier"],
        "singlead_base": store["singlead"],
        "singlead_adjusted": store["singlead"] + PRICING["cushion_singlead"],
        "doublead_base": store["doublead"],
        "doublead_adjusted": store["doublead"] + PRICING["cushion_doublead"],
        "singlemin_base": store["singlemin"],
        "singlemin_adjusted": store["singlemin"] + PRICING["minimum_singlemin"],
        "doublemin_base": store["doublemin"],
        "doublemin_adjusted": store["doublemin"] + PRICING["minimum_doublemin"],
    }
    
    # Apply 5% discount if paid in full
    if paid_in_full:
        discount_pct = PRICING["paid_full_discount"]
        result["paid_in_full_discount_applied"] = True
        result["singlead_final"] = result["singlead_adjusted"] * (1 - discount_pct)
        result["doublead_final"] = result["doublead_adjusted"] * (1 - discount_pct)
        result["singlemin_final"] = result["singlemin_adjusted"] * (1 - discount_pct)
        result["doublemin_final"] = result["doublemin_adjusted"] * (1 - discount_pct)
    else:
        result["paid_in_full_discount_applied"] = False
    
    return result


def format_rate_display(rates: dict, include_discount: bool = False) -> str:
    """Format rate information for display."""
    output = []
    output.append(f"\n📍 {rates['store_name']} | Tier {rates['tier']} | {rates['city']}, {rates['state']}")
    output.append(f"   Store Code: {rates['store_code']}")
    output.append("\n   SINGLE AD:")
    output.append(f"      Base: ${rates['singlead_base']:,.2f}")
    output.append(f"      With Cushion (+$1,325): ${rates['singlead_adjusted']:,.2f}")
    
    if include_discount and rates.get('paid_in_full_discount_applied'):
        output.append(f"      Paid in Full (5% off): ${rates['singlead_final']:,.2f}")
    
    output.append("\n   DOUBLE AD:")
    output.append(f"      Base: ${rates['doublead_base']:,.2f}")
    output.append(f"      With Cushion (+$1,325): ${rates['doublead_adjusted']:,.2f}")
    
    if include_discount and rates.get('paid_in_full_discount_applied'):
        output.append(f"      Paid in Full (5% off): ${rates['doublead_final']:,.2f}")
    
    output.append("\n   MINIMUM (Monthly):")
    output.append(f"      Single Min Base: ${rates['singlemin_base']:,.2f}")
    output.append(f"      Single Min Adjusted (+$125): ${rates['singlemin_adjusted']:,.2f}")
    
    if include_discount and rates.get('paid_in_full_discount_applied'):
        output.append(f"      Single Min Paid in Full: ${rates['singlemin_final']:,.2f}")
    
    output.append(f"      Double Min Base: ${rates['doublemin_base']:,.2f}")
    output.append(f"      Double Min Adjusted (+$125): ${rates['doublemin_adjusted']:,.2f}")
    
    if include_discount and rates.get('paid_in_full_discount_applied'):
        output.append(f"      Double Min Paid in Full: ${rates['doublemin_final']:,.2f}")
    
    return "\n".join(output)


def main():
    """CLI interface for rate lookups."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python rate_calculator.py <city> [chain_name] [--paid-in-full]")
        print("\nExamples:")
        print("  python rate_calculator.py 'Longview' 'Fred Meyer'")
        print("  python rate_calculator.py 'Bend' 'Safeway' --paid-in-full")
        print("  python rate_calculator.py 'Portland'")
        sys.exit(1)
    
    city = sys.argv[1]
    chain_name = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
    paid_in_full = "--paid-in-full" in sys.argv
    
    stores = find_stores_by_city_and_chain(city, chain_name)
    
    if not stores:
        print(f"❌ No stores found for {city}" + (f" with {chain_name}" if chain_name else ""))
        sys.exit(1)
    
    for store in stores:
        rates = calculate_adjusted_rates(store, paid_in_full)
        print(format_rate_display(rates, include_discount=paid_in_full))
    
    print()


if __name__ == "__main__":
    main()
