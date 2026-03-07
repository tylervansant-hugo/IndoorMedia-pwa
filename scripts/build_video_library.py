#!/usr/bin/env python3
"""Build a video library from Google Drive folders with category mapping."""

import subprocess
import json
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
DATA_DIR = WORKSPACE / "data"
VIDEO_LIBRARY_FILE = DATA_DIR / "video_library.json"

# Google Drive folder IDs
MAIN_FOLDER = "1GHr0Ds5aJKY56dhSKYDYy8B3bdhMn6Mv"
CATEGORY_FOLDERS = {
    "Real Estate": "1WBBHLyYmEu6vaJ2_2fjrWj45hiN3XQiV",
    "Financial Services": "1ZOnBEVqLxo0DThkRWIq4tFkhfLFGw0Oz",
    "Dispensaries": "1oVzKx33V3zokqEOoMaPNduI5z7mP7bju",
    "Food & Drink": "10NSxr1JCHSE_IIu8H9RBEvQC9HSbDKKg",
    "Clothing": "169CAuzpqTfaELu6eF7TXTWOX2qM6OztI",
    "Pets": "1nHcMfBc9oHhhsbU6rYdE3vyVAmquSG7E",
    "Kids": "1CkwryWu5CArJ0tvyuo23FfKe-qFm6E2c",
    "Automotive": "1Z8VxgRHDuT4j_SOAy4jF3SOhi5m_bz4X",
    "Health & Beauty": "1QMz86KGjxGIzN5FnmxaiSTUklTJFQxFW",
    "Retail": "1HaheS2m9WT-rDNEfPC5CJkgCTPjUiPP9",
}

# Additional local testimonials folder - auto-categorize by business name
LOCAL_TESTIMONIALS_FOLDER = "16QAHNvkEcWp7VUWk-S2yWT3Pka73dFRP"

# Keywords for auto-categorizing local testimonials
AUTO_CATEGORY_KEYWORDS = {
    "Pets": ["pet", "vet", "animal", "hospital", "grooming", "paws", "precious"],
    "Automotive": ["auto", "car", "mechanic", "service", "repair", "dealer", "garage", "grease", "money"],
    "Food & Drink": ["restaurant", "pizza", "tacos", "food", "cafe", "coffee", "donuts", "pho", "thai", "mexican", "brewery", "grill", "biryan", "indian", "frozen yogurt", "ice cream", "korean"],
    "Health & Beauty": ["salon", "spa", "barber", "hair", "beauty", "doctor", "medical", "dental"],
}

# Category keywords for matching prospects
CATEGORY_KEYWORDS = {
    "Real Estate": ["realtor", "real estate", "realty", "property", "agent", "broker"],
    "Financial Services": ["accountant", "financial", "financial advisor", "cpa", "tax", "bank", "advisor"],
    "Dispensaries": ["dispensary", "cannabis", "thc", "cbd", "marijuana"],
    "Food & Drink": ["restaurant", "cafe", "coffee", "bar", "deli", "bakery", "pizza", "taco", "food", "drink"],
    "Clothing": ["apparel", "clothing", "boutique", "fashion", "clothes", "shop", "retail clothing"],
    "Pets": ["pet", "vet", "veterinary", "animal", "dog", "cat", "grooming", "pet store"],
    "Kids": ["daycare", "preschool", "children", "learning", "school", "toys", "kids"],
    "Automotive": ["auto", "car", "mechanic", "service", "repair", "dealer", "garage", "autotek"],
    "Health & Beauty": ["salon", "spa", "barber", "hair", "beauty", "doctor", "medical", "dental", "clinic", "wellness"],
    "Retail": ["retail", "store", "shop", "market", "general merchandise"],
}

def get_videos_in_folder(folder_id: str) -> list:
    """Get all video files in a folder."""
    try:
        cmd = [
            "gog", "drive", "ls",
            f"--parent={folder_id}",
            "--json"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"Error listing folder {folder_id}: {result.stderr}")
            return []
        
        data = json.loads(result.stdout)
        files = data.get("files", [])
        
        # Filter for video files only
        videos = []
        for f in files:
            mime = f.get("mimeType", "").lower()
            if "video" in mime or any(ext in f.get("name", "").lower() for ext in [".mp4", ".mov", ".avi", ".mkv"]):
                videos.append({
                    "title": f.get("name", "").replace(".mp4", "").replace(".mov", "").replace(".avi", "").replace(".mkv", ""),
                    "id": f.get("id", ""),
                    "url": f.get("webViewLink", ""),
                    "mime": f.get("mimeType", ""),
                })
        
        return videos
    except Exception as e:
        print(f"Error getting videos from {folder_id}: {e}")
        return []

def categorize_local_testimonial(video_title: str) -> str:
    """Auto-categorize a local testimonial based on business name."""
    title_lower = video_title.lower()
    
    for category, keywords in AUTO_CATEGORY_KEYWORDS.items():
        if any(kw in title_lower for kw in keywords):
            return category
    
    # Default to Food & Drink if no match
    return "Food & Drink"


def get_local_testimonials() -> dict:
    """Get videos from local testimonials folder and auto-categorize."""
    print(f"  📂 Scanning Local Testimonials...")
    videos = get_videos_in_folder(LOCAL_TESTIMONIALS_FOLDER)
    
    # Group by auto-detected category
    by_category = {}
    for video in videos:
        category = categorize_local_testimonial(video["title"])
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(video)
    
    print(f"     ✅ Found {len(videos)} local testimonials")
    for cat, vids in by_category.items():
        print(f"        → {cat}: {len(vids)} videos")
    
    return by_category


def build_library():
    """Build the complete video library."""
    library = {
        "categories": {},
        "all_videos": [],
        "updated_at": "",
    }
    
    print("🎬 Building video library...")
    
    # Get videos from each main category
    for category, folder_id in CATEGORY_FOLDERS.items():
        print(f"  📂 Scanning {category}...")
        videos = get_videos_in_folder(folder_id)
        
        if videos:
            library["categories"][category] = {
                "keywords": CATEGORY_KEYWORDS.get(category, []),
                "videos": videos,
                "count": len(videos),
            }
            library["all_videos"].extend([{**v, "category": category} for v in videos])
            print(f"     ✅ Found {len(videos)} videos")
        else:
            print(f"     ⚠️  No videos found")
    
    # Add local testimonials with auto-categorization
    local_by_cat = get_local_testimonials()
    for category, videos in local_by_cat.items():
        if category in library["categories"]:
            # Append to existing category
            library["categories"][category]["videos"].extend(videos)
            library["categories"][category]["count"] += len(videos)
        else:
            # Create new category
            library["categories"][category] = {
                "keywords": CATEGORY_KEYWORDS.get(category, []),
                "videos": videos,
                "count": len(videos),
            }
        library["all_videos"].extend([{**v, "category": category} for v in videos])
    
    library["updated_at"] = subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], capture_output=True, text=True).stdout.strip()
    
    # Save library
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(VIDEO_LIBRARY_FILE, 'w') as f:
        json.dump(library, f, indent=2)
    
    print(f"\n✅ Video library saved to {VIDEO_LIBRARY_FILE}")
    print(f"📊 Total videos: {len(library['all_videos'])}")
    print(f"📂 Categories: {len(library['categories'])}")
    
    return library

if __name__ == "__main__":
    build_library()
