#!/bin/bash
# Wait for the testimonial-details scrape to finish, then rebuild + deploy the
# PWA so the live app has the ad images + contact info baked in. Idempotent:
# exits early if the scrape is still running (cron will retry next tick).
set -e
cd "$(dirname "$0")/.."   # -> pwa/

# Still scraping? bail; try again next cron tick.
if pgrep -f "scrape_testimonial_details.py" >/dev/null 2>&1; then
  echo "$(date): scrape still running — will retry."
  exit 0
fi

# Already finalized for this dataset? (marker vs data mtime)
DATA="public/data/testimonials_slim.json"
MARK="public/data/.testimonial_ads_deployed"
if [ -f "$MARK" ] && [ "$MARK" -nt "$DATA" ]; then
  echo "$(date): already deployed for current dataset."
  exit 0
fi

IMGS=$(ls public/testimonial_ads/ 2>/dev/null | wc -l | tr -d ' ')
echo "$(date): scrape done, $IMGS ad images. Building + deploying..."

npm run build
git add -A
git commit -q -m "Testimonial enrichment: ad images + contact info ($IMGS ads) for quote PDF" || true
npx gh-pages -d dist -f
git push origin main || true

touch "$MARK"
BUNDLE=$(grep -o 'index-[A-Za-z0-9_]*\.js' dist/index.html | head -1)
echo "$(date): DEPLOYED. bundle=$BUNDLE imgs=$IMGS"
echo "DEPLOYED bundle=$BUNDLE imgs=$IMGS" > /tmp/testi_finalize_done.txt
