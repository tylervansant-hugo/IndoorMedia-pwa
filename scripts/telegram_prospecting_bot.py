#!/usr/bin/env python3
"""
IndoorMediaProspectBot - Find Today's Deal
Telegram bot for field reps to get top 10 prospects near a store
with b2bappointments integration and mappoint mapping.
"""

import json
import logging
import sys
import os
import asyncio
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

WORKSPACE = Path(__file__).parent.parent
DATA_DIR = WORKSPACE / "data" / "store-rates"
STORES_FILE = DATA_DIR / "stores.json"

TOKEN = "8781563020:AAHm_khWUcjngvS0zuNewBbpMM-p2zuMjzI"

# Load stores once
with open(STORES_FILE) as f:
    STORES_LIST = json.load(f)
STORES = {s["StoreName"]: s for s in STORES_LIST}

# Tracking for prospects that have been saved
PROSPECT_TRACKING = "data/prospect_tracking.json"
Path("data").mkdir(exist_ok=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command."""
    help_text = """
🎯 *IndoorMediaProspectBot*
_Find Today's Deal_

*How to use:*
Send a store number to get top 10 prospects nearby.

*Example:*
`FME07Z-0236`

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
📚 *Example Store Numbers:*

`FME07Z-0236` — Vancouver, WA
`SAF07Y-1073` — Beaverton, OR
`FME07Y-0035` — Beaverton, OR
`HAG07X-3430` — Bellingham, WA

Try any of these to see today's deals!
    """
    await update.message.reply_text(examples_text, parse_mode="Markdown")


async def handle_store_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle store number query."""
    text = update.message.text.strip().upper()
    
    logger.info(f"📥 Received: {text} from user {update.effective_user.id}")
    
    # Validate store format
    if not (len(text) >= 9 and '-' in text):
        await update.message.reply_text(
            "❌ Invalid format. Use store number like: `FME07Z-0236`",
            parse_mode="Markdown"
        )
        return
    
    # Check if store exists
    if text not in STORES:
        await update.message.reply_text(
            f"❌ Store `{text}` not found.\n\nTry: `FME07Z-0236` or use /examples",
            parse_mode="Markdown"
        )
        return
    
    # Acknowledge
    processing = await update.message.reply_text("⏳ Finding today's deals...")
    
    try:
        # Import tool here to avoid startup errors
        from prospecting_tool_enhanced import ProspectingToolEnhanced
        
        tool = ProspectingToolEnhanced()
        
        # Get prospects
        logger.info(f"🔍 Querying prospects for {text}...")
        prospects = tool.run_prospecting(text, limit=10)
        
        if not prospects:
            await processing.edit_text("❌ No prospects found within 2 miles.")
            return
        
        # Get store info
        store = STORES.get(text)
        
        # Format message with results
        lines = [
            f"🎯 *TODAY'S DEALS*",
            f"📍 {store['GroceryChain']} | {store['City']}, {store['State']}",
            f"📦 Store: {text}\n",
        ]
        
        for i, prospect in enumerate(prospects, 1):
            score = prospect['likelihood_score']
            
            # Emoji rating
            if score >= 80:
                emoji = "🔥"
            elif score >= 70:
                emoji = "⭐"
            else:
                emoji = "👀"
            
            lines.append(f"{emoji} *{i}. {prospect['name']}* ({score}/100)")
            lines.append(f"   📞 {prospect['phone']}")
            lines.append(f"   📍 {prospect.get('distance_miles', 'N/A')} mi")
            
            # Advertising signal
            if prospect.get('advertising_signal', {}).get('found_advertising'):
                lines.append(f"   🎯 *ADVERTISING*")
            
            lines.append("")
        
        message = "\n".join(lines)
        
        # Update with results
        await processing.edit_text(message, parse_mode="Markdown")
        
        # Send prospect list with action buttons
        await send_prospects_with_actions(update, prospects, store, text)
        
        logger.info(f"✅ Sent {len(prospects)} prospects")
    
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        await processing.edit_text(f"❌ Error: {str(e)[:100]}")


async def send_prospects_with_actions(
    update: Update,
    prospects: List[Dict],
    store: Dict,
    store_number: str
):
    """Send each prospect with action buttons."""
    city = store.get("City", "").replace(" ", "_")
    store_num = store_number.replace("-", "_")
    
    for i, prospect in enumerate(prospects, 1):
        # Build action buttons
        business_name = prospect.get("name", "Unknown")
        phone = prospect.get("phone", "")
        
        # URL-encode for listing analysis
        analysis_url = f"https://www.indoormedia.com/local-listing-management/?business={urllib.parse.quote(business_name)}"
        
        buttons = [
            [
                InlineKeyboardButton("📁 Save to b2b", callback_data=f"save_b2b_{city}_{store_num}_{i}"),
                InlineKeyboardButton("📊 Analyze", url=analysis_url),
            ],
            [
                InlineKeyboardButton("✅ Booked!", callback_data=f"booked_{city}_{store_num}_{i}"),
            ]
        ]
        
        keyboard = InlineKeyboardMarkup(buttons)
        
        # Format prospect with score
        score = prospect.get('likelihood_score', 0)
        if score >= 80:
            emoji = "🔥"
        elif score >= 70:
            emoji = "⭐"
        else:
            emoji = "👀"
        
        text = f"{emoji} *{business_name}*\n"
        text += f"Score: {score}/100 | Distance: {prospect.get('distance_miles', 'N/A')}mi\n"
        text += f"📞 {phone}"
        
        if prospect.get('advertising_signal', {}).get('found_advertising'):
            text += "\n🎯 *ACTIVELY ADVERTISING*"
        
        await update.effective_chat.send_message(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )


async def handle_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle action button clicks - integrates with b2bappointments & mappoint."""
    query = update.callback_query
    data = query.data
    
    try:
        if data.startswith("save_b2b_"):
            # Parse callback data: save_b2b_City_StoreNum_ProspectIdx
            parts = data.split("_")
            city = parts[2].replace("_", " ")
            store_num = f"{parts[3]}-{parts[4]}" if len(parts) > 4 else parts[3]
            prospect_idx = int(parts[-1])
            
            # Extract business name from message
            message_text = query.message.text
            business_name = message_text.split("*")[1] if "*" in message_text else "Unknown"
            
            # Extract phone number
            phone = "N/A"
            for line in message_text.split("\n"):
                if "📞" in line:
                    phone = line.split("📞")[1].strip()
                    break
            
            await query.answer("💾 Creating contact in b2bappointments...", show_alert=False)
            
            # Import and call b2bappointments automation
            try:
                from b2bappointments_automation import B2BAutomation
                
                automation = B2BAutomation()
                await automation.launch_browser()
                
                success = await automation.create_contact(
                    city=city,
                    store_number=store_num,
                    business_name=business_name,
                    phone=phone,
                    email=f"{business_name.replace(' ', '').lower()}@example.com",  # Placeholder
                    likelihood_score=75,  # Can extract from message if needed
                    category="Prospect"
                )
                
                await automation.close_browser()
                
                if success:
                    await query.edit_message_text(
                        text=query.message.text + "\n✅ Saved to b2bappointments!",
                        parse_mode="Markdown"
                    )
                    logger.info(f"✅ Contact saved: {business_name} in {city}/{store_num}")
                else:
                    await query.edit_message_text(
                        text=query.message.text + "\n⚠️ Error saving to b2bappointments",
                        parse_mode="Markdown"
                    )
                    
            except Exception as e:
                logger.error(f"b2bappointments error: {e}")
                await query.edit_message_text(
                    text=query.message.text + f"\n❌ Error: {str(e)[:50]}",
                    parse_mode="Markdown"
                )
            
        elif data.startswith("booked_"):
            # Mark as appointment booked
            parts = data.split("_")
            city = parts[1].replace("_", " ")
            store_num = f"{parts[2]}-{parts[3]}" if len(parts) > 3 else parts[2]
            
            # Extract business name from message
            message_text = query.message.text
            business_name = message_text.split("*")[1] if "*" in message_text else "Unknown"
            
            await query.answer("🗓️ Updating status & finding nearby stores...", show_alert=False)
            
            try:
                from b2bappointments_automation import B2BAutomation
                
                automation = B2BAutomation()
                await automation.launch_browser()
                
                # Update status to "Appointment Booked"
                success = await automation.update_contact_status(
                    city=city,
                    store_number=store_num,
                    business_name=business_name,
                    status="Appointment Booked"
                )
                
                await automation.close_browser()
                
                if success:
                    await query.edit_message_text(
                        text=query.message.text + "\n✅ Status: Appointment Booked",
                        parse_mode="Markdown"
                    )
                else:
                    await query.edit_message_text(
                        text=query.message.text + "\n⚠️ Could not update status",
                        parse_mode="Markdown"
                    )
                
                # Find nearby stores
                try:
                    from nearby_stores_finder import NearbyStoresFinder
                    
                    finder = NearbyStoresFinder()
                    
                    # Use city-based approximation (would be better with real lat/lon)
                    nearby = finder.find_nearby_stores(
                        prospect_lat=45.6872,  # Default Vancouver, WA
                        prospect_lon=-122.6151,
                        max_distance=3.0,
                        limit=10
                    )
                    
                    if nearby:
                        bundle = finder.generate_recommendation_bundle(nearby, ad_type="single")
                        msg = finder.format_for_telegram(business_name, nearby, bundle)
                        
                        await update.effective_chat.send_message(
                            msg,
                            parse_mode="HTML"
                        )
                    else:
                        await update.effective_chat.send_message(
                            "📍 No nearby stores found. Open Mappoint to add contracts.\n[🗺️ Mappoint](https://sales.indoormedia.com/Mappoint)",
                            parse_mode="Markdown"
                        )
                        
                except Exception as e:
                    logger.error(f"nearby_stores error: {e}")
                    await update.effective_chat.send_message(
                        "🗺️ [Open Mappoint to add contracts](https://sales.indoormedia.com/Mappoint)",
                        parse_mode="Markdown"
                    )
                    
            except Exception as e:
                logger.error(f"booked callback error: {e}")
                await query.edit_message_text(
                    text=query.message.text + f"\n❌ Error: {str(e)[:50]}",
                    parse_mode="Markdown"
                )
            
    except Exception as e:
        logger.error(f"Error handling button: {e}", exc_info=True)
        await query.answer(f"Error: {str(e)[:50]}", show_alert=True)


def main():
    """Start the bot."""
    logger.info("🎯 IndoorMediaProspectBot starting...")
    
    app = Application.builder().token(TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("examples", examples))
    app.add_handler(CallbackQueryHandler(handle_button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_store_query))
    
    logger.info("✅ IndoorMediaProspectBot ready. Polling for messages...")
    app.run_polling()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
        sys.exit(0)
