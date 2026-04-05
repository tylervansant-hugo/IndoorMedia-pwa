#!/usr/bin/env python3
"""
Scan Gmail for Ad Proof emails from zone.XXX@indoormedia.com
Extract: client name, contract #, store, ad size, image URL, recipients
Save to pwa/public/data/ad_proofs.json
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime

ACCOUNT = "tyler.vansant@indoormedia.com"
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "pwa", "public", "data", "ad_proofs.json")
DAYS_BACK = 90  # scan last 90 days on first run, then daily catches new ones

# Rep email mapping (email -> rep display name)
REP_EMAILS = {
    "tyler.vansant@indoormedia.com": "Tyler Van Sant",
    "tyler.vansant@rtui.com": "Tyler Van Sant",
    "richard.leibowitz@indoormedia.com": "Rick Leibowitz",
    "amy.dixon@indoormedia.com": "Amy Dixon",
    "jan.banks@indoormedia.com": "Jan Banks",
    "dave.boring@indoormedia.com": "Dave Boring",
    "megan.wink@indoormedia.com": "Megan Wink",
    "matthew.boozer@indoormedia.com": "Matthew Boozer",
    "marty.eng@indoormedia.com": "Marty Eng",
    "adan.ramos@indoormedia.com": "Adan Ramos",
    "christian.johnson@indoormedia.com": "Christian Johnson",
    "sandee.deppiesse@indoormedia.com": "Sandee Deppiesse",
    "ben.patacsil@indoormedia.com": "Ben Patacsil",
    "tyler.blair@indoormedia.com": "Tyler Blair",
}

# Admin emails - these users see ALL ad proofs
ADMIN_EMAILS = {
    "tyler.vansant@indoormedia.com",
    "tyler.vansant@rtui.com",
    "richard.leibowitz@indoormedia.com",
}


def search_ad_proof_emails(days_back=7):
    """Search Gmail for ad proof emails."""
    query = f"from:zone subject:\"Ad Proof from IndoorMedia\" newer_than:{days_back}d"
    cmd = [
        "gog", "gmail", "messages", "search", query,
        "--max", "200",
        "--account", ACCOUNT,
        "--json", "--no-input"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"Error searching: {result.stderr}", file=sys.stderr)
        return []
    
    try:
        data = json.loads(result.stdout)
        return data.get("messages", [])
    except json.JSONDecodeError:
        print(f"Failed to parse search results", file=sys.stderr)
        return []


def get_email_details(msg_id):
    """Get full email details."""
    cmd = [
        "gog", "gmail", "get", msg_id,
        "--account", ACCOUNT,
        "--json", "--no-input"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        print(f"Error getting {msg_id}: {result.stderr}", file=sys.stderr)
        return None
    
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Failed to parse email {msg_id}", file=sys.stderr)
        return None


def parse_subject(subject):
    """Parse: Ad Proof from IndoorMedia , Client Name - Location [Zone - Cycle - Contract#]"""
    info = {
        "client_name": "",
        "location": "",
        "zone": "",
        "cycle": "",
        "contract_number": "",
    }
    
    # Extract bracket contents: [07W - B2 - J357077]
    bracket_match = re.search(r'\[([^\]]+)\]', subject)
    if bracket_match:
        parts = [p.strip() for p in bracket_match.group(1).split('-')]
        if len(parts) >= 1:
            info["zone"] = parts[0]
        if len(parts) >= 2:
            info["cycle"] = parts[1].strip()
        if len(parts) >= 3:
            info["contract_number"] = parts[2].strip()
    
    # Extract client name and location from middle part
    # "Ad Proof from IndoorMedia , Client Name - Location [...]"
    middle = re.sub(r'\[.*?\]', '', subject)
    middle = re.sub(r'^.*?Ad Proof from IndoorMedia\s*,?\s*', '', middle, flags=re.IGNORECASE).strip()
    
    if ' - ' in middle:
        parts = middle.rsplit(' - ', 1)
        info["client_name"] = parts[0].strip()
        info["location"] = parts[1].strip()
    else:
        info["client_name"] = middle.strip()
    
    return info


def parse_body(body):
    """Extract store info, ad size, install month, and image URL from email body."""
    info = {
        "store": "",
        "ad_size": "",
        "install_month": "",
        "run_months": "",
        "image_url": "",
        "review_deadline": "",
    }
    
    # Extract store info line (e.g., "Albertsons 0243, 220 Ironwood Dr, Coeur D'Alene, ID")
    store_match = re.search(r'where your coupon will be dispensed:\*?\s*\n(.+)', body)
    if store_match:
        info["store"] = store_match.group(1).strip()
    
    # Ad size (Single or Double)
    size_match = re.search(r'This will be a \*?(\w+)\*? size ad', body)
    if size_match:
        info["ad_size"] = size_match.group(1)
    
    # Install month and run months
    install_match = re.search(r'installed in \*?(\w+)\*? and run.*?for \*?([^*\n]+)\*?', body)
    if install_match:
        info["install_month"] = install_match.group(1).strip()
        info["run_months"] = install_match.group(2).strip().rstrip('.')
    
    # Image URL - extract Google Drive file ID and build direct link
    img_match = re.search(r'GetGoogleDriveCoupon\?id=([^\s\)>\]]+)', body)
    if img_match:
        drive_id = img_match.group(1).rstrip('>')
        info["image_url"] = f"https://lh3.googleusercontent.com/d/{drive_id}"
        info["drive_id"] = drive_id
    
    # Review deadline
    deadline_match = re.search(r'REPLY ALL.*?by \*?(\d{2}/\d{2}/\d{4})\*?', body)
    if deadline_match:
        info["review_deadline"] = deadline_match.group(1)
    
    return info


def extract_recipients(email_data):
    """Get all recipient emails (to + cc) to determine which reps should see this proof."""
    recipients = set()
    headers = email_data.get("headers", {})
    
    for field in ["to", "cc", "bcc"]:
        value = headers.get(field, "")
        if value:
            # Extract all email addresses
            emails = re.findall(r'[\w.+-]+@[\w.-]+', value.lower())
            recipients.update(emails)
    
    return list(recipients)


def extract_client_email(email_data):
    """Get the client email (the 'to' field, excluding indoormedia addresses)."""
    to_field = email_data.get("headers", {}).get("to", "")
    emails = re.findall(r'[\w.+-]+@[\w.-]+', to_field.lower())
    # Filter out indoormedia emails — client is the non-indoormedia recipient
    client_emails = [e for e in emails if 'indoormedia.com' not in e and 'rtui.com' not in e]
    return client_emails[0] if client_emails else (emails[0] if emails else "")


def extract_client_name_from_body(body):
    """Extract the salutation name from the email body (first line is usually 'Name,')."""
    lines = body.strip().split('\n')
    for line in lines[:3]:
        line = line.strip().rstrip(',')
        if line and len(line) < 60 and not line.startswith('*') and not line.startswith('Below'):
            return line
    return ""


def match_reps(recipients):
    """Match recipient emails to rep names."""
    matched = []
    for email in recipients:
        email_lower = email.lower()
        if email_lower in REP_EMAILS:
            matched.append({
                "email": email_lower,
                "name": REP_EMAILS[email_lower]
            })
    return matched


def main():
    # Load existing proofs
    existing = {}
    if os.path.exists(OUTPUT):
        try:
            with open(OUTPUT) as f:
                existing_list = json.load(f)
                existing = {p["message_id"]: p for p in existing_list}
        except (json.JSONDecodeError, KeyError):
            pass
    
    # Determine scan window
    days = DAYS_BACK if not existing else 3
    if "--full" in sys.argv:
        days = DAYS_BACK
    
    print(f"Scanning last {days} days for ad proof emails...")
    messages = search_ad_proof_emails(days)
    print(f"Found {len(messages)} ad proof emails")
    
    new_count = 0
    for msg in messages:
        msg_id = msg.get("id", "")
        if msg_id in existing:
            continue  # Already processed
        
        print(f"  Processing: {msg.get('subject', 'unknown')[:80]}...")
        details = get_email_details(msg_id)
        if not details:
            continue
        
        subject = details.get("headers", {}).get("subject", msg.get("subject", ""))
        body = details.get("body", "")
        
        subject_info = parse_subject(subject)
        body_info = parse_body(body)
        recipients = extract_recipients(details)
        reps = match_reps(recipients)
        client_email = extract_client_email(details)
        contact_name = extract_client_name_from_body(body)
        
        proof = {
            "message_id": msg_id,
            "date": msg.get("date", ""),
            "from": details.get("headers", {}).get("from", ""),
            "subject": subject,
            "client_name": subject_info["client_name"],
            "contact_name": contact_name,
            "client_email": client_email,
            "location": subject_info["location"],
            "zone": subject_info["zone"],
            "cycle": subject_info["cycle"],
            "contract_number": subject_info["contract_number"],
            "store": body_info["store"],
            "ad_size": body_info["ad_size"],
            "install_month": body_info["install_month"],
            "run_months": body_info["run_months"],
            "image_url": body_info["image_url"],
            "review_deadline": body_info["review_deadline"],
            "recipients": recipients,
            "reps": reps,
        }
        
        existing[msg_id] = proof
        new_count += 1
    
    # Deduplicate: keep only the newest proof per contract + store combo
    all_proofs = sorted(existing.values(), key=lambda p: p.get("date", ""), reverse=True)
    
    seen = {}  # key: (contract_number, store) -> newest proof
    deduped = []
    dupes_removed = 0
    for p in all_proofs:
        key = (p.get("contract_number", ""), p.get("store", ""))
        if key[0] and key in seen:
            dupes_removed += 1
            continue  # Skip older version
        if key[0]:
            seen[key] = True
        deduped.append(p)
    
    if dupes_removed:
        print(f"Deduplication: removed {dupes_removed} older versions (same contract + store)")
    
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, 'w') as f:
        json.dump(deduped, f, indent=2)
    
    print(f"Done! {new_count} new proofs added, {dupes_removed} dupes removed. Total: {len(deduped)}")
    return new_count


if __name__ == "__main__":
    main()
