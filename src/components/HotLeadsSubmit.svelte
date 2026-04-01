<script>
  import { onMount } from 'svelte';
  
  export let user;
  export let onLeadSubmitted = () => {};
  
  let submitMode = 'manual'; // 'manual' or 'card'
  let formData = {
    business_name: '',
    contact_name: '',
    category: 'Restaurant',
    phone: '',
    email: '',
    address: '',
    store_id: '',
    store_chain: '',
    store_city: '',
    distance_mi: ''
  };
  
  let cardImage = null;
  let cardImagePreview = null;
  let ocrLoading = false;
  let ocrText = '';
  let extractedData = null;
  let submitting = false;
  let submitMessage = '';
  let tesseractReady = false;
  
  let allStores = [];
  let filteredStores = [];
  let storeSearchText = '';
  
  const categories = [
    'Auto / Accessories / Parts',
    'Auto / Car Wash / Detailing',
    'Auto / Inspection / Testing / Smog',
    'Auto / Repair / Body / Maintenance',
    'Auto / Sales / Leasing / Rental',
    'Auto / Towing / Storage',
    'Beauty / Beauty & Health',
    'Beauty / Hair / Nails / Spa / Tanning',
    'Education / School',
    'Entertainment / Bar / Night Club',
    'Entertainment / Dance Studio / Classes',
    'Entertainment / Family Entertainment',
    'Entertainment / Gaming / Casinos',
    'Entertainment / Golf Courses / Supplies',
    'Entertainment / Hotel / Motel',
    'Entertainment / Martial Arts',
    'Entertainment / Music / Lessons',
    'Entertainment / Party Supplies / Planning',
    'Entertainment / Recreation Centers / Halls',
    'Entertainment / Sports Bar / Lounge / Winery',
    'Entertainment / Tattoos & Piercing',
    'Entertainment / Travel Agencies',
    'General / Child Care',
    'General / Community Services',
    'Health / Blood / Plasma Donations',
    'Health / CBD',
    'Health / Dental / Orthodontics',
    'Health / Dispensary',
    'Health / Fitness & Health',
    'Health / Hearing Aids / Devices',
    'Health / Medical',
    'Health / Optical',
    'Health / Pharmaceuticals',
    'Health / Senior Care / Living',
    'Home Services / Cleaning / Maid Service',
    'Home Services / Dry Cleaning / Laundry / Tailors',
    'Home Services / Energy',
    'Home Services / Funeral Home / Cemetery',
    'Home Services / Glass Repair',
    'Home Services / Home Improvement / Contracting',
    'Home Services / Pet Care',
    'Home Services / Propane & Natural Gas',
    'Home Services / Real Estate / Realtors',
    'Home Services / Recycling / Salvage',
    'Home Services / Rental Services',
    'Home Services / Storage',
    'Home Services / Tool Repair & Parts',
    'Home Services / Vehicle & License Registration',
    'Home Services / Video / Production',
    'Home Services / Water Delivery',
    'Legal / Attorney / Law Firm',
    'Legal / Mortgage',
    'Insurance',
    'Personal Finance / Financial',
    'Professional Services / Audio / Video Equipment',
    'Professional Services / Computers / Repair',
    'Professional Services / Printing / Supplies',
    'Professional Services / Recruiting',
    'Professional Services / Restaurant Equipment',
    'Professional Services / Transportation / Delivery',
    'Professional Services / Water Treatment',
    'Restaurant / Asian',
    'Restaurant / Bakery',
    'Restaurant / Breweries',
    'Restaurant / Casual Dining',
    'Restaurant / Catering',
    'Restaurant / Coffee Shops',
    'Restaurant / Cultural Dining',
    'Restaurant / Deli',
    'Restaurant / Donut Shops',
    'Restaurant / Fast Food',
    'Restaurant / Fine Dining',
    'Restaurant / Food Delivery',
    'Restaurant / Ice Cream / Yogurt Shops',
    'Restaurant / Mexican',
    'Restaurant / Pizza',
    'Restaurant / Sandwich Shops',
    'Retail / Antiques & Collectibles',
    'Retail / Arts & Crafts',
    'Retail / Barbeque Grills & Supplies',
    'Retail / Battery Supplies',
    'Retail / Bicycle Shop',
    'Retail / Candy & Sweets',
    'Retail / Communication',
    'Retail / Convenience Store / Gas Station',
    'Retail / Feed Store / Farm Equipment',
    'Retail / Florists',
    'Retail / Framing',
    'Retail / Furniture',
    'Retail / Grocery Store',
    'Retail / Hobby Shops / Equipment',
    'Retail / Jewelry / Watch Repair',
    'Retail / Liquor Store',
    'Retail / Pawn Shops / Gold & Silver',
    'Retail / Pet Supply Store',
    'Retail / Shopping / Boutique',
    'Retail / Sewing Machines / Contractors',
    'Retail / Shipping / Postal Services',
    'Retail / Smoke Shop',
    'Retail / Specialty Foods',
    'Retail / Sporting / Military Goods',
    'Retail / Toys / Games',
    'Retail / Vacuums',
    'Other / Unknown',
  ];
  
  // Load Tesseract.js
  async function loadTesseract() {
    if (window.Tesseract || tesseractReady) return;
    
    return new Promise((resolve) => {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js';
      script.onload = () => {
        tesseractReady = true;
        resolve();
      };
      script.onerror = () => {
        console.error('Failed to load Tesseract');
        resolve(); // Continue anyway
      };
      document.head.appendChild(script);
    });
  }
  
  onMount(async () => {
    // Load all 7,835 stores for reference
    try {
      const response = await fetch(import.meta.env.BASE_URL + 'data/stores.json');
      const stores = await response.json();
      allStores = stores.map(s => ({
        id: s.StoreName,
        chain: s.GroceryChain,
        city: s.City,
        state: s.State,
        address: s.Address,
        cycle: s.Cycle
      }));
      console.log(`Loaded ${allStores.length} stores for reference`);
    } catch (err) {
      console.error('Error loading stores:', err);
    }
    
    // Load Tesseract.js for OCR
    await loadTesseract();
  });
  
  function handleCardImageSelect(e) {
    const file = e.target.files?.[0];
    if (file) {
      cardImage = file;
      const reader = new FileReader();
      reader.onload = (event) => {
        cardImagePreview = event.target?.result;
      };
      reader.readAsDataURL(file);
    }
  }
  
  async function extractFromCard() {
    if (!cardImage) return;
    
    ocrLoading = true;
    submitMessage = 'Loading OCR...';
    
    try {
      // Wait for Tesseract to load
      await loadTesseract();
      
      if (!window.Tesseract) {
        submitMessage = '⚠️ OCR unavailable. Please fill in info manually.';
        ocrLoading = false;
        return;
      }
      
      submitMessage = 'Reading business card...';
      
      // Use Tesseract.js for OCR
      const { data: { text } } = await window.Tesseract.recognize(cardImagePreview, 'eng');
      ocrText = text;
      
      // Try to extract phone, email, name, address
      const phoneMatch = text.match(/\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})/);
      const emailMatch = text.match(/[\w\.-]+@[\w\.-]+\.\w+/);
      
      // Extract contact name (usually first line or before title)
      const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0);
      let contactName = '';
      if (lines.length > 0) {
        // First line is often the name (if not title)
        const firstLine = lines[0];
        if (firstLine.length < 50 && !firstLine.match(/\d{3}/) && !firstLine.includes('@')) {
          contactName = firstLine;
        }
      }
      
      // Extract address (look for zip code pattern)
      const addressMatch = text.match(/\d+\s+[A-Za-z\s]+(?:St|Ave|Blvd|Dr|Rd|Lane|Way|Court),?\s*[A-Za-z\s]+,?\s*[A-Z]{2}\s*\d{5}/);
      const address = addressMatch ? addressMatch[0] : '';
      
      extractedData = {
        phone: phoneMatch ? `(${phoneMatch[1]}) ${phoneMatch[2]}-${phoneMatch[3]}` : '',
        email: emailMatch ? emailMatch[0] : '',
        contact_name: contactName,
        address: address,
        business_name: '', // User needs to fill this
        raw_text: text
      };
      
      if (extractedData.phone) formData.phone = extractedData.phone;
      if (extractedData.email) formData.email = extractedData.email;
      if (extractedData.contact_name) formData.contact_name = extractedData.contact_name;
      if (extractedData.address) {
        formData.address = extractedData.address;
        // Find nearest 3 stores to this address
        findNearestStores(extractedData.address);
      }
      
      submitMessage = '✓ Card read! Review and fill in any missing info.';
      ocrLoading = false;
    } catch (err) {
      console.error('OCR error:', err);
      submitMessage = `Error reading card: ${err.message || 'Unknown error'}. Please fill in manually.`;
      ocrLoading = false;
    }
  }
  
  function findNearestStores(address) {
    // Simple heuristic: find stores by city/state from address
    const addressLower = address.toLowerCase();
    const stateMatch = address.match(/[A-Z]{2}\s*\d{5}/);
    
    if (!stateMatch) {
      filteredStores = [];
      return;
    }
    
    const state = stateMatch[0].substring(0, 2);
    
    // Find stores in same state, limit to 3
    const nearbyStores = allStores
      .filter(s => s.State === state)
      .slice(0, 3);
    
    if (nearbyStores.length > 0) {
      // Auto-select first nearby store as reference
      formData.store_id = nearbyStores[0].StoreName;
      formData.store_chain = nearbyStores[0].GroceryChain;
      formData.store_city = nearbyStores[0].City;
    }
  }
  
  function filterStores(text) {
    storeSearchText = text;
    if (!text || text.length < 2) {
      filteredStores = [];
      return;
    }
    const search = text.toLowerCase();
    filteredStores = allStores.filter(s => 
      s.id.toLowerCase().includes(search) ||
      s.chain.toLowerCase().includes(search) ||
      s.city.toLowerCase().includes(search) ||
      (s.state && s.state.toLowerCase().includes(search)) ||
      `${s.chain} ${s.city}`.toLowerCase().includes(search)
    ).slice(0, 8);
  }
  
  function selectStore(store) {
    formData.store_id = store.id;
    formData.store_chain = store.chain;
    formData.store_city = store.city;
    storeSearchText = `${store.chain} — ${store.city}, ${store.state} (${store.id})`;
    filteredStores = [];
  }
  
  async function submitLead() {
    // Validate
    if (!formData.business_name || !formData.phone || !formData.email) {
      alert('Please fill in: Business Name, Phone, Email');
      return;
    }
    
    submitting = true;
    submitMessage = 'Saving lead...';
    
    try {
      const newLead = {
        ...formData,
        submitted_by: user?.name || 'Unknown',
        submitted_at: new Date().toISOString(),
        status: 'approved',
        _hook: `Submitted by ${user?.name || 'rep'}`
      };
      
      // Save to localStorage (no backend API)
      const leads = JSON.parse(localStorage.getItem('submitted_leads') || '[]');
      leads.push(newLead);
      localStorage.setItem('submitted_leads', JSON.stringify(leads));
      
      submitMessage = '✅ Lead added to Hot Leads!';
      
      // Reset form
      setTimeout(() => {
        formData = {
          business_name: '',
          contact_name: '',
          category: 'Restaurant',
          phone: '',
          email: '',
          address: '',
          store_id: '',
          store_chain: '',
          store_city: '',
          distance_mi: ''
        };
        cardImage = null;
        cardImagePreview = null;
        ocrText = '';
        extractedData = null;
        submitMessage = '';
        submitting = false;
        
        onLeadSubmitted();
      }, 2000);
    } catch (err) {
      submitMessage = `Error: ${err.message}`;
      submitting = false;
    }
  }
</script>

<div class="submit-container">
  <div class="submit-header">
    <h3>➕ Submit New Lead</h3>
    <p>Found a business? Add it here.</p>
  </div>
  
  <div class="mode-toggle">
    <button 
      class="mode-btn" 
      class:active={submitMode === 'manual'}
      on:click={() => submitMode = 'manual'}
    >
      ✍️ Manual Entry
    </button>
    <button 
      class="mode-btn"
      class:active={submitMode === 'card'}
      on:click={() => submitMode = 'card'}
    >
      📷 Business Card
    </button>
  </div>
  
  {#if submitMode === 'card'}
    <div class="card-upload">
      <div class="upload-area">
        <input
          id="card-file"
          type="file"
          accept="image/*"
          on:change={handleCardImageSelect}
          class="file-input"
          capture="environment"
        />
        <label for="card-file" class="upload-label">
          📸 Upload Business Card
        </label>
        {#if cardImagePreview}
          <div class="preview">
            <img src={cardImagePreview} alt="Card preview" />
          </div>
        {/if}
      </div>
      
      {#if cardImage && !extractedData}
        <button class="extract-btn" on:click={extractFromCard} disabled={ocrLoading}>
          {ocrLoading ? 'Reading card...' : '🔍 Extract Text'}
        </button>
      {/if}
      
      {#if ocrText}
        <div class="ocr-result">
          <h4>Extracted Text:</h4>
          <pre>{ocrText}</pre>
        </div>
      {/if}
    </div>
  {/if}
  
  <div class="form-section">
    <div class="form-group">
      <label>Business Name *</label>
      <input
        type="text"
        placeholder="e.g., Golden Star Chinese Restaurant"
        bind:value={formData.business_name}
      />
    </div>
    
    <div class="form-group">
      <label>Contact Name</label>
      <input
        type="text"
        placeholder="e.g., John Smith"
        bind:value={formData.contact_name}
      />
    </div>
    
    <div class="form-row">
      <div class="form-group">
        <label>Category</label>
        <select bind:value={formData.category}>
          {#each categories as cat}
            <option>{cat}</option>
          {/each}
        </select>
      </div>
      

    </div>
    
    <div class="form-row">
      <div class="form-group">
        <label>Phone *</label>
        <input
          type="tel"
          placeholder="(360) 373-1320"
          bind:value={formData.phone}
        />
      </div>
      
      <div class="form-group">
        <label>Email *</label>
        <input
          type="email"
          placeholder="info@business.com"
          bind:value={formData.email}
        />
      </div>
    </div>
    
    <div class="form-group">
      <label>Address (optional)</label>
      <input
        type="text"
        placeholder="123 Main St, City, WA 98000"
        bind:value={formData.address}
      />
    </div>
    
    <div class="form-group">
      <label>Store Reference (optional)</label>
      <input
        type="text"
        placeholder="Search by store ID, chain, or city..."
        value={storeSearchText}
        on:input={(e) => filterStores(e.target.value)}
      />
      {#if filteredStores.length > 0}
        <div class="store-suggestions">
          {#each filteredStores as store}
            <button
              class="suggestion-item"
              on:click={() => selectStore(store)}
            >
              <strong>{store.chain}</strong> — {store.city}, {store.state}
              <small>{store.id} · Cycle {store.cycle}</small>
            </button>
          {/each}
        </div>
      {/if}
      {#if formData.store_id}
        <div class="selected-store">
          ✅ {formData.store_chain} — {formData.store_city} ({formData.store_id})
        </div>
      {/if}
    </div>
    
    {#if submitMessage}
      <div class="message" class:loading={submitting} class:success={submitMessage.includes('✅')}>
        {submitMessage}
      </div>
    {/if}
    
    <button
      class="submit-btn"
      on:click={submitLead}
      disabled={submitting || !formData.business_name || !formData.phone || !formData.email}
    >
      {submitting ? '⏳ Saving...' : '📤 Submit Lead'}
    </button>
  </div>
</div>

<style>
  .submit-container {
    background: white;
    border-radius: 12px;
    padding: 24px;
    max-width: 800px;
    margin: 0 auto;
    width: 100%;
    box-sizing: border-box;
  }
  
  .submit-header {
    margin-bottom: 24px;
  }
  
  .submit-header h3 {
    margin: 0 0 4px 0;
    font-size: 20px;
    color: #333;
  }
  
  .submit-header p {
    margin: 0;
    font-size: 14px;
    color: #666;
  }
  
  .mode-toggle {
    display: flex;
    gap: 12px;
    margin-bottom: 24px;
    border-bottom: 2px solid #e0e0e0;
  }
  
  .mode-btn {
    background: none;
    border: none;
    padding: 12px 16px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    color: #999;
    border-bottom: 3px solid transparent;
    transition: all 0.2s;
  }
  
  .mode-btn.active {
    color: #CC0000;
    border-bottom-color: #CC0000;
  }
  
  .card-upload {
    margin-bottom: 24px;
    padding: 16px;
    background: #f9f9f9;
    border-radius: 8px;
  }
  
  .upload-area {
    position: relative;
  }
  
  .file-input {
    display: none;
  }
  
  .upload-label {
    display: block;
    padding: 20px;
    border: 2px dashed #ddd;
    border-radius: 8px;
    text-align: center;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .file-input:hover + .upload-label,
  .file-input:focus + .upload-label {
    border-color: #CC0000;
    background: #fff5f5;
  }
  
  .upload-label:active {
    transform: scale(0.98);
  }
  
  .preview {
    margin-top: 12px;
    max-width: 300px;
  }
  
  .preview img {
    width: 100%;
    border-radius: 6px;
    border: 1px solid #ddd;
  }
  
  .extract-btn {
    margin-top: 12px;
    width: 100%;
    padding: 12px;
    background: #CC0000;
    color: white;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .extract-btn:hover:not(:disabled) {
    background: #990000;
  }
  
  .extract-btn:disabled {
    opacity: 0.6;
  }
  
  .ocr-result {
    margin-top: 12px;
    padding: 12px;
    background: white;
    border-radius: 6px;
  }
  
  .ocr-result h4 {
    margin: 0 0 8px 0;
    font-size: 13px;
    color: #666;
  }
  
  .ocr-result pre {
    margin: 0;
    font-size: 12px;
    max-height: 200px;
    overflow-y: auto;
    background: #f9f9f9;
    padding: 8px;
    border-radius: 4px;
    white-space: pre-wrap;
  }
  
  .form-section {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  
  .form-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
    position: relative;
  }
  
  .form-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
  }
  
  label {
    font-size: 13px;
    font-weight: 600;
    color: #333;
  }
  
  input, select {
    padding: 10px 12px;
    border: 2px solid #ddd;
    border-radius: 6px;
    font-size: 13px;
    font-family: inherit;
  }
  
  input:focus, select:focus {
    outline: none;
    border-color: #CC0000;
  }
  
  .store-suggestions {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: white;
    border: 2px solid #cc0000;
    border-top: none;
    border-radius: 0 0 10px 10px;
    max-height: 320px;
    overflow-y: auto;
    z-index: 10;
    box-shadow: 0 8px 24px rgba(0,0,0,0.15);
  }
  
  .suggestion-item {
    display: block;
    width: 100%;
    padding: 12px 14px;
    background: white;
    border: none;
    border-bottom: 1px solid #f0f0f0;
    text-align: left;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.15s;
  }
  
  .suggestion-item:last-child {
    border-bottom: none;
  }
  
  .suggestion-item:hover {
    background: #fff5f5;
  }
  
  .suggestion-item strong {
    font-weight: 700;
    color: #cc0000;
  }
  
  .suggestion-item small {
    display: block;
    font-size: 11px;
    color: #888;
    margin-top: 3px;
  }
  
  .selected-store {
    padding: 10px 14px;
    background: #e8f5e9;
    border-radius: 8px;
    font-size: 14px;
    color: #2e7d32;
    font-weight: 600;
    margin-top: 4px;
  }
  
  .message {
    padding: 12px;
    border-radius: 6px;
    font-size: 13px;
    background: #e8f5e9;
    color: #2e7d32;
    border: 1px solid #81c784;
  }
  
  .message.loading {
    background: #e3f2fd;
    color: #1565c0;
    border-color: #64b5f6;
  }
  
  .submit-btn {
    padding: 12px 16px;
    background: #CC0000;
    color: white;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .submit-btn:hover:not(:disabled) {
    background: #990000;
  }
  
  .submit-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  
  @media (max-width: 480px) {
    .submit-container {
      padding: 16px;
    }
    
    .form-row {
      grid-template-columns: 1fr;
    }
  }
</style>
