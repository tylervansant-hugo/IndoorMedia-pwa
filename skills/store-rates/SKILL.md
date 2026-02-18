---
name: store-rates
description: Look up tape advertising rates for IndoorMedia store network across Oregon and Washington. Query rates by store, city, and chain (Fred Meyer, Safeway, Albertsons, etc.). Automatically applies $1,325 cushion to ad rates, $125 to monthly minimums, and calculates 5% paid-in-full discounts. Use when Tyler asks "what's the rate for [store]?" or "what's the minimum monthly price for [store/city]?" or needs pricing analysis.
---

# Store Rates Skill

Quick access to IndoorMedia's tape advertising rates across Oregon & Washington stores (245 locations, 99 cities) with automatic pricing calculations.

## What This Skill Does

- **Store lookups** by city and chain name (Fred Meyer, Safeway, Albertsons, Quality Food Center, Haggen, Rosauers, etc.)
- **Two pricing displays:**
  - **Standard (Base Rates):** SingleAd/DoubleAd + $1,325 cushion, minimum + $125 floor
  - **Lowest Price:** Monthly minimum with payment term discounts (-7.5% for 6mo, -10% for 3mo, -15% paid in full), then +$125
- **Simple, flexible queries:** "Safeway in Chehalis?", "all stores in Portland?", etc.

## Quick Examples

### Query 1: "What's the base rate for Safeway in Chehalis?"

Run:
```bash
python scripts/rate_calculator.py Chehalis Safeway
```

Output:
```
📍 Safeway | Tier A | Chehalis, US
   Store Code: SAF07Z-3525

   BASE RATES (includes $1,325 cushion):
      Single Ad: $6,325.00
      Double Ad: $8,325.00
      Single Min (Monthly): $4,625.00
      Double Min (Monthly): $6,425.00
```

### Query 2: "Show me the lowest prices with different payment terms"

Run:
```bash
python scripts/rate_calculator.py Chehalis Safeway --lowest
```

Output:
```
📍 Safeway | Tier A | Chehalis, US
   Store Code: SAF07Z-3525

   LOWEST PRICE - SINGLE AD:
      Month-to-month: $4,625.00
      6-month prepaid (7.5% off): $4,287.50
      3-month prepaid (10% off): $4,175.00
      Paid in full (15% off): $3,950.00 ⭐

   LOWEST PRICE - DOUBLE AD:
      Month-to-month: $6,425.00
      6-month prepaid (7.5% off): $5,952.50
      3-month prepaid (10% off): $5,795.00
      Paid in full (15% off): $5,480.00 ⭐
```

### Query 3: "Show me all stores in Bend"

Run:
```bash
python scripts/rate_calculator.py Bend
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
# Standard (base rates with cushion)
python scripts/rate_calculator.py Chehalis Safeway

# Show lowest prices with payment term discounts
python scripts/rate_calculator.py Chehalis Safeway --lowest

# Find all Fred Meyer locations in Longview
python scripts/rate_calculator.py Longview "Fred Meyer"

# Find all stores in Portland (base rates)
python scripts/rate_calculator.py Portland

# Find all stores in Portland with lowest prices
python scripts/rate_calculator.py Portland --lowest
```

## Data Files

- **`references/store_data.json`** - Complete store database with base rates, cycles, tiers
  - **245 stores across 99 cities** in Oregon and Washington
  - Fields: code, name, tier, cycle, address, city, state, zip, singlead, doublead, singlemin, doublemin
  - Pricing rules: $1,325 cushion on ads, $125 minimum floor, payment term discounts (-7.5%, -10%, -15%)

## Pricing Model

### Two Display Modes

#### 1. Standard (Base Rates) — Default
Shows rates WITH $1,325 cushion and $125 minimum floor included.
- **SingleAd (Base Rate):** SingleAd + $1,325
- **DoubleAd (Base Rate):** DoubleAd + $1,325
- **SingleMin (Monthly):** SingleMin + $125
- **DoubleMin (Monthly):** DoubleMin + $125

#### 2. Lowest Price — With `--lowest` flag
Shows monthly minimum WITHOUT cushion, then applies payment term discounts, then adds $125.

**Payment Term Discounts:**
- **Month-to-month:** Base + $125 (no discount)
- **6-month prepaid:** Base × 0.925 + $125 (7.5% off)
- **3-month prepaid:** Base × 0.90 + $125 (10% off)
- **Paid in full:** Base × 0.85 + $125 (15% off)

### Example Calculation

**Safeway in Chehalis (SAF07Z-3525):**

**Standard Display:**
- Base SingleAd: $5,000
- Base Rate (+ $1,325 cushion): **$6,325**
- Base SingleMin: $4,500
- Monthly Min (+ $125 floor): **$4,625**

**Lowest Price Display:**
- Month-to-month: $4,500 + $125 = **$4,625**
- 6-month: ($4,500 × 0.925) + $125 = **$4,287.50**
- 3-month: ($4,500 × 0.90) + $125 = **$4,175**
- Paid in full: ($4,500 × 0.85) + $125 = **$3,950** ⭐

## Extending the Skill

To add more stores to the reference file, edit `references/store_data.json` and add new objects to the `stores` array. The calculator will pick them up automatically.

## Notes

- **Tier codes:** A = smaller, B = medium, C = large/flagship
- **Cycles:** 07Y (year-round), 07Z (seasonal/variable)
- **Chains covered:** Fred Meyer, Safeway, Albertsons, Quality Food Center, Haggen, Rosauers, Shop N Kart, Sherms Market, and more
- All prices are in USD
