# Telegram Bot Integration Guide - ROI Reports

This guide shows exactly where and how to integrate the quarterly ROI report generator into `telegram_prospecting_bot.py`.

## Step 1: Import Statements

Add to the imports section at the top of `telegram_prospecting_bot.py`:

```python
# Around line 1-50, with other imports
from roi_telegram_integration import (
    add_roi_button_to_audit_event,
    handle_roi_report_callback,
    format_roi_report_for_telegram,
    send_roi_email_callback,
)
```

## Step 2: Add Callback Handler for ROI Button

Find the main callback query handler (around line 2500-3000 where button presses are handled).

Look for the section like:
```python
async def handle_button_press(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button presses."""
    query = update.callback_query
    
    if query.data.startswith("action_"):
        # ...existing code...
```

Add this new elif block BEFORE the final else:

```python
    # ========== ROI REPORT HANDLER ==========
    elif query.data.startswith("roi_report:"):
        """Handle ROI report generation from audit events."""
        try:
            message_text = await handle_roi_report_callback(update, context, query.data)
            await query.answer(message_text, show_alert=True)
        except Exception as e:
            await query.answer(f"❌ Error: {str(e)}", show_alert=True)
```

## Step 3: Add ROI Button to Audit Store Card

Find where audit store information is displayed (around line 1680-1720).

Look for the section that builds audit buttons:
```python
    # Build audit confirmation buttons
    buttons = [
        [InlineKeyboardButton("✅ Yes, Correct", callback_data="audit_confirm_yes")],
        [InlineKeyboardButton("❌ No, Adjust", callback_data="audit_confirm_no")],
        [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")],
    ]
```

**Replace** that section with:
```python
    # Build audit confirmation buttons
    buttons = [
        [InlineKeyboardButton("✅ Yes, Correct", callback_data="audit_confirm_yes")],
        [InlineKeyboardButton("❌ No, Adjust", callback_data="audit_confirm_no")],
        [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")],
    ]
    
    # Add ROI report button for customer contracts
    audit_info = context.user_data.get('audit_info', {})
    if audit_info.get('contact_email'):
        buttons = add_roi_button_to_audit_event(
            buttons,
            audit_info.get('contact_email'),
            audit_info.get('store_num', store_num)
        )
```

## Step 4: Add Command Handler for ROI Email

Find where command handlers are registered (around line 150-200, usually at the end of the main/setup function).

Add these command handlers:

```python
    # === ROI Report Commands ===
    async def cmd_roi_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Generate ROI report for a customer. Usage: /roi_report email@customer.com"""
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "Usage: `/roi_report customer@email.com`\n\n"
                "Shows quarterly ROI performance for the customer.",
                parse_mode="Markdown"
            )
            return
        
        contact_email = context.args[0]
        message = await handle_roi_report_callback(update, context, f"roi_report:{contact_email}:0")
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def cmd_roi_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Prepare ROI email for sending. Usage: /roi_email customer@email.com"""
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "Usage: `/roi_email customer@email.com`\n\n"
                "Generates email template ready to send.",
                parse_mode="Markdown"
            )
            return
        
        contact_email = context.args[0]
        rep_name = context.user_data.get('rep_name', 'Your Sales Rep')
        
        try:
            message = await send_roi_email_callback(update, context, contact_email, rep_name)
            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    # Register handlers
    application.add_handler(CommandHandler("roi_report", cmd_roi_report))
    application.add_handler(CommandHandler("roi_email", cmd_roi_email))
```

## Step 5: (Optional) Add ROI Summary to Main Menu

Find the main menu builder (around line 3200-3300).

Add a new menu option:
```python
    menu_text = """*🏠 MAIN MENU*

[Existing options...]

📊 *ROI & REPORTING*
Report quarterly performance to customers or check campaign metrics."""

    buttons = [
        # ... existing buttons ...
        [InlineKeyboardButton("📊 ROI Reports", callback_data="roi_menu")],
    ]
```

Then add a handler for the ROI menu:
```python
    elif query.data == "roi_menu":
        roi_menu_text = """📊 *QUARTERLY ROI REPORTS*

Generate professional ROI reports for customer contracts.

*Quick Actions:*
• `/roi_report customer@email.com` - View report
• `/roi_email customer@email.com` - Email template

*Features:*
✓ Coupon redemption tracking
✓ Revenue impact calculation
✓ Expansion opportunity analysis
✓ Pre-drafted emails ready to send
"""
        await query.edit_message_text(roi_menu_text, parse_mode="Markdown")
```

## Testing the Integration

After making changes, test with:

```bash
# Test direct command
/roi_report Dotcomvapor@gmail.com

# This should output the quarterly report for Felony Pizza

# Test email generation
/roi_email Dotcomvapor@gmail.com

# This should output the email template ready to send
```

## Data Flow Diagram

```
User clicks "📊 Generate Q ROI Report" button
    ↓
roi_report:email:store_num callback
    ↓
handle_roi_report_callback()
    ↓
Load contract from contracts.json
    ↓
generate_quarterly_roi_report()
    ↓
Check QuarterlyROITracker (prevent duplicates)
    ↓
format_roi_report_for_telegram()
    ↓
Send to user as alert popup
```

## Important Notes

1. **Coupon Data**: Currently uses placeholder `coupon_count=0`. You'll need to:
   - Connect to actual coupon redemption system
   - Load from database or metrics file
   - Parse quarterly aggregates

2. **Transaction Values**: `avg_transaction_value` also needs real data:
   - Connect to POS system
   - Or load from historical metrics
   - Calculate quarterly averages

3. **Tracker File**: ROI reports are tracked in `data/roi_report_tracker.json`
   - Prevents duplicate reports for same quarter
   - Created automatically on first use

4. **Telegram Limits**: Report text is limited to 4096 chars per message
   - `format_roi_report_for_telegram()` handles this
   - Longer reports can be sent as separate messages

## Example Output

When user presses the ROI button or runs `/roi_report`:

```
📊 QUARTERLY ROI REPORT

Felony Pizza
Store: 1704 | 2026-Q1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PERFORMANCE SUMMARY

✓ Coupons Redeemed: 38
✓ Gross Revenue: $1,729.00
✓ Gross Profit: $1,210.30
✓ ROI: -65.9%

🚀 STATUS: BETTER THAN FREE - Ad paid for itself!

EXPANSION OPPORTUNITY

EXCELLENT - READY FOR MULTI-LOCATION EXPANSION

Next Step: Schedule expansion discussion with your rep.

💡 To send via email:
/roi_email Dotcomvapor@gmail.com
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No contract found" | Check email spelling in contracts.json |
| "Invalid callback format" | Ensure button data includes email:store |
| "Already reported" | Check `data/roi_report_tracker.json` |
| Message too long | Use `/roi_email` to send formatted version |
| Import errors | Ensure `quarterly_roi_generator.py` is in same directory |

## File Checklist

Before deploying, verify these files exist:

- ✅ `/scripts/quarterly_roi_generator.py` - Core engine
- ✅ `/scripts/roi_telegram_integration.py` - Bot integration
- ✅ `/scripts/ROI_GENERATOR_README.md` - Full documentation
- ✅ `/data/contracts.json` - Customer contract data
- ✅ `/data/roi_report_tracker.json` - Auto-created on first use

## Questions?

See ROI_GENERATOR_README.md for full documentation and examples.
