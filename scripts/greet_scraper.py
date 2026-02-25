#!/usr/bin/env python3
"""
Greet Magazine scraper - Find local advertisers by zip code
Checks if businesses are advertising on Greet Magazine
"""

import sys
import logging
from typing import List, Dict, Optional
import time
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class GreetScraper:
    """Scrape Greet Magazine for local advertisers."""
    
    def __init__(self):
        """Initialize with requests library."""
        try:
            import requests
            from bs4 import BeautifulSoup
            self.requests = requests
            self.BeautifulSoup = BeautifulSoup
        except ImportError:
            logger.error("❌ requests/beautifulsoup4 not installed")
            logger.error("Run: pip install requests beautifulsoup4")
            sys.exit(1)
    
    def get_greet_advertisers(self, city: str, state: str) -> List[Dict]:
        """
        Scrape Greet Magazine for advertisers in a city.
        Returns list of advertiser names and addresses.
        """
        try:
            # Format URL
            city_slug = city.lower().replace(" ", "-")
            state_slug = state.lower()
            url = f"https://greetmag.com/locations/{city_slug}-{state_slug}/partners/"
            
            logger.info(f"🌐 Scraping Greet Magazine: {city}, {state}")
            logger.info(f"   URL: {url}")
            
            # Fetch page
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
            }
            response = self.requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = self.BeautifulSoup(response.content, 'html.parser')
            
            # Find advertiser listings (depends on Greet's HTML structure)
            advertisers = []
            
            # Look for common patterns in business listings
            # This may need adjustment based on actual Greet HTML
            for item in soup.find_all('div', class_=['partner', 'advertiser', 'listing', 'business']):
                name_elem = item.find('h2') or item.find('h3') or item.find('a')
                if name_elem:
                    name = name_elem.get_text(strip=True)
                    if name and len(name) > 2:
                        advertisers.append({
                            'name': name,
                            'source': 'Greet Magazine',
                            'url': url
                        })
            
            # If no results with above pattern, try alternative selectors
            if not advertisers:
                # Try finding all links that might be advertisers
                for link in soup.find_all('a'):
                    text = link.get_text(strip=True)
                    if text and len(text) > 3 and len(text) < 100:
                        # Filter out common navigation links
                        if text.lower() not in ['home', 'about', 'contact', 'advertise', 'back', 'next']:
                            advertisers.append({
                                'name': text,
                                'source': 'Greet Magazine',
                                'url': url
                            })
            
            logger.info(f"✅ Found {len(advertisers)} advertisers on Greet Magazine")
            return advertisers[:50]  # Top 50
        
        except Exception as e:
            logger.warning(f"⚠️ Error scraping Greet: {e}")
            return []
    
    def search_greet_by_business_name(self, business_name: str, city: str, state: str) -> bool:
        """
        Check if a specific business is listed on Greet Magazine.
        Returns True if found, False otherwise.
        """
        try:
            advertisers = self.get_greet_advertisers(city, state)
            business_lower = business_name.lower().strip()
            
            for advertiser in advertisers:
                if business_lower in advertiser['name'].lower():
                    return True
            
            return False
        except Exception as e:
            logger.warning(f"⚠️ Error searching Greet: {e}")
            return False


class GreetCache:
    """Cache Greet results to avoid repeated scraping."""
    
    def __init__(self, cache_file: str = "data/store-rates/greet_cache.json"):
        """Initialize cache."""
        import json
        from pathlib import Path
        
        self.json = json
        self.cache_file = Path(cache_file)
        self.cache = self._load()
    
    def _load(self) -> dict:
        """Load cache from file."""
        if self.cache_file.exists():
            with open(self.cache_file) as f:
                return self.json.load(f)
        return {}
    
    def _save(self):
        """Save cache to file."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, 'w') as f:
            self.json.dump(self.cache, f, indent=2)
    
    def get(self, key: str) -> Optional[List]:
        """Get cached result."""
        return self.cache.get(key)
    
    def set(self, key: str, value: List):
        """Set cached result."""
        self.cache[key] = value
        self._save()
    
    def is_cached(self, key: str) -> bool:
        """Check if key is cached."""
        return key in self.cache


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: greet_scraper.py <city> <state>")
        print("Example: greet_scraper.py 'Ridgefield' 'WA'")
        sys.exit(1)
    
    city = sys.argv[1]
    state = sys.argv[2]
    
    scraper = GreetScraper()
    advertisers = scraper.get_greet_advertisers(city, state)
    
    if advertisers:
        print(f"\n✅ Advertisers found on Greet Magazine in {city}, {state}:")
        for i, adv in enumerate(advertisers[:10], 1):
            print(f"  {i}. {adv['name']}")
    else:
        print(f"❌ No advertisers found or page not accessible")
