#!/usr/bin/env python3
"""
IndoorMedia Rates Bot - Telegram bot for instant rate lookups
Queries: "Longview Safeway single" or "Bend Fred Meyer double 6-month"
"""

import json
import subprocess
import re
import logging
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = "7943939790:AAHlQchij4urPOQvaiWQIrs_TsN4cxv7nPE"

# Path to rate calculator
RATE_CALC = Path(__file__).parent / "rate_calculator.py"
STORE_RATES_SKILL = Path(__file__).parent.parent / "skills" / "store-rates" / "scripts" / "rate_calculator.py"

# Payment plan aliases
PAYMENT_ALIASES = {
    "monthly": "monthly",
    "month": "monthly",
    "12": "monthly",
    "3month": "3month",
    "3": "3month",
    "3-month": "3month",
    "6month": "6month",
    "6": "6month",
    "6-month": "6month",
    "paid": "paid_full",
    "paid-in-full": "paid_full",
    "full": "paid_full",
    "upfront": "paid_full",
}

AD_TYPE_ALIASES = {
    "single": "single",
    "single-ad": "single",
    "singlead": "single",
    "1": "single",
    "double": "double",
    "double-ad": "double",
    "doublead": "double",
    "2": "double",
}


def parse_query(text: str) -> dict:
    """
    Parse a rate query.
    Examples:
      "Longview Safeway single"
      "Bend Fred Meyer double 6-month"
      "Portland Albertsons single paid-in-full"
    """
    parts = text.strip().split()
    
    if len(parts) < 2:
        return None
    
    # Extract ad type and payment plan (end of query)
    ad_type = "single"  # default
    payment_plan = "monthly"  # default
    
    # Work backwards to find ad_type and payment_plan
    query_parts = parts[:]
    
    # Check last part for payment plan
    if len(query_parts) > 0:
        last = query_parts[-1].lower()
        if last in PAYMENT_ALIASES:
            payment_plan = PAYMENT_ALIASES[last]
            query_parts = query_parts[:-1]
    
    # Check second-to-last for ad type
    if len(query_parts) > 0:
        second_last = query_parts[-1].lower()
        if second_last in AD_TYPE_ALIASES:
            ad_type = AD_TYPE_ALIASES[second_last]
            query_parts = query_parts[:-1]
    
    # Remaining parts are city and chain
    if len(query_parts) < 2:
        return None
    
    city = query_parts[0]
    chain = " ".join(query_parts[1:])
    
    return {
        "city": city,
        "chain": chain,
        "ad_type": ad_type,
        "payment_plan": payment_plan,
    }


def get_rates(city: str, chain: str, ad_type: str) -> dict:
    """Call rate calculator and get JSON response."""
    try:
        result = subprocess.run(
            ["python3", str(STORE_RATES_SKILL), city, chain, ad_type, "--json"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        if result.returncode != 0:
            return None
        
        data = json.loads(result.stdout)
        return data
    except Exception as e:
        logger.error(f"Error calling rate calculator: {e}")
        return None


def format_response(data: dict, payment_plan: str) -> str:
    """Format the rate response for Telegram."""
    store = data["store_name"]
    tier = data["tier"]
    ad_type = data["ad_type"]
    plans = data["plans"]
    
    # Get the selected plan
    plan = plans.get(payment_plan)
    if not plan:
        plan = plans["monthly"]  # fallback
    
    response = f"📍 *{store}* | Tier {tier}\n"
    response += f"_{ad_type} - Year-long Campaign_\n\n"
    
    # Show all plans for reference
    response += "💰 *Payment Options:*\n"
    
    for plan_key in ["monthly", "3month", "6month", "paid_full"]:
        p = plans[plan_key]
        
        if plan_key == "paid_full":
            star = " ⭐"
        else:
            star = ""
        
        if p["num_installments"] == 1:
            response += f"• *{p['description']}:* ${p['annual_total']:,.2f}{star}\n"
        else:
            response += f"• *{p['description']}:* ${p['installment_amount']:,.2f}/mo (${p['annual_total']:,.2f} total){star}\n"
    
    response += f"\n_Query matched: `{payment_plan}`_"
    
    return response


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command."""
    message = """🐚 *IndoorMedia Rates Bot*

Get instant pricing for any store.

*Usage:*
`City Chain AdType PaymentPlan`

*Examples:*
• `Longview Safeway single`
• `Bend Fred Meyer double 6-month`
• `Portland Albertsons single paid-in-full`
• `Salem Albertsons double 3-month`

*Ad Types:* single, double (or just use 1, 2)
*Payment Plans:* monthly, 3-month, 6-month, paid-in-full (or 12, 3, 6, full)

*Help:* Type `/cities` to see available locations"""

    await update.message.reply_text(message, parse_mode="Markdown")


async def list_cities(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List available cities."""
    try:
        result = subprocess.run(
            ["python3", str(STORE_RATES_SKILL), "--list-cities"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        if result.returncode == 0:
            lines = result.stdout.split("\n")[:50]  # First 50 lines
            message = "📍 *Available Cities:*\n\n" + "\n".join(lines)
            await update.message.reply_text(message, parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Could not load city list")
    except Exception as e:
        logger.error(f"Error loading cities: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle rate queries."""
    text = update.message.text.strip()
    
    # Ignore commands
    if text.startswith("/"):
        return
    
    # Parse the query
    query = parse_query(text)
    
    if not query:
        await update.message.reply_text(
            "❌ Could not parse query. Try:\n\n`Longview Safeway single`",
            parse_mode="Markdown"
        )
        return
    
    # Get rates
    data = get_rates(query["city"], query["chain"], query["ad_type"])
    
    if not data:
        await update.message.reply_text(
            f"❌ No rates found for {query['city']} {query['chain']}\n\nTry `/cities` to see available locations.",
            parse_mode="Markdown"
        )
        return
    
    # Format response
    response = format_response(data, query["payment_plan"])
    
    await update.message.reply_text(response, parse_mode="Markdown")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors."""
    logger.error(f"Exception: {context.error}")


def main():
    """Start the bot."""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cities", list_cities))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_query))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Start polling
    logger.info("🐚 IndoorMedia Rates Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
