#!/bin/bash
# Updates the Counter Sign API URL in the PWA source and pushes to GitHub
# Called by the service launcher whenever a new tunnel URL is generated

WORKSPACE="/Users/tylervansant/.openclaw/workspace"
PWA_DIR="$WORKSPACE/pwa"
TOOLS_FILE="$PWA_DIR/src/components/Tools.svelte"
TUNNEL_URL_FILE="/tmp/counter-sign-tunnel-url.txt"

if [ ! -f "$TUNNEL_URL_FILE" ]; then
    echo "❌ No tunnel URL file found"
    exit 1
fi

NEW_URL=$(cat "$TUNNEL_URL_FILE")
if [ -z "$NEW_URL" ]; then
    echo "❌ Empty tunnel URL"
    exit 1
fi

# Update the hardcoded URL in Tools.svelte
cd "$PWA_DIR"
sed -i '' "s|: 'https://[a-zA-Z0-9-]*\.trycloudflare\.com'|: '${NEW_URL}'|g" "$TOOLS_FILE"

# Check if anything changed
if git diff --quiet "$TOOLS_FILE"; then
    echo "✅ URL already up to date: $NEW_URL"
    exit 0
fi

# Commit and push
git add "$TOOLS_FILE"
git commit -m "auto: Update Counter Sign tunnel URL to $NEW_URL"
git push origin main

echo "✅ Updated and pushed: $NEW_URL"
