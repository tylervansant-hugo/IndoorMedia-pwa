#!/usr/bin/env python3
"""
Shipping & Delivery Data Module for IndoorMedia ProspectBot.
Loads shipping records from the sales portal scrape and provides
store-level delivery history, status tracking, and UPS links.

Data source: data/shipping_delivery_report.json
Scraped from: https://sales.indoormedia.com/Reports/ReportViewer?Id=129
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path(os.environ.get("WORKSPACE", Path(__file__).parent.parent))
SHIPPING_FILE = WORKSPACE / "data" / "shipping_delivery_report.json"

# Thresholds for delivery status
OVERDUE_DAYS = 45
APPROACHING_DAYS = 30

def load_shipping_data():
    """Load all shipping records from JSON file."""
    if not SHIPPING_FILE.exists():
        return []
    with open(SHIPPING_FILE) as f:
        return json.load(f)

def get_store_shipments(store_number=None, zone=None, manager=None):
    """Get shipments filtered by store number, zone, or manager."""
    data = load_shipping_data()
    results = data
    
    if store_number:
        store_upper = store_number.upper()
        results = [r for r in results if r.get('StoreName', '').upper() == store_upper]
    
    if zone:
        zone_upper = zone.upper()
        results = [r for r in results if r.get('Zone', '').upper() == zone_upper]
    
    if manager:
        manager_lower = manager.lower()
        results = [r for r in results if manager_lower in r.get('RegionalMgr1', '').lower()]
    
    return results

def get_latest_delivery(store_number):
    """Get the most recent DELIVERED shipment for a store."""
    shipments = get_store_shipments(store_number=store_number)
    delivered = [s for s in shipments if s.get('ShipmentStatus') == 'Delivered' and s.get('DeliveryDate')]
    
    if not delivered:
        return None
    
    # Sort by delivery date, most recent first
    delivered.sort(key=lambda x: x['DeliveryDate'], reverse=True)
    return delivered[0]

def get_in_transit(store_number=None, zone=None):
    """Get shipments currently in transit."""
    shipments = get_store_shipments(store_number=store_number, zone=zone)
    return [s for s in shipments if s.get('ShipmentStatus') == 'In_Transit']

def get_delivery_status(store_number):
    """
    Get delivery status for a store.
    Returns dict with: last_delivery_date, days_since, status_emoji, status_text,
                       in_transit, tracking_url, etc.
    """
    latest = get_latest_delivery(store_number)
    in_transit = get_in_transit(store_number=store_number)
    
    result = {
        'store_number': store_number,
        'last_delivery': None,
        'last_delivery_date': None,
        'days_since_delivery': None,
        'status': 'unknown',
        'status_emoji': '❓',
        'status_text': 'No delivery data',
        'in_transit': len(in_transit) > 0,
        'in_transit_count': len(in_transit),
        'in_transit_tracking': [],
        'tracking_url': None,
        'delivery_address': None,
    }
    
    # In-transit tracking info
    for s in in_transit:
        tn = s.get('TrackingNumber', '')
        if tn:
            result['in_transit_tracking'].append({
                'tracking_number': tn,
                'ship_date': s.get('ShipmentDate', ''),
                'url': f"https://www.ups.com/track?tracknum={tn}"
            })
    
    if not latest:
        return result
    
    # Parse delivery date
    dd_str = latest.get('DeliveryDate', '')
    try:
        delivery_date = datetime.fromisoformat(dd_str.replace('Z', '+00:00'))
        # Make naive for comparison
        if delivery_date.tzinfo:
            delivery_date = delivery_date.replace(tzinfo=None)
    except (ValueError, AttributeError):
        return result
    
    days_since = (datetime.now() - delivery_date).days
    
    result['last_delivery'] = latest
    result['last_delivery_date'] = delivery_date
    result['days_since_delivery'] = days_since
    result['delivery_address'] = latest.get('DeliveryAddress', '')
    
    tn = latest.get('TrackingNumber', '')
    if tn:
        result['tracking_url'] = f"https://www.ups.com/track?tracknum={tn}"
    
    # Determine status
    if days_since > OVERDUE_DAYS:
        result['status'] = 'overdue'
        result['status_emoji'] = '🔴'
        result['status_text'] = f'OVERDUE — {days_since} days since last delivery'
    elif days_since > APPROACHING_DAYS:
        result['status'] = 'approaching'
        result['status_emoji'] = '🟡'
        result['status_text'] = f'Approaching — {days_since} days since last delivery'
    else:
        result['status'] = 'recent'
        result['status_emoji'] = '🟢'
        result['status_text'] = f'Recent — {days_since} days since last delivery'
    
    # Override if something is in transit
    if result['in_transit']:
        result['status_text'] += f' (🚚 {result["in_transit_count"]} in transit)'
    
    return result

def get_zone_summary(zone=None, manager=None):
    """
    Get summary for a zone or manager.
    Returns: {overdue: [...], approaching: [...], recent: [...], in_transit: [...]}
    """
    data = load_shipping_data()
    
    if zone:
        data = [r for r in data if r.get('Zone', '').upper() == zone.upper()]
    if manager:
        manager_lower = manager.lower()
        data = [r for r in data if manager_lower in r.get('RegionalMgr1', '').lower()]
    
    # Get unique stores
    stores = list(set(r.get('StoreName', '') for r in data))
    
    overdue = []
    approaching = []
    recent = []
    in_transit_stores = []
    no_data = []
    
    for store in sorted(stores):
        status = get_delivery_status(store)
        
        if status['status'] == 'overdue':
            overdue.append(status)
        elif status['status'] == 'approaching':
            approaching.append(status)
        elif status['status'] == 'recent':
            recent.append(status)
        else:
            no_data.append(status)
        
        if status['in_transit']:
            in_transit_stores.append(status)
    
    return {
        'zone': zone,
        'manager': manager,
        'total_stores': len(stores),
        'overdue': overdue,
        'approaching': approaching,
        'recent': recent,
        'in_transit': in_transit_stores,
        'no_data': no_data,
    }

def get_all_zones_summary():
    """Get summary across all zones."""
    data = load_shipping_data()
    zones = sorted(set(r.get('Zone', '') for r in data))
    
    summaries = {}
    for zone in zones:
        summaries[zone] = get_zone_summary(zone=zone)
    
    return summaries

def format_delivery_card(store_number):
    """Format a Telegram-friendly delivery status card for a store."""
    status = get_delivery_status(store_number)
    
    lines = [f"{status['status_emoji']} *{store_number}*"]
    
    if status['last_delivery_date']:
        date_str = status['last_delivery_date'].strftime('%b %d, %Y')
        lines.append(f"📦 Last delivery: {date_str} ({status['days_since_delivery']}d ago)")
    else:
        lines.append("📦 No delivery records found")
    
    if status['delivery_address']:
        lines.append(f"📍 {status['delivery_address']}")
    
    if status['in_transit']:
        for t in status['in_transit_tracking']:
            ship_date = t['ship_date'][:10] if t['ship_date'] else '?'
            lines.append(f"🚚 In transit (shipped {ship_date})")
    
    lines.append(f"\n{status['status_text']}")
    
    return '\n'.join(lines)

def format_zone_report(zone):
    """Format a full zone report for Telegram."""
    summary = get_zone_summary(zone=zone)
    
    lines = [f"📊 *Zone {zone} Delivery Report*"]
    lines.append(f"Total stores: {summary['total_stores']}\n")
    
    if summary['overdue']:
        lines.append(f"🔴 *OVERDUE ({len(summary['overdue'])} stores):*")
        for s in summary['overdue']:
            days = s['days_since_delivery']
            lines.append(f"  • {s['store_number']} — {days}d ago")
        lines.append("")
    
    if summary['approaching']:
        lines.append(f"🟡 *APPROACHING ({len(summary['approaching'])} stores):*")
        for s in summary['approaching']:
            days = s['days_since_delivery']
            lines.append(f"  • {s['store_number']} — {days}d ago")
        lines.append("")
    
    if summary['recent']:
        lines.append(f"🟢 *RECENT ({len(summary['recent'])} stores):*")
        for s in summary['recent']:
            days = s['days_since_delivery']
            lines.append(f"  • {s['store_number']} — {days}d ago")
        lines.append("")
    
    if summary['in_transit']:
        lines.append(f"🚚 *IN TRANSIT ({len(summary['in_transit'])} stores):*")
        for s in summary['in_transit']:
            for t in s['in_transit_tracking']:
                lines.append(f"  • {s['store_number']} — shipped {t['ship_date'][:10]}")
        lines.append("")
    
    return '\n'.join(lines)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        if arg.startswith(('SAF', 'FME', 'ALB', 'ROS', 'QFC', 'HAG', 'SNK', 'STB', 'JWL')):
            # Store lookup
            print(format_delivery_card(arg))
            status = get_delivery_status(arg)
            if status['tracking_url']:
                print(f"\n🔗 UPS Tracking: {status['tracking_url']}")
        elif len(arg) <= 4:
            # Zone lookup
            print(format_zone_report(arg))
        else:
            print(f"Usage: {sys.argv[0]} <store_number|zone>")
    else:
        # Show all zones summary
        summaries = get_all_zones_summary()
        for zone, summary in summaries.items():
            o = len(summary['overdue'])
            a = len(summary['approaching'])
            r = len(summary['recent'])
            t = len(summary['in_transit'])
            mgr = summary.get('manager', '')
            print(f"Zone {zone}: {summary['total_stores']} stores | 🔴 {o} 🟡 {a} 🟢 {r} 🚚 {t}")
