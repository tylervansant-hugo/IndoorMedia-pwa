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

# Step 4: Commit, build, and DEPLOY to GitHub Pages (gh-pages branch).
# IMPORTANT: the LIVE site is served from the pwa/ app, and BOTH the workspace
# root repo and pwa/ push to the SAME GitHub repo + gh-pages branch. Building/
# deploying from the root src/ app would CLOBBER the live pwa build. So we:
#   1) mirror the fresh contracts.json into pwa/public/data
#   2) build + deploy from pwa/ (force) so gh-pages stays the real app
cd /Users/tylervansant/.openclaw/workspace

# Keep the pwa copy in sync with the freshly-rebuilt data files.
cp -f public/data/contracts.json pwa/public/data/contracts.json 2>> /tmp/contracts_scan.log

if ! git diff --quiet public/data/contracts.json data/contracts.json; then
    git add public/data/contracts.json data/contracts.json
    git commit -m "auto: Nightly contracts sync $(date +%Y-%m-%d)" >> /tmp/contracts_scan.log 2>&1
    git push origin main >> /tmp/contracts_scan.log 2>&1

    # Build + deploy the REAL app from pwa/ (this is what the live site serves).
    cd /Users/tylervansant/.openclaw/workspace/pwa
    git add public/data/contracts.json >> /tmp/contracts_scan.log 2>&1
    git commit -m "auto: Nightly contracts sync $(date +%Y-%m-%d)" >> /tmp/contracts_scan.log 2>&1
    git push origin main >> /tmp/contracts_scan.log 2>&1
    npm run build >> /tmp/contracts_scan.log 2>&1 && \
    npx gh-pages -d dist -f >> /tmp/contracts_scan.log 2>&1 && \
    echo "✅ Contracts updated, pushed, and deployed to gh-pages (pwa)" >> /tmp/contracts_scan.log || \
    echo "⚠️ Contracts committed but pwa build/deploy step failed — check log" >> /tmp/contracts_scan.log
    cd /Users/tylervansant/.openclaw/workspace
else
    echo "✅ No changes to contracts" >> /tmp/contracts_scan.log
fi
