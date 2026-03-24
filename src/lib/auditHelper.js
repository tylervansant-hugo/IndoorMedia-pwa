// Zone audit schedule helper
// Use to calculate when a store should be audited based on last delivery + zone

let zones = {};

export async function loadZones() {
  try {
    const res = await fetch('/data/zones.json');
    const data = await res.json();
    zones = data.zones;
  } catch (err) {
    console.warn('Zone data not loaded:', err);
  }
}

export function getZoneByStoreNumber(storeNum) {
  // Extract zone from store number (e.g., "FME07Z-0236" → "07Z")
  const match = storeNum?.match(/\d{2}[A-Z]/);
  return match ? match[0] : null;
}

export function getAuditDueDate(lastDeliveryDate, zoneCode) {
  if (!lastDeliveryDate) return null;
  
  const zone = zones[zoneCode] || zones['7Z']; // Default to Zone 7Z
  if (!zone) return null;
  
  const delivery = new Date(lastDeliveryDate);
  const auditDue = new Date(delivery.getTime() + (45 * 24 * 60 * 60 * 1000)); // 45 days
  
  return {
    deliveryDate: delivery.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    auditDueDate: auditDue.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
    daysUntilAudit: Math.max(0, Math.floor((auditDue - new Date()) / (24 * 60 * 60 * 1000))),
    zone: zone.name,
  };
}

export function getShipmentWindow(zoneCode) {
  const zone = zones[zoneCode];
  return zone?.inStoresDay ? `${zone.name}: ships around the ${zone.inStoresDay}th` : null;
}
