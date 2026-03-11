#!/usr/bin/env python3
"""
Prospecting Cache Layer - Resilient caching + circuit breaker for API failures
Eliminates repeated API calls, graceful degradation when APIs fail
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import hashlib

logger = logging.getLogger(__name__)

class ProspectingCache:
    """Cache prospecting results locally with TTL and circuit breaker."""
    
    CACHE_FILE = Path(__file__).parent.parent / "data" / "prospecting_cache.json"
    CIRCUIT_BREAKER_FILE = Path(__file__).parent.parent / "data" / "api_circuit_breaker.json"
    CACHE_TTL_HOURS = 24
    CIRCUIT_BREAKER_THRESHOLD = 3  # Fail 3x, then trip
    CIRCUIT_BREAKER_RESET_HOURS = 1
    
    def __init__(self):
        """Initialize cache files."""
        self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_cache_file()
        self._ensure_circuit_breaker_file()
    
    def _ensure_cache_file(self):
        """Create empty cache if doesn't exist."""
        if not self.CACHE_FILE.exists():
            self.CACHE_FILE.write_text(json.dumps({"cache": {}, "lastUpdated": None}, indent=2))
    
    def _ensure_circuit_breaker_file(self):
        """Create empty circuit breaker if doesn't exist."""
        if not self.CIRCUIT_BREAKER_FILE.exists():
            self.CIRCUIT_BREAKER_FILE.write_text(json.dumps({
                "status": "closed",  # closed=normal, open=APIs failing, half-open=testing
                "failureCount": 0,
                "lastFailureTime": None,
                "lastTrippedTime": None
            }, indent=2))
    
    def _get_cache_key(self, store_number: str, category: str) -> str:
        """Generate cache key for prospecting query."""
        key_str = f"{store_number}|{category}".lower()
        return hashlib.md5(key_str.encode()).hexdigest()[:16]
    
    def get_cached_prospects(self, store_number: str, category: str) -> Optional[List[Dict]]:
        """Retrieve cached prospects if available and not expired."""
        try:
            cache_data = json.loads(self.CACHE_FILE.read_text())
            cache_key = self._get_cache_key(store_number, category)
            
            if cache_key in cache_data["cache"]:
                entry = cache_data["cache"][cache_key]
                created_at = datetime.fromisoformat(entry["createdAt"])
                age_hours = (datetime.now() - created_at).total_seconds() / 3600
                
                if age_hours < self.CACHE_TTL_HOURS:
                    logger.info(f"✅ Cache hit for {store_number}/{category} (age: {age_hours:.1f}h)")
                    return entry["prospects"]
                else:
                    logger.info(f"Cache expired for {store_number}/{category}")
            
            return None
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
            return None
    
    def cache_prospects(self, store_number: str, category: str, prospects: List[Dict]):
        """Store prospecting results in cache."""
        try:
            cache_data = json.loads(self.CACHE_FILE.read_text())
            cache_key = self._get_cache_key(store_number, category)
            
            cache_data["cache"][cache_key] = {
                "storeNumber": store_number,
                "category": category,
                "prospects": prospects,
                "createdAt": datetime.now().isoformat(),
                "count": len(prospects)
            }
            cache_data["lastUpdated"] = datetime.now().isoformat()
            
            self.CACHE_FILE.write_text(json.dumps(cache_data, indent=2))
            logger.info(f"✅ Cached {len(prospects)} prospects for {store_number}/{category}")
        except Exception as e:
            logger.error(f"Cache write error: {e}")
    
    def is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open (APIs failing)."""
        try:
            cb_data = json.loads(self.CIRCUIT_BREAKER_FILE.read_text())
            
            if cb_data["status"] == "open":
                # Check if we should try to half-open
                last_tripped = datetime.fromisoformat(cb_data["lastTrippedTime"])
                age_minutes = (datetime.now() - last_tripped).total_seconds() / 60
                
                if age_minutes > self.CIRCUIT_BREAKER_RESET_HOURS * 60:
                    logger.info("🔄 Circuit breaker half-open: testing APIs")
                    cb_data["status"] = "half-open"
                    self.CIRCUIT_BREAKER_FILE.write_text(json.dumps(cb_data, indent=2))
                    return False
                
                return True
            
            return False
        except Exception as e:
            logger.warning(f"Circuit breaker read error: {e}")
            return False
    
    def record_api_failure(self):
        """Record API failure for circuit breaker."""
        try:
            cb_data = json.loads(self.CIRCUIT_BREAKER_FILE.read_text())
            
            if cb_data["status"] in ["closed", "half-open"]:
                cb_data["failureCount"] += 1
                cb_data["lastFailureTime"] = datetime.now().isoformat()
                
                if cb_data["failureCount"] >= self.CIRCUIT_BREAKER_THRESHOLD:
                    logger.error(f"🔴 Circuit breaker OPEN (failures: {cb_data['failureCount']})")
                    cb_data["status"] = "open"
                    cb_data["lastTrippedTime"] = datetime.now().isoformat()
            
            self.CIRCUIT_BREAKER_FILE.write_text(json.dumps(cb_data, indent=2))
        except Exception as e:
            logger.error(f"Circuit breaker write error: {e}")
    
    def record_api_success(self):
        """Reset circuit breaker on API success."""
        try:
            cb_data = json.loads(self.CIRCUIT_BREAKER_FILE.read_text())
            cb_data["status"] = "closed"
            cb_data["failureCount"] = 0
            cb_data["lastFailureTime"] = None
            self.CIRCUIT_BREAKER_FILE.write_text(json.dumps(cb_data, indent=2))
            logger.info("✅ Circuit breaker CLOSED (APIs working)")
        except Exception as e:
            logger.error(f"Circuit breaker reset error: {e}")
    
    def get_circuit_breaker_status(self) -> Dict:
        """Get current circuit breaker state."""
        try:
            return json.loads(self.CIRCUIT_BREAKER_FILE.read_text())
        except:
            return {"status": "unknown"}
    
    def clear_expired_cache(self):
        """Remove cache entries older than TTL."""
        try:
            cache_data = json.loads(self.CACHE_FILE.read_text())
            original_count = len(cache_data["cache"])
            
            expired_keys = []
            for key, entry in cache_data["cache"].items():
                created_at = datetime.fromisoformat(entry["createdAt"])
                age_hours = (datetime.now() - created_at).total_seconds() / 3600
                if age_hours >= self.CACHE_TTL_HOURS:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del cache_data["cache"][key]
            
            self.CACHE_FILE.write_text(json.dumps(cache_data, indent=2))
            logger.info(f"🗑️ Cleaned {len(expired_keys)}/{original_count} cache entries")
        except Exception as e:
            logger.warning(f"Cache cleanup error: {e}")


# Singleton instance
_cache_instance = None

def get_cache() -> ProspectingCache:
    """Get or create cache singleton."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ProspectingCache()
    return _cache_instance
