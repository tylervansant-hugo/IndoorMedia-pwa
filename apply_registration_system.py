#!/usr/bin/env python3
"""
Script to apply registration & admin system to telegram_prospecting_bot.py

This script makes the following changes:
1. Replaces the start() function with registration gate version
2. Adds /admin command handler
3. Adds callback handlers for admin dashboard
4. Adds message handler for registration input
5. Imports the registration patch module

Run: python3 apply_registration_system.py
"""

import re
from pathlib import Path

WORKSPACE = Path(__file__).parent
BOT_FILE = WORKSPACE / "scripts" / "telegram_prospecting_bot.py"
PATCH_FILE = WORKSPACE / "registration_admin_patch.py"

def apply_registration_system():
    """Apply registration system changes to bot."""
    
    print("📝 Reading bot file...")
    with open(BOT_FILE, 'r') as f:
        bot_code = f.read()
    
    # Check if already applied
    if "start_with_registration_gate" in bot_code:
        print("⚠️  Registration system already applied!")
        return False
    
    # ========================================================================
    # 1. Add import for registration patch
    # ========================================================================
    print("✅ Step 1: Adding imports...")
    
    # Find the import section (after other telegram imports)
    import_pattern = r"(from telegram\.ext import.*?\n)"
    match = re.search(import_pattern, bot_code)
    if match:
        insert_pos = match.end()
        import_code = "\n# --- Registration & Admin System ---\ntry:\n    from registration_admin_patch import (\n        start_with_registration_gate,\n        admin_command,\n        handle_callback,\n        handle_registration_message,\n        AWAITING_USER_NAME,\n        AWAITING_USER_EMAIL,\n    )\n    REGISTRATION_SYSTEM_LOADED = True\nexcept ImportError as e:\n    logger.warning(f\"Registration system not available: {e}\")\n    REGISTRATION_SYSTEM_LOADED = False\n"
        bot_code = bot_code[:insert_pos] + import_code + bot_code[insert_pos:]
        print("   ✓ Imports added")
    
    # ========================================================================
    # 2. Replace the start() function
    # ========================================================================
    print("✅ Step 2: Replacing start() function...")
    
    # Find the start function
    start_pattern = r"async def start\(update: Update, context: ContextTypes\.DEFAULT_TYPE\):.*?(?=\nasync def )"
    match = re.search(start_pattern, bot_code, re.DOTALL)
    if match:
        new_start = '''async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command — registration gate, then show main menu."""
    if REGISTRATION_SYSTEM_LOADED:
        await start_with_registration_gate(update, context)
    else:
        logger.error("Registration system not loaded!")
        await update.effective_chat.send_message("❌ System error. Please try again later.")

'''
        bot_code = bot_code[:match.start()] + new_start + bot_code[match.end():]
        print("   ✓ start() function replaced")
    else:
        print("   ⚠️  Could not find start() function")
    
    # ========================================================================
    # 3. Find main() and add handlers
    # ========================================================================
    print("✅ Step 3: Adding handlers to main()...")
    
    main_pattern = r"def main\(\):.*?app\.run_polling\(\)"
    match = re.search(main_pattern, bot_code, re.DOTALL)
    if match:
        main_start = match.start()
        main_end = match.end()
        main_content = bot_code[main_start:main_end]
        
        # Check if handlers already exist
        if "admin_command" not in main_content:
            # Find the position to insert (before app.run_polling())
            insert_pattern = r"(\s+)app\.run_polling\(\)"
            insert_match = re.search(insert_pattern, main_content)
            if insert_match:
                indent = insert_match.group(1)
                insert_text = f'''{indent}# --- Registration & Admin Handlers ---
{indent}if REGISTRATION_SYSTEM_LOADED:
{indent}    app.add_handler(CommandHandler("admin", admin_command))
{indent}    app.add_handler(CallbackQueryHandler(handle_callback, pattern="^admin_"))
{indent}    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_registration_message), group=1)
{indent}
'''
                new_main_content = main_content.replace(insert_match.group(0), insert_text + insert_match.group(0))
                bot_code = bot_code[:main_start] + new_main_content + bot_code[main_end:]
                print("   ✓ Handlers added to main()")
            else:
                print("   ⚠️  Could not find app.run_polling() in main()")
        else:
            print("   ℹ️  Handlers already present")
    else:
        print("   ⚠️  Could not find main() function")
    
    # ========================================================================
    # 4. Save updated bot file
    # ========================================================================
    print("✅ Step 4: Saving updated bot file...")
    
    with open(BOT_FILE, 'w') as f:
        f.write(bot_code)
    
    print("   ✓ Bot file updated")
    
    return True

def verify_installation():
    """Verify that the registration system is properly installed."""
    print("\n📊 Verifying installation...")
    
    with open(BOT_FILE, 'r') as f:
        bot_code = f.read()
    
    checks = [
        ("Import statement", "from registration_admin_patch import"),
        ("start_with_registration_gate", "start_with_registration_gate"),
        ("admin_command", "admin_command"),
        ("handle_callback", "handle_callback"),
        ("admin command handler", 'CommandHandler("admin", admin_command)'),
    ]
    
    all_good = True
    for check_name, pattern in checks:
        if pattern in bot_code:
            print(f"   ✅ {check_name}")
        else:
            print(f"   ❌ {check_name} - NOT FOUND")
            all_good = False
    
    return all_good

if __name__ == "__main__":
    print("🚀 Installing Registration & Admin System")
    print("=" * 60)
    
    if apply_registration_system():
        print("\n✅ Installation complete!")
        if verify_installation():
            print("\n✅ All checks passed!")
            print("\nNext steps:")
            print("1. Test with a new user: /start")
            print("2. New user should see registration form")
            print("3. Try /admin as Tyler (ID: 8548368719)")
            print("4. See pending registrations and approve/reject")
        else:
            print("\n⚠️  Some verification checks failed")
            print("Please review the changes manually")
    else:
        print("\n❌ Installation failed or already complete")
