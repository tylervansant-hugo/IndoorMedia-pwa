#!/usr/bin/env python3
"""
Integration module for advertising signals in prospect cards.
Adds ad signals detection + likelihood score boost to prospect data.
"""

import logging
from typing import Dict, Optional
import asyncio
from datetime import datetime

from advertising_signals import (
    get_all_ad_signals,
    format_ad_signals_for_display,
    get_likelihood_boost
)

logger = logging.getLogger(__name__)


def add_advertising_signals_to_prospect(prospect: Dict, force_refresh: bool = False) -> Dict:
    """
    Add advertising signals to a prospect dict.
    
    Args:
        prospect: Prospect dict from prospecting tool
        force_refresh: Skip cache and fetch fresh data
    
    Returns:
        Enhanced prospect dict with advertising_signals field
    """
    business_name = prospect.get("name", "")
    
    if not business_name:
        logger.warning("Prospect missing name — skipping ad signal check")
        return prospect
    
    try:
        # Get advertising signals (with caching)
        signals = get_all_ad_signals(business_name, force_refresh=force_refresh)
        
        # Add to prospect dict
        prospect["advertising_signals"] = signals
        
        # Extract and apply likelihood boost
        boost = get_likelihood_boost(signals)
        if boost > 0:
            # Increase likelihood score
            current_score = prospect.get("likelihood_score", 0)
            new_score = min(100, current_score + boost)  # Cap at 100
            prospect["likelihood_score"] = new_score
            prospect["likelihood_boost_from_ads"] = boost
            
            logger.info(f"✨ Boosted {business_name}: {current_score} → {new_score} (+{boost})")
        
        return prospect
    
    except Exception as e:
        logger.error(f"Error adding ad signals to {business_name}: {e}")
        # Return prospect unchanged on error (graceful fallback)
        return prospect


def enhance_prospects_batch(prospects: list, force_refresh: bool = False) -> list:
    """
    Add advertising signals to a batch of prospects.
    
    Args:
        prospects: List of prospect dicts
        force_refresh: Skip cache and fetch fresh data
    
    Returns:
        Enhanced prospects with advertising signals
    """
    enhanced = []
    for p in prospects:
        try:
            enhanced_p = add_advertising_signals_to_prospect(p, force_refresh=force_refresh)
            enhanced.append(enhanced_p)
        except Exception as e:
            logger.warning(f"Error enhancing prospect: {e}")
            enhanced.append(p)  # Add unenhanced version as fallback
    
    return enhanced


def format_prospect_card_with_signals(prospect: Dict, show_signals: bool = True) -> str:
    """
    Format a prospect card with advertising signals section.
    
    Args:
        prospect: Prospect dict with advertising_signals field
        show_signals: Whether to include signals section (default True)
    
    Returns:
        Formatted string for Telegram message
    """
    business_name = prospect.get("name", "Unknown")
    address = prospect.get("address", "")
    phone = prospect.get("phone", "")
    score = prospect.get("likelihood_score", 0)
    rating = prospect.get("rating", 0)
    
    # Header with emoji rating
    if score >= 80:
        emoji = "🔥"
    elif score >= 70:
        emoji = "⭐"
    else:
        emoji = "👀"
    
    text = f"{emoji} *{business_name}*\n"
    
    # Score line
    score_line = f"📊 {score}/100"
    if rating and rating > 0:
        stars = "⭐" * int(round(rating))
        score_line += f" | {stars} {rating:.1f}/5"
    text += score_line + "\n"
    
    # Contact info
    if phone:
        text += f"📞 {phone}\n"
    if address:
        text += f"📍 {address}\n"
    
    # Advertising signals section (if available and requested)
    if show_signals and "advertising_signals" in prospect:
        signals = prospect["advertising_signals"]
        signals_display = format_ad_signals_for_display(signals)
        if signals_display:
            text += f"\n{signals_display}"
    
    return text


def build_prospect_buttons_with_refresh(prospect_id: str) -> list:
    """
    Build buttons for prospect card including refresh signal button.
    
    Args:
        prospect_id: Unique prospect ID
    
    Returns:
        List of button rows for InlineKeyboardMarkup
    """
    buttons = [
        [
            {"text": "📍 Maps", "url": ""},  # URL added by caller
            {"text": "🎬 Video", "callback_data": f"video_{prospect_id}"},
        ],
        [
            {"text": "💾 Save", "callback_data": f"save_{prospect_id}"},
            {"text": "🔄 Refresh Signals", "callback_data": f"refresh_signals_{prospect_id}"},
        ],
        [
            {"text": "📝 Notes", "callback_data": f"note_{prospect_id}"},
            {"text": "📅 Calendar", "callback_data": f"cal_{prospect_id}"},
        ],
    ]
    return buttons


async def refresh_advertising_signals_async(business_name: str) -> Dict:
    """
    Refresh advertising signals for a business (async wrapper).
    
    Args:
        business_name: Name of business to check
    
    Returns:
        Updated signals dict
    """
    # Run in background thread to avoid blocking
    loop = asyncio.get_event_loop()
    signals = await loop.run_in_executor(
        None,
        lambda: get_all_ad_signals(business_name, force_refresh=True)
    )
    return signals


if __name__ == "__main__":
    """Test integration."""
    # Sample prospect
    test_prospect = {
        "name": "Autotek International LLC",
        "address": "123 Main St, Portland, OR 97201",
        "phone": "(503) 555-1234",
        "likelihood_score": 65,
        "rating": 4.2,
    }
    
    print("Before enhancement:")
    print(f"Score: {test_prospect['likelihood_score']}\n")
    
    # Enhance with ad signals
    enhanced = add_advertising_signals_to_prospect(test_prospect)
    
    print("After enhancement:")
    print(f"Score: {enhanced['likelihood_score']}")
    if enhanced.get("likelihood_boost_from_ads"):
        print(f"Boost: +{enhanced['likelihood_boost_from_ads']}")
    
    # Format for display
    display = format_prospect_card_with_signals(enhanced)
    print(f"\nFormatted card:\n{display}")
