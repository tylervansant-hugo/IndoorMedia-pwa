# 🚀 Integration Guide: Advertising Signals into ProspectBot

This guide shows exactly how to integrate the advertising signals detector into `telegram_prospecting_bot.py`.

## Step 1: Import the Integration Module

Add these imports at the top of `telegram_prospecting_bot.py` (around line 30-40):

```python
# Advertising signals integration
try:
    from prospect_advertising_integration import add_advertising_signals_to_prospect
    from telegram_bot_ad_signals_patch import register_ad_signals_handlers
    SIGNALS_AVAILABLE = True
except ImportError:
    SIGNALS_AVAILABLE = False
    logger.warning("⚠️ Advertising signals module not available")
```

## Step 2: Register Callbacks with Bot

In the main function or wherever you set up handlers (usually around line 2000+), add:

```python
async def main():
    """Start the bot."""
    application = Application.builder().token(TOKEN).build()
    
    # ... existing handlers ...
    
    # Register advertising signals handlers
    if SIGNALS_AVAILABLE:
        register_ad_signals_handlers(application)
        logger.info("✅ Advertising signals handlers registered")
    
    # ... rest of setup ...
```

## Step 3: Modify `send_prospects_with_full_info()` Function

Find this function (around line 2485) and modify it to add signals:

### Add signal enrichment at the start of the loop:

```python
async def send_prospects_with_full_info(update: Update, prospects: List[Dict], store: Dict, context: ContextTypes.DEFAULT_TYPE = None):
    """Send each prospect once with full info + buttons in one message."""
    
    for i, prospect in enumerate(prospects, 1):
        # ADD THIS: Enrich prospect with advertising signals
        if SIGNALS_AVAILABLE:
            try:
                prospect = add_advertising_signals_to_prospect(prospect, force_refresh=False)
            except Exception as e:
                logger.warning(f"Error adding ad signals: {e}")
        
        # ... rest of existing code ...
```

### Add signals display after website section:

Find this section in `send_prospects_with_full_info()`:

```python
        # Website link
        if website:
            web_url = website if website.startswith("http") else f"https://{website}"
            text += f"🌐 [Website]({web_url})\n"
```

Add after it:

```python
        # Advertising signals (NEW!)
        ad_signals = prospect.get('advertising_signals', {})
        if ad_signals and ad_signals.get('found_advertising'):
            text += "\n🎬 *ADVERTISING SIGNALS*\n"
            platforms = ad_signals.get('platforms', {})
            
            if platforms.get('meta', {}).get('found'):
                text += "  • 📘 *Meta Ads Library* — Active ads detected\n"
            if platforms.get('google', {}).get('found'):
                text += "  • 🔍 *Google Ads Library* — Active ads detected\n"
            
            boost = ad_signals.get('likelihood_boost', 0)
            if boost > 0:
                text += f"\n✨ *+{boost} Likelihood Boost*\n"
                text += "_(This business is already advertising online — good prospect!)_\n"
```

### Add refresh button to buttons list:

Find the buttons section that has "Show Actions":

```python
        # Expand for more actions
        buttons.append([
            InlineKeyboardButton("▶️ Show Actions", callback_data=f"expand_{prospect_id}"),
        ])
```

Modify to:

```python
        # Expand for more actions + refresh signals
        buttons.append([
            InlineKeyboardButton("▶️ Show Actions", callback_data=f"expand_{prospect_id}"),
            InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_signals_{prospect_id}"),
        ])
```

### Store ad signals in context:

Find where prospect data is stored in context (around line 2580):

```python
        # Store prospect info for callback handlers
        if context:
            if 'prospects' not in context.user_data:
                context.user_data['prospects'] = {}
            context.user_data['prospects'][prospect_id] = {
                'name': business_name,
                'address': address,
                # ... other fields ...
            }
```

Add this field to the dict:

```python
                'advertising_signals': ad_signals,  # NEW!
```

## Step 4: Verify Integration

Test that everything works:

```bash
# 1. Run tests
python3 scripts/test_advertising_signals.py

# 2. Test direct module
python3 scripts/advertising_signals.py "Test Business Name"

# 3. Check cache was created
ls -la data/advertising_signals_cache.json
```

Expected output:
```
✅ Advertising signals handlers registered
✅ Signals module working
Cache file created at data/advertising_signals_cache.json
```

## Step 5: Optional - Custom Likelihood Score Boost

If you want to adjust the +15 boost amount, edit `advertising_signals.py`:

```python
# Around line 150, in AdvertisingSignalsDetector.check_business():
# Change this:
if meta_result.get("found"):
    results["found_advertising"] = True
    results["likelihood_boost"] += 15  # ← Change this number

# To something like:
    results["likelihood_boost"] += 20  # +20 instead of +15
```

## Complete Example

Here's a minimal example of the integrated function:

```python
async def send_prospects_with_full_info(update: Update, prospects: List[Dict], store: Dict, context: ContextTypes.DEFAULT_TYPE = None):
    """Send each prospect once with full info + buttons in one message."""
    
    for i, prospect in enumerate(prospects, 1):
        # Enrich with advertising signals
        if SIGNALS_AVAILABLE:
            try:
                prospect = add_advertising_signals_to_prospect(prospect, force_refresh=False)
            except Exception as e:
                logger.warning(f"Error adding signals: {e}")
        
        # Extract prospect info
        business_name = prospect.get("name", "Unknown")
        address = prospect.get("address", "")
        phone = prospect.get("phone", "")
        score = prospect.get('likelihood_score', 0)
        website = prospect.get("website", "")
        
        # Build message
        text = f"🔥 *{business_name}*\n"
        text += f"📊 Likelihood: {score}/100\n"
        text += f"📞 {phone}\n"
        text += f"📍 {address}\n"
        
        # Add advertising signals
        ad_signals = prospect.get('advertising_signals', {})
        if ad_signals and ad_signals.get('found_advertising'):
            text += "\n🎬 *ADVERTISING SIGNALS*\n"
            platforms = ad_signals.get('platforms', {})
            if platforms.get('meta', {}).get('found'):
                text += "  • 📘 Meta: Active ads detected\n"
            if platforms.get('google', {}).get('found'):
                text += "  • 🔍 Google: Active ads detected\n"
            boost = ad_signals.get('likelihood_boost', 0)
            if boost > 0:
                text += f"\n✨ *+{boost} score boost* — Already advertising online!\n"
        
        # Buttons with refresh option
        buttons = [
            [InlineKeyboardButton("📍 Maps", url=google_maps_url)],
            [
                InlineKeyboardButton("▶️ Show Actions", callback_data=f"expand_{prospect_id}"),
                InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_signals_{prospect_id}"),
            ],
        ]
        
        # Store in context
        if context:
            if 'prospects' not in context.user_data:
                context.user_data['prospects'] = {}
            context.user_data['prospects'][prospect_id] = {
                'name': business_name,
                'address': address,
                'phone': phone,
                'likelihood_score': score,
                'advertising_signals': ad_signals,
                # ... other fields ...
            }
        
        await update.effective_chat.send_message(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
```

## Testing in Telegram

Once integrated, test by:

1. Send `/start` to bot
2. Search for prospects
3. See prospect cards with signals
4. Look for 🎬 **ADVERTISING SIGNALS** section
5. Click 🔄 **Refresh** button to manually check

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "advertising signals not available" warning | Make sure all 3 files are in `scripts/` directory |
| Signals not showing on cards | Check that `add_advertising_signals_to_prospect()` is being called |
| Cache not being used | Check file permissions on `data/` directory |
| Refresh button not working | Make sure `register_ad_signals_handlers()` was called during bot setup |
| Timeout errors | Increase timeout in `advertising_signals.py` (currently 8 seconds) |

## Performance Impact

- **First lookup**: +1-2 seconds (network request)
- **Cached lookup**: <0.1 seconds (disk read)
- **UI delay**: Negligible (happens before message sent)
- **Memory**: ~50KB per 100 cached businesses

## Deployment

When ready to deploy:

1. Test locally with test suite
2. Add files to production server
3. Restart bot process
4. Monitor logs for "advertising signals handlers registered"
5. Test with real prospects in production

## Quick Reference

| File | Purpose |
|------|---------|
| `advertising_signals.py` | Core detector (Meta/Google checks) |
| `prospect_advertising_integration.py` | Integration layer (adds signals to prospects) |
| `telegram_bot_ad_signals_patch.py` | Telegram callbacks (refresh button) |
| `test_advertising_signals.py` | Test suite |
| `data/advertising_signals_cache.json` | 24h cache storage |

## That's It!

Once integrated:
- ✅ Advertising signals appear automatically on prospect cards
- ✅ Likelihood scores are boosted if ads found (+15)
- ✅ Users can click "🔄 Refresh" to manually check
- ✅ Results are cached for 24 hours (fast lookups)

---

**Questions?** Check the comprehensive guide at `AD_SIGNALS_README.md`
