#!/usr/bin/env python3
"""
Nearby Stores Finder
When a prospect books an appointment, finds nearby stores and generates
recommendations with pricing bundles.
"""

import json
import math
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NearbyStoresFinder:
    def __init__(self, stores_db_path: str = "data/store-rates/stores.json"):
        """Initialize with store database."""
        self.stores_db_path = stores_db_path
        self.stores = self._load_stores()
        self.geocode_cache = self._load_geocode_cache()

    def _load_stores(self) -> List[Dict]:
        """Load store database."""
        try:
            with open(self.stores_db_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load stores: {e}")
            return []

    def _load_geocode_cache(self) -> Dict:
        """Load cached coordinates for stores."""
        cache_path = "data/store-rates/geocode_cache.json"
        if Path(cache_path).exists():
            try:
                with open(cache_path, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_geocode_cache(self):
        """Save geocode cache."""
        cache_path = "data/store-rates/geocode_cache.json"
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(self.geocode_cache, f, indent=2)

    def _get_store_coordinates(self, store: Dict) -> Optional[Tuple[float, float]]:
        """
        Get latitude/longitude for a store.
        Uses cached values or approximates based on city/zip.
        """
        store_id = store.get("store_number")
        
        if store_id in self.geocode_cache:
            cached = self.geocode_cache[store_id]
            return (cached["lat"], cached["lon"])
        
        # Approximate coordinates based on major cities in CA/OR/WA
        city = store.get("city", "").lower()
        zip_code = store.get("zip", "")
        
        # City-based approximations (can be improved with real geocoding)
        city_coords = {
            "los angeles": (34.0522, -118.2437),
            "san francisco": (37.7749, -122.4194),
            "san diego": (32.7157, -117.1611),
            "sacramento": (38.5816, -121.4944),
            "fresno": (36.7469, -119.7726),
            "long beach": (33.7701, -118.1937),
            "oakland": (37.8044, -122.2712),
            "bakersfield": (35.3733, -119.0187),
            "portland": (45.5152, -122.6784),
            "salem": (44.9429, -123.0351),
            "eugene": (44.0521, -123.0868),
            "seattle": (47.6062, -122.3321),
            "spokane": (47.6587, -117.4260),
            "tacoma": (47.2529, -122.4443),
            "vancouver": (45.6872, -122.6151),
        }
        
        for city_name, coords in city_coords.items():
            if city_name in city:
                self.geocode_cache[store_id] = {"lat": coords[0], "lon": coords[1]}
                self._save_geocode_cache()
                return coords
        
        # Default fallback (Sacramento, CA center)
        return (38.5816, -121.4944)

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates in miles."""
        # Haversine formula
        R = 3959  # Earth radius in miles
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c

    def find_nearby_stores(
        self,
        prospect_lat: float,
        prospect_lon: float,
        max_distance: float = 3.0,
        limit: int = 10
    ) -> List[Dict]:
        """
        Find stores within max_distance miles of prospect location.
        Returns sorted by distance.
        """
        nearby = []
        
        for store in self.stores:
            store_coords = self._get_store_coordinates(store)
            if not store_coords:
                continue
            
            distance = self._calculate_distance(
                prospect_lat, prospect_lon,
                store_coords[0], store_coords[1]
            )
            
            if distance <= max_distance:
                nearby.append({
                    **store,
                    "distance": round(distance, 2),
                    "lat": store_coords[0],
                    "lon": store_coords[1]
                })
        
        # Sort by distance
        nearby.sort(key=lambda x: x["distance"])
        
        return nearby[:limit]

    def _calculate_payment_plan(self, base_price: float, plan: str) -> Dict:
        """Calculate payment plan pricing."""
        production_fee = 125.0
        
        plans = {
            "monthly": (base_price + production_fee) / 12,
            "3_month": ((base_price * 0.90) + production_fee) / 3,
            "6_month": ((base_price * 0.925) + production_fee) / 6,
            "paid_in_full": (base_price * 0.85) + production_fee,
        }
        
        return {
            "monthly": {
                "per_payment": round(plans["monthly"], 2),
                "total": round(plans["monthly"] * 12, 2),
                "display": f"${plans['monthly']:.0f}/mo × 12 = ${plans['monthly'] * 12:.0f}"
            },
            "3_month": {
                "per_payment": round(plans["3_month"], 2),
                "total": round(plans["3_month"] * 3, 2),
                "display": f"${plans['3_month']:.0f} × 3 = ${plans['3_month'] * 3:.0f} (10% off)"
            },
            "6_month": {
                "per_payment": round(plans["6_month"], 2),
                "total": round(plans["6_month"] * 6, 2),
                "display": f"${plans['6_month']:.0f} × 6 = ${plans['6_month'] * 6:.0f} (7.5% off)"
            },
            "paid_in_full": {
                "per_payment": round(plans["paid_in_full"], 2),
                "total": round(plans["paid_in_full"], 2),
                "display": f"${plans['paid_in_full']:.0f} (15% off)"
            }
        }[plan]

    def generate_recommendation_bundle(
        self,
        nearby_stores: List[Dict],
        ad_type: str = "single"
    ) -> Dict:
        """
        Generate pricing bundle for recommended nearby stores.
        Selects top 5 stores and calculates combined pricing.
        """
        if not nearby_stores:
            return {}
        
        # Select top 5 by distance
        recommended = nearby_stores[:5]
        
        # Calculate totals for each plan
        pricing_key = f"{ad_type}_ad_price"
        
        totals = {
            "monthly": 0,
            "3_month": 0,
            "6_month": 0,
            "paid_in_full": 0,
        }
        
        stores_pricing = []
        
        for store in recommended:
            base_price = store.get(pricing_key, 0)
            if not base_price:
                continue
            
            plans = self._calculate_payment_plan(base_price, "monthly")
            
            stores_pricing.append({
                "store_number": store.get("store_number"),
                "city": store.get("city"),
                "chain": store.get("chain"),
                "distance": store.get("distance"),
                "single_ad_price": store.get("single_ad_price"),
                "double_ad_price": store.get("double_ad_price"),
            })
            
            # Add to totals (using monthly as base for calculation)
            totals["monthly"] += plans["monthly"]
            totals["3_month"] += ((base_price * 0.90) + 125) / 3
            totals["6_month"] += ((base_price * 0.925) + 125) / 6
            totals["paid_in_full"] += (base_price * 0.85) + 125
        
        return {
            "recommended_stores": stores_pricing,
            "store_count": len(stores_pricing),
            "total_pricing": {
                "monthly": {
                    "per_payment": round(totals["monthly"], 2),
                    "total": round(totals["monthly"] * 12, 2),
                    "display": f"${totals['monthly']:.0f}/mo × 12 = ${totals['monthly'] * 12:.0f}"
                },
                "3_month": {
                    "per_payment": round(totals["3_month"], 2),
                    "total": round(totals["3_month"] * 3, 2),
                    "display": f"${totals['3_month']:.0f} × 3 = ${totals['3_month'] * 3:.0f}"
                },
                "6_month": {
                    "per_payment": round(totals["6_month"], 2),
                    "total": round(totals["6_month"] * 6, 2),
                    "display": f"${totals['6_month']:.0f} × 6 = ${totals['6_month'] * 6:.0f}"
                },
                "paid_in_full": {
                    "per_payment": round(totals["paid_in_full"], 2),
                    "total": round(totals["paid_in_full"], 2),
                    "display": f"${totals['paid_in_full']:.0f}"
                }
            }
        }

    def format_for_telegram(
        self,
        business_name: str,
        nearby_stores: List[Dict],
        bundle: Dict
    ) -> str:
        """Format nearby stores recommendation for Telegram."""
        if not nearby_stores:
            return f"❌ No nearby stores found for {business_name} in their location."
        
        msg = f"🗺️ <b>Nearby Store Opportunities</b>\n"
        msg += f"<b>{business_name}</b>\n\n"
        
        msg += f"📍 <b>Top Recommended Stores ({bundle['store_count']} stores within 3 miles)</b>\n"
        msg += "─" * 40 + "\n"
        
        for i, store in enumerate(bundle['recommended_stores'], 1):
            msg += f"{i}. <b>{store['chain']}</b> - {store['city']}\n"
            msg += f"   Distance: {store['distance']}mi\n"
            msg += f"   Single: ${store['single_ad_price']} | Double: ${store['double_ad_price']}\n\n"
        
        msg += "💰 <b>Total Package Pricing (5-Store Bundle)</b>\n"
        msg += "─" * 40 + "\n"
        msg += f"Monthly: {bundle['total_pricing']['monthly']['display']}\n"
        msg += f"3-Month: {bundle['total_pricing']['3_month']['display']}\n"
        msg += f"6-Month: {bundle['total_pricing']['6_month']['display']}\n"
        msg += f"Paid-in-Full: {bundle['total_pricing']['paid_in_full']['display']}\n\n"
        
        msg += "🎯 Ready to enter contracts? Open Mappoint to add this business to your map.\n"
        msg += "[🗺️ Open Mappoint](https://sales.indoormedia.com/Mappoint)"
        
        return msg


def main():
    """CLI interface for testing."""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python nearby_stores_finder.py <lat> <lon> [city]")
        return
    
    lat, lon = float(sys.argv[1]), float(sys.argv[2])
    finder = NearbyStoresFinder()
    
    nearby = finder.find_nearby_stores(lat, lon, max_distance=3.0, limit=10)
    bundle = finder.generate_recommendation_bundle(nearby)
    
    print(json.dumps(bundle, indent=2))


if __name__ == "__main__":
    main()
