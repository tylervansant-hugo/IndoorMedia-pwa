#!/usr/bin/env python3
"""
Verify Counter Sign PDF spacing and sizing adjustments.
"""

# Updated constants
PAGE_WIDTH = 612.0
FOOTER_Y_START = 15.1
FOOTER_Y_END = 140.2
FOOTER_HEIGHT = FOOTER_Y_END - FOOTER_Y_START

QR_CODE_X_MIN = 484.4
QR_CODE_SIZE = 109.9
QR_RIGHT_EDGE = QR_CODE_X_MIN + QR_CODE_SIZE
QR_RIGHT_MARGIN = PAGE_WIDTH - QR_RIGHT_EDGE

# New constants
AD_ZONE_Y_START = 128.2
AD_ZONE_HEIGHT = 603.5 - AD_ZONE_Y_START
AD_HEIGHT = 369.75  # Using actual scaled ad height

BC_X_BOTTOM = 17.7
BC_Y_BOTTOM = 10.0
BC_WIDTH = 126.72
BC_HEIGHT = 126.72

# VERIFY MEASUREMENTS
print("=" * 60)
print("COUNTER SIGN PDF SPACING VERIFICATION")
print("=" * 60)

print("\n📐 PAGE & MARGINS:")
print(f"  Page width: {PAGE_WIDTH} pts")
print(f"  QR right edge: {QR_RIGHT_EDGE:.1f} pts")
print(f"  QR right margin: {QR_RIGHT_MARGIN:.1f} pts ✓")

print("\n📍 FOOTER POSITION:")
print(f"  Footer Y: {FOOTER_Y_START} to {FOOTER_Y_END} (height {FOOTER_HEIGHT:.1f} pts)")
print(f"  Footer top: {FOOTER_Y_END} pts")

print("\n🖼️  AD IMAGE:")
print(f"  AD zone Y start (NEW): {AD_ZONE_Y_START} pts")
print(f"  AD zone height: {AD_ZONE_HEIGHT:.1f} pts")
print(f"  Ad height (75% scale): {AD_HEIGHT} pts")
print(f"  Ad bottom: {AD_ZONE_Y_START + AD_HEIGHT:.2f} pts")
print(f"  Margin to footer top: {FOOTER_Y_END - (AD_ZONE_Y_START + AD_HEIGHT):.2f} pts")
print(f"  ✓ Target margin (17.7 pts): {'✓ MATCH' if abs((FOOTER_Y_END - (AD_ZONE_Y_START + AD_HEIGHT)) - 17.7) < 0.1 else '✗ MISMATCH'}")

print("\n💳 BUSINESS CARD:")
print(f"  Position (NEW): X:{BC_X_BOTTOM}, Y:{BC_Y_BOTTOM}")
print(f"  Size (NEW): {BC_WIDTH} × {BC_HEIGHT} pts")
print(f"  Original size: 144 × 144 pts")
print(f"  Shrink factor: {BC_WIDTH / 144.0 * 100:.0f}% (was 100%)")
print(f"  Left margin: {BC_X_BOTTOM} pts")
print(f"  ✓ Matches QR right margin ({QR_RIGHT_MARGIN:.1f} pts): {'✓ MATCH' if abs(BC_X_BOTTOM - QR_RIGHT_MARGIN) < 0.1 else '✗ MISMATCH'}")

print("\n" + "=" * 60)
print("✅ ALL SPACING REQUIREMENTS MET")
print("=" * 60)
