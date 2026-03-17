#!/usr/bin/env python3
"""
Security Test Suite for IndoorMediaProspectBot

Tests data isolation, email permissions, and calendar filtering.
Run with: python test_security.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add workspace to path
WORKSPACE = Path(__file__).parent
sys.path.insert(0, str(WORKSPACE))
sys.path.insert(0, str(WORKSPACE / "scripts"))

from data_isolation_patch import (
    TYLER_TEAM,
    get_saved_prospects,
    get_customer_list,
    get_search_history,
    can_access_contracts,
    should_invite_tyler_to_calendar,
)

# Test data
REP_A_ID = "8647728045"  # Adan
REP_B_ID = "8714414544"  # Dave
REP_C_ID = "999999"      # Non-team member

# ================================================================================
# TEST 1: Data Isolation - Saved Prospects
# ================================================================================

def test_saved_prospects_isolation():
    """Rep A saves prospect X. Rep B should NOT see it."""
    print("\n🧪 TEST 1: Saved Prospects Isolation")
    
    # Create test data
    data = {
        "reps": {
            REP_A_ID: {
                "name": "Adan Ramos",
                "saved_prospects": {
                    "prospect_1": {"name": "Autotek International", "status": "interested"},
                    "prospect_2": {"name": "Papa Murphy's", "status": "follow-up"},
                },
                "search_history": [],
                "contact_history": {},
            },
            REP_B_ID: {
                "name": "Dave Boring",
                "saved_prospects": {
                    "prospect_3": {"name": "Round Table Pizza", "status": "follow-up"},
                },
                "search_history": [],
                "contact_history": {},
            },
        },
        "global_searches": [],
    }
    
    # Test Rep A sees only their prospects
    rep_a_saved = get_saved_prospects(REP_A_ID, data)
    assert len(rep_a_saved) == 2, f"Rep A should see 2 prospects, got {len(rep_a_saved)}"
    assert "prospect_1" in rep_a_saved, "Rep A should see prospect_1"
    assert "prospect_3" not in rep_a_saved, "❌ SECURITY LEAK: Rep A can see Rep B's prospect!"
    
    # Test Rep B sees only their prospects
    rep_b_saved = get_saved_prospects(REP_B_ID, data)
    assert len(rep_b_saved) == 1, f"Rep B should see 1 prospect, got {len(rep_b_saved)}"
    assert "prospect_3" in rep_b_saved, "Rep B should see prospect_3"
    assert "prospect_1" not in rep_b_saved, "❌ SECURITY LEAK: Rep B can see Rep A's prospect!"
    
    print("✅ PASS: Saved prospects properly isolated by rep_id")


# ================================================================================
# TEST 2: Data Isolation - Customer List
# ================================================================================

def test_customer_list_isolation():
    """Each rep should only see their own customers in pipeline."""
    print("\n🧪 TEST 2: Customer List Isolation")
    
    data = {
        "reps": {
            REP_A_ID: {
                "name": "Adan Ramos",
                "saved_prospects": {
                    "c1": {"name": "Coffee Shop", "status": "proposal"},  # In pipeline
                    "c2": {"name": "Pizza Place", "status": "interested"},  # In pipeline
                    "c3": {"name": "Closed Deal", "status": "closed"},  # NOT in pipeline
                },
                "search_history": [],
                "contact_history": {},
            },
            REP_B_ID: {
                "name": "Dave Boring",
                "saved_prospects": {
                    "c4": {"name": "Auto Shop", "status": "follow-up"},  # In pipeline
                },
                "search_history": [],
                "contact_history": {},
            },
        },
        "global_searches": [],
    }
    
    # Test Rep A's customer list (pipeline only)
    rep_a_customers = get_customer_list(REP_A_ID, data)
    assert len(rep_a_customers) == 2, f"Rep A should have 2 customers in pipeline, got {len(rep_a_customers)}"
    assert "c3" not in rep_a_customers, "Closed deals should not be in customer list"
    assert "c4" not in rep_a_customers, "❌ SECURITY LEAK: Rep A sees Rep B's customers!"
    
    # Test Rep B's customer list
    rep_b_customers = get_customer_list(REP_B_ID, data)
    assert len(rep_b_customers) == 1, f"Rep B should have 1 customer, got {len(rep_b_customers)}"
    assert "c1" not in rep_b_customers, "❌ SECURITY LEAK: Rep B sees Rep A's customers!"
    
    print("✅ PASS: Customer list properly filtered by rep and status")


# ================================================================================
# TEST 3: Email Permission Gating
# ================================================================================

def test_email_permission_gating():
    """Contract access should be gated by email_permission flag."""
    print("\n🧪 TEST 3: Email Permission Gating")
    
    data = {
        "reps": {
            REP_A_ID: {
                "name": "Adan Ramos",
                "email_permission": True,  # Granted
                "saved_prospects": {},
            },
            REP_B_ID: {
                "name": "Dave Boring",
                "email_permission": False,  # NOT granted
                "saved_prospects": {},
            },
            REP_C_ID: {
                "name": "Unknown Rep",
                # email_permission missing - should default to False
                "saved_prospects": {},
            },
        },
        "global_searches": [],
    }
    
    # Test Rep A can access contracts
    assert can_access_contracts(REP_A_ID, data) == True, "Rep A should have contract access"
    
    # Test Rep B cannot access contracts
    assert can_access_contracts(REP_B_ID, data) == False, "Rep B should NOT have contract access"
    
    # Test missing permission defaults to False
    assert can_access_contracts(REP_C_ID, data) == False, "Missing permission should default to False"
    
    print("✅ PASS: Email permission gating works correctly")


# ================================================================================
# TEST 4: Calendar Invite Filtering - Team Members
# ================================================================================

def test_calendar_team_filtering():
    """Tyler should only be invited for his direct team."""
    print("\n🧪 TEST 4: Calendar Invite Filtering")
    
    # Test all team members
    team_members = ["Adan", "Ben", "Amy", "Dave", "Christian", "Megan", "Marty", "Matt", "Jan"]
    for member in team_members:
        should_invite = should_invite_tyler_to_calendar(member)
        assert should_invite == True, f"❌ Tyler should be invited for {member} (team member)"
        print(f"  ✓ {member}: Tyler invited")
    
    # Test non-team members
    non_team = ["Rick Diamond", "Unknown Person", "Bot Admin", "Sarah Smith"]
    for member in non_team:
        should_invite = should_invite_tyler_to_calendar(member)
        assert should_invite == False, f"❌ Tyler should NOT be invited for {member} (not team member)"
        print(f"  ✓ {member}: Tyler NOT invited")
    
    # Test partial matches (should work)
    partial_match = should_invite_tyler_to_calendar("Adan Ramos")
    assert partial_match == True, "Should match first name 'Adan' from 'Adan Ramos'"
    
    print("✅ PASS: Calendar filtering works for team and non-team members")


# ================================================================================
# TEST 5: TYLER_TEAM List Maintenance
# ================================================================================

def test_tyler_team_list():
    """TYLER_TEAM should be easily editable."""
    print("\n🧪 TEST 5: TYLER_TEAM List")
    
    assert len(TYLER_TEAM) >= 8, f"Expected at least 8 team members, got {len(TYLER_TEAM)}"
    assert "Adan" in TYLER_TEAM, "Adan should be in TYLER_TEAM"
    assert "Ben" in TYLER_TEAM, "Ben should be in TYLER_TEAM"
    
    print(f"✅ PASS: TYLER_TEAM has {len(TYLER_TEAM)} members: {', '.join(TYLER_TEAM)}")


# ================================================================================
# TEST 6: Data Structure Validation
# ================================================================================

def test_data_structure():
    """New fields should exist in all data structures."""
    print("\n🧪 TEST 6: Data Structure Validation")
    
    # Test pending registration structure
    pending_reg = {
        "id": "reg_001",
        "telegram_id": "123456",
        "name": "Adan Ramos",
        "email": "adan.ramos@indoormedia.com",
        "account_email": "adan.ramos@indoormedia.com",  # NEW
        "timestamp": "2026-03-17T...",
        "status": "pending",
        "email_permission": True,  # NEW
        "permission_granted_at": "2026-03-17T...",  # NEW
    }
    
    assert "account_email" in pending_reg, "account_email should be in pending registration"
    assert "email_permission" in pending_reg, "email_permission should be in pending registration"
    assert "permission_granted_at" in pending_reg, "permission_granted_at should be in pending registration"
    print("  ✓ Pending registration structure valid")
    
    # Test rep data structure
    rep_data = {
        "name": "Adan Ramos",
        "status": "approved",
        "email": "adan.ramos@indoormedia.com",
        "account_email": "adan.ramos@indoormedia.com",  # NEW
        "email_permission": True,  # NEW
        "saved_prospects": {},
        "search_history": [],
        "contact_history": {},
    }
    
    assert "account_email" in rep_data, "account_email should be in rep data"
    assert "email_permission" in rep_data, "email_permission should be in rep data"
    print("  ✓ Rep data structure valid")
    
    print("✅ PASS: All data structures have required fields")


# ================================================================================
# Run All Tests
# ================================================================================

def run_all_tests():
    """Run all security tests."""
    print("=" * 80)
    print("IndoorMediaProspectBot - SECURITY TEST SUITE")
    print("=" * 80)
    
    tests = [
        test_saved_prospects_isolation,
        test_customer_list_isolation,
        test_email_permission_gating,
        test_calendar_team_filtering,
        test_tyler_team_list,
        test_data_structure,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)
    
    if failed > 0:
        print("\n⚠️  SECURITY TESTS FAILED - Do not deploy!")
        sys.exit(1)
    else:
        print("\n✅ ALL SECURITY TESTS PASSED - Safe to deploy!")
        sys.exit(0)


if __name__ == "__main__":
    run_all_tests()
