#!/usr/bin/env python3
"""Re-parse all contract PDFs and rebuild contracts.json for the PWA."""

import subprocess, re, json, os
from datetime import datetime
from pathlib import Path

contracts_dir = Path(__file__).parent.parent / "data" / "contracts"
pwa_contracts = Path(__file__).parent.parent / "pwa" / "public" / "data" / "contracts.json"
pdfs = sorted(contracts_dir.glob("*.pdf"))
print(f"Found {len(pdfs)} PDFs")

all_contracts = []

for pdf_path in pdfs:
    text = subprocess.run(["pdftotext", str(pdf_path), "-"], capture_output=True, text=True).stdout
    if not text.strip():
        print(f"  ⚠️ Empty: {pdf_path.name}")
        continue

    contract = {}

    # Contract number
    m = re.search(r"Contract #:\s*(\S+)", text)
    contract["contract_number"] = m.group(1) if m else pdf_path.stem

    # Date
    m = re.search(r"Contract #:.*?\n(\d{1,2}/\d{1,2}/\d{4})", text)
    if m:
        try:
            d = datetime.strptime(m.group(1), "%m/%d/%Y")
            contract["date"] = d.strftime("%Y-%m-%d %H:%M")
            contract["payment_date"] = m.group(1)
        except:
            pass

    # Sales rep
    m = re.search(r"Sales Representative:\s*\n(.+?)\s*\|", text)
    contract["sales_rep"] = m.group(1).strip() if m else ""

    # Parse customer info block
    lines = text.split("\n")
    cust_start = None
    for i, line in enumerate(lines):
        if "Customer Information" in line:
            cust_start = i + 1
            break

    if cust_start:
        cust_lines = []
        for j in range(cust_start, min(cust_start + 30, len(lines))):
            l = lines[j].strip()
            if l.startswith("Product") or l.startswith("ConnectionHUB"):
                break
            if l and l != "Billing Information" and l != "Customer Information":
                cust_lines.append(l)

        skip_words = [
            "Billing", "Renewal", "New Customer", "Payment", "Frequency",
            "Electronic", "amount", "deposit", "Paid in", "remaining",
            "additional", "schedule", "Credit Card", "Check Debit",
            "beginning on", "paid on"
        ]

        for cl in cust_lines:
            if "@" in cl and not contract.get("contact_email"):
                em = re.search(r"[\w.+-]+@[\w.-]+\.\w+", cl)
                if em and "indoormedia" not in em.group(0).lower():
                    contract["contact_email"] = em.group(0)
            elif re.search(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", cl) and not contract.get("contact_phone"):
                pm = re.search(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", cl)
                contract["contact_phone"] = pm.group(0) if pm else ""
            elif re.match(r"^\d+\s", cl) and not contract.get("address"):
                contract["address"] = cl
            elif not any(kw.lower() in cl.lower() for kw in skip_words):
                if not contract.get("business_name"):
                    contract["business_name"] = cl
                elif (not contract.get("contact_name") and len(cl.split()) >= 2
                      and not any(c.isdigit() for c in cl) and "@" not in cl):
                    contract["contact_name"] = cl

    # Fallback business name
    if not contract.get("business_name"):
        m = re.search(r"Advertiser's Business Name:\s*\n?\s*(.+?)(?:\n|$)", text)
        if m:
            contract["business_name"] = m.group(1).strip()

    # Fallback contact name
    if not contract.get("contact_name"):
        m = re.search(r"Advertiser's Printed Name:\s*\n?\s*(.+?)(?:\n|$)", text)
        if m:
            contract["contact_name"] = m.group(1).strip()

    # Contract total
    m = re.search(r"Contract Total\s*\$?([\d,]+\.?\d*)", text)
    if m:
        try:
            contract["total_amount"] = float(m.group(1).replace(",", ""))
        except:
            pass
    if not contract.get("total_amount"):
        m = re.search(r"Net Price\s*\$?([\d,]+\.?\d*)", text)
        if m:
            try:
                contract["total_amount"] = float(m.group(1).replace(",", ""))
            except:
                pass

    # Extract zone from text (e.g. "(07Z)" or "(05X)" etc.)
    zone_match = re.search(r'\((\d{2}[A-Z])\)', text)
    contract_zone = zone_match.group(1) if zone_match else ""

    # Extract individual Register Tape line items
    # Pattern: Register Tape, store-number (zone), address, Est. Start date, Ad type, price
    rt_pattern = re.findall(
        r"Register Tape\s*\n?([\w][\w\s]*?-\d+)\s*\((\w+)\)\s*\n([^\n]+)\n[^\n]*Est\.\s*Start:\s*\w*\s*(\d{1,2}/\d{1,2}/\d{4})\s*\n(Single|Double)\s+Ad[^\$]*\$([\d,]+\.\d{2})",
        text, re.DOTALL
    )

    if rt_pattern:
        for store_num, zone, addr, est_start, ad_type, price in rt_pattern:
            price_val = 0
            try:
                price_val = float(price.replace(",", "").strip())
            except:
                pass
            entry = {
                "contract_number": contract.get("contract_number", ""),
                "date": contract.get("date", ""),
                "business_name": contract.get("business_name", ""),
                "contact_name": contract.get("contact_name", ""),
                "contact_email": contract.get("contact_email", ""),
                "contact_phone": contract.get("contact_phone", ""),
                "sales_rep": contract.get("sales_rep", ""),
                "store_name": store_num.strip().split("-")[0].strip() if "-" in store_num else "",
                "store_number": store_num.strip().split("-")[-1] if "-" in store_num else "",
                "zone": zone if re.match(r'\d{2}[A-Z]', zone) else contract_zone,
                "product_description": f"{ad_type} Ad",
                "total_amount": price_val,
                "payment_date": contract.get("payment_date", ""),
                "address": addr.strip(),
                "extracted_at": datetime.now().isoformat(),
            }
            all_contracts.append(entry)
        
        # If all line items have $0, use total contract amount spread across items
        line_totals = sum(e.get("total_amount", 0) for e in all_contracts if e.get("contract_number") == contract.get("contract_number"))
        if line_totals == 0 and contract.get("total_amount"):
            matching = [e for e in all_contracts if e.get("contract_number") == contract.get("contract_number")]
            per_item = round(contract["total_amount"] / len(matching), 2) if matching else 0
            for e in matching:
                e["total_amount"] = per_item
    else:
        # Single store or couldn't parse line items - save as one entry with contract total
        contract.setdefault("store_name", "")
        contract.setdefault("store_number", "")
        contract.setdefault("product_description", "")
        contract["zone"] = contract_zone
        contract["extracted_at"] = datetime.now().isoformat()
        # Add contract date if not already set (from PDF extraction)
        if not entry.get("extracted_at") and entry.get("date"):
            entry["extracted_at"] = entry["date"]
        elif not entry.get("extracted_at"):
            entry["extracted_at"] = datetime.now().isoformat()
        all_contracts.append(entry)

    # Add extracted_at to main contract record too
    if not contract.get("extracted_at") and contract.get("date"):
        contract["extracted_at"] = contract.get("date")
    elif not contract.get("extracted_at"):
        contract["extracted_at"] = datetime.now().isoformat()
    
    biz = contract.get("business_name", "?")
    total = contract.get("total_amount", 0) or 0
    rep = contract.get("sales_rep", "?")
    print(f'  ✅ {contract.get("contract_number")}: {biz} - {rep} - ${total:,.0f}')

print(f"\nTotal line items: {len(all_contracts)}")

# Save
with open(pwa_contracts, "w") as f:
    json.dump({"contracts": all_contracts, "last_scan": datetime.now().isoformat()}, f, indent=2, default=str)
print(f"Saved to {pwa_contracts}")
