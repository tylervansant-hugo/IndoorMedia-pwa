#!/usr/bin/env python3
"""
Counter Sign Generator - PRECISE POSITIONING
Exact ad image sizing and QR code placement based on template measurements.

TEMPLATE MEASUREMENTS (Safeway 8.5" × 11" = 612 × 792 pts):
- Header (top): Y 603.5-792 pts (DO NOT MODIFY)
- Ad Zone (middle): Y 110.5-603.5 pts (fill completely)
- Footer (bottom): Y 15.1-140.2 pts (preserve + overlay)
  - QR Code: exact x=484.4-594.4, y=22.7-132.6 (109.9×109.9 pts)
  - Business Card: x=36, y=144, size 144×144 pts
  - Text Overlay: x=198, y=180, size 216×144 pts
"""

import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import io
import qrcode
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants - PRECISE MEASUREMENTS
LETTER_WIDTH_PTS = 612.0
LETTER_HEIGHT_PTS = 792.0
DPI = 72  # Points per inch for PDF

# LAYOUT COORDINATES (in points, origin at bottom-left)
HEADER_Y_START = 603.5  # Header begins here
HEADER_Y_END = 792.0    # Top of page
HEADER_HEIGHT = HEADER_Y_END - HEADER_Y_START

AD_ZONE_Y_START = 430  # Ad positioned up 40 more pts (390 + 40)
AD_ZONE_Y_END = 603.5    # Ad zone ends (where header starts)
AD_ZONE_HEIGHT = AD_ZONE_Y_END - AD_ZONE_Y_START
AD_Y_POS = 430  # Ad top positioned 210 pts higher total

FOOTER_Y_START = 15.1
FOOTER_Y_END = 140.2
FOOTER_HEIGHT = FOOTER_Y_END - FOOTER_Y_START

# QR CODE - EXACT POSITION FROM TEMPLATE
QR_CODE_X_MIN = 484.4
QR_CODE_Y_MIN = 22.7
QR_CODE_SIZE = 109.9  # 109.9 × 109.9 pts (~1.53" × 1.53")

# WHITE BACKGROUND BOX (covers original QR)
QR_BG_X_MIN = 476.9
QR_BG_Y_MIN = 15.1
QR_BG_SIZE = 125.1  # 125.1 × 125.1 pts (~1.74" × 1.74")

# BUSINESS CARD - BOTTOM-LEFT (replaces RTUI logo area)
BC_X_BOTTOM = 9.2  # Shifted left by 5 pts more (was 14.2)
BC_Y_BOTTOM = 10.0
BC_WIDTH = 126.72
BC_HEIGHT = 126.72

# BUSINESS CARD - TOP-LEFT (legacy position)
BC_X_TOP = 36.0
BC_Y_TOP = 144.0

# TEXT OVERLAY - BOTTOM-CENTER (between business card and QR)
TEXT_X = 180.0
TEXT_Y = 40.0
TEXT_WIDTH = 304.0  # 484 - 180 = space between business card and QR
TEXT_HEIGHT = 100.0

# Ad image margins
AD_X_MARGIN = 36.0  # 0.5" on each side
AD_WIDTH = LETTER_WIDTH_PTS - (2 * AD_X_MARGIN)

# Direct team member info
DIRECT_TEAM = {
    "Adan Ramos": {
        "cell": "206.383.7190",
        "corporate": "800.247.4793",
        "email": "Adan.ramos@indoormedia.com",
        "landing_page": "https://www.indoormedia.com/tape-sales/advertise-with-adan-ramos/"
    },
    "Amy Dixon": {
        "cell": "562.480.6026",
        "corporate": "800.247.4793",
        "email": "Amy.Dixon@indoormedia.com",
        "landing_page": "https://www.indoormedia.com/tape-sales/advertise-with-amy-dixon/"
    },
    "Ben Patacsil": {
        "cell": "206.383.7190",
        "corporate": "800.247.4793",
        "email": "Ben.Patacsil@indoormedia.com",
        "landing_page": "https://www.indoormedia.com/tape-sales/advertise-with-ben-patacsil/"
    },
    "Christian Johnson": {
        "cell": "206.383.7190",
        "corporate": "800.247.4793",
        "email": "Christian.Johnson@indoormedia.com",
        "landing_page": "https://www.indoormedia.com/tape-sales/advertise-with-christian-johnson/"
    },
    "Dave Boring": {
        "cell": "503.522.0887",
        "corporate": "800.247.4793",
        "email": "Dave.Boring@indoormedia.com",
        "landing_page": "https://www.indoormedia.com/tape-sales/advertise-with-dave-boring/"
    },
    "Jan Banks": {
        "cell": "503.781.2505",
        "corporate": "800.247.4793",
        "email": "Jan.Banks@indoormedia.com",
        "landing_page": "https://www.indoormedia.com/tape-sales/advertise-with-jan-banks/"
    },
    "Matt Boozer": {
        "cell": "503.970.2479",
        "corporate": "800.247.4793",
        "email": "Matthew.Boozer@indoormedia.com",
        "landing_page": "https://www.indoormedia.com/tape-sales/advertise-with-matt-boozer/"
    },
    "Megan Wink": {
        "cell": "206.434.6917",
        "corporate": "800.247.4793",
        "email": "Megan.Wink@indoormedia.com",
        "landing_page": "https://www.indoormedia.com/tape-sales/advertise-with-megan-wink/"
    },
    "Marty Eng": {
        "cell": "971.732.2972",
        "corporate": "800.247.4793",
        "email": "Anthony.Eng@indoormedia.com",
        "landing_page": "https://www.indoormedia.com/tape-sales/advertise-with-marty-eng/"
    }
}


def generate_qr_code(url: str, box_size: int = 10) -> Image.Image:
    """Generate QR code image with white background."""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=box_size,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        return img
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        return None


def create_footer_text_overlay(
    text: str,
    width: int = 304,
    height: int = 100,
    font_size: int = 14
) -> Image.Image:
    """
    Create footer text overlay with white text on transparent background.
    
    Args:
        text: Text content (will be split into multiple lines)
        width: Image width in pixels (default 304 pts)
        height: Image height in pixels (default 100 pts)
        font_size: Font size in points (default 14)
    
    Returns:
        PIL Image with RGBA (transparent background)
    """
    try:
        # Create transparent background (RGBA)
        img = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Try to load Helvetica Bold
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", font_size)
            except:
                font = ImageFont.load_default()
        
        # Draw text centered, white color on transparent background
        draw.multiline_text(
            (width // 2, height // 2),
            text,
            fill=(255, 255, 255, 255),  # White with full opacity
            font=font,
            anchor="mm",
            align="center"
        )
        
        logger.info(f"✓ Created footer text overlay: {width}×{height} px, font size {font_size}")
        return img
    except Exception as e:
        logger.error(f"Error creating footer text overlay: {e}")
        return None


def resize_ad_image(image_path: str, max_width: float, max_height: float) -> Tuple[Image.Image, float, float]:
    """
    Load and resize ad image to fit within max dimensions while maintaining aspect ratio.
    
    Args:
        image_path: Path to ad image file
        max_width: Maximum width in points
        max_height: Maximum height in points
    
    Returns:
        (resized_image, final_width, final_height) in points
    """
    try:
        img = Image.open(image_path)
        
        # Calculate scaling to fit (maintain aspect ratio)
        img_ratio = img.width / img.height
        available_ratio = max_width / max_height
        
        if img_ratio > available_ratio:
            # Image is wider - fit to width
            final_width = max_width
            final_height = max_width / img_ratio
        else:
            # Image is taller - fit to height
            final_height = max_height
            final_width = final_height * img_ratio
        
        # Resize image (convert points to pixels, assuming 72 DPI)
        new_width_px = int(final_width)
        new_height_px = int(final_height)
        
        img_resized = img.resize(
            (new_width_px, new_height_px),
            Image.Resampling.LANCZOS
        )
        
        logger.info(f"Resized ad image to {final_width:.1f}×{final_height:.1f} pts ({new_width_px}×{new_height_px} px)")
        
        return img_resized, final_width, final_height
    
    except Exception as e:
        logger.error(f"Error resizing ad image: {e}")
        return None, None, None


# Full ad zone: from just above footer to below template text
# Footer top ~140 pts, Template text ("CASH REGISTER RECEIPT TAPE?") ends ~470 pts
# Use 150 to 430 as safe zone — more clearance below template text
GRID_Y_BOTTOM = 150.0   # Just above footer area
GRID_Y_TOP = 430.0       # Well below "CASH REGISTER RECEIPT TAPE?" text
GRID_HEIGHT = GRID_Y_TOP - GRID_Y_BOTTOM  # 280 pts total
GRID_GAP = 10.0          # Gap between images


def calculate_grid_positions(num_images: int) -> list:
    """
    Calculate (x, y, width, height) for each image in a 2-column grid.
    Uses the full white space between header and footer.
    
    Returns list of (x, y, cell_width, cell_height) tuples — one per image.
    y is the BOTTOM of the cell (PDF coordinate system: origin at bottom-left).
    """
    if num_images == 1:
        # Single image: centered, use most of the space
        w = AD_WIDTH * 0.85
        h = GRID_HEIGHT * 0.85
        x = AD_X_MARGIN + (AD_WIDTH - w) / 2
        y = GRID_Y_BOTTOM + (GRID_HEIGHT - h) / 2
        return [(x, y, w, h)]
    
    # 2-4 images: 2-column grid
    # 5-6 images: 3-column × 2-row grid
    if num_images <= 4:
        cols = 2
        rows = (num_images + 1) // 2
    else:
        cols = 3
        rows = 2
    
    usable_width = AD_WIDTH - (GRID_GAP * (cols - 1))
    usable_height = GRID_HEIGHT - (GRID_GAP * (rows - 1))
    
    cell_w = usable_width / cols
    cell_h = usable_height / rows
    
    positions = []
    for idx in range(num_images):
        col = idx % cols
        row = idx // cols
        
        x = AD_X_MARGIN + col * (cell_w + GRID_GAP)
        # Top row starts at top of grid, rows go downward
        y = GRID_Y_TOP - (row + 1) * cell_h - row * GRID_GAP
        
        positions.append((x, y, cell_w, cell_h))
    
    logger.info(f"Grid layout: {num_images} images → {cols} cols × {rows} rows, cell: {cell_w:.1f}×{cell_h:.1f} pts, zone: {GRID_Y_BOTTOM:.0f}-{GRID_Y_TOP:.0f}")
    
    return positions


def overlay_content_on_template(
    template_pdf_path: str,
    ad_image_paths: Optional[list] = None,
    business_card_path: Optional[str] = None,
    qr_image: Optional[Image.Image] = None,
    rep_data: Optional[Dict] = None,
    landing_page_url: Optional[str] = None,
) -> bytes:
    """
    Overlay all components on store template with EXACT positioning.
    
    FOOTER LAYOUT:
    - Bottom-left: Business card (144×144 pts at X:36, Y:22.7)
    - Bottom-right: QR code (109.9×109.9 pts, exact position)
    
    AD ZONE LAYOUT (Middle):
    - Supports 1-6 images in a 2-column grid
    - Auto-calculates grid dimensions based on image count
    - Maintains aspect ratio for each image
    
    Overlay order (important for layering):
    1. White background box (to cover original QR code)
    2. Ad images (grid layout in middle section)
    3. Business card (bottom-left)
    4. QR code (bottom-right, on white background)
    
    Args:
        ad_image_paths: List of paths to ad images (1-6)
    
    Returns PDF bytes.
    """
    try:
        # Read template
        pdf_reader = PdfReader(template_pdf_path)
        page = pdf_reader.pages[0]
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)
        
        logger.info(f"Template size: {page_width}×{page_height} pts")
        
        # Create overlay using reportlab
        overlay_buffer = io.BytesIO()
        c = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))
        
        # ========== 1. WHITE BACKGROUND FOR QR (draw first, behind QR code) ==========
        c.setFillColor(colors.white)
        c.rect(QR_BG_X_MIN, QR_BG_Y_MIN, QR_BG_SIZE, QR_BG_SIZE, fill=1, stroke=0)
        logger.info(f"✓ White background at ({QR_BG_X_MIN}, {QR_BG_Y_MIN}): {QR_BG_SIZE}×{QR_BG_SIZE} pts")
        
        # ========== 2. AD IMAGES (GRID LAYOUT) ==========
        if ad_image_paths and len(ad_image_paths) > 0:
            try:
                valid_paths = [p for p in ad_image_paths if p and Path(p).exists()]
                positions = calculate_grid_positions(len(valid_paths))
                
                for idx, ad_path in enumerate(valid_paths):
                    cell_x, cell_y, cell_w, cell_h = positions[idx]
                    
                    # Resize image to fit cell (95% to leave a tiny margin)
                    img_resized, final_width, final_height = resize_ad_image(
                        ad_path,
                        max_width=cell_w * 0.95,
                        max_height=cell_h * 0.95
                    )
                    
                    if img_resized:
                        # Center image within its cell
                        ad_x = cell_x + (cell_w - final_width) / 2
                        ad_y = cell_y + (cell_h - final_height) / 2
                        
                        # Save to temp file for reportlab
                        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                            img_resized.save(tmp.name, format='PNG')
                            c.drawImage(tmp.name, ad_x, ad_y, width=final_width, height=final_height)
                            logger.info(f"✓ Ad image #{idx+1}/{len(valid_paths)} at ({ad_x:.1f}, {ad_y:.1f}): {final_width:.1f}×{final_height:.1f} pts [cell: {cell_x:.0f},{cell_y:.0f} {cell_w:.0f}×{cell_h:.0f}]")
            except Exception as e:
                logger.warning(f"Could not add ad images: {e}")
                import traceback
                traceback.print_exc()
        
        # ========== 3. BUSINESS CARD (BOTTOM-LEFT) ==========
        if business_card_path and Path(business_card_path).exists():
            try:
                bc_img = Image.open(business_card_path)
                
                # Maintain aspect ratio, fit in 144×144 box at bottom-left
                bc_ratio = bc_img.width / bc_img.height
                if bc_ratio > 1:  # Wider
                    final_bc_width = BC_WIDTH
                    final_bc_height = BC_WIDTH / bc_ratio
                else:  # Taller
                    final_bc_height = BC_HEIGHT
                    final_bc_width = BC_HEIGHT * bc_ratio
                
                # Center in box (bottom-left position)
                bc_x = BC_X_BOTTOM + (BC_WIDTH - final_bc_width) / 2
                bc_y = BC_Y_BOTTOM + (BC_HEIGHT - final_bc_height) / 2
                
                # Use LANCZOS for high-quality resampling
                bc_img_resized = bc_img.resize(
                    (int(final_bc_width), int(final_bc_height)),
                    Image.Resampling.LANCZOS
                )
                
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    bc_img_resized.save(tmp.name, format='PNG', optimize=False)
                    c.drawImage(tmp.name, bc_x, bc_y, width=final_bc_width, height=final_bc_height)
                    logger.info(f"✓ Business card (bottom-left) at ({bc_x:.1f}, {bc_y:.1f}): {final_bc_width:.1f}×{final_bc_height:.1f} pts")
            except Exception as e:
                logger.warning(f"Could not add business card: {e}")
        
        # ========== 4. QR CODE (on top of white background) ==========
        if qr_image:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                qr_image.save(tmp.name, format='PNG')
                c.drawImage(tmp.name, QR_CODE_X_MIN, QR_CODE_Y_MIN, width=QR_CODE_SIZE, height=QR_CODE_SIZE)
                logger.info(f"✓ QR code at ({QR_CODE_X_MIN}, {QR_CODE_Y_MIN}): {QR_CODE_SIZE}×{QR_CODE_SIZE} pts")
        
        # Finalize overlay
        c.save()
        
        # Read overlay PDF
        overlay_buffer.seek(0)
        overlay_pdf = PdfReader(overlay_buffer)
        overlay_page = overlay_pdf.pages[0]
        
        # Merge overlay with template
        page.merge_page(overlay_page)
        
        # Write final PDF
        pdf_writer = PdfWriter()
        pdf_writer.add_page(page)
        for additional_page in pdf_reader.pages[1:]:
            pdf_writer.add_page(additional_page)
        
        output_buffer = io.BytesIO()
        pdf_writer.write(output_buffer)
        output_buffer.seek(0)
        
        logger.info("✓ PDF overlay complete")
        return output_buffer.getvalue()
    
    except Exception as e:
        logger.error(f"Error creating overlay PDF: {e}")
        import traceback
        traceback.print_exc()
        return None


# ======================== CLEAN TEMPLATE FOOTER ========================
# Dark red bar across the bottom with: IndoorMedia logo (left), business card (center), QR code (right)

CLEAN_FOOTER_HEIGHT = 155.0  # Taller to fully cover original footer text
CLEAN_FOOTER_Y = 0.0         # Bottom of page
CLEAN_FOOTER_COLOR = (0.6, 0.0, 0.0)  # Dark maroon/red
LOGO_PATH = Path(__file__).parent.parent / "pwa" / "public" / "logo.png"


def overlay_clean_footer(
    template_pdf_path: str,
    ad_image_paths: Optional[list] = None,
    business_card_path: Optional[str] = None,
    qr_image: Optional[Image.Image] = None,
    rep_data: Optional[Dict] = None,
    landing_page_url: Optional[str] = None,
) -> bytes:
    """
    Clean template: Same chain header + ad zone, but replaces the original footer
    with a dark red bar containing IndoorMedia logo (left), business card (center), QR code (right).
    """
    try:
        pdf_reader = PdfReader(template_pdf_path)
        page = pdf_reader.pages[0]
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)

        logger.info(f"Clean template: {page_width}×{page_height} pts")

        overlay_buffer = io.BytesIO()
        c = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))

        # ========== 1. DARK RED FOOTER BAR ==========
        c.setFillColorRGB(*CLEAN_FOOTER_COLOR)
        c.rect(0, CLEAN_FOOTER_Y, page_width, CLEAN_FOOTER_HEIGHT, fill=1, stroke=0)
        logger.info(f"✓ Clean footer bar: {page_width}×{CLEAN_FOOTER_HEIGHT} pts")

        # ========== 2. INDOORMEDIA LOGO (left) — inverted colors on dark red ==========
        logo_path = LOGO_PATH
        if logo_path.exists():
            try:
                logo_img = Image.open(str(logo_path)).convert('RGBA')
                
                # Invert: background (white/light) → transparent, colored parts → inverted
                pixels = logo_img.load()
                for py in range(logo_img.height):
                    for px in range(logo_img.width):
                        r, g, b, a = pixels[px, py]
                        if a < 30:
                            # Already transparent → keep transparent
                            continue
                        elif r > 230 and g > 230 and b > 230:
                            # White/near-white background → transparent
                            pixels[px, py] = (0, 0, 0, 0)
                        else:
                            # Colored pixel → invert it
                            pixels[px, py] = (255 - r, 255 - g, 255 - b, a)

                logo_ratio = logo_img.width / logo_img.height
                logo_h = CLEAN_FOOTER_HEIGHT * 0.55
                logo_w = logo_h * logo_ratio
                logo_x = 20
                logo_y = CLEAN_FOOTER_Y + (CLEAN_FOOTER_HEIGHT - logo_h) / 2

                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    logo_img.save(tmp.name, format='PNG')
                    c.drawImage(tmp.name, logo_x, logo_y, width=logo_w, height=logo_h, mask='auto')
                    logger.info(f"✓ Logo at ({logo_x:.0f}, {logo_y:.0f}): {logo_w:.0f}×{logo_h:.0f} (white on transparent)")
            except Exception as e:
                logger.warning(f"Could not add logo: {e}")

        # ========== 3. BUSINESS CARD (center) ==========
        if business_card_path and Path(business_card_path).exists():
            try:
                bc_img = Image.open(business_card_path)
                bc_ratio = bc_img.width / bc_img.height
                # Business card: ~45% of footer width, centered
                bc_max_w = page_width * 0.42
                bc_max_h = CLEAN_FOOTER_HEIGHT * 0.80

                if bc_ratio > bc_max_w / bc_max_h:
                    bc_w = bc_max_w
                    bc_h = bc_w / bc_ratio
                else:
                    bc_h = bc_max_h
                    bc_w = bc_h * bc_ratio

                bc_x = (page_width - bc_w) / 2
                bc_y = CLEAN_FOOTER_Y + (CLEAN_FOOTER_HEIGHT - bc_h) / 2

                bc_resized = bc_img.resize((int(bc_w * 2), int(bc_h * 2)), Image.Resampling.LANCZOS)
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    bc_resized.save(tmp.name, format='PNG')
                    c.drawImage(tmp.name, bc_x, bc_y, width=bc_w, height=bc_h)
                    logger.info(f"✓ Business card (center) at ({bc_x:.0f}, {bc_y:.0f}): {bc_w:.0f}×{bc_h:.0f}")
            except Exception as e:
                logger.warning(f"Could not add business card: {e}")

        # ========== 4. QR CODE (right) ==========
        if qr_image:
            qr_size = CLEAN_FOOTER_HEIGHT * 0.75
            qr_x = page_width - qr_size - 20
            qr_y = CLEAN_FOOTER_Y + (CLEAN_FOOTER_HEIGHT - qr_size) / 2
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                qr_image.save(tmp.name, format='PNG')
                c.drawImage(tmp.name, qr_x, qr_y, width=qr_size, height=qr_size)
                logger.info(f"✓ QR code (right) at ({qr_x:.0f}, {qr_y:.0f}): {qr_size:.0f}×{qr_size:.0f}")

        # ========== 5. AD IMAGES (same grid, but shift zone down to account for taller footer) ==========
        if ad_image_paths and len(ad_image_paths) > 0:
            try:
                valid_paths = [p for p in ad_image_paths if p and Path(p).exists()]
                # Adjust grid: bottom at footer top, top same as classic
                clean_grid_bottom = CLEAN_FOOTER_HEIGHT + 5
                clean_grid_top = 430.0
                clean_grid_height = clean_grid_top - clean_grid_bottom

                if len(valid_paths) == 1:
                    w = (page_width - 72) * 0.85
                    h = clean_grid_height * 0.85
                    positions = [((page_width - w) / 2, clean_grid_bottom + (clean_grid_height - h) / 2, w, h)]
                else:
                    cols = 2 if len(valid_paths) <= 4 else 3
                    rows = (len(valid_paths) + cols - 1) // cols
                    gap = 10
                    usable_w = (page_width - 72) - (gap * (cols - 1))
                    usable_h = clean_grid_height - (gap * (rows - 1))
                    cell_w = usable_w / cols
                    cell_h = usable_h / rows
                    positions = []
                    for idx in range(len(valid_paths)):
                        col = idx % cols
                        row = idx // cols
                        x = 36 + col * (cell_w + gap)
                        y = clean_grid_top - (row + 1) * cell_h - row * gap
                        positions.append((x, y, cell_w, cell_h))

                for idx, ad_path in enumerate(valid_paths):
                    cell_x, cell_y, cell_w, cell_h = positions[idx]
                    img_resized, fw, fh = resize_ad_image(ad_path, cell_w * 0.95, cell_h * 0.95)
                    if img_resized:
                        ad_x = cell_x + (cell_w - fw) / 2
                        ad_y = cell_y + (cell_h - fh) / 2
                        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                            img_resized.save(tmp.name, format='PNG')
                            c.drawImage(tmp.name, ad_x, ad_y, width=fw, height=fh)
                            logger.info(f"✓ Clean ad #{idx+1} at ({ad_x:.0f}, {ad_y:.0f}): {fw:.0f}×{fh:.0f}")
            except Exception as e:
                logger.warning(f"Could not add ad images: {e}")
                import traceback
                traceback.print_exc()

        c.save()

        overlay_buffer.seek(0)
        overlay_pdf = PdfReader(overlay_buffer)
        overlay_page = overlay_pdf.pages[0]

        page.merge_page(overlay_page)

        pdf_writer = PdfWriter()
        pdf_writer.add_page(page)
        for additional_page in pdf_reader.pages[1:]:
            pdf_writer.add_page(additional_page)

        output_buffer = io.BytesIO()
        pdf_writer.write(output_buffer)
        output_buffer.seek(0)

        logger.info("✓ Clean template PDF complete")
        return output_buffer.getvalue()

    except Exception as e:
        logger.error(f"Error creating clean template PDF: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_counter_sign(
    chain_code: str,
    ad_image_paths: list,
    rep_name: str,
    rep_cell: str,
    rep_email: str,
    landing_page_url: Optional[str] = None,
    business_card_path: Optional[str] = None,
    style: str = 'classic',
) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Generate counter sign with precise positioning.
    
    Args:
        chain_code: Store code (SAF, HIT, MAC, etc.)
        ad_image_paths: List of paths to ad images (1-6)
        rep_name: Representative name
        rep_cell: Cell phone number
        rep_email: Email address
        landing_page_url: Landing page URL (for QR code)
        business_card_path: Optional business card image
    
    Returns:
        (PDF bytes, output path) or (None, None) if failed
    """
    # Validate ad image paths
    if not ad_image_paths:
        logger.error("No ad images provided")
        return None, None
    
    # Filter out None/empty paths
    valid_paths = [p for p in ad_image_paths if p and Path(p).exists()]
    if not valid_paths:
        logger.error("No valid ad image paths")
        return None, None
    
    if len(valid_paths) > 6:
        logger.warning(f"Too many ad images ({len(valid_paths)}), limiting to 6")
        valid_paths = valid_paths[:6]
    
    # Find template (case-insensitive search)
    templates_dir = Path(__file__).parent.parent / "data" / "store_templates"
    template_files = list(templates_dir.glob(f"{chain_code.upper()}_CounterSign_Fillable*.pdf"))
    
    # If not found with upper(), try exact code as-is
    if not template_files:
        template_files = list(templates_dir.glob(f"{chain_code}_CounterSign_Fillable*.pdf"))
    
    # If still not found, try case-insensitive search
    if not template_files:
        chain_lower = chain_code.lower()
        template_files = [
            f for f in templates_dir.glob("*_CounterSign_Fillable*.pdf")
            if f.name.lower().startswith(chain_lower + "_")
        ]
    
    if not template_files:
        logger.error(f"No template found for {chain_code}")
        return None, None
    
    template_path = template_files[0]
    logger.info(f"Using template: {template_path.name}")
    logger.info(f"Processing {len(valid_paths)} ad image(s)")
    
    # Generate QR code
    qr_image = None
    if landing_page_url and landing_page_url.lower() != 'none':
        qr_image = generate_qr_code(landing_page_url)
    else:
        # Fall back to phone number
        if rep_cell:
            tel_url = f"tel:{rep_cell.replace(' ', '').replace('-', '').replace('.', '')}"
            qr_image = generate_qr_code(tel_url)
    
    # Prepare rep data
    rep_data = {
        'name': rep_name,
        'cell': rep_cell,
        'email': rep_email,
    }
    
    # Create overlay based on style
    if style == 'clean':
        pdf_bytes = overlay_clean_footer(
            str(template_path),
            ad_image_paths=valid_paths,
            business_card_path=business_card_path,
            qr_image=qr_image,
            rep_data=rep_data,
            landing_page_url=landing_page_url,
        )
    else:
        pdf_bytes = overlay_content_on_template(
            str(template_path),
            ad_image_paths=valid_paths,
            business_card_path=business_card_path,
            qr_image=qr_image,
            rep_data=rep_data,
            landing_page_url=landing_page_url,
        )
    
    if not pdf_bytes:
        return None, None
    
    # Save output
    output_dir = Path(__file__).parent.parent / "data" / "generated_signs"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{chain_code}_{rep_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    output_path = output_dir / filename
    
    try:
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
        logger.info(f"✓ Saved to: {output_path}")
        return pdf_bytes, str(output_path)
    except Exception as e:
        logger.error(f"Error saving PDF: {e}")
        return None, None


# Helper functions for workflow integration
def list_available_store_templates():
    """List all available store template codes as a dict."""
    store_codes = [
        "ACM", "ALB", "AMK", "AND", "ARL", "BAK", "BGE", "BGY", "BLO", "BUT", "CAR", "CMI", "COP", "CRL",
        "CSV", "CTR", "CUB", "DAN", "DAW", "DFM", "DIE", "DIL", "DIS", "FAM", "FCO", "FDC", "FDP", "FDT",
        "FES", "FFL", "FGT", "FIE", "FME", "FMK", "FMX", "FoodsCo", "FRY", "FYM", "GDI", "GER", "GIA", "GIE",
        "GMF", "GNF", "GTC", "HAG", "HAR", "HEB", "HIT", "HNB", "HRV", "HYV", "IGA", "JAY", "JOE", "JWL",
        "KKG", "KRO", "KSP", "LAF", "LIN", "LKY", "LOW", "LWS", "MAC", "MAR", "MIT", "MKF", "MKT", "MKT32",
        "MRN", "MST", "OAK", "OWK", "PAK", "PAV", "PCH", "PDF", "PET", "PIG", "PLS", "PNS", "PRC", "QFC",
        "RAL", "RAM", "RAN", "RCH", "REA", "RFP", "RIC", "RID", "ROS", "ROU", "RSM", "RUL", "SAF", "SAL",
        "SCH", "SCO", "SCT", "Sendiks", "SHM", "SHW", "SMI", "SNS", "SON", "SPR", "SRI", "STB", "STM", "SVM",
        "SVT", "TOM", "TOP", "TWY", "UNI", "VAL", "VGS", "VON", "WDM", "WHM", "WIN", "YOK"
    ]
    # Return as dict with code as both key and value for compatibility
    return {code: code for code in store_codes}


def get_direct_team_names():
    """Get list of direct team member names."""
    return list(DIRECT_TEAM.keys())


def get_direct_team_by_name(name: str) -> Optional[Dict]:
    """Get direct team member data by name."""
    return DIRECT_TEAM.get(name)


if __name__ == "__main__":
    print("Counter Sign Precise Generator - Ready for use")
