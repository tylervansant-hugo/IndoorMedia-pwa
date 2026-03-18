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

AD_ZONE_Y_START = 157.9  # Ad zone begins here (footer_top 140.2 + 17.7 pt margin)
AD_ZONE_Y_END = 603.5    # Ad zone ends (where header starts)
AD_ZONE_HEIGHT = AD_ZONE_Y_END - AD_ZONE_Y_START

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
BC_X_BOTTOM = 17.7
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


def resize_ad_image(image_path: str, scale: float = 0.75) -> Tuple[Image.Image, float, float]:
    """
    Load and resize ad image to fit the middle section perfectly.
    
    The ad image fits within:
    - Width: 540 pts (612 - 36*2 margins)
    - Height: 493 pts (from Y 110.5 to 603.5)
    - Scale: 0.75 (default, 25% smaller for white space around edges)
    
    Args:
        image_path: Path to ad image file
        scale: Scale factor (default 0.75 = 25% reduction)
    
    Returns:
        (resized_image, final_width, final_height) in points
    """
    try:
        img = Image.open(image_path)
        
        # Available space (in points)
        max_width = AD_WIDTH * scale  # Apply scale
        max_height = AD_ZONE_HEIGHT * scale  # Apply scale
        
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
        
        logger.info(f"Resized ad image to {final_width:.1f}×{final_height:.1f} pts ({new_width_px}×{new_height_px} px) at {scale*100:.0f}% scale")
        
        return img_resized, final_width, final_height
    
    except Exception as e:
        logger.error(f"Error resizing ad image: {e}")
        return None, None, None


def overlay_content_on_template(
    template_pdf_path: str,
    ad_image_path: Optional[str] = None,
    business_card_path: Optional[str] = None,
    qr_image: Optional[Image.Image] = None,
    rep_data: Optional[Dict] = None,
    landing_page_url: Optional[str] = None,
) -> bytes:
    """
    Overlay all components on store template with EXACT positioning.
    
    FOOTER LAYOUT (updated):
    - Bottom-left: Business card (144×144 pts at X:36, Y:22.7)
    - Bottom-center: White text on transparent background, no white box
      - "SCAN HERE TO SEE HOW WE CAN HELP YOUR BUSINESS" (if landing_page_url)
      - "CALL NOW TO SEE HOW WE CAN HELP YOUR BUSINESS" (if no landing_page_url)
    - Bottom-right: QR code (109.9×109.9 pts, unchanged position)
    
    Overlay order (important for layering):
    1. White background box (to cover original QR code)
    2. Ad image (fills middle section)
    3. Business card (bottom-left)
    4. Text overlay (bottom-center, white on transparent)
    5. QR code (bottom-right, on white background)
    
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
        
        # ========== 2. AD IMAGE (shrunk 25%, centered in zone) ==========
        if ad_image_path:
            try:
                # Apply 0.75 scale (25% smaller = 405×369.75 pts from original 540×493)
                img_resized, final_width, final_height = resize_ad_image(ad_image_path, scale=0.75)
                
                if img_resized:
                    # Center horizontally and vertically in ad zone
                    ad_x = AD_X_MARGIN + (AD_WIDTH - final_width) / 2
                    ad_y = AD_ZONE_Y_START + (AD_ZONE_HEIGHT - final_height) / 2
                    
                    # Save to temp file for reportlab
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        img_resized.save(tmp.name, format='PNG')
                        c.drawImage(tmp.name, ad_x, ad_y, width=final_width, height=final_height)
                        logger.info(f"✓ Ad image (25% smaller, centered) at ({ad_x:.1f}, {ad_y:.1f}): {final_width:.1f}×{final_height:.1f} pts")
            except Exception as e:
                logger.warning(f"Could not add ad image: {e}")
        
        # ========== 3. BUSINESS CARD (BOTTOM-LEFT) ==========
        if business_card_path:
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
                
                bc_img_resized = bc_img.resize(
                    (int(final_bc_width), int(final_bc_height)),
                    Image.Resampling.LANCZOS
                )
                
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    bc_img_resized.save(tmp.name, format='PNG')
                    c.drawImage(tmp.name, bc_x, bc_y, width=final_bc_width, height=final_bc_height)
                    logger.info(f"✓ Business card (bottom-left) at ({bc_x:.1f}, {bc_y:.1f}): {final_bc_width:.1f}×{final_bc_height:.1f} pts")
            except Exception as e:
                logger.warning(f"Could not add business card: {e}")
        
        # ========== 4. FOOTER TEXT OVERLAY (REMOVED) ==========
        # Footer text overlay removed per user request - original template footer text preserved
        logger.info(f"✓ Footer text overlay removed - original template footer text retained")
        
        # ========== 5. QR CODE (on top of white background) ==========
        if qr_image:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                qr_image.save(tmp.name, format='PNG')
                # Draw QR code at exact original position
                c.drawImage(tmp.name, QR_CODE_X_MIN, QR_CODE_Y_MIN, width=QR_CODE_SIZE, height=QR_CODE_SIZE)
                logger.info(f"✓ QR code at ({QR_CODE_X_MIN}, {QR_CODE_Y_MIN}): {QR_CODE_SIZE}×{QR_CODE_SIZE} pts (EXACT)")
        
        # ========== 6. REP INFO (REMOVED - no longer displayed in footer) ==========
        # Rep contact info is now only used for QR code generation
        # Text-based rep info display in footer has been removed
        
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


def generate_counter_sign(
    chain_code: str,
    ad_image_path: str,
    rep_name: str,
    rep_cell: str,
    rep_email: str,
    landing_page_url: Optional[str] = None,
    business_card_path: Optional[str] = None,
) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Generate counter sign with precise positioning.
    
    Args:
        chain_code: Store code (SAF, HIT, MAC, etc.)
        ad_image_path: Path to ad image
        rep_name: Representative name
        rep_cell: Cell phone number
        rep_email: Email address
        landing_page_url: Landing page URL (for QR code)
        business_card_path: Optional business card image
    
    Returns:
        (PDF bytes, output path) or (None, None) if failed
    """
    # Find template
    templates_dir = Path(__file__).parent.parent / "data" / "store_templates"
    template_files = list(templates_dir.glob(f"{chain_code.upper()}_CounterSign_Fillable*.pdf"))
    
    if not template_files:
        logger.error(f"No template found for {chain_code}")
        return None, None
    
    template_path = template_files[0]
    logger.info(f"Using template: {template_path.name}")
    
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
    
    # Create overlay
    pdf_bytes = overlay_content_on_template(
        str(template_path),
        ad_image_path=ad_image_path,
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
