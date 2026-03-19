#!/usr/bin/env python3
"""
IndoorMediaProspectBot - Find Today's Deal
Interactive workflow: Store → Category → Subcategory → Results (10 prospects)
"""

import json
import logging
import sys
import os
import re
import asyncio
import urllib.parse
import hashlib
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pytz

# Shipping data module for real delivery dates
try:
    from shipping_data import (
        get_delivery_status, get_zone_summary, get_all_zones_summary,
        format_delivery_card, format_zone_report, get_in_transit
    )
    SHIPPING_DATA_AVAILABLE = True
except ImportError:
    SHIPPING_DATA_AVAILABLE = False

# Load environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env", override=True)
    load_dotenv(Path(__file__).parent.parent / ".env.local", override=True)
except ImportError:
    pass

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonCommands, ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure scripts directory is in path for imports
SCRIPTS_DIR = Path(__file__).parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# --- Registration & Admin System ---
try:
    from registration_admin_patch import (
        start_with_registration_gate,
        admin_command,
        handle_callback,
        handle_registration_message,
        AWAITING_USER_NAME,
        AWAITING_USER_EMAIL,
        AWAITING_ACCOUNT_EMAIL,
        AWAITING_EMAIL_PERMISSION,
    )
    REGISTRATION_SYSTEM_LOADED = True
except ImportError as e:
    logger.warning(f"Registration system not available: {e}")
    REGISTRATION_SYSTEM_LOADED = False

# --- Data Isolation & Security System ---
try:
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
    DATA_ISOLATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Data isolation system not available: {e}")
    DATA_ISOLATION_AVAILABLE = False

# --- Smart Upsell Email System ---
try:
    from upsell_email_system import (
        get_upsell_email_params_from_contract,
        draft_smart_upsell_email,
    )
    UPSELL_EMAIL_SYSTEM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Upsell email system not available: {e}")
    UPSELL_EMAIL_SYSTEM_AVAILABLE = False

# --- Counter Sign Generator ---
try:
    from counter_sign_workflow import (
        start_counter_sign_guided,
    )
    COUNTER_SIGN_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Counter sign generator not available: {e}")
    COUNTER_SIGN_AVAILABLE = False

# Navigation history management
def push_nav(context: ContextTypes.DEFAULT_TYPE, screen_name: str, callback_data: str = None):
    """Push current screen onto navigation stack."""
    if 'nav_stack' not in context.user_data:
        context.user_data['nav_stack'] = []
    context.user_data['nav_stack'].append({
        'screen': screen_name,
        'callback': callback_data or 'main_menu'
    })

def pop_nav(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Pop previous screen from navigation stack."""
    if 'nav_stack' not in context.user_data or len(context.user_data['nav_stack']) == 0:
        return {'screen': 'main_menu', 'callback': 'main_menu'}
    return context.user_data['nav_stack'].pop()

def get_nav_buttons(context: ContextTypes.DEFAULT_TYPE):
    """
    Get persistent navigation buttons (back + home).
    Automatically uses navigation stack for back button.
    """
    back_screen = pop_nav(context)  # Get previous screen
    push_nav(context, back_screen['screen'], back_screen['callback'])  # Push it back (non-destructive peek)
    
    buttons = [
        InlineKeyboardButton("⬅️ Back", callback_data=f"back_{back_screen['callback']}"),
        InlineKeyboardButton("🏠 Home", callback_data="main_menu")
    ]
    return [buttons]

WORKSPACE = Path(__file__).parent.parent
DATA_DIR = WORKSPACE / "data" / "store-rates"
STORES_FILE = DATA_DIR / "stores.json"
PROSPECT_DATA_FILE = WORKSPACE / "data" / "prospect_data.json"

TOKEN = "8781563020:AAHm_khWUcjngvS0zuNewBbpMM-p2zuMjzI"

# Ensure prospect data directory exists
PROSPECT_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

# --- Rep Registry ---
# Maps Telegram user IDs to contract system rep names
REP_REGISTRY_FILE = WORKSPACE / "data" / "rep_registry.json"

def load_rep_registry():
    """Load the rep registry mapping Telegram IDs to contract rep names."""
    if REP_REGISTRY_FILE.exists():
        with open(REP_REGISTRY_FILE) as f:
            return json.load(f)
    return {}

def save_rep_registry(registry):
    """Save the rep registry."""
    with open(REP_REGISTRY_FILE, 'w') as f:
        json.dump(registry, f, indent=2)

def get_contract_rep_name(telegram_id: str) -> Optional[str]:
    """Get the contract system rep name for a Telegram user."""
    registry = load_rep_registry()
    return registry.get(str(telegram_id), {}).get("contract_name")

def register_rep(telegram_id: str, telegram_name: str, contract_name: str):
    """Register a rep mapping."""
    registry = load_rep_registry()
    registry[str(telegram_id)] = {
        "telegram_name": telegram_name,
        "contract_name": contract_name,
        "registered_at": datetime.now().isoformat(),
    }
    save_rep_registry(registry)

def get_all_contract_rep_names():
    """Get all unique rep names from contracts."""
    contracts_file = WORKSPACE / "data" / "contracts.json"
    if not contracts_file.exists():
        return []
    with open(contracts_file) as f:
        data = json.load(f)
    reps = sorted(set(c.get("sales_rep", "") for c in data.get("contracts", []) if c.get("sales_rep")))
    return reps

def get_rep_customers(contract_rep_name: str, show_all: bool = False):
    """Get customers for a specific rep (or all if show_all)."""
    contracts_file = WORKSPACE / "data" / "contracts.json"
    if not contracts_file.exists():
        return []
    with open(contracts_file) as f:
        data = json.load(f)
    
    customers = []
    for c in data.get("contracts", []):
        if not isinstance(c, dict):
            continue
        rep = c.get("sales_rep", "")
        if show_all or rep.lower() == contract_rep_name.lower():
            customers.append({
                "contract_number": c.get("contract_number", ""),
                "business": c.get("business_name", "Unknown"),
                "owner": c.get("contact_name", ""),
                "amount": c.get("total_amount", 0),
                "date": c.get("date", ""),
                "rep": rep,
                "email": c.get("contact_email", ""),
                "phone": c.get("contact_phone", ""),
                "address": c.get("address", ""),
                "store": c.get("store_name", ""),
                "store_number": c.get("store_number", ""),
                "product": c.get("product_description", ""),
            })
    return customers

# Auto-seed registry from existing prospect_data reps
def _auto_seed_registry():
    """Try to auto-match Telegram users to contract rep names using fuzzy name matching."""
    registry = load_rep_registry()
    contract_reps = get_all_contract_rep_names()
    
    try:
        data = load_prospect_data()
        for tid, rinfo in data.get("reps", {}).items():
            if tid in registry:
                continue
            tname = rinfo.get("name", "")
            if not tname:
                continue
            # Fuzzy match: check if first name matches
            tname_lower = tname.lower().strip()
            for crep in contract_reps:
                crep_lower = crep.lower().strip()
                # Match on first name or full name
                if (tname_lower.split()[0] == crep_lower.split()[0] and 
                    len(tname_lower.split()) > 0 and len(crep_lower.split()) > 0):
                    registry[tid] = {
                        "telegram_name": tname,
                        "contract_name": crep,
                        "registered_at": datetime.now().isoformat(),
                        "auto_matched": True,
                    }
                    logger.info(f"Auto-matched rep: {tname} ({tid}) → {crep}")
                    break
        save_rep_registry(registry)
    except Exception as e:
        logger.warning(f"Auto-seed registry error: {e}")

_auto_seed_registry()

# Load stores once
with open(STORES_FILE) as f:
    STORES_LIST = json.load(f)
STORES = {s["StoreName"]: s for s in STORES_LIST}

# Build city index for quick lookup
def build_city_index():
    """Build a city → stores mapping."""
    city_index = {}
    for store in STORES_LIST:
        city = store.get("City", "Unknown").title()
        state = store.get("State", "").upper()
        key = f"{city}, {state}"
        if key not in city_index:
            city_index[key] = []
        city_index[key].append(store)
    return city_index

def get_store_cycle(store: Dict) -> str:
    """Get the store cycle (A, B, or C) from store data."""
    return store.get("Cycle", "?")

CITY_INDEX = build_city_index()
CITIES_SORTED = sorted(CITY_INDEX.keys())

# --- Rep Registry: Maps Telegram user IDs to contract system names ---
# This maps known reps so contracts filter correctly
REP_REGISTRY_FILE = WORKSPACE / "data" / "rep_registry.json"

def load_rep_registry():
    """Load the rep registry mapping Telegram IDs to contract names."""
    if REP_REGISTRY_FILE.exists():
        with open(REP_REGISTRY_FILE) as f:
            return json.load(f)
    return {}

def save_rep_registry(registry):
    """Save the rep registry."""
    with open(REP_REGISTRY_FILE, 'w') as f:
        json.dump(registry, f, indent=2)

def is_rep_registered(update: Update) -> bool:
    """Check if a rep has completed login/registration."""
    user_id = str(update.effective_user.id) if update.effective_user else None
    if not user_id:
        return False
    registry = load_rep_registry()
    return user_id in registry

# --- Product Catalog: All IndoorMedia products with pricing & metrics ---
PRODUCTS = {
    "register_tape": {
        "name": "Register Tape",
        "emoji": "🧾",
        "impressions_type": "store_foot_traffic",  # Uses case_count
        "tiers": {
            "coop": {
                "name": "Manager Approved Co-Op",
                "emoji": "🎯",
                "pricing": {
                    "monthly": lambda base: (base + PRODUCTION),
                    "3month": lambda base: ((base * 0.90) + PRODUCTION),
                    "6month": lambda base: ((base * 0.925) + PRODUCTION),
                    "pif": lambda base: ((base * 0.85) + PRODUCTION),
                }
            },
            "exclusive": {
                "name": "Exclusive Category",
                "emoji": "🏆",
                "pricing": {
                    "monthly": lambda base: (base + PRODUCTION),
                    "3month": lambda base: (base + PRODUCTION),
                    "6month": lambda base: (base + PRODUCTION),
                    "pif": lambda base: ((base * 0.95)),
                }
            },
            "contractor": {
                "name": "Contractors",
                "emoji": "🔧",
                "pricing": {
                    "3month": lambda base: (base + PRODUCTION),
                    "pif": lambda base: ((base * 0.95)),
                }
            },
        }
    },
    "cartvertising": {
        "name": "Cartvertising",
        "emoji": "🛒",
        "impressions_type": "percentage_of_store",  # Percentage of store impressions
        "tiers": {
            "coop": {
                "name": "Co-Op",
                "emoji": "🎯",
                "pricing": {
                    "monthly": lambda base: 240,  # $240/pin
                    "3month": lambda base: 240,
                    "6month": lambda base: 240,
                    "pif": lambda base: 240,
                }
            },
            "standard": {
                "name": "Standard",
                "emoji": "💲",
                "pricing": {
                    "monthly": lambda base: 240,  # $240/pin
                    "3month": lambda base: 240,
                    "6month": lambda base: 240,
                    "pif": lambda base: 240,
                }
            }
        },
        "impression_percentage": 0.15  # 15% of store impressions (percentages like register tape)
    },
    "digitalboost": {
        "name": "DigitalBoost — 1 Pin",
        "emoji": "🚀",
        "impressions_type": "fixed_impressions",
        "tiers": {
            "standard": {
                "name": "Standard Pricing",
                "emoji": "💲",
                "pricing": {
                    "monthly": lambda base: 3600,  # From screenshot
                }
            }
        },
        "impressions": 240000
    }
}

# Known rep names from contract system (for matching)
KNOWN_CONTRACT_REPS = [
    "Tyler VanSant", "Amy Dixon", "Ben Patacsil", "Megan Wink",
    "Dave Boring", "Adan Ramos", "Christian Johnson", "Marty",
    "Matt Boozer", "Matthew Boozer", "Jan", "Meghan Wink",
    "Rick Diamond", "Richard Diamond",
]

# --- Data Persistence & Rep Tracking ---
# Load video library
VIDEO_LIBRARY = {}
VIDEO_LIBRARY_FILE = WORKSPACE / "data" / "video_library.json"
try:
    if VIDEO_LIBRARY_FILE.exists():
        with open(VIDEO_LIBRARY_FILE) as f:
            VIDEO_LIBRARY = json.load(f)
except Exception as e:
    logger.warning(f"Could not load video library: {e}")

# Load testimonials
TESTIMONIALS = []
TESTIMONIALS_FILE = WORKSPACE / "data" / "testimonials_cache.json"
try:
    if TESTIMONIALS_FILE.exists():
        with open(TESTIMONIALS_FILE) as f:
            TESTIMONIALS = json.load(f)
except Exception as e:
    logger.warning(f"Could not load testimonials: {e}")

# Load product catalog data
PRODUCT_DATA = {}
_product_files = {
    "child_seat": WORKSPACE / "data" / "cartvertising" / "child_seat.json",
    "nose": WORKSPACE / "data" / "cartvertising" / "nose.json",
    "digitalboost": WORKSPACE / "data" / "digital" / "digitalboost.json",
    "findlocal": WORKSPACE / "data" / "digital" / "findlocal.json",
    "reviewboost": WORKSPACE / "data" / "digital" / "reviewboost.json",
    "loyaltyboost": WORKSPACE / "data" / "digital" / "loyaltyboost.json",
}
for _key, _path in _product_files.items():
    try:
        if _path.exists():
            with open(_path) as f:
                PRODUCT_DATA[_key] = json.load(f)
            logger.info(f"✅ Loaded product data: {_key}")
    except Exception as e:
        logger.warning(f"Could not load product {_key}: {e}")

# State proximity mapping (adjacent states)
STATE_NEIGHBORS = {
    "WA": ["OR", "ID", "CA"],
    "OR": ["WA", "ID", "CA", "NV"],
    "CA": ["OR", "NV", "AZ"],
    "ID": ["WA", "OR", "MT", "WY", "NV", "UT"],
    "NV": ["CA", "OR", "ID", "UT", "AZ"],
    "AZ": ["CA", "NV", "UT", "CO", "NM"],
    "UT": ["ID", "NV", "AZ", "CO", "WY"],
    "CO": ["WY", "NE", "KS", "OK", "NM", "UT"],
    "MT": ["ND", "SD", "WY", "ID"],
    "WY": ["MT", "CO", "NE", "UT", "ID"],
    "TX": ["OK", "AR", "LA", "NM"],
}

def extract_state_from_address(address: str) -> str:
    """Extract state abbreviation from address."""
    if not address:
        return None
    
    # Look for 2-letter state abbreviation at end
    parts = address.split()
    if len(parts) >= 1:
        last_part = parts[-1].upper()
        if len(last_part) == 2 and last_part.isalpha():
            return last_part
    
    return None


def extract_city_from_address(address: str) -> str:
    """Extract city name from address (e.g., '123 Main St, Portland, OR 97214' -> 'Portland')."""
    if not address:
        return None
    
    # Format is typically: street, city, state zip
    # So city is before the state (last 2 chars before the zip)
    parts = address.split(',')
    if len(parts) >= 2:
        # City is in the second-to-last comma-separated part (before state/zip)
        city_part = parts[-2].strip() if len(parts) >= 2 else None
        return city_part
    
    return None


# Define nearby cities within same state (both directions are in this map)
NEARBY_CITIES = {
    # Washington
    ("vancouver", "wa"): ["portland", "camas", "washougal", "ridgefield", "battle ground"],
    ("portland", "or"): ["vancouver", "beaverton", "hillsboro", "gresham", "oregon city"],
    ("seattle", "wa"): ["tacoma", "bellevue", "everett", "renton", "kent", "auburn"],
    ("tacoma", "wa"): ["seattle", "fife", "puyallup", "lakewood", "olympia"],
    
    # Oregon
    ("salem", "or"): ["keizer", "marion", "corvallis", "wilsonville"],
    ("eugene", "or"): ["springfield", "coos bay", "medford", "salem"],
    ("portland", "or"): ["vancouver", "beaverton", "hillsboro", "gresham"],
    
    # California
    ("los angeles", "ca"): ["pasadena", "long beach", "glendale", "burbank", "torrance"],
    ("san francisco", "ca"): ["oakland", "berkeley", "daly city", "san mateo"],
    ("san diego", "ca"): ["chula vista", "oceanside", "carlsbad", "vista"],
}


def is_nearby_city(city1: str, city2: str, state: str) -> bool:
    """Check if two cities are nearby in the same state."""
    if not city1 or not city2 or not state:
        return False
    
    c1 = city1.lower().strip()
    c2 = city2.lower().strip()
    state_lower = state.lower().strip()
    
    # Same city
    if c1 == c2:
        return True
    
    # Check nearby list
    key = (c1, state_lower)
    if key in NEARBY_CITIES:
        if c2 in NEARBY_CITIES[key]:
            return True
    
    # Check reverse
    key2 = (c2, state_lower)
    if key2 in NEARBY_CITIES:
        if c1 in NEARBY_CITIES[key2]:
            return True
    
    return False

def get_testimonials_for_prospect(prospect: dict, limit: int = 3) -> list:
    """Get relevant testimonials using keyword search with smart fallbacks.
    
    Strategy:
    1. Extract primary keyword from business name (e.g., "Ramen" from "Kenji's Ramen")
    2. Search for that keyword
    3. If found >= 3 results, return them
    4. If not found, try expanded keywords (e.g., Ramen → [Sushi, Teriyaki, Japanese, Asian])
    5. Return up to `limit` results (default 3)
    """
    # Reload testimonials if cache is empty
    testimonials = TESTIMONIALS if TESTIMONIALS else load_testimonials()
    
    if not testimonials:
        return []
    
    # Extract primary keyword from business name
    business_name = prospect.get('name', '').lower()
    words = business_name.split()
    filtered_words = [w.rstrip("'s").lower() for w in words if w.lower() not in ('the', 'a', 'and', '&')]
    primary_keyword = filtered_words[-1] if filtered_words else business_name
    primary_keyword = primary_keyword.rstrip("'s").strip()
    
    logger.info(f"Testimonials search for '{business_name}' → keyword: '{primary_keyword}'")
    
    # Try primary keyword first
    results = search_testimonials(primary_keyword)
    
    if len(results) >= limit:
        logger.info(f"Found {len(results)} testimonials for '{primary_keyword}'")
        return results[:limit]
    
    # If primary keyword didn't yield enough, try expanded keywords
    expanded_keywords = expand_search_keywords(primary_keyword)
    expanded_keywords = [k for k in expanded_keywords if k.lower() != primary_keyword.lower()]
    
    logger.info(f"'{primary_keyword}' found {len(results)}, trying: {expanded_keywords}")
    
    # Try each expanded keyword
    for keyword in expanded_keywords:
        if len(results) >= limit:
            break
        expanded_results = search_testimonials(keyword)
        existing_businesses = {r.get('business', '').lower() for r in results}
        for r in expanded_results:
            if r.get('business', '').lower() not in existing_businesses and len(results) < limit:
                results.append(r)
    
    return results[:limit]


# National brand to category mapping
NATIONAL_BRANDS = {
    # Automotive
    "Automotive": [
        "jiffy lube", "valvoline", "firestone", "les schwab", "pep boys", "midas", "napa",
        "goodyear", "bridgestone", "costco tire", "walmart tire", "belle tire", "auto zone",
        "advance auto", "o'reilly", "grease monkey", "take 5", "maaco", "amaco",
    ],
    # Food & Drink
    "Food & Drink": [
        "mcdonald's", "subway", "starbucks", "dunkin", "chipotle", "taco bell", "burger king",
        "wendys", "chick-fil-a", "pizza hut", "dominos", "little caesars", "papa johns",
        "kfc", "popeyes", "five guys", "in-n-out", "sonic", "jack in the box",
        "arby's", "panera", "smoothie king", "jamba juice", "raising cane's", "wingstop",
    ],
    # Health & Beauty
    "Health & Beauty": [
        "great clips", "supercuts", "clips", "sport clips", "super salons", "ulta", "sephora",
        "anytime fitness", "planet fitness", "la fitness", "equinox", "orange theory",
    ],
    # Pets
    "Pets": [
        "petsmart", "petco", "pet supermarket", "banfield", "vca", "vetco",
    ],
    # Retail
    "Retail": [
        "walmart", "target", "costco", "best buy", "home depot", "lowes", "ace hardware",
        "dollar general", "dollar tree", "five below", "tjmaxx", "marshalls",
    ],
    # Kids / Care Centers
    "Kids": [
        "daycare", "preschool", "montessori", "learning center", "kindercare", "child care",
        "childcare", "after school", "tutoring", "goddard", "primrose", "bright horizons",
    ],
    # Adult / Senior Care
    "Senior Care": [
        "assisted living", "senior living", "retirement", "nursing home", "memory care",
        "adult day care", "senior center", "brookdale", "sunrise senior",
    ],
    # Dispensaries
    "Dispensary": [
        "dispensary", "cannabis", "marijuana", "weed", "420",
    ],
    # Financial Services
    "Financial Services": [
        "bank", "credit union", "amex", "chase", "wells fargo", "boa", "citi",
    ],
}


def get_category_for_national_brand(business_name: str) -> str:
    """Check if prospect is a national brand and return its category."""
    name_lower = business_name.lower()
    
    for category, brands in NATIONAL_BRANDS.items():
        for brand in brands:
            if brand in name_lower:
                return category
    
    return None


def get_videos_for_prospect(prospect: dict) -> list:
    """Get relevant videos for a prospect based on their business type."""
    if not VIDEO_LIBRARY or not VIDEO_LIBRARY.get("categories"):
        return []
    
    business_name = prospect.get("name", "").lower()
    
    # First check if it's a national brand
    brand_category = get_category_for_national_brand(business_name)
    if brand_category and brand_category in VIDEO_LIBRARY["categories"]:
        videos = VIDEO_LIBRARY["categories"][brand_category].get("videos", [])
        return videos[:3]
    
    # Otherwise use keyword matching
    category = prospect.get("category", "").lower()
    search_text = f"{business_name} {category}".lower()
    
    # Find best matching category
    best_category = None
    best_match_count = 0
    
    for cat_name, cat_data in VIDEO_LIBRARY.get("categories", {}).items():
        keywords = cat_data.get("keywords", [])
        match_count = sum(1 for kw in keywords if kw in search_text)
        
        if match_count > best_match_count:
            best_match_count = match_count
            best_category = cat_name
    
    if best_category:
        videos = VIDEO_LIBRARY["categories"][best_category].get("videos", [])
        return videos[:3]  # Return top 3 videos from best category
    
    return []


def load_prospect_data():
    """Load all prospect data from persistence file."""
    if PROSPECT_DATA_FILE.exists():
        with open(PROSPECT_DATA_FILE) as f:
            return json.load(f)
    return {"reps": {}, "global_searches": []}

def save_prospect_data(data):
    """Save prospect data to persistence file."""
    with open(PROSPECT_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_rep_id(update: Update) -> str:
    """Get unique rep ID from Telegram user."""
    user_id = update.effective_user.id if update.effective_user else "unknown"
    return str(user_id)

def get_rep_name(update: Update) -> str:
    """Get rep name from Telegram user."""
    user = update.effective_user
    if user:
        return f"{user.first_name} {user.last_name}".strip() or user.username or f"Rep {user.id}"
    return "Unknown"

def get_rep_email(update: Update) -> str:
    """Get rep email from rep registry by matching rep name."""
    rep_name = get_rep_name(update)
    registry = load_rep_registry()
    
    # Search registry for matching rep name
    for user_id, rep_info in registry.items():
        if rep_info.get("display_name") == rep_name or rep_info.get("contract_name") == rep_name:
            # Look up email from hardcoded roster (as fallback)
            reps_roster = {
                "Adan Ramos": "Adan.Ramos@Indoormedia.com",
                "Amy Dixon": "Amy.Dixon@indoormedia.com",
                "Ben Patacsil": "Ben.Patacsil@Indoormedia.com",
                "Christian Johnson": "Christian.Johnson@Indoormedia.com",
                "Dave Boring": "Dave.Boring@Indoormedia.com",
                "Jan Banks": "Jan.Banks@Indoormedia.com",
                "Marty/Anthony Eng": "Anthony.Eng@Indoormedia.com",
                "Matt Boozer": "Matthew.Boozer@Indoormedia.com",
                "Megan Wink": "Megan.Wink@Indoormedia.com",
                "Meghan Wink": "Megan.Wink@Indoormedia.com",
            }
            return reps_roster.get(rep_name, f"{rep_name.lower().replace(' ', '.')}@indoormedia.com")
    
    # Fallback: construct from rep name
    return f"{rep_name.lower().replace(' ', '.')}@indoormedia.com"

def get_rep_phone(update: Update) -> str:
    """Get rep phone number from roster by rep name."""
    rep_name = get_rep_name(update)
    
    # Phone roster (add as we get numbers)
    reps_phone = {
        "Adan Ramos": "(360) 555-0101",
        "Amy Dixon": "(503) 555-0102",
        "Ben Patacsil": "(503) 555-0103",
        "Christian Johnson": "(714) 555-0104",
        "Dave Boring": "(360) 555-0105",
        "Jan Banks": "(503) 555-0106",
        "Marty/Anthony Eng": "(503) 555-0107",
        "Matt Boozer": "(541) 555-0108",
        "Megan Wink": "(503) 555-0109",
        "Meghan Wink": "(503) 555-0109",
        "Tyler Van Sant": "(360) 213-8973",
    }
    return reps_phone.get(rep_name, "Not available")

def load_rep_data(rep_id: str):
    """Load data for a specific rep."""
    data = load_prospect_data()
    if rep_id not in data["reps"]:
        data["reps"][rep_id] = {
            "name": "",
            "saved_prospects": {},
            "search_history": [],
            "contact_history": {},
            "session_searches": 0,
            "session_bookmarks": 0,
            "cart": [],  # Cart items: [{store, ad_type, payment_plan, price, store_num}, ...]
        }
        save_prospect_data(data)
    # Ensure cart exists for existing reps
    if "cart" not in data["reps"][rep_id]:
        data["reps"][rep_id]["cart"] = []
        save_prospect_data(data)
    return data["reps"][rep_id]

def add_to_cart(rep_id: str, product_type: str, tier: str = None, store_num: str = None, 
                ad_type: str = None, payment_plan: str = None, impressions_type: str = None, 
                price: float = None, daily_impressions: int = None, **kwargs):
    """Add item to cart. Supports all products (Register Tape, Cartvertising, DigitalBoost).
    
    Args:
        rep_id: Rep ID
        product_type: 'register_tape', 'cartvertising', or 'digitalboost'
        tier: Pricing tier ('coop', 'exclusive', 'contractor', 'standard')
        store_num: Store number (for Register Tape only)
        ad_type: Ad type ('single', 'double') - Register Tape only
        payment_plan: Payment plan ('monthly', '3month', '6month', 'pif')
        impressions_type: Type of impressions ('store_foot_traffic' for Register Tape, 'fixed_impressions' for others)
        price: Price (for non-Register Tape products)
        daily_impressions: Daily impressions (for non-Register Tape products)
    """
    data = load_prospect_data()
    if rep_id not in data["reps"]:
        load_rep_data(rep_id)  # Initialize
        data = load_prospect_data()
    
    product_type = product_type.lower()
    
    # === REGISTER TAPE ===
    if product_type == "register_tape":
        store = STORES.get(store_num)
        if not store:
            return None
        
        # Calculate price from store + tier
        base = store["DoubleAd"] if ad_type.lower() == "double" else store["SingleAd"]
        tier = tier.lower() if tier else "coop"
        
        # Get pricing from tier config
        if tier == "coop":
            if payment_plan == "monthly":
                price = base + PRODUCTION
            elif payment_plan == "3month":
                price = (base * 0.90) + PRODUCTION
            elif payment_plan == "6month":
                price = (base * 0.925) + PRODUCTION
            elif payment_plan == "pif":
                price = (base * 0.85) + PRODUCTION
        elif tier == "exclusive":
            base_total = base + PRODUCTION
            if payment_plan == "monthly":
                price = base_total
            elif payment_plan == "3month":
                price = base_total
            elif payment_plan == "6month":
                price = base_total
            elif payment_plan == "pif":
                price = base_total * 0.95
        elif tier == "contractor":
            base_total = base + PRODUCTION
            if payment_plan == "3month":
                price = base_total
            elif payment_plan == "pif":
                price = base_total * 0.95
        
        # Calculate impressions
        case_count = store.get("Case Count", 0)
        impressions = calculate_impressions_metrics(case_count)
        daily_impressions = impressions.get("daily", 0)
        annual_impressions = daily_impressions * 365
        
        # Calculate cost metrics
        cpm = (price / annual_impressions * 1000) if annual_impressions > 0 else 0
        cost_per_day = price / 365
        
        cart_item = {
            "product_type": "register_tape",
            "product_name": "Register Tape",
            "store_num": store_num,
            "store_name": store.get("GroceryChain", "?"),
            "city": store.get("City", ""),
            "state": store.get("State", ""),
            "address": store.get("Address", ""),
            "tier": tier,
            "ad_type": ad_type,
            "payment_plan": payment_plan,
            "price": price,
            "case_count": case_count,
            "daily_impressions": daily_impressions,
            "annual_impressions": annual_impressions,
            "cpm": cpm,
            "cost_per_day": cost_per_day,
            "added_at": datetime.now().isoformat()
        }
    
    # === CARTVERTISING ===
    elif product_type == "cartvertising":
        # For Cartvertising: percentage-based impressions like register tape, with bundle_type option
        bundle_type = kwargs.get('bundle_type', 'standalone')
        tier = kwargs.get('tier', 'coop')
        tier_config = product["tiers"].get(tier, {})
        pricing_func = tier_config.get("pricing", {}).get(payment_plan)
        if not pricing_func:
            return None
        price = pricing_func(0)  # Cartvertising has fixed per-pin pricing
        
        # Cartvertising impressions based on store data (percentage of store traffic)
        case_count = store.get("Case Count", 0)
        impressions = calculate_impressions_metrics(case_count)
        base_daily = impressions.get("daily", 0)
        
        # Apply percentage (15% of store traffic for cartvertising)
        daily_impressions = int(base_daily * product.get("impression_percentage", 0.15))
        annual_impressions = daily_impressions * 365
        
        # Cartvertising pricing: $240/pin per month (from screenshot)
        price_per_pin = price
        production_fee = 0  # Already included in pricing
        
        # Payment plan pricing (single pin)
        if payment_plan == "monthly":
            price = price_per_pin  # Monthly recurring
        elif payment_plan == "3month":
            # 3-month plan: 3 × price_per_pin
            price = price_per_pin * 3
        elif payment_plan == "6month":
            # 6-month plan: 6 × price_per_pin
            price = price_per_pin * 6
        elif payment_plan == "pif":
            # Paid in full (annual): 12 × price_per_pin with discount
            price = (price_per_pin * 12) * 0.95  # 5% discount
        else:
            price = price_per_pin
        
        # Add production fee to first month/term
        price += production_fee
        
        # Calculate CPM and annual cost
        annual_cost = (price_per_pin * 12) + production_fee  # Standard annual cost
        cost_per_day = annual_cost / 365
        cpm = (price_per_pin / annual_impressions * 1000) if annual_impressions > 0 else 0
        
        cart_item = {
            "product_type": "cartvertising",
            "product_name": f"Cartvertising ({bundle_type.title()}) - {annual_impressions:,} impressions",
            "bundle_type": bundle_type,
            "impressions": impressions,
            "tier": kwargs.get('tier', 'standard'),
            "payment_plan": payment_plan,
            "price": price,
            "daily_impressions": daily_impressions,
            "annual_impressions": annual_impressions,
            "cpm": cpm,
            "cost_per_day": cost_per_day,
            "added_at": datetime.now().isoformat()
        }
    
    # === DIGITALBOOST ===
    elif product_type == "digitalboost":
        # For DigitalBoost: fixed 240k impressions per pin, varying pin count
        pin_count = kwargs.get('pin_count', 1)
        tier = kwargs.get('tier', 'Standard').lower()
        
        # Fixed 240k impressions per pin
        annual_impressions = 240000 * pin_count
        daily_impressions = annual_impressions // 365
        
        # Pricing from screenshot:
        # Co-Op: $2,795 (1st pin) + $2,400/each (2-4)
        # Standard: $3,600/pin
        production_fee = 395  # covers up to 5 pins
        
        if tier == "co-op" or tier == "coop":
            # Co-Op pricing: 1st pin $2,400 + 2nd-4th pins $2,400 each
            if pin_count == 1:
                pin_cost = 2795  # $2,400 + $395 production
            else:
                pin_cost = 2795 + (2400 * (pin_count - 1))
        else:
            # Standard pricing: $3,600 per pin
            pin_cost = 3600 * pin_count + production_fee
        
        # Apply payment plan
        if payment_plan == "monthly":
            price = pin_cost / 12  # Monthly installment
        elif payment_plan == "3month":
            price = pin_cost / 3  # 3-month installment
        elif payment_plan == "6month":
            price = pin_cost / 6  # 6-month installment
        elif payment_plan == "pif":
            price = pin_cost * 0.95  # 5% discount for paid in full
        else:
            price = pin_cost / 12
        
        # Calculate CPM and annual cost
        annual_cost = pin_cost if payment_plan == "pif" else (pin_cost if payment_plan == "monthly" else pin_cost)
        cost_per_day = (pin_cost / 365) if payment_plan == "monthly" else (pin_cost / 12 / 30)
        cpm = (price / annual_impressions * 1000) if annual_impressions > 0 else 0
        
        cart_item = {
            "product_type": "digitalboost",
            "product_name": f"DigitalBoost ({tier.title()}) - {pin_count} Pin{'s' if pin_count > 1 else ''} ({annual_impressions:,} impressions)",
            "pin_count": pin_count,
            "tier": tier,
            "payment_plan": payment_plan,
            "price": price,
            "daily_impressions": daily_impressions,
            "annual_impressions": annual_impressions,
            "cpm": cpm,
            "cost_per_day": cost_per_day,
            "added_at": datetime.now().isoformat()
        }
    
    else:
        return None
    
    data["reps"][rep_id]["cart"].append(cart_item)
    save_prospect_data(data)
    return price

def remove_from_cart(rep_id: str, index: int):
    """Remove item from cart by index."""
    data = load_prospect_data()
    if rep_id in data["reps"] and 0 <= index < len(data["reps"][rep_id]["cart"]):
        data["reps"][rep_id]["cart"].pop(index)
        save_prospect_data(data)
        return True
    return False

def get_cart_summary(rep_id: str):
    """Get cart summary with location breakdown and total."""
    data = load_prospect_data()
    cart = data.get("reps", {}).get(rep_id, {}).get("cart", [])
    
    if not cart:
        return None, None
    
    # Group by location
    by_location = {}
    total = 0
    for item in cart:
        key = f"{item['store_name']} — {item['city']}"
        if key not in by_location:
            by_location[key] = {"items": [], "subtotal": 0}
        by_location[key]["items"].append(item)
        by_location[key]["subtotal"] += item["price"]
        total += item["price"]
    
    return by_location, total

def get_today_date():
    """Get today's date as a string."""
    return datetime.now().strftime("%Y-%m-%d")

# Category structure — each value is either:
#   - A list of Google Places API types (simple)
#   - A dict with {"types": [...], "keyword": "...", "exclude": [...]} (precise)
#
# Google Places Nearby API types reference:
# https://developers.google.com/maps/documentation/places/web-service/supported_types
#
# IMPORTANT: Google Places "type" param only accepts ONE type per query.
# When a list is given, each type is queried separately and results merged.

CATEGORIES = {
    "🍽️ Restaurants": {
        "Mexican": {
            "types": ["restaurant"],
            "keyword": "mexican restaurant taqueria",
            "exclude": ["taco bell"]
        },
        "Pizza": {
            "types": ["restaurant"],
            "keyword": "pizza pizzeria",
            "exclude": []
        },
        "Coffee/Café": {
            "types": ["cafe"],
            "keyword": "coffee cafe espresso",
            "exclude": ["starbucks"]
        },
        "Sushi/Japanese": {
            "types": ["restaurant"],
            "keyword": "sushi japanese ramen",
            "exclude": []
        },
        "Fast Food": {
            "types": ["meal_takeaway", "restaurant"],
            "keyword": "fast food burger",
            "exclude": []
        },
        "Chinese": {
            "types": ["restaurant"],
            "keyword": "chinese restaurant",
            "exclude": []
        },
        "Thai": {
            "types": ["restaurant"],
            "keyword": "thai restaurant",
            "exclude": []
        },
        "Indian": {
            "types": ["restaurant"],
            "keyword": "indian restaurant curry",
            "exclude": []
        },
        "BBQ/Steakhouse": {
            "types": ["restaurant"],
            "keyword": "bbq steakhouse grill smokehouse",
            "exclude": []
        },
        "Italian": {
            "types": ["restaurant"],
            "keyword": "italian restaurant pasta",
            "exclude": []
        },
        "Bakery": {
            "types": ["bakery"],
            "keyword": "bakery pastry",
            "exclude": ["grocery", "walmart", "safeway"]
        },
        "Bar/Pub": {
            "types": ["bar"],
            "keyword": "bar pub tavern brewery taproom",
            "exclude": []
        },
        "All Restaurants": {
            "types": ["restaurant"],
            "keyword": "",
            "exclude": ["mcdonald", "burger king", "wendy", "taco bell"]
        }
    },
    "🚗 Automotive": {
        "Oil Change/Lube": {
            "types": ["car_repair"],
            "keyword": "oil change lube quick lube",
            "exclude": ["body shop", "collision", "auto parts"]
        },
        "Car Wash": {
            "types": ["car_wash"],
            "keyword": "car wash detailing",
            "exclude": []
        },
        "Auto Repair": {
            "types": ["car_repair"],
            "keyword": "auto repair mechanic garage",
            "exclude": ["body shop", "collision", "car wash"]
        },
        "Tires": {
            "types": ["car_repair"],
            "keyword": "tire tires wheel alignment",
            "exclude": []
        },
        "Car Dealer": {
            "types": ["car_dealer"],
            "keyword": "car dealer dealership",
            "exclude": ["rental", "rent"]
        },
        "Body Shop": {
            "types": ["car_repair"],
            "keyword": "body shop collision paint auto body",
            "exclude": []
        },
        "Transmission": {
            "types": ["car_repair"],
            "keyword": "transmission",
            "exclude": []
        }
    },
    "💄 Beauty & Wellness": {
        "Hair Salon": {
            "types": ["hair_salon", "beauty_salon"],
            "keyword": "hair salon haircut stylist",
            "exclude": ["nail", "pet", "dog", "cat"]
        },
        "Barber": {
            "types": ["hair_salon"],
            "keyword": "barber barbershop",
            "exclude": []
        },
        "Nail Salon": {
            "types": ["beauty_salon"],
            "keyword": "nail salon nails manicure pedicure",
            "exclude": ["hair"]
        },
        "Spa/Massage": {
            "types": ["spa"],
            "keyword": "spa massage day spa facial",
            "exclude": ["hot tub", "pool"]
        },
        "Gym/Fitness": {
            "types": ["gym"],
            "keyword": "gym fitness center workout",
            "exclude": []
        },
        "Yoga/Pilates": {
            "types": ["gym"],
            "keyword": "yoga pilates studio",
            "exclude": []
        },
        "Tanning": {
            "types": ["beauty_salon"],
            "keyword": "tanning salon",
            "exclude": []
        }
    },
    "🏥 Health/Medical": {
        "Dentist": {
            "types": ["dentist"],
            "keyword": "dentist dental",
            "exclude": ["hospital", "emergency"]
        },
        "Chiropractor": {
            "types": ["doctor"],
            "keyword": "chiropractor chiropractic",
            "exclude": []
        },
        "Eye Care": {
            "types": ["doctor"],
            "keyword": "optometrist eye care vision glasses optician",
            "exclude": ["hospital"]
        },
        "Veterinarian": {
            "types": ["veterinary_care"],
            "keyword": "veterinarian vet animal clinic",
            "exclude": ["shelter", "rescue", "humane"]
        },
        "Physical Therapy": {
            "types": ["physiotherapist"],
            "keyword": "physical therapy rehab",
            "exclude": ["hospital"]
        },
        "Urgent Care": {
            "types": ["doctor"],
            "keyword": "urgent care walk in clinic",
            "exclude": ["hospital", "emergency room"]
        },
        "Pharmacy": {
            "types": ["pharmacy"],
            "keyword": "pharmacy",
            "exclude": ["walmart", "costco", "safeway", "fred meyer"]
        }
    },
    "🏠 Home Services": {
        "Contractor": {
            "types": ["general_contractor"],
            "keyword": "general contractor remodel renovation",
            "exclude": ["apartment", "property management"]
        },
        "Roofing": {
            "types": ["roofing_contractor"],
            "keyword": "roofing roof contractor",
            "exclude": []
        },
        "Plumber": {
            "types": ["plumber"],
            "keyword": "plumber plumbing",
            "exclude": []
        },
        "Electrician": {
            "types": ["electrician"],
            "keyword": "electrician electrical",
            "exclude": []
        },
        "HVAC": {
            "types": ["electrician"],
            "keyword": "hvac heating cooling air conditioning furnace",
            "exclude": []
        },
        "Landscaping": {
            "types": ["general_contractor"],
            "keyword": "landscaping lawn care yard maintenance",
            "exclude": []
        },
        "Pest Control": {
            "types": ["local_government_office"],
            "keyword": "pest control exterminator",
            "exclude": []
        },
        "Cleaning": {
            "types": ["laundry"],
            "keyword": "cleaning service house cleaning maid janitorial carpet",
            "exclude": []
        }
    },
    "👔 Professionals": {
        "Real Estate Agent": {
            "types": ["real_estate_agency"],
            "keyword": "real estate agent realtor broker",
            "exclude": ["apartment", "property management", "commercial real estate", "senior living", "assisted living", "storage", "self storage", "mortgage"]
        },
        "Insurance Agent": {
            "types": ["insurance_agency"],
            "keyword": "insurance agent",
            "exclude": ["hospital", "medical", "health department"]
        },
        "Accountant/CPA": {
            "types": ["accounting"],
            "keyword": "accountant CPA tax preparation bookkeeper",
            "exclude": ["h&r block", "liberty tax"]
        },
        "Lawyer/Attorney": {
            "types": ["lawyer"],
            "keyword": "lawyer attorney law firm",
            "exclude": ["bail bond"]
        },
        "Financial Advisor": {
            "types": ["finance"],
            "keyword": "financial advisor planner wealth management",
            "exclude": ["bank", "atm", "credit union", "payday"]
        },
        "Mortgage/Lender": {
            "types": ["finance"],
            "keyword": "mortgage lender home loan",
            "exclude": ["bank", "atm", "credit union", "payday"]
        }
    },
    "🛍️ Retail": {
        "Clothing/Apparel": {
            "types": ["clothing_store"],
            "keyword": "clothing store apparel boutique",
            "exclude": ["thrift", "goodwill", "salvation army"]
        },
        "Pet Store": {
            "types": ["pet_store"],
            "keyword": "pet store",
            "exclude": ["shelter", "rescue", "humane"]
        },
        "Jewelry": {
            "types": ["jewelry_store"],
            "keyword": "jewelry jeweler",
            "exclude": ["pawn"]
        },
        "Furniture": {
            "types": ["furniture_store", "home_goods_store"],
            "keyword": "furniture store",
            "exclude": ["thrift", "goodwill"]
        },
        "Florist": {
            "types": ["florist"],
            "keyword": "florist flowers",
            "exclude": ["grocery"]
        },
        "Cell Phone": {
            "types": ["cell_phone_store"],
            "keyword": "cell phone mobile wireless",
            "exclude": []
        },
        "Liquor/Wine": {
            "types": ["liquor_store"],
            "keyword": "liquor wine beer spirits",
            "exclude": ["grocery", "safeway", "fred meyer"]
        },
        "Dispensary": {
            "types": ["store"],
            "keyword": "dispensary cannabis marijuana weed",
            "exclude": ["pharmacy", "medical center"]
        }
    },
    "👶 Care Centers": {
        "Child Care/Day Care": {
            "types": ["school"],
            "keyword": "daycare day care child care childcare preschool learning center montessori",
            "exclude": ["high school", "middle school", "elementary school", "university", "college"]
        },
        "After School Program": {
            "types": ["school"],
            "keyword": "after school program tutoring enrichment kids center",
            "exclude": ["university", "college"]
        },
        "Adult Day Care": {
            "types": ["health"],
            "keyword": "adult day care senior center adult care elderly care",
            "exclude": ["hospital", "emergency"]
        },
        "Assisted Living": {
            "types": ["health"],
            "keyword": "assisted living senior living retirement home nursing home memory care",
            "exclude": ["hospital", "emergency room"]
        }
    },
    "👦 Kids Activities & Tutoring": {
        "Tutoring": {
            "types": ["education"],
            "keyword": "tutoring tutor academic help homework test prep sat act",
            "exclude": ["university", "college"]
        },
        "After School Programs": {
            "types": ["school"],
            "keyword": "after school program afterschool enrichment kids club youth center",
            "exclude": ["university", "college", "babysitting"]
        },
        "Martial Arts": {
            "types": ["gym"],
            "keyword": "martial arts karate taekwondo kung fu judo boxing mma",
            "exclude": []
        },
        "Dance Classes": {
            "types": ["education"],
            "keyword": "dance classes ballet tap hip hop contemporary dance studio",
            "exclude": ["nightclub", "bar"]
        },
        "Music Lessons": {
            "types": ["education"],
            "keyword": "music lessons piano guitar violin drums lessons instructor",
            "exclude": []
        },
        "Youth Sports": {
            "types": ["gym", "sports"],
            "keyword": "youth sports kids sports soccer baseball basketball football swimming",
            "exclude": ["adult", "professional"]
        },
        "Summer Camps": {
            "types": ["school"],
            "keyword": "summer camp day camp kids camp sports camp",
            "exclude": ["adult", "college"]
        },
        "General Kids Activities": {
            "types": ["education"],
            "keyword": "kids activities enrichment programs children classes",
            "exclude": ["university", "college"]
        }
    }
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command — registration gate + access control."""
    chat_id = update.effective_chat.id
    logger.info(f"🚀 START command received from {update.effective_user.username or update.effective_user.id}")
    
    # Guard against duplicate /start within 2 seconds
    last_start = context.user_data.get('last_start_time')
    now = datetime.now()
    if last_start and (now - last_start).total_seconds() < 2:
        logger.warning(f"⏭️ Ignoring duplicate /start command (within 2 seconds)")
        return
    context.user_data['last_start_time'] = now
    
    # Clear any stale awaiting states
    clear_awaiting_states(context)
    
    # Set menu button
    try:
        await context.bot.set_chat_menu_button(
            chat_id=chat_id,
            menu_button=MenuButtonCommands()
        )
    except Exception as e:
        logger.warning(f"Menu button error: {e}")
    
    # Use registration gate if available
    if REGISTRATION_SYSTEM_LOADED:
        await start_with_registration_gate(update, context)
    else:
        # Fallback: old behavior
        rep_id = get_rep_id(update)
        rep_name = get_rep_name(update)
        data_obj = load_prospect_data()
        if rep_id not in data_obj["reps"]:
            data_obj["reps"][rep_id] = {
                "name": rep_name,
                "saved_prospects": {},
                "search_history": [],
                "contact_history": {},
                "session_searches": 0,
                "session_bookmarks": 0,
            }
            save_prospect_data(data_obj)
            logger.info(f"New rep registered: {rep_name} ({rep_id})")
        
        if not is_rep_registered(update):
            await show_rep_login(update, context)
            return
        
        welcome_text = f"""🔴 *INDOORMEDIA*
*Sales Command Center*

Welcome back, {rep_name}! Ready to find customers and close deals?"""
        
        buttons = [[InlineKeyboardButton("🚀 BEGIN", callback_data="begin_main_menu")]]
        
        await update.effective_chat.send_message(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )


async def show_rep_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show rep login/identification screen."""
    buttons = []
    # Show known reps as buttons for easy login
    rep_names_shown = set()
    for name in KNOWN_CONTRACT_REPS:
        # Deduplicate similar names
        short = name.split()[0]  # First name
        if short in rep_names_shown:
            continue
        rep_names_shown.add(short)
        buttons.append([InlineKeyboardButton(f"👤 {name}", callback_data=f"rep_login_{name}")])
    
    buttons.append([InlineKeyboardButton("🆕 I'm New", callback_data="rep_login_new")])
    
    await update.effective_chat.send_message(
        "👋 *Welcome to IndoorMediaProspectBot!*\n\n"
        "Who are you? Select your name to get started:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu."""
    await show_main_menu(update, context)


async def examples(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show example queries."""
    examples_text = """🚀 Start prospect search  \
📚 Example stores & cities  \
📍 Browse categories  \
🔄 Reset search

*Example Store Numbers:*

🏪 *Fred Meyer — Vancouver, WA*
`FME07Z-0236`

🥬 *Safeway — Portland, OR*
`SAF07Y-1073`

🏢 *Haggen — Bellingham, WA*
`HAG07X-3430`

Send any store number or city to get started!
"""
    buttons = [
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(examples_text, parse_mode="Markdown", reply_markup=keyboard)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help menu."""
    help_text = """📖 *How to Use the Bot*

*3 Simple Steps:*

1️⃣ *Enter location*
   Send a store number: `FME07Z-0236`
   Or a city: `Portland`

2️⃣ *Pick a category*
   Restaurants → Mexican
   Retail → Clothing
   Services → Salons

3️⃣ *Get prospects*
   Get ranked by likelihood
   Click [📍 Maps] to view & call
   Click [📞 Call] to dial directly

*Tools Available:*
📊 *ROI Calculator* — Calculate campaign ROI before pitching
💰 *Store Rates* — Quick pricing lookup
📋 *Testimonials* — Find relevant case studies
🏪 *Audit Store* — Track tape inventory

*Button Actions:*
🔍 New Search — Start over
📍 Maps — View on Google Maps
📞 Call — Dial number directly
✅ Booked — Mark as closed
"""
    buttons = [[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]]
    await update.message.reply_text(help_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset search context."""
    context.user_data.clear()
    reset_text = """🔄 *Search Reset*

Your search context has been cleared.
Ready to find new prospects!
"""
    buttons = [[InlineKeyboardButton("🔍 New Search", callback_data="new_search")]]
    await update.message.reply_text(reset_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))


async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open Shellian dashboard."""
    buttons = []
    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        "✨ *Shellian Dashboard*\n\nClick the button below to open your AI assistant dashboard!",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def handle_photo_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo uploads for testimonial coupon images."""
    if context.user_data.get(AWAITING_TEST_COUPON_IMAGE):
        context.user_data[AWAITING_TEST_COUPON_IMAGE] = False
        
        # Get the photo file
        photo = update.message.photo[-1]  # Get highest resolution
        file = await context.bot.get_file(photo.file_id)
        
        # Download the photo
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
            await file.download_to_memory(tmp)
            photo_path = tmp.name
        
        # Store the photo path
        context.user_data['testimonial_form']['coupon_image'] = photo_path
        
        # Build review message
        form = context.user_data.get('testimonial_form', {})
        review = f"""
        📋 *Testimonial Review*
        
        *Personal Info:*
        Name: {form.get('name', '')}
        Business: {form.get('business', '')}
        Address: {form.get('address', '')}
        Phone: {form.get('phone', '')}
        
        *Store Info:*
        Chain: {form.get('grocery_chain', '')}
        Zone: {form.get('zone', '')}
        Store #: {form.get('store_number', '')}
        
        *Program Details:*
        Coupons/week: {form.get('coupons_count', '')}
        Avg Ticket: ${form.get('ticket_price', '')}
        ROI Rating: {form.get('roi_rating', '')}
        Duration: {form.get('duration', '')}
        Would Renew: {form.get('renew', '')}
        Would Recommend: {form.get('recommend', '')}
        Comments: {form.get('comments', '') or '(none)'}
        
        ✅ Coupon image attached
        
        Everything look good?
        """.strip()
        
        buttons = [
            [InlineKeyboardButton("✅ Submit Testimonial", callback_data="test_final_submit")],
            [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")],
        ]
        
        await update.message.reply_text(
            review,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
    
    # If not awaiting coupon image, silently ignore (don't reply)


async def handle_store_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle store number, city name, or persistent keyboard buttons."""
    text = update.message.text.strip()
    
    logger.info(f"📥 Query: {text}")
    

    # Handle submenu buttons
    if text == "⬅️ Main Menu":
        await show_main_menu(update, context)
        return
    elif text == "🔍 Find Prospects":
        context.user_data['search_type'] = 'location'
        await update.message.reply_text("🔍 Enter a store number or city name:", reply_markup=ReplyKeyboardRemove())
        return
    elif text == "💾 Saved Prospects":
        context.user_data['view_saved'] = True
        # This would normally call the saved prospects handler
        await update.message.reply_text("Loading saved prospects...", reply_markup=ReplyKeyboardRemove())
        return
    elif text == "🔄 Reset Search":
        context.user_data.clear()
        await show_main_menu(update, context)
        return
    elif text == "👥 My Customers":
        context.user_data['view_customers'] = True
        await update.message.reply_text("Loading your customers...", reply_markup=ReplyKeyboardRemove())
        return
    elif text == "💳 My Sales":
        context.user_data['view_sales'] = True
        await update.message.reply_text("Loading your sales...", reply_markup=ReplyKeyboardRemove())
        return
    elif text == "📜 Register Tape":
        buttons = [
            [KeyboardButton("💰 Store Rates"), KeyboardButton("⬅️ Back to Products")],
        ]
        await update.message.reply_text(
            "📜 *REGISTER TAPE*\n\nSales presentation & store rate lookup:\n\n🎬 Presentation: https://docs.google.com/presentation/d/1Xs60nX3i6MJkC81GgnK-50jBrkWVPu06xRpmv8z4PIc/edit?usp=sharing\n\n📹 Explainer: https://youtu.be/_gdlyEszHfY?si=0_kHou89WrMhvNY_",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )
        return
    elif text == "💰 Store Rates":
        buttons = [[KeyboardButton("⬅️ Back to Products"), KeyboardButton("⬅️ Main Menu")]]
        context.user_data[AWAITING_RATES] = True  # Set flag so next input is treated as rates lookup
        await update.message.reply_text(
            "💰 *STORE RATES*\n\nEnter a store number or city name to lookup register tape pricing:\n\nPresentation: https://docs.google.com/presentation/d/1Xs60nX3i6MJkC81GgnK-50jBrkWVPu06xRpmv8z4PIc/edit?usp=sharing\n\nExplainer: https://youtu.be/_gdlyEszHfY?si=0_kHou89WrMhvNY_",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )
        return
    elif text == "🛒 Cartvertising":
        buttons = [
            [KeyboardButton("🛒 Child Seat"), KeyboardButton("👃 Nose of Cart")],
            [KeyboardButton("⬅️ Back to Products"), KeyboardButton("⬅️ Main Menu")],
        ]
        await update.message.reply_text(
            "🛒 *CARTVERTISING*\n\nSales presentations & product options:\n\n🎬 Presentation: https://docs.google.com/presentation/d/1xwIF4CaTp07AKunGaJysCSIGqN7VCdbL4fgOH3XEpl4/edit?usp=sharing\n\n📹 Explainer: https://www.youtube.com/watch?v=PduxHWy8sMc",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )
        return
    elif text == "🛒 Child Seat":
        buttons = [
            [KeyboardButton("🎬 Presentation"), KeyboardButton("📹 Explainer")],
            [KeyboardButton("👃 Nose of Cart"), KeyboardButton("⬅️ Back to Products")],
        ]
        await update.message.reply_text(
            "🛒 *CHILD SEAT*\n\nPresentation: https://docs.google.com/presentation/d/1xwIF4CaTp07AKunGaJysCSIGqN7VCdbL4fgOH3XEpl4/edit?usp=sharing\n\nExplainer: https://www.youtube.com/watch?v=PduxHWy8sMc",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )
        return
    elif text == "👃 Nose of Cart":
        buttons = [
            [KeyboardButton("🎬 Presentation"), KeyboardButton("📹 Explainer")],
            [KeyboardButton("🛒 Child Seat"), KeyboardButton("⬅️ Back to Products")],
        ]
        await update.message.reply_text(
            "👃 *NOSE OF CART*\n\nPresentation: https://drive.google.com/file/d/1Bvr0XOWHLO5DMwOmi6NQAcuuk4b9EkFS/view?usp=sharing\n\nExplainer: https://www.youtube.com/watch?v=PduxHWy8sMc",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )
        return
    elif text == "📱 Digital Products":
        buttons = [
            [KeyboardButton("🚀 DigitalBoost"), KeyboardButton("📍 FindLocal")],
            [KeyboardButton("⭐ ReviewBoost"), KeyboardButton("💎 LoyaltyBoost")],
            [KeyboardButton("⬅️ Back to Products"), KeyboardButton("⬅️ Main Menu")],
        ]
        await update.message.reply_text(
            "📱 *DIGITAL PRODUCTS*\n\nSales presentations & product options:\n\n🎬 Presentation: https://docs.google.com/presentation/d/1xwIF4CaTp07AKunGaJysCSIGqN7VCdbL4fgOH3XEpl4/edit?usp=sharing\n\n📹 Explainer: https://www.youtube.com/watch?v=PduxHWy8sMc\n\n🔗 Connection Hub: https://drive.google.com/file/d/199IkMptOlSYviHScKNKUlqELQOhWFxnB/view?usp=sharing",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )
        return
    elif text == "🚀 DigitalBoost":
        buttons = [
            [KeyboardButton("📍 FindLocal"), KeyboardButton("⭐ ReviewBoost")],
            [KeyboardButton("💎 LoyaltyBoost"), KeyboardButton("⬅️ Back to Products")],
        ]
        await update.message.reply_text(
            "🚀 *DIGITALBOOST*\n\nGeofence pin delivering digital banner ads on mobile websites, games & apps.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )
        return
    elif text == "📍 FindLocal":
        buttons = [
            [KeyboardButton("🚀 DigitalBoost"), KeyboardButton("⭐ ReviewBoost")],
            [KeyboardButton("💎 LoyaltyBoost"), KeyboardButton("⬅️ Back to Products")],
        ]
        await update.message.reply_text(
            "📍 *FINDLOCAL*\n\nLocal search optimization & local business profile management.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )
        return
    elif text == "⭐ ReviewBoost":
        buttons = [
            [KeyboardButton("🚀 DigitalBoost"), KeyboardButton("📍 FindLocal")],
            [KeyboardButton("💎 LoyaltyBoost"), KeyboardButton("⬅️ Back to Products")],
        ]
        await update.message.reply_text(
            "⭐ *REVIEWBOOST*\n\nOnline review generation & reputation management.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )
        return
    elif text == "💎 LoyaltyBoost":
        buttons = [
            [KeyboardButton("🚀 DigitalBoost"), KeyboardButton("📍 FindLocal")],
            [KeyboardButton("⭐ ReviewBoost"), KeyboardButton("⬅️ Back to Products")],
        ]
        await update.message.reply_text(
            "💎 *LOYALTYBOOST*\n\nCustomer loyalty & retention program platform.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )
        return
    elif text == "📊 Dashboard":
        await update.message.reply_text("📊 Loading dashboard...", reply_markup=ReplyKeyboardRemove())
        return
    elif text == "👥 Team Sales":
        await update.message.reply_text("👥 Loading team sales...", reply_markup=ReplyKeyboardRemove())
        return
    elif text == "📅 Leaderboard":
        await update.message.reply_text("📅 Loading leaderboard...", reply_markup=ReplyKeyboardRemove())
        return
    elif text == "📊 ROI Calc":
        await update.message.reply_text("📊 Loading ROI calculator...", reply_markup=ReplyKeyboardRemove())
        return
    elif text == "📋 Testimonials":
        await update.message.reply_text("📋 Loading testimonials...", reply_markup=ReplyKeyboardRemove())
        return
    elif text == "📝 Submit Testimonial":
        await update.message.reply_text("📝 Submit a testimonial...", reply_markup=ReplyKeyboardRemove())
        return
    elif text == "🏪 Audit Store":
        await update.message.reply_text("🏪 Loading audit tool...", reply_markup=ReplyKeyboardRemove())
        return
    elif text == "⬅️ Back to Products":
        buttons = [
            [KeyboardButton("📜 Register Tape"), KeyboardButton("🛒 Cartvertising")],
            [KeyboardButton("📱 Digital Products"), KeyboardButton("⬅️ Main Menu")],
        ]
        await update.message.reply_text(
            "🛍️ *PRODUCTS*\n\nExplore register tape, cartvertising, and digital solutions.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )
        return
    
    # Handle text menu shortcuts
    text_lower = text.lower()
    if text_lower in ("menu", "help", "start"):
        await show_main_menu(update, context)
        return
    
    # Handle new rep registration name input
    if context.user_data.get('awaiting_rep_name'):
        context.user_data['awaiting_rep_name'] = False
        user_id = str(update.effective_user.id)
        new_name = text.strip()
        
        registry = load_rep_registry()
        registry[user_id] = {
            "contract_name": new_name,
            "display_name": new_name,
            "role": "rep",
            "registered_at": datetime.now().strftime("%Y-%m-%d"),
        }
        save_rep_registry(registry)
        logger.info(f"✅ New rep registered: {new_name} (ID: {user_id})")
        
        await update.message.reply_text(
            f"✅ *Welcome, {new_name}!*\n\nYou're registered. Loading your dashboard...",
            parse_mode="Markdown"
        )
        await asyncio.sleep(1)
        await show_main_menu(update, context)
        return
    
    # Handle notepad editing if awaiting
    if context.user_data.get(AWAITING_NOTEPAD_EDIT):
        context.user_data[AWAITING_NOTEPAD_EDIT] = False
        context.user_data['notepad'] = text
        
        await update.message.reply_text(
            f"✅ *Notepad Updated*\n\n```\n{text}\n```\n\n_Saved! These notes will be added to calendar appointments._",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
        )
        return
    
    # Handle prospect notes if awaiting
    if context.user_data.get('awaiting_event_note'):
        context.user_data['awaiting_event_note'] = False
        event_id = context.user_data.get('current_event_id', '')
        cust_idx = context.user_data.get('current_event_cust_idx', 0)
        event_idx = context.user_data.get('current_event_idx', 0)
        
        if event_id:
            # Save note to file
            notes_file = WORKSPACE / "data" / "event_notes.json"
            event_notes = {}
            try:
                if notes_file.exists():
                    with open(notes_file) as f:
                        event_notes = json.load(f)
            except:
                pass
            
            # Append note with timestamp and rep name
            rep_name = get_rep_name(update)
            timestamp = datetime.now().strftime("%m/%d %I:%M%p")
            new_note = f"[{timestamp} — {rep_name}] {text}"
            
            if event_notes.get(event_id):
                event_notes[event_id] += f"\n{new_note}"
            else:
                event_notes[event_id] = new_note
            
            with open(notes_file, 'w') as f:
                json.dump(event_notes, f, indent=2)
            
            await update.message.reply_text(
                f"✅ *Note saved!*\n\n📝 {text}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📅 Back to Event", callback_data=f"event_detail_{cust_idx}_{event_idx}")],
                    [InlineKeyboardButton("⬅️ Back to Events", callback_data=f"customer_events_{cust_idx}")],
                ])
            )
        else:
            await update.message.reply_text("❌ Could not save note — event not found.")
        return
    
    if context.user_data.get(AWAITING_PROSPECT_NOTE):
        prospect_id = context.user_data.pop(AWAITING_PROSPECT_NOTE)
        prospect = context.user_data.get('prospects', {}).get(prospect_id, {})
        
        # Save the note
        if 'prospect_notes' not in context.user_data:
            context.user_data['prospect_notes'] = {}
        context.user_data['prospect_notes'][prospect_id] = {
            'business': prospect.get('name', ''),
            'notes': text,
            'timestamp': datetime.now().isoformat(),
        }
        
        # Store the notes in prospect data
        if 'prospect_notes' not in context.user_data:
            context.user_data['prospect_notes'] = {}
        context.user_data['prospect_notes'][prospect_id] = {
            'business': prospect.get('name', ''),
            'notes': text,
            'timestamp': datetime.now().isoformat(),
        }
        
        # Update prospect in context with notes
        if prospect_id in context.user_data.get('prospects', {}):
            context.user_data['prospects'][prospect_id]['notes'] = text
        
        business_name = prospect.get('name', 'Prospect')
        
        # Show expanded view again with notes visible
        # Re-expand the prospect to show notes were saved
        business_name_full = prospect.get('name', 'Unknown')
        address = prospect.get('address', '')
        phone = prospect.get('phone', '')
        distance = prospect.get('distance_miles', 'N/A')
        score = prospect.get('likelihood_score', 0)
        website = prospect.get('website', '')
        
        # Emoji rating
        if score >= 80:
            emoji = "🔥"
        elif score >= 70:
            emoji = "⭐"
        else:
            emoji = "👀"
        
        # Build complete message with all info
        msg = f"{emoji} *{business_name_full}*\n"
        msg += f"📊 Score: {score}/100\n"
        msg += f"📏 Distance: {distance} mi\n"
        msg += f"📞 {phone}\n"
        
        if address:
            msg += f"📍 `{address}`\n"
        
        if website:
            msg += f"🌐 [Visit Website]({website})\n"
        
        # Show notes
        msg += f"\n📝 *Notes:* _{text[:100]}{'...' if len(text) > 100 else ''}_\n"
        
        # Advertising signals
        advertising_signals = prospect.get('advertising_signal', {})
        if advertising_signals:
            platforms = []
            if advertising_signals.get('greet_magazine'):
                platforms.append("📰 Greet")
            if advertising_signals.get('facebook_ads'):
                platforms.append("📘 Facebook")
            if advertising_signals.get('google_local_services'):
                platforms.append("🔍 Google Local")
            if advertising_signals.get('groupon'):
                platforms.append("🎁 Groupon")
            if advertising_signals.get('found_advertising'):
                platforms.append("📢 Active Ads")
            
            if platforms:
                msg += f"\n💡 *Advertising on:* {' | '.join(platforms)}\n"
        
        mappoint_url = f"https://sales.indoormedia.com/Mappoint?business={urllib.parse.quote(business_name_full)}&address={urllib.parse.quote(address)}"
        google_maps_url = f"https://www.google.com/maps/search/{urllib.parse.quote(address)}"
        
        # Show all actions again
        buttons = [
            [
                InlineKeyboardButton("📍 Maps", url=google_maps_url),
                InlineKeyboardButton("🗺️ Mappoint", url=mappoint_url),
            ],
            [
                InlineKeyboardButton("💾 Save", callback_data=f"save_{prospect_id}"),
                InlineKeyboardButton("🎬 Video", callback_data=f"video_{prospect_id}"),
            ],
            [
                InlineKeyboardButton("📝 Notes", callback_data=f"note_{prospect_id}"),
                InlineKeyboardButton("📅 Calendar", callback_data=f"cal_{prospect_id}"),
            ],
            [InlineKeyboardButton("◀️ Collapse", callback_data=f"collapse_{prospect_id}")],
        ]
        
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        return
    
    # Handle cart store selection if awaiting
    if context.user_data.get(AWAITING_CART_STORE):
        context.user_data[AWAITING_CART_STORE] = False
        # Check if it's a city name first
        city_match = text.strip().title()
        if city_match in CITY_INDEX:
            # Show stores in that city with cart add buttons
            stores_in_city = CITY_INDEX[city_match]
            buttons = []
            for store in stores_in_city:
                store_num = store["StoreName"]
                chain = store.get("GroceryChain", "")
                street = store.get("Address", "").split(",")[0] if store.get("Address") else ""
                street = street.strip()[:20]
                label = f"🛒 {store_num} — {chain} {street}"
                buttons.append([InlineKeyboardButton(label, callback_data=f"cart_select_store_{store_num}")])
            buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
            await update.message.reply_text(
                f"📍 *Stores in {city_match}* ({len(stores_in_city)} found)\n\nTap a store to add services:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            return
        # Otherwise try as a store number
        if text.upper() in STORES:
            # Show ad type selection for this store
            await update.message.reply_text(
                f"✅ Store found: {STORES[text.upper()].get('GroceryChain', '?')}\n\n"
                f"Select ad type to add to cart:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📄 Single Ad", callback_data=f"cart_single_{text.upper()}")],
                    [InlineKeyboardButton("📋 Double Ad", callback_data=f"cart_double_{text.upper()}")],
                    [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")],
                ])
            )
            return
        else:
            await update.message.reply_text(
                "❌ Store not found. Try:\n"
                "• Store number (e.g., FME07Z-0236)\n"
                "• City name (e.g., Portland)",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]])
            )
            return
    
    # Handle rates lookup if awaiting
    if context.user_data.get(AWAITING_RATES):
        context.user_data[AWAITING_RATES] = False
        # Check if it's a city name first
        city_match = text.strip().title()
        if city_match in CITY_INDEX:
            # Show stores in that city with rates buttons
            stores_in_city = CITY_INDEX[city_match]
            buttons = []
            for store in stores_in_city:
                store_num = store["StoreName"]
                chain = store.get("GroceryChain", "")
                street = store.get("Address", "").split(",")[0] if store.get("Address") else ""
                street = street.strip()[:20]
                label = f"💰 {store_num} — {chain} {street}"
                buttons.append([InlineKeyboardButton(label, callback_data=f"action_rates_{store_num}")])
            buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="rates_search")])
            await update.message.reply_text(
                f"📍 *Stores in {city_match}* ({len(stores_in_city)} found)\n\nTap a store to see rates:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            return
        # Otherwise try as a store number
        await do_rates_lookup(update, text)
        return
    
    # Handle ROI calculator if awaiting
    # Conversational ROI Calculator Flow
    if context.user_data.get(AWAITING_ROI_ADPRICE):
        # Step 1: Ad price entered
        context.user_data[AWAITING_ROI_ADPRICE] = False
        try:
            value = float(text.replace('$', '').replace(',', '').strip())
            if value < 1 or value > 100000:
                raise ValueError()
            context.user_data['roi_adprice'] = value
            context.user_data[AWAITING_ROI_REDEMPTIONS] = True
            await update.message.reply_text(
                f"✅ Ad Price: ${value:,.2f}/year\n\n"
                f"*Step 2:* How many redemptions per month?\n\n"
                f"_Example: 20 or 50_",
                parse_mode="Markdown"
            )
        except:
            await update.message.reply_text(
                f"❌ Please enter a valid dollar amount (1-100000).\n\n_Example: 3000_",
                parse_mode="Markdown"
            )
            context.user_data[AWAITING_ROI_ADPRICE] = True
        return
    
    if context.user_data.get(AWAITING_ROI_REDEMPTIONS):
        # Step 2: Redemptions entered
        context.user_data[AWAITING_ROI_REDEMPTIONS] = False
        try:
            value = int(text.replace(',', '').strip())
            if value < 1 or value > 1000:
                raise ValueError()
            context.user_data['roi_redemptions'] = value
            context.user_data[AWAITING_ROI_TICKET] = True
            await update.message.reply_text(
                f"✅ Redemptions: {value}/mo\n\n"
                f"*Step 3:* What's the average ticket size?\n\n"
                f"_Example: 35 or 75_",
                parse_mode="Markdown"
            )
        except:
            await update.message.reply_text(
                f"❌ Please enter a valid number (1-1000).\n\n_Example: 20_",
                parse_mode="Markdown"
            )
            context.user_data[AWAITING_ROI_REDEMPTIONS] = True
        return
    
    if context.user_data.get(AWAITING_ROI_TICKET):
        # Step 3: Ticket size entered
        context.user_data[AWAITING_ROI_TICKET] = False
        try:
            value = float(text.replace('$', '').replace(',', '').strip())
            if value < 1 or value > 10000:
                raise ValueError()
            context.user_data['roi_ticket'] = value
            context.user_data[AWAITING_ROI_COUPON] = True
            await update.message.reply_text(
                f"✅ Avg Ticket: ${value:.2f}\n\n"
                f"*Step 4:* What's the coupon discount amount?\n\n"
                f"_Example: 5 or 10_",
                parse_mode="Markdown"
            )
        except:
            await update.message.reply_text(
                f"❌ Please enter a valid dollar amount (1-10000).\n\n_Example: 35_",
                parse_mode="Markdown"
            )
            context.user_data[AWAITING_ROI_TICKET] = True
        return
    
    if context.user_data.get(AWAITING_ROI_COUPON):
        # Step 4: Coupon entered
        context.user_data[AWAITING_ROI_COUPON] = False
        try:
            value = float(text.replace('$', '').replace(',', '').strip())
            if value < 0 or value > 100:
                raise ValueError()
            context.user_data['roi_coupon'] = value
            context.user_data[AWAITING_ROI_COGS] = True
            await update.message.reply_text(
                f"✅ Coupon: ${value:.2f}\n\n"
                f"*Step 5:* What's your COGS percentage?\n\n"
                f"_Example: 30 or 40_",
                parse_mode="Markdown"
            )
        except:
            await update.message.reply_text(
                f"❌ Please enter a valid dollar amount (0-100).\n\n_Example: 10_",
                parse_mode="Markdown"
            )
            context.user_data[AWAITING_ROI_COUPON] = True
        return
    
    if context.user_data.get(AWAITING_ROI_COGS):
        # Step 5: COGS entered - now calculate and show results
        context.user_data[AWAITING_ROI_COGS] = False
        try:
            value = float(text.replace('%', '').replace(',', '').strip())
            if value < 0 or value > 100:
                raise ValueError()
            context.user_data['roi_cogs'] = value
            
            # Calculate and show results with ad price instead of store lookup
            await show_roi_results_with_adprice(update, context)
        except:
            await update.message.reply_text(
                f"❌ Please enter a valid percentage (0-100).\n\n_Example: 35_",
                parse_mode="Markdown"
            )
            context.user_data[AWAITING_ROI_COGS] = True
        return
    
    # Handle testimonial keyword search if awaiting
    if context.user_data.get(AWAITING_KEYWORD):
        context.user_data[AWAITING_KEYWORD] = False
        await do_testimonial_search(update, text, context)
        return
    
    # Handle audit inventory entry if awaiting
    if context.user_data.get(AWAITING_AUDIT_INVENTORY):
        context.user_data[AWAITING_AUDIT_INVENTORY] = False
        parts = text.split()
        
        if len(parts) != 2:
            await update.message.reply_text(
                "❌ Invalid format. Please send:\n`CASES ROLLS`\n\n_Example: `15 25`_",
                parse_mode="Markdown"
            )
            context.user_data[AWAITING_AUDIT_INVENTORY] = True
            return
        
        try:
            current_cases = int(parts[0])
            current_rolls = int(parts[1])
            
            if not (0 <= current_cases <= 50) or not (0 <= current_rolls <= 49):
                raise ValueError("Invalid range")
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid numbers. Cases: 0-50, Rolls: 0-49",
                parse_mode="Markdown"
            )
            context.user_data[AWAITING_AUDIT_INVENTORY] = True
            return
        
        # Get audit info
        audit_info = context.user_data.get('audit_info', {})
        store_num = audit_info.get('store_num', '?')
        starting_cases = audit_info.get('starting_cases', 20)
        delivery_date = audit_info.get('delivery_date', datetime.now())
        cycle = audit_info.get('cycle', '?')
        
        # Calculate metrics
        total_rolls = (current_cases * 50) + current_rolls
        days_until_runout = calculate_days_until_runout(total_rolls)
        
        # Get next delivery date
        next_delivery = get_next_delivery_date(cycle)
        days_until_delivery = (next_delivery - datetime.now()).days
        
        # Check if alert needed
        alert = days_until_runout < days_until_delivery
        
        # Build report
        report = f"📊 *Audit Report*\n\n"
        report += f"*{store_num}*\n"
        report += f"{STORES[store_num].get('GroceryChain', '?')} - {STORES[store_num].get('City', '')}, {STORES[store_num].get('State', '')}\n\n"
        report += f"📦 *Delivery:*\n"
        report += f"Date: {delivery_date.strftime('%B %d, %Y')}\n"
        starting_rolls = starting_cases * 50
        report += f"Starting: {starting_cases} cases ({starting_rolls:,} rolls)\n\n"
        report += f"📋 *Current Inventory:*\n"
        report += f"{current_cases} cases + {current_rolls} rolls = {total_rolls} total rolls\n\n"
        report += f"📅 *Projection:*\n"
        report += f"Days until runout: {days_until_runout:.1f}\n"
        report += f"Next delivery: {next_delivery.strftime('%B %d, %Y')} ({days_until_delivery} days)\n\n"
        
        if alert:
            report += f"⚠️ *ALERT:* Inventory runs out before next delivery!\n"
        else:
            report += f"✅ Inventory sufficient until next delivery\n"
        
        buttons = [
            [InlineKeyboardButton("📧 Send Report", callback_data="audit_send_report")],
            [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")],
        ]
        
        # Store the calculated values for sending
        context.user_data['audit_report'] = {
            'store_num': store_num,
            'starting_cases': starting_cases,
            'current_cases': current_cases,
            'current_rolls': current_rolls,
            'delivery_date': delivery_date,
            'next_delivery': next_delivery,
            'days_until_delivery': days_until_delivery,
            'alert': alert,
        }
        
        await update.message.reply_text(report, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        return
    
    # Handle audit store selection if in audit mode
    if context.user_data.get(AWAITING_AUDIT_STORE):
        context.user_data[AWAITING_AUDIT_STORE] = False
        text_upper = text.upper()
        
        # Check if it's a zone code (e.g., "07Z", "05X")
        if len(text_upper) <= 4 and text_upper.replace(' ', '') and SHIPPING_DATA_AVAILABLE:
            zone_code = text_upper.replace(' ', '')
            summary = get_zone_summary(zone=zone_code)
            if summary['total_stores'] > 0:
                report = format_zone_report(zone_code)
                buttons = [[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]]
                await update.message.reply_text(report, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
                return
        
        if text_upper not in STORES:
            # Silently ignore invalid store codes during audit
            return
        
        store = STORES[text_upper]
        cycle = store.get('Cycle', '?')
        starting_cases = store.get('Case Count', 20)
        
        # Use real shipping data if available
        if SHIPPING_DATA_AVAILABLE:
            status = get_delivery_status(text_upper)
            
            # Build rich audit card with real data
            msg = f"🏪 *Audit: {text_upper}*\n\n"
            msg += f"{store.get('GroceryChain', '?')} - {store.get('City', '')}, {store.get('State', '')}\n"
            if status.get('delivery_address'):
                msg += f"📍 {status['delivery_address']}\n"
            msg += f"🔄 Cycle: {cycle}\n\n"
            
            # Delivery status
            msg += f"📦 *Delivery Status:*\n"
            if status['last_delivery_date']:
                date_str = status['last_delivery_date'].strftime('%B %d, %Y')
                msg += f"{status['status_emoji']} Last delivery: *{date_str}*\n"
                msg += f"⏱ {status['days_since_delivery']} days ago\n"
            else:
                msg += f"❓ No delivery records found\n"
            
            if status['in_transit']:
                msg += f"\n🚚 *In Transit:* {status['in_transit_count']} shipment(s)\n"
                for t in status['in_transit_tracking']:
                    ship_date = t['ship_date'][:10] if t['ship_date'] else '?'
                    msg += f"  Shipped: {ship_date}\n"
            
            msg += f"\n📊 *Status:* {status['status_text']}\n"
            msg += f"\n📦 Case count on file: *{starting_cases} cases*\n"
            msg += f"\nEnter current inventory (rolls remaining):"
            
            # Build buttons
            buttons = []
            # UPS tracking buttons
            if status.get('tracking_url'):
                buttons.append([InlineKeyboardButton("📦 Track Last Delivery", url=status['tracking_url'])])
            for t in status.get('in_transit_tracking', []):
                buttons.append([InlineKeyboardButton(f"🚚 Track In-Transit ({t['ship_date'][:10]})", url=t['url'])])
            buttons.append([InlineKeyboardButton("⬅️ Cancel", callback_data="main_menu")])
            
            # Store audit info
            delivery_date = status['last_delivery_date'] or datetime.now()
            context.user_data['audit_info'] = {
                'store_num': text_upper,
                'cycle': cycle,
                'delivery_date': delivery_date,
                'starting_cases': starting_cases,
                'shipping_status': status,
            }
            context.user_data[AWAITING_AUDIT_INVENTORY] = True
            
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
            return
        
        # Fallback: old cycle-based logic if shipping data not available
        get_delivery_func = get_cycle_delivery_dates()
        delivery_date = get_delivery_func(cycle)
        
        # Store audit info for next step
        context.user_data['audit_info'] = {
            'store_num': text_upper,
            'cycle': cycle,
            'delivery_date': delivery_date,
            'starting_cases': starting_cases,
        }
        
        # Ask for delivery confirmation
        msg = f"🏪 *Audit: {text_upper}*\n\n"
        msg += f"{store.get('GroceryChain', '?')} - {store.get('City', '')}, {store.get('State', '')}\n\n"
        msg += f"📦 *Delivery Confirmation:*\n\n"
        msg += f"_{text_upper}_ was sent *{starting_cases} cases* on *{delivery_date.strftime('%B %d, %Y')}*\n\n"
        msg += f"Is this correct?"
        
        buttons = [
            [InlineKeyboardButton("✅ Yes, Correct", callback_data="audit_confirm_yes")],
            [InlineKeyboardButton("❌ No, Adjust", callback_data="audit_confirm_no")],
            [InlineKeyboardButton("⬅️ Cancel", callback_data="main_menu")],
        ]
        
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        return
    
    # Handle testimonial form fields
    if context.user_data.get(AWAITING_TEST_NAME):
        context.user_data[AWAITING_TEST_NAME] = False
        context.user_data['testimonial_form']['name'] = text.strip()
        context.user_data[AWAITING_TEST_BUSINESS] = True
        await update.message.reply_text(
            "✅ Name saved.\n\n*Step 2:* What is the business name?",
            parse_mode="Markdown"
        )
        return
    
    if context.user_data.get(AWAITING_TEST_BUSINESS):
        context.user_data[AWAITING_TEST_BUSINESS] = False
        context.user_data['testimonial_form']['business'] = text.strip()
        context.user_data[AWAITING_TEST_ADDRESS] = True
        await update.message.reply_text(
            "✅ Business saved.\n\n*Step 3:* What is the business address?",
            parse_mode="Markdown"
        )
        return
    
    if context.user_data.get(AWAITING_TEST_ADDRESS):
        context.user_data[AWAITING_TEST_ADDRESS] = False
        context.user_data['testimonial_form']['address'] = text.strip()
        context.user_data[AWAITING_TEST_PHONE] = True
        await update.message.reply_text(
            "✅ Address saved.\n\n*Step 4:* What is the phone number?",
            parse_mode="Markdown"
        )
        return
    
    if context.user_data.get(AWAITING_TEST_PHONE):
        context.user_data[AWAITING_TEST_PHONE] = False
        context.user_data['testimonial_form']['phone'] = text.strip()
        context.user_data[AWAITING_TEST_CHAIN] = True
        await update.message.reply_text(
            "✅ Phone saved.\n\n*Step 5:* What is the grocery chain? (e.g., Kroger, Safeway, Fred Meyer)",
            parse_mode="Markdown"
        )
        return
    
    if context.user_data.get(AWAITING_TEST_CHAIN):
        context.user_data[AWAITING_TEST_CHAIN] = False
        context.user_data['testimonial_form']['grocery_chain'] = text.strip()
        context.user_data[AWAITING_TEST_ZONE] = True
        await update.message.reply_text(
            "✅ Chain saved.\n\n*Step 6:* What is the zone? (e.g., 07Z, 05X)",
            parse_mode="Markdown"
        )
        return
    
    if context.user_data.get(AWAITING_TEST_ZONE):
        context.user_data[AWAITING_TEST_ZONE] = False
        context.user_data['testimonial_form']['zone'] = text.strip()
        context.user_data[AWAITING_TEST_STORE] = True
        await update.message.reply_text(
            "✅ Zone saved.\n\n*Step 7:* What is the store number? (e.g., 0206)",
            parse_mode="Markdown"
        )
        return
    
    if context.user_data.get(AWAITING_TEST_STORE):
        context.user_data[AWAITING_TEST_STORE] = False
        context.user_data['testimonial_form']['store_number'] = text.strip()
        context.user_data[AWAITING_TEST_COUPONS] = True
        await update.message.reply_text(
            "✅ Store number saved.\n\n*Step 8:* How many coupons per week? (just the number, e.g., 15)",
            parse_mode="Markdown"
        )
        return
    
    if context.user_data.get(AWAITING_TEST_COUPONS):
        context.user_data[AWAITING_TEST_COUPONS] = False
        try:
            count = int(text.strip())
            if count < 0:
                raise ValueError()
            context.user_data['testimonial_form']['coupons_count'] = count
            context.user_data['testimonial_form']['coupons_frequency'] = 'week'
            context.user_data[AWAITING_TEST_TICKET] = True
            await update.message.reply_text(
                f"✅ Coupons: {count}/week saved.\n\n*Step 9:* What is your average ticket price? (e.g., 45 or 75.50)",
                parse_mode="Markdown"
            )
        except ValueError:
            await update.message.reply_text(
                "❌ Please enter a valid number.",
                parse_mode="Markdown"
            )
            context.user_data[AWAITING_TEST_COUPONS] = True
        return
    
    if context.user_data.get(AWAITING_TEST_TICKET):
        context.user_data[AWAITING_TEST_TICKET] = False
        try:
            price = float(text.strip().replace('$', ''))
            context.user_data['testimonial_form']['ticket_price'] = f"{price:.2f}"
            context.user_data[AWAITING_TEST_ROI] = True
            
            # Show ROI rating buttons
            buttons = [
                [InlineKeyboardButton("🔥 EXCELLENT", callback_data="test_roi_excellent")],
                [InlineKeyboardButton("⭐ GOOD", callback_data="test_roi_good")],
                [InlineKeyboardButton("👀 FAIR", callback_data="test_roi_fair")],
                [InlineKeyboardButton("😞 POOR", callback_data="test_roi_poor")],
            ]
            await update.message.reply_text(
                f"✅ Ticket price: ${price:.2f} saved.\n\n*Step 10:* How would you rate the ROI?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except ValueError:
            await update.message.reply_text(
                "❌ Please enter a valid price (e.g., 45 or 75.50).",
                parse_mode="Markdown"
            )
            context.user_data[AWAITING_TEST_TICKET] = True
        return
    
    if context.user_data.get(AWAITING_TEST_DURATION):
        context.user_data[AWAITING_TEST_DURATION] = False
        context.user_data['testimonial_form']['duration'] = text.strip()
        context.user_data[AWAITING_TEST_RENEW] = True
        
        # Show renew buttons
        buttons = [
            [InlineKeyboardButton("✅ YES", callback_data="test_renew_yes")],
            [InlineKeyboardButton("❌ NO", callback_data="test_renew_no")],
        ]
        await update.message.reply_text(
            f"✅ Duration: {text.strip()} saved.\n\n*Step 12:* Would you renew this advertising program?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
    
    if context.user_data.get(AWAITING_TEST_COMMENTS):
        context.user_data[AWAITING_TEST_COMMENTS] = False
        context.user_data['testimonial_form']['comments'] = text.strip()
        context.user_data[AWAITING_TEST_COUPON_IMAGE] = True
        
        await update.message.reply_text(
            f"✅ Comments saved.\n\n*Step 15:* Now, please attach a photo of a coupon sample.",
            parse_mode="Markdown"
        )
        return
    
    if context.user_data.get(AWAITING_TEST_COUPON_IMAGE):
        await update.message.reply_text(
            "⚠️ Please attach an image of the coupon. Use the attachment button or send a photo.",
            parse_mode="Markdown"
        )
        return
    
    # Check if it's a store number (contains a dash)
    if '-' in text.upper():
        # Store number format: ABC12Z-0123
        text_upper = text.upper()
        if text_upper not in STORES:
            # Silently ignore invalid store codes (don't clutter chat)
            return
        
        # Set store and show action menu
        context.user_data['selected_store'] = text_upper
        store = STORES[text_upper]
        await show_store_action_menu(update.effective_chat, text_upper, store, context=context)
    else:
        # Treat as city name
        city_query = text.title()
        
        # Find matching cities
        matching_cities = [c for c in CITIES_SORTED if city_query.lower() in c.lower()]
        
        if not matching_cities:
            # Silently ignore invalid city queries
            return
        
        if len(matching_cities) == 1:
            # If only one match, show stores directly
            await show_city_stores(update, context, matching_cities[0])
        else:
            # If multiple matches, let user pick
            await show_city_options(update, context, matching_cities)


async def show_city_options(update: Update, context: ContextTypes.DEFAULT_TYPE, cities: List[str]):
    """Show multiple matching cities."""
    buttons = []
    for city in cities[:20]:  # Limit to 20 for UI
        buttons.append([InlineKeyboardButton(city, callback_data=f"city_{city}")])
    
    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        "🔍 Found multiple cities. Which one?",
        reply_markup=keyboard
    )


async def show_city_stores(update: Update, context: ContextTypes.DEFAULT_TYPE, city: str, edit_message: bool = False):
    """Show all stores in a city."""
    if city not in CITY_INDEX:
        error_msg = f"❌ City `{city}` not found."
        if edit_message:
            await update.callback_query.edit_message_text(error_msg, parse_mode="Markdown")
        else:
            await update.message.reply_text(error_msg, parse_mode="Markdown")
        return
    
    stores_in_city = CITY_INDEX[city]
    
    # Create buttons for each store with cycle and case count info
    buttons = []
    for store in stores_in_city:
        store_num = store["StoreName"]
        chain = store.get("GroceryChain", "")
        cycle = get_store_cycle(store)
        case_count = store.get("Case Count", "?")
        
        # Button label: "STORE# (Cycle, Cases) - Street"
        street = store.get("Address", "").split(",")[0] if store.get("Address") else "N/A"
        street = street.strip()[:20]  # Truncate long street names
        label = f"{store_num} ({cycle}, {case_count} cases) - {street}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"select_store_{store_num}")])
    
    keyboard = InlineKeyboardMarkup(buttons)
    text = f"📍 *Stores in {city}* ({len(stores_in_city)} found)"
    
    if edit_message:
        # Edit the existing message (from callback)
        await update.callback_query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        # Send new message (from initial query)
        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )


def build_category_keyboard(store_num: str = None):
    """Build the category selection keyboard with back button."""
    buttons = []
    category_list = list(CATEGORIES.keys())
    for i in range(0, len(category_list), 2):
        row = []
        for j in range(2):
            if i + j < len(category_list):
                cat = category_list[i + j]
                row.append(InlineKeyboardButton(cat, callback_data=f"cat_{cat}"))
        buttons.append(row)
    
    # Add back button
    if store_num:
        buttons.append([InlineKeyboardButton("🏪 Back to Store", callback_data=f"select_store_{store_num}")])
    buttons.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def build_subcategory_keyboard(category: str):
    """Build the subcategory keyboard with a back button."""
    subcats = CATEGORIES.get(category, {})
    buttons = []
    subcat_list = list(subcats.keys())
    # 2 per row for readability
    for i in range(0, len(subcat_list), 2):
        row = []
        for j in range(2):
            if i + j < len(subcat_list):
                subcat = subcat_list[i + j]
                # Telegram callback_data max is 64 bytes — truncate if needed
                cb_data = f"subcat_{subcat}"[:64]
                row.append(InlineKeyboardButton(subcat, callback_data=cb_data))
        buttons.append(row)
    # Back button
    buttons.append([InlineKeyboardButton("⬅️ Back to Categories", callback_data="back_categories")])
    return InlineKeyboardMarkup(buttons)


async def send_category_menu(chat, context, edit_message=None):
    """Send or edit message to show category menu."""
    keyboard = build_category_keyboard()
    text = "📂 *Select a category:*"
    if edit_message:
        await edit_message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await chat.send_message(text, parse_mode="Markdown", reply_markup=keyboard)


async def handle_back_to_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to category menu."""
    query = update.callback_query
    await query.answer()
    
    # Get base category buttons
    buttons = []
    category_list = list(CATEGORIES.keys())
    for i in range(0, len(category_list), 2):
        row = []
        for j in range(2):
            if i + j < len(category_list):
                cat = category_list[i + j]
                row.append(InlineKeyboardButton(cat, callback_data=f"cat_{cat}"))
        buttons.append(row)
    
    # Add back to store if available
    store_num = context.user_data.get('selected_store', '')
    if store_num:
        buttons.append([InlineKeyboardButton("🏪 Back to Store", callback_data=f"select_store_{store_num}")])
    
    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(
        "📂 *Select a category:*",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def handle_category_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category selection and show subcategories."""
    query = update.callback_query
    category = query.data.replace("cat_", "")
    
    logger.info(f"Category selected: {category}")
    
    # Store category in context
    context.user_data['selected_category'] = category
    
    await query.answer()
    
    # Get the base keyboard
    subcats = CATEGORIES.get(category, {})
    buttons = []
    subcat_list = list(subcats.keys())
    for i in range(0, len(subcat_list), 2):
        row = []
        for j in range(2):
            if i + j < len(subcat_list):
                subcat = subcat_list[i + j]
                cb_data = f"subcat_{subcat}"[:64]
                row.append(InlineKeyboardButton(subcat, callback_data=cb_data))
        buttons.append(row)
    
    # Add back buttons
    buttons.append([InlineKeyboardButton("⬅️ Back to Categories", callback_data="back_categories")])
    
    # Add back to store if available
    store_num = context.user_data.get('selected_store', '')
    if store_num:
        buttons.append([InlineKeyboardButton("🏪 Back to Store", callback_data=f"select_store_{store_num}")])
    
    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(
        f"*{category}*\n\nSelect subcategory:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def handle_subcategory_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subcategory selection and run prospect search."""
    query = update.callback_query
    subcat = query.data.replace("subcat_", "")
    
    logger.info(f"Subcategory selected: {subcat}")
    
    await query.answer("🔍 Finding prospects...", show_alert=False)
    
    store_number = context.user_data.get('selected_store')
    category = context.user_data.get('selected_category')
    
    if not store_number:
        await query.edit_message_text("❌ Store not found in session. Start over with /start")
        return
    
    try:
        # Import and run prospecting tool with specific category
        import os
        from pathlib import Path
        from dotenv import load_dotenv
        
        workspace = Path(__file__).parent.parent
        load_dotenv(workspace / ".env", override=True)
        load_dotenv(workspace / ".env.local", override=True)
        
        api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if not api_key:
            raise ValueError("API key not found")
        
        import sys
        sys.path.insert(0, str(workspace / "scripts"))
        from prospecting_tool_enhanced import ProspectingToolEnhanced
        
        tool = ProspectingToolEnhanced()
        
        # Get the actual category keyword for API query
        category_name = category.split(" ")[1] if " " in category else category
        
        # Get the selected subcategory's config
        selected_category_data = CATEGORIES.get(category, {})
        subcat_config = selected_category_data.get(subcat, {"types": ["restaurant"], "keyword": "", "exclude": []})
        
        # Parse config — dict with types/keyword/exclude
        if isinstance(subcat_config, dict):
            google_types = subcat_config.get("types", [])
            search_keyword = subcat_config.get("keyword", "") or None
            exclude_terms = subcat_config.get("exclude", [])
        else:
            # Fallback for simple list format
            google_types = subcat_config
            search_keyword = None
            exclude_terms = []
        
        logger.info(f"🔍 Querying {store_number} | subcategory: {subcat} | types: {google_types} | keyword: {search_keyword}")
        
        # Run prospecting with resilient engine (cache → Google → Free API → offline cache)
        prospects = []
        source_info = ""
        try:
            from resilient_prospecting import search_with_resilience
            from google_places_wrapper import search_google_places
            
            store = STORES.get(store_number)
            store_address = f"{store.get('Address', '')}, {store.get('City', '')}, {store.get('State', '')} {store.get('ZIP', '')}"
            
            # Create a wrapper function for Google Places
            def google_places_search(store_num, category, limit):
                """Wrapper to pass to resilient engine."""
                return search_google_places(store_address, category, limit)
            
            # Search with full fallback chain
            prospects, source_info = search_with_resilience(
                store_number=store_number,
                store_address=store_address,
                category=subcat.lower(),
                google_places_func=google_places_search,  # Now configured!
                limit=10
            )
        except Exception as e:
            logger.error(f"❌ Resilient engine error: {e}", exc_info=True)
            store = STORES.get(store_number)
            source_info = f"⚠️ Search failed ({str(e)[:30]})"
        
        if not prospects:
            await query.edit_message_text(f"⚠️ No prospects found with this filter.\n\n{source_info}\n\nTry a different category or store.")
            return
        
        store = STORES.get(store_number)
        
        # Format header with source info
        header = f"🎯 *{subcat}*\n📍 {store['GroceryChain']} | {store['City']}, {store['State']}\n📦 Store: {store_number}\n{source_info}\n*Found {len(prospects)} prospects:*\n"
        await query.edit_message_text(header, parse_mode="Markdown")
        
        # Track this search
        rep_id = get_rep_id(update)
        data_obj = load_prospect_data()
        if rep_id not in data_obj["reps"]:
            data_obj["reps"][rep_id] = {
                "name": get_rep_name(update),
                "saved_prospects": {},
                "search_history": [],
                "contact_history": {},
                "session_searches": 0,
                "session_bookmarks": 0,
            }
        data_obj["reps"][rep_id]["session_searches"] += 1
        save_prospect_data(data_obj)
        
        # Send each prospect with full info in one message
        await send_prospects_with_full_info(update, prospects, store, context)
        
        # Navigation buttons after results
        category = context.user_data.get('selected_category', '')
        store_num = context.user_data.get('selected_store', '')
        nav_buttons = [
            [InlineKeyboardButton(f"⬅️ Back to {category.split(' ', 1)[-1] if ' ' in category else category}", callback_data=f"cat_{category}")],
            [InlineKeyboardButton("📂 All Categories", callback_data="back_categories")],
        ]
        if store_num:
            nav_buttons.append([InlineKeyboardButton("🏪 Back to Store", callback_data=f"select_store_{store_num}")])
        nav_buttons.append([InlineKeyboardButton("🔄 New Store Search", callback_data="new_search")])
        await update.effective_chat.send_message(
            "━━━━━━━━━━━━━━━━━━━━",
            reply_markup=InlineKeyboardMarkup(nav_buttons)
        )
        
        logger.info(f"✅ Sent {len(prospects)} prospects")
        
    except Exception as e:
        logger.error(f"❌ Prospect search error: {e}", exc_info=True)
        
        # Graceful error handling
        error_msg = str(e)[:60]
        display_msg = f"⚠️ Couldn't find prospects for this category.\n\nError: {error_msg}\n\nTry another category or store."
        
        # Add back button
        category = context.user_data.get('selected_category', '')
        back_button = InlineKeyboardButton(f"⬅️ Back to {category.split(' ', 1)[-1] if ' ' in category else category}", callback_data=f"cat_{category}") if category else InlineKeyboardButton("⬅️ Back", callback_data="back_categories")
        
        buttons = [
            [back_button],
            [InlineKeyboardButton("📂 All Categories", callback_data="back_categories")],
            [InlineKeyboardButton("🔄 New Search", callback_data="new_search")],
        ]
        
        await query.edit_message_text(display_msg, reply_markup=InlineKeyboardMarkup(buttons))


async def send_prospects_with_full_info(update: Update, prospects: List[Dict], store: Dict, context: ContextTypes.DEFAULT_TYPE = None):
    """Send each prospect once with full info + buttons in one message."""
    
    for i, prospect in enumerate(prospects, 1):
        business_name = prospect.get("name", "Unknown")
        address = prospect.get("address", "")
        phone = prospect.get("phone", "")
        distance = prospect.get('distance_miles', 'N/A')
        score = prospect.get('likelihood_score', 0)
        website = prospect.get("website", "")
        
        # Emoji rating
        if score >= 80:
            emoji = "🔥"
        elif score >= 70:
            emoji = "⭐"
        else:
            emoji = "👀"
        
        # Build complete message with all info
        text = f"{emoji} *{business_name}*\n"
        
        # Score and rating on same line
        info_line = ""
        if score and score > 0:
            info_line += f"📊 Likelihood: {score}/100"
        if rating_val := prospect.get('rating'):
            stars = "⭐" * min(5, round(rating_val))
            if info_line:
                info_line += f"  |  {stars} {rating_val}/5"
            else:
                info_line += f"{stars} {rating_val}/5"
        if info_line:
            text += info_line + "\n"
        
        # Distance from store
        if distance and distance != 'N/A':
            text += f"📏 {distance} mi from store\n"
        
        # Phone (Telegram auto-links phone numbers)
        if phone:
            text += f"📞 {phone}\n"
        
        # Address
        if address:
            text += f"📍 {address}\n"
        
        # Website link
        if website:
            web_url = website if website.startswith("http") else f"https://{website}"
            text += f"🌐 [Website]({web_url})\n"
        
        # Advertising signals
        advertising_signals = prospect.get('advertising_signal', {})
        if advertising_signals:
            platforms = []
            if advertising_signals.get('greet_magazine'):
                platforms.append("📰 Greet")
            if advertising_signals.get('facebook_ads'):
                platforms.append("📘 Facebook")
            if advertising_signals.get('google_local_services'):
                platforms.append("🔍 Google Local")
            if advertising_signals.get('groupon'):
                platforms.append("🎁 Groupon")
            if advertising_signals.get('found_advertising'):
                platforms.append("📢 Active Ads")
            
            if platforms:
                text += f"💡 *Advertising on:* {' | '.join(platforms)}\n"
        
        # Build URLs for buttons
        mappoint_url = f"https://sales.indoormedia.com/Mappoint?business={urllib.parse.quote(business_name)}&address={urllib.parse.quote(address)}"
        google_maps_url = f"https://www.google.com/maps/search/{urllib.parse.quote(address)}"
        
        # Create a safe callback ID for this prospect (use hash of name + address)
        prospect_id = hashlib.md5(f"{business_name}{address}".encode()).hexdigest()[:12]
        
        # Buttons - quick actions + expand
        buttons = []
        
        # Website button (if available)
        if website:
            web_url = website if website.startswith("http") else f"https://{website}"
            buttons.append([InlineKeyboardButton("🌐 Website", url=web_url)])
        
        # Maps row
        buttons.append([
            InlineKeyboardButton("📍 Maps", url=google_maps_url),
            InlineKeyboardButton("🗺️ Mappoint", url=mappoint_url),
        ])
        
        # Expand for more actions
        buttons.append([
            InlineKeyboardButton("▶️ Show Actions", callback_data=f"expand_{prospect_id}"),
        ])
        
        # Store prospect info for callback handlers
        if context:
            if 'prospects' not in context.user_data:
                context.user_data['prospects'] = {}
            context.user_data['prospects'][prospect_id] = {
                'name': business_name,
                'address': address,
                'phone': phone,
                'store': store.get('StoreName', ''),
                'store_dict': store,
                'website': website,
                'distance_miles': distance,
                'likelihood_score': score,
                'advertising_signal': advertising_signals,
                'rating': prospect.get('rating', 0),
                'user_ratings_total': prospect.get('user_ratings_total', 0),
                'opening_hours': prospect.get('opening_hours'),
                'place_id': prospect.get('place_id', ''),
                'category': prospect.get('category', '') or context.user_data.get('selected_category', '') or context.user_data.get('selected_subcat', ''),
                'email': prospect.get('email', ''),
                'contact_name': prospect.get('contact_name', ''),
            }
        
        await update.effective_chat.send_message(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )


# --- Testimonial Search ---
TESTIMONIALS_CACHE = WORKSPACE / "data" / "testimonials_cache.json"

def load_testimonials():
    """Load testimonials from cache."""
    if TESTIMONIALS_CACHE.exists():
        with open(TESTIMONIALS_CACHE) as f:
            return json.load(f)
    return []

def expand_search_keywords(keyword):
    """Expand a keyword to include related cuisine/category terms.
    
    Examples:
    - 'Ramen' → ['ramen', 'sushi', 'teriyaki', 'japanese', 'asian']
    - 'Pizza' → ['pizza', 'italian', 'restaurant', 'casual dining']
    - 'Salon' → ['salon', 'hair', 'nails', 'spa', 'beauty']
    """
    keyword_lower = keyword.lower()
    
    # Cuisine/category expansions
    expansions = {
        # Asian cuisines
        'ramen': ['ramen', 'sushi', 'teriyaki', 'japanese', 'asian', 'noodles'],
        'sushi': ['sushi', 'ramen', 'teriyaki', 'japanese', 'asian', 'rolls'],
        'teriyaki': ['teriyaki', 'sushi', 'ramen', 'japanese', 'asian'],
        'japanese': ['japanese', 'sushi', 'ramen', 'teriyaki', 'asian'],
        'asian': ['asian', 'japanese', 'chinese', 'thai', 'vietnamese', 'korean'],
        'chinese': ['chinese', 'asian', 'dim sum', 'noodles'],
        'thai': ['thai', 'asian', 'restaurant'],
        'vietnamese': ['vietnamese', 'asian', 'pho'],
        'korean': ['korean', 'bbq', 'asian'],
        
        # Italian
        'pizza': ['pizza', 'italian', 'pasta', 'restaurant'],
        'italian': ['italian', 'pizza', 'pasta', 'casual dining'],
        'pasta': ['pasta', 'italian', 'restaurant'],
        
        # Mexican
        'mexican': ['mexican', 'taco', 'burrito', 'restaurant'],
        'taco': ['taco', 'mexican', 'restaurant'],
        
        # Beauty/Salon
        'salon': ['salon', 'hair', 'nails', 'spa', 'beauty'],
        'hair': ['hair', 'salon', 'nails', 'beauty'],
        'nails': ['nails', 'salon', 'hair', 'spa', 'beauty'],
        'spa': ['spa', 'salon', 'massage', 'wellness'],
        'beauty': ['beauty', 'salon', 'hair', 'nails', 'spa'],
        
        # Health/Fitness
        'gym': ['gym', 'fitness', 'health', 'workout'],
        'fitness': ['fitness', 'gym', 'health', 'wellness'],
        'yoga': ['yoga', 'fitness', 'health', 'wellness'],
        
        # Auto
        'auto': ['auto', 'car', 'mechanic', 'repair'],
        'car wash': ['car wash', 'detailing', 'auto'],
        'mechanic': ['mechanic', 'auto', 'repair', 'car service'],
        
        # Dental
        'dental': ['dental', 'dentist', 'orthodontics', 'teeth'],
        'dentist': ['dentist', 'dental', 'orthodontics'],
        
        # Coffee
        'coffee': ['coffee', 'cafe', 'espresso', 'breakfast'],
        'cafe': ['cafe', 'coffee', 'restaurant'],
    }
    
    # Return expanded keywords or just the original if no expansion found
    return expansions.get(keyword_lower, [keyword_lower])


def search_testimonials(keyword):
    """Search testimonials by keyword, including related category terms.
    
    Expands search keywords to find related categories.
    Example: 'Ramen' searches for ramen, sushi, teriyaki, japanese, asian.
    """
    testimonials = load_testimonials()
    keyword_lower = keyword.lower()
    
    # Get expanded keywords
    search_keywords = expand_search_keywords(keyword_lower)
    
    results = []
    seen = set()  # Avoid duplicates
    
    for t in testimonials:
        searchable = t.get('searchable', '').lower()
        # Check if any expanded keyword matches
        for kw in search_keywords:
            if kw in searchable:
                t_id = t.get('id', '')
                if t_id not in seen:
                    results.append(t)
                    seen.add(t_id)
                break
    
    return results

AWAITING_KEYWORD = "awaiting_keyword"


def clear_awaiting_states(context):
    """Clear all AWAITING_* flags from user_data to prevent stale state intercepts."""
    awaiting_keys = [k for k in context.user_data if k.startswith("awaiting_")]
    for k in awaiting_keys:
        context.user_data[k] = False

async def keyword_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /keyword command — search testimonials."""
    # Check if keyword was passed inline: /keyword pizza
    if context.args:
        keyword = " ".join(context.args)
        await do_testimonial_search(update, keyword, context)
    else:
        context.user_data[AWAITING_KEYWORD] = True
        await update.message.reply_text(
            "🔍 *Testimonial Search*\n\nSend a keyword to search testimonials:\n\n"
            "_Examples: pizza, ROI, skeptical, salon, parking lot_",
            parse_mode="Markdown"
        )

def format_testimonial_page(results, keyword, offset=0, page_size=5):
    """Format a page of testimonial results."""
    total = len(results)
    page_results = results[offset:offset + page_size]
    showing_end = min(offset + page_size, total)
    
    header = f"📋 *Found {total} testimonial(s) for \"{keyword}\"*\n"
    header += f"_Showing {offset + 1}–{showing_end}:_\n"
    text = header + "\n"
    
    for i, r in enumerate(page_results, offset + 1):
        business = r.get('business', 'Unknown').replace('&amp;', '&')
        comment = r.get('comment', '')
        url = r.get('url', '').replace('&amp;', '&')
        if len(comment) > 200:
            comment = comment[:200] + "..."
        text += f"*{i}. {business}*\n"
        if comment:
            text += f"📝 _{comment}_\n"
        if url:
            text += f"🔗 [View]({url})\n"
        text += "\n"
    
    # Buttons
    buttons = []
    if showing_end < total:
        buttons.append([InlineKeyboardButton(f"➡️ Next 5 ({showing_end + 1}–{min(showing_end + page_size, total)} of {total})", callback_data=f"tpage_{offset + page_size}")])
    if offset > 0:
        buttons.append([InlineKeyboardButton(f"⬅️ Previous 5", callback_data=f"tpage_{max(offset - page_size, 0)}")])
    buttons.append([InlineKeyboardButton("🔍 Search Again", callback_data="testimonial_search")])
    buttons.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")])
    
    return text, InlineKeyboardMarkup(buttons)


async def do_testimonial_search(update, keyword, context=None):
    """Run testimonial search and format results."""
    results = search_testimonials(keyword)
    
    if not results:
        await update.message.reply_text(
            f"❌ No testimonials found for *\"{keyword}\"*\n\n"
            "Try broader terms: _restaurant, salon, ROI, skeptical, coupon_",
            parse_mode="Markdown"
        )
        return
    
    # Cache results for pagination
    if context:
        context.user_data['testimonial_results'] = results
        context.user_data['testimonial_keyword'] = keyword
    
    text, keyboard = format_testimonial_page(results, keyword, offset=0)
    
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard,
        disable_web_page_preview=True
    )


# --- Store Rates ---
PRODUCTION = 125.0

PRICING_PADDING = 1200  # Default padding for standard rates
PRODUCTION = 125

def calculate_impressions_metrics(case_count: int) -> dict:
    """Calculate impressions and cost metrics based on case count.
    
    Formula:
    - Quarterly = case_count × 50 rolls/case × 137 segments/roll × 2 repetitions
    - Monthly = Quarterly ÷ 3
    - Daily = Monthly ÷ 30
    """
    quarterly = case_count * 50 * 137 * 2
    monthly = quarterly / 3
    daily = monthly / 30
    
    return {
        "quarterly": int(quarterly),
        "monthly": int(monthly),
        "daily": int(daily),
    }

def calculate_pricing_metrics_for_plan(total_contract_amount: float, daily_impressions: int) -> dict:
    """Calculate daily cost and CPM for a pricing plan.
    
    Campaign runs for 12 months regardless of payment plan.
    - Daily Cost = Total Contract Amount ÷ 365
    - CPM = (Daily Cost ÷ Daily Impressions) × 1,000
    """
    daily_cost = total_contract_amount / 365
    cpm = (daily_cost / daily_impressions * 1000) if daily_impressions > 0 else 0
    
    return {
        "daily_cost": daily_cost,
        "cpm": cpm,
    }

def calculate_pricing_all_tiers(store: dict, ad_type: str = "single") -> dict:
    """Calculate pricing for all three tiers with impressions and CPM."""
    base = store["DoubleAd"] if ad_type.lower() == "double" else store["SingleAd"]
    case_count = store.get("Case Count", 0)
    
    # Calculate impressions
    impressions = calculate_impressions_metrics(case_count)
    
    # === TIER 1: DEFAULT (Padded) ===
    padded_base = base + PRICING_PADDING
    padded_monthly_total = padded_base + PRODUCTION
    padded_monthly_per = padded_monthly_total / 12
    padded_metrics = calculate_pricing_metrics_for_plan(padded_monthly_total, impressions["daily"])
    
    # === TIER 2: MANAGER APPROVED CO-OP (Non-padded, full pricing structure) ===
    coop_monthly_total = base + PRODUCTION
    coop_monthly_per = coop_monthly_total / 12
    
    coop_three_total = (base * 0.90) + PRODUCTION
    coop_three_per = coop_three_total / 3
    
    coop_six_total = (base * 0.925) + PRODUCTION
    coop_six_per = coop_six_total / 6
    
    coop_paid_total = (base * 0.85) + PRODUCTION
    
    # Calculate metrics for each coop plan (use actual contract total, not annualized)
    coop_monthly_metrics = calculate_pricing_metrics_for_plan(coop_monthly_total, impressions["daily"])
    coop_three_metrics = calculate_pricing_metrics_for_plan(coop_three_total, impressions["daily"])
    coop_six_metrics = calculate_pricing_metrics_for_plan(coop_six_total, impressions["daily"])
    coop_paid_metrics = calculate_pricing_metrics_for_plan(coop_paid_total, impressions["daily"])
    
    # === TIER 3: EXCLUSIVE CATEGORY (Base = Co-Op monthly total, 5% discount on paid-in-full only) ===
    exclusive_base_total = coop_monthly_total
    exclusive_monthly_per = exclusive_base_total / 12
    exclusive_monthly_total = exclusive_base_total
    
    exclusive_three_total = exclusive_base_total
    exclusive_three_per = exclusive_three_total / 3
    
    exclusive_six_total = exclusive_base_total
    exclusive_six_per = exclusive_six_total / 6
    
    exclusive_paid_total = (exclusive_base_total * 0.95)
    
    # Calculate metrics for exclusive plans (use actual contract total)
    exclusive_monthly_metrics = calculate_pricing_metrics_for_plan(exclusive_monthly_total, impressions["daily"])
    exclusive_three_metrics = calculate_pricing_metrics_for_plan(exclusive_three_total, impressions["daily"])
    exclusive_six_metrics = calculate_pricing_metrics_for_plan(exclusive_six_total, impressions["daily"])
    exclusive_paid_metrics = calculate_pricing_metrics_for_plan(exclusive_paid_total, impressions["daily"])
    
    # === TIER 4: CONTRACTORS (Base = Co-Op monthly total, no discount on 3-month, 5% max on paid-in-full) ===
    contractor_base_total = coop_monthly_total
    contractor_three_total = contractor_base_total
    contractor_three_per = contractor_three_total / 3
    
    contractor_paid_total = (contractor_base_total * 0.95)
    
    # Calculate metrics for contractor plans (use actual contract total)
    contractor_three_metrics = calculate_pricing_metrics_for_plan(contractor_three_total, impressions["daily"])
    contractor_paid_metrics = calculate_pricing_metrics_for_plan(contractor_paid_total, impressions["daily"])
    
    return {
        "store_number": store["StoreName"],
        "store_name": store["GroceryChain"],
        "city": store["City"],
        "state": store["State"],
        "base_price": base,
        "padded_base": padded_base,
        "ad_type": ad_type,
        "case_count": case_count,
        "impressions": impressions,
        "default": {
            "monthly_per": padded_monthly_per,
            "monthly_total": padded_monthly_total,
            "daily_cost": padded_metrics["daily_cost"],
            "cpm": padded_metrics["cpm"],
        },
        "coop": {
            "base_price": coop_monthly_total,
            "monthly": f"${coop_monthly_per:.2f}/mo × 12 = ${coop_monthly_total:.2f}",
            "monthly_daily": f"${coop_monthly_metrics['daily_cost']:.2f}/day | CPM: ${coop_monthly_metrics['cpm']:.2f}",
            "3month": f"${coop_three_per:.2f} × 3 = ${coop_three_total:.2f} (10% off)",
            "3month_daily": f"${coop_three_metrics['daily_cost']:.2f}/day | CPM: ${coop_three_metrics['cpm']:.2f}",
            "6month": f"${coop_six_per:.2f} × 6 = ${coop_six_total:.2f} (7.5% off)",
            "6month_daily": f"${coop_six_metrics['daily_cost']:.2f}/day | CPM: ${coop_six_metrics['cpm']:.2f}",
            "paid_full": f"${coop_paid_total:.2f} (one payment, 15% off)",
            "paid_full_daily": f"${coop_paid_metrics['daily_cost']:.2f}/day | CPM: ${coop_paid_metrics['cpm']:.2f}",
        },
        "exclusive": {
            "base_price": exclusive_base_total,
            "monthly": f"${exclusive_monthly_per:.2f}/mo × 12 = ${exclusive_monthly_total:.2f}",
            "monthly_daily": f"${exclusive_monthly_metrics['daily_cost']:.2f}/day | CPM: ${exclusive_monthly_metrics['cpm']:.2f}",
            "3month": f"${exclusive_three_per:.2f} × 3 = ${exclusive_three_total:.2f}",
            "3month_daily": f"${exclusive_three_metrics['daily_cost']:.2f}/day | CPM: ${exclusive_three_metrics['cpm']:.2f}",
            "6month": f"${exclusive_six_per:.2f} × 6 = ${exclusive_six_total:.2f}",
            "6month_daily": f"${exclusive_six_metrics['daily_cost']:.2f}/day | CPM: ${exclusive_six_metrics['cpm']:.2f}",
            "paid_full": f"${exclusive_paid_total:.2f} (one payment, 5% off)",
            "paid_full_daily": f"${exclusive_paid_metrics['daily_cost']:.2f}/day | CPM: ${exclusive_paid_metrics['cpm']:.2f}",
        },
        "contractor": {
            "base_price": contractor_base_total,
            "3month": f"${contractor_three_per:.2f} × 3 = ${contractor_three_total:.2f}",
            "3month_daily": f"${contractor_three_metrics['daily_cost']:.2f}/day | CPM: ${contractor_three_metrics['cpm']:.2f}",
            "paid_full": f"${contractor_paid_total:.2f} (one payment, 5% off)",
            "paid_full_daily": f"${contractor_paid_metrics['daily_cost']:.2f}/day | CPM: ${contractor_paid_metrics['cpm']:.2f}",
        }
    }

def format_rates_message_default(pricing: dict) -> str:
    """Format default rates (padded, monthly + total only)."""
    return (
        f"📍 *{pricing['store_name']}* — {pricing['city']}, {pricing['store_number']}\n"
        f"📦 {pricing['ad_type'].upper()} AD | {pricing['case_count']} cases\n\n"
        f"💳 *Payment Option:*\n"
        f"• ${pricing['default']['monthly_per']:.2f}/mo × 12 = ${pricing['default']['monthly_total']:.2f}\n"
        f"  → ${pricing['default']['daily_cost']:.2f}/day | CPM: ${pricing['default']['cpm']:.2f}\n\n"
        f"_Select a rate option below:_"
    )

def format_rates_message_coop(pricing: dict) -> str:
    """Format Manager Approved Co-Op Rates (full pricing structure)."""
    return (
        f"📍 *{pricing['store_name']}* — {pricing['city']}, {pricing['store_number']}\n"
        f"📦 {pricing['ad_type'].upper()} AD | {pricing['case_count']} cases | {pricing['impressions']['daily']:,}/day\n"
        f"🎯 *Manager Approved Co-Op Rates*\n\n"
        f"💳 *Payment Plans:*\n"
        f"• {pricing['coop']['monthly']}\n"
        f"  {pricing['coop']['monthly_daily']}\n\n"
        f"• {pricing['coop']['6month']}\n"
        f"  {pricing['coop']['6month_daily']}\n\n"
        f"• {pricing['coop']['3month']}\n"
        f"  {pricing['coop']['3month_daily']}\n\n"
        f"• {pricing['coop']['paid_full']}\n"
        f"  {pricing['coop']['paid_full_daily']}"
    )

def format_rates_message_exclusive(pricing: dict) -> str:
    """Format Exclusive Category Rates (5% off on paid-in-full only)."""
    return (
        f"📍 *{pricing['store_name']}* — {pricing['city']}, {pricing['store_number']}\n"
        f"📦 {pricing['ad_type'].upper()} AD | {pricing['case_count']} cases | {pricing['impressions']['daily']:,}/day\n"
        f"🏆 *Exclusive Category Rates*\n\n"
        f"💳 *Payment Plans:*\n"
        f"• {pricing['exclusive']['monthly']}\n"
        f"  {pricing['exclusive']['monthly_daily']}\n\n"
        f"• {pricing['exclusive']['6month']}\n"
        f"  {pricing['exclusive']['6month_daily']}\n\n"
        f"• {pricing['exclusive']['3month']}\n"
        f"  {pricing['exclusive']['3month_daily']}\n\n"
        f"• {pricing['exclusive']['paid_full']}\n"
        f"  {pricing['exclusive']['paid_full_daily']}"
    )

def format_rates_message_contractor(pricing: dict) -> str:
    """Format Contractor Rates (3-month + paid-in-full only)."""
    return (
        f"📍 *{pricing['store_name']}* — {pricing['city']}, {pricing['store_number']}\n"
        f"📦 {pricing['ad_type'].upper()} AD | {pricing['case_count']} cases | {pricing['impressions']['daily']:,}/day\n"
        f"🔧 *Contractor Rates*\n\n"
        f"💳 *Payment Plans:*\n"
        f"• {pricing['contractor']['3month']}\n"
        f"  {pricing['contractor']['3month_daily']}\n\n"
        f"• {pricing['contractor']['paid_full']}\n"
        f"  {pricing['contractor']['paid_full_daily']}\n\n"
        f"🎁 *Buy 2 Stores, Get 1 Free!*\n_(Free store must be equal or lesser value & have paid advertiser running)_"
    )

def calculate_pricing(store: dict, ad_type: str = "single") -> dict:
    """Legacy function - returns all-tiers pricing object."""
    return calculate_pricing_all_tiers(store, ad_type)

def format_rates_message(pricing: dict) -> str:
    """Legacy function - returns default (padded) rates."""
    return format_rates_message_default(pricing)

def make_ad_toggle_buttons(store_num: str) -> InlineKeyboardMarkup:
    """Single/Double ad toggle."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📄 Single Ad", callback_data=f"rates_single_{store_num}"),
            InlineKeyboardButton("📋 Double Ad", callback_data=f"rates_double_{store_num}"),
        ],
    ])

def make_tier_selection_buttons(store_num: str, ad_type: str = "single") -> InlineKeyboardMarkup:
    """Rate tier selection buttons after default rates shown."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Manager Approved Co-Op", callback_data=f"tier_coop_{ad_type}_{store_num}")],
        [InlineKeyboardButton("🏆 Exclusive Category", callback_data=f"tier_exclusive_{ad_type}_{store_num}")],
        [InlineKeyboardButton("🔧 Contractors", callback_data=f"tier_contractor_{ad_type}_{store_num}")],
        [InlineKeyboardButton("⬅️ Change Ad Type", callback_data=f"select_store_{store_num}")],
    ])

AWAITING_RATES = "awaiting_rates"
AWAITING_ROI = "awaiting_roi"
AWAITING_ROI_ADPRICE = "awaiting_roi_adprice"
AWAITING_ROI_REDEMPTIONS = "awaiting_roi_redemptions"
AWAITING_ROI_TICKET = "awaiting_roi_ticket"
AWAITING_ROI_COUPON = "awaiting_roi_coupon"
AWAITING_ROI_COGS = "awaiting_roi_cogs"
AWAITING_ROI_ADTYPE = "awaiting_roi_adtype"
AWAITING_ROI_PAYMENT = "awaiting_roi_payment"
AWAITING_ROI_TIER = "awaiting_roi_tier"

async def roi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /roi command."""
    if context.args:
        store_num = " ".join(context.args).upper()
        await open_roi_calculator(update, store_num)
    else:
        context.user_data[AWAITING_ROI] = True
        await update.message.reply_text(
            "📊 *ROI Calculator*\n\n"
            "Enter a store number to calculate ROI:\n\n"
            "_Example: `FME07Z-0236` or `SAF07Y-1073`_",
            parse_mode="Markdown"
        )

async def show_roi_calculator(query, context: ContextTypes.DEFAULT_TYPE, store_num: str):
    """Display interactive ROI calculator with adjustment buttons."""
    store = STORES.get(store_num)
    if not store:
        await query.answer("❌ Store not found", show_alert=True)
        return
    
    # Get current parameters from context
    redemptions = context.user_data.get('roi_redemptions', 20)
    avg_ticket = context.user_data.get('roi_ticket', 35)
    cogs_pct = context.user_data.get('roi_cogs', 35)
    coupon = context.user_data.get('roi_coupon', 10)
    ad_type = context.user_data.get('roi_ad_type', 'single')
    payment_plan = context.user_data.get('roi_payment', 'monthly')
    tier = context.user_data.get('roi_tier', 'coop')
    
    # Calculate ROI using same formula as web calculator
    base = store["DoubleAd"] if ad_type.lower() == "double" else store["SingleAd"]
    
    # Pricing tiers
    PRODUCTION = 125
    PADDING = 1200
    
    if tier.lower() == "coop":
        base_before = base
    else:
        base_before = base + PADDING
    
    # Apply payment plan (annual cost basis)
    if payment_plan.lower() == "paid_full":
        annual = (base_before * 0.85) + PRODUCTION
    elif payment_plan.lower() == "paid_3":
        annual = ((base_before * 0.90) + PRODUCTION) * 3
    elif payment_plan.lower() == "paid_6":
        annual = ((base_before * 0.925) + PRODUCTION) * 6
    else:  # monthly (base + production is the annual cost)
        annual = base_before + PRODUCTION
    
    monthly_cost = annual / 12
    
    # Revenue calculations (assuming these are NEW customers acquired via the coupon)
    # Full ticket amount since these are incremental customers
    monthly_revenue = redemptions * avg_ticket
    monthly_profit = monthly_revenue * (1 - cogs_pct / 100)
    
    annual_revenue = monthly_revenue * 12
    annual_profit = monthly_profit * 12
    annual_cost = annual
    
    # ROI
    monthly_roi = ((monthly_profit - monthly_cost) / monthly_cost * 100) if monthly_cost > 0 else 0
    annual_roi = ((annual_profit - annual_cost) / annual_cost * 100) if annual_cost > 0 else 0
    net_monthly = monthly_profit - monthly_cost
    net_annual = annual_profit - annual_cost
    
    # Format display
    ad_label = "📄 Single" if ad_type == "single" else "📋 Double"
    tier_label = "Co-Op" if tier == "coop" else "Standard"
    plan_label = "Monthly" if payment_plan == "monthly" else ("Paid in 3" if payment_plan == "paid_3" else ("Paid in 6" if payment_plan == "paid_6" else "Paid in Full"))
    
    # Build message
    msg = (f"📊 *ROI Calculator*\n\n"
           f"*Store:* {store['StoreName']} - {store['GroceryChain']}\n"
           f"*Location:* {store['City']}, {store['State']}\n"
           f"_Assumes these are NEW customers acquired via coupon_\n\n"
           f"*Current Settings:*\n"
           f"• Redemptions: {redemptions}/mo (new customers)\n"
           f"• Avg Ticket: ${avg_ticket:.0f} (full price)\n"
           f"• Coupon Cost: ${coupon:.0f} (acquisition expense)\n"
           f"• COGS: {cogs_pct}%\n"
           f"• Ad Type: {ad_label}\n"
           f"• Plan: {plan_label}\n"
           f"• Tier: {tier_label}\n\n"
           f"*💰 Monthly Results:*\n"
           f"New Revenue: ${monthly_revenue:.2f}\n"
           f"Profit (after COGS): ${monthly_profit:.2f}\n"
           f"Ad Cost: ${monthly_cost:.2f}\n"
           f"{'🟢' if net_monthly >= 0 else '🔴'} *NET: ${net_monthly:+,.2f}/mo ({monthly_roi:+.0f}% ROI)*\n\n"
           f"*📈 Annual Results:*\n"
           f"New Revenue: ${annual_revenue:,.2f}\n"
           f"Profit (after COGS): ${annual_profit:,.2f}\n"
           f"Ad Cost: ${annual_cost:,.2f}\n"
           f"{'🟢' if net_annual >= 0 else '🔴'} *NET: ${net_annual:+,.2f}/yr ({annual_roi:+.0f}% ROI)*\n\n"
           f"_Tap buttons below to adjust values_")
    
    # Adjustment buttons - organized by parameter
    buttons = [
        [InlineKeyboardButton("📊 Redemptions", callback_data=f"roi_adj_redemptions_{store_num}")],
        [InlineKeyboardButton("💵 Avg Ticket", callback_data=f"roi_adj_ticket_{store_num}")],
        [InlineKeyboardButton("🏷️ Coupon", callback_data=f"roi_adj_coupon_{store_num}")],
        [InlineKeyboardButton("📦 COGS %", callback_data=f"roi_adj_cogs_{store_num}")],
        [InlineKeyboardButton(f"{ad_label} Ad Type", callback_data=f"roi_adj_adtype_{store_num}")],
        [InlineKeyboardButton(f"📅 {plan_label} Plan", callback_data=f"roi_adj_payment_{store_num}")],
        [InlineKeyboardButton(f"🎯 {tier_label} Tier", callback_data=f"roi_adj_tier_{store_num}")],
        [InlineKeyboardButton("⬅️ Back to Rates", callback_data=f"select_store_{store_num}")],
    ]
    
    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def show_roi_results(update: Update, context: ContextTypes.DEFAULT_TYPE, store_num: str):
    """Display final ROI results after conversational input."""
    store = STORES.get(store_num)
    if not store:
        # Silently return if store not found
        return
    
    # Get parameters from context
    redemptions = context.user_data.get('roi_redemptions', 20)
    avg_ticket = context.user_data.get('roi_ticket', 35)
    cogs_pct = context.user_data.get('roi_cogs', 35)
    coupon = context.user_data.get('roi_coupon', 10)
    ad_type = context.user_data.get('roi_ad_type', 'single')
    payment_plan = context.user_data.get('roi_payment', 'monthly')
    tier = context.user_data.get('roi_tier', 'coop')
    
    # Calculate ROI
    base = store["DoubleAd"] if ad_type.lower() == "double" else store["SingleAd"]
    PRODUCTION = 125
    PADDING = 1200
    
    if tier.lower() == "coop":
        base_before = base
    else:
        base_before = base + PADDING
    
    # Apply payment plan
    if payment_plan.lower() == "paid_full":
        annual = (base_before * 0.85) + PRODUCTION
    elif payment_plan.lower() == "paid_3":
        annual = ((base_before * 0.90) + PRODUCTION) * 3
    elif payment_plan.lower() == "paid_6":
        annual = ((base_before * 0.925) + PRODUCTION) * 6
    else:  # monthly
        annual = base_before + PRODUCTION
    
    monthly_cost = annual / 12
    
    # Revenue calculations
    monthly_revenue = redemptions * avg_ticket
    monthly_profit = monthly_revenue * (1 - cogs_pct / 100)
    
    annual_revenue = monthly_revenue * 12
    annual_profit = monthly_profit * 12
    annual_cost = annual
    
    # ROI
    monthly_roi = ((monthly_profit - monthly_cost) / monthly_cost * 100) if monthly_cost > 0 else 0
    annual_roi = ((annual_profit - annual_cost) / annual_cost * 100) if annual_cost > 0 else 0
    net_monthly = monthly_profit - monthly_cost
    net_annual = annual_profit - annual_cost
    
    # Build message
    msg = (f"📊 *ROI RESULTS*\n\n"
           f"*Store:* {store['StoreName']}\n"
           f"*Location:* {store['City']}, {store['State']}\n\n"
           f"*Inputs:*\n"
           f"• Redemptions: {redemptions}/mo\n"
           f"• Avg Ticket: ${avg_ticket:.2f}\n"
           f"• Coupon: ${coupon:.2f}\n"
           f"• COGS: {cogs_pct}%\n\n"
           f"*💰 Monthly:*\n"
           f"Revenue: ${monthly_revenue:,.2f}\n"
           f"Profit: ${monthly_profit:,.2f}\n"
           f"Ad Cost: ${monthly_cost:,.2f}\n"
           f"{'🟢' if net_monthly >= 0 else '🔴'} *NET: ${net_monthly:+,.2f}/mo ({monthly_roi:+.0f}% ROI)*\n\n"
           f"*📈 Annual:*\n"
           f"Revenue: ${annual_revenue:,.2f}\n"
           f"Profit: ${annual_profit:,.2f}\n"
           f"Ad Cost: ${annual_cost:,.2f}\n"
           f"{'🟢' if net_annual >= 0 else '🔴'} *NET: ${net_annual:+,.2f}/yr ({annual_roi:+.0f}% ROI)*")
    
    buttons = [[InlineKeyboardButton("🔄 Calculate Again", callback_data="roi_calculator")],
               [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]]
    
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def show_roi_results_with_adprice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display final ROI results using ad price directly (no store lookup)."""
    # Get parameters from context
    adprice = context.user_data.get('roi_adprice', 3000)
    redemptions = context.user_data.get('roi_redemptions', 20)
    avg_ticket = context.user_data.get('roi_ticket', 35)
    cogs_pct = context.user_data.get('roi_cogs', 35)
    coupon = context.user_data.get('roi_coupon', 10)
    
    # Annual cost is the ad price
    annual_cost = adprice
    monthly_cost = annual_cost / 12
    
    # Revenue calculations
    monthly_revenue = redemptions * avg_ticket
    monthly_profit = monthly_revenue * (1 - cogs_pct / 100)
    
    annual_revenue = monthly_revenue * 12
    annual_profit = monthly_profit * 12
    
    # ROI
    monthly_roi = ((monthly_profit - monthly_cost) / monthly_cost * 100) if monthly_cost > 0 else 0
    annual_roi = ((annual_profit - annual_cost) / annual_cost * 100) if annual_cost > 0 else 0
    net_monthly = monthly_profit - monthly_cost
    net_annual = annual_profit - annual_cost
    
    # Breakeven: how many redemptions/mo to cover the ad cost
    # profit per redemption = avg_ticket * (1 - cogs_pct/100)
    profit_per_redemption = avg_ticket * (1 - cogs_pct / 100)
    if profit_per_redemption > 0:
        breakeven_monthly = monthly_cost / profit_per_redemption
        breakeven_daily = breakeven_monthly / 30
    else:
        breakeven_monthly = float('inf')
        breakeven_daily = float('inf')
    
    # Customer Lifetime Value — what ONE new customer is worth
    # Based on avg_ticket after COGS at different visit frequencies
    profit_per_visit = avg_ticket * (1 - cogs_pct / 100)
    ltv_1x = profit_per_visit * 1 * 12   # 1 visit/month for a year
    ltv_2x = profit_per_visit * 2 * 12   # 2 visits/month for a year
    ltv_4x = profit_per_visit * 4 * 12   # 4 visits/month (weekly)
    
    # How many new customers to pay for the ad
    new_cust_breakeven_1x = annual_cost / ltv_1x if ltv_1x > 0 else float('inf')
    new_cust_breakeven_2x = annual_cost / ltv_2x if ltv_2x > 0 else float('inf')
    new_cust_breakeven_4x = annual_cost / ltv_4x if ltv_4x > 0 else float('inf')
    
    # Build message
    msg = (f"📊 *ROI RESULTS*\n\n"
           f"*Inputs:*\n"
           f"• Ad Price: ${adprice:,.2f}/year\n"
           f"• Redemptions: {redemptions}/mo\n"
           f"• Avg Ticket: ${avg_ticket:.2f}\n"
           f"• Coupon: ${coupon:.2f}\n"
           f"• COGS: {cogs_pct}%\n\n"
           f"*💰 Monthly:*\n"
           f"Revenue: ${monthly_revenue:,.2f}\n"
           f"Profit: ${monthly_profit:,.2f}\n"
           f"Ad Cost: ${monthly_cost:,.2f}\n"
           f"{'🟢' if net_monthly >= 0 else '🔴'} *NET: ${net_monthly:+,.2f}/mo ({monthly_roi:+.0f}% ROI)*\n\n"
           f"*📈 Annual:*\n"
           f"Revenue: ${annual_revenue:,.2f}\n"
           f"Profit: ${annual_profit:,.2f}\n"
           f"Ad Cost: ${annual_cost:,.2f}\n"
           f"{'🟢' if net_annual >= 0 else '🔴'} *NET: ${net_annual:+,.2f}/yr ({annual_roi:+.0f}% ROI)*\n\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"🎯 *BREAKEVEN*\n"
           f"Profit per redemption: ${profit_per_redemption:,.2f}\n"
           f"To cover ad cost: *{breakeven_monthly:.1f} redemptions/mo*\n"
           f"That's only *{breakeven_daily:.1f} per day*\n\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"👤 *VALUE OF 1 NEW CUSTOMER*\n"
           f"_(annual profit at ${avg_ticket:.0f} ticket, {cogs_pct:.0f}% COGS)_\n\n"
           f"• 1x/month: *${ltv_1x:,.2f}/yr*\n"
           f"• 2x/month: *${ltv_2x:,.2f}/yr*\n"
           f"• 4x/month (weekly): *${ltv_4x:,.2f}/yr*\n\n"
           f"🆓 *Customers needed to make it FREE:*\n"
           f"• 1x/month: *{new_cust_breakeven_1x:.1f} customers*\n"
           f"• 2x/month: *{new_cust_breakeven_2x:.1f} customers*\n"
           f"• 4x/month: *{new_cust_breakeven_4x:.1f} customers*")
    
    buttons = [[InlineKeyboardButton("🔄 Calculate Again", callback_data="roi_calculator")],
               [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]]
    
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def open_roi_calculator(update, store_num: str):
    """Open ROI calculator for a store."""
    store_num = store_num.upper().strip()
    store = STORES.get(store_num)
    
    if store:
        roi_url = f"http://localhost:8501?store={store_num}"
        msg = (f"📊 *ROI Calculator*\n\n"
               f"*Store:* {store['StoreName']} - {store['GroceryChain']}\n"
               f"*Location:* {store['City']}, {store['State']}\n\n"
               f"[💻 Open Calculator]({roi_url})")
        buttons = [
            [InlineKeyboardButton("💻 Open Calculator", url=roi_url)],
            [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")],
        ]
        if isinstance(update, Update) and update.callback_query:
            await update.callback_query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        # Silently ignore invalid store lookups
        pass

async def rates_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /rates command."""
    if context.args:
        store_num = " ".join(context.args).upper()
        await do_rates_lookup(update, store_num)
    else:
        context.user_data[AWAITING_RATES] = True
        await update.message.reply_text(
            "💰 *Store Rates Lookup*\n\nSend a store number:\n\n"
            "_Example: `FME07Z-0236` or `SAF07Y-1073`_",
            parse_mode="Markdown"
        )

async def do_rates_lookup(update, store_num: str, ad_type: str = "single", edit_message=None):
    """Look up rates for a store and display default (padded) rates with tier options."""
    store_num = store_num.upper().strip()
    store = STORES.get(store_num)
    
    if not store:
        # Silently ignore invalid stores (don't clutter chat)
        return
        if edit_message:
            pass
        elif hasattr(update, 'message') and update.message:
            await update.message.reply_text(text, parse_mode="Markdown")
        return
    
    pricing = calculate_pricing(store, ad_type)
    text = format_rates_message_default(pricing)
    
    # Show ad toggle buttons first, then tier selection below
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📄 Single Ad", callback_data=f"rates_single_{store_num}"),
            InlineKeyboardButton("📋 Double Ad", callback_data=f"rates_double_{store_num}"),
        ],
        [InlineKeyboardButton("📊 ROI Calculator", callback_data=f"roi_open_{store_num}")],
        [InlineKeyboardButton("🎯 Manager Approved Co-Op", callback_data=f"tier_coop_{ad_type}_{store_num}")],
        [InlineKeyboardButton("🏆 Exclusive Category", callback_data=f"tier_exclusive_{ad_type}_{store_num}")],
        [InlineKeyboardButton("🔧 Contractors", callback_data=f"tier_contractor_{ad_type}_{store_num}")],
        # Add to Cart button
        [InlineKeyboardButton("🛒 Add to Cart", callback_data=f"cart_payment_{ad_type}_{store_num}")],
        [InlineKeyboardButton("⬅️ Back to Store", callback_data=f"select_store_{store_num}")],
    ])
    
    if edit_message:
        await edit_message.edit_text(text, parse_mode="Markdown", reply_markup=buttons)
    elif hasattr(update, 'message') and update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=buttons)


async def show_store_action_menu(chat, store_num: str, store: dict, edit_message=None, context=None):
    """Show the store action menu: Rates, Testimonials, Prospects, Audit."""
    chain = store.get("GroceryChain", "")
    city = store.get("City", "")
    state = store.get("State", "")
    cycle = store.get("Cycle", "?")
    address = store.get("Address", "")
    case_count = store.get("Case Count", "?")
    
    # Store city in context for back button
    if context:
        context.user_data['last_city'] = city
        context.user_data['last_city_stores'] = CITY_INDEX.get(city, [])
    
    text = (
        f"📍 *{chain}* — {city}, {state}\n"
        f"🏪 Store: `{store_num}` | Cycle: {cycle}\n"
        f"📦 Cases: {case_count}\n"
        f"📫 {address}\n\n"
        f"What would you like to do?"
    )
    
    buttons = [
        [InlineKeyboardButton("🔍 Find Prospects", callback_data=f"action_prospects_{store_num}")],
        [InlineKeyboardButton("💰 Store Rates", callback_data=f"action_rates_{store_num}")],
        [InlineKeyboardButton("📋 Nearby Testimonials", callback_data=f"action_testimonials_{store_num}")],
        [InlineKeyboardButton("🏪 Audit Store", callback_data=f"action_audit_{store_num}")],
        [InlineKeyboardButton("⬅️ Back to City", callback_data=f"back_to_city_{city}")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")],
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    
    if edit_message:
        await edit_message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await chat.send_message(text, parse_mode="Markdown", reply_markup=keyboard)


def find_nearby_testimonials(store: dict, limit: int = 5) -> list:
    """Find testimonials ranked by distance from store location.
    
    Search priority (in order):
    1. Same city
    2. Same state + same zip code
    3. Same state + nearby zip codes
    4. Same state (any zip)
    5. Distance-based ranking (if lat/lon available)
    """
    from math import radians, cos, sin, asin, sqrt
    
    testimonials = load_testimonials()
    if not testimonials:
        return []
    
    store_city = store.get("City", "").lower().strip()
    store_state = store.get("State", "").upper().strip()
    store_zip = store.get("PostalCode", "").strip()
    store_lat = float(store.get("latitude", 0)) if store.get("latitude") else None
    store_lon = float(store.get("longitude", 0)) if store.get("longitude") else None
    
    def haversine_distance(lat1, lon1, lat2, lon2):
        """Calculate distance in miles between two lat/lon points."""
        if not (lat1 and lon1 and lat2 and lon2):
            return float('inf')
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        km = 6371 * c
        return km * 0.621371  # miles
    
    # Bucket testimonials by relevance
    same_city = []
    same_state_same_zip = []
    same_state_nearby_zip = []
    same_state_other_zip = []
    by_distance = []
    
    for t in testimonials:
        full = t.get("full", {})
        test_city = full.get("city", "").lower().strip()
        test_state = full.get("state", "").upper().strip()
        test_zip = full.get("zip", "").strip()
        test_lat = float(full.get("lat")) if full.get("lat") else None
        test_lon = float(full.get("lng")) if full.get("lng") else None
        
        # Bucket 1: Same city (highest priority)
        if store_city and test_city == store_city and test_state == store_state:
            same_city.append(t)
        # Bucket 2: Same state + same zip
        elif test_state == store_state and store_zip and test_zip == store_zip:
            same_state_same_zip.append(t)
        # Bucket 3: Same state + nearby zip (within ±50)
        elif test_state == store_state and store_zip and test_zip:
            try:
                zip_diff = abs(int(store_zip[:5]) - int(test_zip[:5]))
                if zip_diff <= 50:
                    same_state_nearby_zip.append((zip_diff, t))
            except (ValueError, IndexError):
                pass
        # Bucket 4: Same state (any zip)
        elif test_state == store_state:
            same_state_other_zip.append(t)
        # Bucket 5: Distance-based ranking (if coords available)
        elif store_lat and store_lon and test_lat and test_lon:
            dist = haversine_distance(store_lat, store_lon, test_lat, test_lon)
            if dist < float('inf'):
                by_distance.append((dist, t))
    
    # Sort each bucket and combine
    same_state_nearby_zip.sort(key=lambda x: x[0])
    by_distance.sort(key=lambda x: x[0])
    
    result = (
        same_city +
        same_state_same_zip +
        [t for _, t in same_state_nearby_zip] +
        same_state_other_zip +
        [t for _, t in by_distance]
    )
    
    return result[:limit]


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the main menu with 4-category structure."""
    # Clear any stale awaiting states
    clear_awaiting_states(context)
    
    notepad = context.user_data.get('notepad', '').strip()
    
    if notepad:
        preview = notepad[:50] + "..." if len(notepad) > 50 else notepad
        notepad_section = f"\n\n📝 *Notepad:* `{preview}`"
    else:
        notepad_section = ""
    
    menu_text = f"""🔴 *INDOORMEDIA*
═══════════════════════════════════════

*SALES COMMAND CENTER*

🎯 Prospects • 💼 Clients • 🏪 Stores
📦 Products • 📊 Performance • ⚙️ Tools

*Let's get to work!*{notepad_section}"""
    
    # Get cart count for badge
    rep_id = get_rep_id(update) if isinstance(update, Update) else None
    cart_count = 0
    if rep_id:
        try:
            rep_data = load_rep_data(rep_id)
            cart_count = len(rep_data.get("cart", []))
        except:
            cart_count = 0
    
    cart_badge = f" ({cart_count})" if cart_count > 0 else ""
    
    # Main menu - 6 primary categories
    buttons = [
        [InlineKeyboardButton("🎯 Prospects", callback_data="menu_prospects")],
        [InlineKeyboardButton("💼 Clients", callback_data="menu_clients")],
        [InlineKeyboardButton("🏪 Stores", callback_data="menu_stores")],
        [InlineKeyboardButton("📦 Products", callback_data="menu_products")],
        [InlineKeyboardButton("📊 Performance", callback_data="menu_performance")],
        [InlineKeyboardButton("⚙️ Tools", callback_data="menu_tools")],
        [InlineKeyboardButton(f"🛒 Cart{cart_badge}", callback_data="view_cart")],
    ]
    
    if isinstance(update, Update) and update.callback_query:
        await update.callback_query.edit_message_text(
            menu_text, 
            parse_mode="Markdown", 
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        await update.effective_chat.send_message(
            menu_text, 
            parse_mode="Markdown", 
            reply_markup=InlineKeyboardMarkup(buttons)
        )


async def show_submenu_locate_stores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the Locate Stores submenu."""
    query = update.callback_query
    await query.answer()
    buttons = [
        [InlineKeyboardButton("📍 Find Stores Near Me", callback_data="locate_near_me")],
        [InlineKeyboardButton("🔍 Search by City/Store", callback_data="locate_search")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")],
    ]
    await query.edit_message_text(
        "🗺️  *LOCATE STORES*\n\n_Find stores near you or search by location_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def show_submenu_prospects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the Prospects submenu."""
    query = update.callback_query
    await query.answer()
    buttons = [
        [InlineKeyboardButton("🔍 Find Prospects", callback_data="new_search")],
        [InlineKeyboardButton("💾 Saved Prospects", callback_data="saved_prospects")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")],
    ]
    await query.edit_message_text(
        "🎯 *PROSPECTS*\n\n_Find and qualify new opportunities_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_submenu_clients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the Clients submenu."""
    query = update.callback_query
    await query.answer()
    buttons = [
        [InlineKeyboardButton("👥 My Customers", callback_data="client_list")],
        [InlineKeyboardButton("💬 Testimonials", callback_data="testimonial_search")],
        [InlineKeyboardButton("💳 My Sales", callback_data="my_sales_view")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")],
    ]
    await query.edit_message_text(
        "💼 *CLIENTS*\n\n_Manage customers & testimonials_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_submenu_stores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the Stores submenu."""
    query = update.callback_query
    await query.answer()
    buttons = [
        [InlineKeyboardButton("🔍 Search Stores", callback_data="locate_search")],
        [InlineKeyboardButton("💰 Store Rates", callback_data="rates_search")],
        [InlineKeyboardButton("🏪 Audit Store", callback_data="audit_store")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")],
    ]
    await query.edit_message_text(
        "🏪 *STORES*\n\n_Lookup rates & manage inventory_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_submenu_prospecting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the Prospecting submenu (legacy handler)."""
    await show_submenu_prospects(update, context)


async def show_submenu_sales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the Sales Management submenu."""
    query = update.callback_query
    await query.answer()
    buttons = [
        [InlineKeyboardButton("👥 My Customers", callback_data="client_list")],
        [InlineKeyboardButton("💳 My Sales", callback_data="my_sales_view")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")],
    ]
    await query.edit_message_text(
        "💼 *MANAGE CUSTOMERS*\n\n_Build your book of business_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def show_submenu_performance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the Performance submenu."""
    query = update.callback_query
    await query.answer()
    buttons = [
        [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard_view")],
        [InlineKeyboardButton("👥 Team Sales", callback_data="team_sales_view")],
        [InlineKeyboardButton("📅 Monthly Leaderboard", callback_data="monthly_leaderboard")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")],
    ]
    await query.edit_message_text(
        "📈 *PERFORMANCE HUB*\n\n_Track revenue and team progress_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def show_submenu_tools(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the Resources submenu."""
    query = update.callback_query
    await query.answer()
    buttons = [
        [InlineKeyboardButton("📊 ROI Calculator", callback_data="roi_calculator")],
        [InlineKeyboardButton("📋 Testimonial Search", callback_data="testimonial_search")],
        [InlineKeyboardButton("📝 Submit Testimonial", callback_data="submit_testimonial")],
        [InlineKeyboardButton("🏪 Audit Store", callback_data="audit_store")],
        [InlineKeyboardButton("🎨 Counter Sign Generator", callback_data="counter_sign_generator")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")],
    ]
    await query.edit_message_text(
        "⚙️  *RESOURCES*\n\n_Tools for success_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def show_submenu_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the Products submenu."""
    query = update.callback_query
    await query.answer()
    buttons = [
        [InlineKeyboardButton("📜 Register Tape", callback_data="menu_register_tape")],
        [InlineKeyboardButton("🛒 Cartvertising", callback_data="menu_cartvertising")],
        [InlineKeyboardButton("📱 Digital Products", callback_data="menu_digital")],
        [InlineKeyboardButton("📈 ROI Calculator", callback_data="roi_calculator")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")],
    ]
    await query.edit_message_text(
        "📦 *PRODUCTS*\n\n_Presentations • Rates • ROI_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def show_submenu_register_tape(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Register Tape submenu with Presentation and Rates."""
    query = update.callback_query
    await query.answer()
    buttons = [
        [InlineKeyboardButton("🎬 Presentation", url="https://docs.google.com/presentation/d/1Xs60nX3i6MJkC81GgnK-50jBrkWVPu06xRpmv8z4PIc/edit?usp=sharing")],
        [InlineKeyboardButton("📹 Explainer Video", url="https://youtu.be/_gdlyEszHfY?si=0_kHou89WrMhvNY_")],
        [InlineKeyboardButton("💰 Register Tape Rates", callback_data="rates_search")],
        [InlineKeyboardButton("⬅️ Back to Products", callback_data="menu_products")],
    ]
    await query.edit_message_text(
        "📜 *REGISTER TAPE*\n\n_In-store Point-of-Purchase Advertising_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# --- Product Catalog Submenus & Display ---

async def show_submenu_cartvertising(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Cartvertising submenu with presentation and explainer."""
    query = update.callback_query
    await query.answer()
    buttons = [
        [InlineKeyboardButton("🎬 Presentation", url="https://docs.google.com/presentation/d/1xwIF4CaTp07AKunGaJysCSIGqN7VCdbL4fgOH3XEpl4/edit?usp=sharing")],
        [InlineKeyboardButton("📹 Explainer Video", url="https://www.youtube.com/watch?v=PduxHWy8sMc")],
        [InlineKeyboardButton("🛒 Child Seat", callback_data="product_child_seat")],
        [InlineKeyboardButton("👃 Nose of Cart", callback_data="product_nose")],
        [InlineKeyboardButton("⬅️ Back to Products", callback_data="menu_products")],
    ]
    await query.edit_message_text(
        "🛒 *CARTVERTISING*\n\n_Shopping Cart In-Store Advertising_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def show_submenu_digital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Digital Products submenu with presentation and explainer."""
    query = update.callback_query
    await query.answer()
    buttons = [
        [InlineKeyboardButton("🎬 Presentation", url="https://docs.google.com/presentation/d/1xwIF4CaTp07AKunGaJysCSIGqN7VCdbL4fgOH3XEpl4/edit?usp=sharing")],
        [InlineKeyboardButton("📹 Explainer Video", url="https://www.youtube.com/watch?v=PduxHWy8sMc")],
        [InlineKeyboardButton("🔗 Connection Hub", url="https://drive.google.com/file/d/199IkMptOlSYviHScKNKUlqELQOhWFxnB/view?usp=sharing")],
        [InlineKeyboardButton("🚀 DigitalBoost", callback_data="product_digitalboost")],
        [InlineKeyboardButton("📍 FindLocal", callback_data="product_findlocal")],
        [InlineKeyboardButton("⭐ ReviewBoost", callback_data="product_reviewboost")],
        [InlineKeyboardButton("💎 LoyaltyBoost", callback_data="product_loyaltyboost")],
        [InlineKeyboardButton("⬅️ Back to Products", callback_data="menu_products")],
    ]
    await query.edit_message_text(
        "📱 *DIGITAL PRODUCTS*\n\n_Online advertising & customer engagement_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def show_product_child_seat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Child Seat (Cartvertising) package selection with pricing tiers and cart buttons."""
    query = update.callback_query
    await query.answer()
    
    text = (
        "🛒 *CHILD SEAT ADVERTISING*\n\n"
        "_Target mothers with high-intent shopping behavior_\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💰 *Pricing Per Pin*\n"
        "• Co-Op: *$240/pin*\n"
        "• Standard: *$240/pin*\n\n"
        "📊 *Impressions*\n"
        "• Standalone: *240,000*\n"
        "• Bundled: *360,000*\n\n"
        "💳 *Payment Plans*\n"
        "• Monthly\n"
        "• 3-Month\n"
        "• 6-Month\n"
        "• Paid in Full\n\n"
        "_Select a tier and plan below:_"
    )
    
    buttons = [
        [InlineKeyboardButton("🎬 Presentation", url="https://docs.google.com/presentation/d/1xwIF4CaTp07AKunGaJysCSIGqN7VCdbL4fgOH3XEpl4/edit?usp=sharing")],
        [InlineKeyboardButton("📹 Explainer Video", url="https://www.youtube.com/watch?v=PduxHWy8sMc")],
        [InlineKeyboardButton("🎯 CO-OP PRICING", callback_data="cart_coop_child_seat")],
        [InlineKeyboardButton("📋 STANDARD PRICING", callback_data="cart_standard_child_seat")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu_cartvertising")],
    ]
    
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def show_cart_coop_pricing(update: Update, context: ContextTypes.DEFAULT_TYPE, product: str = "child_seat"):
    """Show Co-Op pricing tiers with bundle options for Cartvertising."""
    query = update.callback_query
    await query.answer()
    
    # Co-Op pricing: $240/pin (same as Standard for Cartvertising)
    price_per_pin = 240
    
    text = (
        "🎯 *CO-OP APPROVED PRICING*\n\n"
        f"📌 *Price Per Pin:* ${price_per_pin:,}\n"
        f"🏪 *Production:* $395 (covers up to 5 pins)\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 *BUNDLE TYPES*\n\n"
        f"*STANDALONE (240K impressions):*\n"
        f"  1 pin × ${price_per_pin} = ${price_per_pin + 395:,} with production\n\n"
        f"*BUNDLED (360K impressions):*\n"
        f"  Bundle with Register Tape or DigitalBoost\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💳 *Select payment plan:*"
    )
    
    buttons = [
        [InlineKeyboardButton("📄 Standalone | Monthly", callback_data="cart_add_cartvertising_standalone_monthly")],
        [InlineKeyboardButton("📄 Standalone | 3-Month", callback_data="cart_add_cartvertising_standalone_3month")],
        [InlineKeyboardButton("📄 Standalone | 6-Month", callback_data="cart_add_cartvertising_standalone_6month")],
        [InlineKeyboardButton("📄 Standalone | Paid in Full", callback_data="cart_add_cartvertising_standalone_pif")],
        [InlineKeyboardButton("📋 Bundled | Monthly", callback_data="cart_add_cartvertising_bundled_monthly")],
        [InlineKeyboardButton("📋 Bundled | 3-Month", callback_data="cart_add_cartvertising_bundled_3month")],
        [InlineKeyboardButton("📋 Bundled | 6-Month", callback_data="cart_add_cartvertising_bundled_6month")],
        [InlineKeyboardButton("📋 Bundled | Paid in Full", callback_data="cart_add_cartvertising_bundled_pif")],
        [InlineKeyboardButton("⬅️ Back", callback_data="product_child_seat")],
    ]
    
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def show_cart_standard_pricing(update: Update, context: ContextTypes.DEFAULT_TYPE, product: str = "child_seat"):
    """Show Standard pricing tiers with bundle options for Cartvertising."""
    query = update.callback_query
    await query.answer()
    
    # Standard pricing: $240/pin (same as Co-Op for Cartvertising - no padding for display)
    price_per_pin = 240
    
    text = (
        "📋 *STANDARD PRICING*\n\n"
        f"📌 *Price Per Pin:* ${price_per_pin:,}\n"
        f"🏪 *Production:* $395 (covers up to 5 pins)\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 *BUNDLE TYPES*\n\n"
        f"*STANDALONE (240K impressions):*\n"
        f"  1 pin × ${price_per_pin} = ${price_per_pin + 395:,} with production\n\n"
        f"*BUNDLED (360K impressions):*\n"
        f"  Bundle with Register Tape or DigitalBoost\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💳 *Select payment plan:*"
    )
    
    buttons = [
        [InlineKeyboardButton("📄 Standalone | Monthly", callback_data="cart_add_cartvertising_standalone_monthly")],
        [InlineKeyboardButton("📄 Standalone | 3-Month", callback_data="cart_add_cartvertising_standalone_3month")],
        [InlineKeyboardButton("📄 Standalone | 6-Month", callback_data="cart_add_cartvertising_standalone_6month")],
        [InlineKeyboardButton("📄 Standalone | Paid in Full", callback_data="cart_add_cartvertising_standalone_pif")],
        [InlineKeyboardButton("📋 Bundled | Monthly", callback_data="cart_add_cartvertising_bundled_monthly")],
        [InlineKeyboardButton("📋 Bundled | 3-Month", callback_data="cart_add_cartvertising_bundled_3month")],
        [InlineKeyboardButton("📋 Bundled | 6-Month", callback_data="cart_add_cartvertising_bundled_6month")],
        [InlineKeyboardButton("📋 Bundled | Paid in Full", callback_data="cart_add_cartvertising_bundled_pif")],
        [InlineKeyboardButton("⬅️ Back", callback_data="product_child_seat")],
    ]
    
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))


async def show_product_nose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Nose of Cart pricing."""
    query = update.callback_query
    await query.answer()
    
    text = (
        "👃 *NOSE OF CART PRICING*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📋 *Per Slot Pricing*\n"
        "• 6-Month Base: *$2,000/slot*\n"
        "• Annual Base: *$2,500/slot*\n"
        "• Exclusivity: *$3,995* + production per 60 inserts\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🏭 *Production Fees*\n"
        "• Single store: *$495*\n"
        "• Multi-store (same order): *$395/store*\n"
        "• Charged annually, non-commissionable\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📦 *Store Details*\n"
        "• 1 or 2 slots per store (60 or 120 inserts)\n"
        "• One artwork version per slot\n"
        "• 25+ stores = discuss with management\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💳 *Payment Options*\n"
        "• *Upfront:* Production first, then up to 4 monthly equal payments (first payment 30 days from signing)\n"
        "• *Paid in Full:* +2% commission bonus\n"
        "• *As Earned:* Commission paid as customer pays\n"
    )
    
    buttons = [
        [InlineKeyboardButton("🎬 Presentation", url="https://drive.google.com/file/d/1Bvr0XOWHLO5DMwOmi6NQAcuuk4b9EkFS/view?usp=sharing")],
        [InlineKeyboardButton("📹 Explainer Video", url="https://www.youtube.com/watch?v=PduxHWy8sMc")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu_cartvertising")],
    ]
    
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))


async def show_product_digitalboost(update: Update, context: ContextTypes.DEFAULT_TYPE, pins: int = 0):
    """Show DigitalBoost pricing with pin selector and payment plans."""
    query = update.callback_query
    await query.answer()
    
    if pins == 0:
        # Show overview + pin selector
        text = (
            "🚀 *DIGITALBOOST*\n\n"
            "Geofence pin delivering digital banner ads on mobile websites, games & apps.\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "📋 *Per Pin Pricing*\n"
            "• Standard: *$3,600/pin*\n"
            "• Co-Op Approved: *$2,795 (1st pin) + $2,400 (2-5)*\n"
            "• Production: *$395* (covers up to 5 pins)\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "📊 *Impressions Per Pin*\n"
            "• Standalone: *240,000*\n"
            "• Bundled w/ Tape or Cart: *360,000*\n\n"
            "💳 *Payment Plans*\n"
            "• Monthly\n"
            "• 3-Month\n"
            "• 6-Month\n"
            "• Paid in Full\n\n"
            "_Select number of pins below:_"
        )
        buttons = [
            [InlineKeyboardButton("🎬 Presentation", url="https://drive.google.com/file/d/1LvPJjBk1tvMYFoRAy-AUSugUXV82hUeM/view?usp=sharing")],
            [InlineKeyboardButton("📹 Explainer Video", url="https://drive.google.com/file/d/1_QyAlgZRy1bKJSKC1058260d0jPccVTM/view?usp=sharing")],
        ]
        for n in range(1, 6):
            buttons.append([InlineKeyboardButton(f"📌 {n} Pin{'s' if n > 1 else ''}", callback_data=f"db_select_pins_{n}")])
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="menu_digital")])
    else:
        # Calculate totals for Standard and Co-Op
        std_price = 3600 * pins
        prod = 395  # covers up to 5
        std_total = std_price + prod
        
        # Co-Op: 1st pin = $2,400, additional pins = $2,400 each
        coop_pin_cost = 2400 * pins
        coop_total = coop_pin_cost + prod
        
        impressions_std = 240000 * pins
        impressions_bundled = 360000 * pins
        
        text = (
            f"🚀 *DIGITALBOOST — {pins} Pin{'s' if pins > 1 else ''}*\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📋 *STANDARD PRICING*\n"
            f"• {pins} pin{'s' if pins > 1 else ''} × $3,600 = ${std_price:,}\n"
            f"• Production: $395\n"
            f"• *Total: ${std_total:,}*\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎯 *CO-OP APPROVED*\n"
            f"• {pins} pin{'s' if pins > 1 else ''} × $2,400 = ${coop_pin_cost:,}\n"
            f"• Production: $395\n"
            f"• *Total: ${coop_total:,}*\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Impressions Per Pin*\n"
            f"• Standalone: *{impressions_std:,}* ({impressions_std//pins:,} each)\n"
            f"• Bundled: *{impressions_bundled:,}* ({impressions_bundled//pins:,} each)\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💳 *Select Tier & Plan:*"
        )
        
        # Standard tier buttons
        buttons = [
            [InlineKeyboardButton("📄 STD/Monthly", callback_data=f"cart_add_digitalboost_std_{pins}_monthly")],
            [InlineKeyboardButton("📄 STD/3-Month", callback_data=f"cart_add_digitalboost_std_{pins}_3month")],
            [InlineKeyboardButton("📄 STD/6-Month", callback_data=f"cart_add_digitalboost_std_{pins}_6month")],
            [InlineKeyboardButton("📄 STD/PIF", callback_data=f"cart_add_digitalboost_std_{pins}_pif")],
            # Co-Op tier buttons
            [InlineKeyboardButton("🎯 CO-OP/Monthly", callback_data=f"cart_add_digitalboost_coop_{pins}_monthly")],
            [InlineKeyboardButton("🎯 CO-OP/3-Month", callback_data=f"cart_add_digitalboost_coop_{pins}_3month")],
            [InlineKeyboardButton("🎯 CO-OP/6-Month", callback_data=f"cart_add_digitalboost_coop_{pins}_6month")],
            [InlineKeyboardButton("🎯 CO-OP/PIF", callback_data=f"cart_add_digitalboost_coop_{pins}_pif")],
            [InlineKeyboardButton("⬅️ Change Pins", callback_data="product_digitalboost")],
        ]
    
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))


async def show_product_findlocal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show FindLocal pricing."""
    query = update.callback_query
    await query.answer()
    
    text = (
        "📍 *FINDLOCAL*\n\n"
        "Local SEO / citations / listings management across 50+ directories, maps, voice assistants & GPS apps.\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💰 *Pricing*\n"
        "• *$695/location*\n"
        "• +$195 if Google profile assistance needed\n"
        "• No production fee\n"
        "• No volume discount\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💳 *Payment*\n"
        "• Sold alone: *Upfront payment required*\n"
        "• Sold with other products: Can match contract payment schedule\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📦 *Includes*\n"
        "• 50+ business listing submissions\n"
        "• NAP optimization (name, address, phone)\n"
        "• Hours, photos, categories management\n"
        "• Google Business Profile sync\n"
        "• Monthly automated progress reports\n"
        "• Baseline visibility scan\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📡 *Network:* Google, Apple Maps, Yelp, Bing, Waze, Uber, Foursquare, MapQuest, YP, and 40+ more"
    )
    
    buttons = [
        [InlineKeyboardButton("🎬 Presentation", url="https://drive.google.com/file/d/1rRdFgRWvuzaPJCwxqKzTqtjDtd642DuS/view?usp=sharing")],
        [InlineKeyboardButton("📹 Explainer Video", url="https://drive.google.com/file/d/1_QyAlgZRy1bKJSKC1058260d0jPccVTM/view?usp=sharing")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu_digital")],
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))


async def show_product_reviewboost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show ReviewBoost pricing."""
    query = update.callback_query
    await query.answer()
    
    text = (
        "⭐ *REVIEWBOOST*\n\n"
        "Automated review request campaign via Email & SMS.\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💰 *Pricing*\n"
        "• *$695* — 4-month campaign\n"
        "• Up to 4,000 contacts\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "➕ *Need More Contacts?*\n"
        "• *$495* per additional 4-month campaign\n"
        "• Up to 4,000 extra contacts per cycle\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📦 *Includes*\n"
        "• ReviewKit\n"
        "• Email & SMS review requests\n"
        "• Automated 4-month campaign\n"
    )
    
    buttons = [
        [InlineKeyboardButton("🎬 Presentation", url="https://drive.google.com/file/d/12hP-Ip7t9vHjBNFctj2X1AiatxS5O1LH/view?usp=sharing")],
        [InlineKeyboardButton("📹 Explainer Video", url="https://www.youtube.com/watch?v=PBpbUiIoYcM")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu_digital")],
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))


async def show_product_loyaltyboost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show LoyaltyBoost pricing."""
    query = update.callback_query
    await query.answer()
    
    pif_rate = 3600 * 0.95
    pif_prod = 495 * 0.95
    pif_total = pif_rate + pif_prod
    
    text = (
        "💎 *LOYALTYBOOST*\n\n"
        "Annual loyalty/rewards campaign per location.\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💰 *Pricing*\n"
        "• *$3,600* annual campaign\n"
        "• *$495* production fee (non-commissionable)\n"
        "• Total: *$4,095* per location\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💳 *Payment Options*\n"
        "• *Paid in Full:* 5% off package + production\n"
        f"  → *${pif_total:,.2f}* (save ${4095 - pif_total:,.2f})\n"
        "• *Installments:* 6 or 12 months\n"
        "  Equal consecutive payments from date of sale\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📋 *Notes*\n"
        "• $125 off production with testimonial letter at renewal\n"
        "• Active print ad = better commission structure\n"
    )
    
    buttons = [
        [InlineKeyboardButton("🎬 Presentation 1", url="https://drive.google.com/file/d/1BYpsPLnAC2TRfsaQGuMBytaOYAxuNYMK/view?usp=sharing")],
        [InlineKeyboardButton("📹 Explainer Video", url="https://drive.google.com/file/d/1cyJzpBLcDarK_s1EPue95Q_K335XuDXC/view?usp=sharing")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu_digital")],
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))


# --- Prospect Notes & Calendar ---
AWAITING_PROSPECT_NOTE = "awaiting_prospect_note"
AWAITING_NOTEPAD_EDIT = "awaiting_notepad_edit"
AWAITING_CAL_DATE = "awaiting_cal_date"
AWAITING_CAL_TIME = "awaiting_cal_time"
AWAITING_CART_STORE = "awaiting_cart_store"
AWAITING_EMAIL_EDIT = "awaiting_email_edit"


async def run_deep_scan(business_name: str, address: str, place_id: str = "") -> dict:
    """AI deep scan: search the web for owner name, founding date, location changes."""
    results = {
        'owner_name': None,
        'founded': None,
        'locations_note': None,
        'recent_news': None,
        'signals': None,
    }
    
    try:
        import subprocess
        city_state = ""
        if address:
            parts = address.split(',')
            if len(parts) >= 2:
                city_state = ','.join(parts[-2:]).strip()
        
        search_query = f"{business_name} {city_state} owner founded history"
        
        # Use DuckDuckGo API (no key needed)
        import urllib.request
        ddg_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(search_query)}&format=json&no_html=1&skip_disambig=1"
        
        req = urllib.request.Request(ddg_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            ddg_data = json.loads(resp.read().decode())
        
        abstract = ddg_data.get('AbstractText', '')
        answer = ddg_data.get('Answer', '')
        infobox = ddg_data.get('Infobox', {})
        
        combined_text = f"{abstract} {answer}"
        
        # Parse infobox for founding year and owner
        if infobox and infobox.get('content'):
            for item in infobox['content']:
                label = item.get('label', '').lower()
                val = item.get('value', '')
                if 'founded' in label or 'established' in label or 'opened' in label:
                    results['founded'] = str(val)[:50]
                elif 'owner' in label or 'founder' in label or 'ceo' in label:
                    results['owner_name'] = str(val)[:60]
        
        # Fallback: try to extract owner from abstract text
        if not results['owner_name'] and combined_text:
            import re
            owner_patterns = [
                r'(?:owned|founded|started|opened) by ([A-Z][a-z]+ [A-Z][a-z]+)',
                r'owner[,\s]+([A-Z][a-z]+ [A-Z][a-z]+)',
                r'([A-Z][a-z]+ [A-Z][a-z]+)[,\s]+(?:owner|founder|proprietor)',
            ]
            for pat in owner_patterns:
                m = re.search(pat, combined_text)
                if m:
                    results['owner_name'] = m.group(1)
                    break
        
        # Extract founding year
        if not results['founded'] and combined_text:
            import re
            year_m = re.search(r'(?:founded|established|opened|since|in)\s+(\d{4})', combined_text, re.IGNORECASE)
            if year_m:
                results['founded'] = year_m.group(1)
        
        # Check related topics for location expansion clues
        related = ddg_data.get('RelatedTopics', [])
        location_keywords = ['new location', 'second location', 'moved', 'expansion', 'opening', 'closed', 'relocated']
        location_notes = []
        for topic in related[:5]:
            text = topic.get('Text', '').lower()
            if any(kw in text for kw in location_keywords):
                location_notes.append(topic.get('Text', '')[:80])
        if location_notes:
            results['locations_note'] = location_notes[0]
        
        # If we got abstract, summarize as recent signals
        if abstract and len(abstract) > 30:
            results['signals'] = abstract[:200]
            
    except Exception as e:
        logger.warning(f"Deep scan error: {e}")
        results['signals'] = "Web lookup unavailable — try manually searching the business name."
    
    return results


def build_store_reference(store_num: str, store_dict: dict) -> str:
    """Build a human-friendly store reference.
    
    e.g., "Fred Meyer in Vancouver" or "Fred Meyer on 117th in Vancouver"
    (adds street disambiguation if multiple stores of same chain in same city)
    """
    if not store_dict and not store_num:
        return "your local store"
    
    chain = store_dict.get('GroceryChain', '') if store_dict else ''
    city = store_dict.get('City', '') if store_dict else ''
    state = store_dict.get('State', '') if store_dict else ''
    address = store_dict.get('Address', '') if store_dict else ''
    
    if not chain:
        return "your local store"
    
    # Check if multiple stores of same chain exist in same city
    same_chain_same_city = [
        s for s in STORES_LIST
        if s.get('GroceryChain', '').lower() == chain.lower()
        and s.get('City', '').lower() == city.lower()
        and s.get('State', '').lower() == state.lower()
        and s.get('StoreName') != store_num
    ]
    
    if same_chain_same_city and address:
        # Extract a memorable street reference from address
        # e.g., "14800 NE 117th Ave, Vancouver, WA" → "117th"
        street_ref = extract_street_ref(address)
        if street_ref:
            return f"{chain} on {street_ref} in {city}"
    
    if city:
        return f"{chain} in {city}"
    return chain


def extract_street_ref(address: str) -> str:
    """Extract a short, memorable street name from a full address.
    
    e.g., '14800 NE 117th Ave' → '117th Ave'
         '1234 Main Street' → 'Main St'
    """
    if not address:
        return ""
    
    import re
    # Get the street part (before the first comma)
    street = address.split(',')[0].strip()
    
    # Try to find numbered street: "NE 117th Ave" → "117th"
    m = re.search(r'\b(\d+(?:st|nd|rd|th))\b', street, re.IGNORECASE)
    if m:
        return m.group(1)
    
    # Try to find named street: strip house number, return street name
    # "1234 Main Street" → "Main"
    parts = street.split()
    if len(parts) >= 2 and parts[0].isdigit():
        # Drop house number and directional prefix (NE, SW, etc.)
        rest = parts[1:]
        if rest and re.match(r'^(NE|NW|SE|SW|N|S|E|W)$', rest[0], re.I):
            rest = rest[1:]
        if rest:
            # Drop suffix (St, Ave, Blvd, etc.)
            suffixes = {'st', 'ave', 'blvd', 'dr', 'rd', 'ln', 'ct', 'way', 'pl', 'street', 'avenue', 'boulevard', 'drive', 'road', 'lane', 'court'}
            if rest[-1].lower().rstrip('.') in suffixes:
                rest = rest[:-1]
            return ' '.join(rest)
    
    return ""


def find_nearest_stores(latitude: float, longitude: float, limit: int = 10) -> List[Dict]:
    """Find stores nearest to a given location using Haversine distance.
    
    Returns list of dicts with: store_num, name, chain, city, state, distance_miles
    """
    from math import radians, cos, sin, asin, sqrt
    
    def haversine(lat1, lon1, lat2, lon2):
        """Calculate distance between two lat/lon points in miles."""
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        km = 6371 * c
        return km * 0.621371  # Convert km to miles
    
    distances = []
    for store_num, store in STORES.items():
        try:
            store_lat = float(store.get('latitude', 0))
            store_lon = float(store.get('longitude', 0))
            if store_lat and store_lon:
                dist = haversine(latitude, longitude, store_lat, store_lon)
                distances.append({
                    'store_num': store_num,
                    'name': store.get('StoreName', store_num),
                    'chain': store.get('GroceryChain', '?'),
                    'city': store.get('City', '?'),
                    'state': store.get('State', '?'),
                    'distance_miles': round(dist, 1),
                    'cycle': store.get('Cycle', '?'),
                    'case_count': store.get('Case Count', '?'),
                })
        except (ValueError, TypeError):
            continue
    
    # Sort by distance and return top N
    distances.sort(key=lambda x: x['distance_miles'])
    return distances[:limit]


async def show_nearest_stores_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, stores_list: List[Dict]):
    """Show nearest stores with selection buttons for prospecting/rates/audit."""
    query = update.callback_query
    
    if not stores_list:
        await query.answer("❌ No stores found nearby. Try a different location.", show_alert=True)
        return
    
    text = "📍 *Stores Near You*\n\n"
    text += "Select a store to get started:\n\n"
    
    buttons = []
    for store in stores_list:
        store_display = f"{store['chain']} - {store['distance_miles']}mi"
        buttons.append([InlineKeyboardButton(store_display, callback_data=f"nearme_{store['store_num']}")])
    
    buttons.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")])
    
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


def draft_smart_appointment_email(business_name: str, owner_name: str, category: str, rep_name: str, store_ref: str) -> str:
    """Draft a personalized, vague-but-enticing appointment request email.
    
    Personalized with:
    - Rep's real name
    - Business owner's name (if known)
    - Store chain + city (+ street if multiple in same city)
    - Category-specific social proof hook
    - Goal: 10-15 min appointment
    """
    # Greeting
    if owner_name and owner_name.lower() not in ('unknown', 'n/a', ''):
        # Use first name only
        first_name = owner_name.strip().split()[0]
        greeting = f"Hi {first_name},"
    else:
        # Use business name naturally
        short_name = business_name.split()[0] if business_name else "there"
        greeting = f"Hi,"
    
    # Category-specific social proof hook
    # Keys match both emoji category names (e.g. "🍽️ restaurants") and plain text variants
    category_hooks = {
        "restaurant": "restaurants and eateries",
        "food": "restaurants and eateries",
        "food & drink": "restaurants and eateries",
        "bakery": "bakeries and food shops",
        "coffee": "coffee shops and cafes",
        "cafe": "coffee shops and cafes",
        "automotive": "auto service and tire shops",
        "auto": "auto service and tire shops",
        "auto service": "auto service and tire shops",
        "beauty": "salons, spas, and beauty studios",
        "salon": "salons, spas, and beauty studios",
        "spa": "salons, spas, and beauty studios",
        "wellness": "wellness and fitness studios",
        "gym": "gyms and fitness centers",
        "fitness": "gyms and fitness centers",
        "health": "health and wellness professionals",
        "medical": "medical and dental practices",
        "dental": "dental practices",
        "dentist": "dental practices",
        "veterinary": "veterinary and pet care businesses",
        "vet": "veterinary and pet care businesses",
        "home services": "home service contractors and tradespeople",
        "home": "home service contractors and tradespeople",
        "professional": "professional service businesses",
        "retail": "local retail shops and boutiques",
        "pets": "pet care and retail businesses",
        "real estate": "real estate offices and agencies",
        "financial services": "financial and insurance professionals",
        "insurance": "insurance professionals and agencies",
        "dispensary": "dispensaries and specialty retailers",
        "cannabis": "dispensaries and cannabis retailers",
        "kids": "child care and learning centers",
        "childcare": "child care and learning centers",
        "daycare": "daycares and preschools",
        "preschool": "preschools and learning centers",
        "senior": "senior living and adult care facilities",
        "assisted living": "senior living communities",
        "adult care": "adult day care and senior centers",
        "clothing": "clothing boutiques and retailers",
    }
    cat_lower = (category or '').lower().strip()
    category_phrase = None
    if cat_lower:
        for key, phrase in category_hooks.items():
            if key in cat_lower or cat_lower in key:
                category_phrase = phrase
                break
    if not category_phrase:
        category_phrase = "businesses like yours"
    
    # Handle "Unknown" business name gracefully
    business_ref = business_name if business_name and business_name.lower() != "unknown" else "your business"
    
    email_body = f"""{greeting}

My name is {rep_name} — I work with IndoorMedia, and we partner with {store_ref} to help local businesses connect with their best customers right at the checkout.

I've been seeing some really strong results with {category_phrase} in your area, and I think there's a real opportunity for {business_ref} that I'd love to share with you.

Would you have 10–15 minutes this week? I won't waste your time — I'll come to you, show you what's working locally, and you can decide from there if it makes sense.

Looking forward to connecting,

{rep_name}
IndoorMedia | Field Representative"""
    
    return email_body


def draft_appointment_email(prospect_name: str, owner_name: str, business_name: str, rep_name: str, store_chain: str = "") -> str:
    """Draft a brief appointment request email (legacy)."""
    # Determine opening based on whether we have owner name
    if owner_name and owner_name.lower() != "unknown":
        greeting = f"Hi {owner_name},"
    else:
        greeting = f"Hi {business_name.split()[0]},"  # Use first word of business name
    
    # Build store reference
    store_ref = f"at {store_chain}" if store_chain else "in your neighborhood"
    
    # Brief value proposition
    email_body = f"""{greeting}

I'm {rep_name} with IndoorMedia. We help businesses like {business_name} reach their local customers through register tape advertising {store_ref}.

We've seen great results for similar businesses in your area — increased foot traffic and repeat customers. I'd love to share what we're doing in 10-15 minutes and show you how it could work for you.

Would you be available this week? I'm flexible with timing.

Thanks,
{rep_name}
IndoorMedia"""
    
    return email_body


def draft_followup_email(business_name: str, owner_name: str, rep_name: str, store_ref: str) -> str:
    """Draft a follow-up email (3-5 days after no response)."""
    if owner_name and owner_name.lower() not in ('unknown', 'n/a', ''):
        first_name = owner_name.strip().split()[0]
        greeting = f"Hi {first_name},"
    else:
        greeting = f"Hi,"
    
    # Handle "Unknown" business name gracefully
    business_ref = business_name if business_name and business_name.lower() != "unknown" else "your business"
    followup_ref = f"about {business_ref} and IndoorMedia" if business_ref != "your business" else f"about IndoorMedia"
    
    email_body = f"""{greeting}

Just wanted to follow up on my previous message {followup_ref}.

I know life gets busy — no worries if it got lost in the shuffle. I still think there's a real opportunity here, and I'd hate for you to miss out on what's working for similar businesses in your area.

Are you free for a quick 10-minute call this week? I can work around your schedule.

Best,
{rep_name}
IndoorMedia"""
    
    return email_body


def draft_roi_email(business_name: str, owner_name: str, rep_name: str, store_ref: str, category: str) -> str:
    """Draft an ROI/value-focused email with social proof."""
    if owner_name and owner_name.lower() not in ('unknown', 'n/a', ''):
        first_name = owner_name.strip().split()[0]
        greeting = f"Hi {first_name},"
    else:
        greeting = f"Hi,"
    
    # Category-specific social proof
    proof_points = {
        "restaurant": "restaurants are seeing 15-25% increases in repeat customer traffic",
        "food": "restaurants are seeing 15-25% increases in repeat customer traffic",
        "automotive": "auto shops are booking 20-30% more service appointments",
        "auto service": "auto shops are booking 20-30% more service appointments",
        "beauty": "salons and spas are getting 25-35% more return visits",
        "salon": "salons and spas are getting 25-35% more return visits",
        "spa": "salons and spas are getting 25-35% more return visits",
        "wellness": "wellness businesses report stronger customer retention and loyalty",
        "gym": "gyms and fitness centers are seeing stronger membership growth and retention",
        "fitness": "gyms and fitness centers are seeing stronger membership growth and retention",
        "health": "health and wellness professionals are attracting more local patients and referrals",
        "medical": "medical and dental practices see improved patient engagement and loyalty",
        "dental": "dental practices see improved patient engagement, appointment attendance, and loyalty",
        "dentist": "dental practices see improved patient engagement, appointment attendance, and loyalty",
        "home services": "home service contractors are getting 20-30% more qualified local leads",
        "professional": "professional services are building stronger local networks",
        "veterinary": "veterinary practices are seeing better appointment fill rates and patient loyalty",
        "vet": "veterinary practices are seeing better appointment fill rates and patient loyalty",
        "retail": "retail shops are seeing 15-20% more foot traffic",
        "pets": "pet care and retail businesses report much higher repeat visit rates",
        "real estate": "real estate agents are getting more local buyer/seller connections",
        "financial services": "financial professionals are building stronger local client bases",
        "insurance": "insurance professionals are building stronger local client bases",
        "kids": "child care and learning centers are filling spots faster through local awareness",
        "childcare": "child care and learning centers are filling spots faster through local awareness",
        "daycare": "daycares and learning centers are seeing stronger enrollment through local family outreach",
        "preschool": "preschools are attracting more families through targeted local visibility",
        "senior": "senior living and adult care facilities are building trust with local families",
        "assisted living": "assisted living communities are connecting with families during critical decision moments",
        "adult care": "adult care centers are gaining visibility with local caregivers and families",
        "dispensary": "dispensaries are building loyal customer bases through consistent local awareness",
        "cannabis": "cannabis retailers are seeing strong repeat traffic and customer loyalty",
        "clothing": "boutique retailers are attracting style-conscious local shoppers",
        "retail": "retail shops are seeing 15-20% more foot traffic",
        "bakery": "bakeries and food shops are seeing increased weekday and weekend traffic",
        "coffee": "coffee shops are seeing stronger daily customer traffic and repeat visits",
        "cafe": "coffee shops are seeing stronger daily customer traffic and repeat visits",
    }
    
    cat_lower = (category or '').lower().strip()
    proof_point = "local businesses in your category are seeing strong results"
    for key, proof in proof_points.items():
        if key in cat_lower or cat_lower in key:
            proof_point = proof
            break
    
    # Handle "Unknown" business name gracefully
    business_ref = business_name if business_name and business_name.lower() != "unknown" else "your business"
    
    email_body = f"""{greeting}

I wanted to reach out because we've been working with {store_ref}, and right now {proof_point}.

We've got video testimonials from actual business owners showing exactly what they're doing — increased traffic, better customer loyalty, repeat business. {business_ref} is in the perfect position to benefit from this.

If you've ever thought about boosting local visibility, this is a good time. I'd love to share the numbers (literally) and show you a 5-minute case study from someone just like you.

Free consultation, no pressure — just insights that could change your year.

Can we grab 15 minutes this week?

{rep_name}
IndoorMedia"""
    
    return email_body


def draft_reengagement_email(business_name: str, owner_name: str, rep_name: str, store_ref: str) -> str:
    """Draft a re-engagement email (reaching out to past contacts)."""
    if owner_name and owner_name.lower() not in ('unknown', 'n/a', ''):
        first_name = owner_name.strip().split()[0]
        greeting = f"Hi {first_name},"
    else:
        greeting = f"Hi,"
    
    # Handle "Unknown" business name gracefully
    business_ref = business_name if business_name and business_name.lower() != "unknown" else "your business"
    
    email_body = f"""{greeting}

It's been a while! I wanted to reconnect because things have changed quite a bit at IndoorMedia, and I think {business_ref} could really benefit from what we're doing now.

We've had some major wins with {store_ref} — businesses very similar to yours are seeing measurable results. I'd love to show you what's different this time around.

No strings attached — just a quick conversation about whether this makes sense for your business.

Free to chat this week?

{rep_name}
IndoorMedia"""
    
    return email_body


def draft_limited_time_email(business_name: str, owner_name: str, rep_name: str, store_ref: str) -> str:
    """Draft a limited-time/special offer email."""
    if owner_name and owner_name.lower() not in ('unknown', 'n/a', ''):
        first_name = owner_name.strip().split()[0]
        greeting = f"Hi {first_name},"
    else:
        greeting = f"Hi,"
    
    # Handle "Unknown" business name gracefully
    business_ref = business_name if business_name and business_name.lower() != "unknown" else "your business"
    
    email_body = f"""{greeting}

Quick heads up: we're running a limited partnership program this quarter with {store_ref}, and I'm reaching out to a few select businesses like {business_ref} before I move to other prospects.

The window is open through end of month. If you've been thinking about running local ads but weren't sure where to start, this could be exactly the right time.

I can show you the numbers in 10 minutes, and you'll know exactly what to expect. Fair?

{rep_name}
IndoorMedia | Limited Partnership Program"""
    
    return email_body


# ========================================================================
# CONTRACT & CUSTOMER EMAILS (Post-Signature)
# ========================================================================

def draft_kickoff_email(business_name: str, owner_name: str, rep_name: str, store_ref: str) -> str:
    """Draft kickoff/what's next email (after contract signed)."""
    if owner_name and owner_name.lower() not in ('unknown', 'n/a', ''):
        first_name = owner_name.strip().split()[0]
        greeting = f"Hi {first_name},"
    else:
        greeting = f"Hi,"
    
    business_ref = business_name if business_name and business_name.lower() != "unknown" else "your business"
    
    email_body = f"""{greeting}

Thank you for partnering with IndoorMedia! We're excited to work with {business_ref}. Here's what's next:

**THE PROOF PROCESS**
In the coming weeks, you'll receive a proof of your ad. This is your chance to make sure it's exactly what you want. Please be vocal about any changes—we want to get it perfect for you.

**YOUR AD IS FLEXIBLE**
Remember, you can change your ad quarterly, so if something isn't working, we can adjust it. That said, once we launch, let's give it time to work.

**INSTALLATION & SIGNAGE**
Expect us at {store_ref} around the time of installation. We'll hand you a roll of your register tape and put up signage in the store. We'll coordinate the timing with you beforehand.

**GROWTH TAKES TIME**
This program grows with time. Expect a slower start that gains momentum. Customers need to see your ad multiple times before it clicks—that's where the results come from.

Looking forward to great things ahead!

Best,
{rep_name}
IndoorMedia"""
    
    return email_body


def draft_checkin_email(business_name: str, owner_name: str, rep_name: str, store_ref: str) -> str:
    """Draft check-in/audit email (weeks/months after install)."""
    if owner_name and owner_name.lower() not in ('unknown', 'n/a', ''):
        first_name = owner_name.strip().split()[0]
        greeting = f"Hi {first_name},"
    else:
        greeting = f"Hi,"
    
    business_ref = business_name if business_name and business_name.lower() != "unknown" else "your business"
    
    email_body = f"""{greeting}

I wanted to check in and see how everything is going with your register tape campaign at {store_ref}. We love having {business_ref} as a partner!

A few things I'd love to discuss:
• How the campaign is performing for you
• Any feedback on your ad or messaging
• Opportunities to optimize or adjust
• Plans for your renewal

Would you have a few minutes this week to connect?

Best,
{rep_name}
IndoorMedia"""
    
    return email_body


def draft_upsell_email(business_name: str, owner_name: str, rep_name: str, store_ref: str) -> str:
    """Draft upsell/expansion email (when results are strong)."""
    if owner_name and owner_name.lower() not in ('unknown', 'n/a', ''):
        first_name = owner_name.strip().split()[0]
        greeting = f"Hi {first_name},"
    else:
        greeting = f"Hi,"
    
    business_ref = business_name if business_name and business_name.lower() != "unknown" else "your business"
    
    email_body = f"""{greeting}

Your campaign at {store_ref} is performing great! We're seeing solid results, and I wanted to talk about expanding.

Here are a few options:
• Add a nearby {store_ref} location to amplify your reach
• Increase your ad frequency at this location
• Test a new location in a different area
• Refresh your creative to keep it fresh

The momentum is real. Let's capitalize on it.

When can we schedule a quick call?

Best,
{rep_name}
IndoorMedia"""
    
    return email_body


def draft_renewal_email(business_name: str, owner_name: str, rep_name: str, store_ref: str) -> str:
    """Draft renewal email (contract ending soon)."""
    if owner_name and owner_name.lower() not in ('unknown', 'n/a', ''):
        first_name = owner_name.strip().split()[0]
        greeting = f"Hi {first_name},"
    else:
        greeting = f"Hi,"
    
    business_ref = business_name if business_name and business_name.lower() != "unknown" else "your business"
    
    email_body = f"""{greeting}

Your IndoorMedia partnership at {store_ref} is coming up for renewal. Before we renew, I want to make sure the program is still working for {business_ref}.

Let's talk about:
• Overall results and ROI
• What's working + what we should adjust
• Your plans for the next term
• Any new locations you want to add

I'd love to set up a time to review everything together. How does this week look?

Best,
{rep_name}
IndoorMedia"""
    
    return email_body


def get_meeting_times():
    """Calculate suggested meeting times: 2 hours from now (rounded to 15 min) and alternative."""
    now = datetime.now()
    
    # First option: 2 hours from now, rounded to nearest 15 minutes
    two_hours = now + timedelta(hours=2)
    minutes = two_hours.minute
    rounded_minutes = (minutes // 15 + 1) * 15
    if rounded_minutes == 60:
        first_time = two_hours.replace(minute=0, hour=two_hours.hour + 1)
    else:
        first_time = two_hours.replace(minute=rounded_minutes)
    
    first_time_str = first_time.strftime("%a %b %d at %I:%M %p")
    
    # Second option based on first time
    if first_time.hour >= 16:  # 4 PM or later
        # Next calendar day, early morning (9 AM)
        second_time = (first_time + timedelta(days=1)).replace(hour=9, minute=0)
        second_time_str = second_time.strftime("%a %b %d at 9:00 AM (next day)")
    else:
        # Later same day (4 PM or next available)
        second_time = first_time.replace(hour=16, minute=0)
        if second_time <= now:
            second_time = (first_time + timedelta(days=1)).replace(hour=9, minute=0)
            second_time_str = second_time.strftime("%a %b %d at 9:00 AM (next day)")
        else:
            second_time_str = second_time.strftime("%a %b %d at %I:%M %p")
    
    return first_time_str, second_time_str

# --- Audit Module ---
AWAITING_AUDIT_STORE = "awaiting_audit_store"
AWAITING_AUDIT_DELIVERY = "awaiting_audit_delivery"
AWAITING_AUDIT_INVENTORY = "awaiting_audit_inventory"

# Testimonial submission flow
AWAITING_TEST_NAME = "awaiting_test_name"
AWAITING_TEST_BUSINESS = "awaiting_test_business"
AWAITING_TEST_ADDRESS = "awaiting_test_address"
AWAITING_TEST_PHONE = "awaiting_test_phone"
AWAITING_TEST_COUPONS = "awaiting_test_coupons"
AWAITING_TEST_TICKET = "awaiting_test_ticket"
AWAITING_TEST_ROI = "awaiting_test_roi"
AWAITING_TEST_DURATION = "awaiting_test_duration"
AWAITING_TEST_RENEW = "awaiting_test_renew"
AWAITING_TEST_RECOMMEND = "awaiting_test_recommend"
AWAITING_TEST_COMMENTS = "awaiting_test_comments"
AWAITING_TEST_CHAIN = "awaiting_test_chain"
AWAITING_TEST_ZONE = "awaiting_test_zone"
AWAITING_TEST_STORE = "awaiting_test_store"
AWAITING_TEST_COUPON_IMAGE = "awaiting_test_coupon_image"

async def handle_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route callback to appropriate handler."""
    query = update.callback_query
    data = query.data
    
    try:
        # Handle universal back button
        if data.startswith("back_"):
            await query.answer()
            prev_screen = pop_nav(context)
            # Route to the previous screen's callback
            # Re-trigger the callback data for that screen
            new_callback = prev_screen['callback']
            data = new_callback
            # Fall through to handle the actual callback below
        
        if data.startswith("expand_"):
            prospect_id = data.replace("expand_", "")
            prospect = context.user_data.get('prospects', {}).get(prospect_id, {})
            await query.answer()
            
            # Validate prospect data exists
            if not prospect or not isinstance(prospect, dict):
                logger.error(f"❌ Prospect not found or invalid: {prospect_id}")
                await query.edit_message_text(
                    "❌ Prospect data not found. Please try again or return to main menu.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
                )
                return
            
            # Get stored prospect info with safe fallbacks
            business_name = prospect.get('name', 'Unknown')
            address = prospect.get('address', '')
            phone = prospect.get('phone', 'No phone found')
            distance = prospect.get('distance_miles', 'N/A')
            score = prospect.get('likelihood_score', 0)
            website = prospect.get('website', '')
            rating = prospect.get('rating', 0)
            rating_count = prospect.get('user_ratings_total', 0)
            opening_hours = prospect.get('opening_hours')
            
            # Validate critical fields
            if not business_name or business_name == 'Unknown':
                logger.warning(f"Missing business name for prospect {prospect_id}")
            if not address:
                logger.warning(f"Missing address for prospect {prospect_id}")
            
            try:
                # Emoji rating
                if score >= 80:
                    emoji = "🔥"
                elif score >= 70:
                    emoji = "⭐"
                else:
                    emoji = "👀"
                
                # Build complete message with all info
                text = f"{emoji} *{business_name}*\n"
                text += f"📊 Likelihood: {score}/100"
                
                # Star rating (separate from likelihood score)
                if rating and rating > 0:
                    try:
                        stars = "⭐" * round(rating)
                        text += f"  |  {stars} {rating}/5"
                        if rating_count:
                            text += f" ({rating_count:,} reviews)"
                    except:
                        pass
                text += "\n"
                
                # Contact info - only add if available
                if distance and distance != 'N/A':
                    text += f"📏 Distance: {distance} mi\n"
                if phone and phone != 'No phone found':
                    text += f"📞 {phone}\n"
                
                # Email if available
                email = prospect.get('email', '')
                if email:
                    text += f"📧 {email}\n"
                
                # Address in code block
                if address:
                    text += f"📍 `{address}`\n"
                
                # Today's hours (from opening_hours)
                if opening_hours:
                    weekday_text = opening_hours.get('weekday_text', [])
                    open_now = opening_hours.get('open_now')
                    
                    # Show open/closed status
                    if open_now is True:
                        text += f"🟢 *Open now*"
                    elif open_now is False:
                        text += f"🔴 *Closed now*"
                    
                    # Show today's hours
                    if weekday_text:
                        today_idx = datetime.now().weekday()  # 0=Mon, 6=Sun
                        # weekday_text is [Mon, Tue, Wed, Thu, Fri, Sat, Sun]
                        day_map = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6}
                        if today_idx < len(weekday_text):
                            today_hours = weekday_text[day_map[today_idx]]
                            # Strip day name (e.g., "Monday: 9:00 AM – 5:00 PM" → "9:00 AM – 5:00 PM")
                            if ':' in today_hours:
                                hours_only = today_hours.split(':', 1)[1].strip()
                                text += f" · {hours_only}"
                    text += "\n"
                
                # Website link
                if website:
                    text += f"🌐 [Visit Website]({website})\n"
                
                # Advertising signals
                advertising_signals = prospect.get('advertising_signal', {})
                if advertising_signals:
                    platforms = []
                    if advertising_signals.get('greet_magazine'):
                        platforms.append("📰 Greet")
                    if advertising_signals.get('facebook_ads'):
                        platforms.append("📘 Facebook")
                    if advertising_signals.get('google_local_services'):
                        platforms.append("🔍 Google Local")
                    if advertising_signals.get('groupon'):
                        platforms.append("🎁 Groupon")
                    if advertising_signals.get('found_advertising'):
                        platforms.append("📢 Active Ads")
                    
                    if platforms:
                        text += f"\n💡 *Advertising on:* {' | '.join(platforms)}\n"
                
                # Deep scan results if cached
                deep_scan = prospect.get('deep_scan', {})
                if deep_scan:
                    text += "\n🔍 *Deep Scan Results:*\n"
                    if deep_scan.get('owner_name'):
                        text += f"👤 Owner: {deep_scan['owner_name']}\n"
                    if deep_scan.get('founded'):
                        text += f"📅 Founded: {deep_scan['founded']}\n"
                    if deep_scan.get('locations_note'):
                        text += f"📍 Locations: {deep_scan['locations_note']}\n"
                    if deep_scan.get('recent_news'):
                        text += f"📰 Recent: {deep_scan['recent_news']}\n"
                
                # Build URLs for buttons (safely handle missing values)
                safe_business = urllib.parse.quote(business_name or "Unknown")
                safe_address = urllib.parse.quote(address or "")
                mappoint_url = f"https://sales.indoormedia.com/Mappoint?business={safe_business}&address={safe_address}"
                google_maps_url = f"https://www.google.com/maps/search/{safe_address}" if safe_address else "https://www.google.com/maps"
                
                # Show inline notepad if notes exist
                existing_notes = context.user_data.get('prospect_notes', {}).get(prospect_id, {}).get('notes', '')
                if existing_notes:
                    text += f"\n📝 *Notes:* _{existing_notes[:80]}{'...' if len(existing_notes) > 80 else ''}_\n"
                
                # Get store number for ROI calculator link
                store_number = prospect.get('store', '')
                
                # Expanded buttons (safe construction)
                buttons = []
                
                # Website button (Telegram doesn't support tel: URLs in buttons)
                if website:
                    web_url = website if website.startswith("http") else f"https://{website}"
                    buttons.append([InlineKeyboardButton("🌐 Website", url=web_url)])
                
                # Maps row
                maps_row = []
                if google_maps_url:
                    maps_row.append(InlineKeyboardButton("📍 Maps", url=google_maps_url))
                if mappoint_url:
                    maps_row.append(InlineKeyboardButton("🗺️ Mappoint", url=mappoint_url))
                if maps_row:
                    buttons.append(maps_row)
                
                # Save & Video row
                buttons.append([
                    InlineKeyboardButton("💾 Save", callback_data=f"save_{prospect_id}"),
                    InlineKeyboardButton("🎬 Video", callback_data=f"video_{prospect_id}"),
                ])
                
                # Notes & Testimonials row
                buttons.append([
                    InlineKeyboardButton("📝 Notes", callback_data=f"note_{prospect_id}"),
                    InlineKeyboardButton("📋 Testimonials", callback_data=f"testimonials_{prospect_id}"),
                ])
                
                # Email row
                buttons.append([
                    InlineKeyboardButton("✉️ Draft Email", callback_data=f"draftemail_{prospect_id}"),
                ])
                
                # Calendar button
                buttons.append([InlineKeyboardButton("📅 Calendar", callback_data=f"cal_{prospect_id}")])
                
                # Add collapse and menu buttons
                buttons.extend([
                    [InlineKeyboardButton("◀️ Collapse", callback_data=f"collapse_{prospect_id}")],
                    [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")],
                ])
                
                # Validate text isn't empty
                if not text or text.strip() == "":
                    text = f"📍 *{business_name}*\n(No detailed info available)"
                
                # Send message
                logger.info(f"✅ Expanding prospect {prospect_id}: {business_name}")
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
            except Exception as e:
                logger.error(f"❌ Error expanding prospect {prospect_id}: {str(e)}")
                logger.error(f"Exception type: {type(e).__name__}")
                logger.error(f"Traceback: {e}", exc_info=True)
                try:
                    error_detail = f"Error: {str(e)[:100]}"
                    await query.edit_message_text(
                        f"❌ Error loading prospect details.\n\n{error_detail}\n\nPlease try again.",
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
                    )
                except Exception as edit_err:
                    logger.error(f"Could not edit message: {edit_err}")
                    try:
                        await query.answer("Error occurred. Try again from main menu.", show_alert=True)
                    except:
                        pass
        elif data.startswith("deepscan_"):
            try:
                prospect_id = data.replace("deepscan_", "")
                prospect = context.user_data.get('prospects', {}).get(prospect_id, {})
                await query.answer("🔍 Scanning... this may take 10-20 seconds")
                
                business_name = prospect.get('name', 'Unknown')
                address = prospect.get('address', '')
                place_id = prospect.get('place_id', '')
                
                # Show scanning message
                await query.edit_message_text(
                    f"🔍 *AI Deep Scan: {business_name}*\n\n⏳ Searching for owner, founding date, location history...",
                    parse_mode="Markdown"
                )
                
                # Run the deep scan
                scan_results = await run_deep_scan(business_name, address, place_id)
                
                # Cache results in prospect data
                if 'prospects' in context.user_data and prospect_id in context.user_data['prospects']:
                    context.user_data['prospects'][prospect_id]['deep_scan'] = scan_results
                
                # Build result text
                text = f"🔍 *AI Deep Scan: {business_name}*\n\n"
                
                if scan_results.get('owner_name'):
                    text += f"👤 *Owner:* {scan_results['owner_name']}\n"
                else:
                    text += f"👤 *Owner:* Not found publicly\n"
                
                if scan_results.get('founded'):
                    text += f"📅 *Founded / Open Since:* {scan_results['founded']}\n"
                else:
                    text += f"📅 *Founded:* Unknown\n"
                
                if scan_results.get('locations_note'):
                    text += f"📍 *Locations:* {scan_results['locations_note']}\n"
                
                if scan_results.get('recent_news'):
                    text += f"\n📰 *Recent News / Changes:*\n_{scan_results['recent_news']}_\n"
                
                if scan_results.get('signals'):
                    text += f"\n💡 *Signals:* {scan_results['signals']}\n"
                
                text += f"\n_Scanned {datetime.now().strftime('%b %d, %Y %I:%M %p')}_"
                
                buttons = [
                    [InlineKeyboardButton("✉️ Draft Email", callback_data=f"draftemail_{prospect_id}")],
                    [InlineKeyboardButton("⬅️ Back to Card", callback_data=f"expand_{prospect_id}")],
                ]
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
            except Exception as e:
                logger.error(f"Error in deepscan handler: {e}", exc_info=True)
                try:
                    await query.edit_message_text(
                        f"❌ Error scanning prospect. Please try again.",
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"expand_{prospect_id}")]])
                    )
                except:
                    try:
                        await query.answer("Error scanning. Try again.", show_alert=True)
                    except:
                        pass
        
        elif data.startswith("draftemail_"):
            try:
                prospect_id = data.replace("draftemail_", "")
                prospect = context.user_data.get('prospects', {}).get(prospect_id, {})
                await query.answer()
                
                # Store prospect info in context for template generation
                context.user_data['draft_prospect'] = {
                    'id': prospect_id,
                    'name': prospect.get('name', 'Unknown'),
                    'category': prospect.get('category', ''),
                    'store_dict': prospect.get('store_dict', {}),
                    'store_num': prospect.get('store', ''),
                    'contact_name': prospect.get('contact_name', ''),
                    'deep_scan': prospect.get('deep_scan', {}),
                }
                
                text = "✉️ *Email Templates*\n\nChoose a template for your outreach:\n"
                
                buttons = [
                    [InlineKeyboardButton("🎯 Initial Appointment", callback_data=f"emailtpl_{prospect_id}_initial")],
                    [InlineKeyboardButton("📊 ROI / Value Focused", callback_data=f"emailtpl_{prospect_id}_roi")],
                    [InlineKeyboardButton("⏰ Follow-up (No Response)", callback_data=f"emailtpl_{prospect_id}_followup")],
                    [InlineKeyboardButton("🔄 Re-engagement", callback_data=f"emailtpl_{prospect_id}_reengagement")],
                    [InlineKeyboardButton("⚡ Limited Time Offer", callback_data=f"emailtpl_{prospect_id}_limited")],
                    [InlineKeyboardButton("⬅️ Back to Card", callback_data=f"expand_{prospect_id}")],
                ]
                
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
            except Exception as e:
                logger.error(f"Error in draftemail handler: {e}")
                try:
                    await query.answer("Error loading email templates. Try again.", show_alert=True)
                except:
                    pass
        elif data.startswith("emailtpl_"):
            try:
                # Handle email template selection and generation
                parts = data.split("_")
                prospect_id = parts[1]
                template_type = parts[2] if len(parts) > 2 else "initial"
                
                prospect_info = context.user_data.get('draft_prospect', {})
                if not prospect_info:
                    await query.answer("Prospect info not found", show_alert=True)
                    return
                
                await query.answer()
                
                business_name = prospect_info['name']
                category = prospect_info['category']
                rep_name = get_rep_name(update)
                store_dict = prospect_info['store_dict']
                store_num = prospect_info['store_num']
                deep_scan = prospect_info['deep_scan']
                owner_name = deep_scan.get('owner_name', '') or prospect_info['contact_name']
                
                # Build smart store reference
                store_ref = build_store_reference(store_num, store_dict)
                
                # Generate draft based on template type
                if template_type == "initial":
                    draft = draft_smart_appointment_email(
                        business_name=business_name,
                        owner_name=owner_name,
                        category=category,
                        rep_name=rep_name,
                        store_ref=store_ref,
                    )
                    title = "🎯 Initial Appointment Request"
                elif template_type == "roi":
                    draft = draft_roi_email(
                        business_name=business_name,
                        owner_name=owner_name,
                        rep_name=rep_name,
                        store_ref=store_ref,
                        category=category,
                    )
                    title = "📊 ROI / Value Focused"
                elif template_type == "followup":
                    draft = draft_followup_email(
                        business_name=business_name,
                        owner_name=owner_name,
                        rep_name=rep_name,
                        store_ref=store_ref,
                    )
                    title = "⏰ Follow-up Email"
                elif template_type == "reengagement":
                    draft = draft_reengagement_email(
                        business_name=business_name,
                        owner_name=owner_name,
                        rep_name=rep_name,
                        store_ref=store_ref,
                    )
                    title = "🔄 Re-engagement Email"
                elif template_type == "limited":
                    draft = draft_limited_time_email(
                        business_name=business_name,
                        owner_name=owner_name,
                        rep_name=rep_name,
                        store_ref=store_ref,
                    )
                    title = "⚡ Limited Time Offer"
                else:
                    draft = draft_smart_appointment_email(
                        business_name=business_name,
                        owner_name=owner_name,
                        category=category,
                        rep_name=rep_name,
                        store_ref=store_ref,
                    )
                    title = "✉️ Appointment Request"
                
                text = f"✉️ *{title}*\n\n`{draft}`\n\n"
                text += "_Copy this and send via email or text. Edit as needed._"
                if owner_name:
                    text += f"\n\n👤 _Addressed to: {owner_name}_"
                
                buttons = [
                    [InlineKeyboardButton("🔄 Choose Template", callback_data=f"draftemail_{prospect_id}")],
                    [InlineKeyboardButton("⬅️ Back to Card", callback_data=f"expand_{prospect_id}")],
                ]
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
            except Exception as e:
                logger.error(f"Error in emailtpl handler: {e}")
                try:
                    await query.answer("Error generating email. Try again.", show_alert=True)
                except:
                    pass
        
        elif data.startswith("email_"):
            # Legacy email handler — redirect to draftemail
            prospect_id = data.replace("email_", "")
            if "_" in prospect_id:
                pass  # It's email_edit_ or email_send_ — handled elsewhere
            else:
                await query.answer()
                await query.edit_message_text(
                    "⬆️ Use ✉️ Draft Email button above.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"expand_{prospect_id}")]])
                )
        elif data.startswith("email_edit_"):
            prospect_id = data.replace("email_edit_", "")
            await query.answer()
            
            context.user_data[AWAITING_EMAIL_EDIT] = prospect_id
            
            await query.edit_message_text(
                "📝 *Edit Email Draft*\n\n"
                "Send your revised email message:\n\n"
                "_You can modify the draft above_",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data=f"expand_{prospect_id}")]])
            )
        elif data.startswith("email_send_"):
            prospect_id = data.replace("email_send_", "")
            pending = context.user_data.get('pending_email', {})
            
            if not pending:
                await query.answer("Email info not found", show_alert=True)
                return
            
            await query.answer()
            
            email = pending.get('email', '')
            business = pending.get('business', '')
            draft = pending.get('draft', '')
            
            # Save to Gmail drafts
            try:
                # Create a Gmail draft using gog
                cmd = [
                    "gog", "gmail", "draft",
                    email,
                    f"Let's meet: {business}",
                    draft
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    await query.edit_message_text(
                        f"✅ *Draft Saved to Gmail*\n\n"
                        f"To: {email}\n"
                        f"Subject: Let's meet: {business}\n\n"
                        f"_Check your Gmail drafts folder to review and send._",
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"expand_{prospect_id}")]])
                    )
                else:
                    # Fallback: show confirmation anyway
                    await query.edit_message_text(
                        f"✅ *Draft Ready*\n\n"
                        f"To: {email}\n"
                        f"Subject: Let's meet: {business}\n\n"
                        f"_Copy the draft to your email to send._",
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"expand_{prospect_id}")]])
                    )
            except Exception as e:
                logger.warning(f"Could not create Gmail draft: {e}")
                await query.edit_message_text(
                    f"✅ *Draft Ready*\n\n"
                    f"To: {email}\n"
                    f"Subject: Let's meet: {business}\n\n"
                    f"_Copy the draft text to your email to send._",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"expand_{prospect_id}")]])
                )
            
            # Clear pending email
            context.user_data['pending_email'] = {}
        elif data.startswith("invite_reps_"):
            prospect_id = data.replace("invite_reps_", "")
            await query.answer()
            
            event = context.user_data.get('created_event', {})
            if not event:
                await query.edit_message_text(
                    "❌ Event info not found.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"expand_{prospect_id}")]])
                )
                return
            
            # Hardcoded team roster with emails
            reps_list = [
                {"name": "Adan Ramos", "email": "Adan.Ramos@Indoormedia.com"},
                {"name": "Amy Dixon", "email": "Amy.Dixon@indoormedia.com"},
                {"name": "Ben Patacsil", "email": "Ben.Patacsil@Indoormedia.com"},
                {"name": "Christian Johnson", "email": "Christian.Johnson@Indoormedia.com"},
                {"name": "Dave Boring", "email": "Dave.Boring@Indoormedia.com"},
                {"name": "Jan Banks", "email": "Jan.Banks@Indoormedia.com"},
                {"name": "Marty/Anthony Eng", "email": "Anthony.Eng@Indoormedia.com"},
                {"name": "Matt Boozer", "email": "Matthew.Boozer@Indoormedia.com"},
                {"name": "Meghan Wink", "email": "Megan.Wink@Indoormedia.com"},
            ]
            
            # Store rep list for selection
            context.user_data['pending_rep_invite'] = {
                'prospect_id': prospect_id,
                'event': event,
                'reps': reps_list,
            }
            
            # Show rep selection buttons
            buttons = []
            for i, rep in enumerate(reps_list):
                buttons.append([InlineKeyboardButton(rep["name"], callback_data=f"add_rep_invite_{prospect_id}_{i}")])
            
            buttons.append([InlineKeyboardButton("⬅️ Skip", callback_data=f"expand_{prospect_id}")])
            
            await query.edit_message_text(
                "👥 *Select reps to invite to this appointment:*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        elif data.startswith("add_rep_invite_"):
            try:
                # Extract: add_rep_invite_{prospect_id}_{rep_index}
                remainder = data.replace("add_rep_invite_", "")
                parts = remainder.rsplit("_", 1)
                prospect_id = parts[0]
                rep_index = int(parts[1])
            except (ValueError, IndexError) as e:
                logger.error(f"Failed to parse rep invite data: {data} - {e}")
                await query.answer("Invalid rep selection", show_alert=True)
                return
            
            await query.answer()
            
            pending = context.user_data.get('pending_rep_invite', {})
            reps = pending.get('reps', [])
            event = pending.get('event', {})
            
            if rep_index >= len(reps):
                await query.answer("Invalid rep selection", show_alert=True)
                return
            
            rep_info = reps[rep_index]
            selected_rep = rep_info["name"] if isinstance(rep_info, dict) else rep_info
            rep_email = rep_info["email"] if isinstance(rep_info, dict) else f"{rep_info.lower().replace(' ', '.')}@indoormedia.com"
            
            business_name = event.get('business_name', '')
            date_str = event.get('date_str', '')
            time_str = event.get('time_str', '')
            
            # Add rep to calendar event
            try:
                cal_date = event.get('cal_date')
                hour = event.get('hour')
                minute = event.get('minute')
                
                start_time = cal_date.replace(hour=hour, minute=minute)
                end_time = start_time + timedelta(minutes=30)
                
                # Create event on REP's calendar with timezone in RFC3339 format
                # gog expects RFC3339 timestamps (e.g., 2026-03-17T14:30:00-07:00)
                tz = pytz.timezone("America/Los_Angeles")
                start_aware = tz.localize(start_time) if start_time.tzinfo is None else start_time
                end_aware = tz.localize(end_time) if end_time.tzinfo is None else end_time
                start_rfc3339 = start_aware.isoformat()
                end_rfc3339 = end_aware.isoformat()
                
                # SECURITY: Only add Tyler if rep is on his direct team
                attendees = get_calendar_attendees(selected_rep) if DATA_ISOLATION_AVAILABLE else ["tyler.vansant@indoormedia.com"]
                attendee_str = ",".join(attendees) if attendees else ""
                
                cmd = [
                    "gog", "calendar", "create", rep_email,
                    f"--summary=📅 {business_name} (Booked by {selected_rep})",
                    f"--from={start_rfc3339}",
                    f"--to={end_rfc3339}",
                ]
                
                if attendee_str:
                    cmd.append(f"--attendees={attendee_str}")
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                tyler_note = ""
                if DATA_ISOLATION_AVAILABLE:
                    tyler_note = f"\n_Tyler auto-invited_" if should_invite_tyler_to_calendar(selected_rep) else f"\n_(Tyler not invited - outside direct team)_"
                else:
                    tyler_note = f"\n_Tyler auto-invited_"
                
                if result.returncode == 0:
                    await query.edit_message_text(
                        f"✅ *Appointment Booked!*\n\n"
                        f"Rep: {selected_rep}\n"
                        f"Business: {business_name}\n"
                        f"📅 {date_str} at {time_str}\n\n"
                        f"_Event created on {selected_rep}'s calendar_"
                        f"{tyler_note}",
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("✅ Done", callback_data=f"expand_{prospect_id}")],
                            [InlineKeyboardButton("👥 Invite Another Rep", callback_data=f"invite_reps_{prospect_id}")],
                        ])
                    )
                else:
                    await query.edit_message_text(
                        f"❌ Failed to invite {selected_rep}\n\nPlease try again.",
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"expand_{prospect_id}")]])
                    )
            except Exception as e:
                logger.error(f"Rep invite error: {e}")
                await query.edit_message_text(
                    f"❌ Error: {str(e)[:80]}",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"expand_{prospect_id}")]])
                )
        elif data.startswith("collapse_"):
            try:
                prospect_id = data.replace("collapse_", "")
                prospect = context.user_data.get('prospects', {}).get(prospect_id, {})
                await query.answer()
                
                business_name = prospect.get('name', 'Unknown')
                
                # Show collapsed view
                text = f"📌 *{business_name}*"
                buttons = [[InlineKeyboardButton("▶️ Show Actions", callback_data=f"expand_{prospect_id}")]]
                
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
            except Exception as e:
                logger.error(f"Error in collapse handler: {e}")
                try:
                    await query.answer("Error collapsing prospect. Try again.", show_alert=True)
                except:
                    pass
        elif data.startswith("note_"):
            try:
                prospect_id = data.replace("note_", "")
                prospect = context.user_data.get('prospects', {}).get(prospect_id, {})
                await query.answer()
                context.user_data[AWAITING_PROSPECT_NOTE] = prospect_id
                await query.edit_message_text(
                    f"📝 *Add Notes for {prospect.get('name', 'Prospect')}*\n\n"
                    f"Send your notes (availability, decision timeline, contact person, etc.):\n\n"
                    f"_Example: \"Met with manager, very interested. Follow up next week.\"_",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"expand_{prospect_id}")]])
                )
            except Exception as e:
                logger.error(f"Error in note handler: {e}")
                try:
                    await query.answer("Error loading notes. Try again.", show_alert=True)
                except:
                    pass
        elif data.startswith("cal_"):
            try:
                prospect_id = data.replace("cal_", "")
                prospect = context.user_data.get('prospects', {}).get(prospect_id, {})
                await query.answer()
                
                # Store prospect info for calendar event
                context.user_data['pending_cal'] = {
                    'prospect_id': prospect_id,
                    'name': prospect.get('name', 'Prospect'),
                    'address': prospect.get('address', ''),
                    'phone': prospect.get('phone', ''),
                    'store': prospect.get('store', ''),
                }
                
                # Show date picker (today + next 14 days)
                buttons = []
                for i in range(0, 15):  # 0 = today, 1-14 = next 14 days
                    cal_date = datetime.now() + timedelta(days=i)
                    if i == 0:
                        date_str = f"Today {cal_date.strftime('%m/%d')}"
                    else:
                        date_str = cal_date.strftime("%a %m/%d")
                    buttons.append([InlineKeyboardButton(date_str, callback_data=f"caldate_{i}")])
                
                buttons.append([InlineKeyboardButton("⬅️ Back", callback_data=f"expand_{prospect_id}")])
                
                await query.edit_message_text(
                    f"📅 *Select Date for: {prospect.get('name', 'Prospect')}*\n\n_Pick a date within the next 2 weeks:_",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            except Exception as e:
                logger.error(f"Error in calendar handler: {e}")
                try:
                    await query.answer("Error loading calendar. Try again.", show_alert=True)
                except:
                    pass
        elif data.startswith("caldate_"):
            days_ahead = int(data.replace("caldate_", ""))
            await query.answer()
            
            # Store selected date
            context.user_data['pending_cal']['days_ahead'] = days_ahead
            
            # Show time picker with 15-minute intervals (6 AM to 8 PM)
            buttons = []
            for hour in range(6, 21):  # 6 AM to 8 PM (20:00)
                for minute in [0, 15, 30, 45]:
                    time_obj = datetime.now().replace(hour=hour, minute=minute)
                    time_str = time_obj.strftime("%I:%M %p")  # 12-hour format with AM/PM
                    # Create callback data: hour*4 + minute/15 (0-191 for 6am-8pm)
                    callback_id = hour * 4 + minute // 15
                    buttons.append([InlineKeyboardButton(time_str, callback_data=f"caltime_{callback_id}")])
            
            prospect_id = context.user_data['pending_cal']['prospect_id']
            buttons.append([InlineKeyboardButton("⬅️ Back to Date", callback_data=f"cal_{prospect_id}")])
            
            date_display = (datetime.now() + timedelta(days=days_ahead)).strftime("%A, %B %d")
            await query.edit_message_text(
                f"🕐 *Select Time for {date_display}*\n\n_Choose a time slot (15-minute intervals):_",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        elif data.startswith("caltime_"):
            callback_id = int(data.replace("caltime_", ""))
            await query.answer()
            
            # Decode callback_id back to hour and minute
            hour = callback_id // 4
            minute = (callback_id % 4) * 15
            
            pending = context.user_data.get('pending_cal', {})
            prospect_id = pending.get('prospect_id', '')
            business_name = pending.get('name', 'Prospect')
            address = pending.get('address', '')
            phone = pending.get('phone', '')
            store = pending.get('store', '')
            days_ahead = pending.get('days_ahead', 1)
            
            # Get notepad content
            notepad = context.user_data.get('notepad', '').strip()
            
            # Create Google Calendar event on rep's calendar with timezone
            cal_date = datetime.now() + timedelta(days=days_ahead)
            
            # Convert to RFC3339 format with timezone info (required by gog)
            tz = pytz.timezone("America/Los_Angeles")
            start_dt = cal_date.replace(hour=hour, minute=minute, second=0)
            start_aware = tz.localize(start_dt) if start_dt.tzinfo is None else start_dt
            start_time = start_aware.isoformat()
            
            # End time is 1 hour after start
            end_dt = start_dt + timedelta(hours=1)
            end_aware = tz.localize(end_dt) if end_dt.tzinfo is None else end_dt
            end_time = end_aware.isoformat()
            
            summary = f"👤 Call/Visit: {business_name}"
            description = f"Prospect: {business_name}\nAddress: {address}\nPhone: {phone}\nStore: {store}"
            
            # Add prospect-specific notes if they exist
            prospect_notes = context.user_data.get('prospect_notes', {}).get(prospect_id, {}).get('notes', '')
            if prospect_notes:
                description += f"\n\n📝 Prospect Notes:\n{prospect_notes}"
            
            # Add rep's notepad if it exists
            if notepad:
                description += f"\n\n📋 Rep Notepad:\n{notepad}"
            
            # Get rep's email
            rep_name = get_rep_name(update)
            rep_email = get_rep_email(update)  # Helper function to get rep email from ID
            
            # SECURITY: Only add Tyler if rep is on his direct team
            attendees = get_calendar_attendees(rep_name) if DATA_ISOLATION_AVAILABLE else ["tyler.vansant@indoormedia.com"]
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
            
            # Try to create the calendar event
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    date_str = cal_date.strftime("%a %m/%d")
                    time_str = f"{hour % 12 or 12}:{minute:02d} {'AM' if hour < 12 else 'PM'}"
                    
                    # Store the event info for potential rep invitations
                    context.user_data['created_event'] = {
                        'prospect_id': prospect_id,
                        'business_name': business_name,
                        'date_str': date_str,
                        'time_str': time_str,
                        'cal_date': cal_date,
                        'hour': hour,
                        'minute': minute,
                    }
                    
                    # Show confirmation with option to invite reps
                    buttons = [
                        [InlineKeyboardButton("✅ Done", callback_data=f"expand_{prospect_id}")],
                        [InlineKeyboardButton("👥 Invite Reps", callback_data=f"invite_reps_{prospect_id}")],
                    ]
                    
                    await query.edit_message_text(
                        f"✅ *Event Created!*\n\n"
                        f"Business: {business_name}\n"
                        f"📅 {date_str} at {time_str}\n\n"
                        f"_Would you like to invite reps to this appointment?_",
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup(buttons)
                    )
                else:
                    await query.edit_message_text(
                        f"❌ Failed to create calendar event.\n\nError: {result.stderr[:100]}\n\nPlease try again.",
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"expand_{prospect_id}")]])
                    )
            except Exception as e:
                logger.error(f"Calendar creation error: {e}")
                await query.edit_message_text(
                    f"❌ Calendar error: {str(e)[:100]}",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"expand_{prospect_id}")]])
                )
            
            # Clear pending calendar
            context.user_data['pending_cal'] = {}
            return
        if data.startswith("save_"):
            try:
                prospect_id = data.replace("save_", "")
                prospect = context.user_data.get('prospects', {}).get(prospect_id, {})
                await query.answer()
                
                rep_id = get_rep_id(update)
                rep_data = load_rep_data(rep_id)
                
                # Show status options
                buttons = [
                    [InlineKeyboardButton("⭐ Interested", callback_data=f"savestatus_{prospect_id}_interested")],
                    [InlineKeyboardButton("🔄 Needs Follow-up", callback_data=f"savestatus_{prospect_id}_follow-up")],
                    [InlineKeyboardButton("📋 Proposal Sent", callback_data=f"savestatus_{prospect_id}_proposal")],
                    [InlineKeyboardButton("✅ Closed", callback_data=f"savestatus_{prospect_id}_closed")],
                    [InlineKeyboardButton("⬅️ Back", callback_data=f"expand_{prospect_id}")],
                ]
                
                await query.edit_message_text(
                    f"💾 *Save Prospect: {prospect.get('name', 'Unknown')}*\n\n"
                    f"Select pipeline status:",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            except Exception as e:
                logger.error(f"Error in save handler: {e}")
                try:
                    await query.answer("Error saving prospect. Try again.", show_alert=True)
                except:
                    pass

        elif data.startswith("savestatus_"):
            parts = data.replace("savestatus_", "").rsplit("_", 1)
            prospect_id = parts[0]
            status = parts[1]
            await query.answer()
            
            prospect = context.user_data.get('prospects', {}).get(prospect_id, {})
            rep_id = get_rep_id(update)
            
            # Save prospect
            data_obj = load_prospect_data()
            
            prospect_data = {
                "name": prospect.get('name', ''),
                "address": prospect.get('address', ''),
                "phone": prospect.get('phone', ''),
                "email": prospect.get('email', ''),
                "contact_name": prospect.get('contact_name', ''),
                "score": prospect.get('likelihood_score', 0),
                "status": status,
                "saved_date": datetime.now().isoformat(),
                "last_contacted": None,
                "visit_count": 0,
                "notes": [],
            }
            
            # SECURITY: Use isolation function to save only to this rep's data
            if DATA_ISOLATION_AVAILABLE:
                save_prospect(rep_id, prospect_id, prospect_data, data_obj)
            else:
                if rep_id not in data_obj["reps"]:
                    data_obj["reps"][rep_id] = {"name": "", "saved_prospects": {}, "search_history": [], "contact_history": {}}
                data_obj["reps"][rep_id]["saved_prospects"][prospect_id] = prospect_data
            
            save_prospect_data(data_obj)
            
            status_emoji = {"interested": "⭐", "follow-up": "🔄", "proposal": "📋", "closed": "✅"}
            status_text = status.replace("-", " ").title()
            
            # Collapse the card after saving
            collapsed_text = f"✅ {prospect.get('name', 'Unknown')} · {status_emoji.get(status, '●')} {status_text}"
            buttons = [[InlineKeyboardButton("▶️ Show Actions", callback_data=f"expand_{prospect_id}")]]
            
            await query.edit_message_text(
                collapsed_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        elif data.startswith("testimonials_"):
            try:
                prospect_id = data.replace("testimonials_", "")
                prospect = context.user_data.get('prospects', {}).get(prospect_id, {})
                await query.answer()
                
                # Get relevant testimonials for this prospect
                testimonials = get_testimonials_for_prospect(prospect)
                
                business_name = prospect.get('name', 'Prospect')
                
                if testimonials:
                    text = f"📋 *Written Testimonials - {business_name}*\n\n"
                    
                    for i, t in enumerate(testimonials, 1):
                        bus = t.get('business', 'Unknown')
                        comment = t.get('comment', '')
                        url = t.get('url', '')
                        full = t.get('full', {})
                        city = full.get('city', '')
                        state = full.get('state', '')
                        category = full.get('category', '')
                        
                        text += f"*{i}. {bus}*\n"
                        
                        # Show location + category
                        location_info = []
                        if city and state:
                            location_info.append(f"{city}, {state}")
                        if category:
                            location_info.append(category)
                        
                        if location_info:
                            text += f"📍 {' • '.join(location_info)}\n"
                        
                        if comment:
                            # Truncate long comments
                            display_comment = comment[:200] + "..." if len(comment) > 200 else comment
                            text += f"_{display_comment}_\n"
                        
                        if url:
                            text += f"[Read full testimonial]({url})\n"
                        text += "\n"
                    
                    buttons = [[InlineKeyboardButton("⬅️ Back", callback_data=f"expand_{prospect_id}")]]
                    
                    await query.edit_message_text(
                        text,
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup(buttons)
                    )
                else:
                    await query.edit_message_text(
                        f"❌ No testimonials available for this prospect type in your region.",
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"expand_{prospect_id}")]])
                    )
            except Exception as e:
                logger.error(f"Error in testimonials handler: {e}")
                try:
                    await query.answer("Error loading testimonials. Try again.", show_alert=True)
                except:
                    pass
        elif data.startswith("video_"):
            try:
                prospect_id = data.replace("video_", "")
                prospect = context.user_data.get('prospects', {}).get(prospect_id, {})
                await query.answer()
                
                # Get relevant videos for this prospect
                videos = get_videos_for_prospect(prospect)
                
                if videos:
                    business_name = prospect.get('name', 'Prospect')
                    buttons = []
                    for video in videos[:3]:
                        title = video.get('title', 'Video')
                        url = video.get('url', '')
                        if url:
                            buttons.append([InlineKeyboardButton(f"▶️ {title[:40]}", url=url)])
                    
                    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data=f"expand_{prospect_id}")])
                    
                    await query.edit_message_text(
                        f"🎬 *Video Testimonials for {business_name}*",
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup(buttons)
                    )
                else:
                    await query.edit_message_text(
                        f"❌ No videos available for this prospect type.",
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"expand_{prospect_id}")]])
                    )
            except Exception as e:
                logger.error(f"Error in video handler: {e}")
                try:
                    await query.answer("Error loading videos. Try again.", show_alert=True)
                except:
                    pass
        elif data == "saved_prospects":
            await query.answer()
            
            rep_id = get_rep_id(update)
            data_obj = load_prospect_data()
            saved = get_saved_prospects(rep_id, data_obj) if DATA_ISOLATION_AVAILABLE else data_obj.get("reps", {}).get(rep_id, {}).get("saved_prospects", {})
            
            if not saved:
                await query.edit_message_text(
                    "💾 *Saved Prospects*\n\n_(none yet)_\n\nStart saving prospects to track them here!",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔍 Find Prospects", callback_data="new_search")],
                        [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]
                    ])
                )
                return
            
            # Show saved prospects with filter options
            buttons = [
                [InlineKeyboardButton("⭐ Interested", callback_data="filter_interested")],
                [InlineKeyboardButton("🔄 Follow-up", callback_data="filter_follow-up")],
                [InlineKeyboardButton("📋 Proposal", callback_data="filter_proposal")],
                [InlineKeyboardButton("✅ Closed", callback_data="filter_closed")],
                [InlineKeyboardButton("📊 All", callback_data="filter_all")],
                [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]
            ]
            
            text = f"💾 *Saved Prospects* ({len(saved)} total)\n\nFilter by status:"
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        elif data.startswith("filter_"):
            status_filter = data.replace("filter_", "")
            await query.answer()
            
            rep_id = get_rep_id(update)
            data_obj = load_prospect_data()
            saved = get_saved_prospects(rep_id, data_obj) if DATA_ISOLATION_AVAILABLE else data_obj.get("reps", {}).get(rep_id, {}).get("saved_prospects", {})
            
            # Filter by status
            if status_filter != "all":
                filtered = {k: v for k, v in saved.items() if v.get("status") == status_filter}
            else:
                filtered = saved
            
            if not filtered:
                await query.edit_message_text(
                    f"📌 *No prospects with status: {status_filter.title()}*",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Saved", callback_data="saved_prospects")]])
                )
                return
            
            text = f"📌 *Saved Prospects - {status_filter.title()}*\n\n"
            buttons = []
            
            for prospect_id, prospect in list(filtered.items())[:10]:
                name = prospect.get('name', 'Unknown')
                score = prospect.get('score', 0)
                status = prospect.get('status', 'unknown')
                text += f"• {name} ({score}/100)\n"
                # Use callback to show options for this prospect
                buttons.append([InlineKeyboardButton(f"ℹ️ {name[:25]} - {status}", callback_data=f"prospect_detail_{prospect_id}")])
            
            buttons.append([InlineKeyboardButton("⬅️ Back to Saved", callback_data="saved_prospects")])
            
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        elif data == "my_sales_view":
            await query.answer()
            
            # Load contracts
            contracts_file = WORKSPACE / "data" / "contracts.json"
            tyler_sales = []
            error_msg = None
            try:
                if contracts_file.exists():
                    with open(contracts_file) as f:
                        contracts_data = json.load(f)
                    contracts_list = contracts_data.get("contracts", []) if isinstance(contracts_data, dict) else []
                    tyler_sales = [c for c in contracts_list if c and isinstance(c, dict) and "Tyler" in c.get("sales_rep", "")]
                else:
                    error_msg = "No contracts file found"
            except Exception as e:
                error_msg = f"Error loading contracts: {str(e)}"
                logger.error(f"Error in my_sales_view: {e}")
            
            if error_msg:
                await query.edit_message_text(
                    f"❌ *Error*\n\n{error_msg}",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
                )
                return
            
            if not tyler_sales:
                await query.edit_message_text(
                    "💳 *My Sales*\n\n_(No sales found)_\n\nSales data syncs from Gmail contracts nightly at 8 PM.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
                )
                return
            
            # Calculate metrics (handle None amounts)
            total_revenue = sum((c.get("total_amount") or 0) for c in tyler_sales)
            deal_count = len(tyler_sales)
            avg_deal = total_revenue / deal_count if deal_count > 0 else 0
            
            text = f"💳 *My Sales*\n\n"
            text += f"📊 *Metrics:*\n"
            text += f"💰 Total Revenue: ${total_revenue:,.2f}\n"
            text += f"📈 Closed Deals: {deal_count}\n"
            text += f"📊 Avg Deal Size: ${avg_deal:,.2f}\n\n"
            text += f"*Recent Deals:*\n"
            
            for c in sorted(tyler_sales, key=lambda x: x.get("date", ""), reverse=True)[:5]:
                date = c.get("date", "N/A")
                business = c.get("business_name", "Unknown")
                amount = c.get("total_amount") or 0
                text += f"• {date} - {business} (${amount:,.2f})\n"
            
            buttons = [
                [InlineKeyboardButton("📋 All Deals", callback_data="my_sales_all")],
                [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")],
            ]
            
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        elif data == "my_sales_all":
            await query.answer()
            
            contracts_file = WORKSPACE / "data" / "contracts.json"
            tyler_sales = []
            try:
                if contracts_file.exists():
                    with open(contracts_file) as f:
                        contracts_data = json.load(f)
                    contracts_list = contracts_data.get("contracts", []) if isinstance(contracts_data, dict) else []
                    tyler_sales = [c for c in contracts_list if c and isinstance(c, dict) and "Tyler" in c.get("sales_rep", "")]
            except:
                pass
            tyler_sales = sorted(tyler_sales, key=lambda x: x.get("date", ""), reverse=True)
            
            text = f"💳 *My Sales - All Deals ({len(tyler_sales)} total)*\n\n"
            
            for c in tyler_sales:
                date = c.get("date", "N/A")
                business = c.get("business_name", "Unknown")
                amount = c.get("total_amount") or 0
                contact = c.get("contact_name", "")
                text += f"*{date}* - {business}\n"
                if contact:
                    text += f"  Contact: {contact}\n"
                text += f"  Amount: ${amount:,.2f}\n\n"
            
            buttons = [[InlineKeyboardButton("⬅️ Back", callback_data="my_sales_view")]]
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        elif data == "team_sales_view":
            await query.answer()
            
            contracts_file = WORKSPACE / "data" / "contracts.json"
            all_contracts = []
            error_msg = None
            try:
                if contracts_file.exists():
                    with open(contracts_file) as f:
                        contracts_data = json.load(f)
                    all_contracts = contracts_data.get("contracts", []) if isinstance(contracts_data, dict) else []
                    all_contracts = [c for c in all_contracts if c and isinstance(c, dict)]
                else:
                    error_msg = "No contracts file found"
            except Exception as e:
                error_msg = f"Error loading contracts: {str(e)}"
                logger.error(f"Error in team_sales_view: {e}")
            
            if error_msg:
                await query.edit_message_text(
                    f"❌ *Error*\n\n{error_msg}",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
                )
                return
            
            if not all_contracts:
                await query.edit_message_text(
                    "👥 *Team Sales*\n\n_(No sales found)_\n\nSales data syncs from Gmail contracts nightly at 8 PM.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
                )
                return
            
            # Group by rep
            by_rep = {}
            for c in all_contracts:
                rep = c.get("sales_rep", "Unknown")
                if rep not in by_rep:
                    by_rep[rep] = {"count": 0, "total": 0}
                by_rep[rep]["count"] += 1
                by_rep[rep]["total"] += (c.get("total_amount") or 0)
            
            # Sort by total revenue
            sorted_reps = sorted(by_rep.items(), key=lambda x: x[1]["total"], reverse=True)
            
            total_team_revenue = sum((c.get("total_amount") or 0) for c in all_contracts)
            
            text = f"👥 *Team Sales*\n\n"
            text += f"💰 Total Team Revenue: ${total_team_revenue:,.2f}\n"
            text += f"📊 Total Deals: {len(all_contracts)}\n\n"
            text += f"*Leaderboard (by $):*\n"
            
            for i, (rep, stats) in enumerate(sorted_reps, 1):
                amount = stats.get('total') or 0
                count = stats.get('count') or 0
                text += f"{i}. {rep}\n"
                text += f"   💰 ${amount:,.2f} ({count} deals)\n"
            
            buttons = [
                [InlineKeyboardButton("📋 All Deals", callback_data="team_sales_all")],
                [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")],
            ]
            
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        elif data == "team_sales_all":
            await query.answer()
            
            contracts_file = WORKSPACE / "data" / "contracts.json"
            all_contracts = []
            try:
                if contracts_file.exists():
                    with open(contracts_file) as f:
                        contracts_data = json.load(f)
                    contracts_list = contracts_data.get("contracts", []) if isinstance(contracts_data, dict) else []
                    all_contracts = sorted([c for c in contracts_list if c and isinstance(c, dict)], key=lambda x: x.get("date", ""), reverse=True)
            except:
                pass
            
            text = f"👥 *Team Sales - All Deals ({len(all_contracts)} total)*\n\n"
            
            for c in all_contracts:
                date = c.get("date", "N/A")
                rep = c.get("sales_rep", "Unknown")
                business = c.get("business_name", "Unknown")
                amount = c.get("total_amount") or 0
                text += f"*{date}* - {rep}\n"
                text += f"  {business}: ${amount:,.2f}\n"
            
            buttons = [[InlineKeyboardButton("⬅️ Back", callback_data="team_sales_view")]]
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        elif data == "monthly_leaderboard":
            await query.answer()
            
            contracts_file = WORKSPACE / "data" / "contracts.json"
            all_contracts = []
            try:
                if contracts_file.exists():
                    with open(contracts_file) as f:
                        contracts_data = json.load(f)
                    all_contracts = contracts_data.get("contracts", []) if isinstance(contracts_data, dict) else []
                    all_contracts = [c for c in all_contracts if c and isinstance(c, dict)]
                    logger.info(f"📊 Monthly leaderboard: Loaded {len(all_contracts)} contracts from disk (fresh data)")
            except Exception as e:
                logger.error(f"Error loading contracts for monthly view: {e}")
            
            if not all_contracts:
                await query.edit_message_text(
                    "📅 *Monthly Leaderboard*\n\n_(No sales data yet)_\n\nSales data syncs from Gmail contracts nightly at 8 PM.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
                )
                return
            
            # Get current month and year
            today = datetime.now()
            current_month = today.month
            current_year = today.year
            
            # Group contracts by month and rep
            monthly_data = {}
            for c in all_contracts:
                try:
                    date_str = c.get("date", "")
                    if date_str:
                        # Parse date - handle both formats:
                        # Format 1: "2026-03-06 10:13" (YYYY-MM-DD)
                        # Format 2: "3/13/2026" (M/D/YYYY)
                        try:
                            contract_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
                        except ValueError:
                            # Try alternative format
                            contract_date = datetime.strptime(date_str.split()[0], "%m/%d/%Y")
                        month_key = contract_date.strftime("%B %Y")  # "March 2026"
                    else:
                        month_key = "Unknown"
                    
                    if month_key not in monthly_data:
                        monthly_data[month_key] = {}
                    
                    rep = c.get("sales_rep", "Unknown")
                    if rep not in monthly_data[month_key]:
                        monthly_data[month_key][rep] = {"count": 0, "total": 0}
                    
                    monthly_data[month_key][rep]["count"] += 1
                    monthly_data[month_key][rep]["total"] += (c.get("total_amount") or 0)
                except:
                    pass
            
            # Store monthly_data in context for detail view
            context.user_data["monthly_data"] = monthly_data
            
            # Build message showing current month prominently
            current_month_key = today.strftime("%B %Y")
            text = f"📅 *Monthly Leaderboard* (Jan 2026 - Present)\n\n"
            
            if current_month_key in monthly_data:
                text += f"*{current_month_key}* (Current)\n"
                text += "=" * 30 + "\n"
                
                # Sort by revenue
                sorted_reps = sorted(
                    monthly_data[current_month_key].items(),
                    key=lambda x: x[1]["total"],
                    reverse=True
                )
                
                total_revenue = sum(r["total"] for r in monthly_data[current_month_key].values())
                
                for i, (rep, stats) in enumerate(sorted_reps, 1):
                    amount = stats.get("total", 0)
                    count = stats.get("count", 0)
                    avg_deal = amount / count if count > 0 else 0
                    text += f"{i}. {rep}\n"
                    text += f"   💰 ${amount:,.2f} ({count} deal{'s' if count != 1 else ''})\n"
                    text += f"   📊 Avg: ${avg_deal:,.2f}\n"
                
                text += f"\n💼 *Month Total:* ${total_revenue:,.2f}\n"
            
            # Show ALL months (from Jan 2026 onwards) with clickable buttons
            all_months = sorted([k for k in monthly_data.keys()], reverse=True)
            other_months = [m for m in all_months if m != current_month_key]
            
            if other_months:
                text += f"\n*All Months (Jan 2026 - Present):*"
            
            buttons = []
            for month_key in other_months:  # Show ALL months, not just 6
                month_total = sum(r["total"] for r in monthly_data[month_key].values())
                deal_count = sum(r["count"] for r in monthly_data[month_key].values())
                # Encode month in callback (replace spaces/special chars)
                safe_month = month_key.replace(" ", "_")
                buttons.append([InlineKeyboardButton(f"📊 {month_key} (${month_total:,.0f})", callback_data=f"monthly_detail_{safe_month}")])
            
            buttons.append([InlineKeyboardButton("📈 All Time", callback_data="team_sales_view")])
            buttons.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")])
            
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        elif data.startswith("monthly_detail_"):
            await query.answer()
            
            # Extract month from callback
            safe_month = data.replace("monthly_detail_", "")
            month_key = safe_month.replace("_", " ")
            
            monthly_data = context.user_data.get("monthly_data", {})
            if month_key not in monthly_data:
                await query.answer("Month data not found", show_alert=True)
                return
            
            # Build full leaderboard for this month
            text = f"📊 *{month_key} - Full Leaderboard*\n\n"
            
            # Sort by revenue
            sorted_reps = sorted(
                monthly_data[month_key].items(),
                key=lambda x: x[1]["total"],
                reverse=True
            )
            
            total_revenue = sum(r["total"] for r in monthly_data[month_key].values())
            total_deals = sum(r["count"] for r in monthly_data[month_key].values())
            
            for i, (rep, stats) in enumerate(sorted_reps, 1):
                amount = stats.get("total", 0)
                count = stats.get("count", 0)
                avg_deal = amount / count if count > 0 else 0
                pct_revenue = (amount / total_revenue * 100) if total_revenue > 0 else 0
                text += f"{i}. {rep}\n"
                text += f"   💰 ${amount:,.2f} ({pct_revenue:.1f}%)\n"
                text += f"   📊 {count} deal{'s' if count != 1 else ''} | Avg: ${avg_deal:,.2f}\n\n"
            
            text += f"💼 *Month Total:* ${total_revenue:,.2f}\n"
            text += f"📈 *Total Deals:* {total_deals}\n"
            
            buttons = [[InlineKeyboardButton("⬅️ Back", callback_data="monthly_leaderboard")]]
            
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        elif data == "dashboard_view":
            await query.answer()
            
            try:
                rep_id = get_rep_id(update)
                rep_name = get_rep_name(update)
                rep_data = load_rep_data(rep_id)
                
                # Ensure rep has a name
                if not rep_data.get("name"):
                    rep_data["name"] = rep_name
                    save_prospect_data(load_prospect_data())
            except Exception as e:
                logger.error(f"Dashboard load error: {e}")
                await query.edit_message_text(
                    "❌ Error loading dashboard. Please try again.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
                )
                return
            all_data = load_prospect_data()
            
            try:
                # Personal metrics
                searches_today = rep_data.get("session_searches", 0)
                saved_count = len(rep_data.get("saved_prospects", {}))
                
                # Status breakdown
                statuses = {}
                for prospect in rep_data.get("saved_prospects", {}).values():
                    status = prospect.get("status", "unknown")
                    statuses[status] = statuses.get(status, 0) + 1
                
                # Team metrics
                total_team_searches = sum(r.get("session_searches", 0) for r in all_data["reps"].values())
                total_team_saved = sum(len(r.get("saved_prospects", {})) for r in all_data["reps"].values())
                
                team_statuses = {}
                for rep in all_data["reps"].values():
                    for prospect in rep.get("saved_prospects", {}).values():
                        status = prospect.get("status", "unknown")
                        team_statuses[status] = team_statuses.get(status, 0) + 1
                
                # Busiest reps (with safe access to name)
                rep_activity = []
                for rid, r in all_data["reps"].items():
                    rep_name_safe = r.get("name") or r.get("display_name") or f"Rep {rid[:8]}"
                    searches = r.get("session_searches", 0)
                    rep_activity.append((rep_name_safe, searches))
                
                text = f"📊 *Dashboard*\n\n"
                text += f"👤 *Your Metrics ({rep_name}):*\n"
                text += f"🔍 Searches: {searches_today}\n"
                text += f"💾 Saved: {saved_count}\n"
                
                if statuses:
                    text += f"  • ⭐ Interested: {statuses.get('interested', 0)}\n"
                    text += f"  • 🔄 Follow-up: {statuses.get('follow-up', 0)}\n"
                    text += f"  • 📋 Proposal: {statuses.get('proposal', 0)}\n"
                    text += f"  • ✅ Closed: {statuses.get('closed', 0)}\n"
                
                text += f"\n👥 *Team Metrics:*\n"
                text += f"🔍 Total Searches: {total_team_searches}\n"
                text += f"💾 Total Saved: {total_team_saved}\n"
                
                if team_statuses:
                    text += f"  • ⭐ Interested: {team_statuses.get('interested', 0)}\n"
                    text += f"  • 🔄 Follow-up: {team_statuses.get('follow-up', 0)}\n"
                    text += f"  • 📋 Proposal: {team_statuses.get('proposal', 0)}\n"
                    text += f"  • ✅ Closed: {team_statuses.get('closed', 0)}\n"
                
                if rep_activity:
                    text += f"\n🏆 *Top Reps (Searches):*\n"
                    for i, (name, count) in enumerate(rep_activity[:3], 1):
                        text += f"{i}. {name}: {count}\n"
                
                await query.edit_message_text(text, parse_mode="Markdown", 
                                             reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]]))
            except Exception as e:
                logger.error(f"Dashboard metric error: {e}", exc_info=True)
                await query.edit_message_text(
                    "❌ Error building dashboard metrics. Please try again.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
                )
        elif data == "find_stores_near_me":
            await query.answer()
            # Request location from user
            location_button = KeyboardButton("📍 Share My Location", request_location=True)
            keyboard = ReplyKeyboardMarkup([[location_button]], one_time_keyboard=True, resize_keyboard=True)
            await update.effective_chat.send_message(
                "📍 *Share Your Location*\n\nTap the button below to share your location, and I'll find the nearest stores.",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            context.user_data['waiting_for_location'] = True
        elif data.startswith("nearme_"):
            store_num = data.replace("nearme_", "")
            if store_num == "prospects":
                # Start prospecting flow from near me
                await query.answer()
                store_num = context.user_data.get('selected_store')
                if not store_num:
                    await query.edit_message_text("❌ Store not found. Go back and select a store.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]]))
                    return
                # Store the category for back button reference
                context.user_data['selected_category'] = None
                # Show category menu for prospecting with back to store button
                keyboard = build_category_keyboard(store_num=store_num)
                await query.edit_message_text("📂 *Select a category:*", parse_mode="Markdown", reply_markup=keyboard)
                return
            elif store_num == "rates":
                # Show rates for selected store
                await query.answer()
                store_num = context.user_data.get('selected_store')
                if not store_num or store_num not in STORES:
                    await query.edit_message_text("❌ Store not found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]]))
                    return
                # Show rates with edit_message for callback query
                await do_rates_lookup(update, store_num, ad_type="single", edit_message=query.message)
                return
            elif store_num == "audit":
                # Start audit flow for selected store
                await query.answer()
                selected = context.user_data.get('selected_store')
                if not selected or selected not in STORES:
                    await query.edit_message_text("❌ Store not found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]]))
                    return
                # Trigger audit flow
                store = STORES[selected]
                cycle = store.get('Cycle', '?')
                starting_cases = store.get('Case Count', 20)
                get_delivery_func = get_cycle_delivery_dates()
                delivery_date = get_delivery_func(cycle)
                context.user_data['audit_info'] = {
                    'store_num': selected,
                    'cycle': cycle,
                    'delivery_date': delivery_date,
                    'starting_cases': starting_cases,
                }
                # Show confirmation
                msg = f"🏪 *Audit: {selected}*\n\n"
                msg += f"{store.get('GroceryChain', '?')} - {store.get('City', '')}, {store.get('State', '')}\n\n"
                msg += f"📦 *Delivery Confirmation:*\n\n"
                msg += f"_{selected}_ was sent *{starting_cases} cases* on *{delivery_date.strftime('%B %d, %Y')}*\n\n"
                msg += f"Is this correct?"
                buttons = [
                    [InlineKeyboardButton("✅ Yes, Correct", callback_data="audit_confirm_yes")],
                    [InlineKeyboardButton("❌ No, Adjust", callback_data="audit_confirm_no")],
                    [InlineKeyboardButton("⬅️ Cancel", callback_data="main_menu")],
                ]
                await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
                return
            else:
                # Show store action menu
                await query.answer()
                store = STORES.get(store_num)
                if store:
                    context.user_data['selected_store'] = store_num
                    await show_store_action_menu(None, store_num, store, edit_message=query.message, context=context)
                else:
                    await query.edit_message_text("❌ Store not found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]]))
        elif data == "menu_locate_stores":
            await show_submenu_locate_stores(update, context)
        elif data == "locate_near_me":
            await query.answer()
            context.user_data['waiting_for_location'] = True
            location_button = KeyboardButton("📍 Share My Location", request_location=True)
            keyboard = ReplyKeyboardMarkup([[location_button]], one_time_keyboard=True, resize_keyboard=True)
            await update.effective_chat.send_message(
                "📍 *Find Stores Near You*\n\nTap the button below to share your location and see nearby stores.",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        elif data == "locate_search":
            await query.answer()
            context.user_data['find_stores_mode'] = True
            await update.effective_chat.send_message(
                "🔍 Enter a store number or city name:",
                reply_markup=ReplyKeyboardRemove()
            )
        elif data == "menu_prospects":
            await show_submenu_prospects(update, context)
        elif data == "menu_clients":
            await show_submenu_clients(update, context)
        elif data == "menu_stores":
            await show_submenu_stores(update, context)
        elif data == "menu_prospecting":
            await show_submenu_prospecting(update, context)
        elif data == "menu_sales":
            await show_submenu_sales(update, context)
        elif data == "menu_performance":
            await show_submenu_performance(update, context)
        elif data == "menu_tools":
            await show_submenu_tools(update, context)
        elif data == "menu_products":
            await show_submenu_products(update, context)
        elif data == "menu_register_tape":
            await show_submenu_register_tape(update, context)
        elif data == "menu_cartvertising":
            await show_submenu_cartvertising(update, context)
        elif data == "menu_digital":
            await show_submenu_digital(update, context)
        elif data == "product_child_seat":
            await show_product_child_seat(update, context)
        elif data.startswith("cs_pkg_"):
            pkg_index = int(data.replace("cs_pkg_", ""))
            await show_child_seat_package(update, context, pkg_index)
        elif data == "product_nose":
            await show_product_nose(update, context)
        elif data == "product_digitalboost":
            await show_product_digitalboost(update, context, pins=0)
        elif data.startswith("db_pins_"):
            pins = int(data.replace("db_pins_", ""))
            await show_product_digitalboost(update, context, pins=pins)
        elif data == "product_findlocal":
            await show_product_findlocal(update, context)
        elif data == "product_reviewboost":
            await show_product_reviewboost(update, context)
        elif data == "product_loyaltyboost":
            await show_product_loyaltyboost(update, context)
        elif data == "notepad_edit":
            await query.answer()
            current_notes = context.user_data.get('notepad', '')
            context.user_data[AWAITING_NOTEPAD_EDIT] = True
            
            if current_notes:
                display = f"📝 *Fillable Notepad*\n\n```\n{current_notes}\n```\n\n_Send new text to update your notes:_"
            else:
                display = "📝 *Fillable Notepad*\n\n_(empty)_\n\n_Send text to add your first note:_"
            
            buttons = [
                [InlineKeyboardButton("🗑️ Clear All", callback_data="notepad_clear")],
                [InlineKeyboardButton("⬅️ Cancel", callback_data="main_menu")]
            ]
            
            await query.edit_message_text(
                display,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        elif data == "notepad_clear":
            await query.answer()
            context.user_data['notepad'] = ''
            await query.edit_message_text(
                "🗑️ *Notepad Cleared*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
            )
        elif data.startswith("rep_login_"):
            await query.answer()
            login_value = data.replace("rep_login_", "")
            user_id = str(update.effective_user.id)
            
            if login_value == "new":
                # New rep — ask for name
                context.user_data['awaiting_rep_name'] = True
                await query.edit_message_text(
                    "🆕 *New Rep Registration*\n\n"
                    "Type your full name as it appears on contracts:\n\n"
                    "_Example: Amy Dixon_",
                    parse_mode="Markdown"
                )
            else:
                # Known rep selected
                registry = load_rep_registry()
                registry[user_id] = {
                    "contract_name": login_value,
                    "display_name": login_value,
                    "role": "manager" if "Tyler" in login_value else "rep",
                    "registered_at": datetime.now().strftime("%Y-%m-%d"),
                }
                save_rep_registry(registry)
                logger.info(f"✅ Rep logged in: {login_value} (ID: {user_id})")
                
                await query.edit_message_text(
                    f"✅ *Welcome, {login_value}!*\n\nYou're all set. Loading your dashboard...",
                    parse_mode="Markdown"
                )
                await asyncio.sleep(1)
                await show_main_menu(update, context)
        
        elif data.startswith("customer_detail_"):
            await query.answer()
            idx = int(data.replace("customer_detail_", ""))
            customers = context.user_data.get('customer_list', [])
            if idx >= len(customers):
                await query.edit_message_text("❌ Customer not found.")
                return
            
            c = customers[idx]
            business = c.get('business', '?')
            owner = c.get('owner', '')
            phone = c.get('phone', '')
            email = c.get('email', '')
            address = c.get('address', '')
            amount = c.get('amount', 0)
            store = c.get('store', '')
            store_number = c.get('store_number', '')
            rep = c.get('rep', '')
            date = c.get('date', '')
            
            # Build detail card
            msg = f"🏢 *{business}*\n\n"
            if owner:
                msg += f"👤 *Contact:* {owner}\n"
            if phone:
                msg += f"📞 *Phone:* {phone}\n"
            if email:
                msg += f"📧 *Email:* {email}\n"
            if address:
                clean_addr = address.replace('\n', ', ').strip(', ')
                msg += f"📍 *Address:* {clean_addr}\n"
            msg += f"\n💰 *Deal:* ${amount:,.2f}\n"
            if date:
                msg += f"📅 *Signed:* {date}\n"
            if store:
                msg += f"🏪 *Store:* {store}"
                if store_number:
                    msg += f" ({store_number})"
                msg += "\n"
            if rep:
                msg += f"👤 *Rep:* {rep}\n"
            
            # Calendar event preview
            if 'next_event' in c:
                event = c['next_event']
                event_date = event.get('date', '').split('T')[0] if 'T' in event.get('date', '') else event.get('date', '')
                msg += f"\n📅 *Next:* {event['title']} ({event_date})\n"
            
            # Buttons
            buttons = []
            buttons.append([InlineKeyboardButton("📅 Calendar Events", callback_data=f"customer_events_{idx}")])
            buttons.append([InlineKeyboardButton("✉️ Draft Email", callback_data=f"customer_email_{idx}")])
            
            # Expansion suggestions button (nearby stores + upsell)
            buttons.append([InlineKeyboardButton("🚀 Expansion Opportunities", callback_data=f"customer_expand_{idx}")])
            
            buttons.append([InlineKeyboardButton("⬅️ Back to Customers", callback_data="client_list")])
            
            # Store customer data in context for sub-actions
            context.user_data['current_customer'] = c
            context.user_data['current_customer_idx'] = idx
            
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        
        elif data.startswith("customer_events_"):
            await query.answer("Loading calendar events...")
            idx = int(data.replace("customer_events_", ""))
            c = context.user_data.get('customer_list', [{}])[idx] if idx < len(context.user_data.get('customer_list', [])) else {}
            business = c.get('business', '?')
            owner = c.get('owner', '')
            store_number = c.get('store_number', '')
            contract_num = c.get('contract_number', '')
            
            # IndoorMedia event prefixes — ONLY show these
            im_prefixes = ['📦 Install', '🔍 Audit', '🔄 Check-in', '🔁 Renewal']
            
            # Load notes
            notes_file = WORKSPACE / "data" / "event_notes.json"
            event_notes = {}
            try:
                if notes_file.exists():
                    with open(notes_file) as f:
                        event_notes = json.load(f)
            except:
                pass
            
            # Fetch calendar events matching this customer
            events_found = []
            try:
                cmd = ["/opt/homebrew/bin/gog", "calendar", "list", "--json", "--max", "500",
                       "--from", datetime.now().strftime("%Y-%m-%d"),
                       "--to", (datetime.now() + timedelta(days=400)).strftime("%Y-%m-%d")]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    events = json.loads(result.stdout)
                    if isinstance(events, dict):
                        events = events.get("events", [])
                    for event in events:
                        if isinstance(event, dict):
                            title = event.get("summary", "")
                            is_im_event = any(title.startswith(p) for p in im_prefixes)
                            if not is_im_event:
                                continue
                            title_lower = title.lower()
                            match = False
                            if business and business.lower() in title_lower:
                                match = True
                            elif owner and owner.lower() in title_lower:
                                match = True
                            elif store_number and store_number in title:
                                match = True
                            if match:
                                start = event.get("start", {})
                                start_date = start.get("dateTime", start.get("date", ""))
                                event_id = event.get("id", "")
                                events_found.append({
                                    "title": title,
                                    "date": start_date,
                                    "event_id": event_id,
                                })
            except Exception as e:
                logger.warning(f"Calendar fetch error: {e}")
            
            # Store events in context for note-taking
            sorted_events = sorted(events_found, key=lambda x: x['date'])
            context.user_data['customer_events'] = sorted_events
            
            if sorted_events:
                msg = f"📅 *Events — {business}*\n\n"
                msg += "_Tap an event to view details or add notes:_\n"
                
                buttons = []
                for i, ev in enumerate(sorted_events[:20]):
                    date_str = ev['date'].split('T')[0] if 'T' in ev['date'] else ev['date']
                    title = ev['title']
                    # Shorten for button label
                    if '📦' in title:
                        label = f"📦 Install — {date_str}"
                    elif '🔍' in title:
                        label = f"🔍 Audit — {date_str}"
                    elif '🔄' in title:
                        # Extract check-in number
                        cnum = re.search(r'#(\d+)', title)
                        label = f"🔄 Check-in #{cnum.group(1) if cnum else '?'} — {date_str}"
                    elif '🔁' in title:
                        label = f"🔁 Renewal — {date_str}"
                    else:
                        label = f"{title[:25]} — {date_str}"
                    
                    # Show note indicator
                    eid = ev.get('event_id', '')
                    if eid and event_notes.get(eid):
                        label = f"📝 {label}"
                    
                    buttons.append([InlineKeyboardButton(label, callback_data=f"event_detail_{idx}_{i}")])
            else:
                msg = f"📅 *Events — {business}*\n\n_No IndoorMedia events found._"
                buttons = []
            
            buttons.append([InlineKeyboardButton("⬅️ Back", callback_data=f"customer_detail_{idx}")])
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        
        elif data.startswith("event_detail_"):
            await query.answer()
            parts = data.replace("event_detail_", "").split("_")
            cust_idx = int(parts[0])
            event_idx = int(parts[1])
            
            events_list = context.user_data.get('customer_events', [])
            if event_idx >= len(events_list):
                await query.edit_message_text("❌ Event not found.")
                return
            
            ev = events_list[event_idx]
            title = ev.get('title', '?')
            date_str = ev['date'].split('T')[0] if 'T' in ev.get('date', '') else ev.get('date', '')
            event_id = ev.get('event_id', '')
            
            # Load notes for this event
            notes_file = WORKSPACE / "data" / "event_notes.json"
            event_notes = {}
            try:
                if notes_file.exists():
                    with open(notes_file) as f:
                        event_notes = json.load(f)
            except:
                pass
            
            note = event_notes.get(event_id, '')
            
            msg = f"📅 *{title}*\n\n"
            msg += f"📆 *Date:* {date_str}\n"
            
            if note:
                msg += f"\n📝 *Notes:*\n{note}\n"
            else:
                msg += f"\n📝 _No notes yet_\n"
            
            buttons = [
                [InlineKeyboardButton("📝 Add/Edit Note", callback_data=f"event_note_{cust_idx}_{event_idx}")],
                [InlineKeyboardButton("⬅️ Back to Events", callback_data=f"customer_events_{cust_idx}")],
            ]
            
            context.user_data['current_event_id'] = event_id
            context.user_data['current_event_cust_idx'] = cust_idx
            context.user_data['current_event_idx'] = event_idx
            
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        
        elif data.startswith("event_note_"):
            await query.answer()
            parts = data.replace("event_note_", "").split("_")
            cust_idx = int(parts[0])
            event_idx = int(parts[1])
            
            events_list = context.user_data.get('customer_events', [])
            ev = events_list[event_idx] if event_idx < len(events_list) else {}
            title = ev.get('title', 'this event')
            
            context.user_data['awaiting_event_note'] = True
            context.user_data['current_event_id'] = ev.get('event_id', '')
            context.user_data['current_event_cust_idx'] = cust_idx
            context.user_data['current_event_idx'] = event_idx
            
            await query.edit_message_text(
                f"📝 *Add Note*\n\n"
                f"Event: {title}\n\n"
                f"Type your note below:",
                parse_mode="Markdown"
            )
        
        elif data.startswith("customer_email_"):
            await query.answer()
            idx = int(data.replace("customer_email_", ""))
            
            # Store customer index for template selection
            context.user_data['pending_email_customer_idx'] = idx
            
            # Show email template menu
            msg = "📧 *Select Email Template*\n\n_Choose which email to send:_"
            buttons = [
                [InlineKeyboardButton("🚀 Kickoff/What's Next", callback_data=f"email_template_kickoff_{idx}")],
                [InlineKeyboardButton("✅ Check-in/Audit", callback_data=f"email_template_checkin_{idx}")],
                [InlineKeyboardButton("⬆️ Upsell/Expansion", callback_data=f"email_template_upsell_{idx}")],
                [InlineKeyboardButton("🔄 Renewal", callback_data=f"email_template_renewal_{idx}")],
                [InlineKeyboardButton("⬅️ Back", callback_data=f"customer_detail_{idx}")],
            ]
            
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        
        elif data.startswith("email_template_"):
            await query.answer()
            parts = data.split("_")
            template_type = parts[2]  # kickoff, checkin, upsell, renewal
            idx = int(parts[3])
            
            c = context.user_data.get('customer_list', [{}])[idx] if idx < len(context.user_data.get('customer_list', [])) else {}
            business = c.get('business', '?')
            owner = c.get('owner', '')
            email = c.get('email', '')
            store = c.get('store', '')
            rep_name = get_rep_name(update)
            
            # Select template based on type
            if template_type == "kickoff":
                subject = f"What's Next — {business} & IndoorMedia"
                body = draft_kickoff_email(business, owner, rep_name, store)
            elif template_type == "checkin":
                subject = f"Checking in — {business} & IndoorMedia"
                body = draft_checkin_email(business, owner, rep_name, store)
            elif template_type == "upsell":
                subject = f"Expansion Opportunity — {business}"
                # Use smart upsell system if available and contract number exists
                contract_number = c.get('contract_number', '')
                if UPSELL_EMAIL_SYSTEM_AVAILABLE and contract_number:
                    try:
                        upsell_params = get_upsell_email_params_from_contract(contract_number)
                        if upsell_params:
                            body = draft_smart_upsell_email(
                                business_name=business,
                                owner_name=owner,
                                rep_name=rep_name,
                                store_ref=store,
                                contract_number=contract_number,
                                address=upsell_params.get('address', ''),
                                current_chain=upsell_params.get('store_name', '')
                            )
                        else:
                            body = draft_upsell_email(business, owner, rep_name, store)
                    except Exception as e:
                        logger.error(f"Error generating smart upsell email: {e}")
                        body = draft_upsell_email(business, owner, rep_name, store)
                else:
                    body = draft_upsell_email(business, owner, rep_name, store)
            elif template_type == "renewal":
                subject = f"Time to Renew — {business} & IndoorMedia"
                body = draft_renewal_email(business, owner, rep_name, store)
            else:
                subject = f"Message from IndoorMedia"
                body = "Hi,\n\nLet me know how I can help.\n\nBest,\n" + rep_name
            
            msg = f"✉️ *Draft Email — {business}*\n\n"
            if email:
                msg += f"*To:* {email}\n"
            msg += f"*Subject:* {subject}\n\n"
            msg += f"```\n{body}\n```\n\n"
            msg += "_Copy the email above and send from your email client._"
            
            buttons = [
                [InlineKeyboardButton("⬅️ Back to Templates", callback_data=f"customer_email_{idx}")],
                [InlineKeyboardButton("⬅️ Back to Customer", callback_data=f"customer_detail_{idx}")],
            ]
            
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        
        elif data.startswith("customer_expand_"):
            await query.answer("Finding expansion opportunities...")
            idx = int(data.replace("customer_expand_", ""))
            c = context.user_data.get('customer_list', [{}])[idx] if idx < len(context.user_data.get('customer_list', [])) else {}
            business = c.get('business', '?')
            store_number = c.get('store_number', '')
            
            msg = f"🚀 *Expansion — {business}*\n\n"
            
            # Find the store they're in to get nearby stores
            full_store_num = None
            for sn in STORES:
                if store_number and store_number in sn:
                    full_store_num = sn
                    break
            
            buttons = []
            
            if full_store_num and full_store_num in STORES:
                store_data = STORES[full_store_num]
                city = store_data.get('City', '')
                state = store_data.get('State', '')
                chain = store_data.get('GroceryChain', '')
                
                msg += f"📍 *Current:* {chain} — {city}, {state} ({full_store_num})\n\n"
                
                # Find nearby stores in same city or neighboring cities
                nearby_stores = []
                for sn, sd in STORES.items():
                    if sn == full_store_num:
                        continue
                    if sd.get('City', '') == city and sd.get('State', '') == state:
                        nearby_stores.append(sn)
                
                if nearby_stores:
                    msg += f"🏪 *Nearby Stores in {city}* ({len(nearby_stores)}):\n"
                    for ns in nearby_stores[:8]:
                        ns_data = STORES[ns]
                        ns_chain = ns_data.get('GroceryChain', '')
                        msg += f"• {ns} — {ns_chain}\n"
                        buttons.append([InlineKeyboardButton(f"💰 {ns} Rates", callback_data=f"action_rates_{ns}")])
                    if len(nearby_stores) > 8:
                        msg += f"  _...and {len(nearby_stores) - 8} more_\n"
                else:
                    msg += f"_No other stores found in {city}_\n"
                
                msg += "\n"
            
            # Upsell products they might not have
            msg += "📦 *Product Upsell Opportunities:*\n"
            msg += "• 🚀 DigitalBoost — Geofence ads near the store\n"
            msg += "• 📍 FindLocal — SEO/listings management\n"
            msg += "• ⭐ ReviewBoost — Automated review campaigns\n"
            msg += "• 💎 LoyaltyBoost — Customer loyalty program\n"
            msg += "• 🛒 Cartvertising — Cart ads (Child Seat/Nose)\n"
            
            buttons.append([InlineKeyboardButton("📱 Digital Products", callback_data="menu_digital")])
            buttons.append([InlineKeyboardButton("🛒 Cartvertising", callback_data="menu_cartvertising")])
            buttons.append([InlineKeyboardButton("⬅️ Back", callback_data=f"customer_detail_{idx}")])
            
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        
        elif data == "begin_main_menu":
            await query.answer()
            await show_main_menu(update, context)
        elif data == "main_menu" or data == "back_menu":
            await query.answer()
            await show_main_menu(update, context)
        elif data == "help_menu":
            await query.answer()
            help_text = """📖 *How to Use the Bot*

*3 Simple Steps:*

1️⃣ *Enter location*
   Send a store number: `FME07Z-0236`
   Or a city: `Portland`

2️⃣ *Pick a category*
   Restaurants → Mexican
   Retail → Clothing
   Services → Salons

3️⃣ *Get prospects*
   Get ranked by likelihood
   Click [📍 Maps] to view & call
   Click [📞 Call] to dial directly

*Button Actions:*
🔍 New Search — Start over
📍 Maps — View on Google Maps
📞 Call — Dial number directly
✅ Booked — Mark as closed
"""
            buttons = [[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]]
            await query.edit_message_text(help_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        elif data == "examples_menu":
            await query.answer()
            examples_text = """📚 *Example Store Numbers:*

🏪 *Fred Meyer — Vancouver, WA*
`FME07Z-0236`

🥬 *Safeway — Portland, OR*
`SAF07Y-1073`

🏢 *Haggen — Bellingham, WA*
`HAG07X-3430`

🍷 *Albertsons — Puyallup, WA*
`ALB07Z-3106`

Send any store number to get started!
"""
            buttons = [[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]]
            await query.edit_message_text(examples_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        elif data == "browse_cities":
            await query.answer()
            cities_text = """🏙️ *Popular Cities*

*Oregon:* Portland, Eugene, Salem, Bend, Beaverton
*Washington:* Vancouver, Seattle, Tacoma, Spokane
*California:* Fresno, Modesto, Redding, Los Angeles

Send any city name to see all stores!
"""
            buttons = [[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]]
            await query.edit_message_text(cities_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        elif data.startswith("action_rates_"):
            store_num = data.replace("action_rates_", "")
            await query.answer()
            context.user_data['selected_store'] = store_num
            await do_rates_lookup(None, store_num, "single", edit_message=query.message)
        elif data.startswith("action_testimonials_"):
            store_num = data.replace("action_testimonials_", "")
            await query.answer()
            store = STORES.get(store_num)
            if store:
                results = find_nearby_testimonials(store, limit=5)
                if not results:
                    text = f"❌ No testimonials found near *{store.get('City', '')}*\n\nTry /keyword to search by topic instead."
                    buttons = [
                        [InlineKeyboardButton("🔍 Search by Keyword", callback_data="testimonial_search")],
                        [InlineKeyboardButton("⬅️ Back to Store", callback_data=f"select_store_{store_num}")],
                    ]
                    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
                else:
                    text = f"📋 *Testimonials near {store.get('City', '')}, {store.get('State', '')}*\n\n"
                    for i, r in enumerate(results[:5], 1):
                        business = r.get('business', 'Unknown').replace('&amp;', '&')
                        comment = r.get('comment', '')
                        url = r.get('url', '').replace('&amp;', '&')
                        if len(comment) > 150:
                            comment = comment[:150] + "..."
                        text += f"*{i}. {business}*\n"
                        if comment:
                            text += f"📝 _{comment}_\n"
                        if url:
                            text += f"🔗 [View]({url})\n"
                        text += "\n"
                    buttons = [
                        [InlineKeyboardButton("🔍 Search by Keyword", callback_data="testimonial_search")],
                        [InlineKeyboardButton("⬅️ Back to Store", callback_data=f"select_store_{store_num}")],
                    ]
                    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
        elif data.startswith("action_prospects_"):
            store_num = data.replace("action_prospects_", "")
            await query.answer()
            context.user_data['selected_store'] = store_num
            await query.edit_message_text("📂 *Select a category:*", parse_mode="Markdown", reply_markup=build_category_keyboard(store_num=store_num))
        elif data.startswith("action_audit_"):
            store_num = data.replace("action_audit_", "")
            await query.answer()
            if store_num not in STORES:
                await query.edit_message_text("❌ Store not found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]]))
                return
            store = STORES[store_num]
            cycle = store.get('Cycle', '?')
            starting_cases = store.get('Case Count', 20)
            
            # Use real shipping data if available
            if SHIPPING_DATA_AVAILABLE:
                status = get_delivery_status(store_num)
                delivery_date = status['last_delivery_date'] or datetime.now()
                
                msg = f"🏪 *Audit: {store_num}*\n\n"
                msg += f"{store.get('GroceryChain', '?')} - {store.get('City', '')}, {store.get('State', '')}\n"
                if status.get('delivery_address'):
                    msg += f"📍 {status['delivery_address']}\n"
                msg += f"🔄 Cycle: {cycle}\n\n"
                
                msg += f"📦 *Delivery Status:*\n"
                if status['last_delivery_date']:
                    date_str = status['last_delivery_date'].strftime('%B %d, %Y')
                    msg += f"{status['status_emoji']} Last delivery: *{date_str}*\n"
                    msg += f"⏱ {status['days_since_delivery']} days ago\n"
                else:
                    msg += f"❓ No delivery records found\n"
                
                if status['in_transit']:
                    msg += f"\n🚚 *In Transit:* {status['in_transit_count']} shipment(s)\n"
                
                msg += f"\n📦 Case count: *{starting_cases} cases*\n"
                msg += f"\n{status['status_text']}\n"
                msg += f"\nEnter current inventory (rolls remaining):"
                
                buttons = []
                if status.get('tracking_url'):
                    buttons.append([InlineKeyboardButton("📦 Track Last Delivery", url=status['tracking_url'])])
                for t in status.get('in_transit_tracking', []):
                    buttons.append([InlineKeyboardButton(f"🚚 Track In-Transit", url=t['url'])])
                buttons.append([InlineKeyboardButton("⬅️ Back", callback_data=f"select_store_{store_num}")])
                
                context.user_data['audit_info'] = {
                    'store_num': store_num,
                    'cycle': cycle,
                    'delivery_date': delivery_date,
                    'starting_cases': starting_cases,
                    'shipping_status': status,
                }
                context.user_data[AWAITING_AUDIT_INVENTORY] = True
                
                await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
            else:
                # Fallback to old cycle-based logic
                get_delivery_func = get_cycle_delivery_dates()
                delivery_date = get_delivery_func(cycle)
                context.user_data['audit_info'] = {
                    'store_num': store_num,
                    'cycle': cycle,
                    'delivery_date': delivery_date,
                    'starting_cases': starting_cases,
                }
                msg = f"🏪 *Audit: {store_num}*\n\n"
                msg += f"{store.get('GroceryChain', '?')} - {store.get('City', '')}, {store.get('State', '')}\n\n"
                msg += f"📦 *Delivery Confirmation:*\n\n"
                msg += f"_{store_num}_ was sent *{starting_cases} cases* on *{delivery_date.strftime('%B %d, %Y')}*\n\n"
                msg += f"Is this correct?"
                buttons = [
                    [InlineKeyboardButton("✅ Yes, Correct", callback_data="audit_confirm_yes")],
                    [InlineKeyboardButton("❌ No, Adjust", callback_data="audit_confirm_no")],
                    [InlineKeyboardButton("⬅️ Back", callback_data=f"select_store_{store_num}")],
                ]
                await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        elif data == "roi_calculator":
            await query.answer()
            context.user_data[AWAITING_ROI_ADPRICE] = True
            await query.edit_message_text(
                "📊 *ROI Calculator*\n\n"
                "*Step 1:* What's the ad price (annual cost)?\n\n"
                "_Example: 3000 or 5000_",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu_tools")]])
            )
        elif data == "rates_search":
            await query.answer()
            context.user_data[AWAITING_RATES] = True
            await query.edit_message_text(
                "💰 *Register Tape Rates*\n\n"
                "Type a *city name* or *store number*:\n\n"
                "_Examples:_\n"
                "_City: `Portland` or `Eugene`_\n"
                "_Store: `FME07Z-0236`_\n\n"
                "Or tap 📍 to find stores near you!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎬 Presentation", url="https://docs.google.com/presentation/d/1Xs60nX3i6MJkC81GgnK-50jBrkWVPu06xRpmv8z4PIc/edit?usp=sharing")],
                    [InlineKeyboardButton("📹 Explainer Video", url="https://youtu.be/_gdlyEszHfY?si=0_kHou89WrMhvNY_")],
                    [InlineKeyboardButton("📍 Near Me", callback_data="rates_near_me")],
                    [InlineKeyboardButton("⬅️ Back", callback_data="menu_register_tape")],
                ])
            )
        elif data == "rates_near_me":
            await query.answer()
            context.user_data['rates_mode'] = True
            context.user_data['waiting_for_location'] = True
            context.user_data[AWAITING_RATES] = False
            location_button = KeyboardButton("📍 Share My Location", request_location=True)
            keyboard = ReplyKeyboardMarkup([[location_button]], one_time_keyboard=True, resize_keyboard=True)
            await update.effective_chat.send_message(
                "📍 *Find Stores Near You*\n\nTap the button below to share your location and see nearby store rates.",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        elif data.startswith("roi_open_"):
            await query.answer()
            store_num = data.replace("roi_open_", "")
            store = STORES.get(store_num)
            if store:
                # Initialize ROI parameters with defaults
                context.user_data['roi_store'] = store_num
                context.user_data['roi_redemptions'] = 20
                context.user_data['roi_ticket'] = 35
                context.user_data['roi_cogs'] = 35
                context.user_data['roi_coupon'] = 10
                context.user_data['roi_ad_type'] = 'single'
                context.user_data['roi_payment'] = 'monthly'
                context.user_data['roi_tier'] = 'coop'
                await show_roi_calculator(query, context, store_num)
            else:
                await query.answer("❌ Store not found", show_alert=True)
        
        # ROI Parameter Adjustments (text input)
        elif data.startswith("roi_adj_redemptions_"):
            await query.answer()
            store_num = data.replace("roi_adj_redemptions_", "")
            current = context.user_data.get('roi_redemptions', 20)
            context.user_data[AWAITING_ROI_REDEMPTIONS] = store_num
            await query.edit_message_text(
                f"📊 *Enter redemptions per month:*\n\n"
                f"Current: {current}/mo\n\n"
                f"_Type a number (e.g., 25 or 150)_",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data=f"roi_back_{store_num}")]])
            )
        
        elif data.startswith("roi_adj_ticket_"):
            await query.answer()
            store_num = data.replace("roi_adj_ticket_", "")
            current = context.user_data.get('roi_ticket', 35)
            context.user_data[AWAITING_ROI_TICKET] = store_num
            await query.edit_message_text(
                f"💵 *Enter average ticket amount:*\n\n"
                f"Current: ${current}\n\n"
                f"_Type a dollar amount (e.g., 45 or 125)_",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data=f"roi_back_{store_num}")]])
            )
        
        elif data.startswith("roi_adj_coupon_"):
            await query.answer()
            store_num = data.replace("roi_adj_coupon_", "")
            current = context.user_data.get('roi_coupon', 10)
            context.user_data[AWAITING_ROI_COUPON] = store_num
            await query.edit_message_text(
                f"🏷️ *Enter coupon value:*\n\n"
                f"Current: ${current}\n\n"
                f"_Type a dollar amount (e.g., 5 or 15)_",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data=f"roi_back_{store_num}")]])
            )
        
        elif data.startswith("roi_adj_cogs_"):
            await query.answer()
            store_num = data.replace("roi_adj_cogs_", "")
            current = context.user_data.get('roi_cogs', 35)
            context.user_data[AWAITING_ROI_COGS] = store_num
            await query.edit_message_text(
                f"📦 *Enter COGS percentage:*\n\n"
                f"Current: {current}%\n\n"
                f"_Type a percentage (e.g., 30 or 40)_",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data=f"roi_back_{store_num}")]])
            )
        
        elif data.startswith("roi_adj_adtype_"):
            await query.answer()
            store_num = data.replace("roi_adj_adtype_", "")
            current = context.user_data.get('roi_ad_type', 'single')
            buttons = [
                [
                    InlineKeyboardButton(f"{'✅' if current == 'single' else ''} Single".strip(), callback_data=f"roi_set_adtype_single_{store_num}"),
                    InlineKeyboardButton(f"{'✅' if current == 'double' else ''} Double".strip(), callback_data=f"roi_set_adtype_double_{store_num}"),
                ],
                [InlineKeyboardButton("⬅️ Back", callback_data=f"roi_back_{store_num}")]
            ]
            await query.edit_message_text("*Ad type:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        
        elif data.startswith("roi_set_adtype_"):
            await query.answer()
            parts = data.replace("roi_set_adtype_", "").split("_")
            value = parts[0]
            store_num = parts[1]
            context.user_data['roi_ad_type'] = value
            await show_roi_calculator(query, context, store_num)
        
        elif data.startswith("roi_adj_payment_"):
            await query.answer()
            store_num = data.replace("roi_adj_payment_", "")
            current = context.user_data.get('roi_payment', 'monthly')
            buttons = [
                [InlineKeyboardButton(f"{'✅' if current == 'monthly' else ''} Monthly".strip(), callback_data=f"roi_set_payment_monthly_{store_num}")],
                [InlineKeyboardButton(f"{'✅' if current == 'paid_3' else ''} Paid in 3".strip(), callback_data=f"roi_set_payment_paid_3_{store_num}")],
                [InlineKeyboardButton(f"{'✅' if current == 'paid_6' else ''} Paid in 6".strip(), callback_data=f"roi_set_payment_paid_6_{store_num}")],
                [InlineKeyboardButton(f"{'✅' if current == 'paid_full' else ''} Paid in Full".strip(), callback_data=f"roi_set_payment_paid_full_{store_num}")],
                [InlineKeyboardButton("⬅️ Back", callback_data=f"roi_back_{store_num}")]
            ]
            await query.edit_message_text("*Payment plan:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        
        elif data.startswith("roi_set_payment_"):
            await query.answer()
            parts = data.replace("roi_set_payment_", "").split("_", 1)
            value = "_".join(parts[:-1])
            store_num = parts[-1]
            context.user_data['roi_payment'] = value
            await show_roi_calculator(query, context, store_num)
        
        elif data.startswith("roi_adj_tier_"):
            await query.answer()
            store_num = data.replace("roi_adj_tier_", "")
            current = context.user_data.get('roi_tier', 'coop')
            buttons = [
                [
                    InlineKeyboardButton(f"{'✅' if current == 'coop' else ''} Co-Op".strip(), callback_data=f"roi_set_tier_coop_{store_num}"),
                    InlineKeyboardButton(f"{'✅' if current == 'standard' else ''} Standard".strip(), callback_data=f"roi_set_tier_standard_{store_num}"),
                ],
                [InlineKeyboardButton("⬅️ Back", callback_data=f"roi_back_{store_num}")]
            ]
            await query.edit_message_text("*Tier:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        
        elif data.startswith("roi_set_tier_"):
            await query.answer()
            parts = data.replace("roi_set_tier_", "").split("_")
            value = parts[0]
            store_num = parts[1]
            context.user_data['roi_tier'] = value
            await show_roi_calculator(query, context, store_num)
        
        elif data.startswith("roi_back_"):
            store_num = data.replace("roi_back_", "")
            await show_roi_calculator(query, context, store_num)
        
        elif data.startswith("rates_single_") or data.startswith("rates_double_"):
            await query.answer()
            if data.startswith("rates_single_"):
                store_num = data.replace("rates_single_", "")
                ad_type = "single"
            else:
                store_num = data.replace("rates_double_", "")
                ad_type = "double"
            await do_rates_lookup(None, store_num, ad_type, edit_message=query.message)
        elif data.startswith("tier_coop_"):
            await query.answer()
            parts = data.replace("tier_coop_", "").rsplit("_", 1)
            ad_type = parts[0]
            store_num = parts[1]
            store = STORES.get(store_num)
            if store:
                # Track selected tier for cart add
                context.user_data['selected_tier'] = 'coop'
                pricing = calculate_pricing(store, ad_type)
                text = format_rates_message_coop(pricing)
                buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📄 Single Ad", callback_data=f"rates_single_{store_num}"),
                     InlineKeyboardButton("📋 Double Ad", callback_data=f"rates_double_{store_num}")],
                    [InlineKeyboardButton("🛒 Monthly", callback_data=f"cart_add_{ad_type}_monthly_{store_num}"),
                     InlineKeyboardButton("🛒 6-Month", callback_data=f"cart_add_{ad_type}_6month_{store_num}")],
                    [InlineKeyboardButton("🛒 3-Month", callback_data=f"cart_add_{ad_type}_3month_{store_num}"),
                     InlineKeyboardButton("🛒 PIF", callback_data=f"cart_add_{ad_type}_pif_{store_num}")],
                    [InlineKeyboardButton("⬅️ Back", callback_data=f"rates_single_{store_num}" if ad_type == "single" else f"rates_double_{store_num}")],
                ])
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=buttons)
        elif data.startswith("tier_exclusive_"):
            await query.answer()
            parts = data.replace("tier_exclusive_", "").rsplit("_", 1)
            ad_type = parts[0]
            store_num = parts[1]
            store = STORES.get(store_num)
            if store:
                # Track selected tier for cart add
                context.user_data['selected_tier'] = 'exclusive'
                pricing = calculate_pricing(store, ad_type)
                text = format_rates_message_exclusive(pricing)
                buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📄 Single Ad", callback_data=f"rates_single_{store_num}"),
                     InlineKeyboardButton("📋 Double Ad", callback_data=f"rates_double_{store_num}")],
                    [InlineKeyboardButton("🛒 Monthly", callback_data=f"cart_add_{ad_type}_monthly_{store_num}"),
                     InlineKeyboardButton("🛒 6-Month", callback_data=f"cart_add_{ad_type}_6month_{store_num}")],
                    [InlineKeyboardButton("🛒 3-Month", callback_data=f"cart_add_{ad_type}_3month_{store_num}"),
                     InlineKeyboardButton("🛒 PIF", callback_data=f"cart_add_{ad_type}_pif_{store_num}")],
                    [InlineKeyboardButton("⬅️ Back", callback_data=f"rates_single_{store_num}" if ad_type == "single" else f"rates_double_{store_num}")],
                ])
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=buttons)
        elif data.startswith("tier_contractor_"):
            await query.answer()
            parts = data.replace("tier_contractor_", "").rsplit("_", 1)
            ad_type = parts[0]
            store_num = parts[1]
            store = STORES.get(store_num)
            if store:
                # Track selected tier for cart add
                context.user_data['selected_tier'] = 'contractor'
                pricing = calculate_pricing(store, ad_type)
                text = format_rates_message_contractor(pricing)
                buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📄 Single Ad", callback_data=f"rates_single_{store_num}"),
                     InlineKeyboardButton("📋 Double Ad", callback_data=f"rates_double_{store_num}")],
                    [InlineKeyboardButton("🛒 Monthly", callback_data=f"cart_add_{ad_type}_monthly_{store_num}"),
                     InlineKeyboardButton("🛒 6-Month", callback_data=f"cart_add_{ad_type}_6month_{store_num}")],
                    [InlineKeyboardButton("🛒 3-Month", callback_data=f"cart_add_{ad_type}_3month_{store_num}"),
                     InlineKeyboardButton("🛒 PIF", callback_data=f"cart_add_{ad_type}_pif_{store_num}")],
                    [InlineKeyboardButton("⬅️ Back", callback_data=f"rates_single_{store_num}" if ad_type == "single" else f"rates_double_{store_num}")],
                ])
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=buttons)
        elif data.startswith("cart_payment_"):
            # Select payment plan for adding to cart
            await query.answer()
            parts = data.replace("cart_payment_", "").rsplit("_", 1)
            ad_type = parts[0]
            store_num = parts[1]
            store = STORES.get(store_num)
            
            if store:
                pricing = calculate_pricing(store, ad_type)
                text = f"💰 *Select Payment Plan*\n\n"
                text += f"📍 *{store.get('GroceryChain', '?')}* — {store.get('City', '')}, {store.get('State', '')}\n"
                text += f"📄 {ad_type.title()} Ad\n\n"
                text += "*Payment Plans:*\n"
                text += f"🔄 Monthly: ${pricing['monthly_price']:,.0f}\n"
                text += f"3️⃣ 3-Month: ${pricing['3month_price']:,.0f}\n"
                text += f"6️⃣ 6-Month: ${pricing['6month_price']:,.0f}\n"
                text += f"💵 Paid in Full: ${pricing['pif_price']:,.0f}\n"
                
                buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Monthly", callback_data=f"cart_add_{ad_type}_monthly_{store_num}")],
                    [InlineKeyboardButton("3️⃣ 3-Month", callback_data=f"cart_add_{ad_type}_3month_{store_num}")],
                    [InlineKeyboardButton("6️⃣ 6-Month", callback_data=f"cart_add_{ad_type}_6month_{store_num}")],
                    [InlineKeyboardButton("💵 Paid in Full", callback_data=f"cart_add_{ad_type}_pif_{store_num}")],
                    [InlineKeyboardButton("⬅️ Back", callback_data=f"rates_{ad_type}_{store_num}")],
                ])
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=buttons)
        elif data.startswith("cart_add_"):
            # Add item to cart (Register Tape)
            await query.answer("✅ Added to cart!", show_alert=False)
            parts = data.replace("cart_add_", "").rsplit("_", 1)
            store_num = parts[1]
            payment_info = parts[0].rsplit("_", 1)
            ad_type = payment_info[0]
            payment_plan = payment_info[1]
            
            rep_id = get_rep_id(update)  # Use update directly
            
            # Add Register Tape to cart with new signature
            # Determine tier from context or default to coop
            tier = context.user_data.get('selected_tier', 'coop')
            price = add_to_cart(
                rep_id=rep_id,
                product_type="register_tape",
                tier=tier,
                store_num=store_num,
                ad_type=ad_type,
                payment_plan=payment_plan
            )
            
            if price:
                await query.edit_message_text(
                    f"✅ *Added to Cart!*\n\n"
                    f"💰 Price: ${price:,.0f}\n"
                    f"🛒 View cart from the main menu",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
                )
        elif data == "product_child_seat":
            await show_product_child_seat(update, context)
        elif data == "product_nose":
            await show_product_nose(update, context)
        elif data == "product_digitalboost":
            await show_product_digitalboost(update, context)
        elif data.startswith("db_select_pins_"):
            pin_count = int(data.replace("db_select_pins_", ""))
            await show_product_digitalboost(update, context, pins=pin_count)
        elif data.startswith("cart_coop_child_seat"):
            await show_cart_coop_pricing(update, context, product="child_seat")
        elif data.startswith("cart_standard_child_seat"):
            await show_cart_standard_pricing(update, context, product="child_seat")
        elif data.startswith("cart_add_cartvertising_"):
            # Add Cartvertising to cart
            await query.answer("✅ Added to cart!", show_alert=False)
            parts = data.replace("cart_add_cartvertising_", "").rsplit("_", 1)
            combined = parts[0]  # e.g., 'standalone_monthly', 'bundled_6month'
            payment_plan = parts[1]  # fallback
            
            # Parse the combined parameter
            if "_" in combined:
                bundle_type = combined.split("_")[0]  # 'standalone' or 'bundled'
                payment_plan = "_".join(combined.split("_")[1:])  # 'monthly', '3month', '6month', 'pif'
            else:
                bundle_type = combined
                payment_plan = "monthly"
            
            # Convert impressions to descriptive form
            impressions = "360k" if bundle_type == "bundled" else "240k"
            
            rep_id = get_rep_id(update)
            price = add_to_cart(
                rep_id=rep_id,
                product_type="cartvertising",
                bundle_type=bundle_type,
                impressions=impressions,
                payment_plan=payment_plan,
                tier="standard"
            )
            
            if price:
                await query.edit_message_text(
                    f"✅ *Added to Cart!*\n\n"
                    f"🛒 Cartvertising ({bundle_type.title()})\n"
                    f"📊 {impressions} impressions\n"
                    f"💳 {payment_plan.replace('_', ' ').title()} plan\n"
                    f"💰 ${price:,.0f}\n\n"
                    f"View cart from the main menu to continue",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
                )
        elif data.startswith("cart_add_digitalboost_"):
            # Add DigitalBoost to cart: tier_pincount_plan
            await query.answer("✅ Added to cart!", show_alert=False)
            parts = data.replace("cart_add_digitalboost_", "").rsplit("_", 1)
            combined = parts[0]  # e.g., 'std_3_monthly', 'coop_1_pif'
            payment_plan = parts[1] if len(parts) > 1 else "monthly"
            
            # Parse tier and pin count
            sub_parts = combined.split("_")
            if len(sub_parts) >= 2:
                tier = sub_parts[0]  # 'std' or 'coop'
                pin_count = int(sub_parts[1])
            else:
                tier = "std"
                pin_count = 1
            
            # Convert tier to full name
            tier_name = "Standard" if tier == "std" else "Co-Op"
            
            rep_id = get_rep_id(update)
            price = add_to_cart(
                rep_id=rep_id,
                product_type="digitalboost",
                pin_count=pin_count,
                tier=tier_name,
                payment_plan=payment_plan
            )
            
            if price:
                impressions = 240000 * pin_count
                await query.edit_message_text(
                    f"✅ *Added to Cart!*\n\n"
                    f"🚀 DigitalBoost ({tier_name})\n"
                    f"📌 {pin_count} Pin{'s' if pin_count > 1 else ''}\n"
                    f"📊 {impressions:,} impressions\n"
                    f"💳 {payment_plan.replace('_', ' ').title()} plan\n"
                    f"💰 ${price:,.0f}\n\n"
                    f"View cart from the main menu to continue",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
                )
        elif data == "view_cart":
            # Show cart with all product types
            await query.answer()
            rep_id = get_rep_id(update)  # Use update directly
            cart_items = load_rep_data(rep_id).get("cart", [])
            
            if not cart_items:
                await query.edit_message_text(
                    "🛒 *Your Cart*\n\n_(Empty)_",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
                )
                return
            
            text = "🛒 *Your Cart*\n\n"
            
            # Calculate total
            total = sum(item.get("price", 0) for item in cart_items)
            text += f"💰 *Total: ${total:,.2f}*\n\n"
            
            buttons = []
            
            # Group by product type for display
            for idx, item in enumerate(cart_items):
                product_type = item.get("product_type", "register_tape")
                product_name = item.get("product_name", "Unknown Product")
                price = item.get("price", 0)
                
                # Show all metrics for each item
                text += f"\n📦 *{product_name}*\n"
                text += f"💰 Price: ${price:,.2f}/month\n"
                
                # Show impressions if available
                if "annual_impressions" in item:
                    annual = item.get("annual_impressions", 0)
                    daily = item.get("daily_impressions", 0)
                    text += f"📊 {annual:,} annual impressions ({daily:,}/day)\n"
                
                # Show CPM if available
                if "cpm" in item and item["cpm"] > 0:
                    text += f"💹 CPM: ${item['cpm']:.2f}\n"
                
                # Show cost per day if available
                if "cost_per_day" in item and item["cost_per_day"] > 0:
                    text += f"📅 Cost/Day: ${item['cost_per_day']:.2f}\n"
                
                # Product-specific details
                if product_type == "register_tape":
                    text += f"📍 {item.get('store_name', '?')} — {item.get('city', '')}, {item.get('state', '')}\n"
                    text += f"📄 {item.get('ad_type', 'N/A').title()} Ad | {item.get('payment_plan', 'N/A').title()}\n"
                elif product_type == "cartvertising":
                    text += f"🛒 Bundle: {item.get('bundle_type', 'standalone').title()}\n"
                elif product_type == "digitalboost":
                    text += f"📍 {item.get('pin_count', 1)} Pin{'s' if item.get('pin_count', 1) > 1 else ''}\n"
                
                buttons.append([InlineKeyboardButton(f"❌ Remove", callback_data=f"cart_remove_{idx}")])
            
            text += f"\n\n✅ Ready to finalize?"
            buttons.append([InlineKeyboardButton("📋 Generate Proposal", callback_data="cart_proposal")])
            buttons.append([InlineKeyboardButton("⬅️ Continue Shopping", callback_data="main_menu")])
            
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        elif data.startswith("cart_remove_"):
            # Remove from cart
            await query.answer()
            idx = int(data.replace("cart_remove_", ""))
            rep_id = get_rep_id(update)  # Use update directly
            remove_from_cart(rep_id, idx)
            
            # Refresh cart view
            cart_items = load_rep_data(rep_id).get("cart", [])
            
            if not cart_items:
                await query.edit_message_text(
                    "🛒 *Your Cart*\n\n_(Empty)_",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
                )
                return
            
            text = "🛒 *Your Cart*\n\n"
            
            # Calculate total
            total = sum(item.get("price", 0) for item in cart_items)
            text += f"💰 *Total: ${total:,.2f}*\n\n"
            
            buttons = []
            
            # Group by product type for display
            for idx, item in enumerate(cart_items):
                product_type = item.get("product_type", "register_tape")
                product_name = item.get("product_name", "Unknown Product")
                price = item.get("price", 0)
                
                # Show all metrics for each item
                text += f"\n📦 *{product_name}*\n"
                text += f"💰 Price: ${price:,.2f}/month\n"
                
                # Show impressions if available
                if "annual_impressions" in item:
                    annual = item.get("annual_impressions", 0)
                    daily = item.get("daily_impressions", 0)
                    text += f"📊 {annual:,} annual impressions ({daily:,}/day)\n"
                
                # Show CPM if available
                if "cpm" in item and item["cpm"] > 0:
                    text += f"💹 CPM: ${item['cpm']:.2f}\n"
                
                # Show cost per day if available
                if "cost_per_day" in item and item["cost_per_day"] > 0:
                    text += f"📅 Cost/Day: ${item['cost_per_day']:.2f}\n"
                
                # Product-specific details
                if product_type == "register_tape":
                    text += f"📍 {item.get('store_name', '?')} — {item.get('city', '')}, {item.get('state', '')}\n"
                    text += f"📄 {item.get('ad_type', 'N/A').title()} Ad | {item.get('payment_plan', 'N/A').title()}\n"
                elif product_type == "cartvertising":
                    text += f"🛒 Bundle: {item.get('bundle_type', 'standalone').title()}\n"
                elif product_type == "digitalboost":
                    text += f"📍 {item.get('pin_count', 1)} Pin{'s' if item.get('pin_count', 1) > 1 else ''}\n"
                
                buttons.append([InlineKeyboardButton(f"❌ Remove", callback_data=f"cart_remove_{idx}")])
            
            text += f"\n\n✅ Ready to finalize?"
            buttons.append([InlineKeyboardButton("📋 Generate Proposal", callback_data="cart_proposal")])
            buttons.append([InlineKeyboardButton("⬅️ Continue Shopping", callback_data="main_menu")])
            
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        elif data == "cart_proposal":
            # Generate proposal (supports all products)
            await query.answer()
            rep_id = get_rep_id(update)  # Use update directly
            rep_name = get_rep_name(update)  # Use update directly
            cart_items = load_rep_data(rep_id).get("cart", [])
            
            if not cart_items:
                await query.edit_message_text(
                    "❌ Cart is empty",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
                )
                return
            
            # Calculate total
            total = sum(item.get("price", 0) for item in cart_items)
            
            # Store proposal in context for copying/exporting
            proposal_text = f"""INDOORMEDIA ADVERTISING PROPOSAL

Rep: {rep_name}
Date: {datetime.now().strftime('%B %d, %Y')}

{'='*60}
SERVICES & PRICING
{'='*60}

"""
            
            # Generate proposal for each item
            for idx, item in enumerate(cart_items, 1):
                product_type = item.get("product_type", "register_tape")
                product_name = item.get("product_name", "Unknown Product")
                price = item.get("price", 0)
                
                proposal_text += f"\n{idx}. {product_name}\n"
                proposal_text += f"   Price: ${price:,.2f}\n"
                
                # Add product-specific details
                if product_type == "register_tape":
                    proposal_text += f"   Store: {item.get('store_num', 'N/A')} - {item.get('store_name', '?')}\n"
                    proposal_text += f"   Location: {item.get('city', '')}, {item.get('state', '')}\n"
                    proposal_text += f"   Ad Type: {item.get('ad_type', 'N/A').title()}\n"
                    proposal_text += f"   Payment Plan: {item.get('payment_plan', 'N/A').title()}\n"
                elif product_type == "cartvertising":
                    proposal_text += f"   Bundle: {item.get('bundle_type', 'standalone').title()}\n"
                elif product_type == "digitalboost":
                    proposal_text += f"   Pins: {item.get('pin_count', 1)}\n"
                
                # Show metrics
                if item.get("annual_impressions"):
                    proposal_text += f"   Annual Impressions: {item.get('annual_impressions', 0):,}\n"
                    proposal_text += f"   Daily Impressions: {item.get('daily_impressions', 0):,}\n"
                if item.get("cpm"):
                    proposal_text += f"   CPM: ${item.get('cpm', 0):.2f}\n"
                if item.get("cost_per_day"):
                    proposal_text += f"   Cost Per Day: ${item.get('cost_per_day', 0):.2f}\n"
            
            proposal_text += f"\n{'='*60}\n"
            proposal_text += f"GRAND TOTAL: ${total:,.2f}\n"
            proposal_text += f"{'='*60}\n\n"
            proposal_text += "Ready to discuss terms?\n"
            proposal_text += "Contact us to finalize your campaign.\n"
            
            # Store in context for export
            context.user_data['proposal_text'] = proposal_text
            context.user_data['proposal_total'] = total
            
            text = f"📋 *Proposal Generated*\n\n"
            text += f"💰 *Total: ${total:,.2f}*\n\n"
            text += f"✅ Select action:"
            
            buttons = [
                [InlineKeyboardButton("📋 Copy Text", callback_data="cart_copy_text")],
                [InlineKeyboardButton("📄 Download PDF", callback_data="cart_pdf")],
                [InlineKeyboardButton("⬅️ Back to Cart", callback_data="view_cart")],
                [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")],
            ]
            
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        elif data == "cart_copy_text":
            # Copy proposal to Telegram (as code block for easy copying)
            await query.answer()
            proposal_text = context.user_data.get('proposal_text', '')
            
            if proposal_text:
                await query.edit_message_text(
                    f"```\n{proposal_text}\n```",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📄 Download PDF", callback_data="cart_pdf")],
                        [InlineKeyboardButton("⬅️ Back", callback_data="cart_proposal")],
                    ])
                )
            else:
                await query.answer("❌ Proposal not found", show_alert=True)
        elif data == "cart_pdf":
            # Generate PDF proposal (supports all products)
            await query.answer()
            rep_id = get_rep_id(update)  # Use update directly
            rep_name = get_rep_name(update)  # Use update directly
            cart_items = load_rep_data(rep_id).get("cart", [])
            
            if not cart_items:
                await query.answer("❌ Cart is empty", show_alert=True)
                return
            
            # Show interim message while generating
            await query.edit_message_text("🔄 Generating PDF...", reply_markup=None)
            
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.lib import colors
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import inch
                
                # Create PDF
                pdf_path = Path(tempfile.gettempdir()) / f"proposal_{rep_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
                elements = []
                styles = getSampleStyleSheet()
                
                # Title
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=24,
                    textColor=colors.HexColor('#CC0000'),
                    spaceAfter=30,
                    alignment=1  # Center
                )
                elements.append(Paragraph("INDOORMEDIA", title_style))
                elements.append(Paragraph("Advertising Proposal", styles['Heading2']))
                elements.append(Spacer(1, 12))
                
                # Rep info and contact
                rep_email = get_rep_email(update)
                rep_phone = get_rep_phone(update)
                elements.append(Paragraph(f"<b>Rep:</b> {rep_name}", styles['Normal']))
                elements.append(Paragraph(f"<b>Email:</b> {rep_email}", styles['Normal']))
                elements.append(Paragraph(f"<b>Phone:</b> {rep_phone}", styles['Normal']))
                elements.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
                elements.append(Spacer(1, 12))
                
                # Services & Pricing section
                elements.append(Paragraph("Services & Pricing", styles['Heading3']))
                
                # Build table with all items - include monthly investment
                table_data = [["Service", "Details", "Annual Investment", "Monthly Investment"]]
                total = 0
                monthly_total = 0
                for item in cart_items:
                    product_name = item.get("product_name", "Unknown")
                    price = item.get("price", 0)
                    monthly_price = price / 12
                    total += price
                    monthly_total += monthly_price
                    
                    # Build details column based on product type
                    product_type = item.get("product_type", "register_tape")
                    if product_type == "register_tape":
                        details = f"{item.get('store_num', 'N/A')} - {item.get('store_name', '?')}\n{item.get('city', '')}, {item.get('state', '')}\n{item.get('ad_type', '').title()} Ad"
                    elif product_type == "cartvertising":
                        details = f"Bundle: {item.get('bundle_type', 'standalone').title()}"
                    elif product_type == "digitalboost":
                        details = f"{item.get('pin_count', 1)} Pin{'s' if item.get('pin_count', 1) > 1 else ''}"
                    else:
                        details = ""
                    
                    table_data.append([product_name, details, f"${price:,.2f}", f"${monthly_price:,.2f}"])
                
                # Build and add table once (not per item)
                table = Table(table_data, colWidths=[2*inch, 2.25*inch, 1.25*inch, 1.5*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#CC0000')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
                    ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTNAME', (2, 1), (-1, -1), 'Helvetica-Bold'),
                    ('FONTNAME', (3, 1), (3, -1), 'Helvetica-Bold'),
                ]))
                elements.append(table)
                elements.append(Spacer(1, 12))
                
                # Store Traffic & Metrics section (for Register Tape items)
                rt_items = [item for item in cart_items if item.get("product_type") == "register_tape"]
                if rt_items:
                    elements.append(Paragraph("Store Traffic & Metrics", styles['Heading3']))
                    
                    for item in rt_items:
                        # Store header
                        store_info = f"{item.get('store_num', 'N/A')} - {item.get('store_name', '?')} ({item.get('city', '')}, {item.get('state', '')})"
                        elements.append(Paragraph(f"<b>{store_info}</b>", styles['Normal']))
                        
                        # Metrics table
                        metrics_data = [
                            ["Metric", "Value"],
                            ["Daily Impressions", f"{item.get('daily_impressions', 0):,}"],
                            ["Monthly Impressions", f"{int(item.get('daily_impressions', 0) * 30):,}"],
                            ["Annual Impressions", f"{item.get('annual_impressions', 0):,}"],
                            ["Cost Per Day", f"${item.get('cost_per_day', 0):,.2f}"],
                            ["CPM (Cost Per 1000)", f"${item.get('cpm', 0):,.2f}"],
                        ]
                        
                        metrics_table = Table(metrics_data, colWidths=[3*inch, 2*inch])
                        metrics_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#CC0000')),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, -1), 9),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ]))
                        elements.append(metrics_table)
                        elements.append(Spacer(1, 12))
                
                # Grand total (annual and monthly)
                elements.append(Spacer(1, 12))
                total_style = ParagraphStyle(
                    'Total',
                    parent=styles['Heading2'],
                    fontSize=14,
                    textColor=colors.HexColor('#CC0000'),
                    spaceAfter=6
                )
                elements.append(Paragraph(f"TOTAL ANNUAL INVESTMENT: ${total:,.2f}", total_style))
                elements.append(Paragraph(f"TOTAL MONTHLY INVESTMENT: ${monthly_total:,.2f}", total_style))
                
                # Footer
                elements.append(Spacer(1, 20))
                elements.append(Paragraph("Ready to discuss terms? Contact us to finalize your campaign.", styles['Normal']))
                
                # Build PDF
                doc.build(elements)
                
                # Send PDF to chat
                with open(pdf_path, 'rb') as pdf_file:
                    await update.effective_chat.send_document(
                        pdf_file,
                        caption=f"📄 Proposal: ${total:,.2f}",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
                    )
                
                # Cleanup
                pdf_path.unlink()
                await query.edit_message_text(
                    "✅ PDF sent!",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
                )
                
            except ImportError:
                await query.answer("❌ PDF library not installed", show_alert=True)
            except Exception as e:
                logger.error(f"PDF generation error: {e}")
                await query.answer(f"❌ Error generating PDF: {e}", show_alert=True)
        elif data.startswith("tpage_"):
            # Testimonial pagination
            offset = int(data.replace("tpage_", ""))
            await query.answer()
            results = context.user_data.get('testimonial_results', [])
            keyword = context.user_data.get('testimonial_keyword', '?')
            if results:
                text, keyboard = format_testimonial_page(results, keyword, offset=offset)
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard, disable_web_page_preview=True)
        elif data == "testimonial_search":
            await query.answer()
            context.user_data[AWAITING_KEYWORD] = True
            await query.edit_message_text(
                "🔍 *Testimonial Search*\n\nSend a keyword to search testimonials:\n\n"
                "_Examples: pizza, ROI, skeptical, salon, parking lot, coupon_",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
            )
        elif data == "audit_send_report":
            await query.answer("📧 Sending report...", show_alert=True)
            
            rep_id = get_rep_id(update)
            rep_name = get_rep_name(update)
            report = context.user_data.get('audit_report', {})
            
            # Send email
            success = await send_audit_email(
                update.effective_chat.id,
                report.get('store_num', '?'),
                rep_name,
                rep_id,
                report.get('delivery_date', datetime.now()),
                report.get('starting_cases', 0),
                report.get('current_cases', 0),
                report.get('current_rolls', 0),
                report.get('days_until_delivery', 0),
                report.get('alert', False)
            )
            
            if success:
                msg = "✅ *Audit Report Sent*\n\n"
                msg += f"Report emailed to Tyler at tyler.vansant@indoormedia.com\n\n"
                msg += "_Ready for another audit?_"
                buttons = [
                    [InlineKeyboardButton("🏪 Audit Another Store", callback_data="audit_store")],
                    [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")],
                ]
            else:
                msg = "❌ *Failed to Send Report*\n\n"
                msg += "There was an error sending the email. Please try again later."
                buttons = [[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]]
            
            # Clear audit data
            context.user_data.pop('audit_report', None)
            context.user_data.pop('audit_info', None)
            context.user_data['audit_mode'] = False
            
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        elif data == "submit_testimonial":
            await handle_testimonial_flow(update, context)
        elif data.startswith("test_roi_"):
            await query.answer()
            rating = data.replace("test_roi_", "").upper()
            context.user_data[AWAITING_TEST_ROI] = False
            context.user_data['testimonial_form']['roi_rating'] = rating
            context.user_data[AWAITING_TEST_DURATION] = True
            
            await query.edit_message_text(
                f"✅ ROI Rating: *{rating}* saved.\n\n*Step 11:* How long have you participated in our program? (e.g., 6 months, 1 year)",
                parse_mode="Markdown"
            )
        elif data.startswith("test_renew_"):
            await query.answer()
            answer = "YES" if "yes" in data else "NO"
            context.user_data[AWAITING_TEST_RENEW] = False
            context.user_data['testimonial_form']['renew'] = answer
            context.user_data[AWAITING_TEST_RECOMMEND] = True
            
            buttons = [
                [InlineKeyboardButton("✅ YES", callback_data="test_recommend_yes")],
                [InlineKeyboardButton("❌ NO", callback_data="test_recommend_no")],
            ]
            await query.edit_message_text(
                f"✅ Renew: *{answer}* saved.\n\n*Step 13:* Would you recommend this program to other businesses?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        elif data.startswith("test_recommend_"):
            await query.answer()
            answer = "YES" if "yes" in data else "NO"
            context.user_data[AWAITING_TEST_RECOMMEND] = False
            context.user_data['testimonial_form']['recommend'] = answer
            context.user_data[AWAITING_TEST_COMMENTS] = True
            
            await query.edit_message_text(
                f"✅ Recommend: *{answer}* saved.\n\n*Step 14 (Optional):* Any additional comments about the program?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Skip Comments", callback_data="test_skip_comments")]])
            )
        elif data == "test_skip_comments":
            await query.answer()
            context.user_data[AWAITING_TEST_COMMENTS] = False
            context.user_data['testimonial_form']['comments'] = ""
            context.user_data[AWAITING_TEST_COUPON_IMAGE] = True
            
            await query.edit_message_text(
                "✅ Comments skipped.\n\n*Step 15:* Now, please attach a photo of a coupon sample.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📸 Attach Photo", callback_data="test_attach_photo")]])
            )
        elif data == "test_attach_photo":
            await query.answer()
            await query.edit_message_text(
                "📸 Please send a photo of the coupon sample (or use the attachment button)."
            )
        elif data == "test_final_submit":
            await query.answer()
            form = context.user_data.get('testimonial_form', {})
            photo_path = form.get('coupon_image')
            
            # Save the testimonial
            success = await submit_testimonial_email(form, photo_path)
            
            if success:
                # Send success message to rep
                msg = f"""
                ✅ *Testimonial Submitted!*
                
                Thank you for submitting a testimonial for {form.get('business', '')}.
                
                Your filled form has been saved and your coupon image is on file. Tyler will review your submission.
                """.strip()
                
                # Send the filled form back to the rep (as a downloadable file)
                try:
                    submission_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                    business_name = form.get('business', 'Unknown').replace(' ', '_')[:20]
                    submission_folder = f"/Users/tylervansant/.openclaw/workspace/data/testimonial_submissions/{submission_id}_{business_name}"
                    
                    # Send coupon image back to rep
                    coupon_dest = os.path.join(submission_folder, "coupon.jpg")
                    if os.path.exists(coupon_dest):
                        with open(coupon_dest, 'rb') as f:
                            await update.effective_chat.send_photo(
                                photo=f,
                                caption="📸 Your submitted coupon image"
                            )
                    
                    # Send the filled form HTML as a document
                    html_file = os.path.join(submission_folder, "form_filled.html")
                    if os.path.exists(html_file):
                        with open(html_file, 'rb') as f:
                            await update.effective_chat.send_document(
                                document=f,
                                filename=f"testimonial_{business_name}.html",
                                caption="📝 Your filled testimonial form"
                            )
                except Exception as e:
                    logger.warning(f"Could not send form back to rep: {e}")
                
                buttons = [[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]]
            else:
                msg = f"""
                ⚠️ *Error Submitting*
                
                There was an issue saving your testimonial. Please contact Tyler directly.
                """.strip()
                buttons = [[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]]
            
            # Clean up temp file
            if photo_path and os.path.exists(photo_path):
                try:
                    os.remove(photo_path)
                except:
                    pass
            
            # Clear testimonial form data
            context.user_data.pop('testimonial_form', None)
            clear_awaiting_states(context)
            
            await query.edit_message_text(
                msg,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        elif data == "audit_store":
            await handle_audit_flow(update, context)
        elif data == "counter_sign_generator":
            if COUNTER_SIGN_AVAILABLE:
                await query.answer()
                await start_counter_sign_guided(update, context)
            else:
                await query.answer("❌ Counter sign generator not available", show_alert=True)
        elif data.startswith("counter_sign_chain_"):
            if COUNTER_SIGN_AVAILABLE:
                try:
                    from counter_sign_workflow import handle_store_chain_selection
                    await handle_store_chain_selection(update, context)
                except Exception as e:
                    await query.answer(f"❌ Error: {e}", show_alert=True)
                    logger.error(f"Counter sign chain error: {e}")
            else:
                await query.answer("❌ Counter sign generator not available", show_alert=True)
        elif data.startswith("audit_zone_"):
            zone_code = data.replace("audit_zone_", "")
            await query.answer()
            if SHIPPING_DATA_AVAILABLE:
                report = format_zone_report(zone_code)
                buttons = [
                    [InlineKeyboardButton("🏪 Audit a Store", callback_data="audit_store")],
                    [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")],
                ]
                await query.edit_message_text(report, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
            else:
                await query.edit_message_text("❌ Shipping data not available.", parse_mode="Markdown")
        elif data == "client_list":
            await show_client_list(update, context)
        elif data == "client_list_all":
            await show_client_list_all(update, context)
        elif data == "audit_confirm_yes":
            await query.answer()
            # Move to inventory entry
            audit_info = context.user_data.get('audit_info', {})
            store_num = audit_info.get('store_num', '?')
            
            await query.edit_message_text(
                f"📦 *Enter Current Inventory*\n\n"
                f"For *{store_num}*:\n\n"
                f"Send your current inventory in format:\n`CASES ROLLS`\n\n"
                f"_Example: `15 25` means 15 cases and 25 rolls_\n\n"
                f"(Cases: 0-50, Rolls: 0-49)",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data="main_menu")]])
            )
            context.user_data[AWAITING_AUDIT_INVENTORY] = True
        elif data == "audit_confirm_no":
            await query.answer()
            audit_info = context.user_data.get('audit_info', {})
            
            # Show month and quantity adjustment buttons
            months = ['January', 'February', 'March', 'April', 'May', 'June',
                     'July', 'August', 'September', 'October', 'November', 'December']
            
            buttons = []
            buttons.append([InlineKeyboardButton("📅 Change Month", callback_data="audit_adjust_month")])
            buttons.append([InlineKeyboardButton("📦 Change Cases", callback_data="audit_adjust_cases")])
            buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
            
            await query.edit_message_text(
                "❓ *What would you like to adjust?*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        elif data == "audit_adjust_month":
            await query.answer()
            
            months = ['January', 'February', 'March', 'April', 'May', 'June',
                     'July', 'August', 'September', 'October', 'November', 'December']
            
            buttons = []
            for i, month in enumerate(months, 1):
                buttons.append([InlineKeyboardButton(month, callback_data=f"audit_month_{i}")])
            buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="audit_confirm_no")])
            
            await query.edit_message_text(
                "📅 *Select Delivery Month:*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        elif data.startswith("audit_month_"):
            month = int(data.replace("audit_month_", ""))
            await query.answer()
            
            audit_info = context.user_data.get('audit_info', {})
            delivery_date = audit_info.get('delivery_date')
            
            # Set new delivery date with selected month
            new_date = delivery_date.replace(month=month)
            audit_info['delivery_date'] = new_date
            context.user_data['audit_info'] = audit_info
            
            store_num = audit_info.get('store_num', '?')
            starting_cases = audit_info.get('starting_cases', 20)
            
            msg = f"✅ *Delivery Updated*\n\n"
            msg += f"*{store_num}:* {starting_cases} cases on {new_date.strftime('%B %d, %Y')}\n\n"
            msg += "Now enter current inventory:\n`CASES ROLLS`"
            
            buttons = [[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]]
            
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
            context.user_data[AWAITING_AUDIT_INVENTORY] = True
        elif data == "audit_adjust_cases":
            await query.answer()
            
            buttons = []
            for i in range(0, 51, 5):
                buttons.append([InlineKeyboardButton(f"{i} cases", callback_data=f"audit_cases_{i}")])
            buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="audit_confirm_no")])
            
            await query.edit_message_text(
                "📦 *Select Starting Cases:*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        elif data.startswith("audit_cases_"):
            cases = int(data.replace("audit_cases_", ""))
            await query.answer()
            
            audit_info = context.user_data.get('audit_info', {})
            audit_info['starting_cases'] = cases
            context.user_data['audit_info'] = audit_info
            
            store_num = audit_info.get('store_num', '?')
            delivery_date = audit_info.get('delivery_date')
            
            msg = f"✅ *Cases Updated*\n\n"
            msg += f"*{store_num}:* {cases} cases on {delivery_date.strftime('%B %d, %Y')}\n\n"
            msg += "Now enter current inventory:\n`CASES ROLLS`"
            
            buttons = [[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]]
            
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
            context.user_data[AWAITING_AUDIT_INVENTORY] = True
        elif data == "reset_search":
            await query.answer()
            context.user_data.clear()
            await query.edit_message_text("🔄 Search reset. Start fresh?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]]))
        elif data == "back_categories":
            await handle_back_to_categories(update, context)
        elif data == "new_search":
            await query.answer()
            clear_awaiting_states(context)
            await query.edit_message_text("🔍 Send a store number or city name:")
        elif data.startswith("city_"):
            # City selection from multiple matches
            city = data.replace("city_", "")
            await query.answer()
            await show_city_stores(update, context, city, edit_message=True)
        elif data.startswith("select_store_"):
            # Store selection from city list → show action menu
            store_num = data.replace("select_store_", "")
            await query.answer()
            context.user_data['selected_store'] = store_num
            store = STORES.get(store_num)
            if store:
                await show_store_action_menu(None, store_num, store, edit_message=query.message, context=context)
        elif data.startswith("cat_"):
            await handle_category_select(update, context)
        elif data.startswith("subcat_"):
            await handle_subcategory_select(update, context)
        elif data.startswith("prospect_add_cart_"):
            # Add service from prospect card
            await query.answer()
            prospect_id = data.replace("prospect_add_cart_", "")
            
            rep_id = get_rep_id(update)  # Use update, not query
            data_obj = load_prospect_data()
            rep_data = data_obj["reps"][rep_id]
            prospect = rep_data["saved_prospects"].get(prospect_id, {})
            
            if not prospect:
                await query.answer("❌ Prospect not found", show_alert=True)
                return
            
            # Store prospect in context for cart flow
            context.user_data['cart_prospect_id'] = prospect_id
            context.user_data['cart_prospect_name'] = prospect.get('name', 'Unknown')
            
            # Show store selection (for the prospect's location)
            await query.edit_message_text(
                "🏪 *Select Store*\n\n_Type or search for a store number to add services_",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 Search Stores", callback_data="cart_search_stores")],
                    [InlineKeyboardButton("⬅️ Back", callback_data=f"prospect_detail_{prospect_id}")],
                ])
            )
            context.user_data[AWAITING_CART_STORE] = True
        elif data == "cart_search_stores":
            # Let user search for a store
            await query.answer()
            await query.edit_message_text(
                "🔍 *Find Store*\n\n_Enter a store number (e.g., FME07Z-0236) or city name_",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]])
            )
            context.user_data[AWAITING_CART_STORE] = True
        elif data.startswith("cart_select_store_"):
            # Store selected, now choose ad type
            await query.answer()
            store_num = data.replace("cart_select_store_", "")
            store = STORES.get(store_num)
            
            if store:
                await query.edit_message_text(
                    f"✅ *{store.get('GroceryChain', '?')}* — {store.get('City', '')}, {store.get('State', '')}\n\n"
                    f"Select ad type:",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📄 Single Ad", callback_data=f"cart_single_{store_num}")],
                        [InlineKeyboardButton("📋 Double Ad", callback_data=f"cart_double_{store_num}")],
                        [InlineKeyboardButton("⬅️ Back", callback_data="prospect_add_cart_0")],  # Go back to prospect
                    ])
                )
        elif data.startswith("cart_single_") or data.startswith("cart_double_"):
            # Ad type selected, now choose payment plan
            await query.answer()
            if data.startswith("cart_single_"):
                store_num = data.replace("cart_single_", "")
                ad_type = "single"
            else:
                store_num = data.replace("cart_double_", "")
                ad_type = "double"
            
            store = STORES.get(store_num)
            if store:
                pricing = calculate_pricing(store, ad_type)
                text = f"💰 *Select Payment Plan*\n\n"
                text += f"📍 *{store.get('GroceryChain', '?')}* — {store.get('City', '')}, {store.get('State', '')}\n"
                text += f"📄 {ad_type.title()} Ad\n\n"
                text += "*Payment Plans:*\n"
                text += f"🔄 Monthly: ${pricing['monthly_price']:,.0f}\n"
                text += f"3️⃣ 3-Month: ${pricing['3month_price']:,.0f}\n"
                text += f"6️⃣ 6-Month: ${pricing['6month_price']:,.0f}\n"
                text += f"💵 Paid in Full: ${pricing['pif_price']:,.0f}\n"
                
                buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Monthly", callback_data=f"cart_add_{ad_type}_monthly_{store_num}")],
                    [InlineKeyboardButton("3️⃣ 3-Month", callback_data=f"cart_add_{ad_type}_3month_{store_num}")],
                    [InlineKeyboardButton("6️⃣ 6-Month", callback_data=f"cart_add_{ad_type}_6month_{store_num}")],
                    [InlineKeyboardButton("💵 Paid in Full", callback_data=f"cart_add_{ad_type}_pif_{store_num}")],
                    [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")],
                ])
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=buttons)
        elif data.startswith("back_to_city_"):
            # Go back to city store list
            await query.answer()
            city = data.replace("back_to_city_", "")
            
            if city in CITY_INDEX:
                stores_in_city = CITY_INDEX[city]
                buttons = []
                for store in stores_in_city:
                    store_num = store["StoreName"]
                    chain = store.get("GroceryChain", "")
                    street = store.get("Address", "").split(",")[0] if store.get("Address") else ""
                    street = street.strip()[:20]
                    label = f"🏪 {store_num} — {chain} {street}"
                    buttons.append([InlineKeyboardButton(label, callback_data=f"select_store_{store_num}")])
                buttons.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")])
                
                await query.edit_message_text(
                    f"📍 *Stores in {city}* ({len(stores_in_city)} found)\n\nTap a store:",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
        elif data.startswith("prospect_detail_"):
            prospect_id = data.replace("prospect_detail_", "")
            await query.answer()
            
            rep_id = get_rep_id(update)
            data_obj = load_prospect_data()
            rep_data = data_obj["reps"][rep_id]
            prospect = rep_data["saved_prospects"].get(prospect_id, {})
            
            if not prospect:
                await query.edit_message_text("❌ Prospect not found.")
                return
            
            name = prospect.get('name', 'Unknown')
            address = prospect.get('address', '')
            phone = prospect.get('phone', '')
            email = prospect.get('email', '')
            score = prospect.get('score', 0)
            status = prospect.get('status', 'unknown')
            contact_person = prospect.get('contact_name', '')
            
            # Show prospect details with action options
            text = f"📌 *{name}*\n\n"
            text += f"📊 Score: {score}/100\n"
            
            if contact_person:
                text += f"👤 Contact: {contact_person}\n"
            if address:
                text += f"📍 {address}\n"
            if phone:
                text += f"📞 {phone}\n"
            if email:
                text += f"📧 {email}\n"
            
            text += f"\nStatus: *{status.title()}*\n\n"
            text += "_What would you like to do?_"
            
            buttons = [
                [InlineKeyboardButton("🛒 Add to Cart", callback_data=f"prospect_add_cart_{prospect_id}")],
                [InlineKeyboardButton("🔄 Follow Up", callback_data=f"update_status_{prospect_id}_follow-up")],
                [InlineKeyboardButton("✅ Closed Deal", callback_data=f"update_status_{prospect_id}_closed")],
                [InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_prospect_{prospect_id}")],
                [InlineKeyboardButton("⬅️ Back", callback_data="saved_prospects")],
            ]
            
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        elif data.startswith("update_status_"):
            parts = data.replace("update_status_", "").rsplit("_", 1)
            prospect_id = parts[0]
            new_status = parts[1]
            await query.answer()
            
            rep_id = get_rep_id(update)
            data_obj = load_prospect_data()
            rep_data = data_obj["reps"][rep_id]
            prospect = rep_data["saved_prospects"].get(prospect_id, {})
            
            if prospect:
                prospect['status'] = new_status
                save_prospect_data(data_obj)
                
                status_emoji = {"interested": "⭐", "follow-up": "🔄", "proposal": "📋", "closed": "✅"}
                status_text = new_status.replace("-", " ").title()
                
                # Show confirmation and collapse
                name = prospect.get('name', 'Unknown')
                confirm_text = f"✅ {name} · {status_emoji.get(new_status, '●')} {status_text}"
                buttons = [[InlineKeyboardButton("⬅️ Back", callback_data="saved_prospects")]]
                
                await query.edit_message_text(confirm_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        elif data.startswith("delete_prospect_"):
            prospect_id = data.replace("delete_prospect_", "")
            await query.answer()
            
            rep_id = get_rep_id(update)
            data_obj = load_prospect_data()
            rep_data = data_obj["reps"][rep_id]
            prospect = rep_data["saved_prospects"].get(prospect_id, {})
            
            if prospect:
                name = prospect.get('name', 'Unknown')
                
                # Show confirmation prompt
                text = f"🗑️ *Delete {name}?*\n\n_This action cannot be undone._"
                buttons = [
                    [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_{prospect_id}")],
                    [InlineKeyboardButton("❌ Cancel", callback_data=f"prospect_detail_{prospect_id}")],
                ]
                
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        elif data.startswith("confirm_delete_"):
            prospect_id = data.replace("confirm_delete_", "")
            await query.answer()
            
            rep_id = get_rep_id(update)
            data_obj = load_prospect_data()
            rep_data = data_obj["reps"][rep_id]
            
            if prospect_id in rep_data["saved_prospects"]:
                prospect_name = rep_data["saved_prospects"][prospect_id].get('name', 'Prospect')
                del rep_data["saved_prospects"][prospect_id]
                save_prospect_data(data_obj)
                
                # Show confirmation
                text = f"🗑️ *{prospect_name} deleted*"
                buttons = [[InlineKeyboardButton("📌 Back to Saved", callback_data="saved_prospects")]]
                
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.error(f"Callback error: {e}", exc_info=True)


# --- Audit Module Functions ---

def get_cycle_delivery_dates():
    """Return delivery dates for each cycle (use most recent past date)."""
    today = datetime.now()
    
    cycles = {
        'A': [7, 4, 7],      # Jan 7, Apr 7, Jul 7, Oct 7
        'B': [7, 5, 7],      # Feb 7, May 7, Aug 7, Nov 7
        'C': [7, 6, 7],      # Mar 7, Jun 7, Sep 7, Dec 7
    }
    
    def get_most_recent_past_date(cycle_letter):
        """Get the most recent past delivery date for a given cycle."""
        year = today.year
        
        if cycle_letter == 'A':
            months = [1, 4, 7, 10]  # Jan, Apr, Jul, Oct
        elif cycle_letter == 'B':
            months = [2, 5, 8, 11]  # Feb, May, Aug, Nov
        else:  # C
            months = [3, 6, 9, 12]  # Mar, Jun, Sep, Dec
        
        day = 7
        dates = [datetime(year, month, day) for month in months]
        
        # Get the most recent one <= today
        past_dates = [d for d in dates if d <= today]
        if past_dates:
            return max(past_dates)
        
        # If no past date this year, use last month of previous year
        last_month = months[-1]
        return datetime(year - 1, last_month, day)
    
    return get_most_recent_past_date

def get_next_delivery_date(cycle_letter):
    """Get the next delivery date for a given cycle."""
    today = datetime.now()
    year = today.year
    
    if cycle_letter == 'A':
        months = [1, 4, 7, 10]
    elif cycle_letter == 'B':
        months = [2, 5, 8, 11]
    else:  # C
        months = [3, 6, 9, 12]
    
    day = 7
    dates = [datetime(year, month, day) for month in months]
    
    # Get the next one >= today
    future_dates = [d for d in dates if d >= today]
    if future_dates:
        return min(future_dates)
    
    # If no future date this year, use first month of next year
    first_month = months[0]
    return datetime(year + 1, first_month, day)

def calculate_days_until_runout(current_rolls, usage_per_day=11.1):
    """Calculate how many days until inventory runs out."""
    if usage_per_day <= 0:
        return float('inf')
    return current_rolls / usage_per_day

async def send_audit_email(chat_id, store_num, rep_name, rep_id, delivery_date, 
                           starting_cases, current_cases, current_rolls, 
                           days_until_next, alert):
    """Send audit report email to Tyler."""
    try:
        # Calculate current inventory
        total_rolls = (current_cases * 50) + current_rolls
        days_runout = calculate_days_until_runout(total_rolls)
        
        email_body = f"""
📊 **STORE AUDIT REPORT**

**Store:** {store_num}
**Rep:** {rep_name} (ID: {rep_id})
**Audit Date:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

**Delivery Information:**
- Delivery Date: {delivery_date.strftime('%B %d, %Y')}
- Starting Cases: {starting_cases}

**Current Inventory:**
- Cases: {current_cases}
- Rolls: {current_rolls}
- Total Rolls: {total_rolls}

**Projection:**
- Days Until Runout: {days_runout:.1f}
- Days Until Next Delivery: {days_until_next}

{'⚠️ **ALERT:** Inventory will run out before next delivery cycle!' if alert else '✅ Inventory sufficient until next delivery'}

---
_Submitted via @IndoorMediaProspectBot_
"""
        
        # Use gog CLI to send email
        cmd = [
            'gog', 'gmail', 'send',
            '--to', 'tyler.vansant@indoormedia.com',
            '--subject', f'Audit Report - {store_num}',
            '--body', email_body
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            logger.info(f"✅ Audit email sent for {store_num}")
            return True
        else:
            logger.error(f"❌ Failed to send audit email: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"❌ Error sending audit email: {e}")
        return False

async def handle_testimonial_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the testimonial submission flow."""
    query = update.callback_query
    await query.answer()
    
    # Initialize testimonial form data
    context.user_data['testimonial_form'] = {
        'date': datetime.now().strftime('%m/%d/%Y'),
        'name': '',
        'business': '',
        'address': '',
        'phone': '',
        'coupons_frequency': '',
        'coupons_count': '',
        'ticket_price': '',
        'roi_rating': '',
        'duration': '',
        'renew': '',
        'recommend': '',
        'comments': '',
        'grocery_chain': '',
        'zone': '',
        'store_number': '',
        'coupon_image': None,
    }
    
    # Start with name
    context.user_data[AWAITING_TEST_NAME] = True
    await query.edit_message_text(
        "📝 *Submit Testimonial*\n\n"
        f"Today's date: *{context.user_data['testimonial_form']['date']}*\n\n"
        f"*Step 1:* What is your name?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data="main_menu")]])
    )


async def submit_testimonial_email(form_data: dict, coupon_image_path: str = None) -> bool:
    """Save testimonial form and generate filled PDF for the rep to download."""
    try:
        import json
        import shutil
        from datetime import datetime
        
        # Create submissions directory if it doesn't exist
        submissions_dir = "/Users/tylervansant/.openclaw/workspace/data/testimonial_submissions"
        os.makedirs(submissions_dir, exist_ok=True)
        
        # Create a unique submission folder
        submission_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        business_name = form_data.get('business', 'Unknown').replace(' ', '_')[:20]
        submission_folder = os.path.join(submissions_dir, f"{submission_id}_{business_name}")
        os.makedirs(submission_folder, exist_ok=True)
        
        # Save form data as JSON
        form_file = os.path.join(submission_folder, "form.json")
        with open(form_file, 'w') as f:
            json.dump(form_data, f, indent=2, default=str)
        
        # Copy coupon image if provided
        coupon_dest = None
        if coupon_image_path and os.path.exists(coupon_image_path):
            coupon_dest = os.path.join(submission_folder, "coupon.jpg")
            shutil.copy(coupon_image_path, coupon_dest)
        
        # Generate filled form as HTML and convert to PDF
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; margin: 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ color: #0066cc; margin: 0; }}
                .header p {{ margin: 5px 0; color: #666; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                td {{ padding: 12px; border: 1px solid #ddd; }}
                td:first-child {{ background-color: #f0f0f0; font-weight: bold; width: 35%; }}
                .section-header {{ background-color: #0066cc; color: white; font-weight: bold; padding: 12px; }}
                .comments {{ white-space: pre-wrap; word-wrap: break-word; }}
                .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #999; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📝 Testimonial Form</h1>
                <p>Register Tapes Unlimited — IndoorMedia</p>
                <p>Submitted: {form_data.get('date', '')}</p>
            </div>
            
            <table>
                <tr class="section-header"><td colspan="2">CONTACT INFORMATION</td></tr>
                <tr><td>Contact Name</td><td>{form_data.get('name', '')}</td></tr>
                <tr><td>Business Name</td><td>{form_data.get('business', '')}</td></tr>
                <tr><td>Address</td><td>{form_data.get('address', '')}</td></tr>
                <tr><td>Phone</td><td>{form_data.get('phone', '')}</td></tr>
            </table>
            
            <table>
                <tr class="section-header"><td colspan="2">STORE INFORMATION</td></tr>
                <tr><td>Grocery Chain</td><td>{form_data.get('grocery_chain', '')}</td></tr>
                <tr><td>Zone</td><td>{form_data.get('zone', '')}</td></tr>
                <tr><td>Store #</td><td>{form_data.get('store_number', '')}</td></tr>
            </table>
            
            <table>
                <tr class="section-header"><td colspan="2">PROGRAM PARTICIPATION</td></tr>
                <tr><td>Coupons per Week</td><td>{form_data.get('coupons_count', '')}</td></tr>
                <tr><td>Average Ticket Price</td><td>${form_data.get('ticket_price', '')}</td></tr>
                <tr><td>ROI Rating</td><td><strong>{form_data.get('roi_rating', '')}</strong></td></tr>
                <tr><td>Program Duration</td><td>{form_data.get('duration', '')}</td></tr>
            </table>
            
            <table>
                <tr class="section-header"><td colspan="2">FEEDBACK</td></tr>
                <tr><td>Would Renew?</td><td>{form_data.get('renew', '')}</td></tr>
                <tr><td>Would Recommend?</td><td>{form_data.get('recommend', '')}</td></tr>
                <tr><td style="vertical-align: top;">Comments</td><td class="comments">{form_data.get('comments', '(none)')}</td></tr>
            </table>
            
            <div class="footer">
                <p>Submitted via IndoorMediaProspectBot</p>
                <p>Archived at: {submission_folder}</p>
                <p>Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S PT')}</p>
            </div>
        </body>
        </html>
        """
        
        # Save HTML version
        html_file = os.path.join(submission_folder, "form_filled.html")
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        logger.info(f"✅ Testimonial submission saved: {submission_folder}")
        logger.info(f"   Business: {form_data.get('business')}")
        logger.info(f"   Rep: {form_data.get('name')}")
        logger.info(f"   ROI: {form_data.get('roi_rating')}")
        
        print(f"\n🎉 NEW TESTIMONIAL SUBMISSION: {submission_folder}\n")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error processing testimonial: {e}")
        return False


async def handle_audit_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the audit flow - prompt for store number."""
    query = update.callback_query
    await query.answer()
    
    context.user_data['audit_mode'] = True
    context.user_data[AWAITING_AUDIT_STORE] = True
    
    # Build audit menu with zone overview if shipping data available
    audit_msg = "🏪 *Audit a Store*\n\n"
    audit_msg += "Send a store number or zone code:\n\n"
    audit_msg += "_Store:_ `FME07Z-0236`\n"
    audit_msg += "_Zone:_ `07Z` or `07Y`\n"
    
    buttons = []
    if SHIPPING_DATA_AVAILABLE:
        audit_msg += "\n📊 *Quick Zone Reports:*"
        # Add zone buttons for quick access
        zone_buttons = []
        summaries = get_all_zones_summary()
        for zone, s in sorted(summaries.items()):
            o = len(s['overdue'])
            label = f"{zone} ({s['total_stores']}{'🔴' + str(o) if o else ''})"
            zone_buttons.append(InlineKeyboardButton(label, callback_data=f"audit_zone_{zone}"))
        # Arrange in rows of 3
        for i in range(0, len(zone_buttons), 3):
            buttons.append(zone_buttons[i:i+3])
    
    buttons.append([InlineKeyboardButton("⬅️ Cancel", callback_data="main_menu")])
    
    await query.edit_message_text(
        audit_msg,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_client_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of closed customers (completed deals), filtered by rep."""
    query = update.callback_query
    await query.answer()
    
    rep_id = get_rep_id(update)
    contract_name = get_contract_rep_name(rep_id)
    rep_name = get_rep_name(update)
    
    # Determine if this is a manager (sees all) or rep (sees own)
    registry = load_rep_registry()
    rep_info = registry.get(rep_id, {})
    is_manager = rep_info.get('role') == 'manager'
    
    # Load contracts (closed deals)
    contracts_file = WORKSPACE / "data" / "contracts.json"
    closed_customers = []
    
    try:
        if contracts_file.exists():
            with open(contracts_file) as f:
                contracts_data = json.load(f)
            
            contracts = contracts_data.get("contracts", [])
            
            for c in contracts:
                if isinstance(c, dict):
                    rep = c.get("sales_rep", "")
                    
                    # Filter: managers see all, reps see only their own
                    if is_manager or rep == contract_name or rep == rep_name:
                        closed_customers.append({
                            "business": c.get("business_name", "Unknown"),
                            "owner": c.get("contact_name", ""),
                            "amount": c.get("total_amount", 0),
                            "date": c.get("date", ""),
                            "rep": rep,
                            "email": c.get("contact_email", ""),
                            "phone": c.get("contact_phone", ""),
                            "address": c.get("address", ""),
                            "store": c.get("store_name", ""),
                            "store_number": c.get("store_number", ""),
                            "contract_number": c.get("contract_number", ""),
                        })
    except Exception as e:
        logger.warning(f"Error loading contracts: {e}")
    
    if not closed_customers:
        await query.edit_message_text(
            "👥 *My Customers*\n\n"
            "_(No closed deals yet)_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
        )
        return
    
    # Get upcoming calendar events
    try:
        cmd = ["/opt/homebrew/bin/gog", "calendar", "list", "--json"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            events = json.loads(result.stdout)
            if isinstance(events, dict):
                events = events.get("events", [])
            
            for event in events:
                if isinstance(event, dict):
                    title = event.get("summary", "")
                    start = event.get("start", {})
                    start_date = start.get("dateTime", start.get("date", ""))
                    
                    for customer in closed_customers:
                        biz = customer.get("business", "")
                        if biz and biz.lower() in title.lower():
                            customer["next_event"] = {"title": title, "date": start_date}
                            break
    except Exception as e:
        logger.warning(f"Could not fetch calendar: {e}")
    
    # Store customer list in context for detail views
    sorted_customers = sorted(closed_customers, key=lambda x: x.get("date", ""), reverse=True)
    context.user_data['customer_list'] = sorted_customers
    
    # Build message with summary
    total_revenue = sum(c.get("amount", 0) for c in closed_customers)
    title = "👥 *My Customers*" if not is_manager else "👥 *All Customers*"
    msg = f"{title}\n\n"
    msg += f"💰 Total Revenue: ${total_revenue:,.2f}\n"
    msg += f"📊 Deals: {len(closed_customers)}\n\n"
    msg += "Tap a customer to view details:"
    
    # Clickable customer buttons
    buttons = []
    for i, c in enumerate(sorted_customers[:15]):
        business = c.get('business', '?')
        amount = c.get('amount', 0)
        rep = c.get('rep', '')
        label = f"🏢 {business} — ${amount:,.0f}"
        if is_manager and rep:
            label += f" ({rep.split()[0]})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"customer_detail_{i}")])
    
    if len(sorted_customers) > 15:
        buttons.append([InlineKeyboardButton(f"📋 Show All ({len(sorted_customers)})", callback_data="client_list_all")])
    
    buttons.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")])
    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def show_client_list_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all customers (expanded list)."""
    query = update.callback_query
    await query.answer()
    
    # Get customer list from context
    sorted_customers = context.user_data.get('customer_list', [])
    
    if not sorted_customers:
        await query.edit_message_text(
            "👥 *My Customers*\n\n_(No closed deals yet)_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
        )
        return
    
    # Check if manager
    rep_id = get_rep_id(update)
    registry = load_rep_registry()
    rep_info = registry.get(rep_id, {})
    is_manager = rep_info.get('role') == 'manager'
    
    # Build message with all customers
    total_revenue = sum(c.get("amount", 0) for c in sorted_customers)
    title = "👥 *All Customers*" if is_manager else "👥 *My Customers*"
    msg = f"{title}\n\n"
    msg += f"💰 Total Revenue: ${total_revenue:,.2f}\n"
    msg += f"📊 Deals: {len(sorted_customers)}\n\n"
    msg += "*Complete List:*\n"
    
    # All customers as buttons (paginated in chunks of 20)
    buttons = []
    for i, c in enumerate(sorted_customers):
        business = c.get('business', '?')
        amount = c.get('amount', 0)
        rep = c.get('rep', '')
        label = f"🏢 {business} — ${amount:,.0f}"
        if is_manager and rep:
            label += f" ({rep.split()[0]})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"customer_detail_{i}")])
    
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="client_list")])
    buttons.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")])
    
    # Split into chunks if too many (Telegram limit is ~100 buttons)
    msg_chunks = []
    button_chunks = []
    chunk_size = 40
    
    for i in range(0, len(buttons) - 2, chunk_size):  # Leave room for nav buttons
        chunk = buttons[i:i+chunk_size]
        chunk.append([InlineKeyboardButton("⬅️ Back", callback_data="client_list")])
        chunk.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")])
        button_chunks.append(chunk)
    
    # Send first chunk
    if button_chunks:
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(button_chunks[0]))
    else:
        await query.edit_message_text(msg + "\n_(No customers to display)_", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]]))

async def handle_location_share(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle location sharing from rep to find nearest stores."""
    if not context.user_data.get('waiting_for_location'):
        return
    
    context.user_data['waiting_for_location'] = False
    
    location = update.message.location
    latitude = location.latitude
    longitude = location.longitude
    
    # Find nearest stores
    nearest = find_nearest_stores(latitude, longitude, limit=10)
    
    if not nearest:
        await update.message.reply_text(
            "❌ No stores found nearby. Please try a different location.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Check if user came from rates flow
    rates_mode = context.user_data.get('rates_mode', False)
    context.user_data['rates_mode'] = False  # Reset
    
    # Send back to callback-based UI with store list
    if rates_mode:
        text = "📍 *Stores Near You*\n\nTap a store to see rates:\n\n"
    else:
        text = "📍 *Stores Near You*\n\nSelect a store to get started:\n\n"
    
    buttons = []
    for store in nearest:
        # Format: Chain - Distance (Cycle, Cases) | City
        cycle = store.get('cycle', '?')
        cases = store.get('case_count', '?')
        if rates_mode:
            store_display = f"💰 {store['chain']} - {store['distance_miles']}mi | {store['city']}"
            buttons.append([InlineKeyboardButton(store_display, callback_data=f"action_rates_{store['store_num']}")])
        else:
            store_display = f"{store['chain']} - {store['distance_miles']}mi ({cycle} cycle, {cases} cases)"
            buttons.append([InlineKeyboardButton(store_display, callback_data=f"nearme_{store['store_num']}")])
    
    buttons.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")])
    
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def setup_bot_commands(app):
    """Set up bot commands for Telegram menu."""
    commands = [
        ("start", "🚀 Sales Command Center"),
        ("menu", "🎯 Main Menu"),
        ("rates", "💰 Store Rates & Pricing"),
        ("roi", "📈 ROI Calculator"),
        ("keyword", "💬 Search Testimonials"),
        ("help", "❓ How to Use"),
        ("reset", "🔄 Clear Search"),
    ]
    
    try:
        await app.bot.set_my_commands(commands)
        logger.info(f"✅ Bot commands set: {len(commands)} commands")
        
        # Set the blue menu button to show commands list
        await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        logger.info("✅ Blue menu button enabled")
    except Exception as e:
        logger.warning(f"⚠️ Could not set bot menu: {e}")


def main():
    """Start the bot."""
    logger.info("🎯 IndoorMediaProspectBot starting...")
    
    app = Application.builder().token(TOKEN).build()
    
    # Set up commands on startup
    app.post_init = setup_bot_commands
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("examples", examples))
    app.add_handler(CommandHandler("city", start))
    app.add_handler(CommandHandler("store", start))
    app.add_handler(CommandHandler("rates", rates_command))
    app.add_handler(CommandHandler("roi", roi_command))
    app.add_handler(CommandHandler("keyword", keyword_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("dashboard", dashboard))
    
    # --- Registration & Admin Handlers ---
    if REGISTRATION_SYSTEM_LOADED:
        logger.info("✅ Registration & Admin System loaded")
        app.add_handler(CommandHandler("admin", admin_command))
        app.add_handler(CallbackQueryHandler(handle_callback, pattern="^admin_"))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_registration_message), group=1)
    else:
        logger.warning("⚠️  Registration & Admin System not available")
    
    app.add_handler(CallbackQueryHandler(handle_button_callback))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location_share))
    
    # --- Counter Sign Workflow Handlers (Must come before generic photo handler) ---
    if COUNTER_SIGN_AVAILABLE:
        logger.info("✅ Counter Sign Workflow handlers loaded")
        try:
            from counter_sign_workflow import (
                handle_business_card_upload,
                handle_landing_page_input,
                handle_ad_image_upload,
                STATE_AWAITING_BUSINESS_CARD,
                STATE_AWAITING_LANDING_PAGE,
                STATE_AWAITING_AD_IMAGE,
            )
            # Photo upload (business card or ad image)
            async def handle_counter_sign_photo(update, context):
                state = context.user_data.get('_counter_sign_state')
                logger.info(f"Counter sign photo handler: state={state}")
                if state == STATE_AWAITING_BUSINESS_CARD:
                    logger.info("Routing to handle_business_card_upload")
                    await handle_business_card_upload(update, context)
                elif state == STATE_AWAITING_AD_IMAGE:
                    logger.info("Routing to handle_ad_image_upload")
                    await handle_ad_image_upload(update, context)
                elif state == STATE_AWAITING_LANDING_PAGE:
                    logger.info("In landing page state, rejecting photo")
                    await update.message.reply_text("⏳ Waiting for your **landing page URL**. Send a URL or type 'none'.")
                elif state == STATE_AWAITING_STORE_CHAIN:
                    logger.info("In store chain state, rejecting photo")
                    await update.message.reply_text("🏪 Please select a store chain from the options above.")
                else:
                    logger.info(f"No counter sign state, falling through to generic handler")
                    # No counter sign state, use generic photo handler
                    await handle_photo_upload(update, context)
            
            app.add_handler(MessageHandler(
                filters.PHOTO,
                handle_counter_sign_photo
            ), group=0)
            # Text input (landing page URL)
            async def handle_counter_sign_text(update, context):
                state = context.user_data.get('_counter_sign_state')
                logger.info(f"Counter sign text handler: state={state}, text={update.message.text[:50] if update.message.text else 'None'}")
                if state == 'awaiting_landing_page':
                    logger.info("Routing to handle_landing_page_input")
                    await handle_landing_page_input(update, context)
                elif state in ['awaiting_store_chain', 'awaiting_business_card', 'awaiting_ad_image']:
                    # In counter sign workflow but waiting for different input type
                    logger.info(f"In counter sign state but got text when expecting different input: {state}")
                    await update.message.reply_text("⏳ Waiting for an image. Please send a photo.")
                # If no counter sign state, let the normal text handler (group=3) process it
                # Don't call handle_store_query directly - that causes duplicate processing!
            
            app.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                handle_counter_sign_text
            ), group=0)
        except ImportError as e:
            logger.warning(f"Could not load counter sign handlers: {e}")
    
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_upload), group=2)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_store_query), group=3)
    
    logger.info("✅ IndoorMediaProspectBot ready. Polling for messages...")
    app.run_polling()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
        sys.exit(0)
