/**
 * API Server for Svelte PWA
 * Handles data loading from JSON files and serves API endpoints
 * Run with: node api-server.js
 */

import express from 'express';
import cors from 'cors';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3001;

// Serve built Svelte app FIRST
const distPath = path.join(__dirname, 'dist');
console.log(`[SERVER] Serving static files from: ${distPath}`);
console.log(`[SERVER] Dist folder exists: ${fs.existsSync(distPath)}`);

// Static files middleware
app.use(express.static(distPath));

// API middleware
app.use(cors());
app.use(express.json());

// Mock data for Railway deployment
const MOCK_REPS = [
  { id: 1, name: 'Tyler Van Sant', email: 'tyler.vansant@indoormedia.com', base_location: 'Portland, OR' },
  { id: 2, name: 'Amy Dixon', email: 'amy@indoormedia.com', base_location: 'Tualatin, OR' },
  { id: 3, name: 'Matt', email: 'matt@indoormedia.com', base_location: 'Eugene, OR' },
];

const MOCK_STORES = [
  { store_number: 'FME07Y-0165', name: 'Fred Meyer - Klamath Falls', city: 'Klamath Falls', state: 'OR', single_ad: 3600, double_ad: 5400 },
];

// Data paths - support both local dev and Railway deployment
const WORKSPACE = process.env.WORKSPACE || '/Users/tylervansant/.openclaw/workspace';
const DATA_PATH = path.join(WORKSPACE, 'data');
const STORES_FILE = path.join(DATA_PATH, 'store-rates', 'stores.json');
const REP_REGISTRY_FILE = path.join(DATA_PATH, 'rep_registry.json');
const TESTIMONIALS_FILE = path.join(DATA_PATH, 'testimonials_cache.json');
const PROSPECTS_FILE = path.join(DATA_PATH, 'prospect_data.json');

// Cache data in memory
let storesCache = null;
let repRegistryCache = null;
let testimonialsCache = null;
let prospectsCache = null;

/**
 * Load JSON file with caching
 */
function loadJsonFile(filepath) {
  try {
    const data = fs.readFileSync(filepath, 'utf-8');
    return JSON.parse(data);
  } catch (error) {
    console.error(`[ERROR] Failed to load ${filepath}: ${error.message}`);
    return null;
  }
}

/**
 * Initialize caches
 */
function initializeCaches() {
  console.log('[SERVER] Loading data files...');
  storesCache = loadJsonFile(STORES_FILE) || MOCK_STORES;
  repRegistryCache = loadJsonFile(REP_REGISTRY_FILE) || { 'tyler': MOCK_REPS[0], 'amy': MOCK_REPS[1], 'matt': MOCK_REPS[2] };
  testimonialsCache = loadJsonFile(TESTIMONIALS_FILE) || [];
  prospectsCache = loadJsonFile(PROSPECTS_FILE) || [];
  console.log(
    `[SERVER] ✓ Loaded ${storesCache?.length || 0} stores`,
    `✓ Loaded ${Object.keys(repRegistryCache || {}).length} reps`,
    `✓ Loaded ${Array.isArray(testimonialsCache) ? testimonialsCache.length : 0} testimonials`
  );
}

// ============ API ENDPOINTS ============

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', stores: storesCache?.length || 0, reps: Object.keys(repRegistryCache || {}).length });
});

app.get('/api/rep-registry', (req, res) => {
  if (!repRegistryCache) {
    return res.status(500).json({ error: 'Failed to load reps' });
  }
  res.json(repRegistryCache);
});

app.post('/api/rep/validate', (req, res) => {
  const { username, password } = req.body;
  const rep = repRegistryCache?.[username];
  
  if (rep) {
    res.json({ 
      success: true, 
      rep: { id: rep.id, name: rep.name, email: rep.email } 
    });
  } else {
    res.status(401).json({ success: false, error: 'Invalid credentials' });
  }
});

app.get('/api/stores', (req, res) => {
  if (!storesCache) {
    return res.status(500).json({ error: 'Failed to load stores' });
  }
  res.json(storesCache.slice(0, 100)); // Return first 100
});

app.get('/api/stores/search', (req, res) => {
  const query = req.query.q?.toLowerCase() || '';
  
  if (!storesCache || !query) {
    return res.json([]);
  }
  
  const results = storesCache.filter(store =>
    store.name?.toLowerCase().includes(query) ||
    store.city?.toLowerCase().includes(query) ||
    store.store_number?.toLowerCase().includes(query)
  );
  
  res.json(results.slice(0, 20));
});

app.get('/api/testimonials', (req, res) => {
  if (!testimonialsCache) {
    return res.status(500).json({ error: 'Failed to load testimonials' });
  }
  res.json(testimonialsCache);
});

app.get('/api/prospects', (req, res) => {
  if (!prospectsCache) {
    return res.status(500).json({ error: 'Failed to load prospects' });
  }
  res.json(prospectsCache);
});

// ============ SPA FALLBACK ============
// Serve index.html for all non-API routes (SPA routing)
app.get('*', (req, res) => {
  const indexPath = path.join(distPath, 'index.html');
  
  if (fs.existsSync(indexPath)) {
    console.log(`[REQUEST] Serving SPA from index.html for ${req.path}`);
    res.sendFile(indexPath);
  } else {
    console.error(`[ERROR] index.html not found at ${indexPath}`);
    res.status(404).json({ error: 'index.html not found' });
  }
});

// ============ START SERVER ============
initializeCaches();

app.listen(PORT, '0.0.0.0', () => {
  console.log(`\n[SERVER] ✓ PWA API Server running on http://localhost:${PORT}`);
  console.log(`[SERVER] Available endpoints:`);
  console.log(`  GET  /api/health`);
  console.log(`  GET  /api/rep-registry`);
  console.log(`  POST /api/rep/validate`);
  console.log(`  GET  /api/stores`);
  console.log(`  GET  /api/stores/search`);
  console.log(`  GET  /api/testimonials`);
  console.log(`  GET  /api/prospects`);
  console.log(`[SERVER] Static files being served from: ${distPath}\n`);
});

// Error handling
process.on('unhandledRejection', (err) => {
  console.error('[ERROR] Unhandled rejection:', err);
});

process.on('uncaughtException', (err) => {
  console.error('[ERROR] Uncaught exception:', err);
  process.exit(1);
});
