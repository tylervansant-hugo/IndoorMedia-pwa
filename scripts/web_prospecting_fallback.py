#!/usr/bin/env python3
"""
Fallback Prospecting - Shows Nearby IndoorMedia Stores
When Places API fails, display other IndoorMedia stores in the area
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from math import radians, cos, sin, asin, sqrt

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

WORKSPACE = Path(__file__).parent.parent
DATA_DIR = WORKSPACE / "data" / "store-rates"
STORES_FILE = DATA_DIR / "stores.json"


class NearbyStoresFallback:
    """Show nearby IndoorMedia stores when Places API is unavailable."""
    
    def __init__(self):
        """Initialize."""
        with open(STORES_FILE) as f:
            self.stores_list = json.load(f)
        self.stores = {s["StoreName"]: s for s in self.stores_list}
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in miles between two lat/lon points."""
        if not all([lat1, lon1, lat2, lon2]):
            return None
        
        try:
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * asin(sqrt(a))
            r = 3959  # Earth radius in miles
            return c * r
        except:
            return None
    
    def find_nearby_stores(self, store_number: str, radius_miles: float = 2.0, limit: int = 10) -> List[Dict]:
        """Find other IndoorMedia stores within radius of given store."""
        
        store = self.stores.get(store_number)
        if not store:
            logger.error(f"❌ Store {store_number} not found")
            return []
        
        # Get center point coordinates
        try:
            center_lat = float(store.get('latitude', 0)) or float(store.get('Latitude', 0))
            center_lon = float(store.get('longitude', 0)) or float(store.get('Longitude', 0))
        except:
            logger.warning(f"⚠️ No coordinates for store {store_number}")
            return []
        
        if not center_lat or not center_lon:
            return []
        
        nearby = []
        
        # Calculate distance to all other stores
        for other_store in self.stores_list:
            if other_store.get("StoreName") == store_number:
                continue  # Skip the search store itself
            
            try:
                other_lat = float(other_store.get('latitude', 0)) or float(other_store.get('Latitude', 0))
                other_lon = float(other_store.get('longitude', 0)) or float(other_store.get('Longitude', 0))
                
                if not other_lat or not other_lon:
                    continue
                
                distance = self.haversine_distance(center_lat, center_lon, other_lat, other_lon)
                
                if distance and distance <= radius_miles:
                    nearby.append({
                        'name': f"{other_store.get('GroceryChain')} | {other_store.get('City')}, {other_store.get('State')}",
                        'address': other_store.get('Address', 'N/A'),
                        'phone': f"Store: {other_store.get('StoreName')}",  # Show store number instead
                        'distance_miles': round(distance, 1),
                        'likelihood_score': 100 - int(distance * 10),  # Higher score = closer
                        'store_number': other_store.get('StoreName'),
                        'advertising_signal': {'found_advertising': False},
                        'source': 'indoormedia_stores'
                    })
            except Exception as e:
                logger.warning(f"Error calculating distance: {e}")
                continue
        
        # Sort by distance (closest first)
        nearby.sort(key=lambda x: x['distance_miles'])
        
        logger.info(f"✅ Found {len(nearby)} nearby IndoorMedia stores within {radius_miles} miles")
        return nearby[:limit]
    
    def run_prospecting_fallback(self, store_number: str, limit: int = 10, 
                                 category_keywords: list = None, 
                                 search_keyword: str = None) -> List[Dict]:
        """Fallback: Show nearby IndoorMedia stores instead of external businesses."""
        
        logger.info(f"🏪 Fallback mode: Finding nearby IndoorMedia stores for {store_number}")
        
        nearby_stores = self.find_nearby_stores(store_number, radius_miles=2.0, limit=limit)
        
        if not nearby_stores:
            raise Exception("No nearby IndoorMedia stores found - Please contact support")
        
        return nearby_stores


if __name__ == "__main__":
    tool = WebProspectingFallback()
    prospects = tool.run_prospecting_fallback(
        'SAF07Y-0415',
        limit=5,
        category_keywords=['restaurant'],
        search_keyword='chinese'
    )
    
    for p in prospects[:3]:
        print(f"  ✓ {p.get('name')} - {p.get('url')}")
