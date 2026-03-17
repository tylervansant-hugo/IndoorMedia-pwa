# Deployment Checklist - Security Update v1.0

## Pre-Deployment

- [ ] All security tests pass: `python3 test_security.py`
- [ ] No merge conflicts in modified files
- [ ] Backup of production data created
- [ ] Team notified of maintenance window

## Files Modified

### ✅ Registration Admin Patch
- [x] Added email permission states (`AWAITING_ACCOUNT_EMAIL`, `AWAITING_EMAIL_PERMISSION`)
- [x] Updated registration flow (name → email → account_email → permission)
- [x] Added permission grant/skip buttons during registration
- [x] Updated `add_pending_registration()` to store email_permission
- [x] Updated `approve_registration()` to copy email_permission to rep_registry
- [x] Updated `handle_callback()` to route email_perm callbacks
- [x] Updated `handle_registration_message()` for account_email input

**File:** `/Users/tylervansant/.openclaw/workspace/registration_admin_patch.py`

### ✅ Data Isolation Patch (NEW)
- [x] Created comprehensive helper functions for data isolation
- [x] Implemented `TYLER_TEAM` list (editable, centralized)
- [x] Added email permission checking functions
- [x] Added calendar invite filtering logic
- [x] Added data structure validation helpers

**File:** `/Users/tylervansant/.openclaw/workspace/data_isolation_patch.py`

### ⚠️ Main Bot File (PARTIAL)
- [x] Added imports for data isolation patch
- [x] Added new registration states to imports
- [x] Updated saved_prospects access points (2 locations)
- [x] Updated calendar event creation (rep invite flow) - FILTERED
- [x] Updated calendar event creation (direct booking) - FILTERED
- [x] Updated save_prospect logic to use isolation function
- [ ] ⏳ Search history access points (needs update - not yet critical)
- [ ] ⏳ Contact history access points (needs update - not yet critical)
- [ ] ⏳ Contracts menu gating (needs implementation - blocked on contracts feature)

**File:** `/Users/tylervansant/.openclaw/workspace/scripts/telegram_prospecting_bot.py`

## Test Results

```
================================================================================
IndoorMediaProspectBot - SECURITY TEST SUITE
================================================================================

✅ TEST 1: Saved Prospects Isolation - PASS
✅ TEST 2: Customer List Isolation - PASS
✅ TEST 3: Email Permission Gating - PASS
✅ TEST 4: Calendar Invite Filtering - PASS (9 team members validated)
✅ TEST 5: TYLER_TEAM List - PASS
✅ TEST 6: Data Structure Validation - PASS

RESULTS: 6 passed, 0 failed
================================================================================
✅ ALL SECURITY TESTS PASSED - Safe to deploy!
```

## Deployment Steps

### 1. Backup Production Data
```bash
# Create timestamped backup
cp data/prospect_data.json data/prospect_data.json.backup.$(date +%Y%m%d_%H%M%S)
cp data/pending_registrations.json data/pending_registrations.json.backup.$(date +%Y%m%d_%H%M%S)
cp data/rep_registry.json data/rep_registry.json.backup.$(date +%Y%m%d_%H%M%S)
```

### 2. Deploy Updated Files
```bash
# Copy updated registration patch
cp registration_admin_patch.py scripts/

# Copy new data isolation patch
cp data_isolation_patch.py scripts/

# Updated telegram_prospecting_bot.py already in place
# (modified by edit tool, check if manual merge needed)
```

### 3. Verify Imports Work
```bash
cd scripts
python3 -c "from data_isolation_patch import TYLER_TEAM; print(f'✓ TYLER_TEAM: {TYLER_TEAM}')"
python3 -c "from registration_admin_patch import AWAITING_EMAIL_PERMISSION; print('✓ Registration patch loaded')"
```

### 4. Test Bot Start
```bash
# Test that bot starts without errors
python3 -c "from telegram_prospecting_bot import *; print('✓ Main bot imports successful')"
```

### 5. Smoke Test
- [ ] Send `/start` to bot as existing user → Should work
- [ ] Send `/start` to bot as new user → Registration flow should show name→email→account_email→permission
- [ ] Grant permission → Should store email_permission=true
- [ ] Skip permission → Should store email_permission=false
- [ ] Tyler approves registration → Rep should be able to access bot
- [ ] Create calendar event as team member (Adan) → Tyler should be invited
- [ ] Create calendar event as non-team member → Tyler should NOT be invited

### 6. Production Restart
```bash
# Stop old bot process
pkill -f telegram_prospecting_bot

# Start new bot with updated code
python3 scripts/telegram_prospecting_bot.py
```

### 7. Monitor
- [ ] Check logs for errors in first 30 minutes
- [ ] Test data isolation with 2+ reps
- [ ] Verify no cross-rep data leakage
- [ ] Confirm calendar invites working correctly

## Rollback Plan

If issues arise:

```bash
# Restore backups
cp data/prospect_data.json.backup.* data/prospect_data.json
cp data/pending_registrations.json.backup.* data/pending_registrations.json
cp data/rep_registry.json.backup.* data/rep_registry.json

# Restore old bot code
git checkout scripts/telegram_prospecting_bot.py

# Restart bot
pkill -f telegram_prospecting_bot
python3 scripts/telegram_prospecting_bot.py
```

## Post-Deployment

### Verify Security
- [ ] Run security tests again: `python3 test_security.py`
- [ ] Check prospect_data.json has email_permission fields
- [ ] Check rep_registry.json has email_permission fields
- [ ] Verify no error logs related to data access

### Validate Features
- [ ] New registration includes permission prompt
- [ ] Email permission stored correctly
- [ ] Calendar filtering works (team gets Tyler, non-team doesn't)
- [ ] Data isolation persists across sessions

### Documentation
- [ ] Update team docs on new permission flow
- [ ] Communicate TYLER_TEAM list to ops
- [ ] Document how to add/remove team members

## Future Work

1. **Contracts Menu Gating** (Phase 2)
   - Add `/contracts` command gating
   - Show "Request permission?" button if not granted
   - Only load contracts for users with email_permission=true

2. **Search History Isolation** (Phase 2)
   - Update all search_history access to use isolation function
   - Ensure each rep only sees their own searches

3. **Contact History Isolation** (Phase 2)
   - Update all contact_history access to use isolation function
   - Ensure each rep only sees their own contact attempts

4. **Audit Logging** (Phase 3)
   - Log all data access attempts
   - Alert on suspicious cross-rep access patterns
   - Create audit trail for compliance

## Monitoring

### Key Metrics
- Calendar events created (count + Tyler invites)
- New registrations with email_permission granted
- Data access errors (should be 0)
- Cross-rep data access attempts (should be 0)

### Alert Triggers
- Any attempt to access another rep's saved_prospects
- Any attempt to access another rep's search_history
- Any attempt to access another rep's contact_history
- Registration without email_permission field

## Sign-Off

- [ ] Code review completed
- [ ] Security tests passed
- [ ] Team lead approval
- [ ] Production deployment ready

**Deployed by:** _______________  
**Date:** _______________  
**Notes:** _______________  

---

## Questions?

Refer to:
- `IMPLEMENTATION_GUIDE.md` - Detailed technical changes
- `test_security.py` - Security validation logic
- `data_isolation_patch.py` - Data access isolation functions
- `registration_admin_patch.py` - Registration flow updates
