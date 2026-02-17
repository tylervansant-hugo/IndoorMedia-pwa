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


def calculate_adjusted_rates(store: dict, lowest_price: bool = False) -> dict:
    """
    Calculate adjusted rates for a store.
    
    If lowest_price=False:
    - Standard rates with $1,325 cushion on ad rates
    - $125 floor on minimums
    
    If lowest_price=True:
    - Shows pricing WITHOUT cushion
    - Multiple payment term options:
      * Monthly: base + $125
      * 6-month: base * 0.925 + $125 (7.5% off)
      * 3-month: base * 0.90 + $125 (10% off)
      * Paid in full: base * 0.85 + $125 (15% off)
    """
    
    result = {
        "store_code": store["code"],
        "store_name": store["name"],
        "city": store["city"],
        "state": store["state"],
        "tier": store["tier"],
    }
    
    if not lowest_price:
        # Standard rates WITH cushion
        result["singlead_base"] = store["singlead"]
        result["singlead_with_cushion"] = store["singlead"] + PRICING["cushion_singlead"]
        result["doublead_base"] = store["doublead"]
        result["doublead_with_cushion"] = store["doublead"] + PRICING["cushion_doublead"]
        result["singlemin_base"] = store["singlemin"]
        result["singlemin_with_floor"] = store["singlemin"] + PRICING["minimum_singlemin"]
        result["doublemin_base"] = store["doublemin"]
        result["doublemin_with_floor"] = store["doublemin"] + PRICING["minimum_doublemin"]
    else:
        # Lowest price options WITHOUT cushion, multiple payment terms
        floor = PRICING["minimum_singlemin"]
        
        result["singlead_monthly"] = store["singlead"] + floor
        result["singlead_6month"] = store["singlead"] * 0.925 + floor
        result["singlead_3month"] = store["singlead"] * 0.90 + floor
        result["singlead_paid_in_full"] = store["singlead"] * 0.85 + floor
        
        result["doublead_monthly"] = store["doublead"] + floor
        result["doublead_6month"] = store["doublead"] * 0.925 + floor
        result["doublead_3month"] = store["doublead"] * 0.90 + floor
        result["doublead_paid_in_full"] = store["doublead"] * 0.85 + floor
        
        result["min_monthly"] = store["singlemin"] + floor
        result["min_6month"] = store["singlemin"] * 0.925 + floor
        result["min_3month"] = store["singlemin"] * 0.90 + floor
        result["min_paid_in_full"] = store["singlemin"] * 0.85 + floor
    
    return result


def format_rate_display(rates: dict, lowest_price: bool = False) -> str:
    """Format rate information for display."""
    output = []
    output.append(f"\n📍 {rates['store_name']} | Tier {rates['tier']} | {rates['city']}, {rates['state']}")
    output.append(f"   Store Code: {rates['store_code']}")
    
    if not lowest_price:
        # Standard rates display
        output.append("\n   SINGLE AD:")
        output.append(f"      Base: ${rates['singlead_base']:,.2f}")
        output.append(f"      With Cushion (+$1,325): ${rates['singlead_with_cushion']:,.2f}")
        
        output.append("\n   DOUBLE AD:")
        output.append(f"      Base: ${rates['doublead_base']:,.2f}")
        output.append(f"      With Cushion (+$1,325): ${rates['doublead_with_cushion']:,.2f}")
        
        output.append("\n   MINIMUM (Monthly):")
        output.append(f"      Single Min: ${rates['singlemin_with_floor']:,.2f} (base ${rates['singlemin_base']:,.2f} + $125)")
        output.append(f"      Double Min: ${rates['doublemin_with_floor']:,.2f} (base ${rates['doublemin_base']:,.2f} + $125)")
    else:
        # Lowest price display with payment term options
        output.append("\n   SINGLE AD (Lowest Price):")
        output.append(f"      Monthly: ${rates['singlead_monthly']:,.2f}")
        output.append(f"      6-Month (7.5% off): ${rates['singlead_6month']:,.2f}")
        output.append(f"      3-Month (10% off): ${rates['singlead_3month']:,.2f}")
        output.append(f"      Paid in Full (15% off): ${rates['singlead_paid_in_full']:,.2f} ⭐")
        
        output.append("\n   DOUBLE AD (Lowest Price):")
        output.append(f"      Monthly: ${rates['doublead_monthly']:,.2f}")
        output.append(f"      6-Month (7.5% off): ${rates['doublead_6month']:,.2f}")
        output.append(f"      3-Month (10% off): ${rates['doublead_3month']:,.2f}")
        output.append(f"      Paid in Full (15% off): ${rates['doublead_paid_in_full']:,.2f} ⭐")
        
        output.append("\n   MONTHLY MINIMUM (Lowest Price):")
        output.append(f"      Monthly: ${rates['min_monthly']:,.2f}")
        output.append(f"      6-Month (7.5% off): ${rates['min_6month']:,.2f}")
        output.append(f"      3-Month (10% off): ${rates['min_3month']:,.2f}")
        output.append(f"      Paid in Full (15% off): ${rates['min_paid_in_full']:,.2f} ⭐")
    
    return "\n".join(output)


def main():
    """CLI interface for rate lookups."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python rate_calculator.py <city> [chain_name] [--standard|--lowest]")
        print("\nOptions:")
        print("  --standard   Show rates with $1,325 cushion (default)")
        print("  --lowest     Show lowest prices with payment term discounts")
        print("\nExamples:")
        print("  python rate_calculator.py 'Longview' 'Fred Meyer'")
        print("  python rate_calculator.py 'Longview' 'Fred Meyer' --lowest")
        print("  python rate_calculator.py 'Bend'")
        sys.exit(1)
    
    city = sys.argv[1]
    chain_name = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
    show_lowest = "--lowest" in sys.argv
    
    stores = find_stores_by_city_and_chain(city, chain_name)
    
    if not stores:
        print(f"❌ No stores found for {city}" + (f" with {chain_name}" if chain_name else ""))
        sys.exit(1)
    
    for store in stores:
        rates = calculate_adjusted_rates(store, lowest_price=show_lowest)
        print(format_rate_display(rates, lowest_price=show_lowest))
    
    print()


if __name__ == "__main__":
    main()
