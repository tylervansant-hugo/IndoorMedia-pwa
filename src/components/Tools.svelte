<script>
  import { onMount } from 'svelte';
  import { PDFDocument, rgb, StandardFonts } from 'pdf-lib';
  import { user } from '../lib/stores.js';
  
  let view = 'main'; // main, roi, rates, testimonials, audit, counter-sign, submit-testimonial
  let stores = [];
  let allStores = [];
  let searchQuery = '';
  let selectedStore = null;
  
  // Testimonials state
  let testimonialQuery = '';
  let testimonialResults = [];
  let testimonialLoading = false;
  let testimonialError = '';
  let testimonialData = null;
  
  // Audit state
  let auditStoreNum = null;
  let auditStep = 1; // 1: select store, 2: shipment dates, 3: enter inventory, 4: confirm, 5: report
  let auditCases = '';
  let auditRolls = '';
  let auditDate = new Date().toISOString().split('T')[0];
  let auditPerformedDate = new Date().toISOString().split('T')[0];
  let auditStartingCases = '';
  let auditLastShipmentDate = '';
  let auditNextShipmentDate = '';
  let auditReport = null;

  // ROI Calculator state
  let roiBusinessName = '';
  let roiStoreSearch = '';
  let roiSelectedStore = null;
  let roiAdSize = 'single'; // single or double
  let roiAdCost = '';
  let roiQuarters = 4;
  let roiRedemptions = '';
  let roiTicket = '';
  let roiDiscount = '';
  let roiCogs = '';
  let roiVisitsPerYear = 1;
  let roiResult = null;

  $: roiStoreResults = roiStoreSearch.length >= 2
    ? allStores.filter(s =>
        s.StoreName?.toLowerCase().includes(roiStoreSearch.toLowerCase()) ||
        s.GroceryChain?.toLowerCase().includes(roiStoreSearch.toLowerCase()) ||
        s.City?.toLowerCase().includes(roiStoreSearch.toLowerCase())
      ).slice(0, 8)
    : [];

  // Auto-update ad cost when ad size or store changes
  $: if (roiSelectedStore) {
    roiAdCost = roiAdSize === 'double'
      ? (roiSelectedStore.DoubleAd || '')
      : (roiSelectedStore.SingleAd || '');
  }

  function selectRoiStore(store) {
    roiSelectedStore = store;
    roiStoreSearch = '';
  }

  function calculateROI() {
    const annualAdCost = parseFloat(roiAdCost) || 0;
    const quarters = parseInt(roiQuarters) || 4;
    const months = quarters * 3;
    // Annual cost, pro-rate for fewer quarters
    const totalAdCost = Math.round(annualAdCost * (quarters / 4));
    const costPerQuarter = Math.round(annualAdCost / 4);
    const redemptions = parseInt(roiRedemptions) || 0;
    const ticket = parseFloat(roiTicket) || 0;
    const discount = parseFloat(roiDiscount) || 0;
    const cogsPercent = parseFloat(roiCogs) || 0;
    const visitsPerYear = parseInt(roiVisitsPerYear) || 1;
    
    const monthlyRevenue = redemptions * ticket * (visitsPerYear / 12);
    const monthlyDiscounts = redemptions * discount;
    const monthlyCogs = monthlyRevenue * (cogsPercent / 100);
    const monthlyProfit = monthlyRevenue - monthlyDiscounts - monthlyCogs;
    
    const totalRevenue = monthlyRevenue * months;
    const totalDiscounts = monthlyDiscounts * months;
    const totalCogs = monthlyCogs * months;
    const totalProfit = monthlyProfit * months;
    const campaignProfit = totalProfit - totalAdCost;
    const roiPercent = totalAdCost > 0 ? Math.round((campaignProfit / totalAdCost) * 100) : 0;
    
    // Break-even: how many redemptions per month to cover ad cost
    const profitPerRedemption = ticket - discount - (ticket * cogsPercent / 100);
    const breakEvenRedemptions = profitPerRedemption > 0 ? Math.ceil(totalAdCost / (profitPerRedemption * months)) : '∞';
    
    roiResult = {
      annualAdCost: Math.round(annualAdCost),
      costPerQuarter,
      totalAdCost: Math.round(totalAdCost),
      adSize: roiAdSize,
      quarters,
      months,
      monthlyRevenue: Math.round(monthlyRevenue),
      monthlyProfit: Math.round(monthlyProfit),
      totalRevenue: Math.round(totalRevenue),
      totalDiscounts: Math.round(totalDiscounts),
      totalCogs: Math.round(totalCogs),
      campaignProfit: Math.round(campaignProfit),
      roiPercent,
      cogsPercent,
      visitsPerYear,
      breakEvenRedemptions
    };
  }

  async function downloadRoiPdf() {
    if (!roiResult) return;
    const r = roiResult;
    const biz = roiBusinessName || 'Customer';
    const store = roiSelectedStore
      ? `${roiSelectedStore.GroceryChain} — ${roiSelectedStore.City}, ${roiSelectedStore.State} (${roiSelectedStore.StoreName})`
      : 'N/A';
    const repName = $user?.name || $user?.first_name || 'IndoorMedia Rep';

    const pdfDoc = await PDFDocument.create();
    const page = pdfDoc.addPage([612, 792]);
    const bold = await pdfDoc.embedFont('Helvetica-Bold');
    const reg = await pdfDoc.embedFont('Helvetica');

    // Header
    page.drawRectangle({ x: 0, y: 700, width: 612, height: 92, color: rgb(0.8, 0, 0) });
    page.drawText('ROI ANALYSIS REPORT', { x: 30, y: 745, size: 22, font: bold, color: rgb(1, 1, 1) });
    page.drawText('IndoorMedia Register Tape Advertising', { x: 30, y: 722, size: 12, font: reg, color: rgb(1, 0.9, 0.9) });
    page.drawText(new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }), { x: 30, y: 705, size: 10, font: reg, color: rgb(1, 0.85, 0.85) });

    let y = 670;
    const section = (title) => {
      y -= 14;
      page.drawText(title, { x: 40, y, size: 13, font: bold, color: rgb(0.1, 0.1, 0.1) });
      y -= 22;
    };
    const line = (label, value) => {
      page.drawText(label, { x: 50, y, size: 11, font: reg, color: rgb(0.3, 0.3, 0.3) });
      page.drawText(String(value), { x: 350, y, size: 11, font: bold, color: rgb(0.1, 0.1, 0.1) });
      y -= 20;
    };

    section('PREPARED FOR');
    line('Business:', biz);
    line('Store:', store);
    line('Prepared by:', repName);

    section('CAMPAIGN DETAILS');
    line('Ad Size:', r.adSize === 'double' ? 'Double Ad' : 'Single Ad');
    line('Annual Ad Rate:', `$${r.annualAdCost.toLocaleString()}`);
    line('Campaign Length:', `${r.quarters} quarter(s) / ${r.months} months`);
    line('Total Ad Investment:', `$${r.totalAdCost.toLocaleString()}${r.quarters < 4 ? ' (pro-rated)' : ''}`);

    section('ASSUMPTIONS');
    line('Monthly Redemptions:', roiRedemptions);
    line('Average Customer Spend:', `$${parseFloat(roiTicket || 0).toLocaleString()}`);
    line('Visits per Year:', `${r.visitsPerYear}`);
    line('Avg Discount per Coupon:', `$${parseFloat(roiDiscount || 0).toLocaleString()}`);
    line('COGS:', `${r.cogsPercent}%`);

    section('ROI BREAKDOWN');
    line('Gross Revenue:', `$${r.totalRevenue.toLocaleString()}`);
    line('Less Discounts:', `-$${r.totalDiscounts.toLocaleString()}`);
    line('Less COGS:', `-$${r.totalCogs.toLocaleString()}`);
    line('Less Ad Cost:', `-$${r.totalAdCost.toLocaleString()}`);
    y -= 5;
    page.drawLine({ start: { x: 50, y: y + 12 }, end: { x: 550, y: y + 12 }, thickness: 1.5, color: rgb(0.8, 0, 0) });
    y -= 5;
    page.drawText('NET PROFIT', { x: 50, y, size: 13, font: bold, color: rgb(0.1, 0.1, 0.1) });
    page.drawText(`$${r.campaignProfit.toLocaleString()}`, { x: 350, y, size: 13, font: bold, color: r.campaignProfit >= 0 ? rgb(0.18, 0.49, 0.2) : rgb(0.8, 0, 0) });
    y -= 25;
    page.drawText('RETURN ON INVESTMENT', { x: 50, y, size: 13, font: bold, color: rgb(0.1, 0.1, 0.1) });
    page.drawText(`${r.roiPercent}%`, { x: 350, y, size: 13, font: bold, color: r.roiPercent >= 0 ? rgb(0.18, 0.49, 0.2) : rgb(0.8, 0, 0) });
    y -= 25;
    line('Break-even Redemptions/mo:', String(r.breakEvenRedemptions));

    y -= 20;
    // Verdict box
    const verdictColor = r.roiPercent >= 100 ? rgb(0.91, 0.96, 0.91) : r.roiPercent >= 0 ? rgb(0.95, 0.98, 0.95) : rgb(1, 0.93, 0.93);
    const verdictTextColor = r.roiPercent >= 0 ? rgb(0.18, 0.49, 0.2) : rgb(0.8, 0.2, 0.2);
    page.drawRectangle({ x: 40, y: y - 10, width: 530, height: 40, color: verdictColor, borderColor: verdictTextColor, borderWidth: 1 });
    const verdict = r.roiPercent >= 100
      ? `Excellent ROI! $${r.campaignProfit.toLocaleString()} profit on a $${r.totalAdCost.toLocaleString()} investment.`
      : r.roiPercent >= 0
        ? `Positive ROI. Campaign generates $${r.campaignProfit.toLocaleString()} in profit.`
        : 'Negative ROI at these numbers. Adjust redemptions or ticket size.';
    page.drawText(verdict, { x: 55, y: y + 5, size: 11, font: bold, color: verdictTextColor });

    // Footer
    page.drawText('Prepared by IndoorMedia | indoormedia.com', { x: 40, y: 30, size: 9, font: reg, color: rgb(0.6, 0.6, 0.6) });

    const pdfBytes = await pdfDoc.save();
    const blob = new Blob([pdfBytes], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ROI_Report_${biz.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function exportRoiHtml() {
    if (!roiResult) return;
    const r = roiResult;
    const biz = roiBusinessName || 'Customer';
    const store = roiSelectedStore
      ? `${roiSelectedStore.GroceryChain} — ${roiSelectedStore.City}, ${roiSelectedStore.State} (${roiSelectedStore.StoreName})`
      : 'N/A';
    const date = new Date().toLocaleDateString();
    const repName = $user?.name || $user?.first_name || 'IndoorMedia Rep';

    const html = `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ROI Report — ${biz}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 24px; max-width: 600px; margin: 0 auto; background: #fff; }
  .header { background: linear-gradient(135deg, #CC0000, #8B0000); color: white; padding: 24px; border-radius: 12px; margin-bottom: 24px; text-align: center; }
  .header h1 { font-size: 22px; margin-bottom: 4px; }
  .header p { font-size: 14px; opacity: 0.9; }
  .section { margin-bottom: 20px; }
  .section h3 { font-size: 15px; color: #666; margin-bottom: 8px; border-bottom: 2px solid #eee; padding-bottom: 4px; }
  .row { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; background: #f9f9f9; border-radius: 8px; margin-bottom: 6px; }
  .row.highlight { background: #f0fff0; border: 2px solid #2e7d32; }
  .label { font-size: 13px; color: #555; }
  .value { font-size: 16px; font-weight: 700; }
  .green { color: #2e7d32; }
  .red { color: #c33; }
  .big { font-size: 22px; color: #2e7d32; }
  .footer { text-align: center; color: #999; font-size: 12px; margin-top: 30px; padding-top: 16px; border-top: 1px solid #eee; }
  .logo { font-size: 18px; font-weight: 700; color: #CC0000; margin-bottom: 4px; }
  @media print { body { padding: 12px; } .no-print { display: none; } }
</style></head><body>
<div class="header">
  <h1>📊 ROI Analysis Report</h1>
  <p>Prepared for: ${biz}</p>
  <p>${store} | ${date}</p>
</div>

<div class="section">
  <h3>👤 Details</h3>
  <div class="row"><span class="label">Business</span><span class="value">${biz}</span></div>
  <div class="row"><span class="label">Store</span><span class="value">${store}</span></div>
  <div class="row"><span class="label">Prepared By</span><span class="value">${repName}</span></div>
</div>

<div class="section">
  <h3>📋 Campaign Inputs</h3>
  <div class="row"><span class="label">Ad Size</span><span class="value">${r.adSize === 'double' ? 'Double Ad' : 'Single Ad'}</span></div>
  <div class="row"><span class="label">Annual Ad Rate</span><span class="value">$${r.annualAdCost.toLocaleString()}</span></div>
  <div class="row"><span class="label">Campaign</span><span class="value">${r.quarters} quarter(s) / ${r.months} months</span></div>
  <div class="row"><span class="label">Total Investment</span><span class="value">$${r.totalAdCost.toLocaleString()}</span></div>
  <div class="row"><span class="label">Monthly Redemptions</span><span class="value">${roiRedemptions}</span></div>
  <div class="row"><span class="label">Avg Customer Spend</span><span class="value">$${parseFloat(roiTicket || 0).toLocaleString()}</span></div>
  <div class="row"><span class="label">Visits per Year</span><span class="value">${r.visitsPerYear}</span></div>
  ${roiDiscount ? `<div class="row"><span class="label">Avg Discount per Coupon</span><span class="value">$${parseFloat(roiDiscount).toLocaleString()}</span></div>` : ''}
  ${r.cogsPercent ? `<div class="row"><span class="label">COGS</span><span class="value">${r.cogsPercent}%</span></div>` : ''}
</div>

<div class="section">
  <h3>💰 Revenue Analysis</h3>
  <div class="row"><span class="label">Monthly Revenue</span><span class="value green">$${r.monthlyRevenue.toLocaleString()}/mo</span></div>
  <div class="row"><span class="label">Gross Revenue (${r.months} months)</span><span class="value green">$${r.totalRevenue.toLocaleString()}</span></div>
  ${r.totalDiscounts ? `<div class="row"><span class="label">Less Discounts</span><span class="value red">-$${r.totalDiscounts.toLocaleString()}</span></div>` : ''}
  ${r.totalCogs ? `<div class="row"><span class="label">Less COGS (${r.cogsPercent}%)</span><span class="value red">-$${r.totalCogs.toLocaleString()}</span></div>` : ''}
  <div class="row"><span class="label">Less Ad Investment</span><span class="value red">-$${r.totalAdCost.toLocaleString()}</span></div>
</div>

<div class="section">
  <h3>📊 Results</h3>
  <div class="row highlight"><span class="label">Return on Investment</span><span class="value big">${r.roiPercent}% ROI</span></div>
  <div class="row"><span class="label">Campaign Net Profit</span><span class="value green">$${r.campaignProfit.toLocaleString()}</span></div>
  <div class="row"><span class="label">Break-even Redemptions/mo</span><span class="value">${r.breakEvenRedemptions}</span></div>
</div>

<div class="footer">
  <div class="logo">imPro — IndoorMedia</div>
  <p>Generated ${date} | Register Tape Advertising</p>
</div>

<div class="no-print" style="text-align:center;margin-top:20px;">
  <button onclick="window.print()" style="padding:12px 32px;background:#CC0000;color:white;border:none;border-radius:8px;font-size:16px;cursor:pointer;">🖨️ Print / Save as PDF</button>
</div>
</body></html>`;

    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const w = window.open(url, '_blank');
    if (!w) {
      const a = document.createElement('a');
      a.href = url;
      a.download = `ROI-Report-${biz.replace(/[^a-zA-Z0-9]/g, '_')}.html`;
      a.click();
    }
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  }

  function shareRoiText() {
    if (!roiResult) return;
    const r = roiResult;
    const biz = roiBusinessName || 'Customer';
    const store = roiSelectedStore
      ? `${roiSelectedStore.GroceryChain} — ${roiSelectedStore.City}, ${roiSelectedStore.State}`
      : 'N/A';

    const text = `📊 ROI Report — ${biz}
Store: ${store}

💰 Investment: $${r.totalAdCost.toLocaleString()} (${r.quarters}Q)
📈 Gross Revenue: $${r.totalRevenue.toLocaleString()}${r.totalDiscounts ? `\n🏷️ Discounts: -$${r.totalDiscounts.toLocaleString()}` : ''}${r.totalCogs ? `\n📉 COGS (${r.cogsPercent}%): -$${r.totalCogs.toLocaleString()}` : ''}

✅ ROI: ${r.roiPercent}%
💵 Net Profit: $${r.campaignProfit.toLocaleString()}
📍 Break-even: ${r.breakEvenRedemptions} redemptions/mo

— IndoorMedia Register Tape Advertising`;

    if (navigator.share) {
      navigator.share({ title: `ROI Report — ${biz}`, text }).catch(() => {});
    } else {
      navigator.clipboard.writeText(text).then(() => alert('📋 ROI report copied to clipboard!')).catch(() => {});
    }
  }

  // Submit testimonial state (matches ProspectBot flow)
  let testStep = 1; // 1-15 steps
  let testForm = {
    name: '',           // Step 1: Contact name
    business: '',       // Step 2: Business name
    address: '',        // Step 3: Business address
    phone: '',          // Step 4: Phone number
    groceryChain: '',   // Step 5: Grocery chain
    zone: '',           // Step 6: Zone
    storeNumber: '',    // Step 7: Store number
    couponsPerWeek: '', // Step 8: Coupons per week
    avgTicket: '',      // Step 9: Average ticket price
    roi: '',            // Step 10: ROI rating
    duration: '',       // Step 11: How long advertised
    wouldRenew: '',     // Step 12: Would renew?
    recommend: '',      // Step 13: Would recommend?
    comments: '',       // Step 14: Additional comments
    couponImage: null,  // Step 15: Coupon photo
  };
  let testSubmitting = false;
  let testSubmitted = false;

  function testNext() { testStep++; }
  function testBack() { if (testStep > 1) testStep--; }

  let testStoreSearch = '';
  $: testStoreResults = testStoreSearch.length >= 2
    ? allStores.filter(s =>
        s.StoreName?.toLowerCase().includes(testStoreSearch.toLowerCase()) ||
        s.GroceryChain?.toLowerCase().includes(testStoreSearch.toLowerCase()) ||
        s.City?.toLowerCase().includes(testStoreSearch.toLowerCase())
      ).slice(0, 6)
    : [];

  function selectTestStore(store) {
    testForm.groceryChain = store.GroceryChain;
    testForm.zone = store.ZoneName || '';
    testForm.storeNumber = store.StoreName || '';
    testStoreSearch = '';
  }

  function handleCouponImage(event) {
    const file = event.target.files[0];
    if (file) {
      testForm.couponImage = file;
    }
  }
  
  // Counter sign state
  let counterSignStep = 1; // 1: chain, 2: business card, 3: landing page, 4: ad proof, 5: confirm
  let selectedChainCode = null;
  let counterData = {
    business_card_image: null,
    landing_page_url: '',
    ad_proof_image: null
  };
  let generating = false;
  // Counter Sign API endpoint
  const isDev = window.location.hostname === 'localhost';
  let COUNTER_SIGN_API = isDev 
    ? 'http://localhost:3333'
    : 'https://regulatory-francisco-thriller-christ.trycloudflare.com';
  
  // On production, try to fetch the latest tunnel URL
  if (!isDev) {
    fetch('/api/counter-sign-url')
      .then(r => r.json())
      .then(d => { if (d.url) COUNTER_SIGN_API = d.url; })
      .catch(() => {}); // Fall back to hardcoded URL
  }

  onMount(async () => {
    try {
      const res = await fetch(import.meta.env.BASE_URL + 'data/stores.json');
      allStores = await res.json();
    } catch (err) {
      console.error('Failed to load stores:', err);
    }
  });

  $: filteredStores = searchQuery
    ? allStores.filter(s => 
        s.StoreName?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.GroceryChain?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.City?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : [];

  async function submitTestimonial() {
    testSubmitting = true;
    try {
      const submitted = JSON.parse(localStorage.getItem('submitted_testimonials') || '[]');
      submitted.push({
        ...testForm,
        couponImage: testForm.couponImage ? testForm.couponImage.name : null,
        submittedAt: new Date().toISOString(),
        submittedBy: $user?.name || 'Unknown Rep'
      });
      localStorage.setItem('submitted_testimonials', JSON.stringify(submitted));
      testSubmitted = true;
      setTimeout(() => {
        testForm = { name:'', business:'', address:'', phone:'', groceryChain:'', zone:'', storeNumber:'', couponsPerWeek:'', avgTicket:'', roi:'', duration:'', wouldRenew:'', recommend:'', comments:'', couponImage:null };
        testStep = 1;
        testSubmitted = false;
        testSubmitting = false;
        view = 'main';
      }, 2000);
    } catch (err) {
      console.error('Failed to submit testimonial:', err);
      testSubmitting = false;
    }
  }

  function goBack() {
    if (view === 'audit' && auditStep > 1) {
      auditStep--;
      if (auditStep === 1) { auditStoreNum = null; auditReport = null; }
    } else if (view === 'counter-sign' && counterSignStep > 1) {
      counterSignStep--;
    } else {
      view = 'main';
      selectedStore = null;
      searchQuery = '';
      testimonialQuery = '';
      testimonialResults = [];
    }
  }

  async function loadTestimonialData() {
    if (testimonialData) return testimonialData;
    try {
      const res = await fetch(import.meta.env.BASE_URL + 'data/testimonials.json');
      if (!res.ok) throw new Error('Failed to load');
      testimonialData = await res.json();
      return testimonialData;
    } catch (err) {
      throw new Error('Could not load testimonials database');
    }
  }

  async function searchTestimonials() {
    if (!testimonialQuery.trim()) {
      testimonialResults = [];
      return;
    }

    testimonialLoading = true;
    testimonialError = '';

    try {
      const data = await loadTestimonialData();
      const q = testimonialQuery.trim().toLowerCase();
      
      testimonialResults = data
        .filter(t => t.s && t.s.includes(q))
        .slice(0, 25)
        .map(t => ({
          business: t.b,
          comment: t.c,
          url: t.u
        }));

      if (testimonialResults.length === 0) {
        testimonialError = `No testimonials found for "${testimonialQuery}"`;
      }
    } catch (err) {
      testimonialError = `Error: ${err.message}`;
      testimonialResults = [];
    } finally {
      testimonialLoading = false;
    }
  }

  // Zone install day lookup from RTUI Zone Chart
  const ZONE_INSTALL_DAYS = {'01':1,'02':8,'03':26,'04':28,'05':25,'06':1,'07':7,'08':5,'09':14,'10':30,'11':25,'12':16,'13':20,'14':10,'15':18,'16':7,'17':20,'18':20,'19':8,'20':10,'21':16,'22':1,'23':12,'24':14,'25':23,'26':20,'27':25,'28':6,'29':6};

  function getStoreInstallDay(storeId) {
    const m = (storeId || '').match(/(\d{2})[A-Z]?-/);
    return m ? (ZONE_INSTALL_DAYS[m[1]] || 7) : 7;
  }

  function getLastInstallDate(storeId) {
    const day = getStoreInstallDay(storeId);
    const now = new Date();
    // Find the most recent install day (could be this month or last month)
    let d = new Date(now.getFullYear(), now.getMonth(), day);
    if (d > now) d.setMonth(d.getMonth() - 1);
    return d.toISOString().split('T')[0];
  }

  function getNextInstallDate(storeId) {
    const day = getStoreInstallDay(storeId);
    const now = new Date();
    let d = new Date(now.getFullYear(), now.getMonth(), day);
    if (d <= now) d.setMonth(d.getMonth() + 1);
    return d.toISOString().split('T')[0];
  }

  function getAuditDueDate(storeId) {
    // Audit is 45 days after the last install
    const lastInstall = new Date(getLastInstallDate(storeId) + 'T12:00:00');
    lastInstall.setDate(lastInstall.getDate() + 45);
    return lastInstall.toISOString().split('T')[0];
  }

  function selectAuditStore(store) {
    selectedStore = store;
    auditStoreNum = store.StoreName;
    // Auto-populate dates based on zone install schedule
    auditDate = getLastInstallDate(store.StoreName);
    auditNextShipmentDate = getNextInstallDate(store.StoreName);
    view = 'audit';
  }

  // Chain codes from store templates
  const CHAIN_CODES = [
    'ALB', 'ACM', 'AND', 'ARL', 'BAK', 'BGE', 'BGY', 'BLO', 'BUT',
    'CAR', 'CMI', 'COP', 'CRL', 'CSV', 'CTR', 'CUB', 'DAN', 'DAW',
    'DFM', 'DIE', 'DIL', 'DIS', 'FAM', 'FCO', 'FDC', 'FDP', 'FDT',
    'FES', 'FFL', 'FGT', 'FIE', 'FME', 'FMK', 'FMX', 'FRY', 'FYM',
    'FoodsCo', 'GDI', 'GER', 'GIA', 'GIE', 'GMF', 'GNF', 'GTC', 'HAG',
    'HAR', 'HEB', 'HIT', 'HNB', 'HRV', 'HYV', 'IGA', 'JAY', 'JOE',
    'JWL', 'KKG', 'KRO', 'KSP', 'LAF', 'LIN', 'LKY', 'LOW', 'LWS',
    'MAC', 'MAR', 'MIT', 'MKF', 'MKT32', 'MKT', 'MRN', 'MST', 'OAK',
    'OWK', 'PAK', 'PAV', 'PCH', 'PDF', 'PET', 'PIG', 'PLS', 'PNS',
    'PRC', 'QFC', 'RAL', 'RAM', 'RAN', 'RCH', 'REA', 'RFP', 'RIC',
    'RID', 'ROS', 'ROU', 'RSM', 'RUL', 'SAF', 'SAL', 'SCH', 'SCO',
    'SCT', 'Sendiks', 'SHM', 'SHW', 'SMI', 'SNS', 'SON', 'SPR', 'SRI',
    'STB', 'STM', 'SVM', 'SVT', 'TOM', 'TOP', 'TWY', 'UNI', 'VAL',
    'VGS', 'VON', 'WDM', 'WHM', 'WIN', 'YOK'
  ];

  function selectChain(code) {
    selectedChainCode = code;
    counterSignStep = 2;
  }

  async function readFileAsBytes(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(new Uint8Array(reader.result));
      reader.onerror = reject;
      reader.readAsArrayBuffer(file);
    });
  }

  function downloadBlob(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();
  }

  async function submitCounterSign() {
    if (generating) return;
    
    try {
      generating = true;
      
      const repName = $user?.name || $user?.first_name || 'Tyler Van Sant';
      
      const formData = new FormData();
      formData.append('chain_code', selectedChainCode);
      formData.append('rep_name', repName);
      formData.append('ad_proof', counterData.ad_proof_image);
      
      if (counterData.business_card_image) {
        formData.append('business_card', counterData.business_card_image);
      }
      if (counterData.landing_page_url) {
        formData.append('landing_page_url', counterData.landing_page_url);
      }

      const response = await fetch(`${COUNTER_SIGN_API}/generate`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        let msg = response.statusText;
        try { const e = await response.json(); msg = e.error; } catch {}
        alert(`❌ Error: ${msg}`);
        return;
      }

      const blob = await response.blob();
      downloadBlob(blob, `${selectedChainCode}_CounterSign.pdf`);
      
      counterSignStep = 1;
      selectedChainCode = null;
      counterData = { business_card_image: null, landing_page_url: '', ad_proof_image: null };
      view = 'main';
    } catch (err) {
      alert(`❌ Error: ${err.message}`);
      console.error(err);
    } finally {
      generating = false;
    }
  }

  function generateAuditReport() {
    const cases = parseInt(auditCases) || 0;
    const rolls = parseInt(auditRolls) || 0;
    const starting = parseInt(auditStartingCases) || 20;
    const totalRolls = (cases * 50) + rolls;
    const startingRolls = starting * 50;
    
    // Calculate actual usage rate: (starting rolls - current rolls) / days since delivery
    const delDate = new Date(auditDate);
    const performedDate = new Date(auditPerformedDate + 'T12:00:00');
    const daysSinceDelivery = Math.max(1, Math.floor((performedDate - delDate) / (1000 * 60 * 60 * 24)));
    const rollsUsed = startingRolls - totalRolls;
    const usagePerDay = Math.round((rollsUsed / daysSinceDelivery) * 10) / 10;
    const daysUntilRunout = usagePerDay > 0 ? Math.round((totalRolls / usagePerDay) * 10) / 10 : 999;

    const runoutDate = new Date(performedDate);
    runoutDate.setDate(runoutDate.getDate() + Math.floor(daysUntilRunout));

    // Use the next shipment date that the rep entered
    const nextDelivery = new Date(auditNextShipmentDate);
    const daysUntilDelivery = Math.ceil((nextDelivery - performedDate) / (1000 * 60 * 60 * 24));
    const insufficient = daysUntilRunout < daysUntilDelivery;
    
    // Get expected month name for next delivery
    const nextDeliveryMonth = nextDelivery.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    auditReport = {
      storeNum: auditStoreNum,
      chain: selectedStore?.GroceryChain || '',
      city: selectedStore?.City || '',
      state: selectedStore?.State || '',
      deliveryDate: delDate.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }),
      startingCases: starting,
      startingRolls: startingRolls,
      currentCases: cases,
      currentRolls: rolls,
      totalRolls: totalRolls,
      rollsUsed: rollsUsed,
      daysSinceDelivery: daysSinceDelivery,
      usagePerDay: usagePerDay,
      daysUntilRunout: daysUntilRunout,
      runoutDate: runoutDate.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }),
      nextDelivery: nextDelivery.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }),
      nextDeliveryMonth: nextDeliveryMonth,
      daysUntilDelivery: daysUntilDelivery,
      insufficient: insufficient
    };
    auditStep = 4;
  }

  async function downloadAuditPdf() {
    try {
      const r = auditReport;
      const repName = $user?.name || $user?.first_name || 'Rep';

      const pdfDoc = await PDFDocument.create();
      const page = pdfDoc.addPage([612, 792]);
      const bold = await pdfDoc.embedFont('Helvetica-Bold');
      const reg = await pdfDoc.embedFont('Helvetica');

      // Header
      page.drawRectangle({ x: 0, y: 700, width: 612, height: 92, color: rgb(0.8, 0, 0) });
      page.drawText('STORE AUDIT REPORT', { x: 30, y: 740, size: 22, font: bold, color: rgb(1, 1, 1) });
      page.drawText(r.storeNum, { x: 30, y: 715, size: 14, font: reg, color: rgb(1, 1, 1) });

      let y = 670;
      const section = (title) => {
        y -= 10;
        page.drawText(title, { x: 40, y, size: 13, font: bold, color: rgb(0.1, 0.1, 0.1) });
        y -= 22;
      };
      const line = (label, value) => {
        page.drawText(label, { x: 50, y, size: 11, font: reg, color: rgb(0.3, 0.3, 0.3) });
        page.drawText(String(value), { x: 220, y, size: 11, font: reg, color: rgb(0.1, 0.1, 0.1) });
        y -= 20;
      };

      line('Store:', `${r.chain} - ${r.city}, ${r.state}`);
      line('Rep:', repName);
      line('Audit Date:', new Date(auditPerformedDate + 'T12:00:00').toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }));

      section('DELIVERY');
      line('Delivery Date:', r.deliveryDate);
      line('Starting:', `${r.startingCases} cases (${r.startingRolls.toLocaleString()} rolls)`);

      section('CURRENT INVENTORY');
      line('Full Cases:', String(r.currentCases));
      line('Loose Rolls:', String(r.currentRolls));
      line('Total Rolls:', String(r.totalRolls));

      section('PROJECTION');
      line('Rolls Used:', `${r.rollsUsed} in ${r.daysSinceDelivery} days`);
      line('Usage Rate:', `${r.usagePerDay} rolls/day`);
      line('Days Until Runout:', String(r.daysUntilRunout));
      line('Est. Runout Date:', r.runoutDate);
      line('Next Delivery:', `${r.nextDelivery} (${r.daysUntilDelivery} days)`);

      y -= 15;
      const statusText = r.insufficient
        ? 'INSUFFICIENT: Inventory will run out BEFORE next delivery! Action needed.'
        : 'SUFFICIENT: Inventory will last until next delivery.';
      const statusColor = r.insufficient ? rgb(0.8, 0, 0) : rgb(0, 0.5, 0);
      page.drawText(statusText, { x: 40, y, size: 12, font: bold, color: statusColor });

      page.drawText(`Generated ${new Date().toLocaleString()} - IndoorMedia Audit Tool`, {
        x: 150, y: 20, size: 8, font: reg, color: rgb(0.6, 0.6, 0.6)
      });

      const pdfBytes = await pdfDoc.save();
      downloadBlob(new Blob([pdfBytes], { type: 'application/pdf' }), `Audit_${r.storeNum}.pdf`);
    } catch (err) {
      alert('Error: ' + err.message);
      console.error(err);
    }
  }
</script>

<div class="tools-container">
  <!-- Main Tools Menu -->
  {#if view === 'main'}
    <h2>🛠️ Tools</h2>
    <p class="subtitle">Sales support & management tools</p>

    <div class="button-grid">
      <button class="main-btn" on:click={() => view = 'roi'}>
        <div class="btn-icon">📊</div>
        <div class="btn-text">ROI Calculator</div>
        <div class="btn-desc">Calculate campaign ROI before pitching</div>
      </button>

      <button class="main-btn" on:click={() => view = 'rates'}>
        <div class="btn-icon">💰</div>
        <div class="btn-text">Store Rates</div>
        <div class="btn-desc">Quick pricing lookup by store</div>
      </button>

      <button class="main-btn" on:click={() => view = 'testimonials'}>
        <div class="btn-icon">📋</div>
        <div class="btn-text">Testimonials</div>
        <div class="btn-desc">Find relevant case studies</div>
      </button>

      <button class="main-btn" on:click={() => view = 'audit'}>
        <div class="btn-icon">🏪</div>
        <div class="btn-text">Audit Store</div>
        <div class="btn-desc">Track tape inventory & delivery</div>
      </button>

      <button class="main-btn" on:click={() => view = 'counter-sign'}>
        <div class="btn-icon">🎨</div>
        <div class="btn-text">Counter Sign</div>
        <div class="btn-desc">Generate counter signs</div>
      </button>

      <button class="main-btn" on:click={() => view = 'submit-testimonial'}>
        <div class="btn-icon">⭐</div>
        <div class="btn-text">Submit Testimonial</div>
        <div class="btn-desc">Share customer success stories</div>
      </button>
    </div>
  {/if}

  <!-- ROI Calculator -->
  {#if view === 'roi'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>📊 ROI Calculator</h2>
    <p class="subtitle">Calculate campaign ROI before pitching</p>

    <div class="info-card">
      <p>💡 Show customers their potential ROI on register tape campaigns.</p>
      
      <div class="form-group">
        <label>Business Name *</label>
        <input type="text" bind:value={roiBusinessName} placeholder="e.g., Main Street Coffee" />
      </div>

      <div class="form-group">
        <label>Store</label>
        {#if roiSelectedStore}
          <div class="store-info-card">
            <div class="store-info-header">
              <strong>{roiSelectedStore.GroceryChain}</strong>
              <button class="clear-btn" on:click={() => { roiSelectedStore = null; roiAdCost = ''; }}>✕</button>
            </div>
            <div class="store-info-details">
              <span>📍 {roiSelectedStore.City}, {roiSelectedStore.State}</span>
              <span>🏪 {roiSelectedStore.StoreName}</span>
              <span>🔄 Cycle {roiSelectedStore.Cycle || '—'}</span>
              <span>📦 {roiSelectedStore['Case Count'] || '—'} cases</span>
            </div>
            <div class="store-info-prices">
              <span class:active={roiAdSize === 'single'}>Single: ${(roiSelectedStore.SingleAd || 0).toLocaleString()}/yr</span>
              <span class:active={roiAdSize === 'double'}>Double: ${(roiSelectedStore.DoubleAd || 0).toLocaleString()}/yr</span>
            </div>
          </div>
        {:else}
          <input type="text" bind:value={roiStoreSearch} placeholder="Search store by name, city, or number..." />
          {#if roiStoreResults.length > 0}
            <div class="roi-store-list">
              {#each roiStoreResults as store}
                <button class="roi-store-btn" on:click={() => selectRoiStore(store)}>
                  <strong>{store.GroceryChain}</strong> — {store.City}, {store.State}
                  <span class="store-id">{store.StoreName}</span>
                </button>
              {/each}
            </div>
          {/if}
        {/if}
      </div>

      <div class="form-group">
        <label>Ad Size</label>
        <div class="ad-size-toggle">
          <button class="size-btn" class:active={roiAdSize === 'single'} on:click={() => roiAdSize = 'single'}>
            Single Ad
          </button>
          <button class="size-btn" class:active={roiAdSize === 'double'} on:click={() => roiAdSize = 'double'}>
            Double Ad
          </button>
        </div>
      </div>

      <div class="form-group">
        <label>Annual Ad Cost ($) *</label>
        <input type="number" bind:value={roiAdCost} placeholder="e.g., 1778" />
        {#if roiSelectedStore}
          <p class="hint">Auto-filled from {roiSelectedStore.GroceryChain} {roiAdSize} ad rate</p>
        {:else}
          <p class="hint">Select a store above or enter manually</p>
        {/if}
      </div>

      <div class="form-group">
        <label>Number of Quarters</label>
        <select bind:value={roiQuarters}>
          <option value={1}>1 quarter (${Math.round((parseFloat(roiAdCost) || 0) / 4).toLocaleString()})</option>
          <option value={2}>2 quarters (${Math.round((parseFloat(roiAdCost) || 0) / 2).toLocaleString()})</option>
          <option value={4}>4 quarters — full year (${(parseFloat(roiAdCost) || 0).toLocaleString()})</option>
        </select>
      </div>

      <div class="form-group">
        <label>Monthly Redemptions *</label>
        <input type="number" bind:value={roiRedemptions} placeholder="e.g., 30" />
        <p class="hint">Estimated new customers per month from the ad</p>
      </div>

      <div class="form-group">
        <label>Average Ticket / Customer Spend ($) *</label>
        <input type="number" bind:value={roiTicket} placeholder="e.g., 50" />
      </div>

      <div class="form-group">
        <label>Visits per Year (per customer)</label>
        <input type="number" bind:value={roiVisitsPerYear} placeholder="1" min="1" />
        <p class="hint">How often each new customer returns annually (1 = one-time, 12 = monthly)</p>
      </div>

      <div class="form-group">
        <label>Avg Discount per Coupon ($)</label>
        <input type="number" bind:value={roiDiscount} placeholder="e.g., 10" />
        <p class="hint">If running a coupon/offer on the ad</p>
      </div>

      <div class="form-group">
        <label>COGS (%)</label>
        <input type="number" bind:value={roiCogs} placeholder="e.g., 35" min="0" max="100" />
        <p class="hint">Cost of goods sold (typical: 25-40%)</p>
      </div>

      <button class="action-btn" on:click={calculateROI} disabled={!roiAdCost || !roiRedemptions || !roiTicket}>
        Calculate ROI
      </button>
    </div>

    {#if roiResult}
      <div class="roi-results">
        <h3>📊 ROI Breakdown</h3>
        
        <div class="roi-stats">
          <div class="roi-stat">
            <span class="roi-value">${roiResult.monthlyRevenue.toLocaleString()}</span>
            <span class="roi-label">Monthly Revenue</span>
          </div>
          <div class="roi-stat">
            <span class="roi-value">${roiResult.monthlyProfit.toLocaleString()}</span>
            <span class="roi-label">Monthly Profit</span>
          </div>
          <div class="roi-stat highlight">
            <span class="roi-value">${roiResult.campaignProfit.toLocaleString()}</span>
            <span class="roi-label">Campaign Profit</span>
          </div>
        </div>

        <div class="roi-detail">
          <div class="roi-row">
            <span>Annual Ad Rate ({roiResult.adSize})</span>
            <span>${roiResult.annualAdCost.toLocaleString()}</span>
          </div>
          <div class="roi-row">
            <span>Investment ({roiResult.quarters}Q{roiResult.quarters < 4 ? ' pro-rated' : ''})</span>
            <span class="cost">${roiResult.totalAdCost.toLocaleString()}</span>
          </div>
          <div class="roi-row">
            <span>Gross Revenue ({roiResult.months} months)</span>
            <span>${roiResult.totalRevenue.toLocaleString()}</span>
          </div>
          <div class="roi-row">
            <span>Less Discounts</span>
            <span class="cost">-${roiResult.totalDiscounts.toLocaleString()}</span>
          </div>
          <div class="roi-row">
            <span>Less COGS ({roiResult.cogsPercent}%)</span>
            <span class="cost">-${roiResult.totalCogs.toLocaleString()}</span>
          </div>
          <div class="roi-row total">
            <span>Net Profit After Ad Cost</span>
            <span class="{roiResult.campaignProfit >= 0 ? 'profit' : 'cost'}">${roiResult.campaignProfit.toLocaleString()}</span>
          </div>
          <div class="roi-row total">
            <span>ROI</span>
            <span class="{roiResult.roiPercent >= 0 ? 'profit' : 'cost'}">{roiResult.roiPercent}%</span>
          </div>
          <div class="roi-row">
            <span>Break-even Redemptions/mo</span>
            <span>{roiResult.breakEvenRedemptions}</span>
          </div>
        </div>

        <div class="roi-verdict" class:positive={roiResult.roiPercent >= 0} class:negative={roiResult.roiPercent < 0}>
          {#if roiResult.roiPercent >= 100}
            🚀 Excellent ROI! Customer makes ${roiResult.campaignProfit.toLocaleString()} profit on a ${roiResult.totalAdCost.toLocaleString()} investment.
          {:else if roiResult.roiPercent >= 0}
            ✅ Positive ROI. Campaign pays for itself and generates ${roiResult.campaignProfit.toLocaleString()} in profit.
          {:else}
            ⚠️ Negative ROI at these numbers. Try adjusting redemptions or ticket size.
          {/if}
        </div>

        <div class="roi-export-actions">
          <button class="action-btn" on:click={downloadRoiPdf}>
            📄 PDF Report
          </button>
          <button class="action-btn" on:click={exportRoiHtml} style="background: #CC0000;">
            🌐 Export Report
          </button>
          <button class="action-btn" on:click={shareRoiText} style="background: #2e7d32;">
            📤 Share
          </button>
        </div>
      </div>
    {/if}
  {/if}

  <!-- Store Rates -->
  {#if view === 'rates'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>💰 Store Rates</h2>
    <p class="subtitle">Quick pricing lookup</p>

    <div class="search-box">
      <input
        type="text"
        placeholder="Search by store number, city, or chain..."
        bind:value={searchQuery}
      />
    </div>

    {#if searchQuery}
      <div class="store-list">
        {#each filteredStores.slice(0, 10) as store}
          <div class="store-card">
            <h4>{store.GroceryChain} - {store.City}</h4>
            <p class="store-num">Store: {store.StoreName}</p>
            <p class="store-pricing">
              Single: ${store.SingleAd} | Double: ${store.DoubleAd}
            </p>
          </div>
        {/each}
      </div>
    {/if}
  {/if}

  <!-- Testimonials -->
  {#if view === 'testimonials'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>📋 Testimonials</h2>
    <p class="subtitle">Find relevant case studies and social proof</p>

    <div class="search-box">
      <input
        type="text"
        placeholder="Search by keyword, business type, ROI..."
        bind:value={testimonialQuery}
        on:keydown={(e) => e.key === 'Enter' && searchTestimonials()}
        disabled={testimonialLoading}
      />
      <button class="search-btn" on:click={searchTestimonials} disabled={testimonialLoading || !testimonialQuery.trim()}>
        {testimonialLoading ? '🔄' : '🔍'} Search
      </button>
    </div>

    <div class="info-card">
      <p>💡 Search examples:</p>
      <ul>
        <li>Business categories: "dental", "restaurant", "salon", "gym"</li>
        <li>Results: "parking lot", "foot traffic", "sales increase", "ROI"</li>
        <li>Topics: "skeptical", "started slow", "thank you"</li>
      </ul>
    </div>

    {#if testimonialError}
      <div class="error-card">{testimonialError}</div>
    {/if}

    {#if testimonialResults.length > 0}
      <div class="results-card">
        <h3>Found {testimonialResults.length} testimonial{testimonialResults.length !== 1 ? 's' : ''}</h3>
        {#each testimonialResults as testimonial}
          <div class="testimonial-item">
            <h4>{testimonial.business}</h4>
            <p class="comment">"{testimonial.comment}{testimonial.comment.length === 200 ? '...' : ''}"</p>
            <a href={testimonial.url} target="_blank" class="testimonial-link">Read full story →</a>
          </div>
        {/each}
      </div>
    {:else if testimonialQuery && !testimonialLoading}
      <p class="hint">Press Enter or click Search to find testimonials</p>
    {/if}
  {/if}

  <!-- Audit Store -->
  {#if view === 'audit'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    
    {#if auditStep === 1}
      <h2>Audit Store</h2>
      <p class="subtitle">Select store to audit</p>

      <div class="search-box">
        <input
          type="text"
          placeholder="Search store..."
          bind:value={searchQuery}
        />
      </div>

      <div class="store-list">
        {#each filteredStores.slice(0, 15) as store}
          <button class="store-select-btn" on:click={() => { selectAuditStore(store); auditStep = 2; }}>
            <div>
              <h4>{store.GroceryChain} - {store.City}</h4>
              <p class="store-num">{store.StoreName}</p>
            </div>
            <div class="arrow">&rarr;</div>
          </button>
        {/each}
      </div>

    {:else if auditStep === 2}
      <h2>Audit: {auditStoreNum}</h2>
      <p class="subtitle">{selectedStore?.GroceryChain} - {selectedStore?.City}</p>

      <div class="form-card">
        <p class="form-label">📅 Dates</p>
        <p class="hint" style="margin-bottom:10px;">📍 Zone install day: <strong>{getStoreInstallDay(auditStoreNum)}{getStoreInstallDay(auditStoreNum) == 1 || getStoreInstallDay(auditStoreNum) == 21 || getStoreInstallDay(auditStoreNum) == 31 ? 'st' : getStoreInstallDay(auditStoreNum) == 2 || getStoreInstallDay(auditStoreNum) == 22 ? 'nd' : getStoreInstallDay(auditStoreNum) == 3 || getStoreInstallDay(auditStoreNum) == 23 ? 'rd' : 'th'} of each month</strong> | Audit due: <strong>{new Date(getAuditDueDate(auditStoreNum) + 'T12:00:00').toLocaleDateString('en-US', {month:'short', day:'numeric'})}</strong> (45 days post-install)</p>
        
        <div class="form-group">
          <label>Date Audit Performed *</label>
          <input type="date" bind:value={auditPerformedDate} required />
        </div>

        <div class="form-group">
          <label>Last Delivery/Install Date *</label>
          <input type="date" bind:value={auditDate} required />
          <p class="hint">Auto-set from zone schedule — adjust if different</p>
        </div>

        <div class="form-group">
          <label>Next Shipment/Install Date *</label>
          <input type="date" bind:value={auditNextShipmentDate} required />
          <p class="hint">Auto-set from zone schedule — next {getStoreInstallDay(auditStoreNum)}{getStoreInstallDay(auditStoreNum) == 1 || getStoreInstallDay(auditStoreNum) == 21 || getStoreInstallDay(auditStoreNum) == 31 ? 'st' : getStoreInstallDay(auditStoreNum) == 2 || getStoreInstallDay(auditStoreNum) == 22 ? 'nd' : getStoreInstallDay(auditStoreNum) == 3 || getStoreInstallDay(auditStoreNum) == 23 ? 'rd' : 'th'}</p>
        </div>

        <button class="action-btn" on:click={() => auditStep = 3} disabled={!auditDate || !auditNextShipmentDate}>
          Continue to Inventory
        </button>
        
        <button class="back-btn" on:click={() => auditStep = 1}>
          ← Back
        </button>
      </div>

    {:else if auditStep === 3}
      <h2>Audit: {auditStoreNum}</h2>
      <p class="subtitle">{selectedStore?.GroceryChain} - {selectedStore?.City}</p>

      <div class="form-card">
        <p class="form-label">📦 Current Inventory</p>
        
        <div class="form-group">
          <label>Starting Cases (at delivery)</label>
          <input type="number" bind:value={auditStartingCases} min="0" max="50" placeholder="e.g., 20" />
        </div>

        <div class="form-group">
          <label>Full Cases Currently</label>
          <input type="number" bind:value={auditCases} min="0" max="50" placeholder="0-50" />
        </div>

        <div class="form-group">
          <label>Loose Rolls Currently</label>
          <input type="number" bind:value={auditRolls} min="0" max="49" placeholder="0-49" />
        </div>

        <button class="action-btn" on:click={generateAuditReport} disabled={!auditCases && auditCases !== 0}>
          Generate Audit Report
        </button>
        
        <button class="back-btn" on:click={() => auditStep = 2}>
          ← Back to Dates
        </button>
      </div>

    {:else if auditStep === 4 && auditReport}
      <h2>Audit Report</h2>

      <div class="report-card">
        <div class="report-header">{auditReport.storeNum}</div>
        <p class="report-chain">{auditReport.chain} - {auditReport.city}</p>

        <div class="report-section">
          <h4>Delivery</h4>
          <p>Date: {auditReport.deliveryDate}</p>
          <p>Starting: {auditReport.startingCases} cases ({auditReport.startingRolls} rolls)</p>
        </div>

        <div class="report-section">
          <h4>Current Inventory</h4>
          <p>{auditReport.currentCases} cases + {auditReport.currentRolls} rolls = {auditReport.totalRolls} total rolls</p>
        </div>

        <div class="report-section">
          <h4>Projection</h4>
          <p>Rolls used: {auditReport.rollsUsed} in {auditReport.daysSinceDelivery} days</p>
          <p>Usage rate: {auditReport.usagePerDay} rolls/day</p>
          <p>Days until runout: {auditReport.daysUntilRunout}</p>
          <p>Est. runout date: {auditReport.runoutDate}</p>
          <p class="next-delivery-highlight">📅 Next delivery: <strong>{auditReport.nextDeliveryMonth}</strong></p>
          <p class="next-delivery-detail">({auditReport.nextDelivery}, {auditReport.daysUntilDelivery} days away)</p>
        </div>

        <div class="report-status" class:status-ok={!auditReport.insufficient} class:status-warn={auditReport.insufficient}>
          {auditReport.insufficient ? 'INSUFFICIENT: Inventory may run out before next delivery!' : 'SUFFICIENT: Inventory should last until next delivery.'}
        </div>

        <button class="action-btn" on:click={downloadAuditPdf}>
          Download Audit PDF
        </button>

        <button class="edit-btn" on:click={() => auditStep = 2}>
          Edit
        </button>
      </div>
    {/if}
  {/if}

  <!-- Counter Sign Generator -->
  {#if view === 'counter-sign'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    
    {#if counterSignStep === 1}
      <h2>🎨 Counter Sign Generator</h2>
      <p class="subtitle">Select store chain template</p>

      <div class="chain-grid">
        {#each CHAIN_CODES as code}
          <button class="chain-btn" on:click={() => selectChain(code)}>
            {code}
          </button>
        {/each}
      </div>
    {/if}

    {#if counterSignStep === 2}
      <h2>1. Business Card</h2>
      <p class="subtitle">{selectedChainCode}</p>

      <div class="upload-card">
        <div class="upload-box">
          <p>📸 Upload your personal business card image</p>
          <input type="file" accept="image/*" on:change={(e) => counterData.business_card_image = e.target.files?.[0]} />
          {#if counterData.business_card_image}
            <p class="upload-ok">✅ {counterData.business_card_image.name}</p>
          {/if}
        </div>

        <button class="next-btn" on:click={() => counterSignStep = 3} disabled={!counterData.business_card_image}>
          Next →
        </button>
      </div>
    {/if}

    {#if counterSignStep === 3}
      <h2>2. Landing Page (Optional)</h2>
      <p class="subtitle">{selectedChainCode}</p>

      <div class="form-card">
        <div class="form-group">
          <label>Your Personal Landing Page URL</label>
          <input type="url" bind:value={counterData.landing_page_url} placeholder="https://www.indoormedia.com/tape-sales/your-name/" />
        </div>

        <p class="info-text">💡 Leave blank if you don't have one</p>

        <button class="next-btn" on:click={() => counterSignStep = 4}>
          Next →
        </button>
      </div>
    {/if}

    {#if counterSignStep === 4}
      <h2>3. Ad Proof</h2>
      <p class="subtitle">{selectedChainCode}</p>

      <div class="upload-card">
        <div class="upload-box">
          <p>📸 Upload the advertiser's ad proof/proof of concept image</p>
          <input type="file" accept="image/*" on:change={(e) => counterData.ad_proof_image = e.target.files?.[0]} />
          {#if counterData.ad_proof_image}
            <p class="upload-ok">✅ {counterData.ad_proof_image.name}</p>
          {/if}
        </div>

        <button class="next-btn" on:click={() => counterSignStep = 5} disabled={!counterData.ad_proof_image}>
          Review & Generate →
        </button>
      </div>
    {/if}

    {#if counterSignStep === 5}
      <h2>Review & Generate</h2>
      <p class="subtitle">{selectedChainCode}</p>

      <div class="review-card">
        <div class="review-section">
          <h4>Business Card</h4>
          <p>✅ {counterData.business_card_image?.name}</p>
        </div>

        <div class="review-section">
          <h4>Landing Page</h4>
          <p>{counterData.landing_page_url || '(Optional - not provided)'}</p>
        </div>

        <div class="review-section">
          <h4>Ad Proof</h4>
          <p>✅ {counterData.ad_proof_image?.name}</p>
        </div>

        <button class="action-btn" on:click={submitCounterSign} disabled={generating}>
          {generating ? '⏳ Generating...' : '✅ Generate Counter Sign PDF'}
        </button>
        
        <button class="edit-btn" on:click={() => counterSignStep = 2}>
          ✏️ Edit
        </button>
      </div>
    {/if}
  {/if}

  <!-- Submit Testimonial -->
  {#if view === 'submit-testimonial'}
    <button class="back-btn" on:click={() => { if (testStep > 1) testBack(); else { view = 'main'; testStep = 1; } }}>← {testStep > 1 ? 'Previous' : 'Back'}</button>
    <h2>⭐ Submit Testimonial</h2>
    <p class="subtitle">Step {testStep} of 15</p>
    <div class="step-progress"><div class="step-bar" style="width: {(testStep / 15) * 100}%"></div></div>

    {#if testSubmitted}
      <div class="success-card">
        <p>✅ Testimonial submitted!</p>
        <p>Thank you for sharing. Redirecting...</p>
      </div>
    {:else}
      <div class="form-card">

        {#if testStep === 1}
          <p class="step-label">👤 Contact Name</p>
          <div class="form-group">
            <input type="text" bind:value={testForm.name} placeholder="Owner/Manager name" />
          </div>
          <button class="action-btn" on:click={testNext} disabled={!testForm.name.trim()}>Next →</button>

        {:else if testStep === 2}
          <p class="step-label">🏢 Business Name</p>
          <div class="form-group">
            <input type="text" bind:value={testForm.business} placeholder="e.g., Main Street Coffee" />
          </div>
          <button class="action-btn" on:click={testNext} disabled={!testForm.business.trim()}>Next →</button>

        {:else if testStep === 3}
          <p class="step-label">📍 Business Address</p>
          <div class="form-group">
            <input type="text" bind:value={testForm.address} placeholder="123 Main St, City, State ZIP" />
          </div>
          <button class="action-btn" on:click={testNext} disabled={!testForm.address.trim()}>Next →</button>

        {:else if testStep === 4}
          <p class="step-label">📞 Phone Number</p>
          <div class="form-group">
            <input type="tel" bind:value={testForm.phone} placeholder="(555) 123-4567" />
          </div>
          <button class="action-btn" on:click={testNext} disabled={!testForm.phone.trim()}>Next →</button>

        {:else if testStep === 5}
          <p class="step-label">🏪 Grocery Chain</p>
          <div class="form-group">
            <input type="text" bind:value={testStoreSearch} placeholder="Search store (Safeway, Kroger, etc.)" />
            {#if testStoreResults.length > 0}
              <div class="roi-store-list">
                {#each testStoreResults as store}
                  <button class="roi-store-btn" on:click={() => selectTestStore(store)}>
                    <strong>{store.GroceryChain}</strong> — {store.City}, {store.State}
                    <span class="store-id">{store.StoreName}</span>
                  </button>
                {/each}
              </div>
            {/if}
            {#if testForm.groceryChain}
              <p class="hint">✅ Selected: {testForm.groceryChain}</p>
            {/if}
          </div>
          <button class="action-btn" on:click={testNext} disabled={!testForm.groceryChain.trim()}>Next →</button>

        {:else if testStep === 6}
          <p class="step-label">🗺️ Zone</p>
          <div class="form-group">
            <input type="text" bind:value={testForm.zone} placeholder="e.g., 07Z, 05X" />
            <p class="hint">{testForm.zone ? '✅ ' + testForm.zone : 'Auto-filled from store if available'}</p>
          </div>
          <button class="action-btn" on:click={testNext} disabled={!testForm.zone.trim()}>Next →</button>

        {:else if testStep === 7}
          <p class="step-label">🔢 Store Number</p>
          <div class="form-group">
            <input type="text" bind:value={testForm.storeNumber} placeholder="e.g., SAF07Z-0206" />
            <p class="hint">{testForm.storeNumber ? '✅ ' + testForm.storeNumber : 'Auto-filled from store search'}</p>
          </div>
          <button class="action-btn" on:click={testNext} disabled={!testForm.storeNumber.trim()}>Next →</button>

        {:else if testStep === 8}
          <p class="step-label">🎟️ Coupons Redeemed Per Week</p>
          <div class="form-group">
            <input type="number" bind:value={testForm.couponsPerWeek} placeholder="e.g., 15" min="0" />
          </div>
          <button class="action-btn" on:click={testNext} disabled={!testForm.couponsPerWeek}>Next →</button>

        {:else if testStep === 9}
          <p class="step-label">💵 Average Ticket Price</p>
          <div class="form-group">
            <input type="number" bind:value={testForm.avgTicket} placeholder="e.g., 45.00" step="0.01" min="0" />
          </div>
          <button class="action-btn" on:click={testNext} disabled={!testForm.avgTicket}>Next →</button>

        {:else if testStep === 10}
          <p class="step-label">📊 ROI Rating</p>
          <div class="rating-btns">
            <button class="rating-btn" class:active={testForm.roi === 'excellent'} on:click={() => { testForm.roi = 'excellent'; testNext(); }}>🔥 Excellent</button>
            <button class="rating-btn" class:active={testForm.roi === 'good'} on:click={() => { testForm.roi = 'good'; testNext(); }}>⭐ Good</button>
            <button class="rating-btn" class:active={testForm.roi === 'fair'} on:click={() => { testForm.roi = 'fair'; testNext(); }}>👀 Fair</button>
            <button class="rating-btn" class:active={testForm.roi === 'poor'} on:click={() => { testForm.roi = 'poor'; testNext(); }}>😞 Poor</button>
          </div>

        {:else if testStep === 11}
          <p class="step-label">⏱️ How Long Have They Advertised?</p>
          <div class="form-group">
            <input type="text" bind:value={testForm.duration} placeholder="e.g., 6 months, 1 year" />
          </div>
          <button class="action-btn" on:click={testNext} disabled={!testForm.duration.trim()}>Next →</button>

        {:else if testStep === 12}
          <p class="step-label">🔄 Would They Renew?</p>
          <div class="rating-btns">
            <button class="rating-btn" class:active={testForm.wouldRenew === 'yes'} on:click={() => { testForm.wouldRenew = 'yes'; testNext(); }}>✅ Yes</button>
            <button class="rating-btn" class:active={testForm.wouldRenew === 'no'} on:click={() => { testForm.wouldRenew = 'no'; testNext(); }}>❌ No</button>
          </div>

        {:else if testStep === 13}
          <p class="step-label">👍 Would They Recommend IndoorMedia?</p>
          <div class="rating-btns">
            <button class="rating-btn" class:active={testForm.recommend === 'yes'} on:click={() => { testForm.recommend = 'yes'; testNext(); }}>✅ Yes</button>
            <button class="rating-btn" class:active={testForm.recommend === 'no'} on:click={() => { testForm.recommend = 'no'; testNext(); }}>❌ No</button>
          </div>

        {:else if testStep === 14}
          <p class="step-label">💬 Additional Comments</p>
          <div class="form-group">
            <textarea bind:value={testForm.comments} placeholder="Any other details about their experience..." rows="4"></textarea>
          </div>
          <button class="action-btn" on:click={testNext}>Next →</button>

        {:else if testStep === 15}
          <p class="step-label">📸 Coupon Photo (optional)</p>
          <div class="form-group">
            <input type="file" accept="image/*" on:change={handleCouponImage} />
            {#if testForm.couponImage}
              <p class="hint">✅ {testForm.couponImage.name}</p>
            {:else}
              <p class="hint">Upload a photo of a redeemed coupon</p>
            {/if}
          </div>

          <div class="review-section">
            <h3>📋 Review</h3>
            <div class="review-row"><span>Name:</span><span>{testForm.name}</span></div>
            <div class="review-row"><span>Business:</span><span>{testForm.business}</span></div>
            <div class="review-row"><span>Address:</span><span>{testForm.address}</span></div>
            <div class="review-row"><span>Phone:</span><span>{testForm.phone}</span></div>
            <div class="review-row"><span>Store:</span><span>{testForm.groceryChain} {testForm.storeNumber}</span></div>
            <div class="review-row"><span>Coupons/wk:</span><span>{testForm.couponsPerWeek}</span></div>
            <div class="review-row"><span>Avg Ticket:</span><span>${testForm.avgTicket}</span></div>
            <div class="review-row"><span>ROI:</span><span>{testForm.roi}</span></div>
            <div class="review-row"><span>Duration:</span><span>{testForm.duration}</span></div>
            <div class="review-row"><span>Would Renew:</span><span>{testForm.wouldRenew}</span></div>
            <div class="review-row"><span>Recommend:</span><span>{testForm.recommend}</span></div>
            {#if testForm.comments}<div class="review-row"><span>Comments:</span><span>{testForm.comments}</span></div>{/if}
          </div>

          <button class="action-btn" on:click={submitTestimonial} disabled={testSubmitting}>
            {testSubmitting ? '⏳ Submitting...' : '✅ Submit Testimonial'}
          </button>
        {/if}

      </div>
    {/if}
  {/if}
</div>

<style>
  .tools-container {
    padding: 20px;
    max-width: 100%;
    margin: 0 auto;
  }

  h2 {
    margin: 0 0 8px;
    font-size: 24px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .subtitle {
    margin: 0 0 20px;
    color: var(--text-secondary);
    font-size: 14px;
  }

  .back-btn {
    background: none;
    border: none;
    color: #CC0000;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    padding: 10px 0;
    margin-bottom: 15px;
  }

  .back-btn:hover {
    text-decoration: underline;
  }

  .button-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1.5rem;
    width: 100%;
  }

  @media (min-width: 768px) {
    .button-grid {
      grid-template-columns: repeat(3, 1fr);
      gap: 2rem;
    }
  }

  @media (min-width: 1200px) {
    .button-grid {
      grid-template-columns: repeat(4, 1fr);
      gap: 2rem;
    }
  }

  .main-btn {
    background: var(--card-bg);
    border: 2px solid var(--border-color);
    border-radius: 16px;
    padding: 2rem 1.5rem;
    cursor: pointer;
    transition: all 0.2s;
    text-align: center;
    color: var(--text-primary);
    min-height: 180px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 100%;
  }

  .main-btn:hover {
    border-color: #cc0000;
    box-shadow: 0 4px 12px rgba(204, 0, 0, 0.1);
    transform: translateY(-2px);
  }

  .btn-icon { font-size: 2rem; margin-bottom: 0.5rem; }
  .btn-text { font-weight: 600; color: var(--text-primary, #eee); margin-bottom: 0.25rem; }
  .btn-desc { font-size: 0.85rem; color: var(--text-tertiary, #999); }

  .search-box {
    margin: 15px 0;
  }

  .search-box input {
    width: 100%;
    padding: 12px;
    border: 1px solid #ddd;
    border-radius: 8px;
    font-size: 14px;
    box-sizing: border-box;
  }

  .store-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    max-height: 400px;
    overflow-y: auto;
  }

  .store-card {
    background: white;
    border: 1px solid #eee;
    border-radius: 8px;
    padding: 12px;
  }

  .store-card h4 {
    margin: 0 0 4px;
    font-size: 14px;
    color: #333;
  }

  .store-num, .store-pricing {
    margin: 0;
    font-size: 12px;
    color: #666;
  }

  .store-pricing {
    color: #CC0000;
    font-weight: 600;
    margin-top: 4px;
  }

  .store-select-btn {
    background: white;
    border: 1px solid #eee;
    border-radius: 8px;
    padding: 12px;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .store-select-btn:hover {
    border-color: #CC0000;
    box-shadow: 0 2px 8px rgba(204, 0, 0, 0.1);
  }

  .store-select-btn h4 {
    margin: 0 0 4px;
    font-size: 14px;
    color: #333;
  }

  .arrow {
    color: #CC0000;
    font-size: 18px;
  }

  .info-card {
    background: #f9f9f9;
    border-radius: 12px;
    padding: 16px;
    margin-top: 15px;
  }

  .info-card p {
    margin: 0 0 12px;
    color: #555;
    font-size: 13px;
    line-height: 1.5;
  }

  .info-card ul {
    margin: 0;
    padding-left: 20px;
    font-size: 13px;
    color: #555;
  }

  .info-card li {
    margin: 4px 0;
  }

  .form-card {
    background: #f9f9f9;
    border-radius: 12px;
    padding: 16px;
    margin-top: 15px;
  }

  .form-label {
    display: block;
    margin-bottom: 12px;
    font-weight: 700;
    font-size: 14px;
    color: var(--text-primary);
  }

  .form-group {
    margin-bottom: 16px;
  }

  .form-group label {
    display: block;
    margin-bottom: 6px;
    font-weight: 600;
    font-size: 13px;
    color: #333;
  }

  .hint {
    margin-top: 4px;
    font-size: 12px;
    color: var(--text-secondary);
    font-style: italic;
  }

  .form-group input,
  .form-group textarea {
    width: 100%;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 6px;
    font-size: 13px;
    box-sizing: border-box;
    font-family: inherit;
  }

  .form-group textarea {
    min-height: 80px;
    resize: vertical;
  }

  .action-btn, .next-btn, .edit-btn {
    width: 100%;
    background: #CC0000;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    margin-top: 10px;
  }

  .action-btn:hover, .next-btn:hover {
    background: #990000;
  }

  .edit-btn {
    background: #666;
    margin-top: 8px;
  }

  .edit-btn:hover {
    background: #444;
  }

  .next-btn:disabled, .action-btn:disabled {
    background: #ccc;
    cursor: not-allowed;
    opacity: 0.7;
  }

  .review-card {
    background: #f5f5f5;
    border-radius: 12px;
    padding: 16px;
    margin-top: 16px;
  }

  .review-section {
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid #e0e0e0;
  }

  .review-section:last-of-type {
    border-bottom: none;
  }

  .review-section h4 {
    margin: 0 0 6px;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    color: #333;
    letter-spacing: 0.5px;
  }

  .review-section p {
    margin: 0;
    color: #555;
    font-size: 14px;
    line-height: 1.4;
  }

  .report-card {
    background: #f9f9f9;
    border-radius: 12px;
    padding: 16px;
    margin-top: 15px;
  }

  .report-header {
    font-size: 20px;
    font-weight: 700;
    color: #CC0000;
    margin-bottom: 4px;
  }

  .report-chain {
    margin: 0 0 16px;
    color: #666;
    font-size: 14px;
  }

  .report-section {
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid #e0e0e0;
  }

  .report-section h4 {
    margin: 0 0 8px;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    color: #333;
    letter-spacing: 0.5px;
  }

  .report-section p {
    margin: 4px 0;
    color: #555;
    font-size: 13px;
  }

  .report-status {
    padding: 12px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 13px;
    margin-bottom: 12px;
  }

  .status-ok {
    background: #e8f5e9;
    color: #2e7d32;
  }

  .status-warn {
    background: #fce4ec;
    color: #c62828;
  }

  .chain-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
    gap: 10px;
    margin-top: 15px;
  }

  .chain-btn {
    background: white;
    border: 2px solid #ddd;
    border-radius: 8px;
    padding: 12px 8px;
    font-weight: 600;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
    color: #333;
  }

  .chain-btn:hover {
    border-color: #CC0000;
    background: #fff5f5;
  }

  .upload-card {
    background: #f9f9f9;
    border-radius: 12px;
    padding: 16px;
    margin-top: 15px;
  }

  .upload-box {
    background: white;
    border: 2px dashed #ddd;
    border-radius: 8px;
    padding: 24px;
    text-align: center;
    margin-bottom: 16px;
  }

  .upload-box p {
    margin: 0 0 12px;
    color: #666;
    font-size: 14px;
  }

  .upload-box input[type="file"] {
    display: block;
    margin: 0 auto;
    cursor: pointer;
  }

  .upload-ok {
    color: #CC0000;
    font-weight: 600;
    margin-top: 12px !important;
  }

  .info-text {
    margin: 12px 0 0;
    color: #999;
    font-size: 12px;
  }

  .search-btn {
    background: #CC0000;
    color: white;
    border: none;
    padding: 10px 16px;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
    font-size: 14px;
    margin-top: 8px;
    width: 100%;
    transition: background 0.2s;
  }

  .search-btn:hover:not(:disabled) {
    background: #990000;
  }

  .search-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .error-card {
    background: #ffe0e0;
    border: 1px solid #ff9999;
    color: #c33;
    padding: 12px;
    border-radius: 8px;
    margin: 15px 0;
    font-size: 14px;
  }

  .success-card {
    background: #e8f5e9;
    border: 1px solid #81c784;
    color: #2e7d32;
    padding: 16px;
    border-radius: 8px;
    margin: 20px 0;
    text-align: center;
  }

  .success-card p {
    margin: 8px 0;
    font-size: 14px;
    font-weight: 600;
  }

  .form-group.checkbox {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 16px;
  }

  .form-group.checkbox input[type="checkbox"] {
    width: auto;
    padding: 0;
    margin: 0;
  }

  .form-group.checkbox label {
    margin: 0;
    font-weight: 500;
  }

  select {
    width: 100%;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 6px;
    font-size: 13px;
    box-sizing: border-box;
    font-family: inherit;
    color: #333;
  }

  /* Testimonial Steps */
  .step-progress { height: 4px; background: #eee; border-radius: 2px; margin-bottom: 20px; overflow: hidden; }
  .step-bar { height: 100%; background: #CC0000; border-radius: 2px; transition: width 0.3s; }
  .step-label { font-size: 16px; font-weight: 700; color: var(--text-primary); margin-bottom: 12px; }

  .rating-btns { display: flex; flex-direction: column; gap: 8px; }
  .rating-btn { padding: 14px; border: 2px solid #ddd; border-radius: 8px; background: var(--card-bg, white); font-size: 15px; font-weight: 600; cursor: pointer; text-align: center; transition: all 0.2s; color: var(--text-primary); }
  .rating-btn.active, .rating-btn:hover { border-color: #CC0000; background: #fff5f5; color: #CC0000; }

  .review-section { margin: 16px 0; padding: 12px; background: var(--bg-secondary, #f9f9f9); border-radius: 8px; }
  .review-section h3 { margin: 0 0 10px; font-size: 14px; font-weight: 700; }
  .review-row { display: flex; justify-content: space-between; padding: 4px 0; font-size: 12px; }
  .review-row span:first-child { color: var(--text-secondary); font-weight: 600; }
  .review-row span:last-child { color: var(--text-primary); text-align: right; max-width: 60%; }

  /* ROI Results */
  .roi-results { margin-top: 20px; }
  .roi-results h3 { margin: 0 0 16px; font-size: 18px; color: var(--text-primary); }
  .roi-stats { display: flex; gap: 10px; margin-bottom: 16px; }
  .roi-stat { flex: 1; background: var(--card-bg, white); border: 1px solid var(--border-color, #eee); border-radius: 10px; padding: 14px; text-align: center; }
  .roi-stat.highlight { border-color: #CC0000; background: #fff5f5; }
  .roi-value { display: block; font-size: 20px; font-weight: 700; color: #CC0000; }
  .roi-label { display: block; font-size: 11px; color: #888; margin-top: 4px; text-transform: uppercase; }
  .roi-detail { background: var(--card-bg, white); border: 1px solid var(--border-color, #eee); border-radius: 10px; padding: 16px; }
  .roi-row { display: flex; justify-content: space-between; padding: 8px 0; font-size: 13px; border-bottom: 1px solid #f0f0f0; }
  .roi-row:last-child { border-bottom: none; }
  .roi-row.total { font-weight: 700; font-size: 14px; border-top: 2px solid #ddd; padding-top: 12px; margin-top: 4px; }
  .roi-row .cost { color: #c33; }
  .roi-row .profit { color: #2e7d32; font-weight: 700; }
  .roi-export-actions { display: flex; gap: 8px; margin-top: 16px; }
  .roi-export-actions .action-btn { flex: 1; font-size: 13px; padding: 10px; }
  .roi-verdict { margin-top: 16px; padding: 14px; border-radius: 10px; font-size: 14px; font-weight: 600; text-align: center; }
  .roi-verdict.positive { background: #e8f5e9; color: #2e7d32; border: 1px solid #81c784; }
  .roi-verdict.negative { background: #ffe0e0; color: #c33; border: 1px solid #ff9999; }

  .store-info-card { padding: 12px; background: #fff5f5; border: 1px solid #CC0000; border-radius: 8px; }
  .store-info-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 15px; color: #333; }
  .store-info-details { display: flex; flex-wrap: wrap; gap: 8px 16px; margin-bottom: 8px; font-size: 12px; color: var(--text-secondary); }
  .store-info-prices { display: flex; gap: 16px; font-size: 13px; color: var(--text-secondary); }
  .store-info-prices span.active { color: #CC0000; font-weight: 700; }

  .ad-size-toggle { display: flex; gap: 8px; }
  .size-btn { flex: 1; padding: 10px; border: 2px solid #ddd; border-radius: 8px; background: var(--card-bg, white); font-size: 14px; font-weight: 600; cursor: pointer; text-align: center; transition: all 0.2s; color: var(--text-primary); }
  .size-btn.active { border-color: #CC0000; background: #fff5f5; color: #CC0000; }
  .size-btn:hover { border-color: #CC0000; }

  .selected-store-badge { display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; background: #fff5f5; border: 1px solid #CC0000; border-radius: 6px; font-size: 13px; font-weight: 600; color: #333; }
  .clear-btn { background: none; border: none; color: #CC0000; font-size: 16px; cursor: pointer; padding: 0 4px; font-weight: 700; }
  .roi-store-list { display: flex; flex-direction: column; gap: 4px; margin-top: 6px; max-height: 200px; overflow-y: auto; }
  .roi-store-btn { text-align: left; padding: 10px; background: var(--card-bg, white); border: 1px solid var(--border-color, #eee); border-radius: 6px; font-size: 12px; cursor: pointer; transition: all 0.2s; color: var(--text-primary); }
  .roi-store-btn:hover { border-color: #CC0000; background: #fff5f5; }
  .roi-store-btn .store-id { float: right; color: #CC0000; font-weight: 600; font-size: 11px; }

  .results-card {
    background: white;
    border: 1px solid #eee;
    border-radius: 8px;
    padding: 16px;
    margin-top: 15px;
  }

  .results-card h3 {
    margin: 0 0 16px;
    font-size: 16px;
    color: #333;
  }

  .testimonial-item {
    padding: 12px 0;
    border-bottom: 1px solid #f0f0f0;
  }

  .testimonial-item:last-child {
    border-bottom: none;
  }

  .testimonial-item h4 {
    margin: 0 0 6px;
    font-size: 14px;
    color: #333;
    font-weight: 600;
  }

  .testimonial-item .comment {
    margin: 0 0 8px;
    font-size: 13px;
    color: #666;
    font-style: italic;
  }

  .testimonial-link {
    color: #CC0000;
    text-decoration: none;
    font-size: 13px;
    font-weight: 600;
    transition: color 0.2s;
  }

  .testimonial-link:hover {
    color: #990000;
    text-decoration: underline;
  }

  .hint {
    text-align: center;
    color: #999;
    font-size: 13px;
    margin-top: 20px;
    padding: 20px;
  }

  .next-delivery-highlight {
    margin: 12px 0 4px !important;
    padding: 10px;
    background: #fff5f5;
    border-left: 4px solid #CC0000;
    border-radius: 4px;
    font-size: 14px !important;
    font-weight: 600;
  }

  .next-delivery-highlight strong {
    color: #CC0000;
    font-size: 16px;
  }

  .next-delivery-detail {
    margin: 0 !important;
    padding: 0 0 0 10px;
    font-size: 12px !important;
    color: var(--text-secondary);
  }
</style>
