#!/usr/bin/env python3
"""
Build video testimonial index from Google Drive folders.

Scans two Drive folders:
1. Categorized folder (1GHr0Ds5aJKY56dhSKYDYy8B3bdhMn6Mv) - subfolders by category
2. Flat folder (16QAHNvkEcWp7VUWk-S2yWT3Pka73dFRP) - video files with business names

Outputs to: data/video_index.json
"""

import json
import subprocess
import re
from pathlib import Path

# Category inference patterns for flat folder videos
CATEGORY_PATTERNS = {
    'pizza': ['pizza', 'round table', 'papa murphy', 'mountain mike'],
    'mexican': ['mexican', 'taqueria', 'taco', 'burrito', 'vaqueros', 'atilano', 'carnitas', 'tequila', 'cielito lindo', 'catedral'],
    'asian': ['asian', 'chinese', 'thai', 'pho', 'sushi', 'korean', 'japanese', 'vietnamese', 'kindee', 'biryani', 'amrutha'],
    'automotive': ['auto', 'car wash', 'honda', 'grease money'],
    'pets': ['pet', 'animal hospital', 'veterinary'],
    'coffee': ['coffee', 'cafe'],
    'ice_cream': ['ice cream', 'yogurt', 'baskin robbins', 'blue cow', 'mojo'],
    'donuts': ['donut', 'mojo'],
    'dispensary': ['dispensary', 'smoke shop', 'cbd', 'top shelf'],
    'real_estate': ['realtor', 'real estate', 'shelley', 'carrie'],
    'salon': ['salon', 'spa', 'nail', 'hair'],
    'fast_food': ['arby', 'denny'],
    'brewery': ['brewing', 'von ebert'],
    'seafood': ['seafood', 'janthony'],
    'general': ['general', 'collard green', 'perko', 'sourdough', 'baja fresh', 'wing stop', 'buffalo wings', 'hall of flame', 'potato shack', 'white horse'],
}

# Drive folder mappings to broader categories
FOLDER_CATEGORY_MAP = {
    'Food & Drink': 'food_drink',
    'Automotive': 'automotive',
    'Health & Beauty': 'beauty',
    'Pets': 'pets',
    'Real Estate': 'real_estate',
    'Financial Services': 'financial',
    'Dispensaries': 'dispensary',
    'Clothing': 'retail',
    'Kids': 'kids',
    'Retail': 'retail',
}

def run_gog_search(query, max_results=100):
    """Execute gog drive search and return JSON results."""
    try:
        result = subprocess.run(
            ['gog', 'drive', 'search', query, '--max', str(max_results), '--json'],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running gog: {e}")
        print(f"Stderr: {e.stderr}")
        return {"files": []}
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return {"files": []}

def infer_category_from_name(name):
    """Infer category from business name for flat folder videos."""
    name_lower = name.lower()
    
    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if pattern in name_lower:
                return category
    
    return 'uncategorized'

def scan_folder_recursive(folder_id, parent_category=None, source=''):
    """Recursively scan a Drive folder for videos."""
    videos = []
    
    query = f"'{folder_id}' in parents"
    result = run_gog_search(query)
    
    for file in result.get('files', []):
        mime_type = file.get('mimeType', '')
        
        # If it's a folder, recurse into it
        if mime_type == 'application/vnd.google-apps.folder':
            folder_name = file['name']
            category = FOLDER_CATEGORY_MAP.get(folder_name, folder_name.lower().replace(' & ', '_').replace(' ', '_'))
            
            # Recursively scan subfolder
            subfolder_videos = scan_folder_recursive(file['id'], category, source or folder_name)
            videos.extend(subfolder_videos)
        
        # If it's a video, add it
        elif 'video' in mime_type:
            name = file.get('name', '')
            # Remove file extension
            clean_name = re.sub(r'\.(mp4|mov|avi|mkv|m4v|quicktime)$', '', name, flags=re.IGNORECASE)
            
            videos.append({
                'name': clean_name,
                'driveId': file['id'],
                'webViewLink': file['webViewLink'],
                'category': parent_category or 'uncategorized',
                'folder_source': source or 'categorized',
                'mimeType': mime_type,
                'modifiedTime': file.get('modifiedTime', '')
            })
    
    return videos

def main():
    print("Building video testimonial index...")
    
    all_videos = []
    
    # Scan Folder 1: Categorized subfolders
    print("\n[1/2] Scanning categorized folder (1GHr0Ds5aJKY56dhSKYDYy8B3bdhMn6Mv)...")
    folder1_videos = scan_folder_recursive('1GHr0Ds5aJKY56dhSKYDYy8B3bdhMn6Mv', source='categorized')
    print(f"  Found {len(folder1_videos)} videos in categorized folders")
    all_videos.extend(folder1_videos)
    
    # Scan Folder 2: Flat video files (with category inference)
    print("\n[2/2] Scanning flat folder (16QAHNvkEcWp7VUWk-S2yWT3Pka73dFRP)...")
    result = run_gog_search("'16QAHNvkEcWp7VUWk-S2yWT3Pka73dFRP' in parents", max_results=200)
    
    folder2_videos = []
    for file in result.get('files', []):
        mime_type = file.get('mimeType', '')
        
        if 'video' in mime_type:
            name = file.get('name', '')
            clean_name = re.sub(r'\.(mp4|mov|avi|mkv|m4v|quicktime)$', '', name, flags=re.IGNORECASE)
            
            # Infer category from business name
            category = infer_category_from_name(clean_name)
            
            folder2_videos.append({
                'name': clean_name,
                'driveId': file['id'],
                'webViewLink': file['webViewLink'],
                'category': category,
                'folder_source': 'flat',
                'mimeType': mime_type,
                'modifiedTime': file.get('modifiedTime', '')
            })
    
    print(f"  Found {len(folder2_videos)} videos in flat folder")
    all_videos.extend(folder2_videos)
    
    # Sort by modified time (most recent first)
    all_videos.sort(key=lambda x: x['modifiedTime'], reverse=True)
    
    # Save to JSON (workspace/data/)
    output_path = Path(__file__).parent.parent.parent.parent / 'data' / 'video_index.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(all_videos, f, indent=2)
    
    print(f"\n✓ Video index saved to: {output_path}")
    print(f"  Total videos: {len(all_videos)}")
    
    # Print category breakdown
    from collections import Counter
    cat_counts = Counter(v['category'] for v in all_videos)
    print("\nCategory breakdown:")
    for cat, count in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat}: {count}")

if __name__ == '__main__':
    main()
