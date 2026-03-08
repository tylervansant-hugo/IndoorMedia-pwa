#!/usr/bin/env python3
"""
IndoorMedia ROI Calculator - Web Tool
Calculate ROI for register tape advertising based on store performance metrics
"""

import streamlit as st
import json
import pandas as pd
from pathlib import Path

# Load store data
WORKSPACE = Path(__file__).parent.parent
STORES_FILE = WORKSPACE / "data" / "store-rates" / "stores.json"

with open(STORES_FILE) as f:
    STORES_LIST = json.load(f)

STORES = {s["StoreName"]: s for s in STORES_LIST}

# Build city index
CITY_INDEX = {}
for store in STORES_LIST:
    city = store.get("City", "Unknown").title()
    state = store.get("State", "").upper()
    key = f"{city}, {state}"
    if key not in CITY_INDEX:
        CITY_INDEX[key] = []
    CITY_INDEX[key].append(store)

CITIES_SORTED = sorted(CITY_INDEX.keys())

# Pricing constants
PRICING_PADDING = 1200
PRODUCTION = 125

def get_price_for_store(store: dict, ad_type: str = "single", payment_plan: str = "monthly", tier: str = "coop") -> dict:
    """Calculate ad costs for a store.
    
    Returns dict with 'per_installment', 'annual', and 'payment_display' keys.
    Base prices in store data are ANNUAL.
    """
    base = store["DoubleAd"] if ad_type.lower() == "double" else store["SingleAd"]
    
    # Step 1: Determine base before discount
    if tier.lower() == "coop":
        base_before = base
    else:
        # Padded pricing (standard/non-co-op)
        base_before = base + PRICING_PADDING
    
    # Step 2: Apply payment plan discount and calculate installments
    if payment_plan.lower() == "paid_full":
        # 15% discount, then add production
        annual = (base_before * 0.85) + PRODUCTION
        per_installment = annual
        payment_display = f"${annual:.2f} (one payment, 15% off)"
    elif payment_plan.lower() == "paid_3":
        # 10% discount, then add production, divide by 3
        annual = ((base_before * 0.90) + PRODUCTION) * 3
        per_installment = ((base_before * 0.90) + PRODUCTION)
        payment_display = f"${per_installment:.2f} × 3 = ${annual:.2f} (10% off)"
    elif payment_plan.lower() == "paid_6":
        # 7.5% discount, then add production, divide by 6
        annual = ((base_before * 0.925) + PRODUCTION) * 6
        per_installment = ((base_before * 0.925) + PRODUCTION)
        payment_display = f"${per_installment:.2f} × 6 = ${annual:.2f} (7.5% off)"
    else:  # monthly
        # No discount, add production, multiply by 12
        annual = (base_before + PRODUCTION) * 12
        per_installment = base_before + PRODUCTION
        payment_display = f"${per_installment:.2f}/month × 12 = ${annual:.2f}"
    
    # For ROI purposes, monthly cost is always annual/12
    monthly = annual / 12
    
    return {"per_installment": per_installment, "monthly": monthly, "annual": annual, "payment_display": payment_display}

def calculate_roi(store: dict, ad_type: str, payment_plan: str, tier: str,
                  redemptions: int, avg_ticket: float, cogs_pct: float, coupon: float) -> dict:
    """Calculate ROI for a store campaign.
    
    Campaign runs for 12 months. Different payment plans affect daily/monthly cost.
    """
    
    # Get annual and monthly ad costs
    prices = get_price_for_store(store, ad_type, payment_plan, tier)
    annual_cost = prices["annual"]
    monthly_cost = prices["monthly"]
    
    # Calculate profit (monthly basis)
    discounted_ticket = avg_ticket - coupon
    monthly_revenue = redemptions * discounted_ticket
    monthly_profit = monthly_revenue * (1 - cogs_pct / 100)
    
    # Annual profit
    annual_revenue = monthly_revenue * 12
    annual_profit = monthly_profit * 12
    
    # ROI calculations
    monthly_roi = ((monthly_profit - monthly_cost) / monthly_cost * 100) if monthly_cost > 0 else 0
    annual_roi = ((annual_profit - annual_cost) / annual_cost * 100) if annual_cost > 0 else 0
    
    # Daily metrics
    daily_cost = annual_cost / 365
    daily_profit = annual_profit / 365
    
    # Break-even
    breakeven_redemptions = monthly_cost / discounted_ticket if discounted_ticket > 0 else 0
    
    return {
        "monthly_revenue": monthly_revenue,
        "monthly_profit": monthly_profit,
        "monthly_cost": monthly_cost,
        "annual_cost": annual_cost,
        "annual_revenue": annual_revenue,
        "annual_profit": annual_profit,
        "daily_cost": daily_cost,
        "daily_profit": daily_profit,
        "monthly_roi": monthly_roi,
        "annual_roi": annual_roi,
        "breakeven_redemptions": breakeven_redemptions,
    }

# Streamlit UI
st.set_page_config(page_title="IndoorMedia ROI Calculator", layout="wide")
st.title("📊 Register Tape ROI Calculator")
st.markdown("Calculate your advertising ROI with register tape campaigns")

# Check for store parameter in URL
query_params = st.query_params
pre_selected_store_num = query_params.get("store", None)

# Store selection
st.header("1️⃣ Select Your Store")
col1, col2 = st.columns(2)

with col1:
    # If store param provided, default to Store Number search
    if pre_selected_store_num:
        search_type = "Store Number"
    else:
        search_type = st.radio("Find by:", ["City, State", "Store Number"], horizontal=True)

selected_store = None
if search_type == "City, State":
    city_selection = st.selectbox("City, State:", CITIES_SORTED)
    if city_selection:
        stores_in_city = CITY_INDEX[city_selection]
        store_names = [f"{s['StoreName']} - {s['GroceryChain']}" for s in stores_in_city]
        selected_store_name = st.selectbox("Store:", store_names)
        if selected_store_name:
            store_num = selected_store_name.split(" - ")[0]
            selected_store = STORES[store_num]
else:
    # Pre-fill with store from URL if provided
    if pre_selected_store_num:
        if pre_selected_store_num in STORES:
            selected_store = STORES[pre_selected_store_num]
            st.success(f"✅ Pre-loaded from link: {pre_selected_store_num}")
        else:
            st.warning(f"Store {pre_selected_store_num} not found")
    else:
        store_number = st.text_input("Store Number (e.g., KRO21Y-0350):")
        if store_number and store_number in STORES:
            selected_store = STORES[store_number]
        elif store_number:
            st.warning("Store not found")

if selected_store:
    st.success(f"✅ Selected: {selected_store['StoreName']} - {selected_store['GroceryChain']}, {selected_store['City']}, {selected_store['State']}")
    
    # Performance metrics
    st.header("2️⃣ Business Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        redemptions = st.slider("Redemptions/month:", 1, 50, 20, step=1)
    
    with col2:
        avg_ticket = st.slider("Avg ticket ($):", 5.0, 500.0, 35.0, step=5.0,
                              help="Most restaurants: $20-$100. Adjust for your customer base.")
    
    with col3:
        cogs_pct = st.slider("COGS (%):", 20, 50, 35, step=1)
    
    with col4:
        coupon = st.slider("Coupon discount ($):", 0.0, 100.0, 10.0, step=1.0)
    
    # Advertising options
    st.header("3️⃣ Advertising Options")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        ad_type = st.radio("Ad Size:", ["Single", "Double"], horizontal=True)
    
    with col2:
        payment_plan = st.radio("Payment Plan:", ["Monthly", "Paid in 3", "Paid in 6", "Paid in Full"], horizontal=True)
        plan_map = {
            "Monthly": "monthly",
            "Paid in 3": "paid_3",
            "Paid in 6": "paid_6",
            "Paid in Full": "paid_full"
        }
        plan_key = plan_map[payment_plan]
    
    with col3:
        tier = st.radio("Tier:", ["Co-Op", "Standard"], horizontal=True)
        tier_key = "coop" if tier == "Co-Op" else "standard"
    
    # Calculate ROI
    roi_data = calculate_roi(
        selected_store,
        ad_type.lower(),
        plan_key,
        tier_key,
        redemptions,
        avg_ticket,
        cogs_pct,
        coupon
    )
    
    # Get pricing details for display
    prices = get_price_for_store(selected_store, ad_type.lower(), plan_key, tier_key)
    
    # Display results
    st.header("4️⃣ ROI Results")
    st.info(f"📢 **{ad_type} Ad - {tier} Tier**\n\n{prices['payment_display']}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Monthly Revenue", f"${roi_data['monthly_revenue']:.2f}")
    
    with col2:
        st.metric("Monthly Net Profit", f"${roi_data['monthly_profit'] - roi_data['monthly_cost']:.2f}",
                 delta=f"ROI: {roi_data['monthly_roi']:.0f}%")
    
    with col3:
        st.metric("Annual Revenue", f"${roi_data['annual_revenue']:.2f}")
    
    with col4:
        st.metric("Annual Net Profit", f"${roi_data['annual_profit'] - roi_data['annual_cost']:.2f}",
                 delta=f"ROI: {roi_data['annual_roi']:.0f}%")
    
    # Breakdown
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💰 Monthly Breakdown")
        st.write(f"**Redemptions:** {redemptions}/month")
        st.write(f"**Avg Ticket:** ${avg_ticket:.2f}")
        st.write(f"**Coupon:** -${coupon:.2f}")
        st.write(f"**Actual Ticket:** ${avg_ticket - coupon:.2f}")
        st.write(f"---")
        st.write(f"**Revenue:** ${roi_data['monthly_revenue']:.2f}")
        st.write(f"**COGS ({cogs_pct}%):** -${roi_data['monthly_revenue'] * (cogs_pct/100):.2f}")
        st.write(f"**Profit (after COGS):** ${roi_data['monthly_profit']:.2f}")
        st.write(f"**Ad Cost:** -${roi_data['monthly_cost']:.2f}")
        st.write(f"---")
        net_monthly = roi_data['monthly_profit'] - roi_data['monthly_cost']
        color = "🟢" if net_monthly >= 0 else "🔴"
        st.write(f"# {color} **NET MONTHLY PROFIT: ${net_monthly:.2f}**")
    
    with col2:
        st.subheader("📈 Annual Projection")
        st.write(f"**Annual Revenue:** ${roi_data['annual_revenue']:.2f}")
        st.write(f"**Annual COGS Cost:** -${roi_data['annual_profit'] - (roi_data['annual_revenue'] * (1 - cogs_pct/100)):.2f}")
        st.write(f"**Annual Profit (after COGS):** ${roi_data['annual_profit']:.2f}")
        st.write(f"**Annual Ad Cost:** -${roi_data['annual_cost']:.2f}")
        st.write(f"---")
        net_annual = roi_data['annual_profit'] - roi_data['annual_cost']
        color = "🟢" if net_annual >= 0 else "🔴"
        st.write(f"# {color} **NET ANNUAL PROFIT: ${net_annual:.2f}**")
    
    # Break-even analysis
    st.markdown("---")
    st.subheader("🎯 Break-Even Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Redemptions Needed to Break Even", f"{roi_data['breakeven_redemptions']:.1f}")
    
    with col2:
        if roi_data['breakeven_redemptions'] > 0:
            if redemptions >= roi_data['breakeven_redemptions']:
                pct_above = ((redemptions - roi_data['breakeven_redemptions']) / roi_data['breakeven_redemptions'] * 100)
                st.metric("Above Break-Even", f"+{pct_above:.0f}%", delta="✅ Profitable")
            else:
                pct_below = ((roi_data['breakeven_redemptions'] - redemptions) / roi_data['breakeven_redemptions'] * 100)
                st.metric("Below Break-Even", f"-{pct_below:.0f}%", delta="⚠️ Not yet")
        else:
            st.metric("Status", "Instantly Profitable", delta="✅ No break-even needed")

else:
    st.info("👈 Start by selecting a store to see ROI calculations")
