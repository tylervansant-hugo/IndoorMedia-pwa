#!/usr/bin/env python3
"""
Telegram Mini App Wrapper
Adds mini app button to Telegram bots
"""

import requests
import sys

RATES_TOKEN = "8538356016:AAE3nlsh-He8JRR-9JQGS1InprYlgjZ3tWM"
PROSPECT_TOKEN = "8781563020:AAHm_khWUcjngvS0zuNewBbpMM-p2zuMjzI"

# Web app URL (for Telegram to call)
# NOTE: For local development, use ngrok or tunnel
# Format: https://yourdomain.com/miniapp
WEB_APP_URL = "http://localhost:5000/miniapp"

def set_mini_app(token, app_name, description):
    """Set mini app for a bot."""
    url = f"https://api.telegram.org/bot{token}/setMyDefaultAdministratorRights"
    
    # Actually, Telegram mini apps are set via setWebAppInfo, not this endpoint
    # For now, we'll just provide setup instructions
    print(f"✅ To add mini app to {app_name}:")
    print(f"   1. Go to @BotFather")
    print(f"   2. Select your bot")
    print(f"   3. Edit menu button → Web App")
    print(f"   4. URL: {WEB_APP_URL}")
    print()


if __name__ == "__main__":
    print("🎯 Telegram Mini App Setup\n")
    set_mini_app(RATES_TOKEN, "IndoorMediaRatesBot", "Store pricing lookup")
    set_mini_app(PROSPECT_TOKEN, "IndoorMediaProspectBot", "Find today's deals")
    
    print("\n📝 NOTES:")
    print("   • API running on: http://localhost:5000")
    print("   • Mini app file: scripts/miniapp.html")
    print("   • For production, use ngrok: ngrok http 5000")
    print("   • Then update WEB_APP_URL above with ngrok URL")
