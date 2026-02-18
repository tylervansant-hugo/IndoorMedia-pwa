#!/bin/bash
# Weekly testimonials database refresh script

cd /Users/tylervansant/.openclaw/workspace

echo "🔄 Refreshing testimonials database..."
python3 scripts/testimonial_search.py --refresh

echo "📦 Committing to git..."
git add -A
git commit -m "Update testimonials cache: $(date '+%Y-%m-%d')" || true

echo "✅ Testimonials database updated and committed"
