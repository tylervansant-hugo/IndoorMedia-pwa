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

  const { storeId, email, password } = req.body;

  if (!storeId || !email || !password) {
    return res.status(400).json({ error: 'storeId, email, and password required' });
  }

  let browser;
  try {
    console.log(`Scraping Roogle for store: ${storeId} (as ${email})`);

    browser = await puppeteer.launch({
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });
    await page.setDefaultTimeout(30000);

    // Step 1: Navigate to sales.indoormedia.com and authenticate
    console.log('Step 1: Authenticating with sales.indoormedia.com');
    await page.goto('https://sales.indoormedia.com/', { waitUntil: 'networkidle2' });

    // Fill login form
    const emailInputs = await page.$$('input[type="email"], input[type="text"]');
    for (const input of emailInputs) {
      const name = await input.evaluate(el => el.name || el.id);
      if (name.toLowerCase().includes('email') || name.toLowerCase().includes('user')) {
        await input.fill(email);
        break;
      }
    }

    const passwordInputs = await page.$$('input[type="password"]');
    if (passwordInputs.length > 0) {
      await passwordInputs[0].fill(password);
    }

    const submitButtons = await page.$$('button[type="submit"], input[type="submit"]');
    if (submitButtons.length > 0) {
      await submitButtons[0].click();
      await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(2000);
    }

    // Step 2: Navigate to Roogle (skynet.indoormedia.com)
    console.log('Step 2: Navigating to Roogle');
    await page.goto('https://skynet.indoormedia.com/', { waitUntil: 'networkidle2' });

    // Step 3: Search for store
    console.log(`Step 3: Searching for store: ${storeId}`);
    const storeInputs = await page.$$('input');
    let storeField = null;

    for (const input of storeInputs) {
      const placeholder = await input.evaluate(el => el.placeholder || el.name || '');
      if (placeholder.toLowerCase().includes('store')) {
        storeField = input;
        break;
      }
    }

    if (storeField) {
      await storeField.fill(storeId);

      // Click Search button
      const buttons = await page.$$('button');
      for (const btn of buttons) {
        const text = await btn.evaluate(el => el.textContent);
        if (text && text.includes('Search')) {
          await btn.click();
          await page.waitForLoadState('networkidle2');
          break;
        }
      }
    }

    // Step 4: Click store result
    console.log('Step 4: Clicking store result');
    const storeLinks = await page.$$('a');
    for (const link of storeLinks) {
      const text = await link.evaluate(el => el.textContent);
      if (text && text.includes(storeId)) {
        await link.click();
        await page.waitForLoadState('networkidle2');
        break;
      }
    }

    // Step 5: Click Tape Info
    console.log('Step 5: Navigating to Tape Info');
    const allElements = await page.$$('a, button');
    for (const elem of allElements) {
      const text = await elem.evaluate(el => el.textContent?.trim());
      if (text === 'Tape Info' || text?.includes('Tape Info')) {
        await elem.click();
        await page.waitForLoadState('networkidle2');
        break;
      }
    }

    // Step 6: Click Tape Contracts
    console.log('Step 6: Opening Tape Contracts');
    const allButtons = await page.$$('button');
    for (const btn of allButtons) {
      const btnText = await btn.evaluate(el => el.textContent?.trim());
      if (btnText === 'Tape Contracts' || btnText?.includes('Tape Contracts')) {
        await btn.click();
        await page.waitForLoadState('networkidle2');
        break;
      }
    }

    // Step 7: Extract contract data
    console.log('Step 7: Extracting contract data');
    const contracts = await page.evaluate(() => {
      const currentContracts = [];
      const pastContracts = [];

      let isCurrentSection = true;
      const rows = document.querySelectorAll('tr');

      rows.forEach(row => {
        const rowText = row.textContent;

        if (rowText.includes('Current Contracts')) {
          isCurrentSection = true;
          return;
        }
        if (rowText.includes('Past Contracts')) {
          isCurrentSection = false;
          return;
        }

        const cells = row.querySelectorAll('td');
        if (cells.length >= 5) {
          const businessName = cells[1]?.textContent?.trim() || '';
          const status = cells[3]?.textContent?.trim() || '';
          const price = cells[4]?.textContent?.trim() || '';
          const category = cells[6]?.textContent?.trim() || '';

          if (businessName && status) {
            const contract = {
              businessName,
              status,
              price,
              category,
              isActive: isCurrentSection
            };

            if (isCurrentSection) {
              currentContracts.push(contract);
            } else {
              pastContracts.push(contract);
            }
          }
        }
      });

      return { currentContracts, pastContracts };
    });

    await browser.close();

    // Remove duplicates
    const uniqueCurrent = Array.from(new Map(contracts.currentContracts.map(c => [c.businessName, c])).values());
    const uniquePast = Array.from(new Map(contracts.pastContracts.map(c => [c.businessName, c])).values());

    console.log(`✅ Found ${uniqueCurrent.length} current and ${uniquePast.length} past contracts`);

    return res.status(200).json({
      success: true,
      source: 'Real Roogle Data (Live Scrape)',
      storeId,
      email,
      current: uniqueCurrent,
      past: uniquePast,
      all: [...uniqueCurrent, ...uniquePast]
    });

  } catch (error) {
    console.error('Roogle scraper error:', error);
    if (browser) {
      try {
        await browser.close();
      } catch (e) {
        console.error('Error closing browser:', e);
      }
    }
    return res.status(500).json({ error: error.message || 'Scraper failed' });
  }
}
