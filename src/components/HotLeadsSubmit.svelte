<script>
  import { onMount } from 'svelte';
  
  export let user;
  export let onLeadSubmitted = () => {};
  
  let submitMode = 'manual'; // 'manual' or 'card'
  let formData = {
    business_name: '',
    category: 'Restaurant',
    phone: '',
    email: '',
    address: '',
    store_id: '',
    store_chain: '',
    store_city: '',
    distance_mi: '',
    rating: 4.5,
    reviews: 0
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
    'Restaurant',
    'Auto Repair',
    'Salon/Barber',
    'Dental',
    'Gym/Fitness',
    'Veterinary',
    'Chiropractor',
    'Other'
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
    // Load stores for reference
    try {
      const response = await fetch(import.meta.env.BASE_URL + 'data/hot_leads.json');
      const leads = await response.json();
      allStores = [...new Set(leads.map(l => ({
        id: l.store_id,
        chain: l.store_chain,
        city: l.store_city,
        tier: l.store_tier
      })))];
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
      
      // Try to extract phone, email, name
      const phoneMatch = text.match(/\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})/);
      const emailMatch = text.match(/[\w\.-]+@[\w\.-]+\.\w+/);
      
      extractedData = {
        phone: phoneMatch ? `(${phoneMatch[1]}) ${phoneMatch[2]}-${phoneMatch[3]}` : '',
        email: emailMatch ? emailMatch[0] : '',
        business_name: '', // User needs to fill this
        raw_text: text
      };
      
      if (extractedData.phone) formData.phone = extractedData.phone;
      if (extractedData.email) formData.email = extractedData.email;
      
      submitMessage = '✓ Card read! Review and fill in any missing info.';
      ocrLoading = false;
    } catch (err) {
      console.error('OCR error:', err);
      submitMessage = `Error reading card: ${err.message || 'Unknown error'}. Please fill in manually.`;
      ocrLoading = false;
    }
  }
  
  function filterStores(text) {
    storeSearchText = text;
    if (!text) {
      filteredStores = [];
      return;
    }
    const search = text.toLowerCase();
    filteredStores = allStores.filter(s => 
      s.id.toLowerCase().includes(search) ||
      s.chain.toLowerCase().includes(search) ||
      s.city.toLowerCase().includes(search)
    ).slice(0, 5);
  }
  
  function selectStore(store) {
    formData.store_id = store.id;
    formData.store_chain = store.chain;
    formData.store_city = store.city;
    storeSearchText = `${store.chain} ${store.city}`;
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
        status: 'pending_review',
        _hook: `Submitted by ${user?.name || 'rep'}`
      };
      
      // Save to submitted_leads.json
      const response = await fetch('/api/submit-lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newLead)
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      submitMessage = '✅ Lead submitted! Waiting for Tyler\'s review.';
      
      // Reset form
      setTimeout(() => {
        formData = {
          business_name: '',
          category: 'Restaurant',
          phone: '',
          email: '',
          address: '',
          store_id: '',
          store_chain: '',
          store_city: '',
          distance_mi: '',
          rating: 4.5,
          reviews: 0
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
    <p>Found a business? Add it here. Tyler will review and approve.</p>
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
    
    <div class="form-row">
      <div class="form-group">
        <label>Category</label>
        <select bind:value={formData.category}>
          {#each categories as cat}
            <option>{cat}</option>
          {/each}
        </select>
      </div>
      
      <div class="form-group">
        <label>Rating (optional)</label>
        <input
          type="number"
          min="0"
          max="5"
          step="0.1"
          bind:value={formData.rating}
          placeholder="4.5"
        />
      </div>
      
      <div class="form-group">
        <label>Reviews (optional)</label>
        <input
          type="number"
          min="0"
          bind:value={formData.reviews}
          placeholder="0"
        />
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
              <strong>{store.chain}</strong> {store.city}
              <small>{store.id}</small>
            </button>
          {/each}
        </div>
      {/if}
      {#if formData.store_id}
        <div class="selected-store">
          ✓ {formData.store_chain} {formData.store_city}
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
    max-width: 600px;
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
    border: 1px solid #ddd;
    border-top: none;
    border-radius: 0 0 6px 6px;
    max-height: 200px;
    overflow-y: auto;
    z-index: 10;
  }
  
  .suggestion-item {
    display: block;
    width: 100%;
    padding: 10px 12px;
    background: white;
    border: none;
    text-align: left;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .suggestion-item:hover {
    background: #f9f9f9;
  }
  
  .suggestion-item strong {
    font-weight: 600;
    color: #333;
  }
  
  .suggestion-item small {
    display: block;
    font-size: 11px;
    color: #999;
    margin-top: 2px;
  }
  
  .selected-store {
    padding: 8px 12px;
    background: #f0f0f0;
    border-radius: 6px;
    font-size: 13px;
    color: #333;
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
