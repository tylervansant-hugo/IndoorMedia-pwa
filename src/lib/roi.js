/**
 * Shared ROI calculator module.
 * Canonical formula from Tools.svelte buildScenario().
 *
 * @param {Object} params
 * @param {number} params.totalAdCost   - Total ad investment for the campaign period
 * @param {number} params.months        - Campaign length in months
 * @param {number} params.redemptions   - Monthly coupon redemptions
 * @param {number} params.newCustomers  - New customers per month (non-coupon exposure)
 * @param {number} params.ticket        - Average customer spend ($)
 * @param {number} params.discount      - Average coupon discount ($)
 * @param {number} params.cogsPercent   - Cost of goods sold (0-100)
 * @param {number} params.visitsPerYear - Return visits per customer per year
 * @returns {Object} ROI breakdown
 */
export function calculateROI({
  totalAdCost = 0,
  months = 12,
  redemptions = 0,
  newCustomers = 0,
  ticket = 0,
  discount = 0,
  cogsPercent = 0,
  visitsPerYear = 1,
} = {}) {
  // Coupon redemptions (trackable)
  const monthlyRedemptionRevenue = redemptions * ticket * (visitsPerYear / 12);
  const monthlyDiscounts = redemptions * discount;

  // New customers (includes non-coupon exposure customers)
  const monthlyNewCustomerRevenue = newCustomers * ticket * (visitsPerYear / 12);

  const monthlyRevenue = monthlyRedemptionRevenue + monthlyNewCustomerRevenue;
  const monthlyCogs = monthlyRevenue * (cogsPercent / 100);
  const monthlyProfit = monthlyRevenue - monthlyDiscounts - monthlyCogs;

  const totalRevenue = monthlyRevenue * months;
  const totalDiscounts = monthlyDiscounts * months;
  const totalCogs = monthlyCogs * months;
  const campaignProfit = (monthlyProfit * months) - totalAdCost;
  const roiPercent = totalAdCost > 0 ? Math.round((campaignProfit / totalAdCost) * 100) : 0;

  const totalNewCustomers = newCustomers * months;
  const customerLifetimeValue = ticket * visitsPerYear;

  return {
    newCustomersPerMonth: newCustomers,
    totalNewCustomers,
    customerLifetimeValue: Math.round(customerLifetimeValue),
    newCustomerTotalValue: Math.round(totalNewCustomers * customerLifetimeValue),
    monthlyRevenue: Math.round(monthlyRevenue),
    monthlyProfit: Math.round(monthlyProfit),
    totalRevenue: Math.round(totalRevenue),
    totalDiscounts: Math.round(totalDiscounts),
    totalCogs: Math.round(totalCogs),
    campaignProfit: Math.round(campaignProfit),
    roiPercent,
  };
}
