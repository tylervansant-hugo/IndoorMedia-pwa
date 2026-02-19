#!/usr/bin/env python3
"""
Calendar Sales Prep Pipeline
Scans Google Calendar for upcoming business meetings, generates testimonial
packages, and emails them to IndoorMedia reps.

Usage:
  python3 scripts/calendar_sales_prep.py              # Scan next 48h, process new events
  python3 scripts/calendar_sales_prep.py --dry-run     # Show what would be sent
  python3 scripts/calendar_sales_prep.py --hours 72    # Custom lookahead window
"""

import json
import subprocess
import re
import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
TRACKING_FILE = WORKSPACE / 'data' / 'calendar_prep_sent.json'
TESTIMONIAL_PICKER = WORKSPACE / 'skills' / 'testimonial-picker' / 'scripts' / 'testimonial_picker.py'

INDOORMEDIA_DOMAINS = {'indoormedia.com', 'rtui.com'}
TYLER_EMAIL = 'tyler.vansant@indoormedia.com'

# Internal meeting keywords — skip these
INTERNAL_KEYWORDS = [
    'team kick-off', 'kick off', 'kickoff', 'team meeting', 'standup',
    'stand-up', 'one-on-one', '1:1', 'training', 'audit', 'aging report',
    'check aging', 'basketball', 'garbage', 'trash', 'pick up kids',
    'doctor', 'dentist', 'lunch break',
]

# Business name inference: name → likely type
BUSINESS_TYPE_HINTS = {
    # Mexican
    'mexico': 'mexican restaurant', 'mexican': 'mexican restaurant',
    'taqueria': 'mexican restaurant', 'taco': 'mexican restaurant',
    'burrito': 'mexican restaurant', 'cielito': 'mexican restaurant',
    'jalisco': 'mexican restaurant', 'guadalajara': 'mexican restaurant',
    'azteca': 'mexican restaurant', 'cancun': 'mexican restaurant',
    'fiesta': 'mexican restaurant', 'el ': 'mexican restaurant',
    'la ': 'mexican restaurant', 'los ': 'mexican restaurant',
    'vaquero': 'mexican restaurant',
    # Pizza
    'pizza': 'pizza place', 'pizzeria': 'pizza place',
    'pie ': 'pizza place', 'crust': 'pizza place',
    # Asian
    'chinese': 'chinese restaurant', 'wok': 'chinese restaurant',
    'panda': 'chinese restaurant', 'dragon': 'chinese restaurant',
    'thai': 'thai restaurant', 'sushi': 'japanese restaurant',
    'teriyaki': 'japanese restaurant', 'pho': 'vietnamese restaurant',
    'korea': 'korean restaurant', 'kim': 'korean restaurant',
    'kitchen': 'restaurant',  # generic but common
    # American / general
    'grill': 'restaurant', 'cafe': 'cafe', 'coffee': 'coffee shop',
    'diner': 'restaurant', 'bar ': 'restaurant', 'pub': 'restaurant',
    'brew': 'brewery', 'wing': 'restaurant',
    # Auto
    'auto': 'auto service', 'car wash': 'car wash', 'lube': 'oil change',
    'tire': 'tire shop', 'mechanic': 'auto repair', 'fuel': 'fuel station',
    'gas ': 'gas station',
    # Beauty
    'salon': 'hair salon', 'nail': 'nail salon', 'spa': 'spa',
    'barber': 'barbershop', 'hair': 'hair salon', 'beauty': 'beauty salon',
    'clip': 'hair salon',
    # Pet
    'pet': 'pet store', 'vet': 'veterinary', 'animal': 'pet care',
    'grooming': 'pet grooming',
    # Other
    'cleaners': 'dry cleaning', 'laundry': 'laundromat',
    'dispensary': 'dispensary', 'cannabis': 'dispensary',
    'gym': 'fitness', 'yoga': 'fitness',
}

# OR/WA cities that might appear in event titles (for "Sending Customers" pattern)
OR_WA_CITIES = {
    'portland', 'salem', 'eugene', 'gresham', 'hillsboro', 'beaverton',
    'bend', 'medford', 'springfield', 'corvallis', 'albany', 'hood river',
    'seaside', 'astoria', 'tillamook', 'cannon beach', 'lincoln city',
    'newport', 'coos bay', 'brookings', 'roseburg', 'grants pass',
    'klamath falls', 'the dalles', 'hermiston', 'pendleton', 'la grande',
    'baker city', 'ontario', 'mcminnville', 'newberg', 'woodburn',
    'silverton', 'dallas', 'cottage grove', 'florence', 'tualatin',
    'tigard', 'lake oswego', 'west linn', 'oregon city', 'milwaukie',
    'clackamas', 'happy valley', 'wilsonville', 'sherwood', 'canby',
    'sandy', 'estacada', 'molalla', 'stayton', 'lebanon', 'sweet home',
    'redmond', 'prineville', 'madras', 'la pine', 'sunriver',
    # Washington
    'seattle', 'spokane', 'tacoma', 'vancouver', 'bellevue', 'everett',
    'kent', 'yakima', 'renton', 'bellingham', 'kennewick', 'olympia',
    'puyallup', 'longview', 'kelso', 'centralia', 'chehalis',
    'aberdeen', 'port angeles', 'sequim', 'bothell', 'kirkland',
    'redmond', 'issaquah', 'sammamish', 'woodinville', 'lynnwood',
    'shoreline', 'mountlake terrace', 'edmonds', 'mukilteo',
    'marysville', 'arlington', 'mount vernon', 'burlington',
    'sedro-woolley', 'anacortes', 'oak harbor', 'coupeville',
    'port townsend', 'bremerton', 'silverdale', 'poulsbo',
    'gig harbor', 'lakewood', 'university place', 'bonney lake',
    'enumclaw', 'auburn', 'federal way', 'tukwila', 'seatac',
    'burien', 'white center', 'des moines', 'covington', 'maple valley',
    'black diamond', 'orting', 'eatonville', 'yelm', 'tumwater',
    'lacey', 'shelton', 'elma', 'montesano', 'hoquiam', 'westport',
    'ocean shores', 'long beach', 'ilwaco', 'cathlamet',
    'woodland', 'kalama', 'castle rock', 'toledo', 'winlock',
    'morton', 'packwood', 'randle', 'white salmon', 'stevenson',
    'goldendale', 'toppenish', 'sunnyside', 'grandview', 'prosser',
    'richland', 'pasco', 'west richland', 'walla walla',
    'college place', 'pullman', 'moscow', 'clarkston', 'lewiston',
    'ellensburg', 'cle elum', 'wenatchee', 'east wenatchee',
    'leavenworth', 'chelan', 'ephrata', 'moses lake', 'othello',
    'airway heights',
}

# State abbreviation lookup for known cities
CITY_TO_STATE = {}
# We'll populate OR cities as OR, WA cities as WA in a simple way
_or_cities = {
    'portland', 'salem', 'eugene', 'gresham', 'hillsboro', 'beaverton',
    'bend', 'medford', 'springfield', 'corvallis', 'albany', 'hood river',
    'seaside', 'astoria', 'tillamook', 'cannon beach', 'lincoln city',
    'newport', 'coos bay', 'brookings', 'roseburg', 'grants pass',
    'klamath falls', 'the dalles', 'hermiston', 'pendleton', 'la grande',
    'baker city', 'ontario', 'mcminnville', 'newberg', 'woodburn',
    'silverton', 'dallas', 'cottage grove', 'florence', 'tualatin',
    'tigard', 'lake oswego', 'west linn', 'oregon city', 'milwaukie',
    'clackamas', 'happy valley', 'wilsonville', 'sherwood', 'canby',
    'sandy', 'estacada', 'molalla', 'stayton', 'lebanon', 'sweet home',
    'redmond', 'prineville', 'madras', 'la pine', 'sunriver',
}
for c in _or_cities:
    CITY_TO_STATE[c] = 'OR'
for c in OR_WA_CITIES - _or_cities:
    CITY_TO_STATE[c] = 'WA'


def load_tracking():
    """Load processed event tracking data."""
    if TRACKING_FILE.exists():
        with open(TRACKING_FILE) as f:
            return json.load(f)
    return {}


def save_tracking(data):
    """Save processed event tracking data."""
    TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKING_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def get_calendar_events(hours=48):
    """Fetch upcoming calendar events."""
    now = datetime.now(timezone(timedelta(hours=-8)))  # PST
    end = now + timedelta(hours=hours)
    
    cmd = [
        'gog', 'calendar', 'events', 'primary',
        '--from', now.isoformat(),
        '--to', end.isoformat(),
        '--json'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error fetching calendar: {result.stderr}")
        return []
    
    data = json.loads(result.stdout)
    return data.get('events', [])


def is_indoormedia_email(email):
    """Check if email belongs to IndoorMedia/RTUI."""
    if not email:
        return False
    domain = email.split('@')[-1].lower()
    return domain in INDOORMEDIA_DOMAINS


def is_internal_meeting(event):
    """Check if this is an internal meeting (skip it)."""
    summary = (event.get('summary') or '').lower()
    
    # Check internal keywords
    for keyword in INTERNAL_KEYWORDS:
        if keyword in summary:
            return True
    
    # If ALL attendees are internal, it might be internal
    # BUT if it has a physical address/location, it's likely a business visit
    attendees = event.get('attendees', [])
    if attendees:
        all_internal = all(
            is_indoormedia_email(a.get('email', ''))
            for a in attendees
            if a.get('email')
        )
        if all_internal and not is_business_title(summary):
            # Check if there's a real street address in the location
            location = event.get('location', '')
            has_street_address = bool(re.search(r'\d+\s+\w+.*(st|ave|blvd|rd|dr|ln|way|hwy|pkwy)', location, re.IGNORECASE))
            if not has_street_address:
                return True
    
    return False


def is_business_title(summary):
    """Check if a title looks like a business meeting."""
    summary_lower = summary.lower()
    patterns = [
        'appointment', 'sending customers', 'meet with',
        'meeting with', 'presentation', 'pitch', 'demo',
        'in-person', 'follow up', 'follow-up',
    ]
    return any(p in summary_lower for p in patterns)


def parse_simple_appointments_description(description):
    """Parse structured data from Simple Appointments Inc descriptions."""
    info = {}
    if not description:
        return info
    
    # Type
    m = re.search(r'Type:\s*(.+?)(?:\n|$)', description)
    if m:
        info['business_type'] = m.group(1).strip()
    
    # Address
    m = re.search(r'Address:\s*(.+?)(?:\n|$)', description)
    if m:
        addr = m.group(1).strip()
        info['address'] = addr
        # Extract city and state from address like "8147 SW Nyberg St, Tualatin, OR 97062, USA"
        addr_match = re.search(r',\s*([^,]+),\s*([A-Z]{2})\s+\d{5}', addr)
        if addr_match:
            info['city'] = addr_match.group(1).strip()
            info['state'] = addr_match.group(2).strip()
    
    # Contact person
    m = re.search(r'(?:Contact Person|Ask For):\s*(.+?)(?:\n|$)', description)
    if m:
        info['contact'] = m.group(1).strip()
    
    # Phone
    m = re.search(r'Phone:\s*(.+?)(?:\n|$)', description)
    if m:
        info['phone'] = m.group(1).strip()
    
    return info


def infer_business_type(business_name):
    """Try to guess business type from name."""
    name_lower = business_name.lower()
    for hint, btype in BUSINESS_TYPE_HINTS.items():
        if hint in name_lower:
            return btype
    return 'business'  # generic fallback


def extract_city_from_title_or_location(event, business_name=''):
    """Try to find city from event title, location, or known city list."""
    # Check location field first
    location = event.get('location', '')
    if location:
        # Try to parse city from address
        addr_match = re.search(r',\s*([^,]+),\s*([A-Z]{2})\s+\d{5}', location)
        if addr_match:
            return addr_match.group(1).strip(), addr_match.group(2).strip()
        # Check if location contains a known city
        loc_lower = location.lower()
        for city in sorted(OR_WA_CITIES, key=len, reverse=True):  # longest first
            if city in loc_lower:
                return city.title(), CITY_TO_STATE.get(city, '')
    
    # Check title for known cities
    summary = (event.get('summary') or '').lower()
    for city in sorted(OR_WA_CITIES, key=len, reverse=True):
        if city in summary:
            return city.title(), CITY_TO_STATE.get(city, '')
    
    return '', ''


def parse_event(event):
    """Parse a calendar event and extract business meeting info.
    
    Returns None if not a business meeting, or a dict with:
    - business_name, business_type, city, state, contact, phone, address
    - meeting_time, rep_emails
    """
    summary = event.get('summary', '')
    description = event.get('description', '')
    
    if not summary:
        return None
    
    # Skip internal meetings
    if is_internal_meeting(event):
        return None
    
    info = {
        'business_name': '',
        'business_type': '',
        'city': '',
        'state': '',
        'contact': '',
        'phone': '',
        'address': '',
        'meeting_time': '',
        'rep_emails': [],
        'event_id': event.get('id', ''),
        'raw_summary': summary,
    }
    
    # Extract meeting time
    start = event.get('start', {})
    info['meeting_time'] = start.get('dateTime', start.get('date', ''))
    
    # Extract rep emails (IndoorMedia/RTUI attendees only)
    attendees = event.get('attendees', [])
    for att in attendees:
        email = att.get('email', '')
        if is_indoormedia_email(email):
            info['rep_emails'].append(email)
    
    # Always include Tyler
    if TYLER_EMAIL not in info['rep_emails']:
        info['rep_emails'].append(TYLER_EMAIL)
    
    # Also check creator
    creator_email = event.get('creator', {}).get('email', '')
    if is_indoormedia_email(creator_email) and creator_email not in info['rep_emails']:
        info['rep_emails'].append(creator_email)
    
    summary_lower = summary.lower().strip()
    
    # Pattern 1: "In-Person Appointment: {BusinessName}"
    m = re.match(r'(?:in-person\s+)?appointment[:\s]+(.+)', summary, re.IGNORECASE)
    if m:
        info['business_name'] = m.group(1).strip()
        # Parse description for structured data
        desc_info = parse_simple_appointments_description(description)
        info.update({k: v for k, v in desc_info.items() if v})
        if not info['business_type']:
            info['business_type'] = infer_business_type(info['business_name'])
        if not info['city']:
            city, state = extract_city_from_title_or_location(event)
            info['city'] = city
            info['state'] = state
        return info
    
    # Pattern 2: "Meet with {Contact} at {Business} in {City}"
    m = re.match(r'meet(?:ing)?\s+with\s+(.+?)\s+at\s+(.+?)\s+in\s+(.+)', summary, re.IGNORECASE)
    if m:
        info['contact'] = m.group(1).strip()
        info['business_name'] = m.group(2).strip()
        city_str = m.group(3).strip()
        info['city'] = city_str
        info['state'] = CITY_TO_STATE.get(city_str.lower(), '')
        info['business_type'] = infer_business_type(info['business_name'])
        return info
    
    # Pattern 2b: "Meet with {Contact} at {Business}" (no city)
    m = re.match(r'meet(?:ing)?\s+with\s+(.+?)\s+at\s+(.+)', summary, re.IGNORECASE)
    if m:
        info['contact'] = m.group(1).strip()
        info['business_name'] = m.group(2).strip()
        info['business_type'] = infer_business_type(info['business_name'])
        city, state = extract_city_from_title_or_location(event)
        info['city'] = city
        info['state'] = state
        return info
    
    # Pattern 3: "{Store} Sending Customers to {Business}"
    m = re.match(r'(.+?)\s+sending\s+customers\s+to\s+(.+)', summary, re.IGNORECASE)
    if m:
        store_part = m.group(1).strip()
        info['business_name'] = m.group(2).strip()
        info['business_type'] = infer_business_type(info['business_name'])
        
        # Try to extract city from store part (e.g., "Brookings Fred Meyer")
        store_lower = store_part.lower()
        for city in sorted(OR_WA_CITIES, key=len, reverse=True):
            if store_lower.startswith(city):
                info['city'] = city.title()
                info['state'] = CITY_TO_STATE.get(city, '')
                break
        
        if not info['city']:
            city, state = extract_city_from_title_or_location(event)
            info['city'] = city
            info['state'] = state
        return info
    
    # Fallback: has IndoorMedia attendees + not clearly internal
    has_indoormedia = any(is_indoormedia_email(a.get('email', '')) for a in attendees)
    has_external = any(
        not is_indoormedia_email(a.get('email', ''))
        for a in attendees
        if a.get('email')
    )
    
    # Also check: if the event has a location with a real address, it's likely a business visit
    has_location = bool(event.get('location', '').strip())
    
    if has_indoormedia and (has_external or is_business_title(summary) or has_location):
        info['business_name'] = summary.strip()
        info['business_type'] = infer_business_type(summary)
        
        # Try to get city/state from location field
        city, state = extract_city_from_title_or_location(event)
        info['city'] = city
        info['state'] = state
        return info
    
    return None


def run_testimonial_picker(business_type, business_name, city, state):
    """Run the testimonial picker and return its output."""
    query = f"{business_type} in {city}" if city else business_type
    
    cmd = [
        sys.executable, str(TESTIMONIAL_PICKER),
        query,
        '--business', business_name,
    ]
    if state:
        cmd.extend(['--state', state])
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE))
    if result.returncode != 0:
        print(f"  ⚠️  Testimonial picker error: {result.stderr}")
        return None
    
    return result.stdout


def parse_testimonial_output(output):
    """Parse testimonial picker output into structured data."""
    sections = {
        'video': {'name': '', 'link': ''},
        'written': [],
        'nearby': None,
    }
    
    lines = output.strip().split('\n')
    current_section = None
    current_item = {}
    
    for line in lines:
        line = line.rstrip()
        
        if line.startswith('🎬 VIDEO TESTIMONIAL'):
            current_section = 'video'
            continue
        elif line.startswith('📝 MATCHING TESTIMONIALS'):
            current_section = 'written'
            continue
        elif line.startswith('📍 NEARBY TESTIMONIAL'):
            current_section = 'nearby'
            current_item = {}
            continue
        
        if current_section == 'video':
            if line.startswith('🔗 '):
                sections['video']['link'] = line[2:].strip()
            elif line.strip() and not line.startswith('Loading'):
                sections['video']['name'] = line.strip()
        
        elif current_section == 'written':
            m = re.match(r'(\d+)\.\s+(.+)', line)
            if m:
                if current_item:
                    sections['written'].append(current_item)
                current_item = {'header': m.group(2).strip(), 'quote': '', 'redemptions': '', 'pdf': ''}
            elif line.strip().startswith('"') and current_item:
                current_item['quote'] = line.strip().strip('"')
            elif '📊' in line and current_item:
                current_item['redemptions'] = line.strip().replace('📊 ', '').replace('   📊 ', '')
            elif '📄' in line and current_item:
                m2 = re.search(r'(https://\S+)', line)
                if m2:
                    current_item['pdf'] = m2.group(1)
        
        elif current_section == 'nearby':
            if line.strip().startswith('"'):
                current_item['quote'] = line.strip().strip('"')
            elif '📊' in line:
                current_item['redemptions'] = line.strip().replace('📊 ', '')
            elif '📄' in line:
                m2 = re.search(r'(https://\S+)', line)
                if m2:
                    current_item['pdf'] = m2.group(1)
            elif line.strip() and 'header' not in current_item:
                current_item['header'] = line.strip()
    
    # Don't forget last written item
    if current_item and current_section == 'written':
        sections['written'].append(current_item)
    elif current_item and current_section == 'nearby':
        sections['nearby'] = current_item
    
    return sections


def build_html_email(meeting_info, testimonials):
    """Build HTML email body."""
    t = testimonials
    
    # Format meeting time nicely
    mt = meeting_info.get('meeting_time', '')
    try:
        dt = datetime.fromisoformat(mt)
        meeting_time_str = dt.strftime('%A, %B %d at %I:%M %p')
    except:
        meeting_time_str = mt
    
    # Build meeting details section
    details = []
    if meeting_info.get('contact'):
        details.append(f"<strong>Contact:</strong> {meeting_info['contact']}")
    if meeting_info.get('phone'):
        details.append(f"<strong>Phone:</strong> {meeting_info['phone']}")
    if meeting_info.get('address'):
        details.append(f"<strong>Address:</strong> {meeting_info['address']}")
    if meeting_info.get('business_type') and meeting_info['business_type'] != 'business':
        details.append(f"<strong>Type:</strong> {meeting_info['business_type'].title()}")
    
    details_html = '<br>'.join(details) if details else ''
    
    # Build written testimonials
    written_html = ''
    for i, w in enumerate(t.get('written', []), 1):
        redemptions_line = f'<br><span style="color:#2d7d46;">📊 {w["redemptions"]}</span>' if w.get('redemptions') else ''
        written_html += f"""
        <tr>
            <td style="padding:12px 16px; border-bottom:1px solid #eee;">
                <strong>{i}. {w.get('header', '')}</strong><br>
                <em style="color:#555;">"{w.get('quote', '')}"</em>
                {redemptions_line}
                <br><a href="{w.get('pdf', '#')}" style="color:#1a73e8;">📄 View Testimonial PDF</a>
            </td>
        </tr>"""
    
    # Build nearby testimonial
    nearby_html = ''
    if t.get('nearby'):
        n = t['nearby']
        n_redemptions = f'<br><span style="color:#2d7d46;">📊 {n["redemptions"]}</span>' if n.get('redemptions') else ''
        nearby_html = f"""
        <tr>
            <td style="padding:12px 16px; background:#f0f7ff; border-radius:8px;">
                <strong>📍 Nearby Business</strong><br>
                <strong>{n.get('header', '')}</strong><br>
                <em style="color:#555;">"{n.get('quote', '')}"</em>
                {n_redemptions}
                <br><a href="{n.get('pdf', '#')}" style="color:#1a73e8;">📄 View Testimonial PDF</a>
            </td>
        </tr>"""
    
    city_state = f"{meeting_info.get('city', '')}, {meeting_info.get('state', '')}".strip(', ')
    
    html = f"""<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
    
    <div style="background: linear-gradient(135deg, #1a73e8, #0d47a1); color: white; padding: 24px; border-radius: 12px 12px 0 0;">
        <h1 style="margin:0; font-size:22px;">🎯 Sales Prep Package</h1>
        <h2 style="margin:8px 0 0; font-size:18px; font-weight:normal; opacity:0.95;">
            {meeting_info.get('business_name', 'Business')} — {city_state}
        </h2>
        <p style="margin:8px 0 0; opacity:0.85; font-size:14px;">
            📅 {meeting_time_str}
        </p>
    </div>
    
    {"<div style='background:#f8f9fa; padding:16px; border-left:4px solid #1a73e8; margin:0;'>" + details_html + "</div>" if details_html else ""}
    
    <div style="background:white; padding:20px; border:1px solid #e0e0e0; border-radius: 0 0 12px 12px;">
        
        <h3 style="color:#1a73e8; margin-top:0;">🎬 Video Testimonial</h3>
        <div style="background:#f8f9fa; padding:12px 16px; border-radius:8px; margin-bottom:20px;">
            <strong>{t.get('video', {}).get('name', '')}</strong><br>
            <a href="{t.get('video', {}).get('link', '#')}" style="color:#1a73e8; font-size:14px;">
                ▶️ Watch Video Testimonial
            </a>
        </div>
        
        <h3 style="color:#1a73e8;">📝 Written Testimonials</h3>
        <table style="width:100%; border-collapse:collapse;">
            {written_html}
        </table>
        
        <h3 style="color:#1a73e8; margin-top:20px;">📍 Nearby Success Story</h3>
        <table style="width:100%; border-collapse:collapse;">
            {nearby_html}
        </table>
        
        <hr style="border:none; border-top:1px solid #eee; margin:24px 0 12px;">
        <p style="color:#999; font-size:12px; text-align:center; margin:0;">
            Auto-generated by Shelldon 🐚 • IndoorMedia Sales Prep
        </p>
    </div>
</body>
</html>"""
    
    return html


def send_email(recipients, subject, html_body, dry_run=False):
    """Send HTML email via gog gmail."""
    if dry_run:
        print(f"  📧 [DRY RUN] Would send to: {', '.join(recipients)}")
        print(f"  📧 Subject: {subject}")
        print(f"  📧 HTML body: {len(html_body)} chars")
        return True
    
    for recipient in recipients:
        cmd = [
            'gog', 'gmail', 'send',
            '--to', recipient,
            '--subject', subject,
            '--body-html', html_body,
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ❌ Failed to email {recipient}: {result.stderr}")
        else:
            print(f"  ✅ Emailed {recipient}")
    
    return True


def process_event(event, dry_run=False):
    """Process a single calendar event."""
    meeting = parse_event(event)
    if not meeting:
        return None
    
    print(f"\n{'='*60}")
    print(f"📅 {meeting['raw_summary']}")
    print(f"   Business: {meeting['business_name']}")
    print(f"   Type: {meeting['business_type']}")
    print(f"   City: {meeting['city']}, {meeting['state']}")
    print(f"   Contact: {meeting.get('contact', 'N/A')}")
    print(f"   Reps: {', '.join(meeting['rep_emails'])}")
    print(f"   Time: {meeting['meeting_time']}")
    
    # Run testimonial picker
    print(f"\n   🔍 Running testimonial picker...")
    output = run_testimonial_picker(
        meeting['business_type'],
        meeting['business_name'],
        meeting['city'],
        meeting['state']
    )
    
    if not output:
        print("   ⚠️  No testimonials found")
        return meeting
    
    # Parse output
    testimonials = parse_testimonial_output(output)
    
    print(f"   ✅ Found: video={bool(testimonials['video']['link'])}, "
          f"written={len(testimonials['written'])}, "
          f"nearby={bool(testimonials['nearby'])}")
    
    # Build and send email
    city_state = f"{meeting['city']}, {meeting['state']}".strip(', ')
    try:
        dt = datetime.fromisoformat(meeting['meeting_time'])
        date_str = dt.strftime('%b %d')
    except:
        date_str = 'Upcoming'
    
    subject = f"Sales Prep: {meeting['business_name']} - {city_state} | {date_str}"
    html = build_html_email(meeting, testimonials)
    
    send_email(meeting['rep_emails'], subject, html, dry_run=dry_run)
    
    return meeting


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Calendar Sales Prep Pipeline')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be sent without emailing')
    parser.add_argument('--hours', type=int, default=48, help='Lookahead window in hours (default: 48)')
    parser.add_argument('--reprocess', action='store_true', help='Reprocess already-sent events')
    args = parser.parse_args()
    
    print(f"🐚 Shelldon Sales Prep Pipeline")
    print(f"   Scanning next {args.hours} hours...")
    print(f"   Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    
    # Load tracking
    tracking = load_tracking()
    
    # Get events
    events = get_calendar_events(args.hours)
    print(f"   Found {len(events)} calendar events")
    
    processed = 0
    skipped = 0
    
    for event in events:
        event_id = event.get('id', '')
        
        # Skip already processed
        if event_id in tracking and not args.reprocess:
            skipped += 1
            continue
        
        result = process_event(event, dry_run=args.dry_run)
        
        if result:
            processed += 1
            if not args.dry_run:
                tracking[event_id] = {
                    'sent_at': datetime.now().isoformat(),
                    'recipients': result['rep_emails'],
                    'business': result['business_name'],
                }
    
    # Save tracking
    if not args.dry_run:
        save_tracking(tracking)
    
    print(f"\n{'='*60}")
    print(f"✅ Done! Processed: {processed} | Skipped: {skipped} | Total: {len(events)}")


if __name__ == '__main__':
    main()
