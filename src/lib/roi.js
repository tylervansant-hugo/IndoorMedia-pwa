/**
 * Shared ROI calculator module — compounding monthly formula.
 *
 * Coupon-redemption model
 * ------------------------
 * Each month a business gets `couponRedemptions` total redemptions.  Of those,
 * `newCustomers` are brand-new customers and the rest
 * (`couponRedemptions - newCustomers`) are returning/existing loyal customers.
 *
 * NEW customers compound month over month: the people you win in month 1 keep
 * coming back, then month 2 adds a fresh batch on top, etc.  Over 12 months
 * the customer-months total = newCustomers × (1+2+...+12) = newCustomers × 78.
 *   New-customer revenue = newCustomers × avgSpend × 78
 *
 * RETURNING redeemers are a steady recurring monthly stream (your existing
 * loyal audience using the coupon each month):
 *   Returning revenue = (couponRedemptions - newCustomers) × avgSpend × 12
 *
 * This cleanly shows the dual value: register-tape coupons KEEP your existing
 * loyal audience AND introduce new customers.
 *
 * @param {Object} params
 * @param {number} params.investment          - Total ad investment ($)
 * @param {number} params.avgSpend            - Average customer spend ($)
 * @param {number} params.couponRedemptions   - Total coupon redemptions per month
 * @param {number} params.newCustomers        - How many of those redemptions are NEW customers
 * @param {number} params.cogsPercent         - Cost of goods sold (0-100)
 * @param {number} params.visitsPerYear       - Informational only (baked into the 12-month compounding)
 * @param {number} params.discountAmount      - Flat $ off per redeemed coupon (cost of the offer)
 * @param {number} params.discountPercent     - % off per redeemed coupon (0-100), applied to avgSpend
 * @param {number} params.giveawayCost        - Cost of a free/giveaway item per redemption ($)
 * @returns {Object} ROI breakdown
 *
 * Coupon-offer cost model
 * -----------------------
 * Each redeemed coupon carries the cost of the offer the business honored:
 *   - `discountPercent` reduces the customer's effective spend (applied to avgSpend first)
 *   - `discountAmount`  is a flat $ knocked off after the % discount
 *   - `giveawayCost`    is the business's hard cost of a free item given per redemption
 * Effective spend per redemption = max(0, avgSpend*(1-discountPercent/100) - discountAmount).
 * Total offer cost = giveawayCost applied to every redemption across the year
 * (steady returning stream = ×12; compounding new stream = ×78).
 */
export function calculateROI({
  investment = 0,
  avgSpend = 0,
  couponRedemptions = 0,
  newCustomers = 0,
  cogsPercent = 0,
  visitsPerYear = 12,
  discountAmount = 0,
  discountPercent = 0,
  giveawayCost = 0,
} = {}) {
  // Compounding factor: sum of 1..12 = 78
  const COMPOUNDING_FACTOR = 78; // 12 * 13 / 2

  // If a caller supplies newCustomers without an explicit couponRedemptions
  // (e.g. the Tools ROI calculator has no "redemptions" field), treat total
  // redemptions as at least the new-customer count so they aren't clamped away.
  const effectiveRedemptions = Math.max(couponRedemptions, newCustomers);
  // Clamp: new customers can't exceed total redemptions.
  const newCust = Math.max(0, Math.min(newCustomers, effectiveRedemptions));
  const returningCust = Math.max(0, effectiveRedemptions - newCust);

  // Effective spend after the coupon offer (% off first, then $ off). Never below 0.
  const pctOff = Math.max(0, Math.min(discountPercent, 100)) / 100;
  const effectiveSpend = Math.max(0, avgSpend * (1 - pctOff) - Math.max(0, discountAmount));

  // New-customer revenue compounds month over month.
  const newCustomerRevenue = newCust * effectiveSpend * COMPOUNDING_FACTOR;
  // Returning/existing loyal redeemers are a steady recurring monthly stream.
  const returningRevenue = returningCust * effectiveSpend * 12;

  const grossRevenue = newCustomerRevenue + returningRevenue;
  const cogs = grossRevenue * (cogsPercent / 100);

  // Giveaway/free-item cost is a hard cost paid on every redemption across the year.
  // New redemptions compound (×78 customer-months); returning are steady (×12).
  const perRedemptionGiveaway = Math.max(0, giveawayCost);
  const giveawayTotal =
    perRedemptionGiveaway * newCust * COMPOUNDING_FACTOR +
    perRedemptionGiveaway * returningCust * 12;

  const netRevenue = grossRevenue - cogs - giveawayTotal;
  const netProfit = netRevenue - investment;
  const roiPercent = investment > 0 ? Math.round((netProfit / investment) * 100) : 0;

  return {
    grossRevenue: Math.round(grossRevenue),
    newCustomerRevenue: Math.round(newCustomerRevenue),
    returningRevenue: Math.round(returningRevenue),
    cogs: Math.round(cogs),
    giveawayTotal: Math.round(giveawayTotal),
    netRevenue: Math.round(netRevenue),
    netProfit: Math.round(netProfit),
    roiPercent,
    // Convenience fields
    investment: Math.round(investment),
    effectiveSpend: Math.round(effectiveSpend * 100) / 100,
    discountAmount: Math.max(0, discountAmount),
    discountPercent: Math.max(0, Math.min(discountPercent, 100)),
    giveawayCost: perRedemptionGiveaway,
    couponRedemptionsPerMonth: couponRedemptions,
    totalCouponRedemptions: couponRedemptions * 12,
    newCustomersPerMonth: newCust,
    totalNewCustomers: newCust * 12,
    returningCustomersPerMonth: returningCust,
    visitsPerYear,
  };
}
