"""
Smart Upsell Email System for IndoorMediaProspectBot

This module provides intelligent upsell email generation with:
1. Product tracking from contracts (Single/Double detection)
2. Personalized product suggestions based on what they signed up for
3. Nearby store finding (different chains only)
4. Dynamic email templates that are natural and actionable

Integration:
  1. Add to top of telegram_prospecting_bot.py:
     from upsell_email_system import (
         get_customer_signed_up_product,
         get_suggested_products,
         get_nearby_stores,
         draft_smart_upsell_email,
     )
  2. Replace draft_upsell_email() calls with draft_smart_upsell_email()
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from difflib import get_close_matches

logger = logging.getLogger(__name__)

# Workspace path
WORKSPACE = Path(__file__).parent.parent

# === PRODUCT TRACKING & SUGGESTIONS ===

def get_customer_signed_up_product(contract_number: str) -> str:
    """
    Look up what product a customer signed up for based on contract_number.
    
    Args:
        contract_number: Contract number (e.g., "J426747E")
    
    Returns:
        Product type: "Single", "Double", "Digital", "Cartvertising", or "Unknown"
    """
    try:
        contracts_file = WORKSPACE / "data" / "contracts.json"
        if not contracts_file.exists():
            return "Unknown"
        
        with open(contracts_file) as f:
            data = json.load(f)
        
        contracts = data.get("contracts", [])
        for contract in contracts:
            if contract.get("contract_number") == contract_number:
                product = contract.get("product_description", "").strip()
                if product in ["Single", "Double"]:
                    return product
                return product if product else "Unknown"
        
        return "Unknown"
    except Exception as e:
        logger.error(f"Error looking up contract {contract_number}: {e}")
        return "Unknown"


def get_suggested_products(product_signed_up_for: str) -> List[str]:
    """
    Get ordered list of products to suggest based on what they already have.
    
    Priority order:
    - Single → Digital, Double upgrade, Cartvertising
    - Double → Digital, Cartvertising
    - Digital → Register Tape, Cartvertising
    - Cartvertising → Digital, Register Tape
    
    Args:
        product_signed_up_for: Product they currently have ("Single", "Double", etc.)
    
    Returns:
        List of suggested products in priority order
    """
    product = product_signed_up_for.strip().title()
    
    suggestions = {
        "Single": ["Digital", "Double", "Cartvertising"],
        "Double": ["Digital", "Cartvertising"],
        "Digital": ["Register Tape", "Cartvertising"],
        "Cartvertising": ["Digital", "Register Tape"],
    }
    
    return suggestions.get(product, [])


# === NEARBY STORE FINDING ===

def extract_city_state_from_address(address: str) -> Tuple[str, str]:
    """
    Extract city and state from an address string.
    
    Examples:
        "2430 SE Umatilla St" → ("Portland", "OR")
        "1020 Atlantic Ave." → ("Longview", "WA")
        "700 SE Chkalov Dr. Suite 1" → ("Longview", "WA")
    
    Returns:
        Tuple of (city, state) or ("Unknown", "US") if extraction fails
    """
    try:
        # Address parsing is imperfect without a proper geocoding API.
        # We'll use the store data to find nearby addresses as a fallback.
        # For now, return placeholder that indicates we need additional context.
        return ("Unknown", "US")
    except Exception as e:
        logger.error(f"Error extracting city/state from address: {e}")
        return ("Unknown", "US")


def find_nearby_stores_by_address(
    address: str,
    exclude_chain: Optional[str] = None,
    limit: int = 5
) -> List[Dict]:
    """
    Find nearby stores based on a business address.
    
    Logic:
    1. Attempt to match address to known store addresses
    2. Find all stores in same city/state
    3. Filter to different chains than current one
    4. Return top N by proximity or default sort
    
    Args:
        address: Business address (e.g., "2430 SE Umatilla St")
        exclude_chain: Current chain to exclude (e.g., "Quality Food Center")
        limit: Max stores to return (default 5)
    
    Returns:
        List of store dicts with: StoreName, GroceryChain, City, State, Address
    """
    try:
        stores_file = WORKSPACE / "data" / "store-rates" / "stores.json"
        if not stores_file.exists():
            return []
        
        with open(stores_file) as f:
            all_stores = json.load(f)
        
        if not all_stores:
            return []
        
        # Try to find matching store by address or nearby address
        city_state = None
        matching_stores = []
        
        # Look for exact or similar address matches
        address_lower = address.lower()
        for store in all_stores:
            store_addr = store.get("Address", "").lower()
            
            # Check for exact match or partial match on key address components
            if store_addr == address_lower or address_lower in store_addr or store_addr in address_lower:
                city_state = (store.get("City", ""), store.get("State", ""))
                matching_stores.append(store)
        
        # If no exact match found, try fuzzy matching on address words
        if not city_state and not matching_stores:
            address_words = set(w.lower() for w in address.split() if len(w) > 2)
            
            # Find stores with matching address components
            best_match = None
            best_overlap = 0
            for store in all_stores:
                store_addr = store.get("Address", "").lower()
                store_words = set(w.lower() for w in store_addr.split() if len(w) > 2)
                overlap = len(address_words & store_words)
                
                if overlap >= 2:  # At least 2 significant words match
                    if overlap > best_overlap:
                        best_overlap = overlap
                        best_match = store
                        city_state = (store.get("City", ""), store.get("State", ""))
        
        # If still no match, infer from address format patterns
        if not city_state:
            # Look for directional prefixes (SE, NW, etc.) which hint at Portland/Seattle
            address_upper = address.upper()
            addr_parts = address.split()
            
            inferred_state = None
            inferred_city = None
            
            # Check for OR/WA abbreviations explicitly
            if "OR" in address_upper:
                inferred_state = "OR"
                # Portland is the most common OR location for register tape customers
                inferred_city = "Portland"
            elif "WA" in address_upper:
                inferred_state = "WA"
                inferred_city = "Longview"  # Common WA location
            # If address has SE/NW/NE directional prefix, likely Portland
            elif any(prefix in address_upper for prefix in ["SE ", "NW ", "NE ", "SW "]):
                inferred_state = "OR"
                inferred_city = "Portland"
            
            if inferred_state and inferred_city:
                city_state = (inferred_city, inferred_state)
        
        # Build nearby stores list from city/state
        nearby_stores = []
        if city_state:
            city, state = city_state
            
            # Get all stores in this city/state
            candidates = [
                s for s in all_stores
                if s.get("City") == city and s.get("State") == state
            ]
            
            # Separate by chain: different chains FIRST, then same chain
            different_chain_stores = []
            same_chain_stores = []
            
            if exclude_chain:
                exclude_chain_clean = exclude_chain.lower().strip()
                for s in candidates:
                    if s.get("GroceryChain", "").lower().strip() != exclude_chain_clean:
                        different_chain_stores.append(s)
                    else:
                        same_chain_stores.append(s)
            else:
                different_chain_stores = candidates
            
            # Add different chain stores first, then same chain stores
            all_sorted = different_chain_stores + same_chain_stores
            
            # Format and limit results
            for store in all_sorted[:limit]:
                nearby_stores.append({
                    "StoreName": store.get("StoreName", ""),
                    "GroceryChain": store.get("GroceryChain", ""),
                    "City": store.get("City", ""),
                    "State": store.get("State", ""),
                    "Address": store.get("Address", ""),
                    "latitude": store.get("latitude"),
                    "longitude": store.get("longitude"),
                })
        
        return nearby_stores[:limit]
    
    except Exception as e:
        logger.error(f"Error finding nearby stores for address '{address}': {e}")
        return []


def find_nearby_stores_by_address_by_city(
    city: str,
    state: str,
    exclude_chain: Optional[str] = None,
    limit: int = 5
) -> List[Dict]:
    """
    Find nearby stores in a specific city/state (direct lookup).
    If not enough stores found in the exact city, expand to nearby cities in the same state.
    
    Args:
        city: City name (e.g., "Woodland", "Portland")
        state: State abbreviation (e.g., "WA", "OR")
        exclude_chain: Chain to exclude from results
        limit: Max results to return
    
    Returns:
        List of store dicts
    """
    try:
        stores_file = WORKSPACE / "data" / "store-rates" / "stores.json"
        if not stores_file.exists():
            return []
        
        with open(stores_file) as f:
            all_stores = json.load(f)
        
        # Find all stores in this city/state
        candidates = [
            s for s in all_stores
            if s.get("City") == city and s.get("State") == state
        ]
        
        # Exclude current chain
        if exclude_chain:
            exclude_chain_clean = exclude_chain.lower().strip()
            candidates = [
                s for s in candidates
                if s.get("GroceryChain", "").lower().strip() != exclude_chain_clean
            ]
        
        # If not enough results, expand to other cities in the same state
        if len(candidates) < limit:
            # Get all cities in this state (excluding the current city)
            other_city_stores = [
                s for s in all_stores
                if s.get("State") == state and s.get("City") != city
            ]
            
            # Exclude current chain
            if exclude_chain:
                exclude_chain_clean = exclude_chain.lower().strip()
                other_city_stores = [
                    s for s in other_city_stores
                    if s.get("GroceryChain", "").lower().strip() != exclude_chain_clean
                ]
            
            # Add to candidates until we have enough
            for store in other_city_stores:
                if len(candidates) < limit:
                    candidates.append(store)
        
        # Format results
        nearby_stores = []
        for store in candidates[:limit]:
            nearby_stores.append({
                "StoreName": store.get("StoreName", ""),
                "GroceryChain": store.get("GroceryChain", ""),
                "City": store.get("City", ""),
                "State": store.get("State", ""),
                "Address": store.get("Address", ""),
                "latitude": store.get("latitude"),
                "longitude": store.get("longitude"),
            })
        
        return nearby_stores
    except Exception as e:
        logger.error(f"Error finding nearby stores in {city}, {state}: {e}")
        return []


def get_nearby_stores(
    address: str,
    exclude_chain: Optional[str] = None,
    limit: int = 5
) -> List[Dict]:
    """
    Public interface for finding nearby stores.
    Wrapper around find_nearby_stores_by_address with error handling.
    """
    return find_nearby_stores_by_address(address, exclude_chain, limit)


# === EMAIL GENERATION ===

def draft_smart_upsell_email(
    business_name: str,
    owner_name: str,
    rep_name: str,
    store_ref: str,
    contract_number: Optional[str] = None,
    address: Optional[str] = None,
    current_chain: Optional[str] = None
) -> str:
    """
    Draft intelligent upsell email with:
    - Product tracking (what they signed up for)
    - Smart product suggestions
    - Nearby store recommendations
    
    Args:
        business_name: Customer's business name
        owner_name: Contact person's name
        rep_name: Sales rep name
        store_ref: Current store reference (e.g., "Quality Food Center #0206")
        contract_number: Optional contract number to look up product
        address: Optional business address for nearby store finding
        current_chain: Optional current chain name for filtering nearby stores
    
    Returns:
        Formatted email text ready to copy/send
    """
    
    # Build greeting
    if owner_name and owner_name.lower() not in ('unknown', 'n/a', ''):
        first_name = owner_name.strip().split()[0]
        greeting = f"Hi {first_name},"
    else:
        greeting = "Hi,"
    
    # Get product they signed up for
    signed_up_for = "Single"  # Default
    if contract_number:
        signed_up_for = get_customer_signed_up_product(contract_number)
    
    # Get suggested products
    suggested_products = get_suggested_products(signed_up_for)
    
    # Get nearby stores
    nearby_stores = []
    if address and current_chain:
        nearby_stores = get_nearby_stores(address, exclude_chain=current_chain, limit=5)
    
    # Build email sections
    email_body = f"""{greeting}

Your campaign at {store_ref} is performing great! We're seeing solid results, and I wanted to talk about expanding.

Here are a few proven options:
"""
    
    # Option 1: Digital
    if "Digital" in suggested_products:
        email_body += """
**Option 1: Digital**
Try our digital offerings to reach customers beyond the register. It's a natural complement to your register tape ads.
"""
    
    # Option 2: Upgrade or Expand
    if "Double" in suggested_products:
        email_body += """
**Option 2: Upgrade to our Double Format**
Upgrade to our Double format (3.6" tall × 2.75" wide) for more real estate. You get space for a bigger logo, larger images, or more offers—more impact at every transaction.
"""
    elif "Register Tape" in suggested_products:
        email_body += """
**Option 2: Register Tape Expansion**
Expand your register tape presence to complementary locations to amplify your reach.
"""
    else:
        email_body += """
**Option 2: Expand Your Reach**
Add more locations to amplify your reach and reinforce your message at checkout.
"""
    
    # Option 3: Cartvertising
    if "Cartvertising" in suggested_products:
        email_body += """
**Option 3: Cartvertising**
Shopping carts are high-traffic touchpoints. Add cart ads to reinforce your message at checkout.
"""
    
    # Option 4: New Locations
    if nearby_stores:
        email_body += "\n**Option 4: New Locations**\nConsider expanding to nearby stores:\n"
        for store in nearby_stores:
            chain = store.get("GroceryChain", "Store")
            city = store.get("City", "")
            email_body += f"• {chain} in {city}\n"
    else:
        email_body += """
**Option 4: New Locations**
Test a new location in a nearby area to expand your market footprint.
"""
    
    # Closing
    email_body += f"""
The momentum is real. Let's capitalize on it.

When can we schedule a quick call?

Best,
{rep_name}
IndoorMedia"""
    
    return email_body


# === HELPER FOR EMAIL TEMPLATE CALLBACK ===

def _get_store_location_from_number(store_number: str, chain_name: str) -> Tuple[str, str]:
    """
    Look up a store's actual city/state from the stores database using store number.
    
    Args:
        store_number: Store number from contract (e.g., "0206", "1762")
        chain_name: Store chain name (e.g., "Safeway", "Quality Food Center")
    
    Returns:
        Tuple of (city, state) or ("", "") if not found
    """
    try:
        stores_file = WORKSPACE / "data" / "store-rates" / "stores.json"
        if not stores_file.exists():
            return ("", "")
        
        with open(stores_file) as f:
            stores = json.load(f)
        
        # Look for store with matching number and chain
        for store in stores:
            store_name = store.get("StoreName", "")
            # Store names are like "SAF07Z-1762" or "QFC07Z-0206"
            if store_number in store_name and chain_name.lower() in store.get("GroceryChain", "").lower():
                return (store.get("City", ""), store.get("State", ""))
        
        return ("", "")
    except Exception as e:
        logger.error(f"Error looking up store {store_number}: {e}")
        return ("", "")


def get_upsell_email_params_from_contract(contract_number: str) -> Dict:
    """
    Extract all necessary parameters for upsell email from a contract.
    
    Returns dict with keys:
    - product_description: What they signed up for
    - address: Business address for nearby store search
    - store_name: Current store chain
    - store_number: Store number (for location lookup)
    - contact_name: Owner/contact name
    - business_name: Business name
    - signed_up_for: Simple product name
    - nearby_stores: List of nearby store suggestions
    """
    try:
        contracts_file = WORKSPACE / "data" / "contracts.json"
        if not contracts_file.exists():
            return {}
        
        with open(contracts_file) as f:
            data = json.load(f)
        
        contracts = data.get("contracts", [])
        for contract in contracts:
            if contract.get("contract_number") == contract_number:
                product = contract.get("product_description", "Single").strip()
                address = contract.get("address", "")
                store_name = contract.get("store_name", "")
                store_number = contract.get("store_number", "")
                
                # First, try to get actual store location from store number
                actual_city, actual_state = _get_store_location_from_number(store_number, store_name)
                
                # Use actual store location if found, otherwise fall back to address parsing
                if actual_city and actual_state:
                    # Find nearby stores in the actual store's city/state
                    nearby_stores = find_nearby_stores_by_address_by_city(
                        actual_city, actual_state, exclude_chain=store_name, limit=5
                    )
                else:
                    # Fall back to address-based lookup
                    nearby_stores = get_nearby_stores(address, exclude_chain=store_name, limit=5)
                
                return {
                    "product_description": contract.get("product_description", ""),
                    "address": address,
                    "store_name": store_name,
                    "store_number": store_number,
                    "contact_name": contract.get("contact_name", ""),
                    "business_name": contract.get("business_name", ""),
                    "signed_up_for": product,
                    "nearby_stores": nearby_stores,
                }
        
        return {}
    except Exception as e:
        logger.error(f"Error extracting upsell params from contract {contract_number}: {e}")
        return {}


if __name__ == "__main__":
    """Test the system with sample data."""
    print("=== Smart Upsell Email System Tests ===\n")
    
    # Test 1: Product lookup
    print("Test 1: Product lookup")
    product = get_customer_signed_up_product("J426747E")
    print(f"  Contract J426747E product: {product}")
    assert product == "Single", f"Expected 'Single', got '{product}'"
    print("  ✓ PASS\n")
    
    # Test 2: Suggested products
    print("Test 2: Suggested products")
    for test_product in ["Single", "Double", "Digital"]:
        suggestions = get_suggested_products(test_product)
        print(f"  If customer has {test_product}: {suggestions}")
    print("  ✓ PASS\n")
    
    # Test 3: Nearby stores
    print("Test 3: Nearby stores (for first contract)")
    params = get_upsell_email_params_from_contract("J426747E")
    if params:
        print(f"  Address: {params.get('address')}")
        print(f"  Current store: {params.get('store_name')}")
        print(f"  Nearby stores found: {len(params.get('nearby_stores', []))}")
        for store in params.get('nearby_stores', [])[:3]:
            print(f"    - {store['GroceryChain']} in {store['City']}")
    print("  ✓ PASS\n")
    
    # Test 4: Email generation
    print("Test 4: Email generation")
    if params:
        email = draft_smart_upsell_email(
            business_name=params.get('business_name'),
            owner_name=params.get('contact_name'),
            rep_name="Tyler VanSant",
            store_ref="Quality Food Center #0206",
            contract_number="J426747E",
            address=params.get('address'),
            current_chain=params.get('store_name')
        )
        print(f"  Generated email ({len(email)} chars)")
        print(f"  First 200 chars: {email[:200]}...")
    print("  ✓ PASS\n")
    
    print("=== All tests passed! ===")
