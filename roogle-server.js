const express = require('express');
const puppeteer = require('puppeteer');
const cors = require('cors');

const app = express();
const PORT = 3001;

app.use(cors());
app.use(express.json());

app.post('/api/roogle-scraper', async (req, res) => {
  const { storeId, email, password } = req.body;
  
  if (!storeId || !email || !password) {
    return res.status(400).json({ error: 'storeId, email, and password required' });
  }

  let browser;
  try {
    console.log(`Scraping Roogle for store: ${storeId}`);
    
    browser = await puppeteer.launch({
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });
    await page.setDefaultTimeout(30000);

    // Navigate to Roogle
    console.log('Navigating to skynet.indoormedia.com');
    await page.goto('https://skynet.indoormedia.com/', { waitUntil: 'networkidle2' });
    
    // Check if login is needed
    const loginForm = await page.$('input[type="email"]');
    if (loginForm) {
      console.log('Logging in...');
      await page.type('input[type="email"]', email);
      await page.type('input[type="password"]', password);
      await page.click('button[type="submit"]');
      await page.waitForNavigation({ waitUntil: 'networkidle2' });
    }

    // Find and fill the Store field
    console.log('Searching for store:', storeId);
    const storeInputs = await page.$$('input');
    let storeField = null;
    
    for (const input of storeInputs) {
      const placeholder = await input.evaluate(el => el.placeholder);
      if (placeholder && placeholder.toLowerCase().includes('store')) {
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
          break;
        }
      }
      
      await page.waitForLoadState('networkidle2');
      console.log('Store search complete');
    }

    // Click on the store result
    console.log('Clicking store result');
    const storeLinks = await page.$$('a');
    for (const link of storeLinks) {
      const text = await link.evaluate(el => el.textContent);
      if (text && text.includes(storeId)) {
        await link.click();
        await page.waitForLoadState('networkidle2');
        break;
      }
    }

    // Click on Tape Info tab
    console.log('Navigating to Tape Info');
    const allElements = await page.$$('a, button');
    for (const elem of allElements) {
      const text = await elem.evaluate(el => el.textContent?.trim());
      if (text === 'Tape Info' || text?.includes('Tape Info')) {
        await elem.click();
        await page.waitForLoadState('networkidle2');
        break;
      }
    }

    // Click on Tape Contracts button
    console.log('Opening Tape Contracts');
    const allButtons = await page.$$('button');
    for (const btn of allButtons) {
      const btnText = await btn.evaluate(el => el.textContent?.trim());
      if (btnText === 'Tape Contracts' || btnText?.includes('Tape Contracts')) {
        await btn.click();
        await page.waitForLoadState('networkidle2');
        break;
      }
    }

    // Extract contracts
    console.log('Extracting contract data');
    const contracts = await page.evaluate(() => {
      const currentContracts = [];
      const pastContracts = [];
      
      let isCurrentSection = true;
      const rows = document.querySelectorAll('tr');

      rows.forEach(row => {
        const rowText = row.textContent;
        
        // Detect section headers
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

    console.log(`Found ${uniqueCurrent.length} current and ${uniquePast.length} past contracts`);

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
});

app.listen(PORT, () => {
  console.log(`🚀 Roogle scraper server running at http://localhost:${PORT}`);
  console.log(`📡 API endpoint: http://localhost:${PORT}/api/roogle-scraper`);
});
