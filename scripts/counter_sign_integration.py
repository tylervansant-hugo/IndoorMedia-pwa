#!/usr/bin/env python3
"""
Counter Sign Bot Integration - Adds /countersign commands to telegram bot
Patch to integrate with telegram_prospecting_bot.py
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)

from counter_sign_workflow import (
    start_counter_sign_direct,
    start_counter_sign_guided,
    handle_store_chain_selection,
    handle_business_card_upload,
    handle_landing_page_input,
    handle_rep_name_input,
    handle_rep_email_input,
    handle_rep_phone_input,
    handle_ad_image_upload,
    handle_direct_team_ad_image,
    STATE_AWAITING_STORE_CHAIN,
    STATE_AWAITING_AD_IMAGE,
    STATE_AWAITING_LANDING_PAGE,
    STATE_AWAITING_BUSINESS_CARD,
    STATE_AWAITING_REP_NAME,
    STATE_AWAITING_REP_EMAIL,
    STATE_AWAITING_REP_PHONE,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def countersign_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle /countersign command.
    Usage: /countersign [store_code]
    Example: /countersign SAF
    
    For direct team members only.
    """
    user_id = update.effective_user.id
    
    # Get store code from args
    args = context.args
    
    if not args:
        # Show help
        await update.message.reply_text(
            "📝 Counter Sign Generator\n\n"
            "Usage: /countersign [STORE_CODE]\n"
            "Example: /countersign SAF\n\n"
            "Or use /countersign_guided for custom counter signs."
        )
        return -1
    
    store_code = args[0].upper()
    
    # Start direct team workflow
    return await start_counter_sign_direct(update, context, store_code)


async def countersign_guided_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle /countersign_guided command.
    For non-direct team members to create custom counter signs.
    """
    # Start guided workflow
    return await start_counter_sign_guided(update, context)


def get_counter_sign_handlers() -> list:
    """
    Get the conversation handlers for counter sign workflows.
    These should be added to the telegram app.
    
    Returns list of handlers to add to app.
    """
    
    # DIRECT TEAM WORKFLOW (just /countersign [code] + ad image)
    direct_team_conv = ConversationHandler(
        entry_points=[CommandHandler("countersign", countersign_command)],
        states={
            STATE_AWAITING_AD_IMAGE: [
                MessageHandler(filters.PHOTO, handle_direct_team_ad_image),
                CommandHandler("cancel", cancel_workflow),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_workflow),
        ],
        per_user=True,
    )
    
    # GUIDED WORKFLOW (store → card → landing page → ad image)
    guided_conv = ConversationHandler(
        entry_points=[CommandHandler("countersign_guided", countersign_guided_command)],
        states={
            STATE_AWAITING_STORE_CHAIN: [
                CallbackQueryHandler(handle_store_chain_selection, pattern="^counter_sign_chain_"),
                CommandHandler("cancel", cancel_workflow),
            ],
            STATE_AWAITING_BUSINESS_CARD: [
                MessageHandler(filters.PHOTO, handle_business_card_upload),
                CommandHandler("cancel", cancel_workflow),
            ],
            STATE_AWAITING_LANDING_PAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_landing_page_input),
                CommandHandler("cancel", cancel_workflow),
            ],
            STATE_AWAITING_REP_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rep_name_input),
                CommandHandler("cancel", cancel_workflow),
            ],
            STATE_AWAITING_REP_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rep_email_input),
                CommandHandler("cancel", cancel_workflow),
            ],
            STATE_AWAITING_REP_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rep_phone_input),
                CommandHandler("cancel", cancel_workflow),
            ],
            STATE_AWAITING_AD_IMAGE: [
                MessageHandler(filters.PHOTO, handle_ad_image_upload),
                CommandHandler("cancel", cancel_workflow),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_workflow),
        ],
        per_user=True,
    )
    
    return [direct_team_conv, guided_conv]


async def cancel_workflow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel counter sign workflow."""
    await update.message.reply_text("❌ Counter sign generation cancelled.")
    context.user_data.clear()
    return -1


def add_counter_sign_handlers_to_app(app):
    """
    Add counter sign handlers to a telegram Application.
    Call this in telegram_prospecting_bot.py main() function.
    
    Usage:
        from counter_sign_integration import add_counter_sign_handlers_to_app
        ...
        app = Application.builder().token(TOKEN).build()
        ...
        add_counter_sign_handlers_to_app(app)
        ...
    """
    try:
        handlers = get_counter_sign_handlers()
        for handler in handlers:
            app.add_handler(handler)
        logger.info("✅ Counter sign handlers added to bot")
    except Exception as e:
        logger.error(f"❌ Failed to add counter sign handlers: {e}")


# Update bot commands list
def get_counter_sign_commands() -> list:
    """Get counter sign commands for bot menu."""
    return [
        ("countersign", "📋 Generate counter sign (direct team: /countersign [CODE])"),
        ("countersign_guided", "📋 Create custom counter sign"),
    ]
