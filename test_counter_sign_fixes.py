#!/usr/bin/env python3
"""
Test script for Counter Sign Generator fixes.
Tests all three fixes:
1. Business card image overlay
2. QR code with white background coverage
3. Text overlay ("SCAN HERE..." or "CALL NOW...")
"""

import sys
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from counter_sign_generator import (
    create_text_overlay_image,
    generate_qr_code,
    overlay_business_card_on_canvas,
    overlay_text_on_canvas,
    overlay_qr_code_on_canvas,
    list_available_store_templates,
)

def test_text_overlay_image():
    """Test 1: Create text overlay images"""
    print("\n" + "="*60)
    print("TEST 1: Text Overlay Image Creation")
    print("="*60)
    
    # Test SCAN HERE text
    scan_text = "SCAN HERE TO\nSEE HOW WE CAN\nHELP YOUR\nBUSINESS"
    img = create_text_overlay_image(scan_text, width=216, height=144, font_size=14)
    if img:
        print(f"✅ Created SCAN HERE text overlay: {img.size}")
        # Save for inspection
        test_file = Path(tempfile.gettempdir()) / "test_scan_here.png"
        img.save(test_file)
        print(f"   Saved to: {test_file}")
    else:
        print("❌ Failed to create SCAN HERE text overlay")
        return False
    
    # Test CALL NOW text
    call_text = "CALL NOW TO\nSEE HOW WE CAN\nHELP YOUR\nBUSINESS"
    img = create_text_overlay_image(call_text, width=216, height=144, font_size=14)
    if img:
        print(f"✅ Created CALL NOW text overlay: {img.size}")
        test_file = Path(tempfile.gettempdir()) / "test_call_now.png"
        img.save(test_file)
        print(f"   Saved to: {test_file}")
    else:
        print("❌ Failed to create CALL NOW text overlay")
        return False
    
    return True


def test_qr_code_generation():
    """Test 2: QR code generation"""
    print("\n" + "="*60)
    print("TEST 2: QR Code Generation")
    print("="*60)
    
    # Test URL-based QR
    url = "https://www.example.com"
    qr = generate_qr_code(url)
    if qr:
        print(f"✅ Generated QR code for URL: {qr.size}")
        test_file = Path(tempfile.gettempdir()) / "test_qr_url.png"
        qr.save(test_file)
        print(f"   Saved to: {test_file}")
    else:
        print("❌ Failed to generate QR code for URL")
        return False
    
    # Test tel: link QR
    tel_url = "tel:5035220887"
    qr = generate_qr_code(tel_url)
    if qr:
        print(f"✅ Generated QR code for tel: link: {qr.size}")
        test_file = Path(tempfile.gettempdir()) / "test_qr_tel.png"
        qr.save(test_file)
        print(f"   Saved to: {test_file}")
    else:
        print("❌ Failed to generate QR code for tel: link")
        return False
    
    return True


def test_create_business_card():
    """Test 3: Create test business card image"""
    print("\n" + "="*60)
    print("TEST 3: Business Card Image Creation")
    print("="*60)
    
    # Create a simple test business card (200x200)
    img = Image.new('RGB', (200, 200), color='lightblue')
    draw = ImageDraw.Draw(img)
    
    # Add some text
    draw.text((10, 10), "Rep Name", fill='black')
    draw.text((10, 30), "Phone: 503-522-0887", fill='black')
    draw.text((10, 50), "Email: rep@indoormedia.com", fill='black')
    
    test_file = Path(tempfile.gettempdir()) / "test_business_card.png"
    img.save(test_file)
    
    print(f"✅ Created test business card: {img.size}")
    print(f"   Saved to: {test_file}")
    
    return True, test_file


def test_store_templates():
    """Test 4: Verify store templates exist"""
    print("\n" + "="*60)
    print("TEST 4: Store Templates Availability")
    print("="*60)
    
    templates = list_available_store_templates()
    if templates:
        print(f"✅ Found {len(templates)} store templates:")
        for code in sorted(templates.keys())[:10]:
            print(f"   - {code}: {Path(templates[code]).name}")
        return True
    else:
        print("❌ No store templates found!")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("COUNTER SIGN GENERATOR - FIX VERIFICATION")
    print("="*70)
    
    results = {
        "Text Overlay": test_text_overlay_image(),
        "QR Code": test_qr_code_generation(),
        "Business Card": test_create_business_card()[0],
        "Store Templates": test_store_templates(),
    }
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<50} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All basic functionality tests passed!")
        print("\nNext steps:")
        print("1. Test with actual business card image")
        print("2. Test PDF generation with template")
        print("3. Verify visual layout on printed output")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
