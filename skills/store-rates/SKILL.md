---
name: store-rates
description: Look up tape advertising rates for IndoorMedia store network across Oregon and Washington. Query rates by store, city, and chain (Fred Meyer, Safeway, Albertsons, etc.). Automatically applies $1,325 cushion to ad rates, $125 to monthly minimums, and calculates 5% paid-in-full discounts. Use when Tyler asks "what's the rate for [store]?" or "what's the minimum monthly price for [store/city]?" or needs pricing analysis.
---

# Store Rates Skill

Quick access to IndoorMedia's tape advertising rates across Oregon & Washington stores, with automatic pricing adjustments baked in.

## What This Skill Does

- **Store lookups** by city and chain name (Fred Meyer, Safeway, Albertsons, etc.)
- **Automatic pricing adjustments:**
  - **Cushion:** +$1,325 on SingleAd and DoubleAd rates by default
  - **Minimum floor:** +$125 on SingleMin and DoubleMin
  - **Paid-in-full discount:** 5% off all adjusted rates when paid upfront
- **Simple, flexible queries:** "Fred Meyer in Longview?", "minimum for Bend stores?", etc.

## Quick Examples

### Query 1: "What's the rate for the Fred Meyer in Longview?"

Run:
```bash
python scripts/rate_calculator.py Longview "Fred Meyer"
```

Output:
```
📍 Fred Meyer | Tier A | Longview, WA
   Store Code: FME07Z-0185

   SINGLE AD:
      Base: $5,100.00
      With Cushion (+$1,325): $6,425.00

   DOUBLE AD:
      Base: $7,140.00
      With Cushion (+$1,325): $8,465.00

   MINIMUM (Monthly):
      Single Min Base: $4,590.00
      Single Min Adjusted (+$125): $4,715.00
      Double Min Base: $6,426.00
      Double Min Adjusted (+$125): $6,551.00
```

### Query 2: "What's the minimum monthly price for that store with paid-in-full discount?"

Run:
```bash
python scripts/rate_calculator.py Longview "Fred Meyer" --paid-in-full
```

Output: Same as above, plus:
```
      Single Min Paid in Full (5% off): $4,479.25
      Double Min Paid in Full (5% off): $6,223.45
```

### Query 3: "Show me all Safeway rates in Bend"

Run:
```bash
python scripts/rate_calculator.py Bend Safeway
```

## How to Use

### From Python (in skills or agents)

```python
from pathlib import Path
import json

script_dir = Path(__file__).parent
# Import or run the rate_calculator module
from rate_calculator import find_stores_by_city_and_chain, calculate_adjusted_rates, format_rate_display

# Find stores
stores = find_stores_by_city_and_chain("Longview", "Fred Meyer")

# Calculate rates (without discount)
rates = calculate_adjusted_rates(stores[0], paid_in_full=False)
print(format_rate_display(rates))

# Calculate rates with 5% discount
rates_discounted = calculate_adjusted_rates(stores[0], paid_in_full=True)
print(format_rate_display(rates_discounted, include_discount=True))
```

### From CLI

```bash
# Find Fred Meyer in Longview (base + cushion)
python scripts/rate_calculator.py Longview "Fred Meyer"

# Find all stores in Portland
python scripts/rate_calculator.py Portland

# Find all stores in Portland with 5% paid-in-full discount
python scripts/rate_calculator.py Portland --paid-in-full
```

## Data Files

- **`references/store_data.json`** - Complete store database with base rates, cycles, tiers, and adjustment rules
  - 380+ stores across OR and WA
  - Fields: code, name, tier, cycle, address, city, state, zip, singlead, doublead, singlemin, doublemin
  - Adjustment settings: $1,325 cushion, $125 minimum floor, 5% paid-in-full discount

## Pricing Model

### Base Rates (from reference file)
- **SingleAd:** Price per instance
- **DoubleAd:** Price per instance (2x size)
- **SingleMin:** Monthly minimum for single ads
- **DoubleMin:** Monthly minimum for double ads

### Adjustments Applied
1. **Cushion (+$1,325):** Added to both SingleAd and DoubleAd
2. **Minimum Floor (+$125):** Added to both SingleMin and DoubleMin
3. **Paid-in-Full Discount (5%):** Applied to all adjusted prices when flagged

### Example Calculation

Fred Meyer in Longview (FME07Z-0185):
- Base SingleAd: $5,100
- Adjusted SingleAd (+ $1,325): **$6,425**
- Paid-in-Full (5% off $6,425): **$6,103.75**

---

Base SingleMin: $4,590
- Adjusted SingleMin (+ $125): **$4,715**
- Paid-in-Full (5% off $4,715): **$4,479.25**

## Extending the Skill

To add more stores to the reference file, edit `references/store_data.json` and add new objects to the `stores` array. The calculator will pick them up automatically.

## Notes

- **Tier codes:** A = smaller, B = medium, C = large/flagship
- **Cycles:** 07Y (year-round), 07Z (seasonal/variable)
- **Chains covered:** Fred Meyer, Safeway, Albertsons, Quality Food Center, Haggen, Rosauers, Shop N Kart, Sherms Market, and more
- All prices are in USD
