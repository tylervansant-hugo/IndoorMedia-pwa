#!/usr/bin/env python3
"""Save and analyze shipping data from IndoorMedia reports."""
import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Read raw data from stdin
import sys
raw = sys.stdin.read()
data = json.loads(raw)

# Save raw data
output_file = DATA_DIR / "shipping_delivery_report.json"
with open(output_file, 'w') as f:
    json.dump(data, f, indent=2)
print(f"✅ Saved {len(data)} shipment records to {output_file}")

# Filter Tyler's stores (RegionalMgr1 = Tyler VanSant)
tyler_stores = [r for r in data if r.get('RegionalMgr1') == 'Tyler VanSant']
print(f"\n📊 TYLER'S TERRITORY:")
print(f"  Total shipments: {len(tyler_stores)}")

# Unique stores
unique_stores = sorted(set(r['StoreName'] for r in tyler_stores))
print(f"  Unique stores: {len(unique_stores)}")

# Count by status
statuses = {}
for r in tyler_stores:
    status = r.get('ShipmentStatus', 'Unknown')
    statuses[status] = statuses.get(status, 0) + 1
print(f"  Status: {statuses}")

# Find stores with most recent delivery
store_latest = {}
for r in tyler_stores:
    store = r['StoreName']
    delivery_date = r.get('DeliveryDate', '')
    if delivery_date and (store not in store_latest or delivery_date > store_latest[store]):
        store_latest[store] = delivery_date

# Sort by delivery date (oldest first = longest since delivery)
sorted_stores = sorted(store_latest.items(), key=lambda x: x[1])
print(f"\n⚠️ STORES NEEDING ATTENTION (oldest deliveries):")
for store, date in sorted_stores[:10]:
    try:
        dt = datetime.fromisoformat(date.split('.')[0])
        days_ago = (datetime.now() - dt).days
        print(f"  {store:20s} | Last delivery: {date[:10]} ({days_ago} days ago)")
    except:
        print(f"  {store:20s} | Last delivery: {date[:10]}")

# In-transit shipments
in_transit = [r for r in tyler_stores if r.get('ShipmentStatus') == 'In_Transit']
if in_transit:
    print(f"\n🚚 IN TRANSIT ({len(in_transit)} shipments):")
    for r in in_transit:
        print(f"  {r['StoreName']:20s} | Shipped: {r['ShipmentDate'][:10]} | Tracking: {r['TrackingNumber']}")

# Zones breakdown
zones = {}
for r in tyler_stores:
    zone = r.get('Zone', '?')
    if zone not in zones:
        zones[zone] = set()
    zones[zone].add(r['StoreName'])
print(f"\n🗺️ ZONES:")
for zone, stores in sorted(zones.items()):
    print(f"  {zone}: {len(stores)} stores")
