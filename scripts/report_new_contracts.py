#!/usr/bin/env python3
"""
Generate a report of TRULY new contracts by comparing current and previous scans.
Compares contract_number to identify new ones.
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

def get_contract_numbers(contracts):
    """Get set of contract numbers."""
    return set(c.get("contract_number") for c in contracts if c.get("contract_number"))

def main():
    current = load_contracts(CONTRACTS_FILE)
    previous = load_contracts(PREVIOUS_CONTRACTS_FILE)
    
    current_nums = get_contract_numbers(current)
    previous_nums = get_contract_numbers(previous)
    
    new_nums = current_nums - previous_nums
    
    print(f"📊 Contracts Report ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print(f"   Previous scan: {len(previous)} contracts")
    print(f"   Current scan: {len(current)} contracts")
    print(f"   New contracts: {len(new_nums)}")
    
    if new_nums:
        print(f"\n📬 NEW CONTRACTS ({len(new_nums)}):")
        new_contracts = [c for c in current if c.get("contract_number") in new_nums]
        # Sort by extracted_at (contract date)
        new_contracts = sorted(new_contracts, key=lambda x: x.get("extracted_at", ""), reverse=True)
        for c in new_contracts:
            biz = c.get("business_name", "?")
            rep = c.get("sales_rep", "?")
            amount = c.get("total_amount", 0)
            date = c.get("extracted_at", "").split("T")[0] if c.get("extracted_at") else "?"
            print(f"   • {c['contract_number']} | {biz} ({rep}) | ${amount:,.0f} | {date}")
    else:
        print("\n✅ No new contracts")
    
    # Save current as previous for next run
    with open(PREVIOUS_CONTRACTS_FILE, 'w') as f:
        json.dump({"contracts": current}, f, indent=2, default=str)
    
    return len(new_nums)

if __name__ == "__main__":
    main()
