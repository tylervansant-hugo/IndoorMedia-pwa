#!/usr/bin/env python3
"""Extract and analyze shipping data from IndoorMedia reports."""
import json, sys
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Read from file
data = json.loads(Path(sys.argv[1]).read_text()) if len(sys.argv) > 1 else json.loads(sys.stdin.read())

# Save raw
output = DATA_DIR / "shipping_delivery_report.json"
output.write_text(json.dumps(data, indent=2))
print(f"✅ Saved {len(data)} records to {output}")

# Tyler's stores
tyler = [r for r in data if r.get('RegionalMgr1') == 'Tyler VanSant']
unique = sorted(set(r['StoreName'] for r in tyler))
delivered = [r for r in tyler if r['ShipmentStatus'] == 'Delivered']
in_transit = [r for r in tyler if r['ShipmentStatus'] == 'In_Transit']

print(f"\n📊 YOUR TERRITORY (Zone 07Z):")
print(f"  Total shipments: {len(tyler)}")
print(f"  Unique stores: {len(unique)}")
print(f"  Delivered: {len(delivered)}")
print(f"  In Transit: {len(in_transit)}")

# Latest delivery per store
now = datetime.now()
store_latest = {}
for r in tyler:
    store = r['StoreName']
    dd = r.get('DeliveryDate', '')
    if dd and (store not in store_latest or dd > store_latest[store]):
        store_latest[store] = dd

# Sort oldest first
sorted_stores = sorted(store_latest.items(), key=lambda x: x[1])

print(f"\n⚠️  STORES NEEDING ATTENTION (oldest deliveries):")
for store, date in sorted_stores[:15]:
    try:
        dt = datetime.fromisoformat(date.split('.')[0])
        days = (now - dt).days
        flag = "🔴" if days > 45 else "🟡" if days > 30 else "🟢"
        print(f"  {flag} {store:20s} | Last: {date[:10]} ({days}d ago)")
    except:
        print(f"  ❓ {store:20s} | Last: {date[:10]}")

print(f"\n🚚 IN TRANSIT:")
for r in in_transit:
    print(f"  📦 {r['StoreName']:20s} | Shipped: {r['ShipmentDate'][:10]} | Track: {r['TrackingNumber']}")
