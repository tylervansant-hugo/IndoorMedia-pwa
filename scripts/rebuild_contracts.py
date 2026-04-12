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

    # Helper to build a contract entry
    def make_entry(**overrides):
        entry = {
            "contract_number": contract.get("contract_number", ""),
            "date": contract.get("date", ""),
            "business_name": contract.get("business_name", ""),
            "contact_name": contract.get("contact_name", ""),
            "contact_email": contract.get("contact_email", ""),
            "contact_phone": contract.get("contact_phone", ""),
            "sales_rep": contract.get("sales_rep", ""),
            "store_name": "",
            "store_number": "",
            "zone": contract_zone,
            "product_description": "",
            "total_amount": 0,
            "payment_date": contract.get("payment_date", ""),
            "address": contract.get("address", ""),
            "extracted_at": contract.get("date", datetime.now().isoformat()),
        }
        entry.update(overrides)
        return entry

    if rt_pattern:
        for store_num, zone, addr, est_start, ad_type, price in rt_pattern:
            price_val = 0
            try:
                price_val = float(price.replace(",", "").strip())
            except:
                pass
            entry = make_entry(
                store_name=store_num.strip().split("-")[0].strip() if "-" in store_num else "",
                store_number=store_num.strip().split("-")[-1] if "-" in store_num else "",
                zone=zone if re.match(r'\d{2}[A-Z]', zone) else contract_zone,
                product_description=f"{ad_type} Ad",
                total_amount=price_val,
                address=addr.strip(),
            )
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
        entry = make_entry(
            product_description="",
            total_amount=contract.get("total_amount", 0),
        )
        all_contracts.append(entry)

    # Extract digital products: FindLocal, ReviewBoost, LoyaltyBoost, DigitalBoost
    digital_pattern = re.findall(
        r"(FindLocal|ReviewBoost|LoyaltyBoost|DigitalBoost)\s*\n([^\n]*)\n[^\n]*Est\.\s*Start:\s*(\S+)\s*\n([^\n]*)\n?\s*\$?([\d,]+\.\d{2})",
        text
    )
    for product, addr, est_start, duration, price in digital_pattern:
        price_val = 0
        try:
            price_val = float(price.replace(",", "").strip())
        except:
            pass
        entry = make_entry(
            product_description=product,
            total_amount=price_val,
            address=addr.strip(),
            product_type="digital",
        )
        all_contracts.append(entry)
    
    biz = contract.get("business_name", "?")
    total = contract.get("total_amount", 0) or 0
    rep = contract.get("sales_rep", "?")
    print(f'  ✅ {contract.get("contract_number")}: {biz} - {rep} - ${total:,.0f}')

print(f"\nTotal line items (raw): {len(all_contracts)}")

# Deduplicate: same contract_number + store_number + product_description = duplicate
seen = set()
deduped = []
for c in all_contracts:
    key = (c.get("contract_number",""), c.get("store_number",""), c.get("product_description",""), str(c.get("total_amount",0)))
    if key not in seen:
        seen.add(key)
        deduped.append(c)
    else:
        print(f"  🔄 Deduped: {c.get('contract_number')} | {c.get('business_name')} | {c.get('product_description')} | ${c.get('total_amount',0):,.0f}")

all_contracts = deduped
print(f"Total line items (after dedup): {len(all_contracts)}")

# Save
with open(pwa_contracts, "w") as f:
    json.dump({"contracts": all_contracts, "last_scan": datetime.now().isoformat()}, f, indent=2, default=str)
print(f"Saved to {pwa_contracts}")
