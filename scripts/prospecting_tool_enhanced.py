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
        
        self.api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if not self.api_key:
            raise ValueError("❌ GOOGLE_PLACES_API_KEY not set in .env")
        
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
    
    def query_google_places(self, latitude: float, longitude: float, radius_meters: int = 3219) -> List[Dict]:
        """Query Google Places."""
        try:
            import googlemaps
        except ImportError:
            logger.error("❌ googlemaps not installed")
            return []
        
        gmaps = googlemaps.Client(key=self.api_key)
        results_by_place_id = {}
        
        for category in ['restaurant', 'salon', 'auto_repair_shop', 'gym', 'veterinary_care', 'shopping_mall']:
            try:
                places = gmaps.places_nearby(
                    location=(latitude, longitude),
                    radius=radius_meters,
                    type=category,
                    rank_by='prominence'
                )
                
                for place in places.get('results', []):
                    place_id = place.get('place_id')
                    if place_id not in results_by_place_id:
                        results_by_place_id[place_id] = {
                            'name': place.get('name'),
                            'address': place.get('vicinity'),
                            'lat': place.get('geometry', {}).get('location', {}).get('lat'),
                            'lng': place.get('geometry', {}).get('location', {}).get('lng'),
                            'rating': place.get('rating', 0),
                            'user_ratings_total': place.get('user_ratings_total', 0),
                            'types': place.get('types', []),
                            'place_id': place_id,
                            'phone': place.get('formatted_phone_number', 'N/A'),
                            'website': place.get('website', 'N/A'),
                            'business_status': place.get('business_status', 'OPERATIONAL'),
                        }
                
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"⚠️ Error querying {category}: {e}")
        
        return list(results_by_place_id.values())
    
    def check_advertising_signals(self, business_name: str, city: str) -> Dict:
        """Check if business is advertising (Greet Magazine, etc.)"""
        signals = {'business': business_name, 'found_advertising': False, 'boost': 0}
        
        # Check Greet Magazine cache first
        cache_key = f"{business_name}|{city}".lower()
        if cache_key in self.greet_cache:
            signals['found_advertising'] = self.greet_cache[cache_key]
            if signals['found_advertising']:
                signals['boost'] = 40  # +40 likelihood score
                signals['source'] = 'Greet Magazine (cached)'
            return signals
        
        # Query Greet if available
        if self.greet:
            try:
                found = self.greet.search_greet_by_business_name(business_name, city, 'WA')
                self.greet_cache[cache_key] = found
                self._save_greet_cache()
                
                if found:
                    signals['found_advertising'] = True
                    signals['boost'] = 40  # +40 likelihood score
                    signals['source'] = 'Greet Magazine'
            except Exception as e:
                logger.warning(f"⚠️ Could not check Greet: {e}")
        
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
        
        # Advertising signals (0-40 points)
        ad_signals = self.check_advertising_signals(business['name'], city)
        if ad_signals['found_advertising']:
            score += ad_signals['boost']
            details.append(f"🎯 Advertising: {ad_signals.get('source', 'Multiple channels')} ⭐⭐⭐")
        
        score = min(100, score)
        business['likelihood_score'] = round(score, 1)
        business['score_details'] = details
        business['advertising_signal'] = ad_signals
        
        return business
    
    def run_prospecting(self, store_num: str, limit: int = 10) -> List[Dict]:
        """Run enhanced prospecting."""
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
        logger.info(f"🔎 Scanning for advertising signals (Greet Magazine, etc.)...\n")
        
        # Query Google Places
        businesses = self.query_google_places(store['latitude'], store['longitude'])
        logger.info(f"Found {len(businesses)} businesses nearby")
        
        # Score each prospect
        scored = []
        for business in businesses:
            scored_business = self.score_prospect(business, store['latitude'], store['longitude'], store['City'])
            if scored_business:
                scored.append(scored_business)
        
        # Sort by likelihood score
        scored.sort(key=lambda x: x['likelihood_score'], reverse=True)
        
        return scored[:limit]


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
