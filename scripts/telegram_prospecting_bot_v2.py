#!/usr/bin/env python3
"""
IndoorMediaProspectBot v2 - Simplified Search Flow
Telegram bot with store/zip/near-me input + category filtering
"""

import json
import logging
import sys
import os
import asyncio
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

WORKSPACE = Path(__file__).parent.parent
DATA_DIR = WORKSPACE / "data" / "store-rates"
STORES_FILE = DATA_DIR / "stores.json"
CATEGORIES_FILE = WORKSPACE / "data" / "business_categories.json"

TOKEN = "8781563020:AAHm_khWUcjngvS0zuNewBbpMM-p2zuMjzI"

# Conversation states
LOCATION_INPUT, CATEGORY_SELECT, SEARCHING = range(3)

# Load data
with open(STORES_FILE) as f:
    STORES_LIST = json.load(f)
STORES = {s["StoreName"]: s for s in STORES_LIST}

with open(CATEGORIES_FILE) as f:
    CATEGORIES = json.load(f)["categories"]

# Track user selections
USER_SESSIONS: Dict[int, Dict] = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command."""
    help_text = """
🎯 *IndoorMediaProspectBot v2*
_Find Today's Deal_

*How to use:*
1️⃣ /search — Start a new search
2️⃣ Enter store # (e.g., FME07Z-0236) or zip code
3️⃣ Select business categories
4️⃣ Get top 10 prospects ranked by likelihood

*Quick examples:*
`/examples` — Sample store numbers

*Commands:*
/start — This message
/search — New search
/help — Full instructions
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

Start with: /search
    """
    await update.message.reply_text(examples_text, parse_mode="Markdown")


async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start search conversation."""
    user_id = update.effective_user.id
    USER_SESSIONS[user_id] = {
        "location": None,
        "categories": set(),
        "prospects": []
    }
    
    await update.message.reply_text(
        "🔍 *New Search*\n\n"
        "Enter a store number, zip code, or click 📍 Near Me\n\n"
        "Examples:\n"
        "`FME07Z-0236` — Store number\n"
        "`97201` — Zip code\n"
        "📍 — Use my location",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📍 Near Me", callback_data="near_me")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
        ])
    )
    
    return LOCATION_INPUT


async def handle_location_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle location input (store number, zip code, or message)."""
    user_id = update.effective_user.id
    text = update.message.text.strip().upper()
    
    # Validate input
    if len(text) < 3:
        await update.message.reply_text("❌ Invalid input. Try a store number or zip code.")
        return LOCATION_INPUT
    
    USER_SESSIONS[user_id]["location"] = text
    
    # Show category selector
    await show_category_selector(update, context, user_id, page=0)
    return CATEGORY_SELECT


async def show_category_selector(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, page: int = 0):
    """Show paginated category selector."""
    categories_per_page = 5
    total_pages = (len(CATEGORIES) + categories_per_page - 1) // categories_per_page
    
    start_idx = page * categories_per_page
    end_idx = start_idx + categories_per_page
    page_categories = CATEGORIES[start_idx:end_idx]
    
    # Build buttons
    buttons = []
    for cat in page_categories:
        selected = "✓" if cat in USER_SESSIONS[user_id]["categories"] else "  "
        buttons.append([InlineKeyboardButton(
            f"{selected} {cat}",
            callback_data=f"cat_{cat.replace(' ', '_')}"
        )])
    
    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀ Prev", callback_data=f"page_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="page_info"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ▶", callback_data=f"page_{page+1}"))
    buttons.append(nav_buttons)
    
    # Action buttons
    selected_count = len(USER_SESSIONS[user_id]["categories"])
    buttons.append([InlineKeyboardButton(
        f"🔍 Search ({selected_count} selected)",
        callback_data="search_now"
    )])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    
    keyboard = InlineKeyboardMarkup(buttons)
    
    text = f"*Select Business Categories*\n\n📍 Location: `{USER_SESSIONS[user_id]['location']}`\n\nPage {page+1}/{total_pages}"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def handle_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category selection and pagination."""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    if data == "cancel":
        await query.answer()
        USER_SESSIONS.pop(user_id, None)
        await query.edit_message_text("❌ Search cancelled.")
        return ConversationHandler.END
    
    elif data.startswith("cat_"):
        # Toggle category selection
        category = data.replace("cat_", "").replace("_", " ")
        if category in USER_SESSIONS[user_id]["categories"]:
            USER_SESSIONS[user_id]["categories"].discard(category)
        else:
            USER_SESSIONS[user_id]["categories"].add(category)
        
        await query.answer(f"{'✓ Added' if category in USER_SESSIONS[user_id]['categories'] else '✗ Removed'} {category}")
        await show_category_selector(update, context, user_id, page=0)
        return CATEGORY_SELECT
    
    elif data.startswith("page_"):
        page_str = data.replace("page_", "")
        if page_str == "info":
            await query.answer("Use arrow buttons to navigate", show_alert=False)
            return CATEGORY_SELECT
        page = int(page_str)
        await show_category_selector(update, context, user_id, page=page)
        return CATEGORY_SELECT
    
    elif data == "search_now":
        if not USER_SESSIONS[user_id]["categories"]:
            await query.answer("❌ Please select at least one category!", show_alert=True)
            return CATEGORY_SELECT
        
        await query.answer("🔍 Searching...")
        
        # Run search
        location = USER_SESSIONS[user_id]["location"]
        categories = list(USER_SESSIONS[user_id]["categories"])
        
        await query.edit_message_text(
            f"🔍 *Searching...*\n\n"
            f"📍 Location: `{location}`\n"
            f"🏢 Categories: {', '.join(categories[:3])}{'...' if len(categories) > 3 else ''}",
            parse_mode="Markdown"
        )
        
        # Import prospecting tool
        try:
            from prospecting_tool_enhanced import ProspectingToolEnhanced
            
            tool = ProspectingToolEnhanced()
            
            # Get prospects
            logger.info(f"🔍 Searching with location={location}, categories={categories}")
            prospects = tool.run_prospecting(location, limit=10)
            
            # Filter by selected categories (if available in the tool)
            # For now, just return top 10
            
            if not prospects:
                await query.edit_message_text(
                    f"❌ No prospects found for `{location}`",
                    parse_mode="Markdown"
                )
                USER_SESSIONS.pop(user_id, None)
                return ConversationHandler.END
            
            # Store results
            USER_SESSIONS[user_id]["prospects"] = prospects
            
            # Send results
            store = STORES.get(location, {})
            
            lines = [
                f"🎯 *TODAY'S DEALS*",
                f"📍 {store.get('GroceryChain', 'Store')} | {store.get('City', 'Location')}",
                f"📦 {location}\n",
            ]
            
            for i, prospect in enumerate(prospects, 1):
                score = prospect['likelihood_score']
                
                if score >= 80:
                    emoji = "🔥"
                elif score >= 70:
                    emoji = "⭐"
                else:
                    emoji = "👀"
                
                lines.append(f"{emoji} *{i}. {prospect['name']}* ({score}/100)")
                lines.append(f"   📞 {prospect.get('phone', 'N/A')}")
                lines.append(f"   📍 {prospect.get('distance_miles', 'N/A')} mi")
                
                if prospect.get('advertising_signal', {}).get('found_advertising'):
                    lines.append(f"   🎯 *ADVERTISING*")
                
                lines.append("")
            
            message = "\n".join(lines)
            
            await query.edit_message_text(message, parse_mode="Markdown")
            
            # Send results with action buttons
            await send_prospects_with_actions(
                update.effective_chat,
                prospects,
                store,
                location
            )
            
            logger.info(f"✅ Sent {len(prospects)} prospects")
            USER_SESSIONS.pop(user_id, None)
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"❌ Search error: {e}", exc_info=True)
            await query.edit_message_text(f"❌ Error: {str(e)[:100]}")
            USER_SESSIONS.pop(user_id, None)
            return ConversationHandler.END


async def handle_near_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle near me location request."""
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer()
    
    # For now, ask for zip code since we can't access device location
    await query.edit_message_text(
        "📍 *Share your location*\n\n"
        "I don't have access to your device location, so please enter your zip code:",
        parse_mode="Markdown"
    )
    
    return LOCATION_INPUT


async def send_prospects_with_actions(chat, prospects: List[Dict], store: Dict, location: str):
    """Send each prospect with action buttons."""
    for i, prospect in enumerate(prospects, 1):
        business_name = prospect.get("name", "Unknown")
        phone = prospect.get("phone", "N/A")
        
        # URL-encode for listing analysis
        analysis_url = f"https://www.indoormedia.com/local-listing-management/?business={urllib.parse.quote(business_name)}"
        
        buttons = [
            [
                InlineKeyboardButton("📊 Analyze", url=analysis_url),
                InlineKeyboardButton("📞 Call", url=f"tel:{phone}"),
            ]
        ]
        
        keyboard = InlineKeyboardMarkup(buttons)
        
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
        
        await chat.send_message(text, parse_mode="Markdown", reply_markup=keyboard)
        
        # Small delay between messages
        await asyncio.sleep(0.2)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation."""
    user_id = update.effective_user.id
    USER_SESSIONS.pop(user_id, None)
    await update.message.reply_text("❌ Search cancelled.")
    return ConversationHandler.END


def main():
    """Start the bot."""
    logger.info("🎯 IndoorMediaProspectBot v2 starting...")
    
    app = Application.builder().token(TOKEN).build()
    
    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("search", search_start)],
        states={
            LOCATION_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_location_input),
                CallbackQueryHandler(handle_near_me, pattern="near_me"),
                CallbackQueryHandler(cancel, pattern="cancel"),
            ],
            CATEGORY_SELECT: [
                CallbackQueryHandler(handle_category_callback),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("examples", examples))
    app.add_handler(conv_handler)
    
    logger.info("✅ IndoorMediaProspectBot v2 ready. Polling for messages...")
    app.run_polling()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
        sys.exit(0)
