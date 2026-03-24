<script>
  import { onMount } from 'svelte';
  import { PDFDocument, rgb, StandardFonts } from 'pdf-lib';
  import { user } from '../lib/stores.js';
  
  let view = 'main'; // main, roi, rates, testimonials, audit, counter-sign
  let stores = [];
  let allStores = [];
  let searchQuery = '';
  let selectedStore = null;
  
  // Audit state
  let auditStoreNum = null;
  let auditCases = 20;
  let auditDate = new Date().toISOString().split('T')[0];
  
  // Counter sign state
  let counterSignStep = 1; // 1: chain, 2: business card, 3: landing page, 4: ad proof, 5: confirm
  let selectedChainCode = null;
  let counterData = {
    business_card_image: null,
    landing_page_url: '',
    ad_proof_image: null
  };
  let generating = false;
  const COUNTER_SIGN_API = 'https://likewise-cottage-announcement-apps.trycloudflare.com';

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
    if (view === 'audit' && auditStoreNum) {
      auditStoreNum = null;
    } else if (view === 'counter-sign' && counterSignStep > 1) {
      counterSignStep--;
    } else {
      view = 'main';
      selectedStore = null;
      searchQuery = '';
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

  // Audit tool - generate downloadable report
  async function submitAudit() {
    try {
      const repName = $user?.name || $user?.first_name || 'Unknown Rep';
      const store = selectedStore;
      
      const pdfDoc = await PDFDocument.create();
      const page = pdfDoc.addPage([612, 792]);
      const font = await pdfDoc.embedFont('Helvetica-Bold');
      const fontR = await pdfDoc.embedFont('Helvetica');
      
      // Header
      page.drawRectangle({ x: 0, y: 700, width: 612, height: 92, color: rgb(0.8, 0, 0) });
      page.drawText('Store Audit Report', { x: 30, y: 735, size: 24, font, color: rgb(1, 1, 1) });
      
      // Content
      let y = 660;
      const line = (label, value) => {
        page.drawText(label, { x: 40, y, size: 12, font, color: rgb(0.2, 0.2, 0.2) });
        page.drawText(value, { x: 200, y, size: 12, font: fontR, color: rgb(0.3, 0.3, 0.3) });
        y -= 30;
      };
      
      line('Store:', `${store?.GroceryChain || ''} - ${store?.City || ''}`);
      line('Store #:', auditStoreNum || '');
      line('Rep:', repName);
      line('Audit Date:', new Date().toLocaleDateString());
      line('Last Delivery:', auditDate);
      line('Cases in Stock:', String(auditCases));
      
      y -= 20;
      // Status
      const daysAgo = Math.floor((Date.now() - new Date(auditDate).getTime()) / (1000 * 60 * 60 * 24));
      let status = '🟢 Recent';
      if (daysAgo > 45) status = '🔴 OVERDUE';
      else if (daysAgo > 30) status = '🟡 Approaching';
      
      page.drawText('Delivery Status:', { x: 40, y, size: 12, font, color: rgb(0.2, 0.2, 0.2) });
      page.drawText(`${status} (${daysAgo} days since delivery)`, { x: 200, y, size: 12, font: fontR, color: rgb(0.3, 0.3, 0.3) });
      y -= 30;
      
      page.drawText('Estimated Runout:', { x: 40, y, size: 12, font, color: rgb(0.2, 0.2, 0.2) });
      const runoutDays = Math.round(auditCases * 3.5);
      page.drawText(`~${runoutDays} days (${auditCases} cases × 3.5 days/case)`, { x: 200, y, size: 12, font: fontR, color: rgb(0.3, 0.3, 0.3) });
      
      // Footer
      page.drawText(`Generated ${new Date().toLocaleString()} — IndoorMedia Audit Tool`, {
        x: 150, y: 20, size: 8, font: fontR, color: rgb(0.6, 0.6, 0.6)
      });
      
      const pdfBytes = await pdfDoc.save();
      downloadBlob(new Blob([pdfBytes], { type: 'application/pdf' }), `Audit_${auditStoreNum || 'Store'}.pdf`);
      
    } catch (err) {
      alert(`❌ Error: ${err.message}`);
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
    <p class="subtitle">Find relevant case studies</p>

    <div class="search-box">
      <input
        type="text"
        placeholder="Search by keyword, business type, ROI..."
      />
    </div>

    <div class="info-card">
      <p>💡 Search for testimonials by:</p>
      <ul>
        <li>Business category (dental, restaurant, salon, etc.)</li>
        <li>Keywords (ROI, foot traffic, sales increase, etc.)</li>
        <li>Specific results (parking lot, drive-through, etc.)</li>
      </ul>
    </div>
  {/if}

  <!-- Audit Store -->
  {#if view === 'audit'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    
    {#if !auditStoreNum}
      <h2>🏪 Audit Store</h2>
      <p class="subtitle">Track tape inventory & delivery status</p>

      <div class="search-box">
        <input
          type="text"
          placeholder="Search store..."
          bind:value={searchQuery}
        />
      </div>

      <div class="store-list">
        {#each filteredStores.slice(0, 15) as store}
          <button class="store-select-btn" on:click={() => selectAuditStore(store)}>
            <div>
              <h4>{store.GroceryChain} - {store.City}</h4>
              <p class="store-num">{store.StoreName}</p>
            </div>
            <div class="arrow">→</div>
          </button>
        {/each}
      </div>
    {:else}
      <h2>🏪 Audit: {auditStoreNum}</h2>

      <div class="form-card">
        <div class="form-group">
          <label>Last Delivery Date</label>
          <input type="date" bind:value={auditDate} />
        </div>

        <div class="form-group">
          <label>Cases in Stock</label>
          <input type="number" bind:value={auditCases} min="0" />
        </div>

        <button class="action-btn" on:click={submitAudit}>📥 Generate Audit Report</button>
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
    background: #f9f9f9;
    border-radius: 12px;
    padding: 16px;
    margin-top: 15px;
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
</style>
// cache bust 1774325294
