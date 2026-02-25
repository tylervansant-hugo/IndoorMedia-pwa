#!/usr/bin/env python3
"""
IndoorMedia Rates Bot v2 - Store-specific pricing
Supports: store#, city+chain, cycle+city, street search
Displays per-installment + total for all payment plans
"""

import json
import logging
import sys
from pathlib import Path
from typing import List, Optional, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

WORKSPACE = Path(__file__).parent.parent
DATA_DIR = WORKSPACE / "data" / "store-rates"
STORES_FILE = DATA_DIR / "stores.json"
INDEX_FILE = DATA_DIR / "indexes.json"

TOKEN = "8538356016:AAE3nlsh-He8JRR-9JQGS1InprYlgjZ3tWM"


class StoreSearch:
    """Search stores by various criteria."""
    
    def __init__(self):
        with open(STORES_FILE) as f:
            self.stores_list = json.load(f)
        self.stores = {s["StoreName"]: s for s in self.stores_list}
        
        with open(INDEX_FILE) as f:
            self.indexes = json.load(f)
    
    def by_store_number(self, store_num: str) -> Optional[Dict]:
        store_num = store_num.upper()
        return self.stores.get(store_num)
    
    def by_city_chain(self, city: str, chain: str) -> List[Dict]:
        key = f"{city}-{chain}".lower()
        store_nums = self.indexes["by_city_chain"].get(key, [])
        return [self.stores[num] for num in store_nums if num in self.stores]
    
    def by_cycle(self, cycle: str, city: str) -> List[Dict]:
        key = f"{cycle}-{city}".lower()
        store_nums = self.indexes["by_cycle"].get(key, [])
        return [self.stores[num] for num in store_nums if num in self.stores]
    
    def by_street(self, street_name: str) -> List[Dict]:
        street_lower = street_name.lower()
        results = []
        for store in self.stores_list:
            if street_lower in store["Address"].lower():
                results.append(store)
        return results


def calculate_pricing(store: Dict, ad_type: str = "single") -> Dict:
    """Calculate pricing with both per-installment and total."""
    base = store["DoubleAd"] if ad_type.lower() == "double" else store["SingleAd"]
    PROD = 125.0
    
    return {
        "store_number": store["StoreName"],
        "store_name": store["GroceryChain"],
        "city": store["City"],
        "address": store["Address"],
        "base_price": base,
        "ad_type": ad_type,
        "plans": {
            "monthly": {
                "per_installment": round((base + PROD) / 12, 2),
                "total": round(base + PROD, 2),
                "display": f"${round((base + PROD) / 12, 2):.2f}/mo × 12 = ${round(base + PROD, 2):.2f}"
            },
            "3month": {
                "per_installment": round(((base * 0.90) + PROD) / 3, 2),
                "total": round((base * 0.90) + PROD, 2),
                "display": f"${round(((base * 0.90) + PROD) / 3, 2):.2f} × 3 = ${round((base * 0.90) + PROD, 2):.2f} (10% off)"
            },
            "6month": {
                "per_installment": round(((base * 0.925) + PROD) / 6, 2),
                "total": round((base * 0.925) + PROD, 2),
                "display": f"${round(((base * 0.925) + PROD) / 6, 2):.2f} × 6 = ${round((base * 0.925) + PROD, 2):.2f} (7.5% off)"
            },
            "paid_full": {
                "per_installment": round((base * 0.85) + PROD, 2),
                "total": round((base * 0.85) + PROD, 2),
                "display": f"${round((base * 0.85) + PROD, 2):.2f} (one payment, 15% off)"
            }
        }
    }


def format_message(pricing: Dict) -> str:
    """Format pricing for Telegram."""
    lines = [
        f"📍 *{pricing['store_name']}* — {pricing['city']}, {pricing['store_number']}",
        f"📦 {pricing['ad_type'].upper()} AD | Base: ${pricing['base_price']:.2f}",
        "",
        "💳 *Payment Plans:*",
    ]
    
    for plan_name, plan in pricing["plans"].items():
        lines.append(f"• {plan['display']}")
    
    return "\n".join(lines)


def make_ad_buttons() -> InlineKeyboardMarkup:
    """Buttons to toggle single/double ad."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📄 Single Ad", callback_data="ad_single"),
            InlineKeyboardButton("📋 Double Ad", callback_data="ad_double"),
        ]
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command."""
    help_text = """
🐚 *IndoorMedia Rates Bot*

**Query Formats:**
• Store #: `FME07Y-0165`
• City + Chain: `Klamath Falls Fred Meyer`
• Cycle + City: `A Cycle Beaverton`
• Street: `Shasta Way`

**Commands:**
/cities — List all cities
/chains — List all chains
/help — This message

Type a query to get pricing!
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle queries."""
    text = update.message.text.strip()
    
    if not text or text.startswith("/"):
        return
    
    # Detect ad type
    ad_type = "double" if "double" in text.lower() else "single"
    query = text.lower().replace("double", "").replace("ad", "").strip()
    
    search = StoreSearch()
    stores = []
    
    parts = query.split()
    
    # Try store number (4+ chars, all alphanum)
    if len(parts) == 1 and len(parts[0]) > 4:
        store = search.by_store_number(parts[0])
        if store:
            stores = [store]
    
    # Try city+chain (2+ parts)
    if not stores and len(parts) >= 2:
        # Check if starts with cycle indicator (A/B/C Cycle City)
        if parts[0] in ["a", "b", "c"] and len(parts) > 2 and "cycle" in query:
            cycle = parts[0].upper()
            city_name = " ".join(parts[2:])
            stores = search.by_cycle(cycle, city_name)
        else:
            # City + Chain
            city = parts[0]
            chain = " ".join(parts[1:])
            stores = search.by_city_chain(city, chain)
    
    # Try street (single word)
    if not stores and len(parts) == 1:
        stores = search.by_street(parts[0])
    
    if not stores:
        await update.message.reply_text("❌ No stores found. Try: `FME07Y-0165` or `Klamath Falls Fred Meyer`")
        return
    
    # Show first result
    store = stores[0]
    pricing = calculate_pricing(store, ad_type)
    msg = format_message(pricing)
    
    context.user_data["last_store"] = store
    context.user_data["last_ad_type"] = ad_type
    
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=make_ad_buttons())
    
    # Show alternatives if multiple
    if len(stores) > 1:
        alts = "\n".join([f"• {s['StoreName']} — {s['Address']}" for s in stores[1:4]])
        await update.message.reply_text(f"*Other matches:*\n{alts}", parse_mode="Markdown")


async def callback_ad_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle single/double ad."""
    query = update.callback_query
    ad_type = "double" if "double" in query.data else "single"
    
    store = context.user_data.get("last_store")
    if not store:
        await query.answer("❌ Store data expired. Please search again.")
        return
    
    pricing = calculate_pricing(store, ad_type)
    msg = format_message(pricing)
    
    context.user_data["last_ad_type"] = ad_type
    
    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=make_ad_buttons())
    await query.answer()


async def cmd_cities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all cities."""
    search = StoreSearch()
    cities = set(s["City"] for s in search.stores_list)
    city_list = "\n".join(sorted(cities))
    
    msg = f"*{len(cities)} Cities:*\n\n{city_list}"
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_chains(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all chains."""
    search = StoreSearch()
    chains = set(s["GroceryChain"] for s in search.stores_list)
    chain_list = "\n".join(sorted(chains))
    
    msg = f"*{len(chains)} Chains:*\n\n{chain_list}"
    await update.message.reply_text(msg, parse_mode="Markdown")


def main():
    """Start the bot."""
    logger.info("🐚 IndoorMedia Rates Bot v2 starting...")
    
    app = Application.builder().token(TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("cities", cmd_cities))
    app.add_handler(CommandHandler("chains", cmd_chains))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    from telegram.ext import CallbackQueryHandler
    app.add_handler(CallbackQueryHandler(callback_ad_toggle, pattern=r"^ad_"))
    
    logger.info("✅ Bot is running. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
        sys.exit(0)
