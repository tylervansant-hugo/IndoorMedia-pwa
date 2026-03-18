# Counter Sign Generator - Setup & Integration Guide

## Installation

### 1. Install Dependencies

```bash
source /Users/tylervansant/.openclaw/workspace/.venv_bot/bin/activate
pip install PyPDF2 reportlab Pillow qrcode
```

### 2. Files Already Created

The following files have been created in the workspace:

```
scripts/
├── counter_sign_generator.py      ✅ Core PDF generation module
├── counter_sign_workflow.py       ✅ Telegram conversation handlers
├── counter_sign_integration.py    ✅ Bot integration functions
└── test_counter_sign.py          ✅ Test suite

data/
├── counter_sign_config.json       ✅ Configuration file
└── generated_signs/               ✅ Output directory created
    └── (PDFs will be stored here)
```

### 3. Verify Installation

```bash
cd /Users/tylervansant/.openclaw/workspace
source .venv_bot/bin/activate
python3 scripts/test_counter_sign.py
```

Expected output:
```
✅ All tests passed!
```

## Integration with Telegram Bot

### Step 1: Update `telegram_prospecting_bot.py`

Add the import at the top of the file (around line 30-50, with other imports):

```python
# Around line 40-50, with other imports
from counter_sign_integration import add_counter_sign_handlers_to_app
```

### Step 2: Add Handlers in main() Function

Find the `main()` function (currently around line 8094) and add the counter sign handlers:

```python
def main():
    """Start the bot."""
    logger.info("🎯 IndoorMediaProspectBot starting...")
    
    app = Application.builder().token(TOKEN).build()
    
    # Set up commands on startup
    app.post_init = setup_bot_commands
    
    # ✅ ADD THIS LINE:
    add_counter_sign_handlers_to_app(app)
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    # ... rest of existing handlers
```

### Step 3: Update Bot Commands Menu

Find the `setup_bot_commands()` function and add counter sign commands:

```python
async def setup_bot_commands(app):
    """Set up bot commands for Telegram menu."""
    commands = [
        ("start", "🚀 Start prospect search"),
        ("menu", "📂 Main menu"),
        ("rates", "💰 Store rates & pricing"),
        ("roi", "📊 ROI calculator"),
        ("keyword", "📋 Search testimonials"),
        ("countersign", "📋 Counter sign (direct team)"),        # ✅ ADD
        ("countersign_guided", "📋 Custom counter sign"),        # ✅ ADD
        ("help", "📖 How to use the bot"),
        ("examples", "📚 Example cities & stores"),
        ("city", "🏙️ Search by city"),
        # ... rest of commands
    ]
```

## Configuration

### Direct Team Member Data

The 9 direct team members are pre-configured in `data/counter_sign_config.json`:

- Adan Ramos
- Amy Dixon
- Ben Patacsil
- Christian Johnson
- Dave Boring
- Jan Banks
- Matt Boozer
- Megan Wink
- Marty Eng

Each has:
- Cell phone
- Corporate phone
- Email
- Landing page URL

### Store Templates

130 store templates are located in `data/store_templates/`:

```bash
ls /Users/tylervansant/.openclaw/workspace/data/store_templates/ | wc -l
# Output: 130
```

Each template is 8.5×11" and named with chain code (SAF, FME, ACM, etc.).

## Usage

### For Direct Team Members

In Telegram, type:
```
/countersign SAF
```

The bot will:
1. Check if you're registered as a direct team member
2. Ask for your ad image (JPG/PNG)
3. Pull your landing page from config
4. Generate QR code → landing page
5. Send PDF (ready to print)

### For Non-Direct Team Members

Type:
```
/countersign_guided
```

The bot will walk through:
1. Store chain selection (130+ chains)
2. Business card image upload
3. Landing page URL (or "none")
4. Your name
5. Your email
6. Your phone
7. Ad image upload
8. Generate & send PDF

## Testing Workflows

### Test 1: Direct Team Workflow

```bash
# Manually verify with test script
source .venv_bot/bin/activate
python3 scripts/test_counter_sign.py
```

### Test 2: PDF Quality Check

1. Generate a test counter sign (see test script)
2. Download: `/Users/tylervansant/.openclaw/workspace/data/generated_signs/Adan_Ramos/SAF/SAF_Adan_Ramos_*.pdf`
3. Open in Preview or PDF reader
4. Verify:
   - Header/footer from template is intact
   - Ad image is centered
   - Rep info is readable (bottom left)
   - QR code appears (bottom right) or "CALL NOW"
   - Overall dimensions are 8.5×11"

## File Locations

### Generated PDFs
```
data/generated_signs/
├── Adan_Ramos/
│   ├── SAF/
│   │   └── *.pdf
│   └── FME/
│       └── *.pdf
├── Amy_Dixon/...
└── [other reps]/
```

Each rep has a folder. Within that, each store chain gets its own folder. PDFs are named:
```
{CHAIN_CODE}_{STORE_NAME}_{REP_NAME}_{TIMESTAMP}.pdf
```

### Configuration Files
```
data/counter_sign_config.json     # Direct team data, layout settings
data/rep_registry.json            # Telegram user → rep mapping
```

### Source Code
```
scripts/counter_sign_generator.py    # Core PDF engine
scripts/counter_sign_workflow.py     # Telegram workflows
scripts/counter_sign_integration.py  # Bot integration
scripts/test_counter_sign.py        # Tests
```

## Troubleshooting Integration

### Bot doesn't recognize /countersign

**Check:**
1. Did you add the import? `from counter_sign_integration import add_counter_sign_handlers_to_app`
2. Did you add the handler? `add_counter_sign_handlers_to_app(app)` in `main()`
3. Did you restart the bot? (Kill and restart the process)
4. Is the command in the bot menu? Check `setup_bot_commands()`

### Command runs but errors with "module not found"

```bash
# Verify packages are installed in bot venv
source .venv_bot/bin/activate
python3 -c "import PyPDF2; import qrcode; import PIL; print('✅')"
```

If error, reinstall:
```bash
pip install PyPDF2 reportlab Pillow qrcode
```

### Telegram user not recognized as direct team member

1. Check their user ID is in `data/rep_registry.json`:
   ```bash
   grep "user_id_here" data/rep_registry.json
   ```

2. Check their contract name matches DIRECT_TEAM:
   ```bash
   cat data/counter_sign_config.json | grep "Adan Ramos"
   ```

3. Have them use `/countersign_guided` instead

### PDF generation fails with image

**Check:**
1. Is the image JPG or PNG? (GIF, WebP not supported)
2. Is the image file valid? (Try opening in Preview)
3. Is the file smaller than 5MB?
4. Are there any special characters in filename?

## Production Deployment

### Pre-Launch Checklist

- [ ] Dependencies installed in .venv_bot
- [ ] Test suite passes: `python3 test_counter_sign.py`
- [ ] Integration code added to telegram_prospecting_bot.py
- [ ] Bot restarted
- [ ] Test /countersign command with direct team rep
- [ ] Test /countersign_guided with custom workflow
- [ ] Verify PDFs save to correct directory
- [ ] Test with real ad image (not test image)
- [ ] Check PDF quality (open in viewer)
- [ ] Verify QR code scans correctly

### Monitoring

Check logs for errors:
```bash
tail -f logs/telegram_bot.log | grep -i "counter\|error"
```

Monitor generated signs directory:
```bash
watch "ls -lrt data/generated_signs/*/* | tail -5"
```

## Updating Direct Team Data

To add or update a direct team member:

1. Edit `data/counter_sign_config.json`
2. Add/update entry in `direct_team` section:
   ```json
   {
     "New Rep Name": {
       "cell": "206.555.1234",
       "corporate": "800.247.4793",
       "email": "name@indoormedia.com",
       "landing_page": "https://www.indoormedia.com/tape-sales/advertise-with-[name]/"
     }
   }
   ```
3. Also update in `scripts/counter_sign_generator.py` DIRECT_TEAM dict for consistency
4. Add Telegram user to `data/rep_registry.json`
5. Bot will use new data on next command

## Support & Maintenance

### Regular Tasks

**Weekly:**
- Monitor generated signs directory size
- Check for errors in logs

**Monthly:**
- Review generated PDFs for quality
- Update direct team data if needed

**As Needed:**
- Add new store templates to `data/store_templates/`
- Update rep landing pages in config
- Troubleshoot user issues

### Getting Help

1. **Check README:** `COUNTER_SIGN_README.md`
2. **Run tests:** `python3 scripts/test_counter_sign.py`
3. **Review logs:** Check bot logs for error messages
4. **Contact Tyler:** tyler.vansant@indoormedia.com

## Uninstalling

To remove the counter sign system:

1. Remove integration from `telegram_prospecting_bot.py`:
   - Delete the import line
   - Delete the `add_counter_sign_handlers_to_app(app)` line

2. Optional: Remove files (if disk space needed):
   ```bash
   rm -rf scripts/counter_sign_*.py
   rm -f data/counter_sign_config.json
   rm -rf data/generated_signs/
   ```

3. No dependency conflicts - other parts of bot unaffected

---

## Quick Reference

```bash
# Activate bot environment
source /Users/tylervansant/.openclaw/workspace/.venv_bot/bin/activate

# Run tests
python3 /Users/tylervansant/.openclaw/workspace/scripts/test_counter_sign.py

# View generated PDFs
ls /Users/tylervansant/.openclaw/workspace/data/generated_signs/

# Check bot logs
tail -f /Users/tylervansant/.openclaw/workspace/logs/telegram_bot.log

# Edit direct team data
nano /Users/tylervansant/.openclaw/workspace/data/counter_sign_config.json
```

---

**Status:** ✅ Ready for Deployment
**Last Updated:** March 18, 2026
**Version:** 1.0
