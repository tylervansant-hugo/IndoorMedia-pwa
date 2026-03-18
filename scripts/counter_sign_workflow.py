#!/usr/bin/env python3
"""
Counter Sign Telegram Workflow - Simplified workflow
Store chain → business card → landing page → ad image → PDF
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

try:
    from counter_sign_generator import (
        generate_counter_sign,
        list_available_store_templates,
    )
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from counter_sign_generator import (
        generate_counter_sign,
        list_available_store_templates,
    )

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states - SIMPLIFIED
STATE_AWAITING_STORE_CHAIN = "awaiting_store_chain"
STATE_AWAITING_BUSINESS_CARD = "awaiting_business_card"
STATE_AWAITING_LANDING_PAGE = "awaiting_landing_page"
STATE_AWAITING_AD_IMAGE = "awaiting_ad_image"
STATE_GENERATING = "generating"


async def start_counter_sign_guided(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Start the counter sign generation workflow."""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        message_send = lambda text, **kwargs: query.edit_message_text(text, **kwargs)
    else:
        message_send = update.effective_chat.send_message

    # Show store chain selection
    templates = list_available_store_templates()

    if not templates:
        await message_send("❌ No store templates available.")
        return -1

    # Create keyboard with chains
    chains = sorted(templates.keys())
    keyboard = []
    for i in range(0, len(chains), 5):
        row = [
            InlineKeyboardButton(code, callback_data=f"counter_sign_chain_{code}")
            for code in chains[i:i+5]
        ]
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)
    context.user_data['_counter_sign_state'] = STATE_AWAITING_BUSINESS_CARD

    await message_send(
        "🏪 Select store chain:",
        reply_markup=reply_markup
    )

    return STATE_AWAITING_STORE_CHAIN


async def handle_store_chain_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Handle store chain selection callback."""
    query = update.callback_query
    await query.answer()

    # Extract chain code from callback data
    chain_code = query.data.replace("counter_sign_chain_", "")
    context.user_data['store_chain'] = chain_code
    context.user_data['_counter_sign_state'] = STATE_AWAITING_BUSINESS_CARD

    await query.edit_message_text(
        f"📸 Store: **{chain_code}**\n\nNow send your **business card image** (JPG or PNG)"
    )

    return STATE_AWAITING_BUSINESS_CARD


async def handle_business_card_upload(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Handle business card image upload."""
    if not update.message.photo:
        await update.message.reply_text("❌ Please send a valid image.")
        return STATE_AWAITING_BUSINESS_CARD

    try:
        # Download and save business card image (use highest resolution)
        photo = update.message.photo[-1]  # Get highest resolution available
        file = await context.bot.get_file(photo.file_id)
        
        temp_dir = Path(tempfile.gettempdir()) / "counter_signs"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        card_path = temp_dir / f"business_card_{update.effective_user.id}.jpg"
        await file.download_to_drive(card_path)
        
        context.user_data['business_card_path'] = str(card_path)
        context.user_data['_counter_sign_state'] = STATE_AWAITING_LANDING_PAGE
        
        await update.message.reply_text(
            "✅ Business card saved!\n\nNow enter your **landing page URL**\n"
            "(or type 'none' for phone fallback)"
        )

        return STATE_AWAITING_LANDING_PAGE

    except Exception as e:
        logger.error(f"Error saving business card: {e}")
        await update.message.reply_text(f"❌ Error: {e}")
        return STATE_AWAITING_BUSINESS_CARD


async def handle_landing_page_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Handle landing page URL input."""
    if not update.message.text:
        await update.message.reply_text("❌ Please enter a valid URL or 'none'.")
        return STATE_AWAITING_LANDING_PAGE

    url = update.message.text.strip()
    
    # Validate URL
    if url.lower() != 'none':
        if not (url.startswith('http://') or url.startswith('https://')):
            await update.message.reply_text(
                "❌ URL must start with http:// or https://\n"
                "Or type 'none' for phone fallback."
            )
            return STATE_AWAITING_LANDING_PAGE

    context.user_data['landing_page_url'] = url
    context.user_data['_counter_sign_state'] = STATE_AWAITING_AD_IMAGE

    await update.message.reply_text(
        "✅ Landing page saved!\n\nNow send your **ad image** (JPG or PNG)"
    )

    return STATE_AWAITING_AD_IMAGE


async def handle_ad_image_upload(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Handle ad image upload and generate PDF."""
    if not update.message.photo:
        await update.message.reply_text("❌ Please send a valid image.")
        return STATE_AWAITING_AD_IMAGE

    try:
        logger.info(f"Starting ad image upload for user {update.effective_user.id}")
        context.user_data['_counter_sign_state'] = STATE_GENERATING
        
        # Download ad image
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        temp_dir = Path(tempfile.gettempdir()) / "counter_signs"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        ad_path = temp_dir / f"ad_image_{update.effective_user.id}.jpg"
        await file.download_to_drive(ad_path)

        # Get user info
        store_chain = context.user_data.get('store_chain', 'UNKNOWN')
        business_card_path = context.user_data.get('business_card_path')
        landing_page_url = context.user_data.get('landing_page_url', 'none')
        user_name = update.effective_user.first_name or "User"

        # Generate counter sign PDF
        await update.message.reply_text("⏳ Generating counter sign... (this may take a moment)")

        pdf_bytes, pdf_path = generate_counter_sign(
            chain_code=store_chain,
            ad_image_path=str(ad_path),
            rep_name=user_name,
            rep_cell="800.247.4793",
            rep_email="info@indoormedia.com",
            landing_page_url=landing_page_url,
            business_card_path=business_card_path,
        )

        if pdf_bytes and pdf_path:
            # Send PDF to user
            try:
                with open(pdf_path, 'rb') as pdf_file:
                    await update.message.reply_document(
                        document=pdf_file,
                        filename=f"{store_chain}_{user_name}_{pdf_path.split('/')[-1]}",
                        caption="✅ Your counter sign is ready!\n\nPrint on 8.5\" × 11\" paper."
                    )
                logger.info(f"✅ Counter sign generated: {pdf_path}")
            except Exception as e:
                logger.error(f"Error sending PDF: {e}")
                await update.message.reply_text(f"❌ Error sending PDF: {e}")
        else:
            await update.message.reply_text("❌ Error generating PDF. Please try again.")
            logger.error(f"PDF generation returned None for {store_chain}")

        # Reset state
        context.user_data['_counter_sign_state'] = None

        return -1

    except Exception as e:
        logger.error(f"Error in ad image upload: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error: {str(e)}")
        context.user_data['_counter_sign_state'] = None
        return -1
