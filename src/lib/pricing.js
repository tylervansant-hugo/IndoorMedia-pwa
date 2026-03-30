/**
 * Pricing utilities for IndoorMedia products
 * Integrates with store pricing data from stores.json
 */

// Price tiers based on case counts from store data
export const PRICE_TIERS = {
  registerTape: {
    // RegisterTape pricing based on store tape case counts
    small: { quantity: '1,000', price: 2550, perUnit: 2.55 },
    medium: { quantity: '5,000', price: 3800, perUnit: 0.76 },
    large: { quantity: '10,000+', price: 5100, perUnit: 0.51 },
  },
  cartvertising: {
    // Cartvertising based on average single/double ad pricing from stores
    single: { quantity: 'Single', price: 4050, perUnit: 4050 },
    double: { quantity: 'Double', price: 5670, perUnit: 2835 },
    multi: { quantity: '5+ stores', price: 22500, perUnit: 4500 },
  },
  digitalBoost: {
    // Digital boost premium digital display pricing
    single: { quantity: '1 screen', price: 7500, perUnit: 7500 },
    zone: { quantity: '3-5 screens', price: 18000, perUnit: 4500 },
    network: { quantity: '10+ screens', price: 35000, perUnit: 3500 },
  },
};

/**
 * Format currency for display
 */
export function formatCurrency(amount) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

/**
 * Calculate subtotal for cart item
 */
export function calculateSubtotal(item) {
  return item.price * item.quantity;
}

/**
 * Calculate cart total
 */
export function calculateCartTotal(items) {
  return items.reduce((sum, item) => sum + calculateSubtotal(item), 0);
}

/**
 * Calculate average per item
 */
export function calculateAveragePerItem(items) {
  if (items.length === 0) return 0;
  return calculateCartTotal(items) / items.length;
}

/**
 * Apply volume discount based on cart total
 */
export function getVolumeDiscount(total) {
  if (total >= 50000) return 0.15; // 15% off
  if (total >= 25000) return 0.10; // 10% off
  if (total >= 10000) return 0.05; // 5% off
  return 0;
}

/**
 * Calculate final total with volume discount
 */
export function calculateFinalTotal(items) {
  const subtotal = calculateCartTotal(items);
  const discount = getVolumeDiscount(subtotal);
  return subtotal * (1 - discount);
}

/**
 * Generate cart summary for export/sharing
 */
export function generateCartSummary(items) {
  const subtotal = calculateCartTotal(items);
  const discount = getVolumeDiscount(subtotal);
  const discountAmount = subtotal * discount;
  const total = subtotal - discountAmount;

  return {
    items: items.length,
    subtotal,
    discountPercentage: Math.round(discount * 100),
    discountAmount,
    total,
    formattedSubtotal: formatCurrency(subtotal),
    formattedDiscount: formatCurrency(discountAmount),
    formattedTotal: formatCurrency(total),
  };
}

/**
 * Generate CSV export of cart items
 */
export function generateCSVExport(items) {
  let csv = 'Product,Plan,Unit Price,Quantity,Subtotal,Added Date\n';
  
  items.forEach(item => {
    const subtotal = calculateSubtotal(item);
    const date = new Date(item.addedAt).toLocaleDateString();
    csv += `"${item.productName}","${item.planName}","$${item.perUnit.toFixed(2)}",${item.quantity},"$${subtotal.toFixed(2)}","${date}"\n`;
  });

  return csv;
}

/**
 * Generate JSON export of cart items
 */
export function generateJSONExport(items) {
  const summary = generateCartSummary(items);
  return {
    exportDate: new Date().toISOString(),
    items,
    summary,
  };
}

/**
 * Validate cart item
 */
export function validateCartItem(item) {
  const required = ['productId', 'planName', 'productName', 'quantity', 'price'];
  for (const field of required) {
    if (!(field in item)) {
      return false;
    }
  }
  return item.quantity > 0 && item.price > 0;
}
