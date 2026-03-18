# Safeway Counter Sign Template Measurements

## Page Dimensions
- **Width:** 612.0 pts (8.5")
- **Height:** 792.0 pts (11.0")

## Layout Sections (PDF coordinates: origin at bottom-left)

### TOP SECTION (Header) - DO NOT MODIFY
- **Y Range:** 603.5 - 792.0 pts (from bottom)
- **Height:** 188.5 pts (~2.62")
- **Content:** 
  - "ATTENTION!" banner
  - Header text: "HAVE YOU SEEN OUR COUPON ON THE BACK OF THE CASH REGISTER RECEIPT TAPE?"

### MIDDLE SECTION (Ad Image Zone) - FILL COMPLETELY
- **Y Range:** 110.5 - 603.5 pts (from bottom)
- **Height:** 493.0 pts (~6.85")
- **X Range:** Full width (0 - 612 pts) with margins
- **Width:** ~550 pts (~7.64") considering margins
- **Purpose:** Ad image should fill this entire blank area
- **Constraints:** 
  - No overlaps with header (above 603.5)
  - No overlaps with footer (below 110.5)
  - No overlaps with QR code (bottom-right corner)

### BOTTOM SECTION (Red Footer Bar) - PRESERVE & OVERLAY
- **Y Range:** 15.1 - 140.2 pts (from bottom)
- **Height:** 125.1 pts (~1.74")
- **Full Width:** 476.9 - 601.9 pts (125.1 width) - THIS IS BACKGROUND

#### Footer Subsections:

**Bottom-Left (Business Card)**
- **Position:** x=36, y=144 pts (from bottom)
- **Size:** ~144 × 144 pts (~2" × 2")
- **Purpose:** Rep business card image

**Bottom-Center (Text Overlay)**
- **Position:** x=198, y=180 pts (from bottom)
- **Size:** ~216 × 144 pts (~3" × 2")
- **Purpose:** "SCAN HERE TO SEE HOW WE CAN HELP YOUR BUSINESS" or "CALL NOW..."
- **Replaces:** Original "SCAN HERE FOR ADDITIONAL DISCOUNTS IN YOUR AREA"

**Bottom-Right (QR Code) - EXACT PLACEMENT CRITICAL**
- **QR Code Grid Bounds:** x=484.4-594.4, y=22.7-132.6 pts (from bottom)
- **QR Code Size:** 109.9 × 109.9 pts (~1.53" × 1.53")
- **Center Point:** (539.4, 77.6 pts from bottom)
- **Background White Box:** 
  - **Size:** ~125 × 125 pts (~1.74" × 1.74")
  - **Bounds:** x=476.9-601.9, y=15.1-140.2 pts
  - **Purpose:** White background to cover original QR code and provide contrast

## Implementation Strategy

1. **Do NOT modify** the header (top 188.5 pts)
2. **Ad image** fills 493 pts height in middle (110.5 - 603.5 y-range)
3. **Overlay on footer:**
   - White box first at x=476.9, y=15.1, size 125.1×125.1 (covers original QR)
   - New QR code at x=484.4, y=22.7, size 109.9×109.9
   - Business card at x=36, y=144, size 144×144
   - Text at x=198, y=180, size 216×144

## PDF Library Approach

Use **PyPDF2** to:
1. Load template PDF
2. Create overlay canvas with reportlab
3. Ensure white background box drawn BEFORE new QR code
4. Merge overlay with template using `page.merge_page()`
