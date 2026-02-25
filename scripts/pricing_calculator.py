#!/usr/bin/env python3
"""
Calculate pricing with payment plans for IndoorMedia stores.
Displays per-installment amount AND total for each plan.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Optional

WORKSPACE = Path(__file__).parent.parent
DATA_DIR = WORKSPACE / "data" / "store-rates"
STORES_FILE = DATA_DIR / "stores.json"


def load_stores() -> Dict:
    """Load stores database by store number."""
    with open(STORES_FILE) as f:
        stores_list = json.load(f)
    
    stores = {}
    for store in stores_list:
        stores[store["StoreName"]] = store
    
    return stores


def calculate_pricing(store: Dict, ad_type: str = "single") -> Dict:
    """
    Calculate pricing with payment plans.
    
    Payment structure:
    - Monthly: (base + $125) ÷ 12 = per month, total = base + $125
    - 3-month: ((base × 0.90) + $125) ÷ 3 = per payment, total = (base × 0.90) + $125
    - 6-month: ((base × 0.925) + $125) ÷ 6 = per payment, total = (base × 0.925) + $125
    - Paid-in-full: (base × 0.85) + $125 = one payment
    """
    
    # Get base price
    if ad_type.lower() == "double":
        base = store["DoubleAd"]
    else:
        base = store["SingleAd"]
    
    PRODUCTION = 125.0
    
    # Calculate each plan
    plans = {}
    
    # Monthly: divide by 12
    monthly_total = base + PRODUCTION
    monthly_per = monthly_total / 12
    plans["monthly"] = {
        "per_installment": round(monthly_per, 2),
        "installments": 12,
        "total": round(monthly_total, 2),
        "display": f"${monthly_per:.2f}/month × 12 = ${monthly_total:.2f}"
    }
    
    # 3-month: 10% discount on base, then add production
    three_month_total = (base * 0.90) + PRODUCTION
    three_month_per = three_month_total / 3
    plans["3month"] = {
        "per_installment": round(three_month_per, 2),
        "installments": 3,
        "total": round(three_month_total, 2),
        "display": f"${three_month_per:.2f}/payment × 3 = ${three_month_total:.2f} (10% off)"
    }
    
    # 6-month: 7.5% discount on base, then add production
    six_month_total = (base * 0.925) + PRODUCTION
    six_month_per = six_month_total / 6
    plans["6month"] = {
        "per_installment": round(six_month_per, 2),
        "installments": 6,
        "total": round(six_month_total, 2),
        "display": f"${six_month_per:.2f}/payment × 6 = ${six_month_total:.2f} (7.5% off)"
    }
    
    # Paid-in-full: 15% discount on base, then add production
    paid_full_total = (base * 0.85) + PRODUCTION
    plans["paid_full"] = {
        "per_installment": round(paid_full_total, 2),
        "installments": 1,
        "total": round(paid_full_total, 2),
        "display": f"${paid_full_total:.2f} (one payment, 15% off)"
    }
    
    return {
        "store_number": store["StoreName"],
        "store_name": store["GroceryChain"],
        "city": store["City"],
        "state": store["State"],
        "address": store["Address"],
        "base_price": base,
        "ad_type": ad_type,
        "plans": plans
    }


def format_output(pricing: Dict) -> str:
    """Format pricing for display."""
    lines = [
        f"📍 {pricing['store_name']} | {pricing['city']}, {pricing['state']}",
        f"📦 Store: {pricing['store_number']}",
        f"💰 Base Price: ${pricing['base_price']:.2f} ({pricing['ad_type']} ad)",
        "",
        "💳 Payment Plans:",
    ]
    
    for plan_name, plan in pricing["plans"].items():
        lines.append(f"  • {plan['display']}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: pricing_calculator.py <store_number> [ad_type]")
        print("Example: pricing_calculator.py FME07Y-0165 single")
        sys.exit(1)
    
    store_num = sys.argv[1].upper()
    ad_type = sys.argv[2].lower() if len(sys.argv) > 2 else "single"
    
    stores = load_stores()
    
    if store_num not in stores:
        print(f"❌ Store {store_num} not found")
        sys.exit(1)
    
    store = stores[store_num]
    pricing = calculate_pricing(store, ad_type)
    
    # Output as JSON for bot integration
    print(json.dumps(pricing, indent=2))
