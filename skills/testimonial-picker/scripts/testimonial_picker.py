#!/usr/bin/env python3
"""
Testimonial Picker - Curated testimonial packages for sales appointments.

Given a business type and city, pulls:
- 1 video testimonial in the same category
- 3-4 strong written testimonials (high redemptions, same category)
- 1 nearby written testimonial (geographically close)

Usage:
  python3 testimonial_picker.py "pizza place" "Longview"
  python3 testimonial_picker.py --category "Pizza" --city "Longview" --state "WA"
"""

import json
import argparse
import re
from pathlib import Path
from collections import defaultdict
from math import radians, sin, cos, sqrt, atan2

# Approximate city coordinates for distance calculation (OR/WA focus)
CITY_COORDS = {
    # Washington
    'seattle': (47.6062, -122.3321),
    'spokane': (47.6588, -117.4260),
    'tacoma': (47.2529, -122.4443),
    'vancouver': (45.6387, -122.6615),
    'bellevue': (47.6101, -122.2015),
    'everett': (47.9790, -122.2021),
    'kent': (47.3809, -122.2348),
    'yakima': (46.6021, -120.5059),
    'renton': (47.4829, -122.2171),
    'bellingham': (48.7519, -122.4787),
    'kennewick': (46.2112, -119.1372),
    'olympia': (47.0379, -122.9007),
    'puyallup': (47.1854, -122.2929),
    'longview': (46.1382, -122.9382),
    'airway heights': (47.6447, -117.5936),
    
    # Oregon
    'portland': (45.5152, -122.6784),
    'salem': (44.9429, -123.0351),
    'eugene': (44.0521, -123.0868),
    'gresham': (45.4984, -122.4318),
    'hillsboro': (45.5229, -122.9898),
    'beaverton': (45.4871, -122.8037),
    'bend': (44.0582, -121.3153),
    'medford': (42.3265, -122.8756),
    'springfield': (44.0462, -122.9811),
    'corvallis': (44.5646, -123.2620),
    'albany': (44.6365, -123.1059),
    'hood river': (45.7054, -121.5215),
}

# Category mapping: written testimonial categories -> video categories
CATEGORY_MAP = {
    # Food categories
    'pizza': ['pizza', 'food_drink'],
    'mexican': ['mexican', 'food_drink'],
    'asian': ['asian', 'food_drink'],
    'chinese': ['asian', 'food_drink'],
    'japanese': ['asian', 'food_drink'],
    'thai': ['asian', 'food_drink'],
    'vietnamese': ['asian', 'food_drink'],
    'korean': ['asian', 'food_drink'],
    'sushi': ['asian', 'food_drink'],
    'cultural dining': ['food_drink'],
    'casual dining': ['food_drink', 'general'],
    'sandwich shops': ['food_drink'],
    'fast food': ['fast_food', 'food_drink'],
    'ice cream / yogurt shops': ['ice_cream', 'food_drink'],
    'coffee shops': ['coffee', 'food_drink'],
    'donut shops': ['donuts', 'ice_cream', 'food_drink'],
    'bakery': ['food_drink'],
    
    # Automotive
    'car wash / detailing': ['automotive'],
    'repair / body / maintenance': ['automotive'],
    
    # Beauty
    'hair / nails / spa / tanning': ['beauty', 'salon'],
    
    # Pets
    'pet care': ['pets'],
    'pet supply store': ['pets'],
    
    # Real estate
    'real estate / realtors': ['real_estate'],
    
    # Dispensary
    'dispensary': ['dispensary'],
    
    # Other
    'dry cleaning / laundry services / tailors / shoe repair': ['retail'],
    'home improvement /  contracting / supplies': ['retail'],
    'sporting / military goods & supplies': ['retail'],
    'fitness & health': ['beauty'],
}

def load_testimonials():
    """Load written testimonials cache."""
    # Go up from skills/testimonial-picker/scripts to workspace root
    cache_path = Path(__file__).parent.parent.parent.parent / 'data' / 'testimonials_cache.json'
    with open(cache_path) as f:
        return json.load(f)

def load_video_index():
    """Load video testimonials index."""
    # Go up from skills/testimonial-picker/scripts to workspace root
    index_path = Path(__file__).parent.parent.parent.parent / 'data' / 'video_index.json'
    with open(index_path) as f:
        return json.load(f)

def normalize_category(category):
    """Normalize category string for matching."""
    return category.lower().strip()

def get_video_categories(written_category):
    """Map a written testimonial category to video categories."""
    norm_cat = normalize_category(written_category)
    
    # Try exact match first
    if norm_cat in CATEGORY_MAP:
        return CATEGORY_MAP[norm_cat]
    
    # Try partial match (e.g., "pizza place" should match "pizza")
    for key, value in CATEGORY_MAP.items():
        if key in norm_cat or norm_cat in key:
            return value
    
    # Check if it's a specific type mentioned in the input
    # Food categories
    if any(term in norm_cat for term in ['pizza', 'mexican', 'thai', 'chinese', 'japanese', 'asian', 'sushi']):
        if 'pizza' in norm_cat:
            return ['pizza', 'food_drink']
        elif 'mexican' in norm_cat:
            return ['mexican', 'food_drink']
        elif any(term in norm_cat for term in ['thai', 'chinese', 'japanese', 'asian', 'sushi', 'vietnamese', 'korean']):
            return ['asian', 'food_drink']
    
    # Beauty/Salon categories
    if any(term in norm_cat for term in ['nail', 'salon', 'hair', 'spa', 'barber']):
        return ['beauty', 'salon']
    
    # Automotive
    if any(term in norm_cat for term in ['auto', 'car wash', 'repair', 'mechanic', 'oil change']):
        return ['automotive']
    
    # Pets
    if any(term in norm_cat for term in ['pet', 'veterinary', 'vet', 'animal']):
        return ['pets']
    
    # Real estate
    if any(term in norm_cat for term in ['realtor', 'real estate']):
        return ['real_estate']
    
    # Dispensary
    if any(term in norm_cat for term in ['dispensary', 'cbd', 'cannabis']):
        return ['dispensary']
    
    # Default for restaurants/food
    return ['food_drink']

def find_video_match(category, video_index):
    """Find best matching video testimonial."""
    video_categories = get_video_categories(category)
    
    # Prefer flat folder (more recent, OR/WA region) but only if it's an exact match
    flat_videos = [v for v in video_index if v['folder_source'] == 'flat']
    categorized_videos = [v for v in video_index if v['folder_source'] == 'categorized']
    
    # Try exact match on first (most specific) category in flat folder
    if video_categories:
        first_cat = video_categories[0]
        # Exact match in flat folder (most recent, local)
        matches = [v for v in flat_videos if v['category'] == first_cat]
        if matches:
            return matches[0]  # Most recent (already sorted by date)
        
        # Exact match in categorized folder
        matches = [v for v in categorized_videos if v['category'] == first_cat]
        if matches:
            return matches[0]
    
    # Try broader categories
    for vid_cat in video_categories[1:]:
        # Flat folder
        matches = [v for v in flat_videos if v['category'] == vid_cat]
        if matches:
            return matches[0]
        
        # Categorized folder
        matches = [v for v in categorized_videos if v['category'] == vid_cat]
        if matches:
            return matches[0]
    
    # Last resort: any food & drink video from flat folder (prefer local)
    food_flat = [v for v in flat_videos if v['category'] in ['food_drink', 'general']]
    if food_flat:
        return food_flat[0]
    
    food_videos = [v for v in video_index if v['category'] in ['food_drink', 'general']]
    return food_videos[0] if food_videos else video_index[0]

def calculate_score(testimonial, target_category):
    """Calculate composite score for testimonial relevance."""
    score = 0
    
    # Category match (most important)
    test_cat = normalize_category(testimonial['full'].get('category', ''))
    target_norm = normalize_category(target_category)
    
    # Exact match
    if test_cat == target_norm:
        score += 100
    # Partial match
    elif target_norm in test_cat or test_cat in target_norm:
        score += 50
    # Special case: Thai/Chinese/Japanese/Vietnamese/Korean -> Asian
    elif test_cat == 'asian' and any(cuisine in target_norm for cuisine in ['thai', 'chinese', 'japanese', 'vietnamese', 'korean', 'sushi']):
        score += 90
    elif any(cuisine in test_cat for cuisine in ['thai', 'chinese', 'japanese', 'vietnamese', 'korean', 'sushi']) and 'asian' in target_norm:
        score += 90
    # Special case: Nail/Hair/Spa -> Hair / Nails / Spa / Tanning
    elif any(term in target_norm for term in ['nail', 'hair', 'salon', 'spa', 'barber']) and 'hair / nails / spa' in test_cat:
        score += 90
    elif any(term in test_cat for term in ['nail', 'hair', 'salon', 'spa', 'barber']) and any(term in target_norm for term in ['nail', 'hair', 'salon', 'spa']):
        score += 80
    
    # Results strength
    per_month = testimonial['full'].get('perMonth', 0) or 0
    per_week = testimonial['full'].get('perWeek', 0) or 0
    score += min(per_month, 200) / 2  # Cap at 100 points
    score += min(per_week * 4, 100) / 2  # Approximate monthly from weekly
    
    # ROI/redemption mentions in comments
    comments = testimonial['full'].get('comments', '').lower()
    if any(term in comments for term in ['roi', 'return on investment', 'redemption']):
        score += 30
    
    # Specific numbers mentioned
    if re.search(r'\$\d+', comments):
        score += 20
    if re.search(r'\d+\s*(coupon|redemption)', comments):
        score += 20
    
    return score

def haversine_distance(coord1, coord2):
    """Calculate distance between two lat/lon coordinates in miles."""
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    R = 3959  # Earth radius in miles
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

def find_nearby_testimonial(city, state, testimonials, exclude_ids):
    """Find geographically closest testimonial."""
    city_norm = city.lower().strip()
    target_coords = CITY_COORDS.get(city_norm)
    
    # If target city not in our coords, find by state and city name similarity
    candidates = []
    
    for t in testimonials:
        if t['id'] in exclude_ids:
            continue
        
        t_city = (t['full'].get('city') or '').lower().strip()
        t_state = (t['full'].get('state') or '').strip().upper()
        
        # Same state preference
        if state and t_state == state.upper():
            if target_coords:
                # Calculate distance if we have coords
                t_coords = CITY_COORDS.get(t_city)
                if t_coords:
                    distance = haversine_distance(target_coords, t_coords)
                    candidates.append((distance, t))
                else:
                    # Same state, unknown distance
                    candidates.append((500 if t_city != city_norm else 0, t))
            else:
                # No target coords, prefer exact city match
                candidates.append((0 if t_city == city_norm else 500, t))
    
    # Sort by distance
    candidates.sort(key=lambda x: x[0])
    
    return candidates[0][1] if candidates else None

def extract_quote(comments, max_length=120):
    """Extract a compelling quote snippet from comments."""
    if not comments:
        return "Great results with IndoorMedia!"
    
    # Split into sentences
    sentences = re.split(r'[.!?]+', comments)
    
    # Find sentences with numbers or strong words
    good_sentences = []
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        
        # Prioritize sentences with numbers, ROI, redemptions
        if any(term in sent.lower() for term in ['$', 'redemption', 'coupon', 'roi', 'customer', 'revenue']):
            good_sentences.append(sent)
        elif len(sent) > 20:  # Minimum substance
            good_sentences.append(sent)
    
    if not good_sentences:
        good_sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    # Pick first good sentence
    quote = good_sentences[0] if good_sentences else comments
    
    # Truncate if needed
    if len(quote) > max_length:
        quote = quote[:max_length-3] + '...'
    
    return quote

def format_output(video, written_matches, nearby, target_category):
    """Format the output for Telegram."""
    output = []
    
    # Video testimonial
    output.append("🎬 VIDEO TESTIMONIAL")
    output.append(f"{video['name']} - {video['category'].replace('_', ' ').title()}")
    output.append(f"🔗 {video['webViewLink']}")
    output.append("")
    
    # Written testimonials
    output.append("📝 MATCHING TESTIMONIALS")
    output.append("")
    
    for i, t in enumerate(written_matches, 1):
        full = t['full']
        business = full.get('businessName', 'Unknown')
        grocery = full.get('groceryStore', 'N/A')
        city = full.get('city', 'Unknown')
        state = full.get('state', '')
        per_month = full.get('perMonth', 0) or 0
        
        quote = extract_quote(full.get('comments', ''))
        pdf_url = f"https://testimonials.indoormedia.com/home/pdf/{t['id']}.pdf"
        
        output.append(f"{i}. {business} | {grocery} | {city}, {state}")
        output.append(f'   "{quote}"')
        if per_month > 0:
            output.append(f"   📊 {int(per_month)} redemptions/month")
        output.append(f"   📄 PDF: {pdf_url}")
        output.append("")
    
    # Nearby testimonial
    if nearby:
        output.append("📍 NEARBY TESTIMONIAL")
        full = nearby['full']
        business = full.get('businessName', 'Unknown')
        grocery = full.get('groceryStore', 'N/A')
        city = full.get('city', 'Unknown')
        state = full.get('state', '')
        quote = extract_quote(full.get('comments', ''))
        pdf_url = f"https://testimonials.indoormedia.com/home/pdf/{nearby['id']}.pdf"
        
        output.append(f"{business} | {grocery} | {city}, {state}")
        output.append(f'"{quote}"')
        output.append(f"📄 PDF: {pdf_url}")
    
    return '\n'.join(output)

def main():
    parser = argparse.ArgumentParser(description='Pick testimonials for sales appointments')
    parser.add_argument('business_type', nargs='?', help='Type of business (e.g., "pizza place")')
    parser.add_argument('city', nargs='?', help='City name (e.g., "Longview")')
    parser.add_argument('--category', help='Explicit category')
    parser.add_argument('--state', help='State abbreviation (e.g., "WA")')
    
    args = parser.parse_args()
    
    # Determine category and city
    if args.category:
        category = args.category
    elif args.business_type:
        category = args.business_type
    else:
        parser.print_help()
        return
    
    city = args.city or ''
    state = args.state or ''
    
    # Load data
    print(f"Loading testimonials for: {category} in {city}, {state}...\n")
    testimonials = load_testimonials()
    video_index = load_video_index()
    
    # 1. Find video match
    video = find_video_match(category, video_index)
    
    # 2. Find 3-4 strong written testimonials
    scored = []
    for t in testimonials:
        t_cat = t['full'].get('category', '')
        if not t_cat:
            continue
        
        score = calculate_score(t, category)
        scored.append((score, t))
    
    # Sort by score and take top 4
    scored.sort(key=lambda x: x[0], reverse=True)
    written_matches = [t for score, t in scored[:4]]
    
    # 3. Find nearby testimonial (exclude the ones already selected)
    exclude_ids = {t['id'] for t in written_matches}
    nearby = find_nearby_testimonial(city, state, testimonials, exclude_ids)
    
    # Format and print
    output = format_output(video, written_matches, nearby, category)
    print(output)

if __name__ == '__main__':
    main()
