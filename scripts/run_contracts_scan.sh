#!/bin/bash
# Nightly 8 PM contracts scan + PWA update
export PATH="/opt/homebrew/bin:$PATH"
cd /Users/tylervansant/.openclaw/workspace

# Step 1: Scan Gmail for new contract emails, download PDFs, create calendar events
python3 scripts/contract_calendar.py --newer-than 2d >> /tmp/contracts_scan.log 2>&1

# Step 2: Re-parse all PDFs and rebuild contracts.json for PWA (now uses contract date, not extraction time)
python3 scripts/rebuild_contracts.py >> /tmp/contracts_scan.log 2>&1

# Step 3: Generate report of truly new contracts (by extraction timestamp)
# Note: This shows contracts extracted in the last 25 hours; old contracts re-parsed won't show as "new"
python3 scripts/report_new_contracts.py > /tmp/contracts_report.txt 2>&1

# Extract just the top section (new contracts, not all re-extractions)
head -50 /tmp/contracts_report.txt

# Step 4: Push updated contracts to GitHub (Vercel auto-deploys)
cd pwa
if ! git diff --quiet public/data/contracts.json; then
    git add public/data/contracts.json
    git commit -m "auto: Nightly contracts sync $(date +%Y-%m-%d)"
    git push origin main
    echo "✅ Contracts updated and pushed" >> /tmp/contracts_scan.log
else
    echo "✅ No changes to contracts" >> /tmp/contracts_scan.log
fi
