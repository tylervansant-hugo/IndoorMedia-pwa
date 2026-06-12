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
 * @returns {Object} ROI breakdown
 */
export function calculateROI({
  investment = 0,
  avgSpend = 0,
  couponRedemptions = 0,
  newCustomers = 0,
  cogsPercent = 0,
  visitsPerYear = 12,
} = {}) {
  // Compounding factor: sum of 1..12 = 78
  const COMPOUNDING_FACTOR = 78; // 12 * 13 / 2

  // Clamp: new customers can't exceed total redemptions.
  const newCust = Math.max(0, Math.min(newCustomers, couponRedemptions));
  const returningCust = Math.max(0, couponRedemptions - newCust);

  // New-customer revenue compounds month over month.
  const newCustomerRevenue = newCust * avgSpend * COMPOUNDING_FACTOR;
  // Returning/existing loyal redeemers are a steady recurring monthly stream.
  const returningRevenue = returningCust * avgSpend * 12;

  const grossRevenue = newCustomerRevenue + returningRevenue;
  const cogs = grossRevenue * (cogsPercent / 100);
  const netRevenue = grossRevenue - cogs;
  const netProfit = netRevenue - investment;
  const roiPercent = investment > 0 ? Math.round((netProfit / investment) * 100) : 0;

  return {
    grossRevenue: Math.round(grossRevenue),
    newCustomerRevenue: Math.round(newCustomerRevenue),
    returningRevenue: Math.round(returningRevenue),
    cogs: Math.round(cogs),
    netRevenue: Math.round(netRevenue),
    netProfit: Math.round(netProfit),
    roiPercent,
    // Convenience fields
    investment: Math.round(investment),
    couponRedemptionsPerMonth: couponRedemptions,
    totalCouponRedemptions: couponRedemptions * 12,
    newCustomersPerMonth: newCust,
    totalNewCustomers: newCust * 12,
    returningCustomersPerMonth: returningCust,
    visitsPerYear,
  };
}
