#!/usr/bin/env python3
"""
Generate a report of new contracts by checking extraction timestamp.
If a contract was extracted in the last 25 hours, it's NEW (caught by today's scan).
"""

import json
from pathlib import Path
from datetime import datetime, timedelta

CONTRACTS_FILE = Path(__file__).parent.parent / "pwa" / "public" / "data" / "contracts.json"

def main():
    with open(CONTRACTS_FILE) as f:
        current = json.load(f)
    
    contracts = current.get("contracts", [])
    
    # Find contracts extracted in the last 25 hours (roughly: today's scan window)
    cutoff = datetime.now() - timedelta(hours=25)
    
    new_contracts = []
    for c in contracts:
        extracted_str = c.get("extracted_at", "")
        if extracted_str:
            try:
                extracted = datetime.fromisoformat(extracted_str.replace("Z", "+00:00"))
                if extracted > cutoff:
                    new_contracts.append(c)
            except:
                pass
    
    # Group by contract number
    by_contract = {}
    for c in new_contracts:
        num = c.get("contract_number", "?")
        by_contract.setdefault(num, []).append(c)
    
    # Sort by contract number (newest first, roughly)
    by_contract = dict(sorted(by_contract.items(), reverse=True))
    
    print(f"📊 Contracts Report ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print(f"   Total in system: {len(contracts)} line items")
    print(f"   Extracted today: {len(new_contracts)} line items")
    print(f"   New unique contracts: {len(by_contract)}")
    
    if by_contract:
        print(f"\n✅ {len(by_contract)} NEW CONTRACTS:")
        
        total_revenue = 0
        for num, items in by_contract.items():
            biz = items[0].get("business_name", "?")
            rep = items[0].get("sales_rep", "?")
            contract_total = sum(c.get("total_amount", 0) for c in items)
            total_revenue += contract_total
            
            print(f"\n   {num} | {biz} | {rep} | ${contract_total:,.0f}")
            for c in items:
                store = c.get("store_name", "")
                product = c.get("product_description", "")
                amt = c.get("total_amount", 0)
                if product:
                    print(f"      • {product} | ${amt:,.0f}")
        
        print(f"\n   💰 Total new revenue: ${total_revenue:,.0f}")
    else:
        print(f"\n✅ No new contracts extracted in the last 25 hours")

if __name__ == "__main__":
    main()
