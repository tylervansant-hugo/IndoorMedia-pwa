#!/usr/bin/env python3
"""
Refactored Testimonial Search System with Category-Specific Keyword Chains
Prevents cross-category contamination (e.g., dog grooming appearing for dental)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

WORKSPACE = Path(__file__).parent.parent
TESTIMONIALS_FILE = WORKSPACE / "data" / "testimonials_cache.json"

# ============================================================================
# CATEGORY FALLBACK KEYWORDS - Complete mapping for all business categories
# Each category has: primary keywords + fallback chain + strict exclusions
# ============================================================================

CATEGORY_FALLBACKS = {
    "🍽️ Restaurants": {
        "Mexican": {
            "primary": ["mexican", "taco", "burrito", "taqueria"],
            "fallbacks": ["mexican", "taco", "burrito", "taqueria", "restaurant", "food", "dining"],
            "exclude_categories": ["🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "mechanic", "car", "hair", "salon"]
        },
        "Pizza": {
            "primary": ["pizza", "pizzeria", "italian", "pasta"],
            "fallbacks": ["pizza", "pizzeria", "italian", "pasta", "restaurant", "dining"],
            "exclude_categories": ["🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "mechanic", "car", "hair"]
        },
        "Coffee/Café": {
            "primary": ["coffee", "cafe", "espresso", "roastery"],
            "fallbacks": ["coffee", "cafe", "espresso", "roastery", "barista", "drinks", "beverage", "tea"],
            "exclude_categories": ["🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "mechanic", "car", "hair", "salon"]
        },
        "Sushi/Japanese": {
            "primary": ["sushi", "japanese", "ramen", "teriyaki"],
            "fallbacks": ["sushi", "japanese", "ramen", "teriyaki", "asian", "restaurant", "dining"],
            "exclude_categories": ["🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "mechanic", "car", "hair"]
        },
        "Fast Food": {
            "primary": ["fast food", "burger", "sandwich", "quick lunch"],
            "fallbacks": ["fast food", "burger", "sandwich", "meal", "quick", "restaurant"],
            "exclude_categories": ["🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "mechanic", "car", "hair"]
        },
        "Chinese": {
            "primary": ["chinese", "dim sum", "noodles", "wok"],
            "fallbacks": ["chinese", "dim sum", "noodles", "wok", "asian", "restaurant"],
            "exclude_categories": ["🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "mechanic", "car", "hair"]
        },
        "Thai": {
            "primary": ["thai", "pad thai", "curry"],
            "fallbacks": ["thai", "pad thai", "curry", "asian", "restaurant"],
            "exclude_categories": ["🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "mechanic", "car", "hair"]
        },
        "Indian": {
            "primary": ["indian", "curry", "tandoori", "naan"],
            "fallbacks": ["indian", "curry", "tandoori", "naan", "restaurant"],
            "exclude_categories": ["🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "mechanic", "car", "hair"]
        },
        "BBQ/Steakhouse": {
            "primary": ["bbq", "steakhouse", "grill", "smokehouse", "steak"],
            "fallbacks": ["bbq", "steakhouse", "grill", "smokehouse", "steak", "restaurant"],
            "exclude_categories": ["🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "mechanic", "car", "hair"]
        },
        "Italian": {
            "primary": ["italian", "pasta", "risotto", "lasagna"],
            "fallbacks": ["italian", "pasta", "risotto", "lasagna", "restaurant"],
            "exclude_categories": ["🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "mechanic", "car", "hair"]
        },
        "Bakery": {
            "primary": ["bakery", "pastry", "bread", "cake"],
            "fallbacks": ["bakery", "pastry", "bread", "cake", "dessert"],
            "exclude_categories": ["🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "mechanic", "car", "hair"]
        },
        "Bar/Pub": {
            "primary": ["bar", "pub", "tavern", "brewery", "taproom"],
            "fallbacks": ["bar", "pub", "tavern", "brewery", "taproom", "drinks", "nightlife"],
            "exclude_categories": ["🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "mechanic", "car", "hair"]
        },
        "All Restaurants": {
            "primary": ["restaurant", "dining", "food"],
            "fallbacks": ["restaurant", "dining", "food", "meal"],
            "exclude_categories": ["🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "mechanic", "car", "hair", "salon"]
        }
    },
    
    "🚗 Automotive": {
        "Oil Change/Lube": {
            "primary": ["oil change", "lube", "quick lube", "synthetic oil"],
            "fallbacks": ["oil change", "lube", "quick lube", "synthetic", "maintenance", "auto"],
            "exclude_categories": ["🍽️ Restaurants", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "restaurant", "food", "hair", "salon"]
        },
        "Car Wash": {
            "primary": ["car wash", "detailing", "auto detail"],
            "fallbacks": ["car wash", "detailing", "auto detail", "wash", "cleaning"],
            "exclude_categories": ["🍽️ Restaurants", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "restaurant", "food", "hair"]
        },
        "Auto Repair": {
            "primary": ["auto repair", "mechanic", "garage", "repair"],
            "fallbacks": ["auto repair", "mechanic", "garage", "repair", "auto service", "maintenance"],
            "exclude_categories": ["🍽️ Restaurants", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "restaurant", "food", "hair", "salon"]
        },
        "Tires": {
            "primary": ["tire", "tires", "wheel alignment", "rotation"],
            "fallbacks": ["tire", "tires", "wheel", "alignment", "rotation", "balance"],
            "exclude_categories": ["🍽️ Restaurants", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "restaurant", "food", "hair"]
        },
        "Car Dealer": {
            "primary": ["car dealer", "dealership", "new car", "used car"],
            "fallbacks": ["car dealer", "dealership", "dealer", "auto sales"],
            "exclude_categories": ["🍽️ Restaurants", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "restaurant", "food", "hair"]
        },
        "Body Shop": {
            "primary": ["body shop", "collision", "paint", "auto body"],
            "fallbacks": ["body shop", "collision", "paint", "auto body", "repair"],
            "exclude_categories": ["🍽️ Restaurants", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "restaurant", "food", "hair"]
        },
        "Transmission": {
            "primary": ["transmission", "trans", "gearbox"],
            "fallbacks": ["transmission", "trans", "gearbox", "automatic", "manual"],
            "exclude_categories": ["🍽️ Restaurants", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "restaurant", "food", "hair"]
        }
    },
    
    "💄 Beauty & Wellness": {
        "Hair Salon": {
            "primary": ["hair salon", "salon", "haircut", "stylist"],
            "fallbacks": ["hair salon", "salon", "haircut", "stylist", "hair", "cut", "styling", "color"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "🏥 Health/Medical", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "restaurant", "food", "car", "mechanic"]
        },
        "Barber": {
            "primary": ["barber", "barbershop", "haircut"],
            "fallbacks": ["barber", "barbershop", "haircut", "men's haircut", "hair"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "🏥 Health/Medical", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "restaurant", "food", "car"]
        },
        "Nail Salon": {
            "primary": ["nail salon", "nails", "manicure", "pedicure"],
            "fallbacks": ["nail salon", "nails", "manicure", "pedicure", "nail art"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "🏥 Health/Medical", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "restaurant", "food", "car", "hair"]
        },
        "Spa/Massage": {
            "primary": ["spa", "massage", "day spa", "facial", "relaxation"],
            "fallbacks": ["spa", "massage", "day spa", "facial", "massage therapy", "wellness"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "🏥 Health/Medical", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "restaurant", "food", "car"]
        },
        "Gym/Fitness": {
            "primary": ["gym", "fitness", "fitness center", "workout"],
            "fallbacks": ["gym", "fitness", "fitness center", "workout", "health club", "training"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "🏥 Health/Medical", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "restaurant", "food", "car"]
        },
        "Yoga/Pilates": {
            "primary": ["yoga", "pilates", "yoga studio"],
            "fallbacks": ["yoga", "pilates", "yoga studio", "pilates studio", "fitness"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "🏥 Health/Medical", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "restaurant", "food", "car"]
        },
        "Tanning": {
            "primary": ["tanning", "tanning salon", "spray tan"],
            "fallbacks": ["tanning", "tanning salon", "spray tan", "tan"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "🏥 Health/Medical", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "grooming", "dog", "pet", "restaurant", "food", "car"]
        }
    },
    
    "🏥 Health/Medical": {
        "Dentist": {
            "primary": ["dentist", "dental", "orthodontics", "orthodontist"],
            "fallbacks": ["dentist", "dental", "orthodontics", "orthodontist", "denture", "implant", "teeth", "oral", "cavity", "crown"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["restaurant", "grooming", "dog", "pet", "car", "mechanic", "hair", "salon", "food"]
        },
        "Chiropractor": {
            "primary": ["chiropractor", "chiropractic", "spine", "alignment"],
            "fallbacks": ["chiropractor", "chiropractic", "spine", "alignment", "back pain"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["restaurant", "grooming", "dog", "pet", "car", "mechanic", "hair", "food"]
        },
        "Optometrist/Eyecare": {
            "primary": ["optometrist", "eye care", "vision", "glasses", "contacts"],
            "fallbacks": ["optometrist", "eye care", "vision", "glasses", "contacts", "eye doctor"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["restaurant", "grooming", "dog", "pet", "car", "mechanic", "hair", "food"]
        },
        "Physical Therapy": {
            "primary": ["physical therapy", "pt", "physical therapist", "rehab"],
            "fallbacks": ["physical therapy", "pt", "physical therapist", "rehabilitation", "rehab"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["restaurant", "grooming", "dog", "pet", "car", "mechanic", "hair", "food"]
        },
        "Urgent Care": {
            "primary": ["urgent care", "walk-in clinic", "clinic"],
            "fallbacks": ["urgent care", "walk-in clinic", "clinic", "medical care"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["restaurant", "grooming", "dog", "pet", "car", "mechanic", "hair", "food"]
        },
        "Veterinary": {
            "primary": ["veterinary", "vet", "animal hospital", "pet hospital"],
            "fallbacks": ["veterinary", "vet", "animal hospital", "pet hospital", "animal clinic"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "💄 Beauty & Wellness"],
            "exclude_keywords": ["restaurant", "car", "mechanic", "hair", "salon", "food", "dental"]
        }
    },
    
    "🏠 Pet Care": {
        "Dog Grooming": {
            "primary": ["dog grooming", "grooming", "dog groomer", "pet grooming"],
            "fallbacks": ["dog grooming", "grooming", "dog groomer", "pet grooming", "pet", "paws", "wash", "spa", "bathing", "dog"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness"],
            "exclude_keywords": ["dental", "restaurant", "food", "car", "mechanic", "hair salon", "nails", "eyecare"]
        },
        "Pet Boarding": {
            "primary": ["pet boarding", "boarding", "dog boarding", "boarding facility"],
            "fallbacks": ["pet boarding", "boarding", "dog boarding", "facility", "kennel"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness"],
            "exclude_keywords": ["dental", "restaurant", "food", "car", "mechanic", "hair", "salon"]
        },
        "Pet Supply": {
            "primary": ["pet supply", "pet store", "dog supplies"],
            "fallbacks": ["pet supply", "pet store", "dog supplies", "pet supplies"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness"],
            "exclude_keywords": ["dental", "restaurant", "food", "car", "mechanic", "hair", "salon"]
        },
        "Pet Training": {
            "primary": ["dog training", "pet training", "training", "obedience"],
            "fallbacks": ["dog training", "pet training", "training", "obedience", "puppy class"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness"],
            "exclude_keywords": ["dental", "restaurant", "food", "car", "mechanic", "hair", "salon"]
        }
    },
    
    "🏘️ Real Estate": {
        "Real Estate Agent": {
            "primary": ["real estate", "realtor", "real estate agent"],
            "fallbacks": ["real estate", "realtor", "real estate agent", "property", "agent"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["restaurant", "grooming", "dental", "car", "mechanic", "hair", "salon"]
        },
        "Property Management": {
            "primary": ["property management", "property manager", "landlord"],
            "fallbacks": ["property management", "property manager", "landlord", "management"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["restaurant", "grooming", "dental", "car", "mechanic", "hair"]
        }
    },
    
    "🔧 Home Services": {
        "Plumbing": {
            "primary": ["plumbing", "plumber", "pipes", "drain", "water"],
            "fallbacks": ["plumbing", "plumber", "pipes", "drain", "water", "bathroom", "fixtures", "installation"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "restaurant", "grooming", "dog", "car", "mechanic", "hair", "salon"]
        },
        "Electrical": {
            "primary": ["electrical", "electrician", "electric"],
            "fallbacks": ["electrical", "electrician", "electric", "wiring", "installation"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "restaurant", "grooming", "dog", "car", "mechanic", "hair"]
        },
        "HVAC": {
            "primary": ["hvac", "heating", "air conditioning", "hvac service"],
            "fallbacks": ["hvac", "heating", "air conditioning", "hvac service", "furnace", "ac"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "restaurant", "grooming", "dog", "car", "mechanic", "hair"]
        },
        "General Contractor": {
            "primary": ["contractor", "general contractor", "construction", "builder"],
            "fallbacks": ["contractor", "general contractor", "construction", "builder", "remodel"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "restaurant", "grooming", "dog", "car", "mechanic", "hair"]
        },
        "Cleaning Service": {
            "primary": ["cleaning", "house cleaning", "janitorial"],
            "fallbacks": ["cleaning", "house cleaning", "janitorial", "maid service", "clean"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "restaurant", "grooming", "dog", "car", "mechanic", "hair"]
        }
    },
    
    "📚 Services": {
        "Photography": {
            "primary": ["photography", "photographer", "photo"],
            "fallbacks": ["photography", "photographer", "photo", "portrait", "photos"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "restaurant", "grooming", "dog", "car", "mechanic", "hair"]
        },
        "Accounting/Tax": {
            "primary": ["accounting", "tax", "cpa", "accountant"],
            "fallbacks": ["accounting", "tax", "cpa", "accountant", "bookkeeping"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "restaurant", "grooming", "dog", "car", "mechanic", "hair"]
        },
        "Legal": {
            "primary": ["law", "attorney", "lawyer", "legal"],
            "fallbacks": ["law", "attorney", "lawyer", "legal", "law firm"],
            "exclude_categories": ["🍽️ Restaurants", "🚗 Automotive", "🏥 Health/Medical", "💄 Beauty & Wellness", "🏠 Pet Care"],
            "exclude_keywords": ["dental", "restaurant", "grooming", "dog", "car", "mechanic", "hair"]
        }
    }
}


# ============================================================================
# KEYWORD EXTRACTION - Extract primary business type from business name
# ============================================================================

BUSINESS_TYPE_KEYWORDS = {
    # Dental
    "dental": ["dental", "dentist", "orthodontics", "orthodontist", "denture", "implant", "ortho"],
    
    # Dog/Pet Grooming
    "dog grooming": ["grooming", "dog", "groomer", "paws", "ruff", "spa", "wash", "pet grooming", "pet spa"],
    
    # Plumbing
    "plumbing": ["plumbing", "plumber", "pipes", "drain", "water"],
    
    # Hair Salon
    "hair salon": ["salon", "hair", "haircut", "stylist", "barber", "barbershop"],
    
    # Coffee
    "coffee": ["coffee", "cafe", "espresso", "roastery", "barista"],
    
    # Restaurant
    "restaurant": ["restaurant", "cafe", "diner", "pizza", "sushi", "ramen"],
    
    # Auto/Car
    "auto": ["auto", "car", "mechanic", "garage", "repair", "wash"],
    
    # Real Estate
    "real estate": ["realtor", "realty", "property", "real estate"],
}


def extract_business_keyword(business_name: str) -> str:
    """
    Extract primary business keyword from prospect name.
    
    Examples:
    - "Mountain View Dental" → "dental"
    - "The Fluffy Ruff Dog Spa" → "dog grooming"
    - "Joe's Plumbing" → "plumbing"
    - "Sunrise Salon" → "hair salon"
    
    Returns the matched keyword or the last word if no match found.
    """
    if not business_name:
        return ""
    
    business_lower = business_name.lower()
    
    # Remove common articles/words
    words = business_lower.split()
    filtered_words = [
        w.rstrip("'s") for w in words 
        if w.lower() not in ('the', 'a', 'an', 'and', '&', "'s")
    ]
    
    # Check for multi-word matches first (e.g., "dog grooming", "hair salon")
    for keyword_group, keywords in BUSINESS_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in business_lower:
                return keyword_group.split()[0]  # Return first word of keyword group
    
    # Fallback to last word
    return filtered_words[-1] if filtered_words else business_name


def get_category_fallback_keywords(category: str, subcategory: str) -> List[str]:
    """
    Get the complete keyword chain (primary + fallbacks) for a category.
    
    Args:
        category: e.g., "🍽️ Restaurants"
        subcategory: e.g., "Mexican" or "Dentist"
    
    Returns:
        List of keywords in order of priority: [primary, fallback1, fallback2, ...]
    
    Example:
        get_category_fallback_keywords("🏥 Health/Medical", "Dentist")
        → ["dentist", "dental", "orthodontics", "orthodontist", "denture", ...]
    """
    if category not in CATEGORY_FALLBACKS:
        logger.warning(f"Category '{category}' not found in CATEGORY_FALLBACKS")
        return []
    
    if subcategory not in CATEGORY_FALLBACKS[category]:
        logger.warning(f"Subcategory '{subcategory}' not found under '{category}'")
        return []
    
    config = CATEGORY_FALLBACKS[category][subcategory]
    
    # Combine primary + fallbacks, removing duplicates while preserving order
    all_keywords = config.get("primary", []) + config.get("fallbacks", [])
    seen = set()
    unique_keywords = []
    for kw in all_keywords:
        if kw.lower() not in seen:
            seen.add(kw.lower())
            unique_keywords.append(kw)
    
    return unique_keywords


def get_exclusion_keywords(category: str, subcategory: str) -> Tuple[List[str], List[str]]:
    """
    Get exclusion lists for a category.
    
    Returns:
        (exclude_keywords, exclude_categories) tuple
    
    Exclusion keywords are words that should never match (e.g., "dental" never appears in dog grooming results)
    """
    if category not in CATEGORY_FALLBACKS or subcategory not in CATEGORY_FALLBACKS[category]:
        return [], []
    
    config = CATEGORY_FALLBACKS[category][subcategory]
    return config.get("exclude_keywords", []), config.get("exclude_categories", [])


# ============================================================================
# TESTIMONIAL SEARCH - Category-aware search with fallback chains
# ============================================================================

def load_testimonials_from_cache() -> List[Dict]:
    """Load testimonials from cache file."""
    if not TESTIMONIALS_FILE.exists():
        logger.warning(f"Testimonials cache not found at {TESTIMONIALS_FILE}")
        return []
    
    try:
        with open(TESTIMONIALS_FILE) as f:
            testimonials = json.load(f)
            if not isinstance(testimonials, list):
                logger.warning(f"Testimonials file contains {type(testimonials)}, expected list")
                return []
            return testimonials
    except Exception as e:
        logger.error(f"Error loading testimonials: {e}")
        return []


def search_testimonials_by_keyword(keyword: str, testimonials: List[Dict]) -> List[Dict]:
    """
    Search testimonials for a specific keyword.
    
    Args:
        keyword: Search term (e.g., "dental", "grooming")
        testimonials: List of testimonial dicts with 'searchable' field
    
    Returns:
        List of matching testimonials
    """
    if not keyword or not testimonials:
        return []
    
    keyword_lower = keyword.lower().strip()
    results = []
    seen_ids = set()
    
    for t in testimonials:
        t_id = t.get('id', '')
        if t_id in seen_ids:
            continue
        
        # Search in multiple fields for robustness
        searchable = t.get('searchable', '').lower()
        business = t.get('business', '').lower()
        comment = t.get('comment', '').lower()
        
        # Check if keyword appears in any searchable field
        if keyword_lower in searchable or keyword_lower in business or keyword_lower in comment:
            results.append(t)
            seen_ids.add(t_id)
    
    return results


def search_testimonials_by_category(
    category: str,
    subcategory: str,
    testimonials: List[Dict],
    limit: int = 3
) -> List[Dict]:
    """
    Search testimonials for a category with fallback chain.
    
    Respects category boundaries - NEVER crosses into exclusion categories.
    
    Args:
        category: e.g., "🏥 Health/Medical"
        subcategory: e.g., "Dentist"
        testimonials: Full testimonials list
        limit: Max results to return
    
    Returns:
        Up to `limit` testimonials for this category only
    """
    # Get keyword chain
    keywords = get_category_fallback_keywords(category, subcategory)
    exclude_keywords, exclude_categories = get_exclusion_keywords(category, subcategory)
    
    if not keywords:
        logger.warning(f"No keywords for {category}/{subcategory}")
        return []
    
    logger.info(f"Searching {category}/{subcategory} with keywords: {keywords}")
    
    results = []
    
    # Try each keyword in order until we have enough results
    for keyword in keywords:
        if len(results) >= limit:
            break
        
        matches = search_testimonials_by_keyword(keyword, testimonials)
        
        # Filter out exclusions and duplicates
        for match in matches:
            if len(results) >= limit:
                break
            
            match_id = match.get('id', '')
            existing_ids = {r.get('id', '') for r in results}
            
            if match_id in existing_ids:
                continue  # Already have this result
            
            # Check exclusion keywords
            searchable = match.get('searchable', '').lower()
            business = match.get('business', '').lower()
            
            # CRITICAL: Don't include if any exclusion keyword matches
            should_exclude = False
            for exclude_kw in exclude_keywords:
                if exclude_kw.lower() in searchable or exclude_kw.lower() in business:
                    logger.debug(f"Excluding {match.get('business')} due to exclusion keyword '{exclude_kw}'")
                    should_exclude = True
                    break
            
            if not should_exclude:
                results.append(match)
                logger.debug(f"Added: {match.get('business')} (keyword: {keyword})")
    
    logger.info(f"Found {len(results)} testimonials for {category}/{subcategory}")
    return results[:limit]


def get_testimonials_for_prospect(
    prospect: Dict,
    category: str,
    subcategory: str,
    testimonials: Optional[List[Dict]] = None,
    limit: int = 3
) -> List[Dict]:
    """
    Get relevant testimonials for a prospect.
    
    NEW SIGNATURE: Takes category + subcategory explicitly
    
    Args:
        prospect: Prospect dict with 'name' field
        category: Prospect's category (e.g., "🏥 Health/Medical")
        subcategory: Prospect's subcategory (e.g., "Dentist")
        testimonials: Optional cached testimonials list (loads from file if not provided)
        limit: Max results to return (default 3)
    
    Returns:
        List of up to `limit` testimonials
    
    Example:
        prospect = {"name": "Mountain View Dental", ...}
        results = get_testimonials_for_prospect(prospect, "🏥 Health/Medical", "Dentist")
        # Returns dental-only testimonials, never grooming/plumbing/etc.
    """
    # Load testimonials if not provided
    if testimonials is None:
        testimonials = load_testimonials_from_cache()
    
    if not testimonials:
        logger.warning("No testimonials available")
        return []
    
    # Validate category exists
    if category not in CATEGORY_FALLBACKS:
        logger.warning(f"Unknown category: {category}")
        return []
    
    if subcategory not in CATEGORY_FALLBACKS[category]:
        logger.warning(f"Unknown subcategory: {subcategory} under {category}")
        return []
    
    # Use category-specific search with fallback chain
    results = search_testimonials_by_category(category, subcategory, testimonials, limit)
    
    return results


# ============================================================================
# CONVENIENCE FUNCTION - For backward compatibility
# ============================================================================

def get_testimonials_simple(
    business_name: str,
    category: str,
    testimonials: Optional[List[Dict]] = None,
    limit: int = 3
) -> List[Dict]:
    """
    Simplified interface: Get testimonials by business name and category name.
    
    Attempts to infer subcategory from business name.
    
    Example:
        results = get_testimonials_simple(
            "Mountain View Dental",
            "🏥 Health/Medical"
        )
    """
    if testimonials is None:
        testimonials = load_testimonials_from_cache()
    
    if not testimonials:
        return []
    
    # Try to infer subcategory from business name
    business_keyword = extract_business_keyword(business_name)
    
    # Match against known subcategories
    if category in CATEGORY_FALLBACKS:
        for subcategory in CATEGORY_FALLBACKS[category].keys():
            keywords = get_category_fallback_keywords(category, subcategory)
            if business_keyword.lower() in [kw.lower() for kw in keywords]:
                return get_testimonials_for_prospect(
                    {"name": business_name},
                    category,
                    subcategory,
                    testimonials,
                    limit
                )
    
    # Fallback: return empty rather than wrong category
    logger.warning(f"Could not match {business_name} to a subcategory in {category}")
    return []
