#!/usr/bin/env python3
"""
Parse ALL Zone 7 renewal data from 8 cycles (B2 + 7 additional PDFs)
and save to pending_renewals.json

This script combines:
- B2 data from the existing parse_b2_renewals.py 
- C1, C2, C4, B1, B4, A1, A2, A4 cycle data extracted from PDFs

Output format matches the B2 parser exactly.
"""

import json
import re
import os
from pathlib import Path

# Get paths
SCRIPT_DIR = Path(__file__).parent
WORKSPACE = SCRIPT_DIR.parent
OUTPUT_PATH = WORKSPACE / 'pwa' / 'public' / 'data' / 'pending_renewals.json'

def clean_price(p):
    """Convert price string to float"""
    if not p or p in ('$-', '$ -', '-', ''):
        return 0
    # Remove $, commas, spaces, parentheses
    cleaned = re.sub(r'[$,\s\(\)]', '', str(p))
    try:
        return float(cleaned)
    except:
        return 0

def format_phone(p):
    """Format phone to (XXX) XXX-XXXX"""
    if not p:
        return ''
    p = re.sub(r'[^\d]', '', str(p))
    if len(p) == 10:
        return f"({p[:3]}) {p[3:6]}-{p[6:]}"
    return p

def clean_rep(rep):
    """Remove [SU...] suffix from rep name"""
    if not rep:
        return ''
    # Remove [SU14624 : US_Tape] style suffixes
    return re.sub(r'\s*\[SU\d+\s*:\s*US_Tape\]', '', rep).strip()

def main():
    renewals = []
    
    # Step 1: Load B2 data from existing parser
    print("Loading B2 data...")
    b2_script = SCRIPT_DIR / 'parse_b2_renewals.py'
    if b2_script.exists():
        # Import and run the B2 parser module
        import sys
        sys.path.insert(0, str(SCRIPT_DIR))
        try:
            from parse_b2_renewals import RAW_DATA as B2_RAW, DIGITAL_DATA as B2_DIGITAL
            
            # Process B2 register tape data
            for r in B2_RAW:
                renewal = {
                    "zone": r["zone"],
                    "store": r["store"],
                    "rep": clean_rep(r["rep"]),
                    "repStatus": r["status"],
                    "business": r["business"],
                    "accountNumber": r["account"],
                    "contractNumber": r["contract"],
                    "contractPrice": clean_price(r["contractPrice"]),
                    "cycleRevenue": clean_price(r["cycleRevenue"]),
                    "lateBalance": clean_price(r["lateBalance"]),
                    "contactName": r["contactName"],
                    "phone": format_phone(r["phone"]),
                    "email": r["email"],
                    "phone2": format_phone(r["phone2"]),
                    "startDate": r["start"],
                    "endDate": r["end"],
                    "runLength": r["runLength"],
                    "address": r["address"],
                    "city": r["city"],
                    "state": r["state"],
                    "zip": r["zip"],
                    "category": r["category"],
                    "adSize": r["adSize"],
                    "exclusive": r["exclusive"] == "TRUE",
                    "renewalContract": r.get("renewal", ""),
                    "cycle": "B2",
                    "product": "Register Tape",
                }
                renewals.append(renewal)
            
            # Process B2 digital data
            for r in B2_DIGITAL:
                renewal = {
                    "zone": r["zone"],
                    "store": "",
                    "rep": clean_rep(r["rep"]),
                    "repStatus": r["status"],
                    "business": r["business"],
                    "accountNumber": r["account"],
                    "contractNumber": r["contract"],
                    "contractPrice": clean_price(r["contractPrice"]),
                    "cycleRevenue": 0,
                    "lateBalance": clean_price(r["lateBalance"]),
                    "contactName": r["contactName"],
                    "phone": format_phone(r["phone"]),
                    "email": r["email"],
                    "phone2": format_phone(r["phone2"]),
                    "startDate": r["start"],
                    "endDate": r["end"],
                    "runLength": r["runLength"],
                    "address": "",
                    "city": "",
                    "state": "",
                    "zip": "",
                    "category": "",
                    "adSize": "",
                    "exclusive": False,
                    "renewalContract": "",
                    "cycle": "B2",
                    "product": r.get("product", "DigitalBoost"),
                    "impressions": r.get("impressions", ""),
                }
                renewals.append(renewal)
            
            print(f"  Loaded {len(renewals)} B2 records")
        except Exception as e:
            print(f"  Warning: Could not load B2 data: {e}")
    
    # Step 2: Load additional cycle data from TSV files
    # These will be populated by extracting the PDFs
    tsv_dir = SCRIPT_DIR / 'tsv_data'
    if tsv_dir.exists():
        for tsv_file in sorted(tsv_dir.glob('*.tsv')):
            cycle = tsv_file.stem  # C1, C2, etc.
            print(f"Loading {cycle} data from {tsv_file.name}...")
            count = 0
            try:
                with open(tsv_file) as f:
                    lines = f.readlines()
                    # Skip header
                    for line in lines[1:]:
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split('\t')
                        if len(parts) < 25:
                            continue
                        
                        table_type = parts[0]
                        
                        if table_type == 'RT':  # Register Tape
                            renewal = {
                                "zone": parts[1],
                                "store": parts[2],
                                "rep": clean_rep(parts[3]),
                                "repStatus": parts[4],
                                "business": parts[5],
                                "accountNumber": parts[6],
                                "contractNumber": parts[7],
                                "contractPrice": clean_price(parts[8]),
                                "cycleRevenue": clean_price(parts[9]),
                                "lateBalance": clean_price(parts[10]),
                                "contactName": parts[11],
                                "phone": format_phone(parts[12]),
                                "email": parts[13],
                                "phone2": format_phone(parts[14]),
                                "startDate": parts[15],
                                "endDate": parts[16],
                                "runLength": parts[17],
                                "address": parts[18],
                                "city": parts[19],
                                "state": parts[20],
                                "zip": parts[21],
                                "category": parts[22],
                                "adSize": parts[23],
                                "exclusive": parts[24] == "TRUE",
                                "renewalContract": parts[25] if len(parts) > 25 else "",
                                "cycle": cycle,
                                "product": "Register Tape",
                            }
                        elif table_type == 'DB':  # DigitalBoost
                            renewal = {
                                "zone": parts[1],
                                "store": "",
                                "rep": clean_rep(parts[3]),
                                "repStatus": parts[4],
                                "business": parts[5],
                                "accountNumber": parts[6],
                                "contractNumber": parts[7],
                                "contractPrice": clean_price(parts[8]),
                                "cycleRevenue": 0,
                                "lateBalance": clean_price(parts[10]),
                                "contactName": parts[11],
                                "phone": format_phone(parts[12]),
                                "email": parts[13],
                                "phone2": format_phone(parts[14]),
                                "startDate": parts[15],
                                "endDate": parts[16],
                                "runLength": parts[17],
                                "address": "",
                                "city": "",
                                "state": "",
                                "zip": "",
                                "category": "",
                                "adSize": "",
                                "exclusive": False,
                                "renewalContract": "",
                                "cycle": cycle,
                                "product": "DigitalBoost",
                                "impressions": parts[9] if parts[9] else "",
                            }
                        else:
                            continue
                        
                        renewals.append(renewal)
                        count += 1
                
                print(f"  Loaded {count} {cycle} records")
            except Exception as e:
                print(f"  Error loading {cycle}: {e}")
    
    # Step 3: Save to JSON
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(renewals, f, indent=2)
    
    # Step 4: Print statistics
    from collections import Counter
    
    print(f"\n{'='*60}")
    print(f"Total renewals: {len(renewals)}")
    print(f"Output: {OUTPUT_PATH}")
    
    cycles = Counter(r['cycle'] for r in renewals)
    print(f"\nBy cycle:")
    for cycle, count in sorted(cycles.items()):
        print(f"  {cycle}: {count}")
    
    zones = Counter(r['zone'] for r in renewals)
    print(f"\nBy zone:")
    for zone, count in sorted(zones.items()):
        print(f"  {zone}: {count}")
    
    reps = Counter(r['rep'] for r in renewals)
    print(f"\nBy rep (top 10):")
    for rep, count in reps.most_common(10):
        print(f"  {rep}: {count}")
    
    products = Counter(r['product'] for r in renewals)
    print(f"\nBy product:")
    for prod, count in sorted(products.items()):
        print(f"  {prod}: {count}")
    
    total_revenue = sum(r['cycleRevenue'] for r in renewals)
    print(f"\nTotal cycle revenue: ${total_revenue:,.2f}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
