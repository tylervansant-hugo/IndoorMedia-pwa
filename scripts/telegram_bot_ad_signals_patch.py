#!/usr/bin/env python3
"""
Patch for telegram_prospecting_bot.py to integrate advertising signals.
This module adds callbacks and signal detection to the prospect workflow.

To use: Import this module in telegram_prospecting_bot.py after handler setup.
"""

import logging
from typing import Dict, Optional
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from advertising_signals import get_all_ad_signals, format_ad_signals_for_display
from prospect_advertising_integration import add_advertising_signals_to_prospect

logger = logging.getLogger(__name__)


async def handle_refresh_signals_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle refresh signals button click."""
    query = update.callback_query
    callback_data = query.data
    
    # Extract prospect ID: refresh_signals_<id>
    prospect_id = callback_data.replace("refresh_signals_", "")
    
    # Get prospect from context
    prospect = context.user_data.get('prospects', {}).get(prospect_id)
    if not prospect:
        await query.answer("❌ Prospect not found", show_alert=True)
        return
    
    business_name = prospect.get('name', '')
    if not business_name:
        await query.answer("❌ Business name not found", show_alert=True)
        return
    
    await query.answer("🔄 Checking advertising signals...", show_alert=False)
    
    try:
        # Fetch fresh signals (force_refresh=True)
        signals = get_all_ad_signals(business_name, force_refresh=True)
        
        # Update prospect in context
        context.user_data['prospects'][prospect_id]['advertising_signals'] = signals
        
        # Extract boost
        boost = signals.get('likelihood_boost', 0)
        current_score = prospect.get('likelihood_score', 0)
        new_score = min(100, current_score + boost) if boost > 0 else current_score
        
        # Update prospect data
        context.user_data['prospects'][prospect_id]['likelihood_score'] = new_score
        context.user_data['prospects'][prospect_id]['likelihood_boost_from_ads'] = boost
        
        # Build result message
        msg = f"✅ *Signals Refreshed for {business_name}*\n\n"
        
        if signals.get('found_advertising'):
            msg += "🎬 *ADVERTISING DETECTED*\n\n"
            
            platforms = signals.get('platforms', {})
            if platforms.get('meta', {}).get('found'):
                msg += "📘 **Meta Ads Library** — Active advertising found\n"
            if platforms.get('google', {}).get('found'):
                msg += "🔍 **Google Ads Library** — Active advertising found\n"
            
            msg += f"\n✨ **+{boost} Likelihood Boost** Applied\n"
            msg += f"Score: {current_score} → {new_score}/100\n"
        else:
            msg += "No advertising detected on Meta or Google platforms.\n"
            msg += "This business may not be investing in digital marketing.\n"
        
        # Checked timestamp
        checked_at = signals.get('checked_at', '')
        if checked_at:
            try:
                dt = datetime.fromisoformat(checked_at)
                msg += f"\n_Checked: {dt.strftime('%I:%M %p')}_"
            except:
                pass
        
        buttons = [
            [InlineKeyboardButton("⬅️ Back to Prospect", callback_data=f"expand_{prospect_id}")],
            [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")],
        ]
        
        await query.edit_message_text(
            msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    except Exception as e:
        logger.error(f"Error refreshing signals: {e}")
        await query.answer(f"⚠️ Error: {str(e)[:50]}", show_alert=True)


def register_ad_signals_handlers(application):
    """
    Register advertising signals handlers with the bot application.
    
    Args:
        application: telegram.ext.Application instance
    
    Usage:
        from telegram_bot_ad_signals_patch import register_ad_signals_handlers
        register_ad_signals_handlers(app)
    """
    from telegram.ext import CallbackQueryHandler
    
    # Register refresh signals handler
    application.add_handler(
        CallbackQueryHandler(
            handle_refresh_signals_callback,
            pattern=r"^refresh_signals_"
        )
    )
    
    logger.info("✅ Advertising signals handlers registered")


def enhance_prospect_display(prospect: Dict, include_signals: bool = True) -> str:
    """
    Build enhanced prospect display with advertising signals.
    
    Args:
        prospect: Prospect dict from context
        include_signals: Whether to include ad signals section
    
    Returns:
        Formatted string for Telegram message
    """
    business_name = prospect.get('name', 'Unknown')
    address = prospect.get('address', '')
    phone = prospect.get('phone', '')
    score = prospect.get('likelihood_score', 0)
    rating = prospect.get('rating', 0)
    distance = prospect.get('distance_miles', 'N/A')
    
    # Emoji rating
    if score >= 80:
        emoji = "🔥"
    elif score >= 70:
        emoji = "⭐"
    else:
        emoji = "👀"
    
    # Build text
    text = f"{emoji} *{business_name}*\n"
    
    # Score line
    score_line = f"📊 {score}/100"
    if rating and rating > 0:
        stars = "⭐" * int(round(rating))
        score_line += f" | {stars} {rating:.1f}/5"
    text += score_line + "\n"
    
    # Distance
    if distance and distance != 'N/A':
        text += f"📏 {distance} mi\n"
    
    # Contact
    if phone:
        text += f"📞 {phone}\n"
    if address:
        text += f"📍 {address}\n"
    
    # Ad signals
    if include_signals:
        signals = prospect.get('advertising_signals')
        if signals and signals.get('found_advertising'):
            display = format_ad_signals_for_display(signals)
            if display:
                text += f"\n{display}"
        
        boost = prospect.get('likelihood_boost_from_ads', 0)
        if boost > 0:
            text += f"\n✨ *+{boost} boost* (from advertising signals)"
    
    return text


if __name__ == "__main__":
    """Test the patch."""
    # Sample prospect
    test_prospect = {
        'name': 'Example Business',
        'address': '123 Main St, Portland, OR',
        'phone': '(503) 555-1234',
        'likelihood_score': 75,
        'rating': 4.5,
        'distance_miles': 2.3,
        'advertising_signals': {
            'business': 'Example Business',
            'found_advertising': True,
            'likelihood_boost': 15,
            'platforms': {
                'meta': {'found': True, 'active_ads': 5},
                'google': {'found': True, 'ad_count': 3}
            }
        }
    }
    
    display = enhance_prospect_display(test_prospect)
    print("Enhanced Prospect Display:\n")
    print(display)
