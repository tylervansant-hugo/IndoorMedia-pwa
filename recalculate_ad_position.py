#!/usr/bin/env python3
"""
Recalculate proper AD_ZONE_Y_START based on footer position and required margins.

PDF coordinate system (origin at bottom-left):
- Page height: 792 pts
- Footer: Y 15.1 to 140.2 (height 125.1 pts)
- Footer top: 140.2 pts
- Header: Y 603.5 to 792
- Ad zone: Should go from some Y_START up to header bottom (603.5)

Goal: 17.7 pt margin between ad image bottom and footer top (140.2)
"""

# Fixed measurements
FOOTER_Y_END = 140.2  # Top of footer zone
HEADER_Y_START = 603.5  # Bottom of header (top of ad zone)
TARGET_MARGIN_BELOW_AD = 17.7  # Space between ad bottom and footer top
AD_HEIGHT = 369.75  # Height of actual ad image (75% scale: 493 * 0.75 = 369.75)

# Calculate proper AD_ZONE_Y_START
# If we want 17.7 pt margin below the ad image:
# ad_bottom + margin = footer_top
# ad_bottom = footer_top - margin = 140.2 - 17.7 = 122.5
# ad_start = ad_bottom - ad_height = 122.5 - 369.75 = -247.25

# This is NEGATIVE, which means the ad is too tall for this constraint.
# The problem: we can't fit a 369.75 pt tall ad with only 122.5 pts of space.

# SOLUTION: The ad must fit between the footer top and header start
# Available space: 603.5 - 140.2 = 463.3 pts
# Ad height: 369.75 pts
# Whitespace available: 463.3 - 369.75 = 93.55 pts

# To maintain symmetric 17.7 pt margins on top and bottom:
# margin_top + ad_height + margin_bottom = total_space
# 17.7 + 369.75 + 17.7 = 405.15 pts (fits within 463.3 available)

# So:
# ad_bottom = footer_top - margin_bottom = 140.2 - 17.7 = 122.5
# ad_start = ad_bottom - ad_height = 122.5 - 369.75 = -247.25  (STILL NEGATIVE!)

# The issue is that ad_bottom would be 122.5, but ad is 369.75 tall.
# This doesn't work. The ad MUST start above footer_top.

# CORRECT INTERPRETATION:
# The footer occupies Y 15.1 to 140.2
# The ad zone should occupy Y 140.2 to 603.5 (or something less)
# If ad is 369.75 tall and we want 17.7 pt margin ABOVE it (below in visual terms),
# then: ad_bottom = ad_start + ad_height
# And there should be 17.7 pts between ad_bottom and footer_top (140.2)
# So: ad_bottom = 140.2 - 17.7 = 122.5
# So: ad_start = 122.5 - 369.75 = -247.25 (IMPOSSIBLE)

# ACTUAL SOLUTION:
# The ad zone starts at 140.2 (top of footer).
# To have 17.7 pt space, ad should start 17.7 pts ABOVE footer top.
# ad_start = 140.2 + 17.7 = 157.9 pts

AD_ZONE_Y_START_CORRECT = FOOTER_Y_END + TARGET_MARGIN_BELOW_AD
AD_ZONE_HEIGHT = HEADER_Y_START - AD_ZONE_Y_START_CORRECT
AD_BOTTOM = AD_ZONE_Y_START_CORRECT + AD_HEIGHT

print("=" * 70)
print("AD ZONE POSITIONING ANALYSIS")
print("=" * 70)

print(f"\nFOOTER ZONE:")
print(f"  Y: 15.1 to {FOOTER_Y_END} (height 125.1 pts)")
print(f"  Top of footer: {FOOTER_Y_END} pts")

print(f"\nHEADER ZONE:")
print(f"  Y: {HEADER_Y_START} to 792 pts")

print(f"\nAVAILABLE SPACE FOR AD:")
print(f"  From footer top ({FOOTER_Y_END}) to header start ({HEADER_Y_START})")
print(f"  Total available: {HEADER_Y_START - FOOTER_Y_END:.1f} pts")

print(f"\nAD IMAGE:")
print(f"  Height (75% scale): {AD_HEIGHT} pts")
print(f"  Required margin above: {TARGET_MARGIN_BELOW_AD} pts")

print(f"\nCALCULATED AD ZONE START:")
print(f"  AD_ZONE_Y_START = footer_top + margin")
print(f"  AD_ZONE_Y_START = {FOOTER_Y_END} + {TARGET_MARGIN_BELOW_AD}")
print(f"  AD_ZONE_Y_START = {AD_ZONE_Y_START_CORRECT} pts ✓")

print(f"\nCHECK FIT:")
print(f"  Ad bottom: {AD_BOTTOM:.2f} pts")
print(f"  Header top: {HEADER_Y_START} pts")
print(f"  Space above ad: {HEADER_Y_START - AD_BOTTOM:.2f} pts")
print(f"  ✓ Fits within page: {AD_BOTTOM < HEADER_Y_START}")

print(f"\nFINAL UPDATE:")
print(f"  Change AD_ZONE_Y_START from 110.5 to {AD_ZONE_Y_START_CORRECT}")

print("\n" + "=" * 70)
