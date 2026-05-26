/**
 * Shared ROI calculator module — compounding monthly formula.
 *
 * The "compounding" insight: month 1 has N new customers, month 2 has 2N,
 * ..., month 12 has 12N.  Total customer-months = N × (1+2+...+12) = N × 78.
 *
 * Gross Annual Revenue = newCustomers × avgSpend × 78
 *   (Verification: 25 × $50 × 78 = $97,500)
 *
 * @param {Object} params
 * @param {number} params.investment      - Total ad investment ($)
 * @param {number} params.avgSpend        - Average customer spend ($)
 * @param {number} params.newCustomers    - New customers gained per month
 * @param {number} params.cogsPercent     - Cost of goods sold (0-100)
 * @param {number} params.visitsPerYear   - Informational only (baked into the 12-month compounding)
 * @returns {Object} ROI breakdown
 */
export function calculateROI({
  investment = 0,
  avgSpend = 0,
  newCustomers = 0,
  cogsPercent = 0,
  visitsPerYear = 12,
} = {}) {
  // Compounding factor: sum of 1..12 = 78
  const COMPOUNDING_FACTOR = 78; // 12 * 13 / 2

  const grossRevenue = newCustomers * avgSpend * COMPOUNDING_FACTOR;
  const cogs = grossRevenue * (cogsPercent / 100);
  const netRevenue = grossRevenue - cogs;
  const netProfit = netRevenue - investment;
  const roiPercent = investment > 0 ? Math.round((netProfit / investment) * 100) : 0;

  return {
    grossRevenue: Math.round(grossRevenue),
    cogs: Math.round(cogs),
    netRevenue: Math.round(netRevenue),
    netProfit: Math.round(netProfit),
    roiPercent,
    // Convenience fields
    investment: Math.round(investment),
    newCustomersPerMonth: newCustomers,
    totalNewCustomers: newCustomers * 12,
    visitsPerYear,
  };
}
