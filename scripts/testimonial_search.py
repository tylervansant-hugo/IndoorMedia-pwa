#!/usr/bin/env python3
"""
Testimonial Search Tool - Search testimonials.indoormedia.com by keyword
Fetches live data from the testimonials database and enables fast keyword search
"""

import json
import sys
import re
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import html

CACHE_FILE = Path(__file__).parent.parent / "data" / "testimonials_cache.json"
SITE_URL = "https://testimonials.indoormedia.com"
API_ENDPOINT = f"{SITE_URL}/Home/Search"


def fetch_testimonials_from_api(limit=10000, batch_size=2000):
    """Fetch testimonials from the site's DataTables API in batches."""
    print(f"🔄 Fetching testimonials from API... (up to {limit} records, {batch_size} per batch)")
    
    all_data = []
    start = 0
    draw = 1
    
    while start < limit:
        fetch_count = min(batch_size, limit - start)
        params = {
            'draw': str(draw),
            'start': str(start),
            'length': str(fetch_count),
        }
        
        try:
            data = urlencode(params).encode('utf-8')
            request = Request(API_ENDPOINT, data=data, headers={'User-Agent': 'Mozilla/5.0'})
            
            with urlopen(request, timeout=120) as response:
                json_data = json.loads(response.read().decode('utf-8'))
                
                records = json_data.get('data', [])
                if not records:
                    print(f"   No more records at offset {start}")
                    break
                
                all_data.extend(records)
                total_available = json_data.get('recordsTotal', 0)
                print(f"   ✅ Batch {draw}: fetched {len(records)} (total so far: {len(all_data)}/{total_available})")
                
                if len(records) < fetch_count:
                    break  # No more data
                    
                start += fetch_count
                draw += 1
                
        except Exception as e:
            print(f"   ❌ Error at offset {start}: {e}")
            if all_data:
                print(f"   Continuing with {len(all_data)} records fetched so far")
            break
    
    if all_data:
        return {'data': all_data, 'recordsTotal': len(all_data)}
    return None


def clean_testimonial(t):
    """Extract clean text from testimonial HTML"""
    if not t:
        return None
    
    html_content = t.get('html', '')
    
    # Extract business name and testimonial text from HTML
    h4_match = re.search(r'<h4>([^<]+)</h4>', html_content)
    business = h4_match.group(1).strip() if h4_match else t.get('businessName', '')
    
    # Extract the testimonial comment text
    comment = t.get('comments', '')
    
    # Extract keywords
    keywords = t.get('metaKeywords', '')
    
    # Combine all searchable text
    searchable = f"{business} {comment} {keywords} {t.get('businessName', '')} {t.get('category', '')}"
    
    return {
        'id': t.get('id'),
        'business': business,
        'comment': comment[:200],  # First 200 chars
        'url': f"{SITE_URL}/{t['id']}-{business.lower().replace(' ', '-')}",
        'searchable': searchable.lower(),
        'full': t  # Keep full record for details
    }


def cache_testimonials(data):
    """Save testimonials to cache"""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Extract and clean testimonial list
    testimonials = []
    if isinstance(data, dict) and 'data' in data:
        items = data['data']
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    cleaned = clean_testimonial(item)
                    if cleaned:
                        testimonials.append(cleaned)
    
    if testimonials:
        with open(CACHE_FILE, 'w') as f:
            json.dump(testimonials, f, indent=2)
        print(f"✅ Cached {len(testimonials)} testimonials")
        return True
    
    return False


def load_testimonials():
    """Load testimonials from cache or fetch fresh"""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r') as f:
                testimonials = json.load(f)
                if testimonials:
                    print(f"📚 Loaded {len(testimonials)} from cache")
                    return testimonials
        except Exception as e:
            print(f"⚠️  Cache error: {e}")
    
    # Fetch if no cache
    data = fetch_testimonials_from_api()
    if data and cache_testimonials(data):
        return json.load(open(CACHE_FILE, 'r'))
    
    return []


def search_testimonials(keyword):
    """Search testimonials by keyword (case-insensitive)"""
    testimonials = load_testimonials()
    
    if not testimonials:
        print("❌ No testimonials found. Try running with --refresh to fetch fresh data.")
        return []
    
    keyword_lower = keyword.lower()
    results = []
    
    for t in testimonials:
        # Search in the searchable text field
        if keyword_lower in t.get('searchable', ''):
            results.append(t)
    
    return results


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python testimonial_search.py <keyword>       - Search testimonials")
        print("  python testimonial_search.py --refresh       - Fetch fresh data")
        print("  python testimonial_search.py --list          - List recent testimonials")
        print("\nExamples:")
        print("  python testimonial_search.py 'skeptical'")
        print("  python testimonial_search.py 'parking lot'")
        print("  python testimonial_search.py 'ROI'")
        print("  python testimonial_search.py 'return on investment'")
        sys.exit(1)
    
    arg = sys.argv[1].lower()
    
    if arg == "--refresh":
        data = fetch_testimonials_from_api()
        if data:
            cache_testimonials(data)
        return
    
    if arg == "--list":
        testimonials = load_testimonials()
        print(f"\n📋 Recent testimonials ({len(testimonials)} total):\n")
        for i, t in enumerate(testimonials[:20], 1):
            print(f"{i:2d}. {t.get('business', 'Unknown')}")
        if len(testimonials) > 20:
            print(f"\n... and {len(testimonials) - 20} more")
        return
    
    # Search
    results = search_testimonials(arg)
    
    if not results:
        print(f"\n❌ No testimonials found matching '{arg}'")
        return
    
    print(f"\n🔍 Found {len(results)} testimonial(s) matching '{arg}':\n")
    for i, result in enumerate(results, 1):
        business = result.get('business', 'Unknown')
        comment = result.get('comment', '')
        url = result.get('url', '')
        
        print(f"{i}. {business}")
        if comment:
            # Show first 150 chars of comment
            preview = comment[:150] + "..." if len(comment) > 150 else comment
            print(f"   📝 \"{preview}\"")
        print(f"   🔗 {url}\n")


if __name__ == "__main__":
    main()
