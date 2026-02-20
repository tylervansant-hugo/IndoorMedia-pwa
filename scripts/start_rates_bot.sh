#!/bin/bash
# Start the IndoorMedia Rates Bot

cd "$(dirname "$0")/.."

echo "🐚 Starting IndoorMedia Rates Bot..."
.venv/bin/python3 scripts/telegram_rates_bot.py
