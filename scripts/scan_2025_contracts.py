#!/usr/bin/env python3
"""Download all 2025 IndoorMedia contract PDFs from Gmail."""

import subprocess, json, re, os
from pathlib import Path

CONTRACTS_DIR = Path(__file__).parent.parent / "data" / "contracts"
PROCESSED_FILE = CONTRACTS_DIR / "processed.json"
CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)

# Load processed
processed = {}
if PROCESSED_FILE.exists():
    with open(PROCESSED_FILE) as f:
        processed = json.load(f)

# Search in batches to get all 2025 emails
periods = [
    ("2024-12-31", "2025-04-01"),
    ("2025-03-31", "2025-07-01"),
    ("2025-06-30", "2025-10-01"),
    ("2025-09-30", "2026-01-01"),
]

all_msgs = {}
for after, before in periods:
    result = subprocess.run([
        "gog", "gmail", "messages", "search",
        f'subject:"IndoorMedia Contract Signed" from:donotreply@indoormedia.com after:{after} before:{before}',
        "--max", "200", "--json"
    ], capture_output=True, text=True, timeout=60)
    data = json.loads(result.stdout)
    for m in data.get("messages", []):
        mid = m.get("id", "")
        if mid:
            all_msgs[mid] = m

print(f"Found {len(all_msgs)} unique emails from 2025")

new_count = 0
skip_count = 0
fail_count = 0

for msg_id, msg in sorted(all_msgs.items(), key=lambda x: x[1].get("date", "")):
    subject = msg.get("subject", "")
    date = msg.get("date", "")
    
    m = re.search(r"([A-Z]\d{6}[A-Z])", subject)
    if not m:
        continue
    contract_num = m.group(1)
    
    pdf_path = CONTRACTS_DIR / f"{contract_num}.pdf"
    if pdf_path.exists():
        skip_count += 1
        continue
    
    if contract_num in processed and processed[contract_num].get("downloaded"):
        skip_count += 1
        continue
    
    # Get email body
    try:
        body_result = subprocess.run(
            ["gog", "gmail", "show", msg_id, "--json"],
            capture_output=True, text=True, timeout=30
        )
        body_data = json.loads(body_result.stdout)
        body_text = body_data.get("body", body_data.get("text", ""))
        
        drive_match = re.search(r"drive\.google\.com/file/d/([a-zA-Z0-9_-]+)", body_text)
        if drive_match:
            file_id = drive_match.group(1)
            dl_result = subprocess.run(
                ["gog", "drive", "download", file_id, "--out", str(pdf_path)],
                capture_output=True, text=True, timeout=30
            )
            if dl_result.returncode == 0:
                print(f"  ✅ {contract_num} ({date[:10]})")
                processed[contract_num] = {"downloaded": True, "date": date}
                new_count += 1
            else:
                print(f"  ❌ Download failed: {contract_num}")
                fail_count += 1
        else:
            print(f"  ⚠️ No Drive link: {contract_num}")
            fail_count += 1
    except Exception as e:
        print(f"  ❌ Error: {contract_num} - {e}")
        fail_count += 1

# Save processed
with open(PROCESSED_FILE, "w") as f:
    json.dump(processed, f, indent=2)

total_pdfs = len(list(CONTRACTS_DIR.glob("*.pdf")))
print(f"\nNew: {new_count} | Skipped: {skip_count} | Failed: {fail_count}")
print(f"Total PDFs: {total_pdfs}")
