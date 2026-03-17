# IndoorMedia ProspectBot - Registration & Admin System

## Overview

This system adds complete user registration, approval workflow, and admin dashboard to the IndoorMediaProspectBot.

### Components

1. **User Registration Flow** (`/start` command)
   - New users (not in rep_registry) see registration form
   - Collects: name + email
   - Stores in `pending_registrations.json` with status: "pending"

2. **Pending Approvals Queue** (`data/pending_registrations.json`)
   - Structure: List of `{id, telegram_id, name, email, timestamp, status}`
   - Status: "pending" | "approved" | "rejected"
   - Auto-generated IDs: `reg_001`, `reg_002`, etc.

3. **Admin Dashboard** (`/admin` command - Tyler only)
   - Shows pending registrations count & list
   - Per-registration buttons: ✅ Approve | ❌ Reject
   - View approved users + deactivate option
   - Tyler's ID: `8548368719`

4. **Access Control Gate**
   - On `/start`: Check `get_rep_status(telegram_id)`
   - Approved → Show main menu (normal flow)
   - Pending → Show "awaiting approval" message
   - Rejected → Show "registration rejected" message
   - New → Start registration flow

5. **Data Persistence**
   - `pending_registrations.json` - all registrations with status
   - `prospect_data.json` - add 'status' field to each rep (approved|pending|rejected)
   - `rep_registry.json` - unchanged (existing rep lookup)

---

## Files Modified

### 1. `scripts/telegram_prospecting_bot.py`

**Changes Required:**

#### A. Import the patch module (top of file, after other imports):
```python
from registration_admin_patch import (
    start_with_registration_gate,
    admin_command,
    handle_callback,
    handle_registration_message,
    load_rep_registry,  # Keep existing, don't conflict
)
```

#### B. Replace the `start()` function:
```python
# OLD:
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command — check rep registration, then show main menu."""
    ...

# NEW:
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command — registration gate, then show main menu."""
    await start_with_registration_gate(update, context)
```

#### C. Add `/admin` command handler in `main()`:
```python
def main():
    ...
    app.add_handler(CommandHandler("admin", admin_command))
    ...
```

#### D. Update callback_query_handler to include registration callbacks:

**Option 1 - Merge handlers:**
```python
# In main(), BEFORE other CallbackQueryHandlers:
app.add_handler(CallbackQueryHandler(handle_callback, pattern="^admin_|^reg_"))
```

**Option 2 - Add to existing callback chain:**
```python
# In your existing callback handler function, add these cases:
if update.callback_query.data.startswith("admin_") or update.callback_query.data.startswith("reg_"):
    await handle_callback(update, context)
    return
```

#### E. Add message handler for registration input:
```python
def main():
    ...
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_registration_message), group=1)
    ...
```

---

## Test Cases

### ✅ Test 1: New User Registration Flow
1. New Telegram user sends `/start`
2. Bot shows: "What's your name?"
3. User replies: "John Smith"
4. Bot shows: "What's your email?"
5. User replies: "john@example.com"
6. Bot shows: "Awaiting approval from Tyler"
7. Check `pending_registrations.json`: Registration saved with status: "pending"

### ✅ Test 2: Pending User Blocked
1. User (from Test 1) sends `/start` again
2. Bot shows: "Awaiting approval message"
3. User CANNOT access main menu or prospects

### ✅ Test 3: Tyler Admin Dashboard
1. Tyler sends `/admin`
2. Bot shows: Pending registrations list (John Smith)
3. Tyler clicks: ✅ Approve
4. John Smith added to `rep_registry.json`
5. John's status updated to "approved" in `pending_registrations.json`

### ✅ Test 4: Approved User Can Use Bot
1. John Smith sends `/start`
2. Bot shows: Main menu (normal flow)
3. John can search prospects, rates, etc.

### ✅ Test 5: Tyler Rejects User
1. New user: "Jane Doe" registers (jane@example.com)
2. Tyler opens `/admin`
3. Tyler clicks: ❌ Reject
4. Jane's status: "rejected"
5. Jane sends `/start`
6. Bot shows: "Registration was rejected"
7. Jane CANNOT use bot

### ✅ Test 6: Tyler Deactivates User
1. John Smith (approved) sends `/start` → works fine
2. Tyler opens `/admin` → "View Approved Users"
3. Tyler clicks: "⛔ Deactivate: John Smith"
4. John's status changed: "approved" → "rejected"
5. John sends `/start` next time
6. Bot shows: "Registration was rejected"
7. John CANNOT use bot

### ✅ Test 7: Existing Users Still Work
1. Users already in `rep_registry.json` (Adan, Christian, etc.)
2. Send `/start`
3. Bot shows: Main menu (skips registration)
4. No changes to their workflows

### ✅ Test 8: Prospect Features Work Post-Approval
1. New user registers → gets approved
2. User can access:
   - 🔍 Find Prospects
   - 💰 Store Rates
   - 📋 Testimonials
   - 🏪 Audit Store
   - All existing features work as before

---

## Data Structures

### `pending_registrations.json`
```json
[
  {
    "id": "reg_001",
    "telegram_id": "8647728045",
    "name": "John Smith",
    "email": "john@example.com",
    "timestamp": "2026-03-17T15:30:00Z",
    "status": "pending"
  },
  {
    "id": "reg_002",
    "telegram_id": "123456789",
    "name": "Jane Doe",
    "email": "jane@example.com",
    "timestamp": "2026-03-17T16:00:00Z",
    "status": "approved"
  }
]
```

### `prospect_data.json` - Updated with `status` field
```json
{
  "reps": {
    "8548368719": {
      "name": "Tyler Van Sant",
      "status": "approved",
      "saved_prospects": { ... },
      ...
    },
    "8647728045": {
      "name": "Adan Ramos",
      "status": "approved",
      "saved_prospects": { ... },
      ...
    }
  }
}
```

---

## API Reference

### Registration Functions

#### `get_rep_status(telegram_id: str) -> str`
Returns: `"approved"` | `"pending"` | `"rejected"` | `"not_registered"`

#### `add_pending_registration(telegram_id: str, name: str, email: str) -> str`
Adds a new pending registration. Returns registration ID.

#### `approve_registration(reg_id: str) -> bool`
Approves a registration, adds to rep_registry.

#### `reject_registration(reg_id: str) -> bool`
Rejects a registration (doesn't remove, just marks status).

#### `get_registration_by_telegram_id(telegram_id: str) -> dict | None`
Retrieves a user's registration record.

---

## Troubleshooting

### Issue: "admin_dashboard callback not working"
**Fix:** Make sure the `CallbackQueryHandler` includes admin callbacks in `main()`.

### Issue: "Users can't complete registration"
**Fix:** Verify `handle_registration_message` is registered in `main()` with `MessageHandler`.

### Issue: "New users skip registration"
**Fix:** Check that `start()` function calls `start_with_registration_gate()`.

### Issue: "Tyler's /admin not accessible"
**Fix:** Verify Tyler's telegram ID is `8548368719` in `TYLER_TELEGRAM_ID` constant.

### Issue: "Approved user still sees 'awaiting approval'"
**Fix:** Check that `pending_registrations.json` has status: "approved" AND `rep_registry.json` has user entry.

---

## Installation Checklist

- [ ] Create `data/pending_registrations.json` (empty or with test data)
- [ ] Update `start()` function in bot
- [ ] Import registration functions from patch module
- [ ] Add `/admin` command handler
- [ ] Add CallbackQueryHandler for admin callbacks
- [ ] Add MessageHandler for registration input
- [ ] Test with new user → registration → approval flow
- [ ] Test with existing users (should skip registration)
- [ ] Test with Tyler's /admin dashboard
- [ ] Verify /start shows correct message based on status

---

## Git Commit Message

```
feat: Add complete user registration and admin approval system

- New users see registration flow (name + email)
- Pending registrations stored in pending_registrations.json
- Tyler can /admin to view and approve/reject registrations
- Access control gate checks registration status on /start
- Approved users see main menu, pending/rejected see appropriate messages
- All existing rep functionality works unchanged
- prospect_data.json now tracks rep status (approved/pending/rejected)

Closes: [issue number if applicable]
```

---

## Support

For questions or issues:
1. Check troubleshooting section above
2. Review test cases to understand expected behavior
3. Check `pending_registrations.json` and `rep_registry.json` manually
4. Run one test case at a time to isolate issues
