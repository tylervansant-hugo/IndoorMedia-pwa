#!/usr/bin/env python3
"""
Integration hooks for quarterly ROI report generator into Telegram bot.

This module provides functions to integrate ROI report generation
into the telegram_prospecting_bot audit timeline and event handlers.

Usage:
    from roi_telegram_integration import (
        add_roi_button_to_audit_event,
        handle_roi_report_callback,
        format_roi_report_for_telegram
    )
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from quarterly_roi_generator import (
    generate_quarterly_roi_report,
    quarterly_roi_email_template,
    load_contract_metrics,
    QuarterlyROITracker,
    create_audit_event_button_data,
)


def add_roi_button_to_audit_event(
    existing_buttons: List[List[InlineKeyboardButton]],
    contact_email: str,
    store_number: str,
) -> List[List[InlineKeyboardButton]]:
    """
    Add "📊 Generate Q ROI Report" button to existing audit event buttons.
    
    Args:
        existing_buttons: List of button rows from audit event
        contact_email: Customer contact email
        store_number: Store/location number
    
    Returns:
        Updated buttons list with ROI button added
    """
    
    roi_button = InlineKeyboardButton(
        text="📊 Generate Q ROI Report",
        callback_data=f"roi_report:{contact_email}:{store_number}"
    )
    
    # Insert ROI button before "Back" button
    if existing_buttons and existing_buttons[-1]:
        last_button = existing_buttons[-1][0]
        if hasattr(last_button, 'text') and 'Back' in last_button.text:
            existing_buttons.insert(-1, [roi_button])
        else:
            existing_buttons.append([roi_button])
    else:
        existing_buttons.append([roi_button])
    
    return existing_buttons


def format_roi_report_for_telegram(
    report: Dict[str, Any],
    include_metrics: bool = True
) -> str:
    """
    Format ROI report for Telegram message (respects 4096 char limit).
    
    Args:
        report: Output from generate_quarterly_roi_report()
        include_metrics: Include detailed metrics section
    
    Returns:
        Telegram-friendly formatted text
    """
    
    stats = report["summary_stats"]
    roi = report["roi_metrics"]
    
    # Telegram-friendly formatting (no fancy unicode boxes)
    text = f"""📊 *QUARTERLY ROI REPORT*

*{stats['business_name']}*
Store: {stats['store_number']} | {stats['quarter']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

*PERFORMANCE SUMMARY*

✓ Coupons Redeemed: {stats['coupon_count']}
✓ Gross Revenue: ${stats['gross_revenue']:,.2f}
✓ Gross Profit: ${stats['gross_profit']:,.2f}
✓ ROI: {stats['roi_percent']:.1f}%

"""
    
    if stats['is_better_than_free']:
        text += "*🚀 STATUS: BETTER THAN FREE - Ad paid for itself!*\n\n"
    else:
        text += "*📈 STATUS: POSITIVE MOMENTUM*\n\n"
    
    text += f"""*EXPANSION OPPORTUNITY*

{stats['expansion_opportunity']}

*Next Step:* Schedule expansion discussion with your rep.

"""
    
    if include_metrics:
        text += f"""*CAMPAIGN DETAILS*

Duration: {stats['months_active']} month{'s' if stats['months_active'] != 1 else ''}
Avg Transaction: ${stats['avg_transaction_value']:.2f}
Report Generated: {stats['report_date'][:10]}
"""
    
    return text


async def handle_roi_report_callback(
    update,
    context,
    callback_data: str,
) -> str:
    """
    Handle ROI report callback from Telegram button press.
    
    Callback format: roi_report:contact_email:store_number
    
    Args:
        update: Telegram update object
        context: Telegram context object
        callback_data: Callback data string from button
    
    Returns:
        Message text to send to user
    """
    
    try:
        parts = callback_data.split(":")
        if len(parts) < 3:
            return "❌ Invalid ROI report request format."
        
        contact_email = parts[1]
        store_number = parts[2]
        
        # Load contract data
        contract = load_contract_metrics(contact_email)
        if not contract:
            return f"❌ No contract found for {contact_email}"
        
        # Check if already reported this quarter
        tracker = QuarterlyROITracker()
        current_quarter = f"{datetime.now().year}-Q{(datetime.now().month - 1) // 3 + 1}"
        
        if tracker.is_reported(contact_email, current_quarter):
            return (
                f"⚠️ ROI report already generated for {current_quarter}\n\n"
                f"Contact: {contact_email}\n"
                f"Store: {store_number}\n\n"
                f"Next report will be available next quarter."
            )
        
        # For now, generate with placeholder metrics
        # In production, these would come from coupon/redemption data
        report = generate_quarterly_roi_report(
            business_name=contract.get("business_name", "Unknown"),
            contact_name=contract.get("contact_name", "Unknown"),
            contact_email=contact_email,
            store_number=store_number,
            start_date=contract.get("date", datetime.now().isoformat()),
            months_active=1,  # TODO: Calculate actual months in service
            coupon_count=0,  # TODO: Load actual coupon redemptions
            avg_transaction_value=0.0,  # TODO: Load actual transaction data
            cogs_percent=0.30,
            total_contract_amount=contract.get("total_amount", 0.0),
            store_name=contract.get("store_name", ""),
        )
        
        # Mark as reported
        tracker.mark_reported(contact_email, current_quarter)
        
        # Format for Telegram
        message_text = format_roi_report_for_telegram(report)
        
        # Add copy-to-email hint
        message_text += "\n\n💡 *To send via email:*\n`/roi_email " + contact_email + "`"
        
        return message_text
    
    except Exception as e:
        return f"❌ Error generating ROI report: {str(e)}"


async def send_roi_email_callback(
    update,
    context,
    contact_email: str,
    rep_name: str,
) -> str:
    """
    Prepare ROI report for email send.
    
    This generates the email template ready for copy/paste or API send.
    
    Args:
        update: Telegram update object
        context: Telegram context object
        contact_email: Customer contact email
        rep_name: Sales rep name
    
    Returns:
        Email template ready to send
    """
    
    try:
        contract = load_contract_metrics(contact_email)
        if not contract:
            return f"❌ No contract found for {contact_email}"
        
        # Generate report with placeholder metrics
        report = generate_quarterly_roi_report(
            business_name=contract.get("business_name", "Unknown"),
            contact_name=contract.get("contact_name", "Unknown"),
            contact_email=contact_email,
            store_number=contract.get("store_number", ""),
            start_date=contract.get("date", datetime.now().isoformat()),
            months_active=1,
            coupon_count=0,
            avg_transaction_value=0.0,
            cogs_percent=0.30,
            total_contract_amount=contract.get("total_amount", 0.0),
            store_name=contract.get("store_name", ""),
        )
        
        # Generate email
        email_text = quarterly_roi_email_template(
            business_name=contract.get("business_name", "Unknown"),
            contact_name=contract.get("contact_name", "Unknown"),
            contact_email=contact_email,
            store_number=contract.get("store_number", ""),
            rep_name=rep_name,
            report=report,
        )
        
        # Format for Telegram (with code block for easy copying)
        response = "✅ *ROI Email Ready to Send*\n\n"
        response += "```\n" + email_text + "\n```\n\n"
        response += "(Copy above text and send via your email client)"
        
        return response
    
    except Exception as e:
        return f"❌ Error preparing email: {str(e)}"


def get_roi_button_for_contract(contract: Dict[str, Any]) -> InlineKeyboardButton:
    """
    Create ROI report button for a single contract card.
    
    Args:
        contract: Contract dict from contracts.json
    
    Returns:
        InlineKeyboardButton ready for use in Telegram
    """
    
    button_data = create_audit_event_button_data(
        business_name=contract.get("business_name", ""),
        contact_name=contract.get("contact_name", ""),
        contact_email=contract.get("contact_email", ""),
        store_number=contract.get("store_number", ""),
        rep_name=contract.get("sales_rep", ""),
    )
    
    return InlineKeyboardButton(
        text=button_data["button_text"],
        callback_data=button_data["callback_data"]
    )


def batch_roi_notification(rep_name: str) -> str:
    """
    Generate a batch notification of ROI reports ready to send.
    
    Args:
        rep_name: Sales rep name
    
    Returns:
        Formatted message with list of customers ready for ROI reports
    """
    
    workspace = Path(__file__).parent.parent
    contracts_file = workspace / "data" / "contracts.json"
    
    try:
        contracts_data = json.loads(contracts_file.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return "❌ Could not load contract data"
    
    # Filter by rep
    rep_contracts = [
        c for c in contracts_data.get("contracts", [])
        if c.get("sales_rep") == rep_name
    ]
    
    if not rep_contracts:
        return f"No active contracts for {rep_name}"
    
    # Build notification
    message = f"📊 *ROI Reports Ready - {rep_name}*\n\n"
    message += f"You have {len(rep_contracts)} active customer(s).\n\n"
    
    for contract in rep_contracts[:5]:  # Show first 5
        message += (
            f"• {contract.get('business_name')}\n"
            f"  Store: {contract.get('store_number')}\n"
            f"  Contact: {contract.get('contact_name')}\n\n"
        )
    
    if len(rep_contracts) > 5:
        message += f"... and {len(rep_contracts) - 5} more\n\n"
    
    message += "/roi_batch_send to generate all reports"
    
    return message


# Integration points for telegram_prospecting_bot.py:
#
# 1. Add to button handlers:
#    elif query.data.startswith("roi_report:"):
#        message = await handle_roi_report_callback(update, context, query.data)
#        await query.answer(message, show_alert=True)
#
# 2. Add ROI button to audit store card:
#    buttons = add_roi_button_to_audit_event(existing_buttons, email, store_num)
#
# 3. Add command handler:
#    application.add_handler(CommandHandler("roi_report", cmd_roi_report))
#    application.add_handler(CommandHandler("roi_email", cmd_roi_email))
