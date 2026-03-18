#!/usr/bin/env python3
"""
Counter Sign Generator - PDF generation with ad overlay, QR codes, and rep info
Handles 8.5×11" counter signs for IndoorMedia retail partners
"""

import json
import logging
import os
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

# Constants
LETTER_WIDTH = 8.5 * inch
LETTER_HEIGHT = 11 * inch
DPI = 72  # Points per inch for PDF

# Direct team rep data
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


def get_store_templates_dir() -> Path:
    """Get the store templates directory path."""
    return Path(__file__).parent.parent / "data" / "store_templates"


def get_generated_signs_dir() -> Path:
    """Get the generated signs output directory."""
    return Path(__file__).parent.parent / "data" / "generated_signs"


def find_store_template(chain_code: str) -> Optional[Path]:
    """
    Find a store template PDF by chain code.
    Chain code should be 3 letters (e.g., 'SAF' for Safeway).
    Returns the first matching template file.
    """
    templates_dir = get_store_templates_dir()
    if not templates_dir.exists():
        logger.error(f"Store templates directory not found: {templates_dir}")
        return None
    
    # Look for files matching pattern: [CODE]_CounterSign_Fillable.pdf
    pattern = f"{chain_code.upper()}_CounterSign_Fillable"
    
    for pdf_file in templates_dir.glob("*.pdf"):
        if pattern in pdf_file.name:
            return pdf_file
    
    # If no exact match, try case-insensitive
    for pdf_file in templates_dir.glob("*.pdf"):
        if pdf_file.name.upper().startswith(chain_code.upper() + "_"):
            return pdf_file
    
    logger.warning(f"No template found for chain code: {chain_code}")
    return None


def load_store_template(chain_code: str) -> Optional[PdfReader]:
    """Load a store template PDF by chain code."""
    template_path = find_store_template(chain_code)
    if not template_path:
        logger.error(f"Template not found for chain code: {chain_code}")
        return None
    
    try:
        return PdfReader(template_path)
    except Exception as e:
        logger.error(f"Error loading template {template_path}: {e}")
        return None


def generate_qr_code(url: str, box_size: int = 10) -> Image.Image:
    """
    Generate a QR code image pointing to the given URL.
    Returns a PIL Image object.
    """
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
        logger.error(f"Error generating QR code for URL {url}: {e}")
        return None


def create_text_overlay_image(text: str, width: int = 216, height: int = 144, font_size: int = 16) -> Image.Image:
    """
    Create a text overlay image with white background and black bold text.
    Used for "SCAN HERE..." or "CALL NOW..." text overlays.
    
    Args:
        text: Text to display
        width: Width in points (PDF units)
        height: Height in points (PDF units)
        font_size: Font size in points
    
    Returns:
        PIL Image object
    """
    try:
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to use a bold font, fall back if unavailable
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", font_size)
            except:
                font = ImageFont.load_default()
        
        # Draw text centered on white background
        draw.multiline_text(
            (width // 2, height // 2),
            text,
            fill='black',
            font=font,
            anchor="mm",
            align="center"
        )
        
        return img
    except Exception as e:
        logger.error(f"Error creating text overlay image: {e}")
        return None


def create_call_now_image(width: int = 300, height: int = 300) -> Image.Image:
    """
    Create an image with "CALL NOW TO SEE HOW WE CAN HELP YOUR BUSINESS" text.
    Used when no landing page URL is provided.
    """
    return create_text_overlay_image(
        "CALL NOW\nTO SEE HOW WE\nCAN HELP YOUR\nBUSINESS",
        width=width,
        height=height,
        font_size=20
    )


def resize_image_to_fit(image_path: str, max_width: float, max_height: float) -> Image.Image:
    """
    Load and resize an image to fit within given dimensions while maintaining aspect ratio.
    Dimensions in points (1/72 inch).
    """
    try:
        img = Image.open(image_path)
        
        # Convert points to pixels (assuming 72 DPI)
        max_w_px = int(max_width)
        max_h_px = int(max_height)
        
        # Calculate scaling to fit
        ratio = min(max_w_px / img.width, max_h_px / img.height)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        
        img.thumbnail(new_size, Image.Resampling.LANCZOS)
        return img
    except Exception as e:
        logger.error(f"Error resizing image {image_path}: {e}")
        return None


def overlay_business_card_on_canvas(
    canvas_obj,
    business_card_path: str,
    position_x: float,
    position_y: float,
    width: float,
    height: float,
) -> bool:
    """
    Add business card image to a reportlab canvas at specified position.
    
    Args:
        canvas_obj: reportlab canvas object
        business_card_path: Path to business card image
        position_x: X coordinate (in points)
        position_y: Y coordinate (in points)
        width: Width (in points, ~2")
        height: Height (in points, ~2")
    
    Returns:
        True if successful, False otherwise
    """
    try:
        img = Image.open(business_card_path)
        
        # Maintain aspect ratio
        img_ratio = img.width / img.height
        available_ratio = width / height
        
        if img_ratio > available_ratio:
            # Image is wider
            new_width = width
            new_height = width / img_ratio
        else:
            # Image is taller
            new_height = height
            new_width = height * img_ratio
        
        # Center within the available space
        centered_x = position_x + (width - new_width) / 2
        centered_y = position_y + (height - new_height) / 2
        
        # Resize image
        img_resized = img.resize(
            (int(new_width), int(new_height)),
            Image.Resampling.LANCZOS
        )
        
        # Save to temp file for reportlab
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        temp_path = temp_file.name
        temp_file.close()
        img_resized.save(temp_path, format='PNG')
        
        # Draw on canvas
        canvas_obj.drawImage(
            temp_path,
            centered_x,
            centered_y,
            width=new_width,
            height=new_height
        )
        
        logger.info(f"Added business card at ({centered_x}, {centered_y}): {new_width}x{new_height}")
        return True
    
    except Exception as e:
        logger.error(f"Error overlaying business card: {e}")
        return False


def overlay_qr_code_on_canvas(
    canvas_obj,
    page_width: float,
    page_height: float,
    qr_image: Image.Image,
    position_x: float,
    position_y: float,
    qr_size: float,
    bg_size: float,
) -> bool:
    """
    Add QR code with white background overlay to canvas.
    White background is drawn first to cover original content.
    
    Args:
        canvas_obj: reportlab canvas object
        page_width: Page width (in points)
        page_height: Page height (in points)
        qr_image: PIL Image object of QR code
        position_x: X coordinate for QR code (in points)
        position_y: Y coordinate for QR code (in points)
        qr_size: QR code size (in points, ~1.5")
        bg_size: White background size (in points, ~1.8")
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Draw white background rectangle FIRST to cover original QR code
        bg_x = position_x - (bg_size - qr_size) / 2
        bg_y = position_y - (bg_size - qr_size) / 2
        
        canvas_obj.setFillColor(colors.white)
        canvas_obj.rect(bg_x, bg_y, bg_size, bg_size, fill=1, stroke=0)
        logger.info(f"Added white background for QR at ({bg_x}, {bg_y}): {bg_size}x{bg_size}")
        
        # Now draw QR code on top of white background
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        temp_path = temp_file.name
        temp_file.close()
        qr_image.save(temp_path, format='PNG')
        
        canvas_obj.drawImage(
            temp_path,
            position_x,
            position_y,
            width=qr_size,
            height=qr_size
        )
        
        logger.info(f"Added QR code at ({position_x}, {position_y}): {qr_size}x{qr_size}")
        return True
    
    except Exception as e:
        logger.error(f"Error overlaying QR code: {e}")
        return False


def overlay_text_on_canvas(
    canvas_obj,
    text_image: Image.Image,
    position_x: float,
    position_y: float,
    width: float,
    height: float,
) -> bool:
    """
    Add text overlay image to canvas.
    
    Args:
        canvas_obj: reportlab canvas object
        text_image: PIL Image object with text
        position_x: X coordinate (in points)
        position_y: Y coordinate (in points)
        width: Width (in points)
        height: Height (in points)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        temp_path = temp_file.name
        temp_file.close()
        text_image.save(temp_path, format='PNG')
        
        canvas_obj.drawImage(
            temp_path,
            position_x,
            position_y,
            width=width,
            height=height
        )
        
        logger.info(f"Added text overlay at ({position_x}, {position_y}): {width}x{height}")
        return True
    
    except Exception as e:
        logger.error(f"Error overlaying text: {e}")
        return False


def overlay_content_on_template(
    template_pdf_path: str,
    ad_image_path: Optional[str] = None,
    business_card_path: Optional[str] = None,
    qr_image: Optional[Image.Image] = None,
    rep_data: Optional[Dict] = None,
    landing_page_url: Optional[str] = None,
) -> bytes:
    """
    Overlay ad image, business card, QR code, text, and rep info onto a store template PDF.
    Layout (8.5" × 11" = 612 × 792 points):
    - Bottom-left: Business card (~2" × 2")
    - Middle-right: Text overlay (~3" × 2")
    - Bottom-right: QR code with white background (~1.5" × 1.5" with 1.8" × 1.8" white bg)
    - Top/Middle: Ad image
    - Bottom-left corner: Rep info text
    
    Returns PDF bytes.
    """
    try:
        # Read the template
        pdf_reader = PdfReader(template_pdf_path)
        
        # Get first page dimensions
        first_page = pdf_reader.pages[0]
        page_width = float(first_page.mediabox.width)
        page_height = float(first_page.mediabox.height)
        
        logger.info(f"Template page size: {page_width} x {page_height}")
        
        # Create overlay PDF using reportlab
        overlay_buffer = io.BytesIO()
        overlay_canvas = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))
        
        # ========== LAYOUT COORDINATES (in points) ==========
        # Bottom-left (business card): ~2" × 2"
        bc_x = 36  # 0.5" margin = 36 pts
        bc_y = 144  # 2" from bottom = 144 pts
        bc_width = 144  # ~2" = 144 pts
        bc_height = 144  # ~2" = 144 pts
        
        # Middle-right (text overlay): ~3" × 2"
        text_x = 198  # ~2.75" from left (bottom-center)
        text_y = 180  # ~2.5" from bottom
        text_width = 216  # ~3" = 216 pts
        text_height = 144  # ~2" = 144 pts
        
        # Bottom-right (QR code): ~1.5" × 1.5" with 1.8" × 1.8" white background
        qr_size = 120  # ~1.5" for actual QR code
        qr_bg_size = 144  # ~1.8" for white background
        qr_x = 432  # ~6" from left, center QR in white bg
        qr_y = 108  # ~1.5" from bottom, center QR in white bg
        
        # Ad image section (middle/top area)
        ad_top = page_height - (2.5 * inch)
        ad_bottom = 3.5 * inch  # Leave space for bottom overlays
        ad_height = ad_top - ad_bottom
        ad_width = page_width - (0.5 * inch * 2)
        
        # ========== OVERLAY BUSINESS CARD ==========
        if business_card_path:
            overlay_business_card_on_canvas(
                overlay_canvas,
                business_card_path,
                bc_x,
                bc_y,
                bc_width,
                bc_height
            )
        
        # ========== OVERLAY TEXT ==========
        if qr_image or rep_data:
            # Determine which text to use
            if landing_page_url and landing_page_url.lower() != 'none':
                text_content = "SCAN HERE TO\nSEE HOW WE CAN\nHELP YOUR\nBUSINESS"
            else:
                text_content = "CALL NOW TO\nSEE HOW WE CAN\nHELP YOUR\nBUSINESS"
            
            text_img = create_text_overlay_image(text_content, int(text_width), int(text_height), 14)
            if text_img:
                overlay_text_on_canvas(
                    overlay_canvas,
                    text_img,
                    text_x,
                    text_y,
                    text_width,
                    text_height
                )
        
        # ========== OVERLAY QR CODE WITH WHITE BACKGROUND ==========
        if qr_image:
            overlay_qr_code_on_canvas(
                overlay_canvas,
                page_width,
                page_height,
                qr_image,
                qr_x,
                qr_y,
                qr_size,
                qr_bg_size
            )
        
        # ========== OVERLAY AD IMAGE ==========
        if ad_image_path:
            try:
                ad_img = Image.open(ad_image_path)
                
                # Scale to fit
                img_ratio = ad_img.width / ad_img.height
                available_ratio = ad_width / ad_height
                
                if img_ratio > available_ratio:
                    # Image is wider, fit to width
                    new_width = ad_width
                    new_height = new_width / img_ratio
                else:
                    # Image is taller, fit to height
                    new_height = ad_height
                    new_width = new_height * img_ratio
                
                # Save resized image to temp file for reportlab
                ad_img_resized = ad_img.resize(
                    (int(new_width), int(new_height)),
                    Image.Resampling.LANCZOS
                )
                
                # Create temp file
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                temp_path = temp_file.name
                temp_file.close()
                ad_img_resized.save(temp_path, format='PNG')
                
                # Calculate centered position
                x = (page_width - new_width) / 2
                y = ad_bottom + (ad_height - new_height) / 2
                
                overlay_canvas.drawImage(
                    temp_path,
                    x,
                    y,
                    width=new_width,
                    height=new_height
                )
                logger.info(f"Added ad image at ({x}, {y}): {new_width}x{new_height}")
            except Exception as e:
                logger.warning(f"Could not add ad image: {e}")
        
        # ========== ADD REP INFO TEXT ==========
        if rep_data:
            try:
                info_x = 36  # 0.5" margin
                info_y = 18  # Just above bottom
                
                # Set up text
                overlay_canvas.setFont("Helvetica-Bold", 10)
                overlay_canvas.drawString(info_x, info_y + 30, rep_data.get('name', 'Rep Name'))
                
                overlay_canvas.setFont("Helvetica", 8)
                overlay_canvas.drawString(info_x, info_y + 20, f"Cell: {rep_data.get('cell', '')}")
                overlay_canvas.drawString(info_x, info_y + 10, f"Email: {rep_data.get('email', '')}")
                overlay_canvas.drawString(info_x, info_y, f"Corporate: {rep_data.get('corporate', '')}")
                
                logger.info(f"Added rep info for {rep_data.get('name', 'Unknown')}")
            except Exception as e:
                logger.warning(f"Could not add rep info: {e}")
        
        # Finish overlay canvas
        overlay_canvas.save()
        
        # Read overlay PDF
        overlay_buffer.seek(0)
        overlay_pdf = PdfReader(overlay_buffer)
        overlay_page = overlay_pdf.pages[0]
        
        # Merge overlay with template
        pdf_writer = PdfWriter()
        for page_num, page in enumerate(pdf_reader.pages):
            if page_num == 0:
                page.merge_page(overlay_page)
            pdf_writer.add_page(page)
        
        # Write final PDF to bytes
        output_buffer = io.BytesIO()
        pdf_writer.write(output_buffer)
        output_buffer.seek(0)
        
        return output_buffer.getvalue()
    
    except Exception as e:
        logger.error(f"Error creating overlay PDF: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_counter_sign(
    chain_code: str,
    ad_image_path: str,
    rep_data: Dict,
    landing_page_url: Optional[str] = None,
    business_card_path: Optional[str] = None,
    store_name: Optional[str] = None,
) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Generate a complete counter sign PDF with overlays.
    
    Args:
        chain_code: Store chain code (e.g., 'SAF')
        ad_image_path: Path to ad image (JPG/PNG)
        rep_data: Dict with keys: name, cell, corporate, email
        landing_page_url: Landing page URL or "none" (defaults to DIRECT_TEAM if available)
        business_card_path: Path to rep business card image (optional)
        store_name: Optional store name for output filename
    
    Returns:
        Tuple of (PDF bytes, output filename)
    """
    # Find template
    template_path = find_store_template(chain_code)
    if not template_path:
        logger.error(f"No template found for chain code: {chain_code}")
        return None, None
    
    # Determine landing page URL
    original_landing_page = landing_page_url
    if landing_page_url is None:
        # Try to look up in DIRECT_TEAM by rep name
        rep_name = rep_data.get('name', '')
        if rep_name in DIRECT_TEAM:
            landing_page_url = DIRECT_TEAM[rep_name].get('landing_page')
    
    # Generate QR code
    qr_image = None
    if landing_page_url and landing_page_url.lower() != 'none':
        qr_image = generate_qr_code(landing_page_url)
    else:
        # Create QR code from phone number (tel: link)
        rep_phone = rep_data.get('cell', rep_data.get('phone', ''))
        if rep_phone:
            tel_url = f"tel:{rep_phone.replace(' ', '').replace('-', '').replace('.', '')}"
            qr_image = generate_qr_code(tel_url)
        else:
            logger.warning("No landing page or phone number available for QR code")
            qr_image = None
    
    # Create overlay with all components
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
    
    # Generate output filename
    rep_name = rep_data.get('name', 'unknown').replace(' ', '_')
    if store_name:
        filename = f"{chain_code}_{store_name}_{rep_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    else:
        filename = f"{chain_code}_{rep_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    # Create output directory
    output_dir = get_generated_signs_dir() / rep_name / chain_code
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / filename
    
    # Save PDF
    try:
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
        logger.info(f"Saved counter sign to: {output_path}")
        return pdf_bytes, str(output_path)
    except Exception as e:
        logger.error(f"Error saving PDF: {e}")
        return None, None


def list_available_store_templates() -> Dict[str, str]:
    """
    List all available store templates and their chain codes.
    Returns dict of {chain_code: template_path}
    """
    templates_dir = get_store_templates_dir()
    chains = {}
    
    if not templates_dir.exists():
        logger.error(f"Templates directory not found: {templates_dir}")
        return chains
    
    for pdf_file in templates_dir.glob("*_CounterSign_Fillable*.pdf"):
        # Extract chain code from filename (first part before underscore)
        parts = pdf_file.name.split('_')
        if parts:
            chain_code = parts[0]
            if chain_code not in chains:
                chains[chain_code] = str(pdf_file)
    
    return chains


def get_direct_team_by_name(rep_name: str) -> Optional[Dict]:
    """Get direct team member data by name."""
    return DIRECT_TEAM.get(rep_name)


def get_direct_team_names() -> list:
    """Get list of direct team member names."""
    return list(DIRECT_TEAM.keys())


if __name__ == "__main__":
    # Test: List available templates
    templates = list_available_store_templates()
    print(f"Found {len(templates)} store templates")
    for code in sorted(templates.keys())[:5]:
        print(f"  {code}: {templates[code]}")
