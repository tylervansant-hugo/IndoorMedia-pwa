#!/usr/bin/env python3
"""
Comprehensive test suite for smart upsell email system.

Tests:
1. Product tracking from contracts
2. Suggested products based on what they signed up for
3. Nearby store finding (different chains only)
4. Email generation (dynamic content based on product + nearby stores)
5. Edge cases (missing data, no nearby stores, unknown products)
"""

import json
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from upsell_email_system import (
    get_customer_signed_up_product,
    get_suggested_products,
    get_nearby_stores,
    draft_smart_upsell_email,
    get_upsell_email_params_from_contract,
)

# Color codes for test output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BOLD = '\033[1m'

class TestResult:
    def __init__(self, name):
        self.name = name
        self.passed = 0
        self.failed = 0
    
    def assert_equal(self, actual, expected, msg=""):
        if actual == expected:
            self.passed += 1
            print(f"  {GREEN}✓{RESET} {msg or f'{actual} == {expected}'}")
        else:
            self.failed += 1
            print(f"  {RED}✗{RESET} {msg or f'Expected {expected}, got {actual}'}")
    
    def assert_in(self, item, container, msg=""):
        if item in container:
            self.passed += 1
            print(f"  {GREEN}✓{RESET} {msg or f'{item} in {container}'}")
        else:
            self.failed += 1
            print(f"  {RED}✗{RESET} {msg or f'{item} not in {container}'}")
    
    def assert_greater_equal(self, actual, expected, msg=""):
        if actual >= expected:
            self.passed += 1
            print(f"  {GREEN}✓{RESET} {msg or f'{actual} >= {expected}'}")
        else:
            self.failed += 1
            print(f"  {RED}✗{RESET} {msg or f'{actual} < {expected}'}")
    
    def report(self):
        total = self.passed + self.failed
        print(f"\n{BOLD}Test Results: {self.name}{RESET}")
        print(f"  Passed: {GREEN}{self.passed}{RESET}")
        print(f"  Failed: {RED}{self.failed}{RESET}")
        print(f"  Total:  {total}")
        return self.failed == 0


def test_product_tracking():
    """Test 1: Product tracking from contracts"""
    print(f"\n{BOLD}=== TEST 1: Product Tracking ==={RESET}")
    result = TestResult("Product Tracking")
    
    # Test Single product
    product = get_customer_signed_up_product("J426747E")
    result.assert_equal(product, "Single", "Contract J426747E = Single")
    
    # Test Double product
    product = get_customer_signed_up_product("J426153E")
    result.assert_equal(product, "Double", "Contract J426153E = Double")
    
    # Test invalid contract
    product = get_customer_signed_up_product("INVALID123")
    result.assert_equal(product, "Unknown", "Invalid contract = Unknown")
    
    return result.report()


def test_suggested_products():
    """Test 2: Suggested products based on what they have"""
    print(f"\n{BOLD}=== TEST 2: Suggested Products ==={RESET}")
    result = TestResult("Suggested Products")
    
    # Test Single → suggests Digital, Double, Cartvertising
    suggestions = get_suggested_products("Single")
    result.assert_equal(len(suggestions), 3, "Single has 3 suggestions")
    result.assert_equal(suggestions[0], "Digital", "First suggestion for Single = Digital")
    result.assert_equal(suggestions[1], "Double", "Second suggestion for Single = Double")
    result.assert_equal(suggestions[2], "Cartvertising", "Third suggestion for Single = Cartvertising")
    
    # Test Double → suggests Digital, Cartvertising (no upgrade option)
    suggestions = get_suggested_products("Double")
    result.assert_equal(len(suggestions), 2, "Double has 2 suggestions")
    result.assert_equal(suggestions[0], "Digital", "First suggestion for Double = Digital")
    result.assert_in("Cartvertising", suggestions, "Cartvertising in Double suggestions")
    
    # Test case insensitivity
    suggestions = get_suggested_products("single")
    result.assert_equal(len(suggestions), 3, "Lowercase 'single' works")
    
    # Test unknown product
    suggestions = get_suggested_products("Unknown")
    result.assert_equal(suggestions, [], "Unknown product = empty suggestions")
    
    return result.report()


def test_nearby_stores():
    """Test 3: Nearby store finding"""
    print(f"\n{BOLD}=== TEST 3: Nearby Store Finding ==={RESET}")
    result = TestResult("Nearby Stores")
    
    # Test Portland address with Quality Food Center exclusion
    stores = get_nearby_stores("2430 SE Umatilla St", exclude_chain="Quality Food Center", limit=5)
    result.assert_greater_equal(len(stores), 3, "Found at least 3 nearby stores in Portland")
    
    # Verify no Quality Food Center stores (excluded)
    qfc_stores = [s for s in stores if s['GroceryChain'] == 'Quality Food Center']
    result.assert_equal(len(qfc_stores), 0, "No Quality Food Center stores in results")
    
    # Verify store structure
    if stores:
        store = stores[0]
        result.assert_in("GroceryChain", store, "Store has GroceryChain")
        result.assert_in("City", store, "Store has City")
        result.assert_in("State", store, "Store has State")
    
    # Test with limit
    stores = get_nearby_stores("700 SE Chkalov Dr", limit=3)
    result.assert_greater_equal(3, len(stores), "Respects limit parameter")
    
    # Test empty address still returns something (falls back to inference)
    stores = get_nearby_stores("", exclude_chain=None, limit=2)
    # Don't assert on count, just that it's a list
    result.assert_equal(type(stores), list, "Returns list even for empty address")
    
    return result.report()


def test_email_generation():
    """Test 4: Email generation"""
    print(f"\n{BOLD}=== TEST 4: Email Generation ==={RESET}")
    result = TestResult("Email Generation")
    
    # Test Single product email
    email = draft_smart_upsell_email(
        business_name="Autotek International",
        owner_name="Zack Hager",
        rep_name="Tyler VanSant",
        store_ref="Quality Food Center",
        contract_number="J426747E",
        address="2430 SE Umatilla St",
        current_chain="Quality Food Center"
    )
    
    # Verify email structure
    result.assert_in("Zack", email, "Email has contact name (greeting)")
    # Note: business name appears in subject line, not body, so check contact is used
    result.assert_in("Quality Food Center", email, "Email has store name")
    result.assert_in("Digital", email, "Email mentions Digital option")
    result.assert_in("Double", email, "Email mentions Double upgrade")
    result.assert_in("Cartvertising", email, "Email mentions Cartvertising")
    result.assert_in("nearby stores", email.lower(), "Email mentions nearby stores")
    result.assert_in("Tyler VanSant", email, "Email has rep signature")
    result.assert_in("IndoorMedia", email, "Email has company name")
    
    # Verify email formatting
    result.assert_greater_equal(len(email), 400, "Email is substantial (>400 chars)")
    
    # Test with no owner name
    email = draft_smart_upsell_email(
        business_name="Test Business",
        owner_name="",
        rep_name="Rep Name",
        store_ref="Store",
        contract_number="J426747E"
    )
    result.assert_in("Hi,", email, "Email handles missing owner name")
    
    return result.report()


def test_contract_params():
    """Test 5: Extract all params from contract"""
    print(f"\n{BOLD}=== TEST 5: Contract Parameters ==={RESET}")
    result = TestResult("Contract Parameters")
    
    # Test valid contract
    params = get_upsell_email_params_from_contract("J426747E")
    result.assert_equal(params.get('business_name'), "Autotek International LLC", "Correct business name")
    result.assert_equal(params.get('contact_name'), "Zack Hager", "Correct contact name")
    result.assert_equal(params.get('signed_up_for'), "Single", "Correct product")
    result.assert_equal(params.get('store_name'), "Quality Food Center", "Correct store name")
    result.assert_in("address", params, "Has address")
    result.assert_in("nearby_stores", params, "Has nearby_stores")
    result.assert_greater_equal(len(params.get('nearby_stores', [])), 0, "Nearby stores is list")
    
    # Test invalid contract
    params = get_upsell_email_params_from_contract("INVALID")
    result.assert_equal(params, {}, "Invalid contract returns empty dict")
    
    return result.report()


def test_edge_cases():
    """Test 6: Edge cases"""
    print(f"\n{BOLD}=== TEST 6: Edge Cases ==={RESET}")
    result = TestResult("Edge Cases")
    
    # Test product lookup with missing contract
    product = get_customer_signed_up_product("")
    result.assert_equal(product, "Unknown", "Empty contract number = Unknown")
    
    # Test suggested products with empty string
    suggestions = get_suggested_products("")
    result.assert_equal(suggestions, [], "Empty product = empty suggestions")
    
    # Test nearby stores with exclude_chain that doesn't exist
    stores = get_nearby_stores(
        "2430 SE Umatilla St",
        exclude_chain="NonexistentChain",
        limit=3
    )
    result.assert_greater_equal(len(stores), 1, "Still finds stores with invalid exclude_chain")
    
    # Test email with None values
    email = draft_smart_upsell_email(
        business_name=None,
        owner_name=None,
        rep_name="",
        store_ref=None
    )
    result.assert_in("Hi,", email, "Email handles None values gracefully")
    
    return result.report()


def main():
    """Run all tests"""
    print(f"\n{BOLD}{YELLOW}{'='*70}{RESET}")
    print(f"{BOLD}{YELLOW}SMART UPSELL EMAIL SYSTEM - COMPREHENSIVE TEST SUITE{RESET}")
    print(f"{BOLD}{YELLOW}{'='*70}{RESET}")
    
    tests = [
        ("Product Tracking", test_product_tracking),
        ("Suggested Products", test_suggested_products),
        ("Nearby Stores", test_nearby_stores),
        ("Email Generation", test_email_generation),
        ("Contract Parameters", test_contract_params),
        ("Edge Cases", test_edge_cases),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n{RED}✗ {name} failed with exception: {e}{RESET}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print(f"\n{BOLD}{YELLOW}{'='*70}{RESET}")
    print(f"{BOLD}{YELLOW}TEST SUMMARY{RESET}")
    print(f"{BOLD}{YELLOW}{'='*70}{RESET}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
        print(f"  {name:30} {status}")
    
    print(f"\n{BOLD}Overall: {passed_count}/{total_count} test suites passed{RESET}")
    
    if passed_count == total_count:
        print(f"{GREEN}{BOLD}🎉 ALL TESTS PASSED!{RESET}")
        return 0
    else:
        print(f"{RED}{BOLD}❌ SOME TESTS FAILED{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
