#!/bin/bash
# Counter Sign API + Cloudflare Tunnel Service
# Starts the Flask API, creates a quick tunnel, and auto-updates the PWA with the new URL.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PWA_DIR="$(dirname "$SCRIPT_DIR")"
WORKSPACE_DIR="$(dirname "$PWA_DIR")"
VENV="$PWA_DIR/.venv"
TUNNEL_URL_FILE="$PWA_DIR/.tunnel_url"
LOG_DIR="$PWA_DIR/logs"
API_PID=""
TUNNEL_PID=""

mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

cleanup() {
  log "Shutting down..."
  [[ -n "$API_PID" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "$TUNNEL_PID" ]] && kill "$TUNNEL_PID" 2>/dev/null || true
  wait 2>/dev/null
  exit 0
}
trap cleanup SIGTERM SIGINT EXIT

# Ensure venv exists
if [[ ! -d "$VENV" ]]; then
  log "Creating Python venv..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install flask flask-cors reportlab qrcode pillow PyPDF2 -q
fi

# Start Flask API
log "Starting Counter Sign API on port 3333..."
"$VENV/bin/python3" "$PWA_DIR/api/counter_sign_server.py" \
  >> "$LOG_DIR/counter_sign_api.log" 2>&1 &
API_PID=$!
sleep 2

# Verify API is up
if ! kill -0 "$API_PID" 2>/dev/null; then
  log "ERROR: API failed to start. Check $LOG_DIR/counter_sign_api.log"
  exit 1
fi
log "API running (PID $API_PID)"

# Start Cloudflare tunnel and capture URL
log "Starting Cloudflare tunnel..."
TUNNEL_LOG="$LOG_DIR/cloudflare_tunnel.log"
cloudflared tunnel --url http://localhost:3333 > "$TUNNEL_LOG" 2>&1 &
TUNNEL_PID=$!

# Wait for tunnel URL (up to 30 seconds)
TUNNEL_URL=""
for i in $(seq 1 30); do
  sleep 1
  TUNNEL_URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUNNEL_LOG" 2>/dev/null | head -1 || true)
  if [[ -n "$TUNNEL_URL" ]]; then
    break
  fi
done

if [[ -z "$TUNNEL_URL" ]]; then
  log "ERROR: Failed to get tunnel URL after 30s"
  exit 1
fi

log "Tunnel URL: $TUNNEL_URL"
echo "$TUNNEL_URL" > "$TUNNEL_URL_FILE"

# Check if URL changed — if so, update the PWA and deploy
OLD_URL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "$PWA_DIR/src/components/Tools.svelte" 2>/dev/null | head -1 || true)

if [[ "$TUNNEL_URL" != "$OLD_URL" ]]; then
  log "Tunnel URL changed ($OLD_URL → $TUNNEL_URL). Updating PWA..."

  # Update both copies
  if [[ -n "$OLD_URL" ]]; then
    sed -i '' "s|$OLD_URL|$TUNNEL_URL|g" "$PWA_DIR/src/components/Tools.svelte"
    sed -i '' "s|$OLD_URL|$TUNNEL_URL|g" "$WORKSPACE_DIR/src/components/Tools.svelte" 2>/dev/null || true
  fi

  # Build and deploy
  cd "$PWA_DIR"
  if command -v npm &>/dev/null; then
    log "Building PWA..."
    npm run build >> "$LOG_DIR/build.log" 2>&1

    log "Deploying to GitHub Pages..."
    git add -A
    git commit -m "auto: update counter sign tunnel URL" --no-verify >> "$LOG_DIR/deploy.log" 2>&1 || true
    git push >> "$LOG_DIR/deploy.log" 2>&1 || log "WARNING: git push failed"
    log "Deploy complete!"
  else
    log "WARNING: npm not found, skipping build/deploy"
  fi
else
  log "Tunnel URL unchanged, no deploy needed."
fi

log "Service ready. API=$API_PID, Tunnel=$TUNNEL_PID"

# Keep running — wait for either process to die
while true; do
  if ! kill -0 "$API_PID" 2>/dev/null; then
    log "API died, restarting..."
    "$VENV/bin/python3" "$PWA_DIR/api/counter_sign_server.py" \
      >> "$LOG_DIR/counter_sign_api.log" 2>&1 &
    API_PID=$!
  fi
  if ! kill -0 "$TUNNEL_PID" 2>/dev/null; then
    log "Tunnel died, restarting..."
    cloudflared tunnel --url http://localhost:3333 > "$TUNNEL_LOG" 2>&1 &
    TUNNEL_PID=$!
    sleep 10
    NEW_URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUNNEL_LOG" 2>/dev/null | tail -1 || true)
    if [[ -n "$NEW_URL" && "$NEW_URL" != "$TUNNEL_URL" ]]; then
      TUNNEL_URL="$NEW_URL"
      echo "$TUNNEL_URL" > "$TUNNEL_URL_FILE"
      log "New tunnel URL: $TUNNEL_URL — updating PWA..."
      cd "$PWA_DIR"
      CURRENT_URL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "src/components/Tools.svelte" | head -1 || true)
      [[ -n "$CURRENT_URL" ]] && sed -i '' "s|$CURRENT_URL|$TUNNEL_URL|g" "src/components/Tools.svelte"
      [[ -n "$CURRENT_URL" ]] && sed -i '' "s|$CURRENT_URL|$TUNNEL_URL|g" "$WORKSPACE_DIR/src/components/Tools.svelte" 2>/dev/null || true
      npm run build >> "$LOG_DIR/build.log" 2>&1 && \
        git add -A && \
        git commit -m "auto: update counter sign tunnel URL" --no-verify >> "$LOG_DIR/deploy.log" 2>&1 && \
        git push >> "$LOG_DIR/deploy.log" 2>&1 || log "WARNING: auto-deploy failed"
    fi
  fi
  sleep 30
done
