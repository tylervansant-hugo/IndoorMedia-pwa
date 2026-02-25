#!/usr/bin/env python3
"""
Facebook Ads Library checker - Find if a business is running ads
Uses Facebook's public Ads Library API
"""

import sys
import logging
from typing import Dict, Optional, List
import json
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class FacebookAdsChecker:
    """Check Facebook Ads Library for active advertising."""
    
    def __init__(self):
        """Initialize."""
        try:
            import requests
            self.requests = requests
        except ImportError:
            logger.error("❌ requests not installed")
            sys.exit(1)
    
    def search_business_ads(self, business_name: str, max_results: int = 10) -> List[Dict]:
        """
        Search Facebook Ads Library for a business.
        Returns list of active ads.
        
        Note: Facebook Ads Library API requires authentication.
        This implementation uses the public web interface approach.
        """
        try:
            # Facebook Ads Library URL (public access)
            # Format: https://www.facebook.com/ads/library/
            
            logger.info(f"🔍 Searching Facebook Ads for: {business_name}")
            
            # Direct API call to Facebook's ads library
            # Note: This requires proper API access or web scraping
            # For now, we'll return a placeholder structure
            
            ads = self._search_facebook_api(business_name)
            return ads
        
        except Exception as e:
            logger.warning(f"⚠️ Error searching Facebook Ads: {e}")
            return []
    
    def _search_facebook_api(self, business_name: str) -> List[Dict]:
        """
        Search using Facebook Ads Library API.
        Uses public endpoint (no auth required for basic queries).
        """
        try:
            # Facebook Ads Archive API (public endpoint)
            # Available at: https://graph.facebook.com/v18.0/ads_archive
            
            url = "https://graph.facebook.com/v18.0/ads_archive"
            
            params = {
                'search_terms': business_name.lower(),
                'ad_type': 'ALL',
                'fields': 'id,name,ad_creation_date,ad_snapshot_url,spend,currency',
                'limit': 10,
                'country': 'US',  # Focus on US only
            }
            
            response = self.requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                ads = data.get('data', [])
                if ads:
                    logger.info(f"✅ Found {len(ads)} active Facebook ads for: {business_name}")
                    return ads
            elif response.status_code == 400:
                # API might have restrictions or require token
                logger.warning("⚠️ Facebook Ads API requires setup or is rate-limited")
                logger.info("   Setup: https://developers.facebook.com/docs/marketing-api/guides/ads-archive")
            
            return []
        
        except Exception as e:
            logger.warning(f"⚠️ Facebook API error: {e}")
            return []
    
    def estimate_ad_spend(self, business_name: str) -> Optional[Dict]:
        """
        Estimate ad spend based on ads found.
        Higher spend = more serious marketing effort.
        """
        ads = self.search_business_ads(business_name)
        
        if not ads:
            return None
        
        return {
            'business': business_name,
            'active_ads': len(ads),
            'spend_indicator': 'HIGH' if len(ads) > 5 else 'MEDIUM' if len(ads) > 0 else 'LOW',
            'source': 'Facebook Ads Library',
            'ads': ads
        }


class AdSpendIndicator:
    """Detect advertising spend signals from multiple sources."""
    
    def __init__(self):
        """Initialize indicators."""
        self.facebook = FacebookAdsChecker()
    
    def check_advertising_signals(self, business_name: str, city: str) -> Dict:
        """
        Check multiple advertising signal sources.
        Returns composite score.
        """
        signals = {
            'business': business_name,
            'city': city,
            'sources': {}
        }
        
        # Check Facebook Ads
        facebook_ads = self.facebook.search_business_ads(business_name)
        if facebook_ads:
            signals['sources']['facebook_ads'] = {
                'found': True,
                'count': len(facebook_ads),
                'boost': 30  # +30 likelihood score
            }
        
        # Additional sources can be added here
        # - Groupon
        # - Google Local Services Ads
        # - etc.
        
        return signals


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: facebook_ads_checker.py <business_name>")
        print("Example: facebook_ads_checker.py 'Quiznos'")
        sys.exit(1)
    
    business_name = sys.argv[1]
    
    checker = FacebookAdsChecker()
    results = checker.search_business_ads(business_name)
    
    print(f"\n🔍 Facebook Ads for: {business_name}")
    if results:
        print(f"✅ Found {len(results)} active ads")
        for ad in results:
            print(f"  - {ad.get('name', 'N/A')}")
    else:
        print("❌ No ads found or API not configured")
