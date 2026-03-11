#!/usr/bin/env python3
"""
Fallback prospects - generates sample prospects when APIs fail
Shows placeholder prospects so ProspectBot never fails completely
"""

import logging
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

FALLBACK_PROSPECTS = {
    "restaurants": [
        {"name": "The Rustic Table", "type": "restaurant", "address": "123 Main St", "phone": "(555) 123-4567"},
        {"name": "Fresh Flavors Cafe", "type": "restaurant", "address": "456 Oak Ave", "phone": "(555) 234-5678"},
        {"name": "Grill House Prime", "type": "restaurant", "address": "789 Pine Rd", "phone": "(555) 345-6789"},
        {"name": "The Garden Bistro", "type": "restaurant", "address": "321 Elm St", "phone": "(555) 456-7890"},
        {"name": "Coastal Kitchen", "type": "restaurant", "address": "654 Beach Way", "phone": "(555) 567-8901"},
    ],
    "salons": [
        {"name": "Elegant Cuts Hair Salon", "type": "salon", "address": "111 Beauty Lane", "phone": "(555) 111-1111"},
        {"name": "Glow Up Salon & Spa", "type": "salon", "address": "222 Style Ave", "phone": "(555) 222-2222"},
        {"name": "The Hair Company", "type": "salon", "address": "333 Fashion Rd", "phone": "(555) 333-3333"},
        {"name": "Luxe Nails & Hair", "type": "salon", "address": "444 Pamper Blvd", "phone": "(555) 444-4444"},
        {"name": "Studio Salon Professionals", "type": "salon", "address": "555 Glam St", "phone": "(555) 555-5555"},
    ],
    "gyms": [
        {"name": "FitLife Gym & Wellness", "type": "gym", "address": "100 Health Ave", "phone": "(555) 100-1001"},
        {"name": "Peak Performance Fitness", "type": "gym", "address": "200 Strength St", "phone": "(555) 200-2002"},
        {"name": "Core Fitness Studio", "type": "gym", "address": "300 Wellness Way", "phone": "(555) 300-3003"},
        {"name": "Iron Works Gym", "type": "gym", "address": "400 Power Blvd", "phone": "(555) 400-4004"},
        {"name": "BodyFlex Training Center", "type": "gym", "address": "500 Muscle Rd", "phone": "(555) 500-5005"},
    ],
    "coffee": [
        {"name": "Morning Brew Cafe", "type": "coffee", "address": "10 Coffee Ln", "phone": "(555) 600-6001"},
        {"name": "The Daily Roast", "type": "coffee", "address": "20 Espresso Ave", "phone": "(555) 600-6002"},
        {"name": "Brew Haven", "type": "coffee", "address": "30 Latte St", "phone": "(555) 600-6003"},
        {"name": "Cup of Joy Coffee", "type": "coffee", "address": "40 Cappuccino Rd", "phone": "(555) 600-6004"},
        {"name": "Artisan Roasters", "type": "coffee", "address": "50 Barista Way", "phone": "(555) 600-6005"},
    ],
    "retail": [
        {"name": "Local Goods Store", "type": "retail", "address": "1 Market Sq", "phone": "(555) 700-7001"},
        {"name": "The Corner Shop", "type": "retail", "address": "2 Commerce Ave", "phone": "(555) 700-7002"},
        {"name": "Community Market", "type": "retail", "address": "3 Trade St", "phone": "(555) 700-7003"},
        {"name": "Downtown Boutique", "type": "retail", "address": "4 Shopping Rd", "phone": "(555) 700-7004"},
        {"name": "Small Business Hub", "type": "retail", "address": "5 Enterprise Blvd", "phone": "(555) 700-7005"},
    ],
}

def get_fallback_prospects(category: str, limit: int = 10) -> List[Dict]:
    """Get fallback prospects for a category when all APIs fail."""
    category_lower = category.lower()
    
    if category_lower not in FALLBACK_PROSPECTS:
        # Return generic fallback
        category_lower = "restaurants"
    
    prospects = FALLBACK_PROSPECTS[category_lower][:limit]
    
    # Add required UI fields
    for i, p in enumerate(prospects):
        p["source"] = "sample"
        p["note"] = "Sample prospects (APIs unavailable)"
        p["distance_miles"] = round(0.3 + (i * 0.2), 2)  # Mock distances: 0.3, 0.5, 0.7, etc
        p["likelihood_score"] = 65 - (i * 5)  # Mock scores: 65, 60, 55, etc (declining)
        p["rating"] = None
        p["user_ratings_total"] = 0
        p["place_id"] = None
        p["opening_hours"] = {}
        p["website"] = None
        p["lat"] = None
        p["lon"] = None
    
    logger.warning(f"⚠️ Using fallback prospects for {category} ({len(prospects)} items)")
    return prospects
