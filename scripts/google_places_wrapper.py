#!/usr/bin/env python3
"""
Google Places API Wrapper - Safe integration with resilient prospecting
Handles API key, errors, rate limiting gracefully
"""

import os
import logging
import googlemaps
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class GooglePlacesWrapper:
    """Wrapper for Google Places API with error handling."""
    
    def __init__(self):
        """Initialize with API key from environment."""
        self.api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        self.client = None
        self.available = False
        
        if self.api_key:
            try:
                self.client = googlemaps.Client(key=self.api_key, timeout=10)
                self.available = True
                logger.info("✅ Google Places API initialized")
            except Exception as e:
                logger.warning(f"⚠️ Google Places API failed to initialize: {e}")
                self.available = False
        else:
            logger.info("ℹ️ GOOGLE_PLACES_API_KEY not set in environment")
    
    def search_nearby(
        self,
        latitude: float,
        longitude: float,
        keyword: str,
        radius: int = 1609,  # 1 mile
        limit: int = 10
    ) -> List[Dict]:
        """
        Search for nearby places using Google Places API.
        
        Returns list of prospects with name, address, phone, etc.
        """
        if not self.available or not self.client:
            logger.warning("Google Places API not available")
            return []
        
        try:
            logger.info(f"🔍 Google Places search: lat={latitude}, lon={longitude}, keyword='{keyword}'")
            
            results = self.client.places_nearby(
                location=(latitude, longitude),
                radius=radius,
                keyword=keyword,
                type="establishment"
            )
            
            logger.info(f"Results type: {type(results)}, value: {results is not None}")
            
            if not results or "results" not in results:
                logger.warning(f"No results from Google Places: {results}")
                return []
            
            results_list = results.get("results", [])
            if not results_list or results_list is None:
                logger.warning("Results list is empty or None")
                return []
            
            prospects = []
            for place in results_list[:limit]:
                # Calculate distance from store location
                import math
                place_lat = place.get("geometry", {}).get("location", {}).get("lat")
                place_lon = place.get("geometry", {}).get("location", {}).get("lng")
                
                distance_miles = None
                if place_lat and place_lon:
                    # Haversine formula
                    dlat = math.radians(place_lat - latitude)
                    dlon = math.radians(place_lon - longitude)
                    a = math.sin(dlat/2)**2 + math.cos(math.radians(latitude)) * math.cos(math.radians(place_lat)) * math.sin(dlon/2)**2
                    c = 2 * math.asin(math.sqrt(a))
                    distance_miles = round((6371 * c) * 0.621371, 2)  # Convert km to miles
                
                # Calculate likelihood score (0-100)
                rating = place.get("rating", 0)
                review_count = place.get("user_ratings_total", 0)
                is_open = place.get("opening_hours", {}).get("open_now", None)
                
                # Score formula:
                # - Rating (0-25): higher rating = higher score
                # - Reviews (0-25): more reviews = higher score
                # - Open status (0-10): open now = +10
                # - Proximity (0-40): closer = higher score
                score = 0
                if rating:
                    score += min(25, int(rating / 5 * 25))
                if review_count:
                    score += min(25, int(min(review_count / 10, 1) * 25))
                if is_open:
                    score += 10
                if distance_miles:
                    # Closer stores get higher proximity score
                    proximity_score = max(0, 40 - (distance_miles * 10))
                    score += proximity_score
                
                score = min(100, max(0, int(score)))
                
                prospect = {
                    "name": place.get("name", "Unknown"),
                    "type": ", ".join(place.get("types", [])),
                    "address": place.get("formatted_address") or place.get("vicinity", "Address not available"),
                    "lat": place_lat,
                    "lon": place_lon,
                    "distance_miles": distance_miles,
                    "likelihood_score": score,
                    "rating": place.get("rating"),
                    "user_ratings_total": place.get("user_ratings_total", 0),
                    "phone": place.get("formatted_phone_number"),
                    "website": place.get("website"),
                    "place_id": place.get("place_id"),
                    "opening_hours": place.get("opening_hours", {}),
                    "source": "Google Places"
                }
                prospects.append(prospect)
            
            logger.info(f"✅ Google Places found {len(prospects)} results")
            return prospects
        
        except googlemaps.exceptions.ApiError as e:
            logger.error(f"❌ Google Places API error: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return []


# Singleton instance
_wrapper = None

def get_google_places() -> GooglePlacesWrapper:
    """Get or create Google Places wrapper."""
    global _wrapper
    if _wrapper is None:
        _wrapper = GooglePlacesWrapper()
    return _wrapper


def search_google_places(
    address: str,
    category: str,
    limit: int = 10
) -> List[Dict]:
    """
    Convenience function: search for prospects using Google Places.
    
    First geocodes the address, then searches for nearby businesses.
    """
    from free_prospecting_api import FreeProspectingAPI
    
    wrapper = get_google_places()
    
    if not wrapper.available:
        logger.warning("Google Places not available, falling back to free API")
        return []
    
    # Geocode the address using free API (Nominatim)
    coords = FreeProspectingAPI.get_store_coordinates(address)
    if not coords:
        logger.warning(f"Could not geocode address: {address}")
        return []
    
    # Search with Google Places
    keyword_map = {
        "restaurants": "restaurant",
        "mexican": "mexican restaurant",
        "pizza": "pizza",
        "salons": "salon hair",
        "gyms": "gym fitness",
        "coffee": "coffee cafe",
        "auto": "auto repair car",
        "retail": "retail shop",
        "veterinary": "veterinary vet",
        "real_estate": "real estate",
    }
    
    category_lower = category.lower() if category else "restaurants"
    keyword = keyword_map.get(category_lower, category_lower if category_lower else "restaurant")
    
    if not keyword:
        logger.warning(f"No keyword found for category: {category}, using 'restaurant'")
        keyword = "restaurant"
    
    prospects = wrapper.search_nearby(
        coords["lat"],
        coords["lon"],
        keyword=keyword,
        limit=limit
    )
    
    return prospects


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    
    wrapper = get_google_places()
    print(f"API Available: {wrapper.available}")
    
    if wrapper.available:
        results = search_google_places(
            "Safeway, Portland, OR 97214",
            "restaurants",
            limit=5
        )
        
        print(f"\n✅ Found {len(results)} prospects:")
        for r in results:
            print(f"  • {r['name']} - {r.get('rating', 'N/A')} ⭐")
