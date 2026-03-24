<script>
  import { onMount } from 'svelte';
  
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
  let counterSignStep = 1; // 1: select store, 2: business info, 3: confirm
  let selectedCounterStore = null;
  let counterData = {
    business_name: '',
    business_card_text: '',
    contact_phone: '',
    offer_text: '',
    cta_text: ''
  };

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

  function selectCounterStore(store) {
    selectedCounterStore = store;
    counterSignStep = 2;
  }

  function submitCounterSign() {
    // This would call the counter sign generator API with store template
    console.log('Generating counter sign:', { store: selectedCounterStore?.StoreName, ...counterData });
    alert('✅ Counter sign generated and ready to download!');
    counterSignStep = 1;
    selectedCounterStore = null;
    counterData = { business_name: '', business_card_text: '', contact_phone: '', offer_text: '', cta_text: '' };
    view = 'main';
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
        <p>Generate custom counter signs</p>
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

        <button class="action-btn">📧 Submit Audit</button>
      </div>
    {/if}
  {/if}

  <!-- Counter Sign Generator -->
  {#if view === 'counter-sign'}
    <button class="back-btn" on:click={goBack}>← Back</button>
    
    {#if counterSignStep === 1}
      <h2>🎨 Counter Sign Generator</h2>
      <p class="subtitle">Create custom counter signs</p>

      <div class="search-box">
        <input
          type="text"
          placeholder="Select store..."
          bind:value={searchQuery}
        />
      </div>

      <div class="store-list">
        {#each filteredStores.slice(0, 15) as store}
          <button class="store-select-btn" on:click={() => selectCounterStore(store)}>
            <div>
              <h4>{store.GroceryChain} - {store.City}</h4>
              <p class="store-num">{store.StoreName}</p>
            </div>
            <div class="arrow">→</div>
          </button>
        {/each}
      </div>
    {/if}

    {#if counterSignStep === 2}
      <h2>Business Information</h2>
      <p class="subtitle">{selectedCounterStore?.GroceryChain} - {selectedCounterStore?.City}</p>

      <div class="form-card">
        <div class="form-group">
          <label>Business Name *</label>
          <input type="text" bind:value={counterData.business_name} placeholder="e.g., Acme Salon" />
        </div>

        <div class="form-group">
          <label>Contact Phone</label>
          <input type="tel" bind:value={counterData.contact_phone} placeholder="(555) 123-4567" />
        </div>

        <div class="form-group">
          <label>Business Card Text</label>
          <input type="text" bind:value={counterData.business_card_text} placeholder="e.g., Your tagline here" />
        </div>

        <div class="form-group">
          <label>Offer Text *</label>
          <textarea bind:value={counterData.offer_text} placeholder="e.g., Save 20% on your first visit" rows="3" />
        </div>

        <div class="form-group">
          <label>Call-to-Action Text</label>
          <input type="text" bind:value={counterData.cta_text} placeholder="e.g., CALL NOW, LEARN MORE" />
        </div>

        <button class="next-btn" on:click={() => counterSignStep = 3} disabled={!counterData.business_name || !counterData.offer_text}>
          Review & Generate →
        </button>
      </div>
    {/if}

    {#if counterSignStep === 3}
      <h2>Review Counter Sign</h2>
      <p class="subtitle">{selectedCounterStore?.GroceryChain} - {selectedCounterStore?.City}</p>

      <div class="review-card">
        <div class="review-section">
          <h4>Business Name</h4>
          <p>{counterData.business_name}</p>
        </div>

        <div class="review-section">
          <h4>Contact</h4>
          <p>{counterData.contact_phone || 'Not provided'}</p>
        </div>

        <div class="review-section">
          <h4>Offer</h4>
          <p>{counterData.offer_text}</p>
        </div>

        <div class="review-section">
          <h4>Call-to-Action</h4>
          <p>{counterData.cta_text || 'LEARN MORE'}</p>
        </div>

        <button class="action-btn" on:click={submitCounterSign}>
          ✅ Generate PDF
        </button>
        
        <button class="edit-btn" on:click={() => counterSignStep = 2}>
          ✏️ Edit Info
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

  .next-btn:disabled {
    background: #ccc;
    cursor: not-allowed;
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
</style>
