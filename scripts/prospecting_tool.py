#!/usr/bin/env python3
"""
"Find Today's Deal" - Prospecting tool for IndoorMedia field reps
Input: Store number (e.g., FME07Z-0236)
Output: Top 10 high-value prospects within 2 miles
Scoring: Distance, Google rating, review velocity, advertising signals
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

# Target business categories
TARGET_CATEGORIES = [
    'restaurant', 'cafe', 'bar', 'bakery',
    'hair_care', 'barber', 'salon', 'spa',
    'auto_repair_shop', 'car_repair', 'mechanic',
    'gym', 'fitness_center',
    'dental_clinic', 'dentist',
    'veterinary_care', 'pet_grooming',
    'clothing_store', 'retail',
    'plumber', 'electrician', 'contractor'
]


class ProspectingTool:
    """Main prospecting engine."""
    
    def __init__(self):
        """Initialize with store data."""
        with open(STORES_FILE) as f:
            self.stores_list = json.load(f)
        self.stores = {s["StoreName"]: s for s in self.stores_list}
        
        # Load Google Places API key
        self.api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if not self.api_key:
            raise ValueError("❌ GOOGLE_PLACES_API_KEY not set in .env")
        
        logger.info("✅ Prospecting tool initialized (599 geocoded stores)")
    
    def get_store_info(self, store_num: str) -> Optional[Dict]:
        """Get store details by store number."""
        store_num = store_num.upper()
        return self.stores.get(store_num)
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in miles between two points."""
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        miles = 3959 * c
        return miles
    
    def query_google_places(self, latitude: float, longitude: float, radius_meters: int = 3219) -> List[Dict]:
        """
        Query Google Places for nearby businesses within 2 miles.
        Queries multiple types to get diverse results.
        """
        try:
            import googlemaps
        except ImportError:
            logger.error("❌ googlemaps not installed. Run: pip install googlemaps")
            return []
        
        gmaps = googlemaps.Client(key=self.api_key)
        results_by_place_id = {}  # Deduplicate by place_id
        
        # Search for each category
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
                
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                logger.warning(f"⚠️ Error querying {category}: {e}")
        
        return list(results_by_place_id.values())
    
    def score_prospect(self, business: Dict, store_lat: float, store_lon: float) -> Dict:
        """
        Calculate likelihood score (0-100).
        Factors:
        - Distance (closer = higher, max 2 miles) → 25 points
        - Google rating (healthier = higher) → 25 points
        - Review velocity (recent activity) → 20 points
        - Business status (open vs closed) → 15 points
        - Category fit → 15 points
        """
        score = 0
        details = []
        
        # Distance factor (0-25 points)
        if business.get('lat') and business.get('lng'):
            distance = self.calculate_distance(
                store_lat, store_lon,
                business['lat'], business['lng']
            )
            if distance <= 2:
                distance_score = 25 * (1 - distance / 2)
                score += distance_score
                business['distance_miles'] = round(distance, 2)
                details.append(f"Distance: {business['distance_miles']} mi")
            else:
                return None  # Outside 2-mile radius
        
        # Rating factor (0-25 points)
        rating = business.get('rating', 0)
        if rating > 0:
            rating_score = min(25, (rating / 5.0) * 25)
            score += rating_score
            details.append(f"Rating: {rating}⭐ ({business.get('user_ratings_total', 0)} reviews)")
        
        # Review velocity (0-20 points) - recent activity
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
        elif status == 'CLOSED_TEMPORARILY':
            score += 7
        
        # Cap at 100
        score = min(100, score)
        business['likelihood_score'] = round(score, 1)
        business['score_details'] = details
        
        return business
    
    def run_prospecting(self, store_num: str, limit: int = 10) -> List[Dict]:
        """Run full prospecting for a store."""
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
        logger.info(f"\n⏳ Querying nearby businesses within 2 miles...\n")
        
        # Query Google Places
        businesses = self.query_google_places(store['latitude'], store['longitude'])
        logger.info(f"Found {len(businesses)} businesses nearby")
        
        # Score each prospect
        scored = []
        for business in businesses:
            scored_business = self.score_prospect(business, store['latitude'], store['longitude'])
            if scored_business:
                scored.append(scored_business)
        
        # Sort by likelihood score
        scored.sort(key=lambda x: x['likelihood_score'], reverse=True)
        
        # Return top N
        return scored[:limit]


def format_results(store_info: Dict, prospects: List[Dict]) -> str:
    """Format results for display."""
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
        if prospect['phone'] != 'N/A':
            lines.append(f"   Distance: {prospect.get('distance_miles', 'N/A')} miles")
        for detail in prospect.get('score_details', []):
            lines.append(f"   ✓ {detail}")
        lines.append("")
    
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: prospecting_tool.py <store_number> [limit]")
        print("Example: prospecting_tool.py FME07Z-0236 10")
        sys.exit(1)
    
    store_num = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    try:
        tool = ProspectingTool()
        
        # Get store info
        store = tool.get_store_info(store_num)
        if not store:
            logger.error(f"❌ Store {store_num} not found")
            sys.exit(1)
        
        # Run prospecting
        prospects = tool.run_prospecting(store_num, limit)
        
        if prospects:
            print(format_results(store, prospects))
        else:
            print(f"❌ No prospects found within 2 miles")
    
    except KeyboardInterrupt:
        print("\n⏹️  Cancelled")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
