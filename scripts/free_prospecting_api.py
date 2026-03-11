#!/usr/bin/env python3
"""
Free Prospecting API - Nominatim + Overpass (no API keys required)
Fallback when Google Places fails, and primary for offline mode
"""

import requests
import logging
import time
from typing import Dict, List, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class FreeProspectingAPI:
    """Use Nominatim (OpenStreetMap) + Overpass for business discovery (free, no keys)."""
    
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    
    # Map business categories to Overpass query terms
    CATEGORY_QUERIES = {
        "restaurants": [
            'amenity="restaurant"',
            'amenity="cafe"',
            'amenity="fast_food"',
            'amenity="pizza"',
        ],
        "coffee": [
            'amenity="cafe"',
            'amenity="coffee"',
        ],
        "salons": [
            'shop="hairdresser"',
            'shop="beauty"',
        ],
        "gyms": [
            'leisure="fitness_centre"',
            'leisure="sports_centre"',
        ],
        "retail": [
            'shop="convenience"',
            'shop="supermarket"',
            'shop="general"',
        ],
        "auto": [
            'shop="car_repair"',
            'shop="car"',
            'amenity="car_wash"',
        ],
        "veterinary": [
            'amenity="veterinary"',
        ],
        "real_estate": [
            'office="real_estate"',
        ],
    }
    
    TIMEOUT = 10
    
    @staticmethod
    def get_store_coordinates(store_address: str) -> Optional[Dict]:
        """Get lat/lon for a store using Nominatim (OpenStreetMap)."""
        try:
            params = {
                "q": store_address,
                "format": "json",
                "limit": 1,
            }
            
            response = requests.get(
                FreeProspectingAPI.NOMINATIM_URL,
                params=params,
                timeout=FreeProspectingAPI.TIMEOUT,
                headers={"User-Agent": "IndoorMediaProspectBot/1.0"}
            )
            response.raise_for_status()
            
            data = response.json()
            if data:
                result = data[0]
                return {
                    "lat": float(result["lat"]),
                    "lon": float(result["lon"]),
                    "displayName": result.get("display_name", store_address)
                }
            return None
        except Exception as e:
            logger.warning(f"Nominatim lookup failed: {e}")
            return None
    
    @staticmethod
    def find_nearby_businesses(
        lat: float,
        lon: float,
        radius_m: int = 1609,  # 1 mile default
        category: str = "restaurants",
        limit: int = 10
    ) -> List[Dict]:
        """Find nearby businesses using Overpass API."""
        try:
            queries = FreeProspectingAPI.CATEGORY_QUERIES.get(category.lower(), [])
            if not queries:
                logger.warning(f"Unknown category: {category}")
                return []
            
            all_results = []
            
            for query_term in queries:
                # Overpass QL query for nearby amenities
                overpass_query = f"""
                [bbox:{lat - 0.015},{lon - 0.015},{lat + 0.015},{lon + 0.015}];
                (
                  node[{query_term}];
                  way[{query_term}];
                  relation[{query_term}];
                );
                out body geom;
                """
                
                try:
                    response = requests.post(
                        FreeProspectingAPI.OVERPASS_URL,
                        data=overpass_query,
                        timeout=FreeProspectingAPI.TIMEOUT,
                        headers={"User-Agent": "IndoorMediaProspectBot/1.0"}
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    if "elements" in data:
                        for element in data["elements"][:15]:  # Limit per query
                            tags = element.get("tags", {})
                            
                            # Get coordinates
                            if "lat" in element and "lon" in element:
                                elem_lat, elem_lon = element["lat"], element["lon"]
                            elif "center" in element:
                                elem_lat = element["center"]["lat"]
                                elem_lon = element["center"]["lon"]
                            else:
                                continue
                            
                            # Build prospect entry
                            prospect = {
                                "name": tags.get("name", "Unknown Business"),
                                "type": tags.get("amenity") or tags.get("shop", "Business"),
                                "address": tags.get("addr:full") or 
                                          f"{tags.get('addr:street', '')} {tags.get('addr:housenumber', '')}".strip() or
                                          "Address not available",
                                "phone": tags.get("phone"),
                                "website": tags.get("website"),
                                "lat": elem_lat,
                                "lon": elem_lon,
                                "distance_m": FreeProspectingAPI._haversine(lat, lon, elem_lat, elem_lon),
                                "source": "OpenStreetMap (Overpass)",
                            }
                            
                            if prospect["name"] and prospect["name"] != "Unknown Business":
                                all_results.append(prospect)
                
                except Exception as e:
                    logger.warning(f"Overpass query failed for {query_term}: {e}")
                    continue
                
                time.sleep(0.5)  # Rate limit: 0.5s between queries
            
            # Sort by distance and limit results
            all_results.sort(key=lambda x: x.get("distance_m", float("inf")))
            return all_results[:limit]
        
        except Exception as e:
            logger.error(f"Error finding nearby businesses: {e}")
            return []
    
    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two lat/lon points in meters."""
        from math import radians, cos, sin, asin, sqrt
        
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371000  # Radius of earth in meters
        return c * r
    
    @staticmethod
    def prospect_search(
        store_address: str,
        category: str = "restaurants",
        limit: int = 10,
        radius_m: int = 1609
    ) -> List[Dict]:
        """Full prospect search: address → coordinates → nearby businesses."""
        logger.info(f"🔍 Free API search: {category} near {store_address}")
        
        # Get store coordinates
        coords = FreeProspectingAPI.get_store_coordinates(store_address)
        if not coords:
            logger.warning(f"Could not geocode store: {store_address}")
            return []
        
        logger.info(f"✅ Found store: {coords['displayName']}")
        
        # Find nearby businesses
        prospects = FreeProspectingAPI.find_nearby_businesses(
            coords["lat"],
            coords["lon"],
            radius_m=radius_m,
            category=category,
            limit=limit
        )
        
        logger.info(f"✅ Found {len(prospects)} prospects using free API")
        return prospects


if __name__ == "__main__":
    # Test: Find restaurants near a store
    logging.basicConfig(level=logging.INFO)
    
    results = FreeProspectingAPI.prospect_search(
        "Safeway, Portland, OR 97214",
        category="restaurants",
        limit=5
    )
    
    print(f"\n✅ Found {len(results)} prospects:")
    for r in results:
        print(f"  • {r['name']} ({r.get('type', 'N/A')}) - {r.get('distance_m', 0):.0f}m away")
