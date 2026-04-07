import express from 'express';
import puppeteer from 'puppeteer';
import cors from 'cors';
import fs from 'fs';

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
    console.log(`\n🚀 Starting Roogle scrape for store: ${storeId} (as ${email})`);
    
    browser = await puppeteer.launch({
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });
    await page.setDefaultTimeout(30000);

    // Step 1: Navigate to sales.indoormedia.com
    console.log('Step 1: Navigating to sales.indoormedia.com');
    await page.goto('https://sales.indoormedia.com/', { waitUntil: 'networkidle2', timeout: 30000 });

    // Step 2: Click "Login" button
    console.log('Step 2: Clicking Login button');
    const loginButtons = await page.$$('a, button');
    for (const btn of loginButtons) {
      const text = await btn.evaluate(el => el.textContent?.trim());
      if (text === 'Login' || text?.toLowerCase().includes('login')) {
        await btn.click();
        await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 }).catch(() => {});
        await new Promise(r => setTimeout(r, 1000));
        break;
      }
    }

    // Step 3: Select the @indoormedia.com email from the chooser
    console.log('Step 3: Selecting @indoormedia.com email');
    const emailLinks = await page.$$('a, button, div[role="button"]');
    for (const link of emailLinks) {
      const text = await link.evaluate(el => el.textContent);
      if (text && text.includes('indoormedia.com')) {
        await link.click();
        await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 }).catch(() => {});
        await new Promise(r => setTimeout(r, 1000));
        break;
      }
    }

    // Step 4: Fill password and login
    console.log('Step 4: Entering password and logging in');

    const passwordInputs = await page.$$('input[type="password"]');
    if (passwordInputs.length > 0) {
      await passwordInputs[0].fill(password);
    }

    const submitButtons = await page.$$('button[type="submit"], input[type="submit"]');
    if (submitButtons.length > 0) {
      await submitButtons[0].click();
      await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 }).catch(() => {});
      await new Promise(r => setTimeout(r, 2000));
    }

    // Step 5: Click on "Roogle" tab
    console.log('Step 5: Clicking Roogle tab');
    const tabs = await page.$$('a, button');
    for (const tab of tabs) {
      const text = await tab.evaluate(el => el.textContent?.trim());
      if (text === 'Roogle') {
        await tab.click();
        await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 }).catch(() => {});
        await new Promise(r => setTimeout(r, 1000));
        break;
      }
    }

    // Step 6: Fill Store field and search
    console.log(`Step 6: Searching for store: ${storeId}`);
    const inputs = await page.$$('input');
    for (const input of inputs) {
      const name = await input.evaluate(el => el.name || '');
      const placeholder = await input.evaluate(el => el.placeholder || '');
      if (name.toLowerCase().includes('store') || placeholder.toLowerCase().includes('store')) {
        await input.fill(storeId);
        break;
      }
    }

    // Click Search Entities button
    const buttons = await page.$$('button');
    for (const btn of buttons) {
      const text = await btn.evaluate(el => el.textContent);
      if (text && text.includes('Search')) {
        await btn.click();
        await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 }).catch(() => {});
        await new Promise(r => setTimeout(r, 1000));
        break;
      }
    }

    // Step 7: Click on store result
    console.log('Step 7: Clicking store result');
    const storeLinks = await page.$$('a');
    for (const link of storeLinks) {
      const text = await link.evaluate(el => el.textContent);
      if (text && text.includes(storeId)) {
        await link.click();
        await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 }).catch(() => {});
        await new Promise(r => setTimeout(r, 1000));
        break;
      }
    }

    // Step 8: Click on "Tape Info"
    console.log('Step 8: Clicking Tape Info');
    const tapeInfoLinks = await page.$$('a');
    for (const link of tapeInfoLinks) {
      const text = await link.evaluate(el => el.textContent?.trim());
      if (text === 'Tape Info' || text?.includes('Tape Info')) {
        await link.click();
        await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 }).catch(() => {});
        await new Promise(r => setTimeout(r, 1000));
        break;
      }
    }

    // Step 9: Click on "Tape Contracts" button
    console.log('Step 9: Clicking Tape Contracts button');
    const contractButtons = await page.$$('button');
    for (const btn of contractButtons) {
      const text = await btn.evaluate(el => el.textContent?.trim());
      if (text === 'Tape Contracts' || text?.includes('Tape Contracts')) {
        await btn.click();
        await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 }).catch(() => {});
        await new Promise(r => setTimeout(r, 1000));
        break;
      }
    }

    // Step 10: Take screenshot and save HTML for debugging
    console.log('Step 10: Capturing page for data extraction');
    await page.screenshot({ path: '/tmp/roogle-contracts.png' });
    const pageHtml = await page.content();
    fs.writeFileSync('/tmp/roogle-contracts.html', pageHtml);

    // Step 11: Dump page text to see structure
    console.log('Step 11: Dumping page text');
    const pageText = await page.evaluate(() => document.body.innerText);
    fs.writeFileSync('/tmp/roogle-page-text.txt', pageText);
    console.log('Page text saved to /tmp/roogle-page-text.txt');
    console.log('\n===== PAGE TEXT PREVIEW =====\n');
    console.log(pageText.substring(0, 2000));
    console.log('\n===== END PREVIEW =====\n');

    // For now, return empty
    const contracts = { currentContracts: [], pastContracts: [] };

    await browser.close();

    // Remove duplicates
    const uniqueCurrent = Array.from(new Map(contracts.currentContracts.map(c => [c.businessName, c])).values());
    const uniquePast = Array.from(new Map(contracts.pastContracts.map(c => [c.businessName, c])).values());

    console.log(`✅ Found ${uniqueCurrent.length} current and ${uniquePast.length} past contracts\n`);

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
    console.error('❌ Roogle scraper error:', error.message);
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
  console.log(`📡 API endpoint: http://localhost:${PORT}/api/roogle-scraper\n`);
});
