#!/usr/bin/env python3
"""
IndoorMedia Rates Bot - Case count based pricing
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

# Load store index
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
    """Call rate calculator."""
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


def format_pricing_message(store_data):
    """Format store pricing for display."""
    name = store_data.get("name", "")
    city = store_data.get("city", "")
    state = store_data.get("state", "")
    case_count = store_data.get("case_count", "")
    pricing = store_data.get("pricing", {})
    ad_type = store_data.get("ad_type", "single").upper()
    
    msg = f"📍 *{name}* | {city}, {state}\n"
    msg += f"📦 {case_count} cases | {ad_type} AD\n\n"
    
    msg += "*💰 Payment Plans:*\n"
    for plan_type in ["monthly", "3month", "6month", "paid_full"]:
        p = pricing.get(plan_type, {})
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

Simple case-count based pricing.

*How to search:*
• By store: `0415 25` (store# case_count)
• By city: `Bend Safeway 20` (city chain case_count)

Then tap buttons to see payment plans!"""
    
    await update.message.reply_text(msg, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user queries."""
    text = update.message.text.strip()
    
    if text.startswith("/"):
        return
    
    parts = text.split()
    
    # Need at least 2 parts
    if len(parts) < 2:
        await update.message.reply_text("Format: store# case_count or city chain case_count\nE.g.: `0415 25` or `Bend Safeway 20`")
        return
    
    # Case 1: Store number + case count (e.g., "0415 25")
    if parts[0].isdigit() and len(parts[0]) == 4:
        store_num = parts[0]
        
        try:
            case_count = int(parts[1])
        except ValueError:
            await update.message.reply_text("❌ Case count must be a number")
            return
        
        if store_num in STORES_BY_NUMBER:
            store = STORES_BY_NUMBER[store_num]
            city = store.get("city", "")
            chain = store.get("name", "")
            
            data = call_rate_calc([city, chain, str(case_count), "single"])
            if data:
                context.user_data["last_store"] = data
                msg = format_pricing_message(data)
                await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=make_payment_buttons())
                return
            else:
                await update.message.reply_text(f"❌ Error getting pricing for case count {case_count}")
                return
        else:
            await update.message.reply_text(f"❌ Store {store_num} not found")
            return
    
    # Case 2: City + chain + case count (e.g., "Bend Safeway 20")
    if len(parts) >= 3:
        try:
            case_count = int(parts[-1])
            city = parts[0]
            chain = " ".join(parts[1:-1])
        except ValueError:
            await update.message.reply_text("❌ Last parameter must be case count (number)")
            return
        
        data = call_rate_calc([city, chain, str(case_count), "single"])
        if data:
            context.user_data["last_store"] = data
            msg = format_pricing_message(data)
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=make_payment_buttons())
            return
        else:
            await update.message.reply_text(f"❌ No stores found for {city} {chain}")
            return
    
    await update.message.reply_text("❌ Invalid format. Try: `0415 25` or `Bend Safeway 20`")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks."""
    query = update.callback_query
    await query.answer()
    
    # Just acknowledge for now - could expand to show plan-specific details
    await query.answer("Plan selected!")


def main():
    """Start bot."""
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🐚 IndoorMedia Rates Bot starting (case count based)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
