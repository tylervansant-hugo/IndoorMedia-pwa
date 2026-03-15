# Quarterly ROI Report Generator

Professional quarterly ROI report generation for IndoorMediaProspectBot customer contracts.

## Overview

This system generates professional, actionable quarterly ROI reports that show customers exactly how their advertising investment is performing. Reports include:

- **Performance Metrics**: Coupon redemptions, revenue impact, profit contribution
- **ROI Analysis**: Payback timeline, "better than free" metrics
- **Expansion Opportunities**: Data-driven recommendations for multi-location expansion
- **Email Templates**: Pre-formatted, ready-to-send emails with actionable pitches

## Files

### `quarterly_roi_generator.py`
Core report generation engine.

**Key Classes:**
- `QuarterlyROITracker` - Track which quarters have been reported (prevents duplicates)

**Key Functions:**
- `generate_quarterly_roi_report()` - Generate a complete quarterly ROI report
- `quarterly_roi_email_template()` - Format report as email template
- `create_audit_event_button_data()` - Generate Telegram button payload
- `load_contract_metrics()` - Load contract data from contracts.json

### `roi_telegram_integration.py`
Integration hooks for Telegram bot callback handlers.

**Key Functions:**
- `add_roi_button_to_audit_event()` - Add ROI button to audit timeline
- `handle_roi_report_callback()` - Process button clicks
- `format_roi_report_for_telegram()` - Telegram-friendly formatting
- `send_roi_email_callback()` - Prepare email for sending
- `batch_roi_notification()` - Notification for sales reps

### `data/roi_report_tracker.json`
Tracks which quarters have been reported for each customer. Format:
```json
{
  "reported_quarters": {
    "customer@email.com": ["2026-Q1", "2026-Q2"],
    "another@email.com": ["2026-Q1"]
  }
}
```

## Usage

### 1. Generate a Basic ROI Report

```python
from quarterly_roi_generator import generate_quarterly_roi_report

report = generate_quarterly_roi_report(
    business_name="Felony Pizza",
    contact_name="Travis McDonald",
    contact_email="Dotcomvapor@gmail.com",
    store_number="1704",
    start_date="2026-02-25",
    months_active=1,
    coupon_count=38,
    avg_transaction_value=45.50,
    cogs_percent=0.30,  # 30% cost of goods
    total_contract_amount=3545.04,
    store_name="Safeway",
)

# Access outputs
print(report["report_text"])  # Professional report
print(report["summary_stats"])  # JSON-serializable metrics
print(report["roi_metrics"])  # Detailed calculations
```

### 2. Format for Email Send

```python
from quarterly_roi_generator import quarterly_roi_email_template

email = quarterly_roi_email_template(
    business_name="Felony Pizza",
    contact_name="Travis McDonald",
    contact_email="Dotcomvapor@gmail.com",
    store_number="1704",
    rep_name="Tyler VanSant",
    report=report,  # From above
)

print(email)  # Copy/paste into email client
```

### 3. Create Telegram Button

```python
from quarterly_roi_generator import create_audit_event_button_data

button_data = create_audit_event_button_data(
    business_name="Felony Pizza",
    contact_name="Travis McDonald",
    contact_email="Dotcomvapor@gmail.com",
    store_number="1704",
    rep_name="Tyler VanSant",
)

print(button_data["callback_data"])  # "roi_report:Dotcomvapor@gmail.com:1704"
```

### 4. Track Reported Quarters

```python
from quarterly_roi_generator import QuarterlyROITracker

tracker = QuarterlyROITracker()

# Mark a quarter as reported
tracker.mark_reported("customer@email.com", "2026-Q1")

# Check if already reported
if tracker.is_reported("customer@email.com", "2026-Q1"):
    print("Already reported - skip")
else:
    print("Not yet reported - safe to generate")

# Get all reported quarters for a customer
quarters = tracker.get_reported_quarters("customer@email.com")
```

## Integration with Telegram Bot

### Add to Audit Event Buttons

In `telegram_prospecting_bot.py`, find where audit event buttons are created:

```python
# BEFORE (existing audit buttons)
buttons = [
    [InlineKeyboardButton("✅ Confirm", callback_data="audit_confirm_yes")],
    [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")],
]

# AFTER (with ROI button)
from roi_telegram_integration import add_roi_button_to_audit_event

buttons = [
    [InlineKeyboardButton("✅ Confirm", callback_data="audit_confirm_yes")],
    [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")],
]
buttons = add_roi_button_to_audit_event(buttons, contact_email, store_number)
```

### Add Callback Handler

Add to the main telegram bot's callback query handler:

```python
elif query.data.startswith("roi_report:"):
    from roi_telegram_integration import handle_roi_report_callback
    
    message_text = await handle_roi_report_callback(update, context, query.data)
    await query.answer(message_text, show_alert=True)
```

### Add Command Handlers

```python
from roi_telegram_integration import send_roi_email_callback

async def cmd_roi_email(update, context):
    """Generate ROI email for manual sending."""
    if not context.args:
        await update.message.reply_text("Usage: /roi_email contact@email.com")
        return
    
    contact_email = context.args[0]
    rep_name = context.user_data.get('rep_name', 'Your Rep')
    
    message = await send_roi_email_callback(update, context, contact_email, rep_name)
    await update.message.reply_text(message, parse_mode="Markdown")

# Register command
application.add_handler(CommandHandler("roi_email", cmd_roi_email))
```

## Key Metrics Explained

### "Better Than Free"
When the gross profit from coupon redemptions **exceeds** the contract cost.

Example:
- Contract cost: $3,545
- Coupons redeemed: 38
- Avg transaction: $45.50
- Gross revenue: $1,729 (38 × $45.50)
- COGS: $518.70 (30%)
- Gross profit: $1,210.30

**Result:** Not yet "better than free", but showing positive momentum with only 1 month active.

### Expansion Opportunity Tiers

| Coupons | Status | Pitch |
|---------|--------|-------|
| < 10 | GOOD | Monitor performance |
| 10-20 | VERY GOOD | Consider expansion after Q2 |
| 20-30 | EXCELLENT | Ready for 2-location expansion |
| 30+ | EXCELLENT - READY FOR EXPANSION | Multi-location scale immediately |

## Data Sources

### Contract Metrics
Load customer contracts from `data/contracts.json`:

```python
from quarterly_roi_generator import load_contract_metrics

contract = load_contract_metrics("customer@email.com")
# Returns: {business_name, contact_name, contact_email, store_number, total_amount, ...}
```

### Coupon Redemptions
**TODO:** Hook into actual coupon redemption system
- Expect metrics file: `data/coupon_metrics.json`
- Format: `{email: {quarter: {coupon_count: X, avg_value: Y, ...}}}`

### Transaction Data
**TODO:** Integrate with POS system
- Requires API/data feed from store POS
- Needed for accurate `avg_transaction_value`

## Testing

Run the example in the script directly:

```bash
python3 scripts/quarterly_roi_generator.py
```

Output includes:
- Sample quarterly report
- Summary statistics JSON
- Email template
- Telegram button data
- Tracker test

## Output Examples

### Report Text
```
QUARTERLY ROI PERFORMANCE REPORT
Felony Pizza | Travis McDonald
Store: Safeway (1704) | Quarter: 2026-Q1
Report Date: March 15, 2026

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXECUTIVE SUMMARY

In the 1 month since launching your IndoorMedia advertising campaign, 
here's what Felony Pizza achieved:

• 38 customers redeemed your in-store coupons
• $1,729.00 in gross revenue driven directly from ads
• $1,210.30 in gross profit (after COGS @ 30%)
• 📊 POSITIVE MOMENTUM — Ad spend already driving strong ROI
```

### Email Template
```
Subject: Your 2026-Q1 IndoorMedia Performance Report — Felony Pizza

Hi Travis,

Great news — your IndoorMedia advertising campaign is delivering results!

📊 QUARTER HIGHLIGHTS

  Coupons Redeemed:         38
  Gross Revenue Generated:  $1,729.00
  Gross Profit:             $1,210.30
  ROI Performance:          -65.9%

✅ The Bottom Line: Your advertising investment is driving positive 
return on investment.

🎯 EXPANSION OPPORTUNITY

With this level of performance, we think you're ready for the next step...
```

## Future Enhancements

1. **Live Coupon Data** - Hook into actual redemption system
2. **POS Integration** - Real transaction values from stores
3. **Trend Analysis** - Month-over-month growth tracking
4. **Batch Reports** - Generate all Q reports at quarter-end
5. **Email API** - Direct send via Gmail/Sendgrid
6. **Multi-Store Aggregation** - Combined reports for multi-location customers
7. **PDF Export** - Professional PDF reports for customer files
8. **Slack/Teams Integration** - Send reports to rep channels

## Support

For questions or updates:
- Check `/Users/tylervansant/.openclaw/workspace/memory/` for recent notes
- Reference MEMORY.md for context on IndoorMedia system
- See `telegram_prospecting_bot.py` for full integration examples
