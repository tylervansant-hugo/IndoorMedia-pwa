#!/usr/bin/env python3
"""
Contract-to-Calendar Pipeline
Monitors Gmail for "IndoorMedia Contract Signed" emails,
extracts contract details from PDF, and creates calendar events.

Calendar Events Created:
1. Install - 10 days before Est. Start date
2. Audit - 45 days after install
3. Check-ins - every 45 days after audit (ongoing)
4. Renewal - 8 months from install date

All events invite the sales rep + Tyler.
"""

import json
import re
import subprocess
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
CONTRACTS_DIR = WORKSPACE / "data" / "contracts"
PROCESSED_FILE = WORKSPACE / "data" / "contracts" / "processed.json"
TYLER_EMAIL = "tyler.vansant@indoormedia.com"
CALENDAR_ID = TYLER_EMAIL  # Use Tyler's calendar
CONTRACTS_JSON = WORKSPACE / "data" / "contracts.json"


def save_to_contracts_json(contract):
    """Save contract details to the main contracts.json for the bot to use."""
    # Load existing
    if CONTRACTS_JSON.exists():
        with open(CONTRACTS_JSON) as f:
            data = json.load(f)
    else:
        data = {"contracts": []}
    
    # Check if already exists
    contract_num = contract.get('contract_num', '')
    for existing in data.get("contracts", []):
        if existing.get("contract_number") == contract_num:
            # Update existing with any new/better fields
            existing.update({
                "contact_email": contract.get('customer_email') or existing.get('contact_email'),
                "contact_phone": contract.get('customer_phone') or existing.get('contact_phone'),
                "contact_name": contract.get('customer_name') or existing.get('contact_name'),
                "address": contract.get('customer_address', '') or existing.get('address', ''),
                "total_amount": contract.get('total') or existing.get('total_amount', 0),
                "product_description": contract.get('ad_type') or existing.get('product_description'),
            })
            with open(CONTRACTS_JSON, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            return
    
    # New contract entry
    entry = {
        "contract_number": contract_num,
        "date": contract.get('contract_date', ''),
        "business_name": contract.get('business_name', ''),
        "contact_name": contract.get('customer_name', ''),
        "contact_email": contract.get('customer_email', ''),
        "contact_phone": contract.get('customer_phone', ''),
        "sales_rep": contract.get('rep_name', ''),
        "store_name": contract.get('store_chain', ''),
        "store_number": contract.get('store_number', ''),
        "product_description": contract.get('ad_type', ''),
        "total_amount": contract.get('total', 0),
        "payment_date": contract.get('contract_date', ''),
        "address": contract.get('customer_address', ''),
        "customer_city_state": contract.get('customer_city_state', ''),
        "extracted_at": datetime.now().isoformat(),
    }
    data["contracts"].append(entry)
    
    with open(CONTRACTS_JSON, 'w') as f:
        json.dump(data, f, indent=2, default=str)

# Ensure dirs exist
CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)


def load_processed():
    """Load list of already-processed contract IDs."""
    if PROCESSED_FILE.exists():
        return json.load(open(PROCESSED_FILE))
    return {}


def save_processed(data):
    """Save processed contracts."""
    with open(PROCESSED_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def search_contract_emails(max_results=10, newer_than="7d"):
    """Search Gmail for contract signed emails."""
    cmd = [
        "gog", "gmail", "messages", "search",
        f"subject:'IndoorMedia Contract Signed' newer_than:{newer_than}",
        "--max", str(max_results),
        "--json"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Gmail search failed: {result.stderr}")
        return []
    
    data = json.loads(result.stdout)
    return data.get("messages", [])


def get_email_body(message_id):
    """Get the full email body."""
    cmd = ["gog", "gmail", "show", message_id, "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Failed to get email: {result.stderr}")
        return None
    return json.loads(result.stdout)


def extract_drive_link(body_text):
    """Extract Google Drive file ID from email body."""
    match = re.search(r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)', body_text)
    if match:
        return match.group(1)
    return None


def download_pdf(drive_file_id, contract_num):
    """Download PDF from Google Drive."""
    pdf_path = CONTRACTS_DIR / f"{contract_num}.pdf"
    if pdf_path.exists():
        return pdf_path
    
    cmd = ["gog", "drive", "download", drive_file_id, "--out", str(pdf_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Failed to download PDF: {result.stderr}")
        return None
    
    print(f"📄 Downloaded: {pdf_path}")
    return pdf_path


def parse_contract_pdf(pdf_path):
    """Extract contract details from PDF using pdftotext."""
    cmd = ["pdftotext", str(pdf_path), "-"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ pdftotext failed: {result.stderr}")
        return None
    
    text = result.stdout
    contract = {}
    
    # Contract number
    m = re.search(r'Contract #:\s*(\S+)', text)
    contract['contract_num'] = m.group(1) if m else None
    
    # Contract date
    m = re.search(r'Contract #:.*?\n(\d{1,2}/\d{1,2}/\d{4})', text)
    contract['contract_date'] = m.group(1) if m else None
    
    # Sales rep name and email
    m = re.search(r'Sales Representative:\s*\n(.+?)\s*\|\s*(\S+@\S+)', text)
    if m:
        contract['rep_name'] = m.group(1).strip()
        contract['rep_email'] = m.group(2).strip()
    
    # Customer Information section — fields appear in order without labels:
    # Business Name, Contact Name, Email, Phone, Street Address, City/State/Zip
    m = re.search(r'Customer Information\s*\n(.+?)(?:\n|$)', text)
    contract['business_name'] = m.group(1).strip() if m else None
    
    # Parse the Customer Information block (lines after "Customer Information")
    lines = text.split('\n')
    cust_start = None
    for i, line in enumerate(lines):
        if 'Customer Information' in line:
            cust_start = i + 1
            break
    
    if cust_start is not None:
        # pdftotext renders 2-column PDFs with interleaved lines,
        # so scan ALL lines after "Customer Information" up to "Product" 
        # and pick out customer fields by pattern (not position)
        cust_lines = []
        for j in range(cust_start, min(cust_start + 30, len(lines))):
            l = lines[j].strip()
            if l.startswith('Product') or l.startswith('Description') or l.startswith('ConnectionHUB'):
                break
            if l:
                cust_lines.append(l)
        
        # Parse fields by pattern recognition
        for cl in cust_lines:
            # Email pattern
            if '@' in cl and not contract.get('customer_email'):
                email_match = re.search(r'[\w.+-]+@[\w.-]+\.\w+', cl)
                if email_match:
                    contract['customer_email'] = email_match.group(0)
            # Phone pattern (xxx) xxx-xxxx or xxx-xxx-xxxx
            elif re.search(r'\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', cl) and not contract.get('customer_phone'):
                phone_match = re.search(r'\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', cl)
                if phone_match:
                    contract['customer_phone'] = phone_match.group(0)
            # Address pattern (starts with number)
            elif re.match(r'^\d+\s', cl) and not contract.get('customer_address'):
                contract['customer_address'] = cl
            # City, State Zip pattern
            elif re.search(r',\s*[A-Z]{2}\s+\d{5}', cl) and not contract.get('customer_city_state'):
                contract['customer_city_state'] = cl
            # Contact name (not business name, no digits, 2+ words, not a section header)
            elif (not contract.get('customer_name') and 
                  cl != contract.get('business_name') and
                  len(cl.split()) >= 2 and 
                  not any(c.isdigit() for c in cl) and
                  '@' not in cl and
                  not any(kw in cl for kw in ['Billing', 'Customer', 'Payment', 'New Customer', 'Frequency', 'amount', 'Paid in'])):
                contract['customer_name'] = cl
    
    # Fallback: Customer name from "Advertiser's Printed Name:" section
    if not contract.get('customer_name'):
        m = re.search(r"Advertiser's Printed Name:\s*\n?\s*(.+?)(?:\n|$)", text)
        if m:
            name = m.group(1).strip()
            if name and not name.startswith('Advertiser') and not name.startswith('E-'):
                contract['customer_name'] = name
    
    # Store info from Register Tape line
    # Pattern: StoreName-NNNN (ZoneCode)\nAddress\nEst. Start: XX MM/DD/YYYY\nAd type
    m = re.search(r'Register Tape\s*\n*([\w]+-\d+)\s*\((\w+)\)\s*\n(.+?)\n.*?Est\.\s*Start:\s*\w*\s*(\d{1,2}/\d{1,2}/\d{4})', text, re.DOTALL)
    if m:
        contract['store_number'] = m.group(1)
        contract['zone'] = m.group(2)
        address_line = m.group(3).strip()
        contract['store_address'] = address_line
        contract['est_start'] = m.group(4)
        
        # Extract city from address (last part before zip)
        addr_match = re.search(r',\s*([^,]+?),?\s*\d{5}', address_line)
        if addr_match:
            contract['city'] = addr_match.group(1).strip()
        else:
            # Try from customer address
            city_match = re.search(r'(\w[\w\s]+),\s*\w{2}\s+\d{5}', text)
            if city_match:
                contract['city'] = city_match.group(1).strip()
    
    # Store chain name (e.g., "Safeway" from "Safeway-1762")
    if contract.get('store_number'):
        chain_match = re.match(r'([A-Za-z]+)', contract['store_number'])
        if chain_match:
            chain_code = chain_match.group(1)
            # Map common codes to names
            chain_map = {
                'SAF': 'Safeway', 'FME': 'Fred Meyer', 'ALB': 'Albertsons',
                'KRO': 'Kroger', 'HAG': 'Haggen', 'VON': 'Vons',
                'RAL': 'Ralphs', 'QFC': 'QFC', 'STB': 'Stater Bros',
                'FF4': 'Food 4 Less', 'HEB': 'HEB', 'SMI': 'Smiths',
                'KSO': 'King Soopers', 'TOM': 'Tom Thumb',
            }
            # Try first 3 chars
            contract['chain_name'] = chain_map.get(chain_code[:3], chain_code)
    
    # Ad type
    m = re.search(r'(Single|Double)\s+Ad', text)
    contract['ad_type'] = m.group(1) if m else 'Single'
    
    # Contract total amount
    m = re.search(r'Contract Total\s*\$?([\d,]+\.?\d*)', text)
    if m:
        try:
            contract['total'] = float(m.group(1).replace(',', ''))
        except ValueError:
            pass
    # Fallback: Net Price
    if not contract.get('total'):
        m = re.search(r'Net Price\s*\$?([\d,]+\.?\d*)', text)
        if m:
            try:
                contract['total'] = float(m.group(1).replace(',', ''))
            except ValueError:
                pass
    
    return contract


def parse_date(date_str):
    """Parse MM/DD/YYYY date string."""
    return datetime.strptime(date_str, "%m/%d/%Y")


def calculate_event_dates(est_start_str):
    """Calculate all calendar event dates from the Est. Start date."""
    est_start = parse_date(est_start_str)
    
    install_date = est_start - timedelta(days=10)
    audit_date = install_date + timedelta(days=45)
    
    # Check-ins every 45 days after audit, until renewal
    renewal_date = install_date + timedelta(days=8*30)  # ~8 months
    
    checkins = []
    next_checkin = audit_date + timedelta(days=45)
    checkin_num = 1
    while next_checkin < renewal_date:
        checkins.append((checkin_num, next_checkin))
        checkin_num += 1
        next_checkin += timedelta(days=45)
    
    return {
        'install': install_date,
        'audit': audit_date,
        'checkins': checkins,
        'renewal': renewal_date,
    }


def create_calendar_event(summary, date, attendees, description="", color=None):
    """Create a Google Calendar event using gog."""
    date_str = date.strftime("%Y-%m-%dT09:00:00-08:00")
    end_str = date.strftime("%Y-%m-%dT10:00:00-08:00")
    
    cmd = [
        "gog", "calendar", "create", CALENDAR_ID,
        "--summary", summary,
        "--from", date_str,
        "--to", end_str,
        "--description", description,
    ]
    
    if color:
        cmd.extend(["--event-color", str(color)])
    
    # Add attendees
    for email in attendees:
        cmd.extend(["--attendees", email])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ❌ Failed to create event: {result.stderr}")
        return False
    
    print(f"  ✅ Created: {summary} on {date.strftime('%m/%d/%Y')}")
    return True


def process_contract(contract):
    """Create all calendar events for a contract."""
    biz = contract.get('business_name', 'Unknown Business')
    customer = contract.get('customer_name', 'Unknown')
    chain = contract.get('chain_name', 'Store')
    city = contract.get('city', '')
    store_num = contract.get('store_number', '')
    rep_email = contract.get('rep_email', '')
    rep_name = contract.get('rep_name', '')
    contract_num = contract.get('contract_num', '')
    est_start = contract.get('est_start')
    
    if not est_start:
        print(f"❌ No Est. Start date found for {contract_num}")
        return False
    
    dates = calculate_event_dates(est_start)
    attendees = [TYLER_EMAIL]
    if rep_email and rep_email != TYLER_EMAIL:
        attendees.append(rep_email)
    
    desc_base = (
        f"Contract: {contract_num}\n"
        f"Business: {biz}\n"
        f"Customer: {customer}\n"
        f"Rep: {rep_name}\n"
        f"Store: {chain} {store_num}, {city}\n"
        f"Est. Start: {est_start}"
    )
    
    print(f"\n📋 Contract {contract_num}: {biz} at {chain} {city}")
    print(f"   Rep: {rep_name} ({rep_email})")
    print(f"   Est. Start: {est_start}")
    print(f"   Creating calendar events...\n")
    
    # 1. Install - 10 days before Est. Start
    create_calendar_event(
        summary=f"📦 Install: {biz} at {chain}, {city}, {store_num}",
        date=dates['install'],
        attendees=attendees,
        description=f"INSTALL\n{desc_base}\n\nInstall tape at store 10 days before circulation start.",
        color=9  # Blue
    )
    
    # 2. Audit - 45 days after install
    create_calendar_event(
        summary=f"🔍 Audit: {chain}, {city}, {store_num} — check in w/ {customer}/{biz}",
        date=dates['audit'],
        attendees=attendees,
        description=f"AUDIT & CHECK-IN\n{desc_base}\n\nVerify tape is displayed correctly. Check in with {customer} at {biz}.",
        color=7  # Teal
    )
    
    # 3. Ongoing 45-day check-ins
    for num, checkin_date in dates['checkins']:
        create_calendar_event(
            summary=f"🔄 Check-in #{num}: {chain}, {city}, {store_num} — {customer}/{biz}",
            date=checkin_date,
            attendees=attendees,
            description=f"45-DAY CHECK-IN #{num}\n{desc_base}\n\nRegular check-in with {customer} at {biz}.",
            color=10  # Green
        )
    
    # 4. Renewal - 8 months from install
    create_calendar_event(
        summary=f"🔁 Renewal: {biz} ({customer}) — {chain}, {city}",
        date=dates['renewal'],
        attendees=attendees,
        description=f"RENEWAL REMINDER\n{desc_base}\n\n8 months since install. Begin renewal conversation with {customer} at {biz}.",
        color=11  # Red
    )
    
    return True


def process_email(message_id, subject):
    """Process a single contract email."""
    # Get email body
    email_data = get_email_body(message_id)
    if not email_data:
        return False
    
    body = email_data.get('body', '')
    
    # Extract contract number from subject
    contract_match = re.search(r'Contract Signed:\s*(\S+)', subject)
    contract_num = contract_match.group(1) if contract_match else None
    
    if not contract_num:
        print(f"❌ Could not extract contract number from: {subject}")
        return False
    
    # Extract Google Drive link
    drive_id = extract_drive_link(body)
    if not drive_id:
        print(f"❌ No Google Drive link found in email for {contract_num}")
        return False
    
    # Download PDF
    pdf_path = download_pdf(drive_id, contract_num)
    if not pdf_path:
        return False
    
    # Parse PDF
    contract = parse_contract_pdf(pdf_path)
    if not contract:
        print(f"❌ Failed to parse PDF for {contract_num}")
        return False
    
    # Save to contracts.json (for bot customer views)
    save_to_contracts_json(contract)
    
    # Create calendar events
    return process_contract(contract)


def run(newer_than="7d", dry_run=False):
    """Main pipeline: search emails, process new contracts."""
    print(f"🔍 Searching for contract emails (newer than {newer_than})...")
    
    emails = search_contract_emails(newer_than=newer_than)
    
    if not emails:
        print("📭 No new contract emails found.")
        return
    
    processed = load_processed()
    new_count = 0
    
    for email in emails:
        msg_id = email['id']
        subject = email.get('subject', '')
        
        # Extract contract number
        contract_match = re.search(r'Contract Signed:\s*(\S+)', subject)
        contract_num = contract_match.group(1) if contract_match else msg_id
        
        if contract_num in processed:
            print(f"⏭️  Already processed: {contract_num}")
            continue
        
        print(f"\n{'='*50}")
        print(f"📧 New contract: {subject}")
        print(f"{'='*50}")
        
        if dry_run:
            print("   [DRY RUN] Would process this contract")
            continue
        
        success = process_email(msg_id, subject)
        
        if success:
            processed[contract_num] = {
                'message_id': msg_id,
                'processed_at': datetime.now().isoformat(),
                'subject': subject,
            }
            save_processed(processed)
            new_count += 1
            print(f"\n✅ Contract {contract_num} fully processed!")
        else:
            print(f"\n❌ Failed to process {contract_num}")
    
    print(f"\n{'='*50}")
    print(f"📊 Summary: {new_count} new contract(s) processed, {len(emails)} total found")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Contract-to-Calendar Pipeline")
    parser.add_argument("--newer-than", default="7d", help="Gmail search window (default: 7d)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without creating events")
    parser.add_argument("--reprocess", help="Reprocess a specific contract number")
    args = parser.parse_args()
    
    if args.reprocess:
        processed = load_processed()
        if args.reprocess in processed:
            del processed[args.reprocess]
            save_processed(processed)
        print(f"🔄 Reprocessing {args.reprocess}...")
    
    run(newer_than=args.newer_than, dry_run=args.dry_run)
