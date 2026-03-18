#!/usr/bin/env python3
"""
Test script for counter sign generator
Creates a test counter sign to verify all systems are working
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw
from counter_sign_generator import (
    generate_counter_sign,
    list_available_store_templates,
    get_direct_team_by_name,
)

def create_test_ad_image(output_path: str):
    """Create a simple test ad image."""
    img = Image.new('RGB', (800, 600), color='lightblue')
    draw = ImageDraw.Draw(img)
    
    # Add some text
    draw.rectangle([50, 50, 750, 550], outline='navy', width=5)
    draw.text((400, 300), "TEST AD IMAGE", fill='black', anchor='mm')
    
    img.save(output_path)
    print(f"✅ Created test image: {output_path}")
    return output_path

def main():
    """Run counter sign tests."""
    print("🧪 Counter Sign Generator Test Suite\n")
    
    # Test 1: List templates
    print("1️⃣ Testing template listing...")
    templates = list_available_store_templates()
    print(f"   ✅ Found {len(templates)} templates")
    
    if not templates:
        print("   ❌ No templates found!")
        return False
    
    # Test 2: Get direct team
    print("\n2️⃣ Testing direct team data...")
    rep = get_direct_team_by_name("Adan Ramos")
    if rep:
        print(f"   ✅ Found Adan Ramos: {rep['email']}")
    else:
        print("   ❌ Could not find Adan Ramos")
        return False
    
    # Test 3: Create test counter sign
    print("\n3️⃣ Testing counter sign generation...")
    
    # Create test ad image
    test_img_path = "/tmp/test_ad.jpg"
    create_test_ad_image(test_img_path)
    
    # Generate counter sign
    rep_data = {
        'name': 'Adan Ramos',
        'email': 'adan.ramos@indoormedia.com',
        'cell': '206.383.7190',
        'corporate': '800.247.4793',
    }
    
    pdf_bytes, output_path = generate_counter_sign(
        chain_code='SAF',
        ad_image_path=test_img_path,
        rep_data=rep_data,
        landing_page_url='https://www.indoormedia.com',
    )
    
    if pdf_bytes and output_path:
        print(f"   ✅ Generated counter sign: {output_path}")
        print(f"   📊 PDF size: {len(pdf_bytes)} bytes")
        
        # Verify file exists
        if Path(output_path).exists():
            print(f"   ✅ File verified on disk")
        else:
            print(f"   ❌ File not found on disk")
            return False
    else:
        print("   ❌ Failed to generate counter sign")
        return False
    
    # Test 4: Test CALL NOW image (no landing page)
    print("\n4️⃣ Testing counter sign without landing page...")
    
    pdf_bytes2, output_path2 = generate_counter_sign(
        chain_code='SAF',
        ad_image_path=test_img_path,
        rep_data=rep_data,
        landing_page_url='none',
    )
    
    if pdf_bytes2:
        print(f"   ✅ Generated 'CALL NOW' counter sign")
    else:
        print("   ❌ Failed to generate 'CALL NOW' counter sign")
        return False
    
    print("\n✅ All tests passed!\n")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
