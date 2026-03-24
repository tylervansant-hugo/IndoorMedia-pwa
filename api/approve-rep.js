import fs from 'fs';
import path from 'path';

const PENDING_FILE = path.join(process.cwd(), 'data', 'pending_reps.json');
const REGISTRY_FILE = path.join(process.cwd(), 'public', 'data', 'rep_registry.json');

function loadPending() {
  try {
    if (fs.existsSync(PENDING_FILE)) {
      return JSON.parse(fs.readFileSync(PENDING_FILE, 'utf-8'));
    }
  } catch {}
  return [];
}

function savePending(data) {
  fs.writeFileSync(PENDING_FILE, JSON.stringify(data, null, 2));
}

function loadRegistry() {
  try {
    if (fs.existsSync(REGISTRY_FILE)) {
      return JSON.parse(fs.readFileSync(REGISTRY_FILE, 'utf-8'));
    }
  } catch {}
  return {};
}

function saveRegistry(data) {
  fs.writeFileSync(REGISTRY_FILE, JSON.stringify(data, null, 2));
}

export default function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,DELETE,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') return res.status(200).end();

  // Simple auth check — manager must provide the manager key
  const authKey = req.headers['authorization'] || req.query.key || '';
  const MANAGER_KEY = process.env.MANAGER_KEY || 'indoormedia2026';
  
  if (authKey !== MANAGER_KEY && authKey !== `Bearer ${MANAGER_KEY}`) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const { id, action } = req.body || {};

  if (!id) {
    return res.status(400).json({ error: 'Missing rep id' });
  }

  const pending = loadPending();
  const repIndex = pending.findIndex(p => p.id === id);

  if (repIndex === -1) {
    return res.status(404).json({ error: 'Registration not found' });
  }

  const rep = pending[repIndex];

  if (action === 'approve') {
    // Add to registry
    const registry = loadRegistry();
    registry[rep.id] = {
      contract_name: rep.name,
      display_name: rep.name,
      email: rep.email || '',
      role: 'rep',
      registered_at: new Date().toISOString().split('T')[0],
      base_location: rep.location || 'Territory TBD'
    };
    saveRegistry(registry);

    // Remove from pending
    pending.splice(repIndex, 1);
    savePending(pending);

    return res.status(200).json({ success: true, message: `${rep.name} approved`, rep: registry[rep.id] });
  }

  if (action === 'reject') {
    pending.splice(repIndex, 1);
    savePending(pending);
    return res.status(200).json({ success: true, message: `${rep.name} rejected` });
  }

  return res.status(400).json({ error: 'Invalid action. Use "approve" or "reject".' });
}
