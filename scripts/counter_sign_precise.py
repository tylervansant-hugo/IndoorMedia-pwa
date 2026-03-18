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

AD_ZONE_Y_START = 110.5  # Ad zone begins here
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

# BUSINESS CARD
BC_X = 36.0
BC_Y = 144.0
BC_WIDTH = 144.0
BC_HEIGHT = 144.0

# TEXT OVERLAY
TEXT_X = 198.0
TEXT_Y = 180.0
TEXT_WIDTH = 216.0
TEXT_HEIGHT = 144.0

# Ad image margins
AD_X_MARGIN = 36.0  # 0.5" on each side
AD_WIDTH = LETTER_WIDTH_PTS - (2 * AD_X_MARGIN)


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


def create_text_overlay_image(
    text: str,
    width: int = 216,
    height: int = 144,
    font_size: int = 14,
    bg_color: str = 'white',
    text_color: str = 'black'
) -> Image.Image:
    """Create text overlay image with specified dimensions."""
    try:
        img = Image.new('RGB', (width, height), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        # Try to use a bold font
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", font_size)
            except:
                font = ImageFont.load_default()
        
        # Draw centered text
        draw.multiline_text(
            (width // 2, height // 2),
            text,
            fill=text_color,
            font=font,
            anchor="mm",
            align="center"
        )
        
        return img
    except Exception as e:
        logger.error(f"Error creating text overlay: {e}")
        return None


def resize_ad_image(image_path: str) -> Tuple[Image.Image, float, float]:
    """
    Load and resize ad image to fit the middle section perfectly.
    
    The ad image must fit:
    - Width: 540 pts (612 - 36*2 margins)
    - Height: 493 pts (from Y 110.5 to 603.5)
    
    Returns:
        (resized_image, final_width, final_height) in points
    """
    try:
        img = Image.open(image_path)
        
        # Available space (in points)
        max_width = AD_WIDTH
        max_height = AD_ZONE_HEIGHT
        
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
    
    Overlay order (important for layering):
    1. White background box (to cover original QR code)
    2. Ad image (fills middle section)
    3. Business card (bottom-left)
    4. Text overlay (bottom-center)
    5. QR code (bottom-right, on white background)
    6. Rep info text (corner info)
    
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
        
        # ========== 2. AD IMAGE (fills middle section) ==========
        if ad_image_path:
            try:
                img_resized, final_width, final_height = resize_ad_image(ad_image_path)
                
                if img_resized:
                    # Center horizontally, position in ad zone
                    ad_x = AD_X_MARGIN + (AD_WIDTH - final_width) / 2
                    ad_y = AD_ZONE_Y_START + (AD_ZONE_HEIGHT - final_height) / 2
                    
                    # Save to temp file for reportlab
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        img_resized.save(tmp.name, format='PNG')
                        c.drawImage(tmp.name, ad_x, ad_y, width=final_width, height=final_height)
                        logger.info(f"✓ Ad image at ({ad_x:.1f}, {ad_y:.1f}): {final_width:.1f}×{final_height:.1f} pts")
            except Exception as e:
                logger.warning(f"Could not add ad image: {e}")
        
        # ========== 3. BUSINESS CARD ==========
        if business_card_path:
            try:
                bc_img = Image.open(business_card_path)
                
                # Maintain aspect ratio, fit in box
                bc_ratio = bc_img.width / bc_img.height
                if bc_ratio > 1:  # Wider
                    final_bc_width = BC_WIDTH
                    final_bc_height = BC_WIDTH / bc_ratio
                else:  # Taller
                    final_bc_height = BC_HEIGHT
                    final_bc_width = BC_HEIGHT * bc_ratio
                
                # Center in box
                bc_x = BC_X + (BC_WIDTH - final_bc_width) / 2
                bc_y = BC_Y + (BC_HEIGHT - final_bc_height) / 2
                
                bc_img_resized = bc_img.resize(
                    (int(final_bc_width), int(final_bc_height)),
                    Image.Resampling.LANCZOS
                )
                
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    bc_img_resized.save(tmp.name, format='PNG')
                    c.drawImage(tmp.name, bc_x, bc_y, width=final_bc_width, height=final_bc_height)
                    logger.info(f"✓ Business card at ({bc_x:.1f}, {bc_y:.1f}): {final_bc_width:.1f}×{final_bc_height:.1f} pts")
            except Exception as e:
                logger.warning(f"Could not add business card: {e}")
        
        # ========== 4. TEXT OVERLAY ==========
        if landing_page_url and landing_page_url.lower() != 'none':
            text_content = "SCAN HERE TO\nSEE HOW WE CAN\nHELP YOUR\nBUSINESS"
        else:
            text_content = "CALL NOW TO\nSEE HOW WE CAN\nHELP YOUR\nBUSINESS"
        
        text_img = create_text_overlay_image(text_content, int(TEXT_WIDTH), int(TEXT_HEIGHT), 14)
        if text_img:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                text_img.save(tmp.name, format='PNG')
                c.drawImage(tmp.name, TEXT_X, TEXT_Y, width=TEXT_WIDTH, height=TEXT_HEIGHT)
                logger.info(f"✓ Text overlay at ({TEXT_X}, {TEXT_Y}): {TEXT_WIDTH}×{TEXT_HEIGHT} pts")
        
        # ========== 5. QR CODE (on top of white background) ==========
        if qr_image:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                qr_image.save(tmp.name, format='PNG')
                # Draw QR code at exact original position
                c.drawImage(tmp.name, QR_CODE_X_MIN, QR_CODE_Y_MIN, width=QR_CODE_SIZE, height=QR_CODE_SIZE)
                logger.info(f"✓ QR code at ({QR_CODE_X_MIN}, {QR_CODE_Y_MIN}): {QR_CODE_SIZE}×{QR_CODE_SIZE} pts (EXACT)")
        
        # ========== 6. REP INFO TEXT ==========
        if rep_data:
            try:
                c.setFont("Helvetica-Bold", 10)
                c.drawString(36, 30, rep_data.get('name', 'Rep Name'))
                
                c.setFont("Helvetica", 8)
                c.drawString(36, 20, f"Cell: {rep_data.get('cell', '')}")
                c.drawString(36, 10, f"Email: {rep_data.get('email', '')}")
                
                logger.info(f"✓ Rep info for {rep_data.get('name', 'Unknown')}")
            except Exception as e:
                logger.warning(f"Could not add rep info: {e}")
        
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


if __name__ == "__main__":
    print("Counter Sign Precise Generator - Ready for use")
