#!/usr/bin/env python3
"""
Scan Gmail for ALL IndoorMedia signed contracts in zones 07Y and 07Z,
going back to 2023. Downloads each contract PDF, extracts fields + zone,
filters to 07Y/07Z, and writes a JSON + readable report grouped by rep.

Usage:
  GOG_ACCOUNT=tyler.vansant@indoormedia.com python3 scripts/scan_7y7z_historical.py [--after 2023/01/01] [--before 2027/01/01] [--limit N]

Reuses the proven gog Gmail + pdftotext pipeline already used by the
contracts scanner. Safe to re-run; it dedupes by contract number.
"""
import subprocess, re, json, os, sys, tempfile, urllib.request, argparse
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT_JSON = ROOT / "data" / "contracts_7y7z_historical.json"
OUT_REPORT = ROOT / "data" / "contracts_7y7z_report.txt"
PDF_CACHE = ROOT / "data" / "contracts_historical_pdfs"
PDF_CACHE.mkdir(exist_ok=True)

ACCOUNT = os.environ.get("GOG_ACCOUNT", "tyler.vansant@indoormedia.com")
TARGET_ZONES = {"07Y", "07Z"}


def log(msg):
    print(msg, flush=True)


def gmail_search(after, before, limit):
    """Return list of message objects for signed-contract emails in range."""
    query = (f'subject:"IndoorMedia Contract Signed" '
             f'from:donotreply@indoormedia.com after:{after} before:{before}')
    cmd = ["gog", "gmail", "messages", "search", query,
           "--max", str(limit), "--json", "--account", ACCOUNT]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        log(f"  search failed: {r.stderr[:200]}")
        return []
    try:
        d = json.loads(r.stdout)
    except json.JSONDecodeError:
        return []
    if isinstance(d, list):
        return d
    return d.get("messages", d.get("results", d.get("threads", [])))


def get_email_body(msg_id):
    cmd = ["gog", "gmail", "messages", "get", msg_id, "--json", "--account", ACCOUNT]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    if r.returncode != 0:
        # fallback to thread get
        cmd = ["gog", "gmail", "get", msg_id, "--json", "--account", ACCOUNT]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if r.returncode != 0:
            return "", ""
    try:
        d = json.loads(r.stdout)
    except json.JSONDecodeError:
        return "", ""
    body = d.get("body", "") or d.get("snippet", "")
    if not body:
        payload = d.get("message", {}).get("payload", {})
        body = payload.get("body", {}).get("data", "")
    subject = d.get("subject", "")
    if not subject:
        subject = d.get("message", {}).get("subject", "")
    return body or "", subject or ""


def extract_pdf_link(body):
    m = re.search(r'https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)', body)
    if m:
        return m.group(1)
    return None


def download_pdf(file_id):
    dest = PDF_CACHE / f"{file_id}.pdf"
    if dest.exists() and dest.stat().st_size > 1000:
        return dest
    url = f"https://drive.google.com/uc?id={file_id}&export=download"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = resp.read()
        if len(data) < 1000 or b"%PDF" not in data[:1024]:
            # Possibly a virus-scan interstitial; try gog drive download
            r = subprocess.run(["gog", "drive", "download", file_id, "--out", str(dest),
                                "--account", ACCOUNT], capture_output=True, text=True, timeout=60)
            if dest.exists() and dest.stat().st_size > 1000:
                return dest
            return None
        dest.write_bytes(data)
        return dest
    except Exception:
        try:
            r = subprocess.run(["gog", "drive", "download", file_id, "--out", str(dest),
                                "--account", ACCOUNT], capture_output=True, text=True, timeout=60)
            if dest.exists() and dest.stat().st_size > 1000:
                return dest
        except Exception:
            pass
        return None


def pdf_text(pdf_path):
    r = subprocess.run(["pdftotext", str(pdf_path), "-"], capture_output=True, text=True, timeout=30)
    return r.stdout or ""


def parse_contract(text, subject):
    c = {"contract_number": None, "date": None, "sales_rep": None,
         "business_name": None, "contact_name": None, "store_number": None,
         "zone": "", "product_description": None, "total_amount": None}

    m = re.search(r"Contract #:\s*(\S+)", text)
    if m:
        c["contract_number"] = m.group(1)
    else:
        m = re.search(r'([A-Z]\d{6}[A-Z])', subject)
        if m:
            c["contract_number"] = m.group(1)

    m = re.search(r"Contract #:.*?\n(\d{1,2}/\d{1,2}/\d{4})", text)
    if m:
        try:
            c["date"] = datetime.strptime(m.group(1), "%m/%d/%Y").strftime("%Y-%m-%d")
        except Exception:
            pass

    m = re.search(r"Sales Representative:\s*\n(.+?)\s*\|", text)
    if m:
        c["sales_rep"] = m.group(1).strip()
    if not c["sales_rep"]:
        m = re.search(r"Signature Sales Rep\s+([^\[\n]+)", text)
        if m:
            c["sales_rep"] = re.sub(r'\[.*?\]', '', m.group(1)).strip()

    # Zone: explicit "(07Z)" pattern, or store number like FME07Z-0165
    zm = re.search(r'\((\d{2}[A-Z])\)', text)
    if zm:
        c["zone"] = zm.group(1)
    else:
        zm = re.search(r'[A-Z]{2,3}(\d{2}[A-Z])-?\d', text)
        if zm:
            c["zone"] = zm.group(1)
    # also try subject like [07Z - A3 - ...]
    if not c["zone"]:
        zm = re.search(r'\[(\d{2}[A-Z])\s*-', subject)
        if zm:
            c["zone"] = zm.group(1)

    # store number e.g. FME07Z-0165 or QFC07Y-0206
    sm = re.search(r'([A-Z]{2,3}\d{2}[A-Z]-\d{3,4})', text)
    if sm:
        c["store_number"] = sm.group(1)

    m = re.search(r"Advertiser's Business Name:\s*\n?\s*(.+?)(?:\n|$)", text)
    if m:
        c["business_name"] = m.group(1).strip()
    if not c["business_name"]:
        m = re.search(r'Business Name\s+([^\n]+?)(?:Customer Email|$)', text)
        if m:
            c["business_name"] = m.group(1).strip()

    m = re.search(r"Advertiser's Printed Name:\s*\n?\s*(.+?)(?:\n|$)", text)
    if m:
        c["contact_name"] = m.group(1).strip()

    if "Register Tape" in text:
        am = re.search(r'(Single|Double)\s+Ad', text)
        c["product_description"] = f"Register Tape {am.group(1) if am else ''} Ad".strip()
    if re.search(r'digital\s*boost', text, re.I):
        c["product_description"] = ((c["product_description"] + " + DigitalBoost")
                                    if c["product_description"] else "DigitalBoost")

    m = re.search(r"Contract Total\s*\$?([\d,]+\.?\d*)", text)
    if not m:
        m = re.search(r"Net Price\s*\$?([\d,]+\.?\d*)", text)
    if m:
        try:
            c["total_amount"] = float(m.group(1).replace(",", ""))
        except ValueError:
            pass
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--after", default="2023/01/01")
    ap.add_argument("--before", default="2027/01/01")
    ap.add_argument("--limit", type=int, default=1000)
    ap.add_argument("--max-emails", type=int, default=0, help="cap processed emails (smoke test)")
    args = ap.parse_args()

    log(f"Searching {args.after} -> {args.before} (account {ACCOUNT})")

    # search year-by-year to avoid huge single queries
    msgs = []
    start_year = int(args.after.split("/")[0])
    end_year = int(args.before.split("/")[0])
    for yr in range(start_year, end_year + 1):
        a = f"{yr}/01/01" if yr > start_year else args.after
        b = f"{yr+1}/01/01" if yr < end_year else args.before
        ym = gmail_search(a, b, args.limit)
        log(f"  {yr}: {len(ym)} emails")
        msgs.extend(ym)

    # dedupe by id
    seen_ids = set()
    uniq = []
    for m in msgs:
        mid = m.get("id") or m.get("messageId") or m.get("threadId")
        if mid and mid not in seen_ids:
            seen_ids.add(mid)
            uniq.append((mid, m))
    log(f"Total unique emails: {len(uniq)}")

    if args.max_emails:
        uniq = uniq[:args.max_emails]
        log(f"Smoke test: limiting to {len(uniq)} emails")

    results = []
    by_contract = {}
    processed = 0
    for mid, meta in uniq:
        processed += 1
        if processed % 25 == 0:
            log(f"  ...processed {processed}/{len(uniq)}, matches so far: {len(results)}")
        body, subject = get_email_body(mid)
        if not body and not subject:
            continue
        file_id = extract_pdf_link(body)
        text = ""
        if file_id:
            pdf = download_pdf(file_id)
            if pdf:
                text = pdf_text(pdf)
        # parse from PDF text primarily, subject as backup
        c = parse_contract(text, subject)
        if c["zone"] not in TARGET_ZONES:
            continue
        cn = c["contract_number"] or mid
        if cn in by_contract:
            continue
        by_contract[cn] = c
        results.append(c)

    log(f"\nDONE. {len(results)} contracts in 07Y/07Z.")

    OUT_JSON.write_text(json.dumps({"generated": datetime.now().isoformat(),
                                    "range": f"{args.after}..{args.before}",
                                    "count": len(results),
                                    "contracts": results}, indent=2))

    # Build readable report grouped by rep
    by_rep = {}
    for c in results:
        rep = c.get("sales_rep") or "(unknown rep)"
        by_rep.setdefault(rep, []).append(c)

    lines = []
    lines.append(f"IndoorMedia 07Y/07Z Contracts — {args.after} to {args.before}")
    lines.append(f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Total contracts: {len(results)}")
    grand_total = sum(c.get("total_amount") or 0 for c in results)
    lines.append(f"Total revenue: ${grand_total:,.2f}")
    lines.append("=" * 60)
    for rep in sorted(by_rep, key=lambda r: -sum(c.get("total_amount") or 0 for c in by_rep[r])):
        cs = sorted(by_rep[rep], key=lambda c: c.get("date") or "")
        rev = sum(c.get("total_amount") or 0 for c in cs)
        lines.append(f"\n{rep} — {len(cs)} contracts — ${rev:,.2f}")
        lines.append("-" * 50)
        for c in cs:
            lines.append(f"  {c.get('date','?')} | {c.get('zone','?')} {c.get('store_number','') or ''} | "
                         f"{c.get('business_name','?')} | {c.get('contract_number','?')} | "
                         f"${(c.get('total_amount') or 0):,.2f}")
    report = "\n".join(lines)
    OUT_REPORT.write_text(report)
    log(f"\nWrote {OUT_JSON}")
    log(f"Wrote {OUT_REPORT}")
    print("\n" + report)


if __name__ == "__main__":
    main()
