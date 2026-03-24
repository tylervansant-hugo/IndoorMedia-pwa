#!/bin/bash
# Start Counter Sign Generator API server

cd "$(dirname "$0")"

echo "🎨 Starting Counter Sign Generator API..."
echo ""

# Check if flask is installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "📦 Installing Flask..."
    python3 -m pip install flask -q
fi

# Run the server
python3 api/counter_sign_server.py
