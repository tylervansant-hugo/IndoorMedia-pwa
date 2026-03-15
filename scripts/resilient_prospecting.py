#!/usr/bin/env python3
"""
Resilient Prospecting Engine
Combines: Cache → Google Places → Free API → Cached Fallback
Handles failures gracefully without showing errors to users
"""

import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Import our components
import sys
from pathlib import Path
scripts_dir = str(Path(__file__).parent)
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

try:
    from prospecting_cache import get_cache
    CACHE_AVAILABLE = True
except Exception as e:
    CACHE_AVAILABLE = False
    logger.warning(f"Cache module not available: {e}")

try:
    from free_prospecting_api import FreeProspectingAPI
    FREE_API_AVAILABLE = True
except Exception as e:
    FREE_API_AVAILABLE = False
    logger.warning(f"Free API module not available: {e}")

# Fallback prospects disabled per Tyler's request - Mar 15, 2026
FALLBACK_AVAILABLE = False
get_fallback_prospects = None


class ResilientProspectingEngine:
    """Smart prospecting with fallbacks and caching."""
    
    def __init__(self):
        """Initialize engine."""
        self.cache = get_cache() if CACHE_AVAILABLE else None
        self.free_api = FreeProspectingAPI if FREE_API_AVAILABLE else None
        self.fallback_available = FALLBACK_AVAILABLE
    
    def search_prospects(
        self,
        store_number: str,
        store_address: str,
        category: str,
        google_places_func=None,  # Caller can pass their Google Places function
        limit: int = 10,
        force_refresh: bool = False
    ) -> tuple[List[Dict], str]:
        """
        Search for prospects with intelligent fallback strategy.
        
        Returns: (prospects, source_info)
        Examples of source_info:
          "✅ Cache hit (24h fresh)"
          "✅ Google Places API"
          "⚠️ Free API (Google Places unavailable)"
          "📦 Offline cache (APIs unavailable)"
        """
        
        logger.info(f"🔍 Prospect search: {store_number} → {category}")
        
        # Step 1: Check circuit breaker (if APIs are failing)
        if self.cache:
            cb_status = self.cache.get_circuit_breaker_status()
            if cb_status.get("status") == "open":
                logger.warning("🔴 Circuit breaker OPEN - using cached fallback")
                return self._get_cached_fallback(store_number, category, limit)
        
        # Step 2: Try cache first (unless force_refresh)
        if not force_refresh and self.cache:
            cached = self.cache.get_cached_prospects(store_number, category)
            if cached:
                return cached[:limit], "✅ Cache hit (24h fresh)"
        
        # Step 3: Try Google Places API (if provided)
        if google_places_func:
            try:
                logger.info("📍 Trying Google Places API...")
                prospects = google_places_func(store_number, category, limit)
                
                if prospects and len(prospects) > 0:
                    # Cache the results
                    if self.cache:
                        self.cache.cache_prospects(store_number, category, prospects)
                        self.cache.record_api_success()
                    
                    return prospects[:limit], "✅ Google Places API"
                else:
                    logger.info(f"Google Places returned empty results (prospects={prospects})")
            except Exception as e:
                logger.error(f"❌ Google Places error: {e}", exc_info=True)
                if self.cache:
                    self.cache.record_api_failure()
        
        # Step 4: Try free API (Nominatim + Overpass)
        if self.free_api:
            try:
                logger.info("🆓 Trying free API (Nominatim + Overpass)...")
                prospects = self.free_api.prospect_search(
                    store_address,
                    category=category,
                    limit=limit,
                    radius_m=1609  # 1 mile
                )
                
                if prospects:
                    # Cache the results
                    if self.cache:
                        self.cache.cache_prospects(store_number, category, prospects)
                        self.cache.record_api_success()
                    
                    return prospects[:limit], "⚠️ Free API (Google unavailable)"
            except Exception as e:
                logger.warning(f"Free API failed: {e}")
                if self.cache:
                    self.cache.record_api_failure()
        
        # Step 5: Fallback disabled per Tyler's request (Mar 15, 2026)
        logger.warning("⚠️ All APIs failed - no fallback available")
        
        # Step 6: Fall back to cached results (even if stale)
        logger.warning("⚠️ All APIs failed, using stale cache")
        return self._get_cached_fallback(store_number, category, limit)
    
    def _get_cached_fallback(
        self,
        store_number: str,
        category: str,
        limit: int
    ) -> tuple[List[Dict], str]:
        """Get any cached results (even if expired) for offline fallback."""
        try:
            if not self.cache:
                return [], "📦 No cache available"
            
            cache_data = self.cache.CACHE_FILE.read_text()
            cache_json = __import__("json").loads(cache_data)
            
            # Find any matching entry (ignore expiration)
            for entry in cache_json.get("cache", {}).values():
                if (entry.get("storeNumber") == store_number and 
                    entry.get("category") == category):
                    prospects = entry.get("prospects", [])
                    created = entry.get("createdAt", "unknown date")
                    source = f"📦 Offline cache ({created[:10]} - may be stale)"
                    return prospects[:limit], source
            
            # No matching cache entry at all
            return [], "📦 No cached prospects available"
        except Exception as e:
            logger.error(f"Fallback cache error: {e}")
            return [], "❌ Unable to retrieve fallback"
    
    def clear_old_cache(self):
        """Clean up old cache entries."""
        if self.cache:
            self.cache.clear_expired_cache()


# Singleton
_engine = None

def get_resilient_engine() -> ResilientProspectingEngine:
    """Get or create resilient engine singleton."""
    global _engine
    if _engine is None:
        _engine = ResilientProspectingEngine()
    return _engine


def search_with_resilience(
    store_number: str,
    store_address: str,
    category: str,
    google_places_func=None,
    limit: int = 10,
    force_refresh: bool = False
) -> tuple[List[Dict], str]:
    """
    Convenience function: search for prospects with auto-fallback.
    
    Usage:
        prospects, source = search_with_resilience(
            "ROS07Z-0042",
            "1234 Main St, Ridgefield, WA 98642",
            "restaurants",
            google_places_func=my_google_places_search,
            limit=10
        )
        
        # Display to user
        message = f"Found {len(prospects)} prospects ({source})"
        for p in prospects:
            message += f"\n• {p['name']}"
    
    Returns: (prospects_list, source_info_string)
    """
    engine = get_resilient_engine()
    return engine.search_prospects(
        store_number,
        store_address,
        category,
        google_places_func=google_places_func,
        limit=limit,
        force_refresh=force_refresh
    )


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    
    # Test with no Google Places (will fall back to free API)
    prospects, source = search_with_resilience(
        "ROS07Z-0042",
        "1234 Main St, Ridgefield, WA 98642",
        "restaurants",
        limit=5
    )
    
    print(f"\n✅ {source}")
    print(f"Found {len(prospects)} prospects:")
    for p in prospects:
        print(f"  • {p.get('name', 'Unknown')}")
