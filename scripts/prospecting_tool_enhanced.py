#!/usr/bin/env python3
"""
"Find Today's Deal" - Enhanced Prospecting Tool
Phase 1+2: Google Places + Advertising Signal Detection (Greet Magazine)
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
import logging
from math import radians, cos, sin, asin, sqrt
import time

# Load environment variables from .env
try:
    from dotenv import load_dotenv
    workspace = Path(__file__).parent.parent
    load_dotenv(workspace / ".env", override=True)
    load_dotenv(workspace / ".env.local", override=True)
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

WORKSPACE = Path(__file__).parent.parent
DATA_DIR = WORKSPACE / "data" / "store-rates"
STORES_FILE = DATA_DIR / "stores.json"
GREET_CACHE = DATA_DIR / "greet_cache.json"


class ProspectingToolEnhanced:
    """Prospecting with advertising signal detection."""
    
    def __init__(self):
        """Initialize."""
        with open(STORES_FILE) as f:
            self.stores_list = json.load(f)
        self.stores = {s["StoreName"]: s for s in self.stores_list}
        
        # Try to load API key from environment, or from .env directly
        self.api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        
        if not self.api_key:
            # Fallback: read directly from .env file
            workspace = Path(__file__).parent.parent
            env_file = workspace / ".env"
            if env_file.exists():
                with open(env_file) as f:
                    for line in f:
                        if line.startswith("GOOGLE_PLACES_API_KEY="):
                            self.api_key = line.split("=", 1)[1].strip()
                            break
        
        if not self.api_key:
            raise ValueError("❌ GOOGLE_PLACES_API_KEY not found in .env or environment")
        
        # Load Greet cache if it exists
        self.greet_cache = self._load_greet_cache()
        
        # Import advertising signal checkers
        try:
            from greet_scraper import GreetScraper
            self.greet = GreetScraper()
        except:
            logger.warning("⚠️ Greet scraper not available")
            self.greet = None
        
        logger.info("✅ Prospecting tool enhanced (with advertising signals)")
    
    def _load_greet_cache(self) -> dict:
        """Load Greet Magazine cache."""
        if GREET_CACHE.exists():
            with open(GREET_CACHE) as f:
                return json.load(f)
        return {}
    
    def _save_greet_cache(self):
        """Save Greet Magazine cache."""
        with open(GREET_CACHE, 'w') as f:
            json.dump(self.greet_cache, f, indent=2)
    
    def get_store_info(self, store_num: str) -> Optional[Dict]:
        """Get store details."""
        store_num = store_num.upper()
        return self.stores.get(store_num)
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in miles."""
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return 3959 * c
    
    def query_google_places(self, latitude: float, longitude: float, radius_meters: int = 3219, category_filter: list = None, search_keyword: str = None) -> List[Dict]:
        """Query Google Places via direct HTTP (bypasses googlemaps library issues)."""
        import requests as http_requests
        
        results_by_place_id = {}
        base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        
        # Build search params
        params = {
            "location": f"{latitude},{longitude}",
            "radius": radius_meters,
            "key": self.api_key
        }
        
        # Use keyword for targeted search (don't combine type + keyword — Google returns 0)
        if search_keyword:
            params["keyword"] = search_keyword
        elif category_filter and len(category_filter) > 0:
            params["type"] = category_filter[0]
        
        try:
            # Main nearby search
            resp = http_requests.get(base_url, params=params, timeout=15)
            data = resp.json()
            
            status = data.get('status')
            if status == 'REQUEST_DENIED':
                error_msg = data.get('error_message', 'Unknown error')
                raise ValueError(f"❌ Google Places API Error: {error_msg}")
            
            places = data.get('results', [])
            logger.info(f"API queries_quota: 60")
            logger.info(f"Found {len(places)} businesses nearby")
            
            for place in places:
                place_id = place.get('place_id')
                if place_id and place_id not in results_by_place_id:
                    # Get phone number via Place Details API
                    phone = 'N/A'
                    website = 'N/A'
                    phone = 'N/A'
                    website = 'N/A'
                    opening_hours = None
                    try:
                        detail_params = {
                            "place_id": place_id,
                            "fields": "formatted_phone_number,website,opening_hours",
                            "key": self.api_key
                        }
                        detail_resp = http_requests.get(details_url, params=detail_params, timeout=10)
                        detail_data = detail_resp.json()
                        if detail_data.get('result'):
                            phone = detail_data['result'].get('formatted_phone_number', 'N/A')
                            website = detail_data['result'].get('website', 'N/A')
                            opening_hours = detail_data['result'].get('opening_hours', None)
                    except:
                        pass
                    
                    results_by_place_id[place_id] = {
                        'name': place.get('name'),
                        'address': place.get('vicinity'),
                        'lat': place.get('geometry', {}).get('location', {}).get('lat'),
                        'lng': place.get('geometry', {}).get('location', {}).get('lng'),
                        'rating': place.get('rating', 0),
                        'user_ratings_total': place.get('user_ratings_total', 0),
                        'types': place.get('types', []),
                        'place_id': place_id,
                        'phone': phone,
                        'website': website,
                        'business_status': place.get('business_status', 'OPERATIONAL'),
                        'opening_hours': opening_hours,
                    }
            
            time.sleep(0.3)
            
        except ValueError:
            raise  # Re-raise API key errors
        except Exception as e:
            logger.warning(f"⚠️ Error querying Google Places: {e}")
        
        return list(results_by_place_id.values())
    
    def check_advertising_signals(self, business_name: str, city: str) -> Dict:
        """Check if business is advertising (Greet Magazine, Facebook Ads, etc.)"""
        signals = {'business': business_name, 'found_advertising': False, 'boost': 0, 'sources': []}
        
        # Check Greet Magazine cache first
        cache_key = f"{business_name}|{city}".lower()
        if cache_key in self.greet_cache:
            if self.greet_cache[cache_key]:
                signals['found_advertising'] = True
                signals['boost'] = 40
                signals['sources'].append('Greet Magazine (cached)')
            return signals
        
        # Query Greet if available
        if self.greet:
            try:
                found = self.greet.search_greet_by_business_name(business_name, city, 'WA')
                self.greet_cache[cache_key] = found
                self._save_greet_cache()
                
                if found:
                    signals['found_advertising'] = True
                    signals['boost'] += 40
                    signals['sources'].append('Greet Magazine')
            except Exception as e:
                logger.warning(f"⚠️ Could not check Greet: {e}")
        
        # Check Facebook Ads (optional, may require API setup)
        try:
            from facebook_ads_checker import FacebookAdsChecker
            fb_checker = FacebookAdsChecker()
            fb_ads = fb_checker.search_business_ads(business_name, max_results=3)
            if fb_ads:
                signals['found_advertising'] = True
                signals['boost'] += 50  # +50 for Facebook ads (strong signal)
                signals['sources'].append(f"Facebook Ads ({len(fb_ads)} active)")
        except Exception as e:
            pass  # Facebook Ads check is optional
        
        if signals['boost'] > 0:
            signals['source'] = ', '.join(signals['sources'])
        
        return signals
    
    def score_prospect(self, business: Dict, store_lat: float, store_lon: float, city: str) -> Optional[Dict]:
        """Score prospect with advertising signals."""
        score = 0
        details = []
        
        # Distance (0-25 points)
        if business.get('lat') and business.get('lng'):
            distance = self.calculate_distance(store_lat, store_lon, business['lat'], business['lng'])
            if distance <= 2:
                distance_score = 25 * (1 - distance / 2)
                score += distance_score
                business['distance_miles'] = round(distance, 2)
                details.append(f"Distance: {business['distance_miles']} mi")
            else:
                return None
        
        # Rating (0-25 points)
        rating = business.get('rating', 0)
        if rating > 0:
            rating_score = min(25, (rating / 5.0) * 25)
            score += rating_score
            details.append(f"Rating: {rating}⭐ ({business.get('user_ratings_total', 0)} reviews)")
        
        # Review velocity (0-20 points)
        reviews = business.get('user_ratings_total', 0)
        if reviews > 50:
            review_score = min(20, (reviews / 200) * 20)
            score += review_score
            details.append(f"Active: {reviews} recent reviews")
        elif reviews > 20:
            score += 10
        
        # Business status (0-15 points)
        status = business.get('business_status', 'OPERATIONAL')
        if status == 'OPERATIONAL':
            score += 15
            details.append("Status: Open ✅")
        
        # Advertising signals (can accumulate: Greet +40, Facebook +50, max 90)
        ad_signals = self.check_advertising_signals(business['name'], city)
        if ad_signals['found_advertising']:
            score += min(90, ad_signals['boost'])  # Cap at 90 points total
            details.append(f"🎯 ADVERTISING: {ad_signals.get('source', 'Multiple channels')} ⭐⭐⭐")
        
        score = min(100, score)
        business['likelihood_score'] = round(score, 1)
        business['score_details'] = details
        business['advertising_signal'] = ad_signals
        
        return business
    
    def run_prospecting(self, store_num: str, limit: int = 10, category_keywords: list = None, search_keyword: str = None, exclude_terms: list = None) -> List[Dict]:
        """Run enhanced prospecting with optional category filtering."""
        store = self.get_store_info(store_num)
        if not store:
            logger.error(f"❌ Store {store_num} not found")
            return []
        
        if not store.get('latitude') or not store.get('longitude'):
            logger.error(f"❌ Store {store_num} not geocoded")
            return []
        
        logger.info(f"\n🔍 Prospecting for {store['GroceryChain']} | {store['City']}, {store['State']}")
        logger.info(f"📍 Location: {store['Address']}")
        logger.info(f"🌐 Coordinates: {store['latitude']:.4f}, {store['longitude']:.4f}")
        logger.info(f"\n⏳ Querying nearby businesses within 2 miles...")
        if category_keywords:
            logger.info(f"🏷️ Filter: {', '.join(category_keywords)}")
        logger.info(f"🔎 Scanning for advertising signals (Greet Magazine, etc.)...\n")
        
        # Query Google Places (with optional category filter and keyword)
        businesses = self.query_google_places(
            store['latitude'], 
            store['longitude'],
            category_filter=category_keywords,
            search_keyword=search_keyword
        )
        logger.info(f"Found {len(businesses)} businesses nearby")
        
        # Apply exclusion filter if provided
        if exclude_terms:
            before_count = len(businesses)
            businesses = [
                b for b in businesses
                if not any(term.lower() in b.get('name', '').lower() for term in exclude_terms)
            ]
            logger.info(f"Exclusion filter: {before_count} → {len(businesses)} (excluded: {exclude_terms})")
        
        # Score each prospect
        scored = []
        for business in businesses:
            scored_business = self.score_prospect(business, store['latitude'], store['longitude'], store['City'])
            if scored_business:
                scored.append(scored_business)
        
        if category_keywords:
            logger.info(f"Filtered by Google Places types: {category_keywords} ({len(scored)} results)")
        
        # Sort by likelihood score
        scored.sort(key=lambda x: x['likelihood_score'], reverse=True)
        
        return scored[:limit]

    def _matches_category(self, business: Dict, category_keywords: list) -> bool:
        """Check if a business matches any of the selected category keywords."""
        name = business.get('name', '').lower()
        types = business.get('types', [])
        
        # Keywords to match for each category
        keyword_mapping = {
            'real_estate': ['real estate', 'realty', 'realtor', 'property', 'broker'],
            'insurance': ['insurance', 'allstate', 'state farm', 'geico', 'progressive'],
            'financial': ['bank', 'credit union', 'financial', 'investment', 'wealth', 'advisor'],
            'accountant': ['accounting', 'cpa', 'accountant', 'bookkeeper', 'tax'],
            'lawyer': ['law', 'attorney', 'legal', 'counsel'],
            'photographer': ['photography', 'photographer', 'photo studio'],
            'mexican': ['mexican', 'taco', 'burrito', 'enchilada', 'tres tacos', 'el '],
            'pizza': ['pizza', 'pizzeria'],
            'cafe': ['cafe', 'coffee', 'espresso', 'latte', 'barista'],
            'sushi': ['sushi', 'japanese', 'ramen'],
            'fast_food': ['fast food', 'burger', 'mcdonald', 'burger king', 'subway', 'taco bell'],
            'steakhouse': ['steakhouse', 'steak', 'grill'],
            'italian': ['italian', 'pasta', 'pizzeria'],
            'restaurant': ['restaurant'],
            'oil_change': ['oil change', 'lube', 'jiffy lube'],
            'car_wash': ['car wash', 'washing station'],
            'auto_repair': ['auto repair', 'mechanic', 'garage'],
            'tire_shop': ['tire', 'tires'],
            'car_dealer': ['car dealer', 'auto dealer', 'toyota', 'honda', 'ford'],
            'transmission': ['transmission', 'transmission repair'],
            'hair_salon': ['hair', 'salon', 'barber', 'haircut'],
            'spa': ['spa', 'massage', 'wellness'],
            'gym': ['gym', 'fitness', 'health club'],
            'dentist': ['dentist', 'dental', 'orthodontist'],
            'optometrist': ['optometrist', 'eye care', 'glasses', 'vision'],
            'doctor': ['doctor', 'physician', 'medical', 'clinic'],
            'nail_salon': ['nail', 'nails'],
            'contractor': ['contractor', 'construction', 'builder'],
            'roofing': ['roofing', 'roof'],
            'landscaping': ['landscaping', 'landscape', 'yard'],
            'plumbing': ['plumbing', 'plumber'],
            'electrician': ['electrical', 'electrician'],
            'handyman': ['handyman', 'home repair'],
            'hvac': ['hvac', 'heating', 'cooling', 'air conditioning'],
            'window_installation': ['window', 'windows'],
            'clothing': ['clothing', 'apparel', 'boutique', 'store'],
            'electronics': ['electronics', 'best buy', 'tech store'],
            'grocery': ['grocery', 'supermarket'],
            'jewelry': ['jewelry', 'jeweler'],
            'furniture': ['furniture'],
            'bookstore': ['bookstore', 'books'],
            'shopping_mall': ['mall'],
            'shoe_store': ['shoe', 'shoes'],
            'convenience_store': ['convenience', '7-eleven', 'circle k'],
            'liquor_store': ['liquor', 'wine', 'beer'],
            'toy_store': ['toy', 'toys'],
            'flower_shop': ['flower', 'florist'],
            'gift_shop': ['gift', 'gifts'],
            'pet_store': ['pet', 'petco', 'pets'],
            'hardware_store': ['hardware', 'home depot', 'lowes'],
            'sporting_goods_store': ['sporting', 'sports', 'outdoor'],
            'laundry': ['laundry', 'laundromat', 'dry clean'],
            'dry_cleaning': ['dry clean', 'laundry'],
            'locksmith': ['locksmith', 'locks'],
            'electronics_repair': ['electronics repair', 'phone repair'],
            'appliance_repair': ['appliance repair'],
            'carpet_cleaning': ['carpet', 'cleaning'],
            'movie_theater': ['movie', 'theater', 'cinema'],
            'museum': ['museum'],
            'bowling_alley': ['bowling'],
            'amusement_park': ['amusement', 'park'],
            'night_club': ['night club', 'nightclub', 'club'],
            'bar_and_grill': ['bar', 'grill', 'lounge'],
        }
        
        # Check if any category keyword matches
        for keyword in category_keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in keyword_mapping:
                patterns = keyword_mapping[keyword_lower]
                for pattern in patterns:
                    if pattern in name:
                        return True
                    # Also check Google Places types
                    for place_type in types:
                        if pattern in place_type.lower():
                            return True
            else:
                # Direct keyword match if not in mapping
                if keyword_lower in name:
                    return True
                for place_type in types:
                    if keyword_lower in place_type.lower():
                        return True
        
        return False


def format_results_enhanced(store_info: Dict, prospects: List[Dict]) -> str:
    """Format results with advertising signals."""
    lines = [
        f"\n{'='*80}",
        f"🎯 TODAY'S DEALS | {store_info['GroceryChain']} — {store_info['City']}, {store_info['State']}",
        f"{'='*80}\n",
    ]
    
    for i, prospect in enumerate(prospects, 1):
        lines.append(f"{i}. 🎯 LIKELIHOOD: {prospect['likelihood_score']}/100")
        lines.append(f"   Business: {prospect['name']}")
        lines.append(f"   Address: {prospect['address']}")
        lines.append(f"   Phone: {prospect['phone']}")
        lines.append(f"   Distance: {prospect.get('distance_miles', 'N/A')} miles")
        for detail in prospect.get('score_details', []):
            lines.append(f"   ✓ {detail}")
        lines.append("")
    
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: prospecting_tool_enhanced.py <store_number> [limit]")
        print("Example: prospecting_tool_enhanced.py FME07Z-0236 10")
        sys.exit(1)
    
    store_num = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    try:
        tool = ProspectingToolEnhanced()
        store = tool.get_store_info(store_num)
        if not store:
            logger.error(f"❌ Store {store_num} not found")
            sys.exit(1)
        
        prospects = tool.run_prospecting(store_num, limit)
        
        if prospects:
            print(format_results_enhanced(store, prospects))
        else:
            print(f"❌ No prospects found")
    
    except KeyboardInterrupt:
        print("\n⏹️  Cancelled")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
