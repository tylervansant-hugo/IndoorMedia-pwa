#!/bin/bash
# Counter Sign API + Cloudflare Tunnel launcher
# Starts Flask API on port 3333 and creates a Cloudflare tunnel
# Saves the tunnel URL to /tmp/counter-sign-tunnel-url.txt

WORKSPACE="/Users/tylervansant/.openclaw/workspace"
VENV="$WORKSPACE/.venv_counter/bin/python"
API="$WORKSPACE/api/counter_sign_server.py"
PORT=3333
TUNNEL_URL_FILE="/tmp/counter-sign-tunnel-url.txt"

# Kill any existing instances
pkill -f "counter_sign_server.py" 2>/dev/null
pkill -f "cloudflared tunnel.*$PORT" 2>/dev/null
sleep 1

# Start Flask API
echo "🎨 Starting Counter Sign API on port $PORT..."
cd "$WORKSPACE"
$VENV $API > /tmp/counter-sign-api.log 2>&1 &
API_PID=$!

# Wait for API to be ready
for i in $(seq 1 10); do
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        echo "✅ API ready (PID $API_PID)"
        break
    fi
    sleep 1
done

# Start Cloudflare tunnel
echo "🌐 Starting Cloudflare tunnel..."
cloudflared tunnel --url http://localhost:$PORT > /tmp/cloudflared-counter.log 2>&1 &
TUNNEL_PID=$!

# Wait for tunnel URL
for i in $(seq 1 15); do
    TUNNEL_URL=$(grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com' /tmp/cloudflared-counter.log 2>/dev/null | head -1)
    if [ -n "$TUNNEL_URL" ]; then
        echo "$TUNNEL_URL" > "$TUNNEL_URL_FILE"
        echo "✅ Tunnel ready: $TUNNEL_URL (PID $TUNNEL_PID)"
        echo "📄 URL saved to $TUNNEL_URL_FILE"
        break
    fi
    sleep 1
done

if [ -z "$TUNNEL_URL" ]; then
    echo "❌ Tunnel failed to start"
    exit 1
fi

echo ""
echo "🎉 Counter Sign Generator is LIVE!"
echo "   Local:  http://localhost:$PORT"
echo "   Public: $TUNNEL_URL"
echo ""
echo "PIDs: API=$API_PID, Tunnel=$TUNNEL_PID"

# Auto-update PWA with new tunnel URL and push
echo "📤 Updating PWA with new tunnel URL..."
bash "$WORKSPACE/scripts/update_tunnel_url.sh"
