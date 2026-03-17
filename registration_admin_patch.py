"""
Registration & Admin System Patch for IndoorMediaProspectBot

This patch adds:
1. User registration flow for new users
2. Pending registrations queue with approval system
3. Admin dashboard for Tyler (only)
4. Access control gate on /start
5. Status tracking in prospect_data.json

Installation:
  1. Replace the start() function with the patched version
  2. Add the new functions to the bot
  3. Register callbacks in main()
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Find workspace root
_current_file = Path(__file__)
if _current_file.name == "registration_admin_patch.py":
    # Running from workspace root
    WORKSPACE = _current_file.parent
else:
    # Running from scripts directory
    WORKSPACE = _current_file.parent.parent

PENDING_REGISTRATIONS_FILE = WORKSPACE / "data" / "pending_registrations.json"
PROSPECT_DATA_FILE = WORKSPACE / "data" / "prospect_data.json"
REP_REGISTRY_FILE = WORKSPACE / "data" / "rep_registry.json"

TYLER_TELEGRAM_ID = "8548368719"

# ============================================================================
# PENDING REGISTRATIONS MANAGEMENT
# ============================================================================

def load_pending_registrations():
    """Load all pending registrations (pending/approved/rejected)."""
    if PENDING_REGISTRATIONS_FILE.exists():
        with open(PENDING_REGISTRATIONS_FILE) as f:
            return json.load(f)
    return []

def save_pending_registrations(registrations):
    """Save pending registrations."""
    with open(PENDING_REGISTRATIONS_FILE, 'w') as f:
        json.dump(registrations, f, indent=2)

def add_pending_registration(telegram_id: str, name: str, email: str, account_email: str = None, email_permission: bool = False):
    """Add a new pending registration."""
    registrations = load_pending_registrations()
    
    account_email = account_email or email
    
    # Check if already exists
    for reg in registrations:
        if reg['telegram_id'] == str(telegram_id):
            # Update existing
            reg['name'] = name
            reg['email'] = email
            reg['account_email'] = account_email
            reg['email_permission'] = email_permission
            if email_permission:
                reg['permission_granted_at'] = datetime.now(timezone.utc).isoformat()
            reg['status'] = 'pending'
            reg['timestamp'] = datetime.now(timezone.utc).isoformat()
            save_pending_registrations(registrations)
            return reg['id']
    
    # Create new
    reg_id = f"reg_{len(registrations) + 1:03d}"
    registrations.append({
        'id': reg_id,
        'telegram_id': str(telegram_id),
        'name': name,
        'email': email,
        'account_email': account_email,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'status': 'pending',
        'email_permission': email_permission,
        'permission_granted_at': datetime.now(timezone.utc).isoformat() if email_permission else None,
    })
    save_pending_registrations(registrations)
    return reg_id

def get_registration_by_id(reg_id: str):
    """Get a specific registration by ID."""
    registrations = load_pending_registrations()
    for reg in registrations:
        if reg['id'] == reg_id:
            return reg
    return None

def get_registration_by_telegram_id(telegram_id: str):
    """Get a registration by Telegram ID."""
    registrations = load_pending_registrations()
    for reg in registrations:
        if reg['telegram_id'] == str(telegram_id):
            return reg
    return None

def update_registration_status(reg_id: str, status: str):
    """Update registration status (approved/rejected)."""
    registrations = load_pending_registrations()
    for reg in registrations:
        if reg['id'] == reg_id:
            reg['status'] = status
            save_pending_registrations(registrations)
            return True
    return False

# ============================================================================
# REP REGISTRY & ACCESS CONTROL
# ============================================================================

def load_rep_registry():
    """Load the rep registry."""
    if REP_REGISTRY_FILE.exists():
        with open(REP_REGISTRY_FILE) as f:
            return json.load(f)
    return {}

def save_rep_registry(registry):
    """Save the rep registry."""
    with open(REP_REGISTRY_FILE, 'w') as f:
        json.dump(registry, f, indent=2)

def is_rep_registered(telegram_id: str) -> bool:
    """Check if rep is registered in rep_registry."""
    registry = load_rep_registry()
    return str(telegram_id) in registry

def approve_registration(reg_id: str):
    """Approve a pending registration and add to rep_registry."""
    reg = get_registration_by_id(reg_id)
    if not reg:
        return False
    
    telegram_id = reg['telegram_id']
    
    # Update status
    update_registration_status(reg_id, 'approved')
    
    # Add to rep_registry if not already there
    registry = load_rep_registry()
    if str(telegram_id) not in registry:
        registry[str(telegram_id)] = {
            'telegram_name': reg['name'],
            'contract_name': reg['name'],
            'email': reg.get('email', ''),
            'account_email': reg.get('account_email', reg.get('email', '')),
            'email_permission': reg.get('email_permission', False),
            'role': 'rep',
            'registered_at': datetime.now().isoformat(),
        }
        save_rep_registry(registry)
    else:
        # Update existing registry entry with new fields
        registry[str(telegram_id)]['account_email'] = reg.get('account_email', reg.get('email', ''))
        registry[str(telegram_id)]['email_permission'] = reg.get('email_permission', False)
        save_rep_registry(registry)
    
    # Update prospect_data with status and email_permission
    _update_rep_status_in_prospect_data(str(telegram_id), 'approved', reg.get('email_permission', False))
    
    return True

def reject_registration(reg_id: str):
    """Reject a pending registration."""
    reg = get_registration_by_id(reg_id)
    if not reg:
        return False
    
    telegram_id = reg['telegram_id']
    
    # Update status
    update_registration_status(reg_id, 'rejected')
    
    # Update prospect_data with status
    _update_rep_status_in_prospect_data(str(telegram_id), 'rejected')
    
    return True

def get_rep_status(telegram_id: str) -> str:
    """Get rep status: 'approved', 'pending', 'rejected', or 'not_registered'.
    
    Check pending_registrations.json first for truth — even if in rep_registry,
    if rejected there, user is rejected.
    """
    # Check pending registrations first (source of truth)
    reg = get_registration_by_telegram_id(telegram_id)
    if reg:
        return reg['status']  # 'pending', 'approved', or 'rejected'
    
    # If not in pending_registrations, check rep_registry (old system)
    if is_rep_registered(telegram_id):
        return 'approved'
    
    return 'not_registered'

# ============================================================================
# PROSPECT DATA HELPER
# ============================================================================

def _load_prospect_data():
    """Load prospect_data.json."""
    if PROSPECT_DATA_FILE.exists():
        with open(PROSPECT_DATA_FILE) as f:
            return json.load(f)
    return {'reps': {}, 'global_searches': []}

def _save_prospect_data(data):
    """Save prospect_data.json."""
    with open(PROSPECT_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def _update_rep_status_in_prospect_data(telegram_id: str, status: str, email_permission: bool = None):
    """Update a rep's status and email_permission in prospect_data."""
    data = _load_prospect_data()
    if str(telegram_id) not in data['reps']:
        data['reps'][str(telegram_id)] = {}
    data['reps'][str(telegram_id)]['status'] = status
    if email_permission is not None:
        data['reps'][str(telegram_id)]['email_permission'] = email_permission
    _save_prospect_data(data)

# ============================================================================
# REGISTRATION FLOW FUNCTIONS
# ============================================================================

AWAITING_USER_NAME = 'awaiting_user_name'
AWAITING_USER_EMAIL = 'awaiting_user_email'
AWAITING_ACCOUNT_EMAIL = 'awaiting_account_email'
AWAITING_EMAIL_PERMISSION = 'awaiting_email_permission'

async def start_registration_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the registration flow for new users."""
    context.user_data[AWAITING_USER_NAME] = True
    
    await update.effective_chat.send_message(
        "👋 *Welcome to IndoorMediaProspectBot!*\n\n"
        "You're new here. Let's get you set up.\n\n"
        "**What's your name?**",
        parse_mode="Markdown"
    )

async def handle_registration_name(update: Update, context: ContextTypes.DEFAULT_TYPE, name: str):
    """Handle name input during registration."""
    context.user_data[AWAITING_USER_NAME] = False
    context.user_data['new_user_name'] = name
    context.user_data[AWAITING_USER_EMAIL] = True
    
    await update.effective_chat.send_message(
        f"✅ Thanks, {name}!\n\n"
        "**What's your contact email address?**",
        parse_mode="Markdown"
    )

async def handle_registration_email(update: Update, context: ContextTypes.DEFAULT_TYPE, email: str):
    """Handle email input and ask for account email."""
    context.user_data[AWAITING_USER_EMAIL] = False
    context.user_data['new_user_email'] = email
    context.user_data[AWAITING_ACCOUNT_EMAIL] = True
    
    await update.effective_chat.send_message(
        f"✅ Got it!\n\n"
        f"**What's your IndoorMedia account email?** (for scanning contracts)",
        parse_mode="Markdown"
    )

async def handle_registration_account_email(update: Update, context: ContextTypes.DEFAULT_TYPE, account_email: str):
    """Handle account email and ask for email permission."""
    context.user_data[AWAITING_ACCOUNT_EMAIL] = False
    context.user_data['new_user_account_email'] = account_email
    context.user_data[AWAITING_EMAIL_PERMISSION] = True
    
    # Ask for permission to scan emails
    buttons = [
        [InlineKeyboardButton("✅ Grant Permission", callback_data="email_perm_grant")],
        [InlineKeyboardButton("❌ Skip for Now", callback_data="email_perm_skip")],
    ]
    
    await update.effective_chat.send_message(
        f"📧 **Email Permission Request**\n\n"
        f"I need permission to scan your email for 'IndoorMedia Contract Signed' emails.\n\n"
        f"This allows you to:\n"
        f"• Track when contracts are signed\n"
        f"• Automatically create calendar events\n"
        f"• Access contract processing workflows\n"
        f"• Approve/manage contracts like the direct team\n\n"
        f"Grant permission?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def handle_email_permission_response(update: Update, context: ContextTypes.DEFAULT_TYPE, granted: bool):
    """Handle email permission choice and submit registration."""
    query = update.callback_query
    await query.answer()
    
    context.user_data[AWAITING_EMAIL_PERMISSION] = False
    
    telegram_id = str(update.effective_user.id)
    name = context.user_data.get('new_user_name', 'Unknown')
    email = context.user_data.get('new_user_email', '')
    account_email = context.user_data.get('new_user_account_email', email)
    
    # Add to pending registrations with email_permission flag
    registrations = load_pending_registrations()
    
    # Check if already exists
    for reg in registrations:
        if reg['telegram_id'] == str(telegram_id):
            reg['name'] = name
            reg['email'] = email
            reg['account_email'] = account_email
            reg['email_permission'] = granted
            if granted:
                reg['permission_granted_at'] = datetime.now(timezone.utc).isoformat()
            reg['status'] = 'pending'
            reg['timestamp'] = datetime.now(timezone.utc).isoformat()
            save_pending_registrations(registrations)
            reg_id = reg['id']
            break
    else:
        # Create new registration
        reg_id = f"reg_{len(registrations) + 1:03d}"
        registrations.append({
            'id': reg_id,
            'telegram_id': str(telegram_id),
            'name': name,
            'email': email,
            'account_email': account_email,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'pending',
            'email_permission': granted,
            'permission_granted_at': datetime.now(timezone.utc).isoformat() if granted else None,
        })
        save_pending_registrations(registrations)
    
    permission_status = "✅ Permission granted!" if granted else "⏭️ Permission skipped (can request later)"
    
    await query.edit_message_text(
        f"✅ **Registration Submitted!**\n\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Account Email: {account_email}\n"
        f"Email Permission: {permission_status}\n\n"
        f"⏳ *Awaiting approval from Tyler.*\n"
        f"You'll be notified when your registration is approved.",
        parse_mode="Markdown"
    )
    
    # Clean up
    context.user_data.pop('new_user_name', None)
    context.user_data.pop('new_user_email', None)
    context.user_data.pop('new_user_account_email', None)
    context.user_data.pop(AWAITING_USER_NAME, None)
    context.user_data.pop(AWAITING_USER_EMAIL, None)
    context.user_data.pop(AWAITING_ACCOUNT_EMAIL, None)
    context.user_data.pop(AWAITING_EMAIL_PERMISSION, None)

# ============================================================================
# ADMIN DASHBOARD FUNCTIONS
# ============================================================================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command — only for Tyler."""
    telegram_id = str(update.effective_user.id)
    
    # Check if user is Tyler
    if telegram_id != TYLER_TELEGRAM_ID:
        await update.effective_chat.send_message(
            "❌ **Access Denied**\n\n"
            "The admin panel is only available to Tyler.",
            parse_mode="Markdown"
        )
        return
    
    # Show admin dashboard
    await show_admin_dashboard(update, context)

async def show_admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the admin dashboard with pending registrations."""
    registrations = load_pending_registrations()
    pending = [r for r in registrations if r['status'] == 'pending']
    approved = [r for r in registrations if r['status'] == 'approved']
    rejected = [r for r in registrations if r['status'] == 'rejected']
    
    # Build message
    msg = f"🛡️ **ADMIN DASHBOARD**\n\n"
    msg += f"📊 **Stats:**\n"
    msg += f"• Pending: {len(pending)}\n"
    msg += f"• Approved: {len(approved)}\n"
    msg += f"• Rejected: {len(rejected)}\n\n"
    
    if pending:
        msg += f"⏳ **PENDING APPROVALS** ({len(pending)}):\n\n"
        for i, reg in enumerate(pending, 1):
            timestamp = reg.get('timestamp', '').split('T')[0]
            msg += f"{i}. {reg['name']} | {reg['email']}\n"
            msg += f"   ID: {reg['telegram_id']} | {timestamp}\n\n"
    else:
        msg += "✅ No pending registrations!\n\n"
    
    # Buttons
    buttons = []
    if pending:
        buttons.append([InlineKeyboardButton("📋 Review Pending", callback_data="admin_review_pending")])
    buttons.append([InlineKeyboardButton("👥 View Approved Users", callback_data="admin_view_approved")])
    buttons.append([InlineKeyboardButton("⛔ Deactivate User", callback_data="admin_deactivate")])
    
    keyboard = InlineKeyboardMarkup(buttons)
    
    if isinstance(update, Update) and update.callback_query:
        await update.callback_query.edit_message_text(msg, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await update.effective_chat.send_message(msg, parse_mode="Markdown", reply_markup=keyboard)

async def show_pending_registrations_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of pending registrations with approve/reject buttons."""
    query = update.callback_query
    await query.answer()
    
    registrations = load_pending_registrations()
    pending = [r for r in registrations if r['status'] == 'pending']
    
    if not pending:
        await query.edit_message_text(
            "✅ **No Pending Registrations**\n\n"
            "All registrations have been reviewed!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin_dashboard")]])
        )
        return
    
    # Show first pending registration
    context.user_data['admin_pending_idx'] = 0
    await _show_pending_registration_detail(query, context)

async def _show_pending_registration_detail(query, context: ContextTypes.DEFAULT_TYPE):
    """Show a single pending registration with approve/reject buttons."""
    registrations = load_pending_registrations()
    pending = [r for r in registrations if r['status'] == 'pending']
    
    idx = context.user_data.get('admin_pending_idx', 0)
    if idx >= len(pending):
        idx = len(pending) - 1
        context.user_data['admin_pending_idx'] = idx
    
    if not pending:
        await query.edit_message_text(
            "✅ **All registrations reviewed!**",
            parse_mode="Markdown"
        )
        return
    
    reg = pending[idx]
    timestamp = reg.get('timestamp', '').split('T')[0]
    
    msg = (f"📋 **PENDING REGISTRATION** ({idx + 1}/{len(pending)})\n\n"
           f"👤 **Name:** {reg['name']}\n"
           f"📧 **Email:** {reg['email']}\n"
           f"🆔 **Telegram ID:** {reg['telegram_id']}\n"
           f"📅 **Submitted:** {timestamp}\n\n"
           f"✅ Approve or ❌ Reject?")
    
    buttons = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_{reg['id']}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_{reg['id']}"),
        ],
        [InlineKeyboardButton("⏭️ Next", callback_data="admin_next_pending")],
        [InlineKeyboardButton("⬅️ Back to Dashboard", callback_data="admin_dashboard")],
    ]
    
    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE, reg_id: str):
    """Approve a pending registration."""
    query = update.callback_query
    await query.answer()
    
    if approve_registration(reg_id):
        reg = get_registration_by_id(reg_id)
        if reg:
            await query.edit_message_text(
                f"✅ **APPROVED**\n\n"
                f"User: {reg['name']}\n"
                f"Email: {reg['email']}\n\n"
                f"They can now use the bot!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📋 Next Pending", callback_data="admin_next_pending"),
                    InlineKeyboardButton("⬅️ Dashboard", callback_data="admin_dashboard"),
                ]])
            )
    else:
        await query.answer("❌ Failed to approve", show_alert=True)

async def handle_admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE, reg_id: str):
    """Reject a pending registration."""
    query = update.callback_query
    await query.answer()
    
    if reject_registration(reg_id):
        reg = get_registration_by_id(reg_id)
        if reg:
            await query.edit_message_text(
                f"❌ **REJECTED**\n\n"
                f"User: {reg['name']}\n"
                f"Email: {reg['email']}\n\n"
                f"They will see a rejection message.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📋 Next Pending", callback_data="admin_next_pending"),
                    InlineKeyboardButton("⬅️ Dashboard", callback_data="admin_dashboard"),
                ]])
            )
    else:
        await query.answer("❌ Failed to reject", show_alert=True)

async def handle_admin_next_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Move to next pending registration."""
    query = update.callback_query
    await query.answer()
    
    idx = context.user_data.get('admin_pending_idx', 0)
    context.user_data['admin_pending_idx'] = idx + 1
    
    await _show_pending_registration_detail(query, context)

async def show_approved_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of approved users with deactivate option."""
    query = update.callback_query
    await query.answer()
    
    registrations = load_pending_registrations()
    approved = [r for r in registrations if r['status'] == 'approved']
    
    if not approved:
        await query.edit_message_text(
            "❌ **No Approved Users Yet**",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin_dashboard")]])
        )
        return
    
    msg = f"👥 **APPROVED USERS** ({len(approved)})\n\n"
    buttons = []
    for i, reg in enumerate(approved, 1):
        msg += f"{i}. {reg['name']} ({reg['email']})\n"
        buttons.append([InlineKeyboardButton(f"⛔ Deactivate: {reg['name']}", callback_data=f"admin_deactivate_user_{reg['id']}")])
    
    buttons.append([InlineKeyboardButton("⬅️ Back to Dashboard", callback_data="admin_dashboard")])
    
    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_admin_deactivate(update: Update, context: ContextTypes.DEFAULT_TYPE, reg_id: str):
    """Deactivate (reject) an approved user."""
    query = update.callback_query
    await query.answer()
    
    # Change status back to rejected
    update_registration_status(reg_id, 'rejected')
    
    reg = get_registration_by_id(reg_id)
    if reg:
        # Update rep status
        _update_rep_status_in_prospect_data(reg['telegram_id'], 'rejected')
        
        await query.edit_message_text(
            f"⛔ **DEACTIVATED**\n\n"
            f"User: {reg['name']}\n"
            f"They can no longer use the bot.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Dashboard", callback_data="admin_dashboard")]])
        )

# ============================================================================
# ACCESS CONTROL GATE (Modified /start)
# ============================================================================

async def start_with_registration_gate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Modified /start that checks registration status before showing main menu.
    
    Flow:
    1. Approved → Show main menu
    2. Pending → Show "awaiting approval" message
    3. Rejected → Show "registration rejected" message
    4. New → Start registration flow
    """
    telegram_id = str(update.effective_user.id)
    rep_name = update.effective_user.first_name or "User"
    
    status = get_rep_status(telegram_id)
    
    if status == 'approved':
        # Approved — show main menu (original /start behavior)
        # Initialize/register rep in prospect data
        rep_data = _load_prospect_data()
        if telegram_id not in rep_data['reps']:
            rep_data['reps'][telegram_id] = {
                'name': rep_name,
                'status': 'approved',
                'saved_prospects': {},
                'search_history': [],
                'contact_history': {},
                'session_searches': 0,
                'session_bookmarks': 0,
            }
        _save_prospect_data(rep_data)
        
        # Show welcome
        await update.effective_chat.send_message(
            f"🔴 *INDOORMEDIA*\n"
            f"*Sales Command Center*\n\n"
            f"Welcome back, {rep_name}! Ready to find customers and close deals?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 BEGIN", callback_data="begin_main_menu")]])
        )
    
    elif status == 'pending':
        # Pending — show awaiting message
        await update.effective_chat.send_message(
            "⏳ **AWAITING APPROVAL**\n\n"
            f"Hi {rep_name}! Your registration is pending approval from Tyler.\n\n"
            "You'll be notified when your account is approved and you can start using the bot.",
            parse_mode="Markdown"
        )
    
    elif status == 'rejected':
        # Rejected — show rejection message
        await update.effective_chat.send_message(
            "❌ **REGISTRATION REJECTED**\n\n"
            f"Hi {rep_name}, unfortunately your registration was not approved.\n\n"
            "If you believe this is an error, please contact Tyler.",
            parse_mode="Markdown"
        )
    
    else:  # not_registered
        # New user — start registration flow
        await start_registration_flow(update, context)

# ============================================================================
# CALLBACK QUERY HANDLER (for admin and registration callbacks)
# ============================================================================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Central callback query handler that routes to appropriate functions."""
    query = update.callback_query
    data = query.data
    
    # Email permission callbacks (during registration)
    if data == "email_perm_grant":
        await handle_email_permission_response(update, context, granted=True)
    elif data == "email_perm_skip":
        await handle_email_permission_response(update, context, granted=False)
    # Admin callbacks
    elif data == "admin_dashboard":
        await show_admin_dashboard(update, context)
    elif data == "admin_review_pending":
        await show_pending_registrations_list(update, context)
    elif data == "admin_view_approved":
        await show_approved_users(update, context)
    elif data == "admin_deactivate":
        await show_approved_users(update, context)
    elif data == "admin_next_pending":
        await handle_admin_next_pending(update, context)
    elif data.startswith("admin_approve_"):
        reg_id = data.replace("admin_approve_", "")
        await handle_admin_approve(update, context, reg_id)
    elif data.startswith("admin_reject_"):
        reg_id = data.replace("admin_reject_", "")
        await handle_admin_reject(update, context, reg_id)
    elif data.startswith("admin_deactivate_user_"):
        reg_id = data.replace("admin_deactivate_user_", "")
        await handle_admin_deactivate(update, context, reg_id)

# ============================================================================
# MESSAGE HANDLER (for registration form input)
# ============================================================================

async def handle_registration_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input during registration flow."""
    if context.user_data.get(AWAITING_USER_NAME):
        await handle_registration_name(update, context, update.message.text.strip())
    elif context.user_data.get(AWAITING_USER_EMAIL):
        await handle_registration_email(update, context, update.message.text.strip())
    elif context.user_data.get(AWAITING_ACCOUNT_EMAIL):
        await handle_registration_account_email(update, context, update.message.text.strip())
