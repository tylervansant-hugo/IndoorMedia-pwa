#!/usr/bin/env python3
"""
Counter Sign Telegram Workflow - Handles both direct team and guided processes
Manages user conversations for counter sign generation
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from counter_sign_generator import (
    generate_counter_sign,
    list_available_store_templates,
    get_direct_team_by_name,
    get_direct_team_names,
    DIRECT_TEAM,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states
STATE_AWAITING_STORE_CHAIN = "awaiting_store_chain"
STATE_AWAITING_AD_IMAGE = "awaiting_ad_image"
STATE_AWAITING_LANDING_PAGE = "awaiting_landing_page"
STATE_AWAITING_BUSINESS_CARD = "awaiting_business_card"
STATE_AWAITING_REP_NAME = "awaiting_rep_name"
STATE_AWAITING_REP_EMAIL = "awaiting_rep_email"
STATE_AWAITING_REP_PHONE = "awaiting_rep_phone"
STATE_GENERATING = "generating"


async def start_counter_sign_direct(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    store_code: str,
) -> int:
    """
    Start counter sign workflow for direct team members.
    Automatically looks up rep from Telegram user and pulls landing page.
    """
    user_id = update.effective_user.id
    
    # Load rep registry
    rep_registry_path = Path(__file__).parent.parent / "data" / "rep_registry.json"
    rep_registry = {}
    if rep_registry_path.exists():
        try:
            with open(rep_registry_path) as f:
                rep_registry = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load rep registry: {e}")
    
    # Find rep by user ID
    rep_name = None
    if str(user_id) in rep_registry:
        rep_name = rep_registry[str(user_id)].get('contract_name') or rep_registry[str(user_id)].get('display_name')
    
    if not rep_name:
        await update.message.reply_text(
            "❌ You are not registered as a direct team member.\n\n"
            "Use /countersign_guided to create a counter sign with your custom info."
        )
        return -1
    
    # Check if rep has landing page
    rep_data = get_direct_team_by_name(rep_name)
    if not rep_data:
        await update.message.reply_text(
            f"❌ '{rep_name}' is not in the direct team list.\n\n"
            "Contact Tyler to add you to the direct team."
        )
        return -1
    
    # Store context for later
    context.user_data['rep_name'] = rep_name
    context.user_data['store_code'] = store_code.upper()
    context.user_data['landing_page'] = rep_data.get('landing_page')
    
    await update.message.reply_text(
        f"📝 Counter Sign Generator - Direct Team\n\n"
        f"Rep: {rep_name}\n"
        f"Store: {store_code.upper()}\n\n"
        f"Please send your ad image (JPG or PNG)"
    )
    
    return STATE_AWAITING_AD_IMAGE


async def start_counter_sign_guided(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    Start guided counter sign workflow for non-direct team members.
    Walks through: store chain → business card → landing page → ad image
    """
    # Handle both callback queries and regular messages
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        chat_id = query.message.chat_id
        message_send = lambda text, **kwargs: query.edit_message_text(text, **kwargs)
    else:
        chat_id = update.effective_chat.id
        message_send = update.effective_chat.send_message
    
    # Show store chain selection
    templates = list_available_store_templates()
    
    if not templates:
        await message_send("❌ No store templates available.")
        return -1
    
    # Create keyboard with chains
    chains = sorted(templates.keys())
    keyboard = []
    for i in range(0, len(chains), 4):
        row = [
            InlineKeyboardButton(code, callback_data=f"counter_sign_chain_{code}")
            for code in chains[i:i+4]
        ]
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.user_data['_counter_sign_state'] = STATE_AWAITING_BUSINESS_CARD
    
    await message_send(
        "🎨 *Counter Sign Generator*\n\n"
        "Select your store chain:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    
    return STATE_AWAITING_STORE_CHAIN


async def handle_store_chain_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Handle store chain selection from keyboard."""
    query = update.callback_query
    await query.answer()
    
    # Extract store code
    store_code = query.data.replace("counter_sign_chain_", "")
    context.user_data['store_code'] = store_code
    
    context.user_data['_counter_sign_state'] = STATE_AWAITING_BUSINESS_CARD
    
    await query.edit_message_text(
        f"✅ Selected: {store_code}\n\n"
        "📸 Please send your business card image (JPG or PNG)"
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
    
    # Download business card image
    try:
        file = await update.message.photo[-1].get_file()
        
        # Save to temp file
        temp_dir = Path(tempfile.gettempdir()) / "counter_signs"
        temp_dir.mkdir(exist_ok=True)
        
        business_card_path = temp_dir / f"business_card_{update.effective_user.id}.jpg"
        await file.download_to_drive(business_card_path)
        
        context.user_data['business_card_path'] = str(business_card_path)
        context.user_data['_counter_sign_state'] = STATE_AWAITING_LANDING_PAGE
        
        await update.message.reply_text(
            "✅ Business card saved.\n\n"
            "Do you have a landing page URL? Reply with the URL or type 'none'"
        )
        
        return STATE_AWAITING_LANDING_PAGE
    
    except Exception as e:
        logger.error(f"Error downloading business card: {e}")
        await update.message.reply_text("❌ Error saving business card. Try again.")
        return STATE_AWAITING_BUSINESS_CARD


async def handle_landing_page_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Handle landing page URL input."""
    if not update.message.text:
        await update.message.reply_text("❌ Please send a valid URL or 'none'")
        return STATE_AWAITING_LANDING_PAGE
    
    landing_page = update.message.text.strip()
    if landing_page.lower() != 'none' and not landing_page.startswith('http'):
        await update.message.reply_text("❌ URL must start with http:// or https://")
        return STATE_AWAITING_LANDING_PAGE
    
    context.user_data['landing_page'] = landing_page
    context.user_data['_counter_sign_state'] = STATE_AWAITING_REP_NAME
    
    # Collect rep info
    await update.message.reply_text(
        "📋 Now I need your business info.\n\n"
        "What is your name?"
    )
    
    return STATE_AWAITING_REP_NAME


async def handle_rep_name_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Handle rep name input."""
    if not update.message.text:
        await update.message.reply_text("❌ Please send a valid name.")
        return STATE_AWAITING_REP_NAME
    
    context.user_data['rep_name'] = update.message.text.strip()
    context.user_data['_counter_sign_state'] = STATE_AWAITING_REP_EMAIL
    
    await update.message.reply_text("What is your email address?")
    return STATE_AWAITING_REP_EMAIL


async def handle_rep_email_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Handle rep email input."""
    if not update.message.text:
        await update.message.reply_text("❌ Please send a valid email.")
        return STATE_AWAITING_REP_EMAIL
    
    context.user_data['rep_email'] = update.message.text.strip()
    context.user_data['_counter_sign_state'] = STATE_AWAITING_REP_PHONE
    
    await update.message.reply_text("What is your phone number?")
    return STATE_AWAITING_REP_PHONE


async def handle_rep_phone_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Handle rep phone input."""
    if not update.message.text:
        await update.message.reply_text("❌ Please send a valid phone number.")
        return STATE_AWAITING_REP_PHONE
    
    context.user_data['rep_phone'] = update.message.text.strip()
    context.user_data['_counter_sign_state'] = STATE_AWAITING_AD_IMAGE
    
    # Now ask for ad image
    await update.message.reply_text(
        "📸 Perfect! Now please send your ad image (JPG or PNG)."
    )
    
    return STATE_AWAITING_AD_IMAGE


async def handle_ad_image_upload(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Handle ad image upload and generate counter sign."""
    if not update.message.photo:
        await update.message.reply_text("❌ Please send a valid image.")
        return STATE_AWAITING_AD_IMAGE
    
    try:
        await update.message.reply_text("⏳ Generating counter sign... please wait")
        
        # Download ad image
        file = await update.message.photo[-1].get_file()
        
        temp_dir = Path(tempfile.gettempdir()) / "counter_signs"
        temp_dir.mkdir(exist_ok=True)
        
        ad_image_path = temp_dir / f"ad_image_{update.effective_user.id}_{context.user_data.get('store_code', 'unknown')}.jpg"
        await file.download_to_drive(ad_image_path)
        
        # Build rep data
        rep_data = {
            'name': context.user_data.get('rep_name', 'Rep'),
            'email': context.user_data.get('rep_email', ''),
            'cell': context.user_data.get('rep_phone', ''),
            'corporate': '800.247.4793',
        }
        
        # Generate counter sign
        pdf_bytes, output_path = generate_counter_sign(
            chain_code=context.user_data.get('store_code', 'UNK'),
            ad_image_path=str(ad_image_path),
            rep_data=rep_data,
            landing_page_url=context.user_data.get('landing_page'),
            business_card_path=context.user_data.get('business_card_path'),
        )
        
        if pdf_bytes:
            # Send PDF
            with open(output_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=Path(output_path).name,
                    caption="✅ Your counter sign is ready!\n\nPrint on 8.5\" × 11\" paper."
                )
            logger.info(f"Counter sign generated for user {update.effective_user.id}")
        else:
            await update.message.reply_text("❌ Error generating counter sign. Please try again.")
        
        # Cleanup
        try:
            ad_image_path.unlink()
        except:
            pass
        
        return -1
    
    except Exception as e:
        logger.error(f"Error handling ad image: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
        return STATE_AWAITING_AD_IMAGE


async def handle_direct_team_ad_image(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Handle ad image upload for direct team members and generate sign."""
    if not update.message.photo:
        await update.message.reply_text("❌ Please send a valid image (JPG or PNG).")
        return STATE_AWAITING_AD_IMAGE
    
    try:
        await update.message.reply_text("⏳ Generating counter sign... please wait")
        
        # Download ad image
        file = await update.message.photo[-1].get_file()
        
        temp_dir = Path(tempfile.gettempdir()) / "counter_signs"
        temp_dir.mkdir(exist_ok=True)
        
        ad_image_path = temp_dir / f"ad_image_{update.effective_user.id}_{context.user_data.get('store_code')}.jpg"
        await file.download_to_drive(ad_image_path)
        
        # Build rep data from DIRECT_TEAM
        rep_name = context.user_data.get('rep_name')
        rep_full_data = get_direct_team_by_name(rep_name)
        
        rep_data = {
            'name': rep_name,
            'email': rep_full_data.get('email', ''),
            'cell': rep_full_data.get('cell', ''),
            'corporate': rep_full_data.get('corporate', '800.247.4793'),
        }
        
        # Generate counter sign
        pdf_bytes, output_path = generate_counter_sign(
            chain_code=context.user_data.get('store_code'),
            ad_image_path=str(ad_image_path),
            rep_data=rep_data,
            landing_page_url=context.user_data.get('landing_page'),
            business_card_path=context.user_data.get('business_card_path'),
        )
        
        if pdf_bytes and output_path:
            # Send PDF
            with open(output_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=Path(output_path).name,
                    caption="✅ Your counter sign is ready!\n\nPrint on 8.5\" × 11\" paper."
                )
            logger.info(f"Counter sign generated for direct team rep {rep_name}")
        else:
            await update.message.reply_text("❌ Error generating counter sign. Please try again.")
        
        # Cleanup
        try:
            ad_image_path.unlink()
        except:
            pass
        
        return -1
    
    except Exception as e:
        logger.error(f"Error handling ad image for direct team: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
        return STATE_AWAITING_AD_IMAGE


def get_workflow_handlers() -> Dict:
    """
    Return dict of workflow handlers for integration into telegram bot.
    """
    return {
        'state_awaiting_store_chain': STATE_AWAITING_STORE_CHAIN,
        'state_awaiting_ad_image': STATE_AWAITING_AD_IMAGE,
        'state_awaiting_landing_page': STATE_AWAITING_LANDING_PAGE,
        'state_awaiting_business_card': STATE_AWAITING_BUSINESS_CARD,
        'state_awaiting_rep_name': STATE_AWAITING_REP_NAME,
        'state_awaiting_rep_email': STATE_AWAITING_REP_EMAIL,
        'state_awaiting_rep_phone': STATE_AWAITING_REP_PHONE,
        'handle_store_chain_selection': handle_store_chain_selection,
        'handle_business_card_upload': handle_business_card_upload,
        'handle_landing_page_input': handle_landing_page_input,
        'handle_rep_name_input': handle_rep_name_input,
        'handle_rep_email_input': handle_rep_email_input,
        'handle_rep_phone_input': handle_rep_phone_input,
        'handle_ad_image_upload': handle_ad_image_upload,
        'handle_direct_team_ad_image': handle_direct_team_ad_image,
    }
