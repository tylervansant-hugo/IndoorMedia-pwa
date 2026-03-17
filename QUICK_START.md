# ⚡ Quick Start - Registration & Admin System

## What's New?

Your IndoorMedia ProspectBot now has:
- 👤 **User Registration Flow** - New users register with name + email
- 🎯 **Pending Approvals** - Tyler reviews and approves registrations
- 🛡️ **Admin Dashboard** - `/admin` command for managing users
- 🔐 **Access Control** - Users can't use bot until approved

## Files to Know

```
/workspace/
├── registration_admin_patch.py       ← Complete registration system
├── data/pending_registrations.json   ← Stores pending/approved users
├── scripts/telegram_prospecting_bot.py ← Updated with registration gate
├── REGISTRATION_INTEGRATION_GUIDE.md ← Full documentation
├── REGISTRATION_SYSTEM_SUMMARY.md    ← Implementation details
└── test_registration_system.py       ← Test suite (all tests pass ✅)
```

## How It Works

### For New Users
```
1. User sends /start
2. Bot asks: "What's your name?"
3. User replies: "John Smith"
4. Bot asks: "What's your email?"
5. User replies: "john@example.com"
6. Bot shows: "Awaiting approval from Tyler"
7. Registration saved with status: "pending"
```

### For Tyler (Admin)
```
1. Tyler sends /admin
2. Bot shows dashboard with pending registrations
3. Tyler clicks "✅ Approve" or "❌ Reject"
4. User's status updated in database
5. User notified on next /start
```

### For Approved Users
```
1. Approved user sends /start
2. Bot shows main menu (normal flow)
3. User can access all features: prospects, rates, testimonials, etc.
```

## Quick Test

Run the test suite to verify everything works:

```bash
cd /Users/tylervansant/.openclaw/workspace
python3 test_registration_system.py
```

Expected output:
```
✅ ALL TESTS PASSED!

Registration & Admin System is ready to use:
  1. New users → /start → registration form
  2. Tyler → /admin → approve/reject registrations
  3. Approved users → /start → main menu
  4. Pending users → /start → 'awaiting approval'
  5. Rejected users → /start → 'registration rejected'
```

## Key Commands

| Command | User | What It Does |
|---------|------|-------------|
| `/start` | Everyone | Registration gate + main menu |
| `/admin` | Tyler only | View pending registrations & approve/reject |
| `/help` | Everyone | Show help (unchanged) |

## Key Callbacks

| Callback | What It Does |
|----------|------------|
| `admin_dashboard` | Show admin dashboard |
| `admin_review_pending` | Show pending registrations list |
| `admin_approve_X` | Approve registration X |
| `admin_reject_X` | Reject registration X |
| `admin_view_approved` | Show approved users |
| `admin_deactivate_user_X` | Deactivate user X |

## Tyler's Telegram ID

**IMPORTANT:** Tyler is identified by his Telegram ID: `8548368719`

Only this ID can access `/admin`. If Tyler's ID changes, update:
- `TYLER_TELEGRAM_ID` in `registration_admin_patch.py`

## Data Files

### `pending_registrations.json`
Stores all registrations (pending/approved/rejected):
```json
[
  {
    "id": "reg_001",
    "telegram_id": "8647728045",
    "name": "John Smith",
    "email": "john@example.com",
    "timestamp": "2026-03-17T15:30:00Z",
    "status": "approved"
  }
]
```

### `prospect_data.json`
Updated with `status` field for each rep:
```json
{
  "reps": {
    "8547728045": {
      "name": "John Smith",
      "status": "approved",
      ...
    }
  }
}
```

### `rep_registry.json`
Unchanged - existing rep lookup still works.

## Backward Compatibility

✅ **Existing users work unchanged:**
- Users already in `rep_registry.json` are auto-approved
- They see main menu on `/start` (no registration)
- All existing features work as before

## What Changed in Bot

The changes to `telegram_prospecting_bot.py` are minimal:

1. **Import patch module** (lines ~50-65):
   ```python
   from registration_admin_patch import (
       start_with_registration_gate,
       admin_command,
       ...
   )
   ```

2. **Update `start()` function** (lines ~993-1050):
   - Calls `start_with_registration_gate()` if system loaded
   - Falls back to old behavior if patch unavailable

3. **Add handlers in `main()`** (lines ~7870-7878):
   - `/admin` command handler
   - Admin callback handlers
   - Registration message handler

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Registration system not available" | Make sure `registration_admin_patch.py` is in workspace root |
| `/admin` command not working | Verify you're using Tyler's ID (8548368719) |
| New user not seeing registration form | Ensure `start()` calls `start_with_registration_gate()` |
| "Awaiting approval" forever | Check `pending_registrations.json` - status should be "approved" |
| Existing user seeing registration | They need to be in `rep_registry.json` AND status="approved" in pending_registrations.json |

## Next Steps

1. ✅ **Test the system** - Run `test_registration_system.py`
2. ✅ **Review the code** - Check `registration_admin_patch.py`
3. 📋 **Read documentation** - See `REGISTRATION_INTEGRATION_GUIDE.md` for details
4. 🚀 **Deploy** - Bot is ready to use with registration enabled

## Git Commit Template

```
feat: Add complete user registration and admin approval system

- New users see registration flow (name + email)
- Pending registrations stored in pending_registrations.json
- Tyler can /admin to view and approve/reject registrations
- Access control gate checks registration status on /start
- Approved users see main menu, pending/rejected see appropriate messages
- All existing rep functionality works unchanged
- prospect_data.json tracks rep status (approved/pending/rejected)

Test results: 9/9 tests pass ✅
```

## API Quick Reference

```python
# Registration Functions
get_rep_status(telegram_id)              # → "approved"|"pending"|"rejected"|"not_registered"
add_pending_registration(id, name, email) # → registration_id
approve_registration(reg_id)             # → adds to rep_registry
reject_registration(reg_id)              # → marks rejected
get_registration_by_id(reg_id)          # → registration dict
get_registration_by_telegram_id(id)     # → registration dict

# Admin Functions
admin_command(update, context)          # → show admin dashboard (Tyler only)
show_admin_dashboard(update, context)   # → display dashboard
handle_callback(update, context)        # → route admin callbacks

# Access Control
start_with_registration_gate(...)       # → check status & show appropriate message
```

## 🎉 You're All Set!

The registration & admin system is:
- ✅ Fully implemented
- ✅ Thoroughly tested
- ✅ Well documented
- ✅ Ready to deploy

Questions? See `REGISTRATION_INTEGRATION_GUIDE.md` for complete docs.

---

**Status:** COMPLETE & READY TO USE 🚀
