#!/usr/bin/env python3
"""
Daily business discovery routine — Phase 1
Extracts store locations from PDF and saves as reference data
"""

import pdfplumber
import csv
from pathlib import Path
from datetime import datetime

STORES_PDF = Path("/Users/tylervansant/.openclaw/media/inbound/file_3---a01472b4-7818-4fe0-a64c-0aa01e51ce04.pdf")
OUTPUT_DIR = Path("/Users/tylervansant/.openclaw/workspace/business_targets")
STORES_CSV = OUTPUT_DIR / "all_stores.csv"

def extract_stores_from_pdf():
    """Extract all store locations and save to CSV."""
    stores = []
    
    with pdfplumber.open(STORES_PDF) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for row in table[2:]:  # Skip headers
                        if row and len(row) >= 9 and row[1] and row[6] and row[7]:
                            stores.append({
                                "store_id": row[1],
                                "chain": row[2],
                                "address": row[5],
                                "city": row[6],
                                "state": row[7],
                                "zip": row[9],
                                "full_address": f"{row[5]}, {row[6]}, {row[7]} {row[9]}",
                                "tape_cases": row[10] if len(row) > 10 else "",
                            })
    
    return stores

def main():
    print("🚀 IndoorMedia Store Location Extraction")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    print("📖 Parsing store data from PDF...")
    stores = extract_stores_from_pdf()
    
    if not stores:
        print("❌ No stores found!")
        return
    
    print(f"✅ Found {len(stores)} stores\n")
    
    # Save to CSV
    print(f"💾 Saving to {STORES_CSV}...")
    with open(STORES_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "store_id", "chain", "address", "city", "state", "zip", "full_address", "tape_cases"
        ])
        writer.writeheader()
        writer.writerows(stores)
    
    print("✅ Store data saved!")
    print(f"\n📊 Summary:")
    
    # Count by state
    by_state = {}
    for store in stores:
        state = store["state"]
        by_state[state] = by_state.get(state, 0) + 1
    
    for state in sorted(by_state.keys()):
        print(f"  {state}: {by_state[state]} stores")
    
    print(f"\nNext steps:")
    print(f"  • Use this CSV as a reference for target discovery")
    print(f"  • Location-based geofence triggers coming soon")
    print(f"  • Full business discovery will use OpenStreetMap API (free)")

if __name__ == "__main__":
    main()
