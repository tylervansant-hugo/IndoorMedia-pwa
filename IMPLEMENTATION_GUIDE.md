# Data Isolation + Email Permissions Implementation Guide

## Overview

This guide details all changes needed to implement:
1. **Data Isolation** - Each rep sees ONLY their own data
2. **Email Permissions** - Users must grant permission to scan contracts
3. **Calendar Filtering** - Only Tyler's direct team gets calendar invites
4. **Security Hardening** - Prevent cross-rep data leakage

---

## Files Modified

### 1. `registration_admin_patch.py` ✅ COMPLETE
- ✅ Added `AWAITING_ACCOUNT_EMAIL` and `AWAITING_EMAIL_PERMISSION` states
- ✅ Updated `handle_registration_email()` to ask for account email
- ✅ Added `handle_registration_account_email()` to ask for permission
- ✅ Added `handle_email_permission_response()` to process choices
- ✅ Updated `add_pending_registration()` to store email_permission
- ✅ Updated `approve_registration()` to copy email_permission to rep_registry
- ✅ Updated `_update_rep_status_in_prospect_data()` to save email_permission
- ✅ Updated `handle_callback()` to route email_perm callbacks
- ✅ Updated `handle_registration_message()` to handle account_email input

### 2. `data_isolation_patch.py` ✅ NEW FILE CREATED
Contains helper functions for:
- `get_saved_prospects(rep_id, data)` - Get rep's saved prospects only
- `get_customer_list(rep_id, data)` - Get rep's customer pipeline
- `get_search_history(rep_id, data)` - Get rep's searches only
- `get_contact_history(rep_id, data)` - Get rep's contacts only
- `save_prospect(rep_id, prospect_id, prospect_data, data)` - Save to rep's data
- `can_access_contracts(rep_id, data)` - Check email permission
- `should_invite_tyler_to_calendar(rep_name)` - Check if Tyler should be invited
- `TYLER_TEAM` list for easy management

### 3. `telegram_prospecting_bot.py` ⚠️ NEEDS UPDATES
**Critical locations to modify:**

#### A. Import Section (Top of file, ~line 40)
Add import for data isolation patch:
```python
from data_isolation_patch import (
    TYLER_TEAM,
    get_saved_prospects,
    get_customer_list,
    get_search_history,
    get_contact_history,
    save_prospect,
    add_to_search_history,
    add_to_contact_history,
    bookmark_prospect,
    can_access_contracts,
    should_invite_tyler_to_calendar,
    get_calendar_attendees,
    ensure_rep_fields,
    ensure_prospect_fields,
)
```

#### B. Saved Prospects Callback Handler (~line 5540)
**Current Code:**
```python
elif data == "saved_prospects":
    await query.answer()
    
    rep_id = get_rep_id(update)
    rep_data = load_rep_data(rep_id)
    saved = rep_data.get("saved_prospects", {})
```

**Updated Code (ISOLATE):**
```python
elif data == "saved_prospects":
    await query.answer()
    
    rep_id = get_rep_id(update)
    data_obj = load_prospect_data()
    saved = get_saved_prospects(rep_id, data_obj)  # USE ISOLATION FUNCTION
```

**Action:** Replace 3 lines with data isolation call.

#### C. Filter Saved Prospects (~line 5571)
**Current Code:**
```python
elif data.startswith("filter_"):
    status_filter = data.replace("filter_", "")
    await query.answer()
    
    rep_id = get_rep_id(update)
    rep_data = load_rep_data(rep_id)
    saved = rep_data.get("saved_prospects", {})
```

**Updated Code:**
```python
elif data.startswith("filter_"):
    status_filter = data.replace("filter_", "")
    await query.answer()
    
    rep_id = get_rep_id(update)
    data_obj = load_prospect_data()
    saved = get_saved_prospects(rep_id, data_obj)  # ISOLATED
```

#### D. Prospect Detail Access (~line 7264)
**Current Code:**
```python
prospect = rep_data["saved_prospects"].get(prospect_id, {})
```

**Updated Code:**
```python
rep_id = get_rep_id(update)
data_obj = load_prospect_data()
saved = get_saved_prospects(rep_id, data_obj)
prospect = saved.get(prospect_id, {})  # SECURITY: Only their own prospects
```

#### E. Save Prospect Action (~line 5408)
**Current Code:**
```python
rep_data["saved_prospects"][prospect_id] = {
    "name": business_name,
    # ... more fields ...
}
save_prospect_data(data_obj)
```

**Updated Code:**
```python
save_prospect(rep_id, prospect_id, {
    "name": business_name,
    # ... more fields ...
}, data_obj)
save_prospect_data(data_obj)
```

#### F. Contracts Menu Access (~line 5xxx - SEARCH FOR "/contracts")
**Add Check BEFORE showing contracts:**
```python
elif data == "contracts":
    await query.answer()
    
    rep_id = get_rep_id(update)
    data_obj = load_prospect_data()
    
    # CHECK EMAIL PERMISSION
    if not can_access_contracts(rep_id, data_obj):
        buttons = [
            [InlineKeyboardButton("✅ Grant Permission", callback_data="request_email_permission")],
            [InlineKeyboardButton("⏭️ Not Now", callback_data="main_menu")],
        ]
        await query.edit_message_text(
            "🔐 **Email Permission Required**\n\n"
            "To access contracts, please grant permission to scan your IndoorMedia emails.\n\n"
            "This is safe and only looks for 'IndoorMedia Contract Signed' emails.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
    
    # PROCEED WITH CONTRACTS FLOW
    # ... existing contracts code ...
```

#### G. Calendar Event Creation - REP INVITE (~line 5119)
**Current Code:**
```python
cmd = [
    "gog", "calendar", "create", rep_email,
    f"--summary=📅 {business_name} (Booked by {selected_rep})",
    f"--from={start_rfc3339}",
    f"--to={end_rfc3339}",
    f"--attendees=tyler.vansant@indoormedia.com",
]
```

**Updated Code (CONDITIONAL):**
```python
# Build attendees list - only add Tyler if rep is on his team
attendees = get_calendar_attendees(selected_rep)
attendee_str = ",".join(attendees) if attendees else ""

cmd = [
    "gog", "calendar", "create", rep_email,
    f"--summary=📅 {business_name} (Booked by {selected_rep})",
    f"--from={start_rfc3339}",
    f"--to={end_rfc3339}",
]

if attendee_str:
    cmd.extend([f"--attendees={attendee_str}"])
```

**Then update confirmation message:**
```python
if should_invite_tyler_to_calendar(selected_rep):
    msg += f"\n_Tyler auto-invited_"
else:
    msg += f"\n_(Tyler not invited - outside direct team)_"
```

#### H. Calendar Event Creation - DIRECT BOOKING (~line 5307)
**Current Code:**
```python
cmd = [
    "gog", "calendar", "create", rep_email,
    "--summary", summary,
    "--from", start_time,
    "--to", end_time,
    "--description", description,
    "--attendees", "tyler.vansant@indoormedia.com",
]
```

**Updated Code:**
```python
rep_name = get_rep_name(update)
attendees = get_calendar_attendees(rep_name)
attendee_str = ",".join(attendees) if attendees else ""

cmd = [
    "gog", "calendar", "create", rep_email,
    "--summary", summary,
    "--from", start_time,
    "--to", end_time,
    "--description", description,
]

if attendee_str:
    cmd.extend(["--attendees", attendee_str])
```

**Then update success message:**
```python
if should_invite_tyler_to_calendar(rep_name):
    msg += f"\n_Tyler auto-invited_"
else:
    msg += f"\n_(Tyler not invited - outside direct team)_"
```

#### I. Contact History (SEARCH FOR "contact_history")
Every place that writes to contact_history must use:
```python
add_to_contact_history(rep_id, prospect_id, contact_info, data_obj)
```

Instead of:
```python
rep_data["contact_history"][prospect_id] = contact_info
```

#### J. Search History (SEARCH FOR "search_history")
Every place that writes to search_history must use:
```python
add_to_search_history(rep_id, search_query, data_obj)
```

Instead of:
```python
rep_data["search_history"].append(search_query)
```

---

## Data Structure Changes

### pending_registrations.json
New fields added:
```json
{
  "account_email": "adan.ramos@indoormedia.com",  // NEW: Email to scan for contracts
  "email_permission": true,                        // NEW: Permission granted?
  "permission_granted_at": "2026-03-17T..."       // NEW: When permission was granted
}
```

### prospect_data.json - Rep Object
New fields added:
```json
"reps": {
  "8647728045": {
    "account_email": "adan.ramos@indoormedia.com",  // NEW
    "email_permission": true,                        // NEW
    "saved_prospects": { ... },
    "search_history": [ ... ],
    "contact_history": { ... },
    "session_searches": 0,
    "session_bookmarks": 0
  }
}
```

---

## Test Cases (Security Critical)

### 1. Data Isolation ✅
**Test:** Rep A saves prospect X. Rep B starts bot. Rep B should NOT see prospect X.
```
1. Login as Rep A (Adan)
2. Find a prospect, save it
3. Logout, clear cache
4. Login as Rep B (Dave)
5. Go to Saved Prospects
6. ❌ Rep A's prospect should NOT appear
7. ✅ Only Rep B's saved prospects should show
```

### 2. Email Permission Gate ✅
**Test:** New user must grant permission to access contracts.
```
1. New user registers
2. During registration, permission prompt appears
3. If user clicks "✅ Grant", email_permission=true
4. If user clicks "❌ Skip", email_permission=false
5. After approval:
   - If granted: Can access /contracts
   - If denied: See "Request permission?" button in contracts menu
```

### 3. Calendar Invites - Team ✅
**Test:** Adan (team) books calendar. Tyler should be invited.
```
1. Login as Adan (Adan Ramos)
2. Create calendar event
3. Check Adan's calendar
4. ✅ Tyler should be attendee
5. Check Tyler's calendar
6. ✅ Event should appear
```

### 4. Calendar Invites - Non-Team ✅
**Test:** Rick (not team) books calendar. Tyler should NOT be invited.
```
1. Login as Rick Diamond (not in TYLER_TEAM)
2. Create calendar event
3. Check Rick's calendar
4. ❌ Tyler should NOT be attendee
5. Confirm: "(Tyler not invited - outside direct team)"
```

### 5. Access Control ✅
**Test:** Non-approved user can't access bot.
```
1. New user registers
2. Tyler doesn't approve yet (status=pending)
3. Try to use /start
4. ❌ Access denied message
5. After Tyler approves (status=approved)
6. ✅ User can use bot
```

### 6. Search History Isolation ✅
**Test:** Each rep's searches are separate.
```
1. Rep A searches for "pizza"
2. Rep B searches for "coffee"
3. Rep A views search history
4. ❌ Should NOT see "coffee" search
5. ✅ Should only see "pizza"
```

### 7. TYLER_TEAM Maintenance ✅
**Test:** Easy to add/remove team members.
```
1. Edit TYLER_TEAM list in data_isolation_patch.py
2. Add new member name (just first name)
3. Restart bot
4. New member now gets Tyler calendar invites
5. ✅ Old members still work correctly
```

---

## Rollout Plan

### Phase 1: Deploy Changes
1. ✅ Update registration_admin_patch.py (DONE)
2. ✅ Create data_isolation_patch.py (DONE)
3. ⏳ Update telegram_prospecting_bot.py imports
4. ⏳ Update all saved_prospects access points
5. ⏳ Update all search_history access points
6. ⏳ Update all contact_history access points
7. ⏳ Add calendar filtering logic
8. ⏳ Add contracts permission gating

### Phase 2: Test
1. Test data isolation with 2+ reps
2. Test new user registration flow
3. Test calendar invites (team vs non-team)
4. Test contracts access (with/without permission)
5. Verify no data leakage in existing data

### Phase 3: Production
1. Backup prospect_data.json
2. Deploy updated bot
3. Test with live team
4. Monitor for data leaks
5. Celebrate 🎉

---

## Security Checklist

- [ ] No rep can access another rep's saved_prospects
- [ ] No rep can see another rep's search_history
- [ ] No rep can see another rep's contact_history
- [ ] Contract access is gated by email_permission flag
- [ ] Non-team members don't get Tyler calendar invites
- [ ] Email permission field is stored and respected
- [ ] Registration stores account_email for contracts
- [ ] All data access uses isolation functions (not direct dict access)
- [ ] TYLER_TEAM list is easily editable
- [ ] No hardcoded team checks (uses centralized list)

---

## Git Commit Message

```
feat: Implement critical security updates

- Add data isolation by rep_id (fixes cross-rep data leakage)
- Add email permission system for contract access
- Add selective calendar invites (Tyler's team only)
- Gate contract features behind email_permission flag
- Add TYLER_TEAM list for easy management
- Update registration flow with permission prompts
- Add comprehensive test cases and documentation

SECURITY: Ensures each rep sees only their own data and prevents
accidental access to other reps' prospects, history, and settings.

Fixes: All cross-rep data access vulnerabilities
Closes: #1
```

