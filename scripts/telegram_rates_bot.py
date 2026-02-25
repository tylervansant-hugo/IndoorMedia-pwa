#!/usr/bin/env python3
"""
IndoorMedia Rates Bot - Clean, simple Telegram interface
"""

import json
import subprocess
from pathlib import Path
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8538356016:AAE3nlsh-He8JRR-9JQGS1InprYlgjZ3tWM"
RATE_CALC = Path(__file__).parent.parent / "skills" / "store-rates" / "scripts" / "rate_calculator.py"

# Load store index for number lookups
STORE_DATA_FILE = Path(__file__).parent.parent / "skills" / "store-rates" / "references" / "store_data.json"
STORES_BY_NUMBER = {}

try:
    with open(STORE_DATA_FILE) as f:
        for store in json.load(f)["stores"]:
            code = store.get("code", "")
            if "-" in code:
                number = code.split("-")[-1]
                STORES_BY_NUMBER[number] = store
except Exception as e:
    logger.error(f"Error loading store data: {e}")


def call_rate_calc(cmd_args):
    """Call rate calculator and return JSON response."""
    try:
        result = subprocess.run(
            ["python3", str(RATE_CALC)] + cmd_args,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
    except Exception as e:
        logger.error(f"Rate calc error: {e}")
    return None


def format_pricing_message(store_data, street_name=None):
    """Format store pricing for display."""
    name = store_data.get("name", "")
    city = store_data.get("city", "")
    state = store_data.get("state", "")
    pricing = store_data.get("pricing", {})
    
    msg = f"📍 *{name}* | {city}, {state}\n"
    if street_name:
        msg += f"📍 _{street_name}_\n"
    msg += "\n*💰 SINGLE AD:*\n"
    
    for plan_type in ["monthly", "3month", "6month", "paid_full"]:
        p = pricing.get(plan_type, {})
        if p.get("installments") == 1:
            star = " ⭐" if plan_type == "paid_full" else ""
            msg += f"• {p.get('desc', '')}: ${p.get('annual', 0):,.2f}{star}\n"
        else:
            star = " ⭐" if plan_type == "paid_full" else ""
            msg += f"• {p.get('desc', '')}: ${p.get('per_month', 0):,.2f}/mo (${p.get('annual', 0):,.2f} total){star}\n"
    
    # Get double pricing
    double_data = call_rate_calc([city, name, "double"])
    if double_data:
        pricing_double = double_data.get("pricing", {})
        msg += "\n*💰 DOUBLE AD:*\n"
        
        for plan_type in ["monthly", "3month", "6month", "paid_full"]:
            p = pricing_double.get(plan_type, {})
            if p.get("installments") == 1:
                star = " ⭐" if plan_type == "paid_full" else ""
                msg += f"• {p.get('desc', '')}: ${p.get('annual', 0):,.2f}{star}\n"
            else:
                star = " ⭐" if plan_type == "paid_full" else ""
                msg += f"• {p.get('desc', '')}: ${p.get('per_month', 0):,.2f}/mo (${p.get('annual', 0):,.2f} total){star}\n"
    
    return msg


def make_payment_buttons():
    """Create payment plan buttons."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Monthly 💵", callback_data="plan_monthly"),
            InlineKeyboardButton("3-Month 📅", callback_data="plan_3month"),
        ],
        [
            InlineKeyboardButton("6-Month 🗓", callback_data="plan_6month"),
            InlineKeyboardButton("Paid-in-Full ⭐", callback_data="plan_paid_full"),
        ]
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command."""
    msg = """🐚 *IndoorMedia Rates Bot*

Get store pricing instantly.

*How to search:*
• By store #: `0415`
• By city+chain: `Bend Safeway`
• By street: `Walker Rd`

Then tap buttons to switch payment plans!"""
    
    await update.message.reply_text(msg, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user queries."""
    text = update.message.text.strip()
    
    if text.startswith("/"):
        return
    
    # Try store number first (4 digits)
    if text.isdigit() and len(text) == 4:
        if text in STORES_BY_NUMBER:
            store = STORES_BY_NUMBER[text]
            city = store.get("city", "")
            chain = store.get("name", "")
            
            data = call_rate_calc([city, chain, "single"])
            if data:
                context.user_data["last_store"] = data
                msg = format_pricing_message(data)
                await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=make_payment_buttons())
                return
        
        await update.message.reply_text(f"❌ Store {text} not found")
        return
    
    # Try street search (has street keywords)
    street_keywords = ("rd", "road", "st", "street", "ave", "avenue", "blvd", "dr", "hwy", "pkwy", "ln", "way")
    if any(kw in text.lower() for kw in street_keywords):
        results = call_rate_calc(["--search-street", text])
        if results and isinstance(results, list) and len(results) > 0:
            context.user_data["street_context"] = text
            msg = f"📍 *Stores on {text}:*\n\n"
            
            buttons = []
            for store in results[:10]:
                num = store.get("code", "").split("-")[-1] if "-" in store.get("code", "") else "?"
                msg += f"• #{num} {store.get('name')} in {store.get('city')}\n"
                buttons.append([InlineKeyboardButton(f"#{num} {store.get('name')}", callback_data=f"street_{num}")])
            
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
            return
        
        await update.message.reply_text(f"❌ No stores found on {text}")
        return
    
    # Try city + chain (2+ words)
    parts = text.split()
    if len(parts) >= 2:
        city = parts[0]
        chain = " ".join(parts[1:])
        
        data = call_rate_calc([city, chain, "single"])
        if data:
            context.user_data["last_store"] = data
            msg = format_pricing_message(data)
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=make_payment_buttons())
            return
        
        await update.message.reply_text(f"❌ No stores found for {city} {chain}")
        return
    
    await update.message.reply_text("❌ Try: store #, city+chain, or street name")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks."""
    query = update.callback_query
    await query.answer()
    
    # Street store button (format: street_NNNN)
    if query.data.startswith("street_"):
        num = query.data.replace("street_", "")
        
        if num in STORES_BY_NUMBER:
            store = STORES_BY_NUMBER[num]
            city = store.get("city", "")
            chain = store.get("name", "")
            
            data = call_rate_calc([city, chain, "single"])
            if data:
                street = context.user_data.get("street_context")
                context.user_data["last_store"] = data
                msg = format_pricing_message(data, street)
                await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=make_payment_buttons())
                return
        
        await query.edit_message_text("❌ Store not found")
        return
    
    # Payment plan buttons (format: plan_PLANTYPE)
    # For now, just acknowledge - full implementation would show plan-specific message
    if query.data.startswith("plan_"):
        await query.answer("Plan selected")
        return


def main():
    """Start bot."""
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🐚 IndoorMedia Rates Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
