import fs from 'fs';
import path from 'path';

const PENDING_FILE = path.join(process.cwd(), 'data', 'pending_reps.json');

function loadPending() {
  try {
    if (fs.existsSync(PENDING_FILE)) {
      return JSON.parse(fs.readFileSync(PENDING_FILE, 'utf-8'));
    }
  } catch {}
  return [];
}

function savePending(data) {
  const dir = path.dirname(PENDING_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(PENDING_FILE, JSON.stringify(data, null, 2));
}

export default function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,DELETE,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') return res.status(200).end();

  // GET — list pending registrations
  if (req.method === 'GET') {
    return res.status(200).json({ pending: loadPending() });
  }

  // POST — new registration request
  if (req.method === 'POST') {
    const { name, email, location } = req.body || {};
    if (!name || typeof name !== 'string' || !name.trim()) {
      return res.status(400).json({ error: 'Name is required' });
    }

    const pending = loadPending();
    
    // Check for duplicates
    if (pending.find(p => p.name.toLowerCase() === name.trim().toLowerCase())) {
      return res.status(409).json({ error: 'Registration already pending for this name' });
    }

    const registration = {
      id: name.trim().toLowerCase().replace(/\s+/g, '_'),
      name: name.trim(),
      email: (email || '').trim(),
      location: (location || '').trim() || 'Territory TBD',
      requestedAt: new Date().toISOString(),
      status: 'pending'
    };

    pending.push(registration);
    savePending(pending);

    // Notify manager via Telegram (best-effort, don't block)
    const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
    const MANAGER_CHAT_ID = process.env.MANAGER_CHAT_ID || '8548368719';
    if (BOT_TOKEN) {
      const msg = `🆕 New Rep Registration!\n\n👤 ${registration.name}\n📧 ${registration.email || 'No email'}\n📍 ${registration.location}\n\nApprove in the PWA → Manage tab`;
      fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: MANAGER_CHAT_ID, text: msg })
      }).catch(() => {}); // Fire and forget
    }

    return res.status(201).json({ success: true, registration });
  }

  return res.status(405).json({ error: 'Method not allowed' });
}
