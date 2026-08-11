#!/bin/bash
# Weekly testimonials database refresh script

cd /Users/tylervansant/.openclaw/workspace

echo "🔄 Refreshing testimonials database..."
python3 scripts/testimonial_search.py --refresh

echo "📦 Committing to git..."
# Stage ONLY the testimonials cache file so unrelated changes
# (contract PDFs, memory notes, state files, submodule bumps) are
# never bundled into the "Update testimonials cache" commit.
TESTIMONIAL_FILE="data/testimonials_cache.json"

if [ -n "$(git status --porcelain -- "$TESTIMONIAL_FILE")" ]; then
  git add -- "$TESTIMONIAL_FILE"
  git commit -m "Update testimonials cache: $(date '+%Y-%m-%d')" || true
  echo "✅ Testimonials cache updated and committed"
else
  echo "ℹ️  No changes to $TESTIMONIAL_FILE — nothing to commit"
fi
