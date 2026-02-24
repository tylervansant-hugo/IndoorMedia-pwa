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
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = "8538356016:AAE3nlsh-He8JRR-9JQGS1InprYlgjZ3tWM"

# Path to rate calculator
RATE_CALC = Path(__file__).parent / "rate_calculator.py"
STORE_RATES_SKILL = Path(__file__).parent.parent / "skills" / "store-rates" / "scripts" / "rate_calculator.py"

# Load store data for store number lookups
STORE_DATA_FILE = STORE_RATES_SKILL.parent.parent / "references" / "store_data.json"
try:
    with open(STORE_DATA_FILE, 'r') as f:
        STORE_DATA_JSON = json.load(f)
        STORES_BY_NUMBER = {}
        for store in STORE_DATA_JSON.get("stores", []):
            # Extract 4-digit number from code (e.g., "SAF07Y-0415" -> "0415")
            code = store.get("code", "")
            if "-" in code:
                number = code.split("-")[-1]
                STORES_BY_NUMBER[number] = store
except Exception as e:
    logger.error(f"Error loading store data: {e}")
    STORES_BY_NUMBER = {}

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


def get_valid_chains() -> set:
    """Load valid chain names from city_chains.json reference file."""
    try:
        chains_file = STORE_RATES_SKILL.parent / "references" / "city_chains.json"
        if chains_file.exists():
            with open(chains_file, 'r') as f:
                data = json.load(f)
                # Extract all unique chains from city_chains data
                chains = set()
                for city, chain_list in data.get("city_chains", {}).items():
                    chains.update(chain_list)
                return chains
    except Exception as e:
        logger.error(f"Error loading chains: {e}")
    # Fallback to known chains
    return {"Fred Meyer", "Safeway", "Albertsons", "Quality Food Center"}


# Cache valid chains
VALID_CHAINS = get_valid_chains()


def parse_query(text: str) -> dict:
    """
    Parse a rate query intelligently.
    Supports:
    - Store numbers: "0415", "0042"
    - City + Chain: "Lincoln City Safeway", "Bend Fred Meyer"
    
    Examples:
      "0415"
      "0042"
      "Lincoln City Safeway"
      "Longview Safeway"
      "Bend Fred Meyer"
      "Portland Albertsons"
    """
    text = text.strip()
    
    # Check if input is a 4-digit store number
    if text.isdigit() and len(text) == 4:
        if text in STORES_BY_NUMBER:
            store_info = STORES_BY_NUMBER[text]
            return {
                "city": store_info.get("city", ""),
                "chain": store_info.get("name", ""),
                "payment_plan": "monthly",
                "store_number": text,
            }
        else:
            return None
    
    parts = text.split()
    
    if len(parts) < 2:
        return None
    
    # Work backwards: extract payment plan
    # Ignore ad_type and "ad"/"ads" in input — we'll show both automatically
    query_parts = parts[:]
    
    payment_plan = "monthly"
    
    # Check last part for payment plan
    if len(query_parts) > 0:
        last = query_parts[-1].lower()
        if last in PAYMENT_ALIASES:
            payment_plan = PAYMENT_ALIASES[last]
            query_parts = query_parts[:-1]
    
    # Remove "ad" or "ads" if present
    while len(query_parts) > 0 and query_parts[-1].lower() in ("ad", "ads"):
        query_parts = query_parts[:-1]
    
    # Remove single/double if mentioned (we'll show both regardless)
    while len(query_parts) > 0 and query_parts[-1].lower() in AD_TYPE_ALIASES:
        query_parts = query_parts[:-1]
    
    if len(query_parts) < 1:
        return None
    
    # Now query_parts contains: [city words...] chain
    # Find the chain by matching against VALID_CHAINS
    chain = None
    city_idx = len(query_parts)
    
    # Try to match a chain (work backwards, longest match first)
    for i in range(len(query_parts), 0, -1):
        potential_chain = " ".join(query_parts[i-1:])
        if potential_chain in VALID_CHAINS:
            chain = potential_chain
            city_idx = i - 1
            break
    
    if not chain or city_idx == 0:
        # Fallback: assume last word is chain, rest is city
        chain = query_parts[-1] if query_parts else None
        city_idx = len(query_parts) - 1
    
    if not chain or city_idx < 0:
        return None
    
    city = " ".join(query_parts[:city_idx])
    
    if not city:
        return None
    
    return {
        "city": city,
        "chain": chain,
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


def format_response(single_data: dict, double_data: dict, payment_plan: str, store_number: str = None) -> tuple:
    """
    Format the rate response showing BOTH single and double ads.
    Returns: (message_text, inline_keyboard)
    """
    store = single_data["store_name"]
    tier = single_data["tier"]
    cycle = single_data.get("cycle", "")
    
    single_plans = single_data["plans"]
    double_plans = double_data["plans"]
    
    # Determine state from cycle
    state = "OR" if cycle.endswith("Y") else "WA" if cycle.endswith("Z") else ""
    state_label = f"Oregon (07Y)" if cycle.endswith("Y") else f"Washington (07Z)" if cycle.endswith("Z") else ""
    
    store_label = store
    if store_number:
        store_label = f"{store} #{store_number}"
    
    response = f"📍 *{store_label}* | {tier} tier | {state_label}\n"
    response += f"_Year-long Campaigns_\n\n"
    
    # Single Ad column
    response += "📺 *SINGLE AD*\n"
    for plan_key in ["monthly", "3month", "6month", "paid_full"]:
        p = single_plans[plan_key]
        
        if plan_key == "paid_full":
            star = " ⭐"
        else:
            star = ""
        
        if p["num_installments"] == 1:
            response += f"• {p['description']}: ${p['annual_total']:,.2f}{star}\n"
        else:
            response += f"• {p['description']}: ${p['installment_amount']:,.2f}/mo (${p['annual_total']:,.2f}){star}\n"
    
    response += "\n"
    
    # Double Ad column
    response += "📺📺 *DOUBLE AD*\n"
    for plan_key in ["monthly", "3month", "6month", "paid_full"]:
        p = double_plans[plan_key]
        
        if plan_key == "paid_full":
            star = " ⭐"
        else:
            star = ""
        
        if p["num_installments"] == 1:
            response += f"• {p['description']}: ${p['annual_total']:,.2f}{star}\n"
        else:
            response += f"• {p['description']}: ${p['installment_amount']:,.2f}/mo (${p['annual_total']:,.2f}){star}\n"
    
    # Build inline buttons for quick plan switching
    buttons = [
        [
            InlineKeyboardButton("Monthly 💵", callback_data=f"plan_monthly"),
            InlineKeyboardButton("3-Month 📅", callback_data=f"plan_3month"),
        ],
        [
            InlineKeyboardButton("6-Month 🗓", callback_data=f"plan_6month"),
            InlineKeyboardButton("Paid-in-Full ⭐", callback_data=f"plan_paid_full"),
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    
    return response, keyboard


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command."""
    message = """🐚 *IndoorMedia Rates Bot*

Get pricing for any store — we show both single & double ads automatically.

*Quick lookup by store number:*
`0415` (Lincoln City Safeway)
`0042` (Any store by 4-digit #)

*Or by location:*
`Longview Safeway`
`Lincoln City Safeway`
`Bend Fred Meyer`
`Portland Albertsons`

We automatically show all payment plans for both ad types. Tap the buttons to switch plans instantly — no retyping needed!

*Payment Plans:* monthly, 3-month, 6-month, paid-in-full

*Need a city list?* Type `/cities`"""

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
            lines = result.stdout.strip().split("\n")  # All lines
            message = "📍 *Available Cities:*\n\n" + "\n".join(lines)
            await update.message.reply_text(message, parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Could not load city list")
    except Exception as e:
        logger.error(f"Error loading cities: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle rate queries — show both single and double ads."""
    text = update.message.text.strip()
    
    # Ignore commands
    if text.startswith("/"):
        return
    
    # Parse the query
    query = parse_query(text)
    
    if not query:
        await update.message.reply_text(
            "❌ Could not parse query. Try:\n\n`0415` (store #)\nor\n`Lincoln City Safeway`\n`Bend Fred Meyer`",
            parse_mode="Markdown"
        )
        return
    
    # Store query in context for button callbacks
    context.user_data["last_query"] = query
    
    # Get rates for BOTH single and double
    single_data = get_rates(query["city"], query["chain"], "single")
    double_data = get_rates(query["city"], query["chain"], "double")
    
    if not single_data or not double_data:
        await update.message.reply_text(
            f"❌ No rates found for {query['city']} {query['chain']}\n\nTry `/cities` to see available locations.",
            parse_mode="Markdown"
        )
        return
    
    # Format response with both ad types
    store_number = query.get("store_number")
    response, keyboard = format_response(single_data, double_data, query["payment_plan"], store_number)
    
    await update.message.reply_text(response, parse_mode="Markdown", reply_markup=keyboard)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle payment plan button clicks."""
    query = update.callback_query
    await query.answer()  # Close button loading state
    
    # Get the selected plan from callback data
    plan_key = query.data.replace("plan_", "")
    
    # Get last query from user data
    last_query = context.user_data.get("last_query")
    if not last_query:
        await query.edit_message_text("❌ Query expired. Please send a new query.")
        return
    
    # Get rates for both single and double
    single_data = get_rates(last_query["city"], last_query["chain"], "single")
    double_data = get_rates(last_query["city"], last_query["chain"], "double")
    if not single_data or not double_data:
        await query.edit_message_text("❌ Could not fetch rates.")
        return
    
    # Format with new plan
    store_number = last_query.get("store_number")
    response, keyboard = format_response(single_data, double_data, plan_key, store_number)
    
    await query.edit_message_text(response, parse_mode="Markdown", reply_markup=keyboard)


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
    application.add_handler(CallbackQueryHandler(button_callback))  # Button callbacks
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_query))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Start polling
    logger.info("🐚 IndoorMedia Rates Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
