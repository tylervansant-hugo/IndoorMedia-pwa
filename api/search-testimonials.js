import fs from 'fs';
import path from 'path';

// Cache file path (relative to project root)
const CACHE_FILE = path.join(process.cwd(), 'data', 'testimonials_cache.json');
const SITE_URL = 'https://testimonials.indoormedia.com';

// Load testimonials from cache
function loadTestimonials() {
  try {
    if (fs.existsSync(CACHE_FILE)) {
      const data = fs.readFileSync(CACHE_FILE, 'utf-8');
      return JSON.parse(data);
    }
  } catch (err) {
    console.error('Failed to load testimonials cache:', err);
  }
  return [];
}

// Search testimonials by keyword
function searchTestimonials(keyword) {
  const testimonials = loadTestimonials();
  if (!testimonials || testimonials.length === 0) {
    return [];
  }

  const keywordLower = keyword.toLowerCase();
  return testimonials.filter((t) => {
    const searchable = (t.searchable || '').toLowerCase();
    return searchable.includes(keywordLower);
  });
}

export default function handler(req, res) {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
  res.setHeader(
    'Access-Control-Allow-Headers',
    'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version'
  );

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  const { q } = req.query;

  if (!q || typeof q !== 'string' || q.trim().length === 0) {
    return res.status(400).json({ error: 'Missing search query parameter: q' });
  }

  try {
    const results = searchTestimonials(q.trim());
    
    return res.status(200).json({
      query: q.trim(),
      count: results.length,
      results: results.map((t) => ({
        id: t.id,
        business: t.business,
        comment: t.comment,
        url: t.url,
      })),
    });
  } catch (err) {
    console.error('Search error:', err);
    return res.status(500).json({ error: 'Internal server error' });
  }
}
