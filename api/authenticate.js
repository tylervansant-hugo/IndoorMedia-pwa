export default async function handler(req, res) {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
  res.setHeader('Access-Control-Allow-Headers', 'X-CSRF-Token,X-Requested-With,Accept,Accept-Version,Content-Length,Content-MD5,Content-Type,Date,X-Api-Version');

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { email, password } = req.body;

  if (!email || !password) {
    return res.status(400).json({ error: 'Email and password required' });
  }

  if (!email.endsWith('@indoormedia.com')) {
    return res.status(400).json({ error: 'Must use @indoormedia.com email' });
  }

  if (password.length < 6) {
    return res.status(400).json({ error: 'Password must be at least 6 characters' });
  }

  try {
    // For Vercel: Accept any @indoormedia.com email with valid password
    // Real authentication happens when using local server
    const repName = email.split('@')[0];
    const sessionToken = Buffer.from(`${email}:${Date.now()}`).toString('base64');

    console.log(`✅ Session created for: ${email}`);

    return res.status(200).json({
      success: true,
      id: repName,
      name: repName.replace(/[._]/g, ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
      email: email,
      sessionToken: sessionToken,
      role: 'rep',
      authenticated: true,
      note: 'Using local server for real Rogue scraping'
    });

  } catch (error) {
    console.error('Authentication error:', error);
    return res.status(500).json({ error: 'Authentication failed. Please try again.' });
  }
}
