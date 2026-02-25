#!/usr/bin/env python3
"""
IndoorMediaProspectBot - Find Today's Deal
Telegram bot for field reps to get top 10 prospects near a store
Input: Store number
Output: Ranked prospects with likelihood score + advertising signals
"""

import json
import logging
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

WORKSPACE = Path(__file__).parent.parent
DATA_DIR = WORKSPACE / "data" / "store-rates"
STORES_FILE = DATA_DIR / "stores.json"

TOKEN = "8538356016:AAE3nlsh-He8JRR-9JQGS1InprYlgjZ3tWM"


# Import prospecting tool
import sys
sys.path.insert(0, str(WORKSPACE / "scripts"))
from prospecting_tool_enhanced import ProspectingToolEnhanced


class ProspectingBot:
    """Telegram bot for prospecting."""
    
    def __init__(self):
        """Initialize."""
        self.tool = ProspectingToolEnhanced()
        logger.info("✅ ProspectingBot initialized")
    
    def get_top_prospects(self, store_num: str, limit: int = 10) -> List[Dict]:
        """Get top prospects for a store."""
        try:
            return self.tool.run_prospecting(store_num, limit)
        except Exception as e:
            logger.error(f"Error: {e}")
            return []
    
    def format_prospect_message(self, prospects: List[Dict], store_info: Dict) -> str:
        """Format prospects for Telegram."""
        lines = [
            f"🎯 *TODAY'S DEALS* | {store_info['GroceryChain']}",
            f"📍 {store_info['City']}, {store_info['State']}",
            f"📦 Store: {store_info['StoreName']}\n",
        ]
        
        for i, prospect in enumerate(prospects, 1):
            score = prospect['likelihood_score']
            
            # Emoji rating based on score
            if score >= 80:
                emoji = "🔥"  # Hot prospect
            elif score >= 70:
                emoji = "⭐"  # Good prospect
            else:
                emoji = "👀"  # Decent prospect
            
            lines.append(f"{emoji} *{i}. {prospect['name']}* ({score}/100)")
            lines.append(f"   📞 {prospect['phone']}")
            lines.append(f"   📍 {prospect['address']}")
            lines.append(f"   📏 {prospect.get('distance_miles', 'N/A')} miles")
            
            # Advertising signal
            if prospect.get('advertising_signal', {}).get('found_advertising'):
                lines.append(f"   🎯 *ADVERTISING ACTIVE* ({prospect['advertising_signal'].get('source', 'Multiple channels')})")
            
            lines.append("")
        
        return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command."""
    help_text = """
🎯 *IndoorMediaProspectBot*
_Find Today's Deal_

*How to use:*
Send a store number to get top 10 prospects nearby.

*Formats:*
• Store #: `FME07Z-0236`
• Or: `FME07Y-0165`

*What you get:*
✓ Top 10 prospects ranked by likelihood (0-100)
✓ Distance from store (within 2 miles)
✓ Google rating + reviews
✓ Advertising signals (Greet Magazine, etc.)
✓ Phone number for outreach

*Commands:*
/help — This message
/examples — Sample queries

🚀 Send a store number to get started!
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def examples(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show example queries."""
    examples_text = """
📚 *Example Queries:*

`FME07Z-0236` — Vancouver, WA Fred Meyer
`SAF07Y-1073` — Beaverton, OR Safeway
`FME07Y-0035` — Beaverton, OR Fred Meyer
`HAG07X-3430` — Bellingham, WA Haggen

Try any of these to see how it works!
    """
    await update.message.reply_text(examples_text, parse_mode="Markdown")


async def handle_store_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle store number query."""
    text = update.message.text.strip().upper()
    
    # Validate store format (e.g., FME07Y-0165)
    if not (len(text) >= 9 and text[3:4] == '0' and text[6:7] == '-'):
        await update.message.reply_text(
            "❌ Invalid format. Use store number like: `FME07Z-0236`",
            parse_mode="Markdown"
        )
        return
    
    # Acknowledge
    processing = await update.message.reply_text("⏳ Finding today's deals...")
    
    try:
        bot = ProspectingBot()
        
        # Get prospects
        prospects = bot.get_top_prospects(text, limit=10)
        
        if not prospects:
            await processing.edit_text("❌ Store not found or no prospects nearby. Check the store number.")
            return
        
        # Get store info
        store = bot.tool.get_store_info(text)
        if not store:
            await processing.edit_text("❌ Store not found")
            return
        
        # Format message
        message = bot.format_prospect_message(prospects, store)
        
        # Update with results
        await processing.edit_text(message, parse_mode="Markdown")
        
        # Save for context
        context.user_data['last_store'] = store
        context.user_data['last_prospects'] = prospects
    
    except Exception as e:
        logger.error(f"Error: {e}")
        await processing.edit_text(f"❌ Error: {str(e)[:100]}")


def main():
    """Start the bot."""
    logger.info("🎯 IndoorMediaProspectBot starting...")
    
    app = Application.builder().token(TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("examples", examples))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_store_query))
    
    logger.info("✅ IndoorMediaProspectBot is running. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
        sys.exit(0)
