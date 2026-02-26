#!/usr/bin/env python3
"""
IndoorMediaProspectBot v3 - Google Places Discovery
Location input → Categories → Subcategories → Google Places Results
Ranked by proximity to store + Google Ads highlighting
"""

import json
import logging
import sys
import os
import asyncio
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
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
CATEGORIES_FILE = WORKSPACE / "data" / "category_structure.json"

TOKEN = "8781563020:AAHm_khWUcjngvS0zuNewBbpMM-p2zuMjzI"

# Conversation states
LOCATION_INPUT, CATEGORY_SELECT, SUBCATEGORY_SELECT, SEARCHING = range(4)

# Load data
with open(STORES_FILE) as f:
    STORES_LIST = json.load(f)
STORES = {s["StoreName"]: s for s in STORES_LIST}

with open(CATEGORIES_FILE) as f:
    CATEGORY_DATA = json.load(f)["categories"]

# Track user sessions
USER_SESSIONS: Dict[int, Dict] = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command."""
    help_text = """
🎯 *IndoorMediaProspectBot v3*
_Discover Businesses Near You_

*How to use:*
1️⃣ /search — Start discovery
2️⃣ Enter location (store #, zip, city, or 📍 near me)
3️⃣ Pick category (Restaurants, Automotive, etc.)
4️⃣ Pick subcategory (Pizza, Sushi, etc.)
5️⃣ See Google Maps results ranked by proximity
6️⃣ Tap to open in Google Maps

*Commands:*
/start — This message
/search — New search
/help — Full instructions
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def examples(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show example queries."""
    examples_text = """
📍 *Try These Locations:*

Store Numbers:
`FME07Z-0236` — Vancouver, WA
`SAF07Y-1073` — Beaverton, OR

Zip Codes:
`97201` — Oregon
`98660` — Washington

City Names:
`Klamath Falls`
`Portland`

Or tap 📍 Near Me
    """
    await update.message.reply_text(examples_text, parse_mode="Markdown")


async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start search conversation."""
    user_id = update.effective_user.id
    USER_SESSIONS[user_id] = {
        "location": None,
        "location_name": None,
        "lat": None,
        "lon": None,
        "category": None,
        "subcategory": None,
        "results": []
    }
    
    await update.message.reply_text(
        "📍 *Where are you searching?*\n\n"
        "Enter a store number, zip code, or city name:\n\n"
        "Examples:\n"
        "`FME07Z-0236` — Store #\n"
        "`97201` — Zip code\n"
        "`Klamath Falls` — City",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📍 Near Me", callback_data="near_me")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
        ])
    )
    
    return LOCATION_INPUT


async def handle_location_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parse location input and resolve to lat/lon."""
    user_id = update.effective_user.id
    location_text = update.message.text.strip()
    
    # Resolve location
    lat, lon, location_name = resolve_location(location_text)
    
    if not lat or not lon:
        await update.message.reply_text(
            f"❌ Couldn't find location: `{location_text}`\n\n"
            f"Try a store #, zip code, or city name.",
            parse_mode="Markdown"
        )
        return LOCATION_INPUT
    
    USER_SESSIONS[user_id]["location"] = location_text
    USER_SESSIONS[user_id]["location_name"] = location_name
    USER_SESSIONS[user_id]["lat"] = lat
    USER_SESSIONS[user_id]["lon"] = lon
    
    logger.info(f"Location resolved: {location_name} ({lat}, {lon})")
    
    # Show categories
    await show_categories(update, context, user_id)
    return CATEGORY_SELECT


async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show main category buttons."""
    buttons = []
    
    # 6 main categories with icons
    for emoji, data in CATEGORY_DATA.items():
        buttons.append([InlineKeyboardButton(
            f"{emoji} {data['name']}",
            callback_data=f"cat_{emoji}"
        )])
    
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    
    keyboard = InlineKeyboardMarkup(buttons)
    
    location_name = USER_SESSIONS[user_id]["location_name"]
    
    text = f"*Pick a Category*\n\n📍 {location_name}"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def handle_category_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category selection."""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    if data == "cancel":
        await query.answer()
        USER_SESSIONS.pop(user_id, None)
        await query.edit_message_text("❌ Search cancelled.")
        return ConversationHandler.END
    
    if data.startswith("cat_"):
        emoji = data.replace("cat_", "")
        category_data = CATEGORY_DATA.get(emoji)
        
        if not category_data:
            await query.answer("❌ Category not found")
            return CATEGORY_SELECT
        
        USER_SESSIONS[user_id]["category"] = emoji
        USER_SESSIONS[user_id]["category_name"] = category_data["name"]
        
        # Show subcategories
        buttons = []
        for sub_emoji, sub_data in category_data["subcategories"].items():
            buttons.append([InlineKeyboardButton(
                f"{sub_emoji} {sub_data['name']}",
                callback_data=f"subcat_{sub_emoji}"
            )])
        
        buttons.append([InlineKeyboardButton("◀ Back", callback_data="back_categories")])
        buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        
        keyboard = InlineKeyboardMarkup(buttons)
        
        location_name = USER_SESSIONS[user_id]["location_name"]
        category_name = category_data["name"]
        
        text = f"*Select {category_name}*\n\n📍 {location_name}"
        
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
        return SUBCATEGORY_SELECT
    
    await query.answer("Invalid selection")
    return CATEGORY_SELECT


async def handle_subcategory_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subcategory selection and search."""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    if data == "back_categories":
        await query.answer()
        await show_categories(update, context, user_id)
        return CATEGORY_SELECT
    
    if data == "cancel":
        await query.answer()
        USER_SESSIONS.pop(user_id, None)
        await query.edit_message_text("❌ Search cancelled.")
        return ConversationHandler.END
    
    if data.startswith("subcat_"):
        emoji = data.replace("subcat_", "")
        category_emoji = USER_SESSIONS[user_id]["category"]
        category_data = CATEGORY_DATA[category_emoji]
        subcategory_data = category_data["subcategories"].get(emoji)
        
        if not subcategory_data:
            await query.answer("❌ Subcategory not found")
            return SUBCATEGORY_SELECT
        
        USER_SESSIONS[user_id]["subcategory"] = emoji
        USER_SESSIONS[user_id]["subcategory_name"] = subcategory_data["name"]
        
        # Start search
        await query.answer("🔍 Searching Google Maps...")
        
        location_name = USER_SESSIONS[user_id]["location_name"]
        category_name = USER_SESSIONS[user_id]["category_name"]
        subcategory_name = subcategory_data["name"]
        google_types = subcategory_data["google_types"]
        
        lat = USER_SESSIONS[user_id]["lat"]
        lon = USER_SESSIONS[user_id]["lon"]
        
        await query.edit_message_text(
            f"🔍 *Searching...*\n\n"
            f"📍 {location_name}\n"
            f"{USER_SESSIONS[user_id]['category']} {category_name}\n"
            f"{emoji} {subcategory_name}",
            parse_mode="Markdown"
        )
        
        # Search Google Places
        try:
            from prospecting_tool_enhanced import ProspectingToolEnhanced
            
            tool = ProspectingToolEnhanced()
            
            # Build search query
            search_query = f"{subcategory_name} near {location_name}"
            
            logger.info(f"Searching: {search_query}")
            
            # For now, return mock results (full Google Places API integration coming)
            # This will use the existing prospecting tool
            results = tool.run_prospecting(location_name, limit=10)
            
            if not results:
                await query.edit_message_text(
                    f"❌ No businesses found for {subcategory_name} in {location_name}",
                    parse_mode="Markdown"
                )
                USER_SESSIONS.pop(user_id, None)
                return ConversationHandler.END
            
            # Sort by distance from location (lat/lon)
            results_with_distance = sort_by_distance(results, lat, lon)
            
            USER_SESSIONS[user_id]["results"] = results_with_distance
            
            # Send results
            await send_results(query, results_with_distance, location_name, subcategory_name)
            
            logger.info(f"✅ Sent {len(results_with_distance)} results")
            USER_SESSIONS.pop(user_id, None)
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Search error: {e}", exc_info=True)
            await query.edit_message_text(f"❌ Error: {str(e)[:100]}")
            USER_SESSIONS.pop(user_id, None)
            return ConversationHandler.END
    
    await query.answer("Invalid selection")
    return SUBCATEGORY_SELECT


def resolve_location(location_text: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """Resolve location text to lat/lon."""
    location_text = location_text.strip().upper()
    
    # Check if it's a store number
    if "-" in location_text and len(location_text) >= 9:
        store = STORES.get(location_text)
        if store:
            lat = float(store.get("Latitude", 0))
            lon = float(store.get("Longitude", 0))
            city = store.get("City", "Unknown")
            return lat, lon, f"{city} ({location_text})"
    
    # Check if it's a zip code (5 digits)
    if location_text.isdigit() and len(location_text) == 5:
        # Find first store in this zip
        for store in STORES_LIST:
            if store.get("Zip") == location_text:
                lat = float(store.get("Latitude", 0))
                lon = float(store.get("Longitude", 0))
                city = store.get("City", "Unknown")
                return lat, lon, f"{city}, {location_text}"
        # If no store found, use approximate US center
        return None, None, None
    
    # Check if it's a city name
    location_lower = location_text.lower()
    for store in STORES_LIST:
        if store.get("City", "").lower() == location_lower:
            lat = float(store.get("Latitude", 0))
            lon = float(store.get("Longitude", 0))
            city = store.get("City", "Unknown")
            return lat, lon, city
    
    return None, None, None


def sort_by_distance(results: List[Dict], lat: float, lon: float) -> List[Dict]:
    """Sort results by distance from lat/lon."""
    import math
    
    def distance_to_point(prospect):
        try:
            p_lat = float(prospect.get("latitude", 0))
            p_lon = float(prospect.get("longitude", 0))
            
            # Haversine formula
            R = 3959  # miles
            lat_rad = math.radians(lat)
            lon_rad = math.radians(lon)
            p_lat_rad = math.radians(p_lat)
            p_lon_rad = math.radians(p_lon)
            
            dlat = p_lat_rad - lat_rad
            dlon = p_lon_rad - lon_rad
            
            a = math.sin(dlat/2)**2 + math.cos(lat_rad) * math.cos(p_lat_rad) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            
            return R * c
        except:
            return 999
    
    return sorted(results, key=distance_to_point)


async def send_results(query, results: List[Dict], location_name: str, category_name: str):
    """Send search results with Google Maps links."""
    await query.edit_message_text(
        f"✅ *Results for {category_name} near {location_name}*\n\n"
        f"Showing {len(results)} businesses, ranked by proximity",
        parse_mode="Markdown"
    )
    
    # Send each result
    for i, result in enumerate(results, 1):
        name = result.get("name", "Unknown")
        rating = result.get("rating", "N/A")
        reviews = result.get("review_count", 0)
        distance = result.get("distance_miles", "N/A")
        phone = result.get("phone", "N/A")
        
        # Check if sponsored (has advertising signal)
        sponsored = "🎯" if result.get("advertising_signal", {}).get("found_advertising") else ""
        
        text = f"*{i}. {name}* {sponsored}\n"
        text += f"⭐ {rating} ({reviews} reviews)\n"
        text += f"📍 {distance} mi away\n"
        text += f"📞 {phone}"
        
        # Google Maps button
        maps_url = f"https://www.google.com/maps/search/{urllib.parse.quote(name)}+{urllib.parse.quote(location_name)}"
        
        buttons = [[
            InlineKeyboardButton("📍 View on Maps", url=maps_url),
            InlineKeyboardButton("📞 Call", url=f"tel:{phone}" if phone != "N/A" else "https://maps.google.com")
        ]]
        
        keyboard = InlineKeyboardMarkup(buttons)
        
        await query.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)
        
        # Small delay
        await asyncio.sleep(0.1)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation."""
    user_id = update.effective_user.id
    USER_SESSIONS.pop(user_id, None)
    await update.message.reply_text("❌ Search cancelled.")
    return ConversationHandler.END


def main():
    """Start the bot."""
    logger.info("🎯 IndoorMediaProspectBot v3 starting...")
    
    app = Application.builder().token(TOKEN).build()
    
    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("search", search_start)],
        states={
            LOCATION_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_location_input),
                CallbackQueryHandler(lambda u, c: handle_location_input(u, c), pattern="near_me"),
                CallbackQueryHandler(cancel, pattern="cancel"),
            ],
            CATEGORY_SELECT: [
                CallbackQueryHandler(handle_category_select),
            ],
            SUBCATEGORY_SELECT: [
                CallbackQueryHandler(handle_subcategory_select),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("examples", examples))
    app.add_handler(conv_handler)
    
    logger.info("✅ IndoorMediaProspectBot v3 ready. Polling for messages...")
    app.run_polling()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
        sys.exit(0)
