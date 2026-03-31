import puppeteer from 'puppeteer-extra';
import StealthPlugin from 'puppeteer-extra-plugin-stealth';

puppeteer.use(StealthPlugin());

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { storeId } = req.body;
  
  if (!storeId) {
    return res.status(400).json({ error: 'storeId required' });
  }

  const email = process.env.ROOGLE_EMAIL;
  const password = process.env.ROOGLE_PASSWORD;
  
  if (!email || !password) {
    return res.status(500).json({ error: 'Roogle credentials not configured' });
  }

  let browser;
  try {
    // Use chrome-aws-lambda for serverless
    const executablePath = process.env.CHROME_EXECUTABLE_PATH || undefined;
    
    browser = await puppeteer.launch({
      headless: 'new',
      executablePath,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage'
      ]
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });
    await page.setDefaultTimeout(30000);

    // Login to Roogle
    await page.goto('https://sales.indoormedia.com/', { waitUntil: 'networkidle2' });
    
    // Fill login form
    await page.type('input[type="email"]', email);
    await page.type('input[type="password"]', password);
    await page.click('button[type="submit"]');
    
    // Wait for navigation after login
    await page.waitForNavigation({ waitUntil: 'networkidle2' });

    // Navigate to store contracts
    await page.goto(`https://sales.indoormedia.com/store/ContractActivityTape?id=${storeId}`, { 
      waitUntil: 'networkidle2' 
    });

    // Extract contracts from page
    const contracts = await page.evaluate(() => {
      const currentContracts = [];
      const pastContracts = [];

      // Look for all rows in tables
      const rows = document.querySelectorAll('tr');
      let isCurrentSection = true;

      rows.forEach(row => {
        // Check if this is a section header
        if (row.textContent.includes('Terminated') || row.textContent.includes('Past')) {
          isCurrentSection = false;
        }

        const cells = row.querySelectorAll('td');
        if (cells.length >= 3) {
          const contract = {
            businessName: cells[0]?.textContent?.trim() || '',
            status: cells[1]?.textContent?.trim() || '',
            contractType: cells[2]?.textContent?.trim() || '',
            price: cells[3]?.textContent?.trim() || '',
            category: cells[4]?.textContent?.trim() || '',
          };

          if (contract.businessName && contract.status) {
            if (isCurrentSection || contract.status.toLowerCase().includes('active')) {
              contract.isActive = true;
              currentContracts.push(contract);
            } else {
              contract.isActive = false;
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

    return res.status(200).json({
      success: true,
      storeId,
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
