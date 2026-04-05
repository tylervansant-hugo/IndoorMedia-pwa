#!/usr/bin/env python3
"""
Combine all 2026 renewal data (B2, C1, B1, A2, C2, A1) into pending_renewals.json
"""

import json
import os
import re
import sys
import subprocess

WORKSPACE = os.path.dirname(os.path.dirname(__file__))
OUTPUT = os.path.join(WORKSPACE, 'pwa', 'public', 'data', 'pending_renewals.json')

def clean_price(p):
    if not p or str(p).strip() in ('$-', '$ -', '-', '$', '', '$0.00', '0.00'):
        return 0
    p = str(p).replace('$', '').replace(',', '').replace('(', '').replace(')', '').strip()
    try:
        return abs(float(p))
    except:
        return 0

def format_phone(p):
    if not p:
        return ''
    p = re.sub(r'[^\d]', '', str(p))
    if len(p) == 10:
        return f"({p[:3]}) {p[3:6]}-{p[6:]}"
    elif len(p) == 11 and p[0] == '1':
        return f"({p[1:4]}) {p[4:7]}-{p[7:]}"
    return p

def clean_rep(rep):
    # Remove [SU... : US_Tape] suffix
    rep = re.sub(r'\s*\[SU\d+\s*:\s*US_Tape\]', '', rep).strip()
    # Fix garbled chars
    rep = rep.replace('â€™', "'").replace('â€˜', "'").replace('â€"', '—')
    return rep

def clean_text(t):
    if not t:
        return ''
    t = str(t).replace('â€™', "'").replace('â€˜', "'").replace('â€"', '—').replace('\u00e2\u0080\u0099', "'")
    t = re.sub(r'â\s*€\s*™', "'", t)
    return t.strip()

def process_raw_record(raw, cycle, product='Register Tape'):
    return {
        'zone': raw.get('zone', ''),
        'store': raw.get('store', ''),
        'rep': clean_rep(raw.get('rep', '')),
        'repStatus': raw.get('status', ''),
        'business': clean_text(raw.get('business', '')),
        'accountNumber': raw.get('account', ''),
        'contractNumber': raw.get('contract', ''),
        'contractPrice': clean_price(raw.get('contractPrice', 0)),
        'cycleRevenue': clean_price(raw.get('cycleRevenue', 0)),
        'lateBalance': clean_price(raw.get('lateBalance', 0)),
        'contactName': clean_text(raw.get('contactName', '')),
        'phone': format_phone(raw.get('phone', '')),
        'email': raw.get('email', ''),
        'phone2': format_phone(raw.get('phone2', '')),
        'startDate': raw.get('start', ''),
        'endDate': raw.get('end', ''),
        'runLength': raw.get('runLength', ''),
        'address': clean_text(raw.get('address', '')),
        'city': raw.get('city', ''),
        'state': raw.get('state', ''),
        'zip': raw.get('zip', ''),
        'category': raw.get('category', ''),
        'adSize': raw.get('adSize', ''),
        'exclusive': raw.get('exclusive', 'FALSE') == 'TRUE',
        'renewalContract': clean_text(raw.get('renewal', '')),
        'cycle': cycle,
        'product': raw.get('product', product),
        'impressions': raw.get('impressions', '') if product == 'DigitalBoost' or raw.get('product') == 'DigitalBoost' else ''
    }

def main():
    # First run B2 parser
    print("Loading B2 data...")
    b2_script = os.path.join(os.path.dirname(__file__), 'parse_b2_renewals.py')
    subprocess.run([sys.executable, b2_script], capture_output=True)
    
    with open(OUTPUT) as f:
        all_records = json.load(f)
    b2_count = len(all_records)
    print(f"  B2: {b2_count} records")
    
    # Load other cycles
    cycles = {
        'C1': 'c1_data.json',
        'B1': 'b1_data.json',
        'A2': 'a2_data.json',
        'C2': 'c2_data.json',
        'A1': 'a1_data.json',
    }
    
    for cycle, filename in cycles.items():
        filepath = os.path.join(os.path.dirname(__file__), filename)
        if not os.path.exists(filepath):
            print(f"  ⚠️  {cycle}: {filename} not found")
            continue
        
        with open(filepath) as f:
            raw_data = json.load(f)
        
        for raw in raw_data:
            rec = process_raw_record(raw, cycle, raw.get('product', 'Register Tape'))
            all_records.append(rec)
        
        print(f"  {cycle}: {len(raw_data)} records")
    
    # Save
    with open(OUTPUT, 'w') as f:
        json.dump(all_records, f, indent=2)
    
    # Stats
    from collections import Counter
    total = len(all_records)
    cycles_count = Counter(r.get('cycle', '?') for r in all_records)
    zones = Counter(r.get('zone', '?') for r in all_records)
    reps = Counter(r.get('rep', '?') for r in all_records)
    total_value = sum(r.get('contractPrice', 0) for r in all_records)
    
    print(f"\n{'='*60}")
    print(f"✅ Total records: {total}")
    print(f"\n📊 By cycle: {dict(sorted(cycles_count.items()))}")
    print(f"\n🗺️  By zone: {dict(sorted(zones.items()))}")
    print(f"\n💰 Total contract value: ${total_value:,.2f}")
    print(f"\n👥 Top reps:")
    for rep, count in reps.most_common(15):
        if rep and rep != '?':
            print(f"  {rep}: {count}")
    
    print(f"\n✅ Saved to {OUTPUT}")

if __name__ == '__main__':
    main()
