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


def create_call_now_image(width: int = 300, height: int = 300) -> Image.Image:
    """
    Create an image with "CALL NOW TO SEE HOW WE CAN HELP YOUR BUSINESS" text.
    Used when no landing page URL is provided.
    """
    try:
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to use a nice font, fall back to default if unavailable
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
            small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
        except:
            font = ImageFont.load_default()
            small_font = font
        
        # Add border
        draw.rectangle(
            [5, 5, width - 5, height - 5],
            outline='black',
            width=3
        )
        
        # Add text
        text = "CALL NOW\nTO SEE HOW WE\nCAN HELP YOUR\nBUSINESS"
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
        logger.error(f"Error creating CALL NOW image: {e}")
        return None


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


def overlay_content_on_template(
    template_pdf_path: str,
    ad_image_path: Optional[str] = None,
    qr_image: Optional[Image.Image] = None,
    rep_data: Optional[Dict] = None,
) -> bytes:
    """
    Overlay ad image, QR code, and rep info onto a store template PDF.
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
        
        # Set up positions (in points)
        # Middle section: approximately 2.5" to 8.5" from top (for ad image)
        ad_top = page_height - (2.5 * inch)
        ad_bottom = 3 * inch  # Leave 3" at bottom for rep info and QR
        ad_height = ad_top - ad_bottom
        ad_width = page_width - (0.5 * inch * 2)  # 0.5" margins
        
        # Add ad image in center
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
        
        # Add QR code (bottom right)
        if qr_image:
            try:
                qr_size = 1.5 * inch  # 1.5" x 1.5" QR code
                qr_x = page_width - qr_size - (0.25 * inch)
                qr_y = 0.25 * inch
                
                # Save QR to temp file
                import tempfile
                qr_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                qr_path = qr_file.name
                qr_file.close()
                qr_image.save(qr_path, format='PNG')
                
                overlay_canvas.drawImage(
                    qr_path,
                    qr_x,
                    qr_y,
                    width=qr_size,
                    height=qr_size
                )
                logger.info(f"Added QR code at ({qr_x}, {qr_y})")
            except Exception as e:
                logger.warning(f"Could not add QR code: {e}")
        
        # Add rep info (bottom left)
        if rep_data:
            try:
                info_x = 0.25 * inch
                info_y = 0.25 * inch
                line_height = 10
                
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
    store_name: Optional[str] = None,
) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Generate a complete counter sign PDF.
    
    Args:
        chain_code: Store chain code (e.g., 'SAF')
        ad_image_path: Path to ad image (JPG/PNG)
        rep_data: Dict with keys: name, cell, corporate, email
        landing_page_url: Landing page URL or None (defaults to DIRECT_TEAM if available)
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
        # Create CALL NOW image
        qr_image = create_call_now_image()
    
    # Create overlay
    pdf_bytes = overlay_content_on_template(
        str(template_path),
        ad_image_path=ad_image_path,
        qr_image=qr_image,
        rep_data=rep_data,
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
