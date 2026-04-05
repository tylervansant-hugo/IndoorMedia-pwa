#!/bin/bash
# Daily 3 PM PDT ad proofs scan + PWA update
export PATH="/opt/homebrew/bin:$PATH"
cd /Users/tylervansant/.openclaw/workspace

# Scan Gmail for new ad proof emails
python3 scripts/scan_ad_proofs.py >> /tmp/ad_proofs_scan.log 2>&1

# Push updated proofs to GitHub Pages
cd pwa
if ! git diff --quiet public/data/ad_proofs.json; then
    git add public/data/ad_proofs.json
    git commit -m "auto: Daily ad proofs sync $(date +%Y-%m-%d)"
    
    # Build and deploy
    rm -rf dist
    npm run build >> /tmp/ad_proofs_scan.log 2>&1
    npx gh-pages -d dist --no-history >> /tmp/ad_proofs_scan.log 2>&1
    
    git push origin main >> /tmp/ad_proofs_scan.log 2>&1
    echo "✅ Ad proofs updated and deployed" >> /tmp/ad_proofs_scan.log
else
    echo "✅ No new ad proofs" >> /tmp/ad_proofs_scan.log
fi
