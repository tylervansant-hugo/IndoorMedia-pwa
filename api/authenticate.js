import puppeteer from 'puppeteer-extra';
import StealthPlugin from 'puppeteer-extra-plugin-stealth';

puppeteer.use(StealthPlugin());

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

  let browser;
  try {
    console.log(`Authenticating: ${email}`);

    browser = await puppeteer.launch({
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });
    await page.setDefaultTimeout(30000);

    // Navigate to sales.indoormedia.com
    console.log('Navigating to sales.indoormedia.com');
    await page.goto('https://sales.indoormedia.com/', { waitUntil: 'networkidle2' });

    // Look for login form
    const loginForm = await page.$('form');
    
    if (loginForm) {
      // Fill email field
      const emailInputs = await page.$$('input[type="email"], input[type="text"]');
      for (const input of emailInputs) {
        const name = await input.evaluate(el => el.name || el.id);
        if (name.toLowerCase().includes('email') || name.toLowerCase().includes('user')) {
          await input.fill(email);
          break;
        }
      }

      // Fill password field
      const passwordInputs = await page.$$('input[type="password"]');
      if (passwordInputs.length > 0) {
        await passwordInputs[0].fill(password);
      }

      // Submit form
      const submitButtons = await page.$$('button[type="submit"], input[type="submit"]');
      if (submitButtons.length > 0) {
        await submitButtons[0].click();
        await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 }).catch(() => {});
        await page.waitForTimeout(2000);
      }
    }

    // Check if authentication succeeded
    const currentUrl = page.url();
    const isLoggedIn = !currentUrl.includes('login') && !currentUrl.includes('signin');

    if (!isLoggedIn) {
      console.log('Authentication failed for:', email);
      await browser.close();
      return res.status(401).json({ error: 'Invalid email or password' });
    }

    console.log('✅ Authentication successful for:', email);

    // Extract rep info from page if available
    const repInfo = await page.evaluate(() => {
      const nameElement = document.querySelector('[data-user-name], .user-name, .profile-name');
      return {
        name: nameElement?.textContent?.trim() || '',
      };
    });

    await browser.close();

    // Return success with session info (NOT the password)
    return res.status(200).json({
      success: true,
      id: email.split('@')[0], // Use username part as ID
      name: repInfo.name || email.split('@')[0],
      email: email,
      sessionToken: Buffer.from(`${email}:${Date.now()}`).toString('base64'),
      role: 'rep',
      authenticated: true
    });

  } catch (error) {
    console.error('Authentication error:', error);
    if (browser) {
      try {
        await browser.close();
      } catch (e) {
        console.error('Error closing browser:', e);
      }
    }
    return res.status(500).json({ error: 'Authentication failed. Please try again.' });
  }
}
