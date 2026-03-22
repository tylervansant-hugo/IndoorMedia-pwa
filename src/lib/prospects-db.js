// localStorage-based prospect database
// Manages saved prospects with full workflow (New → Contacted → Proposal → Closed)

const DB_KEY = 'indoormedia_prospects';
const VERSION = 1;

export const STATUS = {
  NEW: 'New',
  CONTACTED: 'Contacted',
  PROPOSAL: 'Proposal',
  CLOSED: 'Closed'
};

/**
 * Initialize database
 */
export function initDB() {
  if (!localStorage.getItem(DB_KEY)) {
    localStorage.setItem(DB_KEY, JSON.stringify({
      version: VERSION,
      prospects: [],
      history: []
    }));
  }
}

/**
 * Get all saved prospects
 */
export function getAllProspects() {
  const db = getDB();
  return db.prospects || [];
}

/**
 * Get prospects filtered by status
 */
export function getProspectsByStatus(status) {
  const all = getAllProspects();
  return all.filter(p => p.status === status);
}

/**
 * Search prospects by name, address, or category
 */
export function searchProspects(query) {
  const all = getAllProspects();
  const lower = query.toLowerCase();
  
  return all.filter(p =>
    p.name.toLowerCase().includes(lower) ||
    p.address.toLowerCase().includes(lower) ||
    p.category.toLowerCase().includes(lower) ||
    p.subcategory.toLowerCase().includes(lower)
  );
}

/**
 * Get a single prospect by ID
 */
export function getProspect(id) {
  const all = getAllProspects();
  return all.find(p => p.id === id);
}

/**
 * Save a new prospect (from search results)
 */
export function saveProspect(placeData, category, subcategory) {
  initDB();
  const db = getDB();
  
  const prospect = {
    id: generateId(),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    
    // Place data
    placeId: placeData.placeId,
    name: placeData.name,
    address: placeData.address,
    phone: placeData.phone || '',
    website: placeData.website || '',
    
    // Classification
    category: category,
    subcategory: subcategory,
    
    // Metadata
    rating: placeData.rating || 0,
    reviewCount: placeData.reviewCount || 0,
    isOpen: placeData.isOpen,
    hours: placeData.hours || [],
    mapsUrl: placeData.mapsUrl || '',
    
    // IndoorMedia tracking
    status: STATUS.NEW,
    likelihoodScore: placeData.likelihoodScore || 50,
    notes: '',
    contactHistory: [],
    lastContactedAt: null,
    tags: []
  };
  
  db.prospects.push(prospect);
  addHistory({
    prospectId: prospect.id,
    action: 'saved',
    timestamp: prospect.createdAt,
    note: `Prospect saved from ${subcategory} search`
  });
  
  saveDB(db);
  return prospect;
}

/**
 * Update prospect status
 */
export function updateProspectStatus(prospectId, newStatus) {
  const db = getDB();
  const prospect = db.prospects.find(p => p.id === prospectId);
  
  if (!prospect) {
    throw new Error('Prospect not found');
  }
  
  prospect.status = newStatus;
  prospect.updatedAt = new Date().toISOString();
  
  addHistory({
    prospectId: prospectId,
    action: 'status_changed',
    timestamp: prospect.updatedAt,
    note: `Status changed to ${newStatus}`
  });
  
  saveDB(db);
  return prospect;
}

/**
 * Add notes to a prospect
 */
export function addProspectNote(prospectId, note) {
  if (!note.trim()) return;
  
  const db = getDB();
  const prospect = db.prospects.find(p => p.id === prospectId);
  
  if (!prospect) {
    throw new Error('Prospect not found');
  }
  
  prospect.notes = note;
  prospect.updatedAt = new Date().toISOString();
  
  addHistory({
    prospectId: prospectId,
    action: 'note_added',
    timestamp: prospect.updatedAt,
    note: note
  });
  
  saveDB(db);
  return prospect;
}

/**
 * Mark prospect as contacted
 */
export function markContacted(prospectId, method = 'phone') {
  const db = getDB();
  const prospect = db.prospects.find(p => p.id === prospectId);
  
  if (!prospect) {
    throw new Error('Prospect not found');
  }
  
  const now = new Date().toISOString();
  prospect.lastContactedAt = now;
  prospect.updatedAt = now;
  prospect.contactHistory.push({
    timestamp: now,
    method: method, // 'phone', 'email', 'in-person', 'call'
    notes: ''
  });
  
  // Auto-update status if still new
  if (prospect.status === STATUS.NEW) {
    prospect.status = STATUS.CONTACTED;
  }
  
  addHistory({
    prospectId: prospectId,
    action: 'contacted',
    timestamp: now,
    note: `Contacted via ${method}`
  });
  
  saveDB(db);
  return prospect;
}

/**
 * Delete a prospect
 */
export function deleteProspect(prospectId) {
  const db = getDB();
  const index = db.prospects.findIndex(p => p.id === prospectId);
  
  if (index === -1) {
    throw new Error('Prospect not found');
  }
  
  const prospect = db.prospects[index];
  db.prospects.splice(index, 1);
  
  addHistory({
    prospectId: prospectId,
    action: 'deleted',
    timestamp: new Date().toISOString(),
    note: prospect.name
  });
  
  saveDB(db);
}

/**
 * Get prospect history/activity log
 */
export function getProspectHistory(prospectId) {
  const db = getDB();
  return (db.history || []).filter(h => h.prospectId === prospectId);
}

/**
 * Get all activity history
 */
export function getAllHistory() {
  const db = getDB();
  return (db.history || []).sort((a, b) => 
    new Date(b.timestamp) - new Date(a.timestamp)
  );
}

/**
 * Export prospects as JSON
 */
export function exportProspects() {
  const db = getDB();
  return JSON.stringify(db, null, 2);
}

/**
 * Import prospects from JSON
 */
export function importProspects(jsonString) {
  try {
    const imported = JSON.parse(jsonString);
    
    // Validate structure
    if (!Array.isArray(imported.prospects)) {
      throw new Error('Invalid format: missing prospects array');
    }
    
    // Merge or replace
    const db = getDB();
    db.prospects = imported.prospects;
    db.history = imported.history || [];
    
    saveDB(db);
    return true;
  } catch (error) {
    console.error('Import failed:', error);
    throw error;
  }
}

/**
 * Clear all data (backup first!)
 */
export function clearAll() {
  localStorage.removeItem(DB_KEY);
  initDB();
}

/**
 * Get database stats
 */
export function getStats() {
  const db = getDB();
  const prospects = db.prospects || [];
  
  return {
    total: prospects.length,
    new: prospects.filter(p => p.status === STATUS.NEW).length,
    contacted: prospects.filter(p => p.status === STATUS.CONTACTED).length,
    proposal: prospects.filter(p => p.status === STATUS.PROPOSAL).length,
    closed: prospects.filter(p => p.status === STATUS.CLOSED).length,
    averageRating: prospects.length > 0
      ? (prospects.reduce((sum, p) => sum + (p.rating || 0), 0) / prospects.length).toFixed(2)
      : 0
  };
}

// --- Private helpers ---

function getDB() {
  const stored = localStorage.getItem(DB_KEY);
  if (!stored) {
    initDB();
    return {
      version: VERSION,
      prospects: [],
      history: []
    };
  }
  return JSON.parse(stored);
}

function saveDB(db) {
  localStorage.setItem(DB_KEY, JSON.stringify(db));
}

function addHistory(entry) {
  const db = getDB();
  if (!db.history) db.history = [];
  
  db.history.push({
    ...entry,
    id: generateId()
  });
  
  saveDB(db);
}

function generateId() {
  return `prospect_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}
