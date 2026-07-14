#!/usr/bin/env python3
"""
One-time backfill: load ALL Matthew Boozer ad proofs from his start (Aug 2025)
to current into pwa/public/data/ad_proofs.json.

Reuses the parsing logic from scan_ad_proofs.py. Searches Gmail specifically for
ad proofs where matthew.boozer@indoormedia.com is a recipient, then merges into
the existing proofs (keeps every other rep's data untouched) and runs the same
dedup (newest proof per contract+store).
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import scan_ad_proofs as S  # reuse parsing + helpers

BOOZER_EMAIL = "matthew.boozer@indoormedia.com"
ACCOUNT = S.ACCOUNT
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "pwa", "public", "data", "ad_proofs.json")


def search_boozer(after="2025/08/01"):
    import subprocess
    query = f'subject:"Ad Proof from IndoorMedia" {BOOZER_EMAIL} after:{after}'
    cmd = ["gog", "gmail", "messages", "search", query,
           "--max", "500", "--account", ACCOUNT, "--json", "--no-input"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        print("search err:", r.stderr, file=sys.stderr)
        return []
    try:
        return json.loads(r.stdout).get("messages", [])
    except json.JSONDecodeError:
        print("parse err", file=sys.stderr)
        return []


def main():
    existing = {}
    if os.path.exists(OUTPUT):
        with open(OUTPUT) as f:
            for p in json.load(f):
                existing[p["message_id"]] = p

    before = len(existing)
    boozer_before = sum(1 for p in existing.values()
                        if "boozer" in (p.get("rep", "") + str(p.get("reps", ""))).lower())
    print(f"Existing total: {before} | Boozer: {boozer_before}")

    messages = search_boozer()
    print(f"Boozer ad-proof emails found in Gmail: {len(messages)}")

    new_count = 0
    for i, msg in enumerate(messages, 1):
        msg_id = msg.get("id", "")
        if not msg_id or msg_id in existing:
            continue
        details = S.get_email_details(msg_id)
        if not details:
            continue
        subject = details.get("headers", {}).get("subject", msg.get("subject", ""))
        body = details.get("body", "")
        si = S.parse_subject(subject)
        bi = S.parse_body(body)
        recipients = S.extract_recipients(details)
        reps = S.match_reps(recipients)
        proof = {
            "message_id": msg_id,
            "date": msg.get("date", ""),
            "from": details.get("headers", {}).get("from", ""),
            "subject": subject,
            "client_name": si["client_name"],
            "contact_name": S.extract_client_name_from_body(body),
            "client_email": S.extract_client_email(details),
            "location": si["location"],
            "zone": si["zone"],
            "cycle": si["cycle"],
            "contract_number": si["contract_number"],
            "store": bi["store"],
            "ad_size": bi["ad_size"],
            "install_month": bi["install_month"],
            "run_months": bi["run_months"],
            "image_url": bi["image_url"],
            "review_deadline": bi["review_deadline"],
            "recipients": recipients,
            "reps": reps,
        }
        existing[msg_id] = proof
        new_count += 1
        if new_count % 25 == 0:
            print(f"  ...{new_count} new processed (scanned {i}/{len(messages)})")

    # Same dedup as the daily scanner: newest per (contract, store)
    all_proofs = sorted(existing.values(), key=lambda p: p.get("date", ""), reverse=True)
    seen, deduped, dupes = {}, [], 0
    for p in all_proofs:
        key = (p.get("contract_number", ""), p.get("store", ""))
        if key[0] and key in seen:
            dupes += 1
            continue
        if key[0]:
            seen[key] = True
        deduped.append(p)

    with open(OUTPUT, "w") as f:
        json.dump(deduped, f, indent=2)

    boozer_after = sum(1 for p in deduped
                       if "boozer" in (p.get("rep", "") + str(p.get("reps", ""))).lower())
    print(f"Added {new_count} new proofs, removed {dupes} dupes.")
    print(f"Total now: {len(deduped)} | Boozer now: {boozer_after} (was {boozer_before})")


if __name__ == "__main__":
    main()
