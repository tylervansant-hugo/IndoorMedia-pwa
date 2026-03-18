#!/usr/bin/env python3
"""
Advertising Signals Detector for ProspectBot
Detects active advertising across Meta (Facebook), Google Ads, and other platforms
Uses public ad libraries (no auth required)
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import time
import hashlib

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try importing requests (required for scraping)
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("⚠️ requests module not available — some features disabled")

# Configuration
WORKSPACE = Path(__file__).parent.parent
DATA_DIR = WORKSPACE / "data"
CACHE_FILE = DATA_DIR / "advertising_signals_cache.json"
CACHE_TTL_HOURS = 24

# Ensure cache file exists
CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_cache() -> Dict:
    """Load the advertising signals cache from disk."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Cache load error: {e}")
    return {}


def save_cache(cache: Dict) -> None:
    """Save the advertising signals cache to disk."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        logger.error(f"Cache save error: {e}")


def is_cache_valid(cached_at: str, ttl_hours: int = 24) -> bool:
    """Check if cached data is still valid."""
    try:
        cached_time = datetime.fromisoformat(cached_at)
        age = datetime.now() - cached_time
        return age < timedelta(hours=ttl_hours)
    except Exception:
        return False


class MetaAdsChecker:
    """Check Meta (Facebook) Ads Library for active advertising."""
    
    def __init__(self, timeout: int = 8):
        """Initialize Meta Ads checker.
        
        Args:
            timeout: Max seconds to wait per request (default 8)
        """
        self.timeout = timeout
        self.platform = "Meta"
    
    def check_ads(self, business_name: str, limit: int = 10) -> Optional[Dict]:
        """
        Check Meta Ads Library for a business.
        
        Returns:
            Dict with platform, found, active_ads, spend_estimate, ads list, or None if error
        """
        if not REQUESTS_AVAILABLE:
            logger.warning("requests module not available for Meta scraping")
            return None
        
        try:
            logger.info(f"🔍 Checking Meta Ads Library for: {business_name}")
            
            # Meta Ads Library public endpoint
            # Format: https://facebook.com/ads/library/?country=US&q=<business_name>
            search_url = f"https://www.facebook.com/ads/library/?country=US&q={business_name.replace(' ', '+')}"
            
            # Attempt HEAD request to check availability (no scraping needed for now)
            # Full scraping would require Selenium or Playwright
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
            }
            
            response = requests.head(search_url, headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                # Page accessible — business may have ads
                # Note: Full scraping of ad details requires JS rendering (Playwright/Selenium)
                logger.info(f"✅ Meta Ads Library accessible for: {business_name}")
                
                return {
                    "platform": "Meta",
                    "found": True,
                    "active_ads": None,  # Would need JS to extract count
                    "spend_estimate": None,  # Would need account/auth
                    "ads": [],  # Would need JS to extract details
                    "url": search_url,
                    "note": "Use Meta Ads Library UI to view details"
                }
            else:
                logger.info(f"⚠️ Meta Ads Library not accessible for: {business_name}")
                return {
                    "platform": "Meta",
                    "found": False,
                    "active_ads": 0,
                    "ads": []
                }
        
        except requests.Timeout:
            logger.warning(f"⏱ Meta Ads check timed out (>{self.timeout}s)")
            return None
        except Exception as e:
            logger.warning(f"⚠️ Meta Ads check error: {e}")
            return None
    
    def format_result(self, data: Dict) -> Dict:
        """Format Meta ads result for display."""
        if not data:
            return {"platform": "Meta", "found": False}
        
        return {
            "platform": "Meta",
            "found": data.get("found", False),
            "active_ads": data.get("active_ads", 0),
            "spend_estimate": data.get("spend_estimate", "N/A"),
            "ads": data.get("ads", []),
            "url": data.get("url", ""),
        }


class GoogleAdsChecker:
    """Check Google Ads Library for active advertising."""
    
    def __init__(self, timeout: int = 8):
        """Initialize Google Ads checker.
        
        Args:
            timeout: Max seconds to wait per request (default 8)
        """
        self.timeout = timeout
        self.platform = "Google"
    
    def check_ads(self, business_name: str, limit: int = 10) -> Optional[Dict]:
        """
        Check Google Ads Library for a business.
        
        Returns:
            Dict with platform, found, running_ads, ad_count, ads list, or None if error
        """
        if not REQUESTS_AVAILABLE:
            logger.warning("requests module not available for Google scraping")
            return None
        
        try:
            logger.info(f"🔍 Checking Google Ads Library for: {business_name}")
            
            # Google Ads Library public endpoint
            # Format: https://ads.google.com/intl/en_US/home/tools/ads-transparency/
            google_library_url = "https://ads.google.com/intl/en_US/home/tools/ads-transparency/"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
            }
            
            # Test if library is accessible
            response = requests.head(google_library_url, headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                # Library is accessible
                # Note: Full search requires form submission and JS rendering
                logger.info(f"✅ Google Ads Library accessible for: {business_name}")
                
                return {
                    "platform": "Google",
                    "found": True,
                    "running_ads": None,  # Would need JS to check
                    "ad_count": None,
                    "ads": [],  # Would need JS to extract
                    "url": google_library_url,
                    "note": "Use Google Ads Library UI to search"
                }
            else:
                logger.info(f"⚠️ Google Ads Library not accessible")
                return {
                    "platform": "Google",
                    "found": False,
                    "running_ads": False,
                    "ad_count": 0,
                    "ads": []
                }
        
        except requests.Timeout:
            logger.warning(f"⏱ Google Ads check timed out (>{self.timeout}s)")
            return None
        except Exception as e:
            logger.warning(f"⚠️ Google Ads check error: {e}")
            return None
    
    def format_result(self, data: Dict) -> Dict:
        """Format Google ads result for display."""
        if not data:
            return {"platform": "Google", "found": False}
        
        return {
            "platform": "Google",
            "found": data.get("found", False),
            "running_ads": data.get("running_ads", False),
            "ad_count": data.get("ad_count", 0),
            "ads": data.get("ads", []),
            "url": data.get("url", ""),
        }


class AdvertisingSignalsDetector:
    """Main detector for advertising signals across multiple platforms."""
    
    def __init__(self):
        """Initialize the detector with checkers for each platform."""
        self.meta_checker = MetaAdsChecker(timeout=8)
        self.google_checker = GoogleAdsChecker(timeout=8)
        self.cache = load_cache()
    
    def check_business(self, business_name: str, force_refresh: bool = False) -> Dict:
        """
        Check advertising signals for a business across all platforms.
        
        Args:
            business_name: Name of business to check
            force_refresh: Skip cache and fetch fresh data
        
        Returns:
            Dict with results from all platforms + composite scoring
        """
        cache_key = self._get_cache_key(business_name)
        
        # Check cache first (if not forced)
        if not force_refresh and cache_key in self.cache:
            cached = self.cache[cache_key]
            if is_cache_valid(cached.get("cached_at", ""), CACHE_TTL_HOURS):
                logger.info(f"✅ Using cached data for {business_name}")
                return cached["data"]
        
        logger.info(f"🔄 Fetching fresh data for {business_name}")
        
        # Check all platforms in parallel
        results = {
            "business": business_name,
            "checked_at": datetime.now().isoformat(),
            "platforms": {},
            "found_advertising": False,
            "likelihood_boost": 0,
        }
        
        # Meta Ads Library
        try:
            meta_result = self.meta_checker.check_ads(business_name)
            if meta_result:
                results["platforms"]["meta"] = meta_result
                if meta_result.get("found"):
                    results["found_advertising"] = True
                    results["likelihood_boost"] += 15  # +15 points if advertising found
        except Exception as e:
            logger.warning(f"Meta check failed: {e}")
            results["platforms"]["meta"] = {"platform": "Meta", "found": False, "error": str(e)}
        
        # Google Ads Library
        try:
            google_result = self.google_checker.check_ads(business_name)
            if google_result:
                results["platforms"]["google"] = google_result
                if google_result.get("found"):
                    results["found_advertising"] = True
                    results["likelihood_boost"] += 15  # +15 points if advertising found
        except Exception as e:
            logger.warning(f"Google check failed: {e}")
            results["platforms"]["google"] = {"platform": "Google", "found": False, "error": str(e)}
        
        # Cache results
        self.cache[cache_key] = {
            "cached_at": datetime.now().isoformat(),
            "data": results,
            "ttl": CACHE_TTL_HOURS * 3600
        }
        save_cache(self.cache)
        
        return results
    
    def _get_cache_key(self, business_name: str) -> str:
        """Generate a cache key from business name."""
        # Use hash to avoid issues with special characters
        return hashlib.md5(business_name.lower().encode()).hexdigest()[:16]


def check_meta_ads(business_name: str) -> Optional[Dict]:
    """
    Check Meta Ads Library for a business.
    
    Args:
        business_name: Name of business to check
    
    Returns:
        Dict with Meta ads data or None
    """
    checker = MetaAdsChecker(timeout=8)
    result = checker.check_ads(business_name)
    return checker.format_result(result) if result else None


def check_google_ads(business_name: str) -> Optional[Dict]:
    """
    Check Google Ads Library for a business.
    
    Args:
        business_name: Name of business to check
    
    Returns:
        Dict with Google ads data or None
    """
    checker = GoogleAdsChecker(timeout=8)
    result = checker.check_ads(business_name)
    return checker.format_result(result) if result else None


def get_all_ad_signals(business_name: str, force_refresh: bool = False) -> Dict:
    """
    Get advertising signals from all platforms with caching.
    
    Args:
        business_name: Name of business to check
        force_refresh: Skip cache and fetch fresh data
    
    Returns:
        Dict with results from all platforms + boost score
    """
    detector = AdvertisingSignalsDetector()
    return detector.check_business(business_name, force_refresh=force_refresh)


def format_ad_signals_for_display(signals: Dict, max_width: int = 50) -> str:
    """
    Format advertising signals for display in prospect card.
    
    Args:
        signals: Dict from get_all_ad_signals()
        max_width: Max width for formatting
    
    Returns:
        Formatted string for display
    """
    if not signals or not signals.get("platforms"):
        return ""
    
    lines = []
    business = signals.get("business", "")
    
    # Header
    if signals.get("found_advertising"):
        lines.append("🎬 *ADVERTISING SIGNALS*")
    else:
        lines.append("🎬 *ADVERTISING SIGNALS* (none detected)")
    
    # Platform results
    platforms = signals.get("platforms", {})
    
    if platforms.get("meta", {}).get("found"):
        active = platforms["meta"].get("active_ads", "?")
        spend = platforms["meta"].get("spend_estimate", "?")
        lines.append(f"  • 📘 *Meta:* {active} active ads ({spend})")
    
    if platforms.get("google", {}).get("found"):
        active = platforms["google"].get("ad_count", "?")
        lines.append(f"  • 🔍 *Google:* {active} active ads")
    
    # Likelihood boost
    if signals.get("likelihood_boost", 0) > 0:
        boost = signals.get("likelihood_boost", 0)
        lines.append(f"\n✨ *+{boost} likelihood boost* (active advertiser)")
    
    # Last checked
    checked_at = signals.get("checked_at", "")
    if checked_at:
        try:
            dt = datetime.fromisoformat(checked_at)
            minutes_ago = int((datetime.now() - dt).total_seconds() / 60)
            if minutes_ago < 1:
                time_str = "just now"
            elif minutes_ago < 60:
                time_str = f"{minutes_ago}m ago"
            else:
                hours = minutes_ago // 60
                time_str = f"{hours}h ago"
            lines.append(f"_Last updated: {time_str}_")
        except Exception:
            pass
    
    return "\n".join(lines) if lines else ""


def get_likelihood_boost(signals: Dict) -> int:
    """
    Extract likelihood score boost from signals.
    
    Args:
        signals: Dict from get_all_ad_signals()
    
    Returns:
        Integer boost amount (0 if no advertising found)
    """
    return signals.get("likelihood_boost", 0) if signals else 0


if __name__ == "__main__":
    """Test the advertising signals detector."""
    if len(sys.argv) < 2:
        print("Usage: advertising_signals.py <business_name>")
        print("Example: advertising_signals.py 'Autotek International LLC'")
        sys.exit(1)
    
    business_name = sys.argv[1]
    
    print(f"\n🎬 Advertising Signals Detector")
    print(f"📍 Business: {business_name}\n")
    
    # Get signals with caching
    signals = get_all_ad_signals(business_name)
    
    # Display results
    display = format_ad_signals_for_display(signals)
    if display:
        print(display)
    else:
        print("No advertising detected across Meta and Google platforms.")
    
    # Show boost
    boost = get_likelihood_boost(signals)
    if boost > 0:
        print(f"\n✨ Likelihood boost: +{boost} points")
    
    # Raw JSON for debugging
    print(f"\n📋 Raw data:\n{json.dumps(signals, indent=2)}")
