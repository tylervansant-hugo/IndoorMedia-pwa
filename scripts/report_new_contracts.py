#!/usr/bin/env python3
"""
Generate a report of new contracts by comparing current and previous scans.
Uses composite key (contract_number + store_number + product) to detect new line items,
even when a contract number already existed with different stores.
"""

import json
from pathlib import Path
from datetime import datetime

CONTRACTS_FILE = Path(__file__).parent.parent / "pwa" / "public" / "data" / "contracts.json"
PREVIOUS_CONTRACTS_FILE = Path(__file__).parent.parent / "data" / "contracts_previous.json"

def load_contracts(filepath):
    """Load contracts from JSON."""
    if filepath.exists():
        with open(filepath) as f:
            data = json.load(f)
            return data.get("contracts", data) if isinstance(data, dict) else data
    return []

def contract_key(c):
    """Unique key for a contract line item."""
    return (
        c.get("contract_number", ""),
        c.get("store_number", ""),
        c.get("product_description", ""),
        str(c.get("total_amount", 0))
    )

def main():
    current = load_contracts(CONTRACTS_FILE)
    previous = load_contracts(PREVIOUS_CONTRACTS_FILE)
    
    current_keys = {contract_key(c) for c in current}
    previous_keys = {contract_key(c) for c in previous}
    
    new_keys = current_keys - previous_keys
    removed_keys = previous_keys - current_keys
    
    # Find the actual new contract objects
    new_contracts = [c for c in current if contract_key(c) in new_keys]
    # Also track new contract NUMBERS (not just line items)
    new_contract_nums = {c.get("contract_number") for c in new_contracts} - {c.get("contract_number") for c in previous}
    
    # Sort: truly new contract numbers first, then new line items from existing contracts
    new_contracts.sort(key=lambda c: (
        0 if c.get("contract_number") in new_contract_nums else 1,
        c.get("contract_number", ""),
        c.get("store_number", "")
    ))
    
    print(f"📊 Contracts Report ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print(f"   Previous scan: {len(previous)} line items")
    print(f"   Current scan: {len(current)} line items")
    print(f"   New line items: {len(new_keys)}")
    if new_contract_nums:
        print(f"   New contract numbers: {len(new_contract_nums)}")
    
    if new_contracts:
        # Group by contract number
        by_contract = {}
        for c in new_contracts:
            num = c.get("contract_number", "?")
            by_contract.setdefault(num, []).append(c)
        
        print(f"\n📬 NEW CONTRACTS ({len(new_contracts)} line items across {len(by_contract)} contracts):")
        
        total_new_revenue = 0
        for num, items in by_contract.items():
            is_brand_new = num in new_contract_nums
            tag = "🆕 NEW" if is_brand_new else "➕ Added stores"
            biz = items[0].get("business_name", "?")
            rep = items[0].get("sales_rep", "?")
            date = items[0].get("date", "").split(" ")[0] if items[0].get("date") else "?"
            contract_total = sum(c.get("total_amount", 0) for c in items)
            total_new_revenue += contract_total
            
            print(f"\n   {tag} {num} | {biz} | {rep} | ${contract_total:,.0f} | {date}")
            for c in items:
                store = c.get("store_name", "")
                snum = c.get("store_number", "")
                zone = c.get("zone", "")
                product = c.get("product_description", "")
                amt = c.get("total_amount", 0)
                store_info = f"{store} #{snum} ({zone})" if snum else "(no store)"
                print(f"      • {store_info} | {product} | ${amt:,.0f}")
        
        print(f"\n   💰 Total new revenue: ${total_new_revenue:,.0f}")
    else:
        print("\n✅ No new contracts")
    
    # Save current as previous for next run
    with open(PREVIOUS_CONTRACTS_FILE, 'w') as f:
        json.dump({"contracts": current}, f, indent=2, default=str)
    
    return len(new_contracts)

if __name__ == "__main__":
    main()
