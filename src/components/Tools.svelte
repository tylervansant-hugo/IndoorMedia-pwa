<script>
  import { onMount } from 'svelte';
  import { PDFDocument, rgb, StandardFonts } from 'pdf-lib';
  import { user } from '../lib/stores.js';
  
  let view = 'main'; // main, roi, rates, testimonials, audit, counter-sign
  let stores = [];
  let allStores = [];
  let searchQuery = '';
  let selectedStore = null;
  
  // Testimonials state
  let testimonialQuery = '';
  let testimonialResults = [];
  let testimonialLoading = false;
  let testimonialError = '';
  
  // Audit state
  let auditStoreNum = null;
  let auditStep = 1; // 1: select store, 2: enter inventory, 3: report
  let auditCases = '';
  let auditRolls = '';
  let auditDate = new Date().toISOString().split('T')[0];
  let auditStartingCases = '';
  let auditReport = null;
  
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
    : 'https://genetics-born-placing-economic.trycloudflare.com';
  
  // On production, try to fetch the latest tunnel URL
  if (!isDev) {
    fetch('/api/counter-sign-url')
      .then(r => r.json())
      .then(d => { if (d.url) COUNTER_SIGN_API = d.url; })
      .catch(() => {}); // Fall back to hardcoded URL
  }

  onMount(async () => {
    try {
      const res = await fetch('/data/stores.json');
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

  async function searchTestimonials() {
    if (!testimonialQuery.trim()) {
      testimonialResults = [];
      return;
    }

    testimonialLoading = true;
    testimonialError = '';

    try {
      const response = await fetch(`/api/search-testimonials?q=${encodeURIComponent(testimonialQuery)}`);
      if (!response.ok) throw new Error('Search failed');
      const data = await response.json();
      testimonialResults = data.results || [];
      if (testimonialResults.length === 0) {
        testimonialError = `No testimonials found for "${testimonialQuery}"`;
      }
    } catch (err) {
      testimonialError = `Error searching testimonials: ${err.message}`;
      testimonialResults = [];
    } finally {
      testimonialLoading = false;
    }
  }

  function selectAuditStore(store) {
    selectedStore = store;
    auditStoreNum = store.StoreName;
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
    const today = new Date();
    const daysSinceDelivery = Math.max(1, Math.floor((today - delDate) / (1000 * 60 * 60 * 24)));
    const rollsUsed = startingRolls - totalRolls;
    const usagePerDay = Math.round((rollsUsed / daysSinceDelivery) * 10) / 10;
    const daysUntilRunout = usagePerDay > 0 ? Math.round((totalRolls / usagePerDay) * 10) / 10 : 999;

    const runoutDate = new Date();
    runoutDate.setDate(runoutDate.getDate() + Math.floor(daysUntilRunout));

    // Estimate next delivery (28-day cycle from last delivery)
    const nextDelivery = new Date(delDate);
    while (nextDelivery <= new Date()) {
      nextDelivery.setDate(nextDelivery.getDate() + 28);
    }
    const daysUntilDelivery = Math.ceil((nextDelivery - new Date()) / (1000 * 60 * 60 * 24));
    const insufficient = daysUntilRunout < daysUntilDelivery;

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
      daysUntilDelivery: daysUntilDelivery,
      insufficient: insufficient
    };
    auditStep = 3;
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
      line('Audit Date:', new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }));

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

    <div class="tools-grid">
      <button class="tool-btn" on:click={() => view = 'roi'}>
        <div class="tool-emoji">📊</div>
        <h4>ROI Calculator</h4>
        <p>Calculate campaign ROI before pitching</p>
      </button>

      <button class="tool-btn" on:click={() => view = 'rates'}>
        <div class="tool-emoji">💰</div>
        <h4>Store Rates</h4>
        <p>Quick pricing lookup by store</p>
      </button>

      <button class="tool-btn" on:click={() => view = 'testimonials'}>
        <div class="tool-emoji">📋</div>
        <h4>Testimonials</h4>
        <p>Find relevant case studies</p>
      </button>

      <button class="tool-btn" on:click={() => view = 'audit'}>
        <div class="tool-emoji">🏪</div>
        <h4>Audit Store</h4>
        <p>Track tape inventory & delivery</p>
      </button>

      <button class="tool-btn" on:click={() => view = 'counter-sign'}>
        <div class="tool-emoji">🎨</div>
        <h4>Counter Sign</h4>
        <p>Generate counter signs (same as bot)</p>
      </button>

    </div>
  {/if}

  <!-- ROI Calculator -->
  {#if view === 'roi'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    <h2>📊 ROI Calculator</h2>
    <p class="subtitle">Calculate campaign ROI before pitching</p>

    <div class="info-card">
      <p>💡 Use this tool to show customers potential ROI on register tape campaigns.</p>
      <p>Input estimated redemptions, average ticket, COGS, and we'll calculate break-even and monthly/annual profit.</p>
      
      <div class="form-group">
        <label>Monthly Redemptions</label>
        <input type="number" placeholder="e.g., 30" />
      </div>

      <div class="form-group">
        <label>Average Ticket ($)</label>
        <input type="number" placeholder="e.g., 50" />
      </div>

      <div class="form-group">
        <label>Coupon Discount ($)</label>
        <input type="number" placeholder="e.g., 10" />
      </div>

      <div class="form-group">
        <label>COGS (%)</label>
        <input type="number" placeholder="e.g., 35" />
      </div>

      <button class="action-btn">Calculate ROI</button>
    </div>
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
        <div class="form-group">
          <label>Last Delivery Date</label>
          <input type="date" bind:value={auditDate} />
        </div>

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
      </div>

    {:else if auditStep === 3 && auditReport}
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
          <p>Next delivery: {auditReport.nextDelivery} ({auditReport.daysUntilDelivery} days)</p>
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
</div>

<style>
  .tools-container {
    padding: 20px;
    max-width: 600px;
    margin: 0 auto;
  }

  h2 {
    margin: 0 0 8px;
    font-size: 24px;
    color: #333;
  }

  .subtitle {
    margin: 0 0 20px;
    color: #666;
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

  .tools-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
    margin-top: 20px;
  }

  .tool-btn {
    background: white;
    border: 2px solid #eee;
    border-radius: 12px;
    padding: 16px;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s;
  }

  .tool-btn:hover {
    border-color: #CC0000;
    background: #fff5f5;
  }

  .tool-emoji {
    font-size: 32px;
    margin-bottom: 8px;
  }

  .tool-btn h4 {
    margin: 0 0 6px;
    color: #333;
    font-size: 16px;
  }

  .tool-btn p {
    margin: 0;
    color: #666;
    font-size: 13px;
  }

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
</style>
