import { chromium } from 'playwright';

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
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    // Login to Roogle
    await page.goto('https://sales.indoormedia.com/');
    await page.fill('input[type="email"]', email);
    await page.fill('input[type="password"]', password);
    await page.click('button[type="submit"]');
    
    // Wait for login to complete
    await page.waitForNavigation({ waitUntil: 'networkidle' });

    // Navigate to store contracts
    await page.goto(`https://sales.indoormedia.com/store/ContractActivityTape?id=${storeId}`);
    await page.waitForLoadState('networkidle');

    // Extract contracts from page
    const contracts = await page.evaluate(() => {
      const currentContracts = [];
      const pastContracts = [];

      // Parse current contracts (green section)
      const currentRows = document.querySelectorAll('table.current-contracts tbody tr'); // Adjust selector based on actual HTML
      currentRows.forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length >= 4) {
          currentContracts.push({
            businessName: cells[0]?.textContent?.trim() || '',
            status: cells[1]?.textContent?.trim() || 'Active',
            contractType: cells[2]?.textContent?.trim() || '',
            price: cells[3]?.textContent?.trim() || '',
            category: cells[4]?.textContent?.trim() || '',
            isActive: true
          });
        }
      });

      // Parse past contracts (bottom section)
      const pastRows = document.querySelectorAll('table.past-contracts tbody tr'); // Adjust selector
      pastRows.forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length >= 4) {
          pastContracts.push({
            businessName: cells[0]?.textContent?.trim() || '',
            status: cells[1]?.textContent?.trim() || 'Terminated',
            contractType: cells[2]?.textContent?.trim() || '',
            price: cells[3]?.textContent?.trim() || '',
            category: cells[4]?.textContent?.trim() || '',
            isActive: false
          });
        }
      });

      return { currentContracts, pastContracts };
    });

    await browser.close();

    return res.status(200).json({
      success: true,
      storeId,
      current: contracts.currentContracts,
      past: contracts.pastContracts,
      all: [...contracts.currentContracts, ...contracts.pastContracts]
    });

  } catch (error) {
    console.error('Roogle scraper error:', error);
    if (browser) await browser.close();
    return res.status(500).json({ error: error.message });
  }
}
