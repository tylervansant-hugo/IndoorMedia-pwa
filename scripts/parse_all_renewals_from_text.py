#!/usr/bin/env python3
"""
Parse ALL Zone 7 renewal PDFs using pdfplumber and combine into pending_renewals.json.
Falls back to raw text parsing if pdfplumber unavailable.
"""

import json
import os
import re
import sys
import subprocess

OUTPUT = os.path.join(os.path.dirname(__file__), '..', 'pwa', 'public', 'data', 'pending_renewals.json')

# PDF files and their cycle codes
PDFS = {
    'B2': '/Users/tylervansant/.openclaw/media/inbound/ZONE_7_B2_2026---34102ebf-ba90-4cf9-ab5d-0701a9bc94d9.pdf',
    'C1': '/Users/tylervansant/.openclaw/media/inbound/ZONE_7_C1_2026---245df008-f83b-4ea9-a617-b8190cb84a72.pdf',
    'C4': '/Users/tylervansant/.openclaw/media/inbound/ZONE_7_C4_2025---037ca158-1a5e-48d0-9c20-a560083a8643.pdf',
    'B1': '/Users/tylervansant/.openclaw/media/inbound/ZONE_7_B1_2026---ae4e374e-0f97-49e3-b98d-0c61d75b2a22.pdf',
    'A2': '/Users/tylervansant/.openclaw/media/inbound/Zone_7_A2_2026---d24f9693-aa8b-414a-8def-957cfda9684e.pdf',
    'C2': '/Users/tylervansant/.openclaw/media/inbound/ZONE_7_C2_2026---a6ecf32b-2ab8-4edf-b758-e453579fa236.pdf',
    'B4': '/Users/tylervansant/.openclaw/media/inbound/ZONE_7_B4_2025---bb3bdc2c-366c-49eb-9b1a-bfa9a4c2354f.pdf',
    'A1': '/Users/tylervansant/.openclaw/media/inbound/ZONE_7_A1_2026---e8e16115-0a02-4b62-852b-ff203a940d8e.pdf',
    'A4': '/Users/tylervansant/.openclaw/media/inbound/ZONE_7_A4_2025---18a28afd-7409-4718-9409-705e1b52638c.pdf',
}

def clean_price(p):
    if not p or p.strip() in ('$-', '$ -', '-', '$', ''):
        return 0
    p = p.replace('$', '').replace(',', '').replace('(', '').replace(')', '').strip()
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
    return p

def clean_rep(rep):
    # Remove [SU... : US_Tape] suffix
    rep = re.sub(r'\s*\[SU\d+\s*:\s*US_Tape\]', '', rep).strip()
    # Fix garbled chars
    rep = rep.replace('â€™', "'").replace('â€˜', "'").replace('â€"', '—').replace('â€"', '–')
    return rep

def clean_text(t):
    if not t:
        return ''
    t = t.replace('â€™', "'").replace('â€˜', "'").replace('â€"', '—').replace('\u00e2\u0080\u0099', "'")
    t = re.sub(r'â\s*€\s*™', "'", t)
    return t.strip()

def extract_text_from_pdf(pdf_path):
    """Extract text using pdftotext."""
    try:
        result = subprocess.run(['pdftotext', '-raw', pdf_path, '-'], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return result.stdout
    except:
        pass
    return ''

def parse_row_from_text(text, cycle):
    """Try to parse renewal data rows from raw text. This is a heuristic parser."""
    records = []
    
    # Pattern: zone store_id rep_name ... 
    # The text is messy from PDF extraction, so we use the known zone patterns
    zone_pattern = r'(07[WXYZ])'
    store_pattern = r'([A-Z]{2,4}\d{2}[A-Z]-\d{4})'
    
    lines = text.split('\n')
    current_zone = ''
    
    for line in lines:
        line = clean_text(line)
        if not line:
            continue
        
        # Try to find store IDs in the line
        store_match = re.search(store_pattern, line)
        zone_match = re.search(zone_pattern, line)
        
        if store_match and zone_match:
            store_id = store_match.group(1)
            zone = zone_match.group(1)
            
            # Try to extract email (most reliable anchor)
            email_match = re.search(r'[\w.+-]+@[\w.-]+\.\w+', line)
            email = email_match.group(0) if email_match else ''
            
            # Try to extract phone numbers
            phones = re.findall(r'\b\d{10}\b', line.replace('(', '').replace(')', '').replace('-', '').replace(' ', ''))
            phone = format_phone(phones[0]) if phones else ''
            phone2 = format_phone(phones[1]) if len(phones) > 1 else ''
            
            # Try to extract dollar amounts
            prices = re.findall(r'\$[\d,]+\.?\d*', line)
            
            # Try to extract dates
            dates = re.findall(r'\d{1,2}/\d{1,2}/\d{2,4}', line)
            
            record = {
                'zone': zone,
                'store': store_id,
                'rep': '',
                'repStatus': '',
                'business': '',
                'accountNumber': '',
                'contractNumber': '',
                'contractPrice': clean_price(prices[0]) if prices else 0,
                'cycleRevenue': clean_price(prices[1]) if len(prices) > 1 else 0,
                'lateBalance': clean_price(prices[2]) if len(prices) > 2 else 0,
                'contactName': '',
                'phone': phone,
                'email': email,
                'phone2': phone2,
                'startDate': dates[0] if dates else '',
                'endDate': dates[1] if len(dates) > 1 else '',
                'runLength': '',
                'address': '',
                'city': '',
                'state': '',
                'zip': '',
                'category': '',
                'adSize': 'Single' if 'Single' in line else ('Double' if 'Double' in line else ''),
                'exclusive': 'TRUE' in line,
                'renewalContract': '',
                'cycle': cycle,
                'product': 'Register Tape',
            }
            records.append(record)
    
    return records


def main():
    # First, run the B2 parser which has clean hardcoded data
    print("Loading B2 data from existing parser...")
    b2_script = os.path.join(os.path.dirname(__file__), 'parse_b2_renewals.py')
    subprocess.run([sys.executable, b2_script], capture_output=True)
    
    with open(OUTPUT) as f:
        all_records = json.load(f)
    print(f"B2 records loaded: {len(all_records)}")
    
    # For other cycles, try PDF extraction
    for cycle, pdf_path in PDFS.items():
        if cycle == 'B2':
            continue  # Already loaded
        if not os.path.exists(pdf_path):
            print(f"⚠️  {cycle}: PDF not found at {pdf_path}")
            continue
        
        print(f"\nProcessing {cycle}...")
        text = extract_text_from_pdf(pdf_path)
        if text:
            records = parse_row_from_text(text, cycle)
            all_records.extend(records)
            print(f"  {cycle}: {len(records)} records extracted")
        else:
            print(f"  {cycle}: Could not extract text")
    
    # Save
    with open(OUTPUT, 'w') as f:
        json.dump(all_records, f, indent=2)
    
    # Stats
    from collections import Counter
    total = len(all_records)
    cycles = Counter(r.get('cycle', '?') for r in all_records)
    zones = Counter(r.get('zone', '?') for r in all_records)
    reps = Counter(r.get('rep', '?') for r in all_records)
    
    print(f"\n{'='*60}")
    print(f"Total records: {total}")
    print(f"\nBy cycle: {dict(sorted(cycles.items()))}")
    print(f"\nBy zone: {dict(sorted(zones.items()))}")
    print(f"\nTop reps:")
    for rep, count in reps.most_common(15):
        print(f"  {rep}: {count}")


if __name__ == '__main__':
    main()
