#!/bin/bash
# Nightly 8 PM contracts scan + PWA update
export PATH="/opt/homebrew/bin:$PATH"
cd /Users/tylervansant/.openclaw/workspace

# Step 1: Scan Gmail for new contract emails, download PDFs, create calendar events
python3 scripts/contract_calendar.py --newer-than 2d >> /tmp/contracts_scan.log 2>&1

# Step 2: Re-parse all PDFs and rebuild contracts.json for PWA
python3 scripts/rebuild_contracts.py >> /tmp/contracts_scan.log 2>&1

# Step 3: Push updated contracts to GitHub (Vercel auto-deploys)
cd pwa
if ! git diff --quiet public/data/contracts.json; then
    git add public/data/contracts.json
    git commit -m "auto: Nightly contracts sync $(date +%Y-%m-%d)"
    git push origin main
    echo "✅ Contracts updated and pushed" >> /tmp/contracts_scan.log
else
    echo "✅ No new contracts" >> /tmp/contracts_scan.log
fi
