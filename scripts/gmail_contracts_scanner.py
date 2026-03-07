#!/usr/bin/env python3
"""
Gmail Contracts Scanner
Scans Gmail for "IndoorMedia Contract Signed" emails since 1/1/2026
Extracts contract data from email body
"""

import os
import json
import subprocess
import re
from datetime import datetime
from pathlib import Path
import logging
from dotenv import load_dotenv
import urllib.request
import tempfile
import pdfplumber

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
WORKSPACE = Path(__file__).parent.parent
DATA_DIR = WORKSPACE / "data"
CONTRACTS_FILE = DATA_DIR / "contracts.json"

# Load env
load_dotenv(WORKSPACE / ".env", override=True)
load_dotenv(WORKSPACE / ".env.local", override=True)

def load_contracts():
    """Load existing contracts from JSON."""
    if CONTRACTS_FILE.exists():
        with open(CONTRACTS_FILE) as f:
            return json.load(f)
    return {"contracts": [], "last_scan": None}

def save_contracts(data):
    """Save contracts to JSON."""
    CONTRACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONTRACTS_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    logger.info(f"✅ Saved {len(data['contracts'])} contracts to {CONTRACTS_FILE}")

def query_gmail():
    """Query Gmail for IndoorMedia Contract Signed emails since 1/1/2026 from donotreply@indoormedia.com."""
    try:
        # Use gog to search Gmail - only from donotreply@indoormedia.com (original emails, not replies)
        cmd = [
            "gog", "gmail", "search",
            'subject:"IndoorMedia Contract Signed" from:donotreply@indoormedia.com after:2026-01-01',
            "--json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            logger.error(f"Gmail search failed: {result.stderr}")
            return []
        
        # Parse JSON output
        try:
            data = json.loads(result.stdout)
            threads = data.get("threads", [])
            logger.info(f"Found {len(threads)} valid contract emails from donotreply@indoormedia.com")
            return threads
        except json.JSONDecodeError:
            logger.warning("Could not parse Gmail response as JSON")
            return []
    except Exception as e:
        logger.error(f"Error querying Gmail: {e}")
        return []

def get_email_body(thread_id):
    """Get email body from a thread."""
    try:
        cmd = [
            "gog", "gmail", "get",
            thread_id,
            "--json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            logger.warning(f"Could not retrieve email {thread_id}")
            return None
        
        try:
            data = json.loads(result.stdout)
            body = data.get("body", "")
            if not body:
                # Try message payload
                payload = data.get("message", {}).get("payload", {})
                body = payload.get("body", {}).get("data", "")
            return body
        except:
            return None
    except Exception as e:
        logger.warning(f"Error getting email body: {e}")
        return None

def extract_pdf_link(email_body):
    """Extract Google Drive PDF link from email body."""
    # Look for Google Drive links
    match = re.search(r'https://drive\.google\.com/file/d/([^/]+)', email_body)
    if match:
        file_id = match.group(1)
        # Convert to direct download link
        return f"https://drive.google.com/uc?id={file_id}&export=download"
    return None

def download_and_extract_amount(pdf_url):
    """Download PDF from URL and extract contract total amount."""
    try:
        # Download PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            try:
                urllib.request.urlretrieve(pdf_url, tmp.name)
            except Exception as e:
                logger.warning(f"Could not download PDF from {pdf_url}: {e}")
                return None
            
            # Parse PDF
            try:
                with pdfplumber.open(tmp.name) as pdf:
                    full_text = ""
                    for page in pdf.pages:
                        full_text += page.extract_text() + "\n"
                    
                    # Look for "Contract Total" followed by dollar amount
                    match = re.search(r'Contract Total\s*\$?([\d,]+\.?\d*)', full_text)
                    if match:
                        amount_str = match.group(1).replace(',', '')
                        try:
                            return float(amount_str)
                        except ValueError:
                            pass
                    
                    # Also try "Net Price" followed by amount
                    match = re.search(r'Net Price\s*\$?([\d,]+\.?\d*)', full_text)
                    if match:
                        amount_str = match.group(1).replace(',', '')
                        try:
                            return float(amount_str)
                        except ValueError:
                            pass
                    
                    return None
            finally:
                os.unlink(tmp.name)
    except Exception as e:
        logger.warning(f"Error extracting PDF amount: {e}")
        return None

def parse_contract_pdf_details(pdf_url):
    """Download PDF and extract detailed contract information."""
    details = {
        "business_name": None,
        "contact_name": None,
        "contact_email": None,
        "contact_phone": None,
        "address": None,
        "store_name": None,
        "store_number": None,
        "total_amount": None,
        "product_description": None,
    }
    
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            try:
                urllib.request.urlretrieve(pdf_url, tmp.name)
            except:
                return details
            
            try:
                with pdfplumber.open(tmp.name) as pdf:
                    full_text = ""
                    for page in pdf.pages:
                        full_text += page.extract_text() + "\n"
                    
                    # Extract Business Name
                    match = re.search(r"Advertiser's Business Name:\s*([^\n]+)", full_text)
                    if match:
                        details["business_name"] = match.group(1).strip()
                    
                    # Extract Contact Name (Printed Name)
                    match = re.search(r"Advertiser's Printed Name:\s*([^\n]+)", full_text)
                    if match:
                        details["contact_name"] = match.group(1).strip()
                    
                    # Extract Email
                    emails = re.findall(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', full_text)
                    if emails:
                        details["contact_email"] = emails[0]
                    
                    # Extract Phone
                    match = re.search(r'\(?(\d{3})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})', full_text)
                    if match:
                        details["contact_phone"] = f"({match.group(1)}) {match.group(2)}-{match.group(3)}"
                    
                    # Extract Address
                    match = re.search(r'(\d+\s+[^,]+,\s+[^,]+,\s+\d{5})', full_text)
                    if match:
                        details["address"] = match.group(1).strip()
                    
                    # Extract Store Name and Number
                    match = re.search(r'(Quality Food Center|Fred Meyer|Safeway|Albertsons|[A-Z]{3})\s*[#-]?(\d{4}|\d{3}[A-Z])', full_text)
                    if match:
                        details["store_name"] = match.group(1).strip()
                        details["store_number"] = match.group(2).strip()
                    
                    # Extract Product
                    if "Register Tape" in full_text:
                        match = re.search(r'Register Tape.*?(Single|Double).*?Ad', full_text)
                        if match:
                            details["product_description"] = f"Register Tape {match.group(1)} Ad"
                    
                    # Extract Amount
                    match = re.search(r'Contract Total\s*\$?([\d,]+\.?\d*)', full_text)
                    if match:
                        amount_str = match.group(1).replace(',', '')
                        try:
                            details["total_amount"] = float(amount_str)
                        except ValueError:
                            pass
            finally:
                os.unlink(tmp.name)
    except Exception as e:
        logger.warning(f"Error extracting PDF details: {e}")
    
    return details

def parse_contract_email(email_body, subject, date):
    """Extract contract data from email body text."""
    try:
        contract_data = {
            "contract_number": None,
            "date": date,
            "business_name": None,
            "contact_name": None,
            "contact_email": None,
            "contact_phone": None,
            "sales_rep": None,
            "store_name": None,
            "store_number": None,
            "product_description": None,
            "total_amount": None,
            "payment_date": None,
            "address": None,
            "extracted_at": datetime.now().isoformat(),
        }
        
        # Extract Contract Number from subject
        match = re.search(r'([A-Z]\d{6}[A-Z])', subject)
        if match:
            contract_data["contract_number"] = match.group(1)
        
        # Extract Customer Name (name before "Has Signed")
        match = re.search(r'(\w+\s+\w+)\s+Has Signed', email_body)
        if match:
            contract_data["contact_name"] = match.group(1)
        
        # Extract Business Name (stop before "Customer Email")
        match = re.search(r'Business Name\s+([^C\n]+?)(?:Customer Email|$)', email_body)
        if match:
            name = match.group(1).strip()
            # Remove trailing email if present
            name = re.sub(r'\s*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}.*', '', name).strip()
            if name and name != "Customer Email":
                contract_data["business_name"] = name
        
        # Extract Customer Email (first valid email that's not donotreply)
        for match in re.finditer(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', email_body):
            email = match.group(1)
            if "donotreply" not in email.lower() and "indoormedia" not in email.lower():
                contract_data["contact_email"] = email
                break
        
        # Extract Phone (look for pattern like (503) 454-6141)
        match = re.search(r'\(?(\d{3})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})', email_body)
        if match:
            contract_data["contact_phone"] = f"({match.group(1)}) {match.group(2)}-{match.group(3)}"
        
        # Extract Sales Rep (get the name before the bracket)
        match = re.search(r'Signature Sales Rep\s+([^\[\n]+)', email_body)
        if match:
            rep_name = match.group(1).strip()
            # Remove SU numbers and such
            rep_name = re.sub(r'\[.*?\]', '', rep_name).strip()
            if rep_name:
                contract_data["sales_rep"] = rep_name
        
        # Extract Sign Date (from SignDate field)
        match = re.search(r'SignDate\s+(\d{2}/\d{2}/\d{4})', email_body)
        if match:
            contract_data["payment_date"] = match.group(1)
        
        # Extract PDF URL and get detailed info from PDF
        pdf_url = extract_pdf_link(email_body)
        if pdf_url:
            logger.info(f"  📄 Extracting details from PDF...")
            pdf_details = parse_contract_pdf_details(pdf_url)
            
            # Merge PDF details (PDF is authoritative)
            for key in pdf_details:
                if pdf_details[key] is not None:
                    contract_data[key] = pdf_details[key]
        
        logger.info(f"✅ Parsed: {contract_data['contract_number']} - {contract_data['business_name']} / {contract_data['contact_name']} (${contract_data['total_amount']})")
        return contract_data
    
    except Exception as e:
        logger.error(f"Error parsing email: {e}")
        return None

def scan_and_update():
    """Main function: scan Gmail and extract contract data."""
    logger.info("🔍 Starting contracts scan...")
    
    # Query Gmail
    threads = query_gmail()
    if not threads:
        logger.warning("No new emails found")
        return
    
    # Load existing contracts
    data = load_contracts()
    existing_ids = {c.get("contract_number") for c in data["contracts"]}
    
    new_count = 0
    for thread in threads:
        thread_id = thread.get("id")
        subject = thread.get("subject", "")
        date = thread.get("date", "")
        
        try:
            logger.info(f"📧 Processing: {subject}")
            
            # Get email body
            email_body = get_email_body(thread_id)
            if not email_body:
                logger.warning(f"  ⚠️ Could not get email body")
                continue
            
            # Parse contract data from email
            contract = parse_contract_email(email_body, subject, date)
            
            if contract and contract.get("contract_number") not in existing_ids:
                data["contracts"].append(contract)
                existing_ids.add(contract["contract_number"])
                new_count += 1
        
        except Exception as e:
            logger.error(f"  ❌ Error processing {thread_id}: {e}")
            continue
    
    # Update last scan time
    data["last_scan"] = datetime.now().isoformat()
    
    # Save
    save_contracts(data)
    logger.info(f"✅ Scan complete! Added {new_count} new contracts. Total: {len(data['contracts'])}")

if __name__ == "__main__":
    try:
        scan_and_update()
    except KeyboardInterrupt:
        logger.info("Scan cancelled.")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
