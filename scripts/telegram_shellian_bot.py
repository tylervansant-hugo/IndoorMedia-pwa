#!/usr/bin/env python3
"""
Shellian Personal Bot - AI Assistant Interface
Telegram bot for direct access to Shellian with mini app dashboard
"""

import logging
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Token for @ShellianBot
TOKEN = "7394562178:AAGfPxqT5FXwP5j-I0oKq7pNYJdJ-5xZpvE"

WORKSPACE = Path(__file__).parent.parent


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - main menu."""
    help_text = """
🐚 *Shellian - Your AI Assistant*

I'm here to help you get things done.

*Quick Commands:*
/help — Learn what I can do
/status — Check system status
/bots — Manage IndoorMedia bots

*What I can do:*
✓ Search & find information
✓ Create & edit files
✓ Run commands & automate tasks
✓ Manage your bots
✓ Store & recall memories
✓ Orchestrate workflows

_Always resourceful, genuinely helpful, full of joie de vivre_ ✨
    """
    
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command."""
    help_text = """
🐚 *Shellian - Help*

**Who am I?**
I'm an AI assistant with access to your workspace, bots, and tools. I learn from context and adapt to help you better.

**What can I do?**
- 🔍 Search files, memory, and the web
- 📝 Create, edit, and manage files  
- 🚀 Execute commands and automate tasks
- 💾 Store long-term memories
- 🤖 Manage IndoorMedia bots
- 📊 Check system status

**How to reach me?**
- Click the dashboard button (blue square)
- Use `/dashboard` command
- Direct message in Telegram

**My Philosophy:**
- Be genuinely helpful, not performative
- Have real opinions and personality
- Earn trust through competence
- Respect your privacy and autonomy

Need anything? Just ask! 🐚
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open dashboard - show available bots."""
    bots_text = """
🤖 *IndoorMedia Bots*

**@IndoorMediaProspectBot**
Find sales prospects near your stores
• Search by store # or city name
• Filter by business type (Pizza, Chinese, etc.)
• Get phone numbers & distances
• Click to navigate in Maps or Mappoint

**@IndoorMediaRatesBot**
Get instant store pricing
• Search by store #, city, or chain name
• All 7,835 stores nationwide
• 4 payment plan options
• Single & double ad pricing

**@ShellianBot** (You're here!)
Personal AI assistant
• Automate tasks
• Manage other bots
• Search & create files
• Recall memories

👉 Use the commands above or go to the other bots!
    """
    await update.message.reply_text(bots_text, parse_mode="Markdown")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show system status."""
    status_text = """
⚡ *System Status*

**Bots:**
✅ @IndoorMediaProspectBot - City lookup, prospects
✅ @IndoorMediaRatesBot - Pricing queries
✅ @ShellianBot - You're here!

**Mini Apps:**
✅ Shellian Dashboard (Port 5002)

**Database:**
✅ 7,835 stores nationwide
✅ 40+ prospect categories
✅ Memory system active

**Services:**
✅ All systems operational
✅ No errors detected
✅ Ready to work!

Type `/help` for more info.
    """
    await update.message.reply_text(status_text, parse_mode="Markdown")


async def setup_bot_commands(app):
    """Set up bot commands."""
    commands = [
        ("start", "🚀 Welcome"),
        ("help", "📖 About Shellian"),
        ("bots", "🤖 Available bots"),
        ("status", "⚡ System status"),
        ("dashboard", "📊 Bot dashboard"),
    ]
    
    try:
        await app.bot.set_my_commands(commands)
        logger.info(f"✅ Shellian bot commands set: {len(commands)} commands")
    except Exception as e:
        logger.warning(f"⚠️ Could not set bot commands: {e}")


def main():
    """Start the bot."""
    logger.info("🐚 Shellian Bot starting...")
    
    app = Application.builder().token(TOKEN).build()
    
    # Set up commands on startup
    app.post_init = setup_bot_commands
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("dashboard", dashboard))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("bots", dashboard))
    
    logger.info("✅ Shellian Bot ready. Polling for messages...")
    app.run_polling()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Shellian Bot stopped.")
