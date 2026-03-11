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
            results = self.client.places_nearby(
                location=(latitude, longitude),
                radius=radius,
                keyword=keyword,
                type="establishment"
            )
            
            if not results or "results" not in results:
                return []
            
            prospects = []
            for place in results.get("results", [])[:limit]:
                prospect = {
                    "name": place.get("name", "Unknown"),
                    "type": ", ".join(place.get("types", [])),
                    "address": place.get("vicinity", "Address not available"),
                    "lat": place.get("geometry", {}).get("location", {}).get("lat"),
                    "lon": place.get("geometry", {}).get("location", {}).get("lng"),
                    "rating": place.get("rating"),
                    "phone": place.get("formatted_phone_number"),
                    "website": place.get("website"),
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
        "salons": "salon hair",
        "gyms": "gym fitness",
        "coffee": "coffee cafe",
        "auto": "auto repair car",
        "retail": "retail shop",
        "veterinary": "veterinary vet",
        "real_estate": "real estate",
    }
    
    keyword = keyword_map.get(category.lower(), category)
    
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
