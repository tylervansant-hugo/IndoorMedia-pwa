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

// Data paths - support both local dev and Railway deployment
const WORKSPACE = process.env.WORKSPACE || '/Users/tylervansant/.openclaw/workspace';
const DATA_PATH = path.join(WORKSPACE, 'data');
const STORES_FILE = path.join(DATA_PATH, 'store-rates', 'stores.json');
const REP_REGISTRY_FILE = path.join(DATA_PATH, 'rep_registry.json');
const TESTIMONIALS_FILE = path.join(DATA_PATH, 'testimonials_cache.json');
const PROSPECTS_FILE = path.join(DATA_PATH, 'prospect_data.json');

// Mock data for Railway deployment (when files don't exist)
const MOCK_REPS = [
  { id: 1, name: 'Tyler Van Sant', email: 'tyler.vansant@indoormedia.com', base_location: 'Portland, OR' },
  { id: 2, name: 'Amy Dixon', email: 'amy@indoormedia.com', base_location: 'Tualatin, OR' },
  { id: 3, name: 'Matt', email: 'matt@indoormedia.com', base_location: 'Eugene, OR' },
];

const MOCK_STORES = [
  { store_number: 'FME07Y-0165', name: 'Fred Meyer - Klamath Falls', city: 'Klamath Falls', state: 'OR', single_ad: 3600, double_ad: 5400 },
];

// Middleware
app.use(cors());
app.use(express.json());

// Serve built Svelte app
const distPath = path.join(__dirname, 'dist');
console.log(`Serving static files from: ${distPath}`);
console.log(`Dist folder exists: ${fs.existsSync(distPath)}`);
app.use(express.static(distPath, { index: 'index.html' }));

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
    console.error(`Error loading ${filepath}:`, error.message);
    return null;
  }
}

/**
 * Initialize caches
 */
function initializeCaches() {
  console.log('Loading data files...');
  storesCache = loadJsonFile(STORES_FILE) || MOCK_STORES;
  repRegistryCache = loadJsonFile(REP_REGISTRY_FILE) || { 'tyler': MOCK_REPS[0], 'amy': MOCK_REPS[1], 'matt': MOCK_REPS[2] };
  testimonialsCache = loadJsonFile(TESTIMONIALS_FILE) || [];
  prospectsCache = loadJsonFile(PROSPECTS_FILE) || [];
  console.log(
    `✓ Loaded ${storesCache?.length || 0} stores`,
    `✓ Loaded ${Object.keys(repRegistryCache || {}).length} reps`,
    `✓ Loaded ${Array.isArray(testimonialsCache) ? testimonialsCache.length : 0} testimonials`
  );
}

// Routes

/**
 * GET /api/health - Health check
 */
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    stores: storesCache?.length || 0,
    reps: Object.keys(repRegistryCache || {}).length,
  });
});

/**
 * GET /api/rep-registry - Get all representatives
 */
app.get('/api/rep-registry', (req, res) => {
  if (!repRegistryCache) {
    return res.status(500).json({ error: 'Failed to load rep registry' });
  }
  res.json(repRegistryCache);
});

/**
 * POST /api/rep/validate - Validate rep credentials
 */
app.post('/api/rep/validate', (req, res) => {
  const { phone } = req.body;
  if (!phone || !repRegistryCache || !repRegistryCache[phone]) {
    return res.status(401).json({ error: 'Invalid credentials' });
  }
  res.json({
    phone,
    ...repRegistryCache[phone],
  });
});

/**
 * GET /api/stores - Get all stores
 */
app.get('/api/stores', (req, res) => {
  if (!storesCache) {
    return res.status(500).json({ error: 'Failed to load stores' });
  }
  res.json(storesCache);
});

/**
 * GET /api/stores/search - Search stores
 */
app.get('/api/stores/search', (req, res) => {
  if (!storesCache) {
    return res.status(500).json({ error: 'Failed to load stores' });
  }

  const { q = '', city = '', chain = '', state = '' } = req.query;

  let results = storesCache.filter((store) => {
    const matchesQuery =
      !q ||
      store.StoreName.toLowerCase().includes(q.toLowerCase()) ||
      store.City.toLowerCase().includes(q.toLowerCase());

    const matchesCity = !city || store.City === city;
    const matchesChain = !chain || store.GroceryChain === chain;
    const matchesState = !state || store.State === state;

    return matchesQuery && matchesCity && matchesChain && matchesState;
  });

  // Limit results to 100
  results = results.slice(0, 100);

  res.json(results);
});

/**
 * GET /api/stores/:storeName - Get single store details
 */
app.get('/api/stores/:storeName', (req, res) => {
  if (!storesCache) {
    return res.status(500).json({ error: 'Failed to load stores' });
  }

  const store = storesCache.find(
    (s) => s.StoreName === decodeURIComponent(req.params.storeName)
  );

  if (!store) {
    return res.status(404).json({ error: 'Store not found' });
  }

  res.json(store);
});

/**
 * GET /api/pricing/:storeName - Get store pricing with all plans
 */
app.get('/api/pricing/:storeName', (req, res) => {
  if (!storesCache) {
    return res.status(500).json({ error: 'Failed to load stores' });
  }

  const store = storesCache.find(
    (s) => s.StoreName === decodeURIComponent(req.params.storeName)
  );

  if (!store) {
    return res.status(404).json({ error: 'Store not found' });
  }

  // Calculate pricing plans
  const singleAd = store.SingleAd;
  const doubleAd = store.DoubleAd;

  const plans = {
    monthly: {
      name: 'Monthly',
      singleAd: Math.round(singleAd / 12),
      doubleAd: Math.round(doubleAd / 12),
    },
    threeMonth: {
      name: '3-Month',
      singleAd: Math.round(singleAd / 4),
      doubleAd: Math.round(doubleAd / 4),
    },
    sixMonth: {
      name: '6-Month',
      singleAd: Math.round(singleAd / 2),
      doubleAd: Math.round(doubleAd / 2),
    },
    annualPif: {
      name: 'Annual (PIF)',
      singleAd,
      doubleAd,
    },
    coOpMonthly: {
      name: 'Co-Op Monthly',
      singleAd: Math.round((singleAd / 12) * 0.9),
      doubleAd: Math.round((doubleAd / 12) * 0.9),
    },
    coOpAnnual: {
      name: 'Co-Op Annual',
      singleAd: Math.round(singleAd * 0.9),
      doubleAd: Math.round(doubleAd * 0.9),
    },
  };

  res.json({
    storeName: store.StoreName,
    ...store,
    plans,
  });
});

/**
 * GET /api/testimonials - Get testimonials
 */
app.get('/api/testimonials', (req, res) => {
  if (!testimonialsCache) {
    return res.status(500).json({ error: 'Failed to load testimonials' });
  }
  res.json(testimonialsCache);
});

/**
 * GET /api/prospects - Get prospect data
 */
app.get('/api/prospects', (req, res) => {
  if (!prospectsCache) {
    return res.status(500).json({ error: 'Failed to load prospects' });
  }
  res.json(prospectsCache);
});

/**
 * SPA fallback - serve index.html for all non-API routes
 */
app.get('*', (req, res) => {
  const indexPath = path.join(distPath, 'index.html');
  if (fs.existsSync(indexPath)) {
    console.log(`Serving SPA from ${indexPath} for ${req.path}`);
    res.sendFile(indexPath);
  } else {
    console.error(`index.html not found at ${indexPath}`);
    res.status(404).json({ error: 'index.html not found', path: indexPath });
  }
});

// Start server
initializeCaches();

app.listen(PORT, () => {
  console.log(`\n✓ PWA API Server running on http://localhost:${PORT}`);
  console.log(`\n Available endpoints:`);
  console.log(`  GET  /api/health`);
  console.log(`  GET  /api/rep-registry`);
  console.log(`  POST /api/rep/validate`);
  console.log(`  GET  /api/stores`);
  console.log(`  GET  /api/stores/search`);
  console.log(`  GET  /api/stores/:storeName`);
  console.log(`  GET  /api/pricing/:storeName`);
  console.log(`  GET  /api/testimonials`);
  console.log(`  GET  /api/prospects\n`);
});
