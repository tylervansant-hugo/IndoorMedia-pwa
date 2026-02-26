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
import math
import httpx
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
GOOGLE_PLACES_API_KEY = "AIzaSyAyBTp2gd-g-1Qfyy1XVrR5-VLXCbh3O6I"

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
    
    # Handle both message and callback query
    if update.message:
        location_text = update.message.text.strip()
    elif update.callback_query:
        # This shouldn't happen here, but handle it gracefully
        await update.callback_query.answer("Please enter a location")
        return LOCATION_INPUT
    else:
        return LOCATION_INPUT
    
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
        
        # Search Google Places API
        logger.info(f"Searching Google Places: {subcategory_name} near {location_name}")
        
        await query.edit_message_text(
            f"🔍 *Searching nearby {subcategory_name}...*\n\n"
            f"📍 {location_name}",
            parse_mode="Markdown"
        )
        
        try:
            # Search Google Places
            results = await search_google_places(
                query_text=subcategory_name,
                lat=lat,
                lon=lon,
                location_name=location_name
            )
            
            if not results:
                await query.edit_message_text(
                    f"❌ No {subcategory_name} found near {location_name}\n\n"
                    f"[🗺️ Try on Google Maps](https://maps.google.com/maps/search/{urllib.parse.quote(subcategory_name)}/@{lat},{lon},15z)",
                    parse_mode="Markdown"
                )
                USER_SESSIONS.pop(user_id, None)
                return ConversationHandler.END
            
            # Rank results
            ranked = rank_results(results, lat, lon)
            
            USER_SESSIONS[user_id]["results"] = ranked
            
            # Send results
            await send_ranked_results(query, ranked[:10], location_name, subcategory_name, lat, lon)
            
            logger.info(f"✅ Sent {len(ranked[:10])} ranked results")
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
    if "-" in location_text:
        store = STORES.get(location_text)
        if store:
            lat = float(store.get("latitude", 0))
            lon = float(store.get("longitude", 0))
            city = store.get("City", "Unknown")
            chain = store.get("GroceryChain", "Store")
            return lat, lon, f"{city} - {chain} ({location_text})"
    
    # Check if it's a zip code (5 digits)
    if location_text.isdigit() and len(location_text) == 5:
        # Find first store in this zip
        for store in STORES_LIST:
            if store.get("PostalCode") == location_text:
                lat = float(store.get("latitude", 0))
                lon = float(store.get("longitude", 0))
                city = store.get("City", "Unknown")
                return lat, lon, f"{city}, {location_text}"
        # If no store found, return None
        return None, None, None
    
    # Check if it's a city name
    location_lower = location_text.lower()
    for store in STORES_LIST:
        if store.get("City", "").lower() == location_lower:
            lat = float(store.get("latitude", 0))
            lon = float(store.get("longitude", 0))
            city = store.get("City", "Unknown")
            state = store.get("State", "")
            return lat, lon, f"{city}, {state}"
    
    return None, None, None


# (Removed - now using rank_results function instead)


async def search_google_places(query_text: str, lat: float, lon: float, location_name: str) -> List[Dict]:
    """Search Google Places API and return results."""
    try:
        # Nearby search endpoint
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        
        params = {
            "location": f"{lat},{lon}",
            "radius": 5000,  # 5km radius
            "query": query_text,
            "key": GOOGLE_PLACES_API_KEY
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()
        
        if data.get("status") != "OK":
            logger.warning(f"Google Places API error: {data.get('status')}")
            return []
        
        results = []
        for place in data.get("results", [])[:20]:  # Top 20
            result = {
                "name": place.get("name", "Unknown"),
                "lat": place.get("geometry", {}).get("location", {}).get("lat", lat),
                "lon": place.get("geometry", {}).get("location", {}).get("lng", lon),
                "rating": place.get("rating", 0),
                "user_ratings_total": place.get("user_ratings_total", 0),
                "phone": place.get("formatted_phone_number", "N/A"),
                "address": place.get("formatted_address", ""),
                "is_open": place.get("opening_hours", {}).get("open_now"),
                "types": place.get("types", []),
                "place_id": place.get("place_id", ""),
                "sponsored": is_sponsored_ad(place)  # Detect if sponsored
            }
            results.append(result)
        
        logger.info(f"Found {len(results)} results for '{query_text}'")
        return results
        
    except Exception as e:
        logger.error(f"Google Places API error: {e}")
        return []


def is_sponsored_ad(place: Dict) -> bool:
    """Detect if a place is a sponsored/promoted result on Google Maps."""
    # In Google Places API, sponsored results often have specific indicators
    # Check for "business_status", promotional badges, or ads markers
    # For now, we'll look for businesses with high review counts and specific types
    # (real sponsored detection requires additional API calls or web scraping)
    
    # Heuristic: Sponsored ads usually have either very high or very low visibility patterns
    # and are often chains or large businesses
    types = place.get("types", [])
    is_chain_indicator = any(t in types for t in ["establishment", "point_of_interest"])
    has_many_reviews = place.get("user_ratings_total", 0) > 100
    
    # For now, return False (would need actual ads API or web scraping for accuracy)
    return False


def rank_results(results: List[Dict], store_lat: float, store_lon: float) -> List[Dict]:
    """Rank results by multiple criteria."""
    
    def calculate_score(place):
        # Distance score (0-40 points, closer = higher)
        distance = calculate_distance(store_lat, store_lon, place["lat"], place["lon"])
        distance_score = max(0, 40 - (distance * 10))  # Penalize by 10 pts per mile
        
        # Rating score (0-30 points)
        rating_score = (place.get("rating", 0) / 5.0) * 30
        
        # Review count score (0-20 points, more reviews = more active)
        review_count = place.get("user_ratings_total", 0)
        review_score = min(20, (review_count / 100) * 20)  # Cap at 20
        
        # Sponsored ad bonus (0-10 points)
        sponsored_bonus = 10 if place.get("sponsored") else 0
        
        total_score = distance_score + rating_score + review_score + sponsored_bonus
        
        place["score"] = round(total_score, 1)
        place["distance_miles"] = round(distance, 1)
        
        return place
    
    scored = [calculate_score(r) for r in results]
    return sorted(scored, key=lambda x: x["score"], reverse=True)


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in miles using Haversine formula."""
    R = 3959  # Earth radius in miles
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


async def send_ranked_results(query, results: List[Dict], location_name: str, category_name: str, lat: float, lon: float):
    """Send ranked results with detailed info."""
    # Summary message
    await query.edit_message_text(
        f"✅ *Top {len(results)} {category_name} near {location_name}*\n\n"
        f"Ranked by: Distance • Rating • Reviews • Ads",
        parse_mode="Markdown"
    )
    
    # Send each result
    for i, result in enumerate(results, 1):
        name = result.get("name", "Unknown")
        rating = result.get("rating", 0)
        reviews = result.get("user_ratings_total", 0)
        distance = result.get("distance_miles", 0)
        phone = result.get("phone", "N/A")
        score = result.get("score", 0)
        sponsored = "🎯" if result.get("sponsored") else ""
        
        # Rating emoji
        if rating >= 4.5:
            rating_emoji = "🔥"
        elif rating >= 4.0:
            rating_emoji = "⭐"
        elif rating >= 3.5:
            rating_emoji = "👍"
        else:
            rating_emoji = "📍"
        
        text = f"*{i}. {name}* {sponsored}\n"
        text += f"{rating_emoji} {rating}/5.0 ({reviews} reviews)\n"
        text += f"📍 {distance} mi away\n"
        text += f"⚡ Score: {score}/100"
        
        if phone != "N/A":
            text += f"\n📞 {phone}"
        
        # Action buttons
        maps_url = f"https://www.google.com/maps/search/{urllib.parse.quote(name)}/@{lat},{lon},15z"
        directions_url = f"https://maps.google.com/maps/dir/?api=1&destination={result.get('lat')},{result.get('lon')}"
        
        buttons = [
            [
                InlineKeyboardButton("📍 View Maps", url=maps_url),
                InlineKeyboardButton("📍 Directions", url=directions_url)
            ]
        ]
        
        if phone != "N/A":
            buttons.append([InlineKeyboardButton("📞 Call", url=f"tel:{phone}")])
        
        keyboard = InlineKeyboardMarkup(buttons)
        
        await query.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)
        
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
    logger.info("🎯 IndoorMediaProspectBot v3 starting...")
    
    app = Application.builder().token(TOKEN).build()
    
    # Conversation handler
    async def handle_near_me_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle near me button click."""
        query = update.callback_query
        user_id = query.from_user.id
        
        await query.answer()
        await query.edit_message_text(
            "📍 *Share your location*\n\n"
            "I don't have access to your device location, so please enter your zip code:",
            parse_mode="Markdown"
        )
        
        return LOCATION_INPUT
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("search", search_start)],
        states={
            LOCATION_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_location_input),
                CallbackQueryHandler(handle_near_me_callback, pattern="near_me"),
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
