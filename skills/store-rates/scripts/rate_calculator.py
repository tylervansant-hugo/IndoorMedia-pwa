#!/usr/bin/env python3
"""
Store Rate Calculator - Query store rates with annual pricing + payment breakdowns
"""

import json
import sys
from pathlib import Path

# Load store data and city reference
script_dir = Path(__file__).parent
data_file = script_dir.parent / "references" / "store_data.json"
city_ref_file = script_dir.parent / "references" / "city_chains.json"

with open(data_file, 'r') as f:
    data = json.load(f)

with open(city_ref_file, 'r') as f:
    city_ref = json.load(f)

STORES = data["stores"]
PRICING = data["pricing_adjustments"]
STORES_BY_CODE = city_ref["stores_by_code"]
CITY_CHAINS = city_ref["city_chains"]

# Discount structure for payment terms
DISCOUNTS = {
    "monthly": 0.00,        # No discount, 12 installments
    "3month": 0.10,         # 10% off, 3 installments
    "6month": 0.075,        # 7.5% off, 6 installments
    "paid_full": 0.15,      # 15% off, 1 installment
}


def find_stores_by_city_and_chain(city: str, chain_name: str) -> list:
    """Find stores by city and chain name."""
    city_title = city.title()
    chain_title = chain_name.title()
    
    results = []
    
    # Search through store codes we have city info for
    for store_id, store_info in STORES_BY_CODE.items():
        if store_info['city'] == city_title and store_info['chain'] == chain_title:
            # Find the matching rate in STORES
            for rate_store in STORES:
                # Match by name and tier if possible
                if rate_store["name"] == chain_title:
                    result_store = rate_store.copy()
                    result_store["actual_city"] = city_title
                    result_store["actual_state"] = store_info['state']
                    results.append(result_store)
                    break
    
    return results


def find_stores_by_street(street_name: str) -> list:
    """Find stores by street name (case-insensitive substring match)."""
    street_lower = street_name.lower()
    results = []
    
    for store in STORES:
        # Search in city field (which may contain address fragments)
        city = store.get('city', '').lower()
        address = store.get('address', '').lower()
        
        # Match if street name appears in city or address
        if street_lower in city or street_lower in address:
            result_store = store.copy()
            # Add state from city reference if available
            for store_id, store_info in STORES_BY_CODE.items():
                if store_info['chain'] == store['name'] and store_info['city'].lower() in city:
                    result_store['actual_state'] = store_info['state']
                    break
            results.append(result_store)
    
    return results


def calculate_annual_price(monthly_base: float, discount_rate: float) -> float:
    """Calculate annual price with discount applied."""
    annual = monthly_base * 12
    discounted_annual = annual * (1 - discount_rate)
    return discounted_annual


def calculate_payment_plans(store: dict, ad_type: str) -> dict:
    """
    Calculate payment breakdowns for all payment plans.
    Pricing formula: base + $125 production charge, then apply discounts for prepaid.
    
    ad_type: "single" or "double"
    Returns dict with all payment plan details
    """
    # Get base annual price from store data
    if ad_type == "single":
        base_price = store["singlead"]
    else:
        base_price = store["doublead"]
    
    # Production charge
    production_charge = 125.0
    
    plans = {}
    
    # Monthly (12 installments, no discount): base + $125
    annual_total = base_price + production_charge
    plans["monthly"] = {
        "annual_total": round(annual_total, 2),
        "installment_amount": round(annual_total / 12, 2),
        "num_installments": 12,
        "discount": 0,
        "description": "12 monthly payments"
    }
    
    # 3-month prepaid (3 installments, 10% off): (base × 0.90) + $125
    annual_total = (base_price * 0.90) + production_charge
    plans["3month"] = {
        "annual_total": round(annual_total, 2),
        "installment_amount": round(annual_total / 3, 2),
        "num_installments": 3,
        "discount": 10,
        "description": "3 payments (10% off)"
    }
    
    # 6-month prepaid (6 installments, 7.5% off): (base × 0.925) + $125
    annual_total = (base_price * 0.925) + production_charge
    plans["6month"] = {
        "annual_total": round(annual_total, 2),
        "installment_amount": round(annual_total / 6, 2),
        "num_installments": 6,
        "discount": 7.5,
        "description": "6 payments (7.5% off)"
    }
    
    # Paid in full (1 payment, 15% off): (base × 0.85) + $125
    annual_total = (base_price * 0.85) + production_charge
    plans["paid_full"] = {
        "annual_total": round(annual_total, 2),
        "installment_amount": round(annual_total, 2),
        "num_installments": 1,
        "discount": 15,
        "description": "One upfront payment (15% off)"
    }
    
    return plans


def format_rate_display(store: dict, ad_type: str = "single") -> str:
    """Format rate information with annual pricing and payment options."""
    ad_label = "Single Ad" if ad_type == "single" else "Double Ad"
    plans = calculate_payment_plans(store, ad_type)
    
    output = []
    output.append(f"\n📍 {store['name']} | {store['tier']} cycle")
    output.append(f"   {ad_label} - Year-long Campaign\n")
    
    for plan_key in ["monthly", "3month", "6month", "paid_full"]:
        plan = plans[plan_key]
        star = " ⭐" if plan_key == "paid_full" else ""
        
        if plan["num_installments"] == 1:
            output.append(f"   {plan['description']}:")
            output.append(f"      ${plan['annual_total']:,.2f}{star}")
        else:
            output.append(f"   {plan['description']}:")
            output.append(f"      ${plan['installment_amount']:,.2f}/installment (${plan['annual_total']:,.2f} total){star}")
    
    return "\n".join(output)


def format_json_response(store: dict, ad_type: str) -> dict:
    """Return structured JSON for bot usage."""
    ad_label = "SingleAd" if ad_type == "single" else "DoubleAd"
    plans = calculate_payment_plans(store, ad_type)
    
    return {
        "store_name": store["name"],
        "store_code": store["code"],
        "tier": store["tier"],
        "ad_type": ad_label,
        "plans": plans
    }


def list_cities():
    """List all available cities."""
    cities = sorted(CITY_CHAINS.keys())
    print("Available cities:")
    for city in cities:
        chains = ", ".join(sorted(CITY_CHAINS[city]))
        print(f"  {city}: {chains}")


def main():
    """CLI interface for rate lookups."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python rate_calculator.py <city> <chain> <ad_type> [--json]")
        print("  python rate_calculator.py --list-cities")
        print("  python rate_calculator.py --search-street '<street name>'")
        print("\nParameters:")
        print("  city       Store city (e.g., 'Longview')")
        print("  chain      Store chain (e.g., 'Fred Meyer', 'Safeway')")
        print("  ad_type    'single' or 'double'")
        print("  --json     Return JSON instead of formatted text")
        print("\nExamples:")
        print("  python rate_calculator.py Longview 'Fred Meyer' single")
        print("  python rate_calculator.py Longview Safeway double --json")
        print("  python rate_calculator.py --list-cities")
        print("  python rate_calculator.py --search-street 'Walker Rd'")
        sys.exit(1)
    
    # Handle list-cities flag
    if sys.argv[1] == "--list-cities":
        list_cities()
        sys.exit(0)
    
    # Handle street search
    if sys.argv[1] == "--search-street":
        if len(sys.argv) < 3:
            print("❌ Missing street name. Use: python rate_calculator.py --search-street '<street name>'")
            sys.exit(1)
        street = sys.argv[2]
        stores = find_stores_by_street(street)
        if stores:
            # Return JSON array of matching stores with key info
            results = []
            for store in stores:
                results.append({
                    'code': store.get('code'),
                    'name': store.get('name'),
                    'city': store.get('city'),
                    'state': store.get('state'),
                    'tier': store.get('tier'),
                    'singlead': store.get('singlead'),
                    'doublead': store.get('doublead')
                })
            print(json.dumps(results))
        else:
            print(json.dumps([]))
        sys.exit(0)
    
    if len(sys.argv) < 3:
        print("❌ Missing parameters. Use: python rate_calculator.py <city> <chain> [single|double] [--json]")
        sys.exit(1)
    
    city = sys.argv[1]
    chain = sys.argv[2]
    ad_type = sys.argv[3].lower() if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else "single"
    return_json = "--json" in sys.argv
    
    if ad_type not in ["single", "double"]:
        print("❌ ad_type must be 'single' or 'double'")
        sys.exit(1)
    
    stores = find_stores_by_city_and_chain(city, chain)
    
    if not stores:
        print(f"❌ No stores found for {city} {chain}")
        print(f"\nTip: Use 'python rate_calculator.py --list-cities' to see available cities")
        sys.exit(1)
    
    # Deduplicate by tier (in case there are multiple locations)
    seen_tiers = set()
    for store in stores:
        if store["tier"] not in seen_tiers:
            if return_json:
                print(json.dumps(format_json_response(store, ad_type), indent=2))
            else:
                print(format_rate_display(store, ad_type))
            seen_tiers.add(store["tier"])
    
    if not return_json:
        print()


if __name__ == "__main__":
    main()
