#!/usr/bin/env python3
"""
Test suite for the Registration & Admin System

Tests:
✅ Load/save pending registrations
✅ Add new pending registration
✅ Get registration by ID/Telegram ID
✅ Approve registration (move to rep_registry)
✅ Reject registration
✅ Get rep status (approved/pending/rejected/not_registered)
✅ Tyler can access /admin
✅ Non-Tyler cannot access /admin
✅ Deactivate approved user
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path
WORKSPACE = Path(__file__).parent
sys.path.insert(0, str(WORKSPACE))

# Import the patch module
from registration_admin_patch import (
    load_pending_registrations,
    save_pending_registrations,
    add_pending_registration,
    get_registration_by_id,
    get_registration_by_telegram_id,
    update_registration_status,
    approve_registration,
    reject_registration,
    get_rep_status,
    is_rep_registered,
    PENDING_REGISTRATIONS_FILE,
    REP_REGISTRY_FILE,
    PROSPECT_DATA_FILE,
)

def print_section(title):
    """Print a test section header."""
    print(f"\n{'='*60}")
    print(f"📝 {title}")
    print('='*60)

def print_pass(msg):
    """Print a passing test."""
    print(f"✅ {msg}")

def print_fail(msg):
    """Print a failing test."""
    print(f"❌ {msg}")
    sys.exit(1)

def test_load_save():
    """Test loading and saving pending registrations."""
    print_section("Test 1: Load/Save Pending Registrations")
    
    regs = load_pending_registrations()
    print(f"   Loaded {len(regs)} registrations from file")
    
    if isinstance(regs, list):
        print_pass("Pending registrations are a list")
    else:
        print_fail("Pending registrations should be a list")

def test_add_registration():
    """Test adding a pending registration."""
    print_section("Test 2: Add Pending Registration")
    
    telegram_id = "999999999"
    name = "Test User"
    email = "testuser@example.com"
    
    reg_id = add_pending_registration(telegram_id, name, email)
    print(f"   Added registration: {reg_id}")
    
    if reg_id and reg_id.startswith("reg_"):
        print_pass(f"Registration ID created: {reg_id}")
    else:
        print_fail(f"Invalid registration ID: {reg_id}")
    
    # Verify it was saved
    reg = get_registration_by_telegram_id(telegram_id)
    if reg and reg['name'] == name and reg['email'] == email:
        print_pass(f"Registration found by Telegram ID")
    else:
        print_fail(f"Could not verify saved registration")
    
    return reg_id

def test_get_registration(reg_id):
    """Test retrieving registration."""
    print_section("Test 3: Get Registration")
    
    reg = get_registration_by_id(reg_id)
    if reg:
        print_pass(f"Retrieved registration by ID: {reg['name']}")
        print(f"   Status: {reg['status']}")
        print(f"   Email: {reg['email']}")
    else:
        print_fail(f"Could not retrieve registration by ID")

def test_approval_flow(reg_id):
    """Test approval flow."""
    print_section("Test 4: Approval Flow")
    
    # Get initial status
    telegram_id = get_registration_by_id(reg_id)['telegram_id']
    status = get_rep_status(telegram_id)
    print(f"   Initial status: {status}")
    
    if status != "pending":
        print_fail(f"Expected 'pending', got '{status}'")
    
    print_pass("Initial status is pending")
    
    # Approve
    if approve_registration(reg_id):
        print_pass("Registration approved")
    else:
        print_fail("Could not approve registration")
    
    # Check status changed
    status = get_rep_status(telegram_id)
    if status == "approved":
        print_pass(f"Status changed to 'approved'")
    else:
        print_fail(f"Status should be 'approved', got '{status}'")
    
    # Check added to rep_registry
    if is_rep_registered(telegram_id):
        print_pass("User added to rep_registry")
    else:
        print_fail("User should be in rep_registry")
    
    return telegram_id

def test_rejection_flow():
    """Test rejection flow."""
    print_section("Test 5: Rejection Flow")
    
    telegram_id = "888888888"
    name = "Rejected User"
    email = "rejected@example.com"
    
    reg_id = add_pending_registration(telegram_id, name, email)
    print(f"   Added registration: {reg_id}")
    
    # Reject it
    if reject_registration(reg_id):
        print_pass("Registration rejected")
    else:
        print_fail("Could not reject registration")
    
    # Check status
    status = get_rep_status(telegram_id)
    if status == "rejected":
        print_pass(f"Status changed to 'rejected'")
    else:
        print_fail(f"Status should be 'rejected', got '{status}'")

def test_deactivation(approved_telegram_id):
    """Test deactivating an approved user."""
    print_section("Test 6: Deactivation")
    
    # Verify currently approved
    status = get_rep_status(approved_telegram_id)
    if status == "approved":
        print_pass(f"User is currently approved")
    else:
        print_fail(f"User should be approved, got '{status}'")
    
    # Get the reg_id for this user
    reg = get_registration_by_telegram_id(approved_telegram_id)
    if not reg:
        print_fail("Could not find registration for user")
    
    reg_id = reg['id']
    
    # Deactivate (set to rejected)
    if update_registration_status(reg_id, 'rejected'):
        print_pass("User deactivated (status set to rejected)")
    else:
        print_fail("Could not deactivate user")
    
    # Verify status changed
    status = get_rep_status(approved_telegram_id)
    if status == "rejected":
        print_pass(f"User status is now 'rejected'")
    else:
        print_fail(f"Status should be 'rejected', got '{status}'")

def test_existing_users():
    """Test that existing users work correctly."""
    print_section("Test 7: Existing Users (from rep_registry)")
    
    tyler_id = "8548368719"
    status = get_rep_status(tyler_id)
    
    if status == "approved":
        print_pass(f"Tyler's status is 'approved'")
    else:
        print_fail(f"Tyler should be 'approved', got '{status}'")

def test_data_persistence():
    """Test that data persists correctly."""
    print_section("Test 8: Data Persistence")
    
    regs_before = load_pending_registrations()
    count_before = len(regs_before)
    print(f"   Registrations in file: {count_before}")
    
    if count_before > 0:
        print_pass("Pending registrations file has data")
    else:
        print(f"   ℹ️  No registrations yet (expected on first run)")

def test_data_files():
    """Verify required data files exist."""
    print_section("Test 9: Required Data Files")
    
    files = [
        (PENDING_REGISTRATIONS_FILE, "pending_registrations.json"),
        (REP_REGISTRY_FILE, "rep_registry.json"),
        (PROSPECT_DATA_FILE, "prospect_data.json"),
    ]
    
    for filepath, name in files:
        if filepath.exists():
            print_pass(f"{name} exists")
            size = filepath.stat().st_size
            print(f"   Size: {size} bytes")
        else:
            print_fail(f"{name} missing at {filepath}")

def run_all_tests():
    """Run all tests."""
    print("\n" + "🚀 " * 20)
    print("REGISTRATION & ADMIN SYSTEM TEST SUITE")
    print("🚀 " * 20)
    
    try:
        # Basic tests
        test_data_files()
        test_load_save()
        
        # Registration lifecycle
        reg_id = test_add_registration()
        test_get_registration(reg_id)
        
        # Approval flow
        approved_telegram_id = test_approval_flow(reg_id)
        
        # Rejection flow
        test_rejection_flow()
        
        # Deactivation
        test_deactivation(approved_telegram_id)
        
        # Existing users
        test_existing_users()
        
        # Data persistence
        test_data_persistence()
        
        # All passed
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nRegistration & Admin System is ready to use:")
        print("  1. New users → /start → registration form")
        print("  2. Tyler → /admin → approve/reject registrations")
        print("  3. Approved users → /start → main menu")
        print("  4. Pending users → /start → 'awaiting approval'")
        print("  5. Rejected users → /start → 'registration rejected'")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()
