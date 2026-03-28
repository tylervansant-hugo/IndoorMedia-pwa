<script>
  import { onMount } from 'svelte';
  import HotLeadsSubmit from './HotLeadsSubmit.svelte';
  import PendingLeads from './PendingLeads.svelte';
  
  export let user;
  
  let hotLeads = [];
  let filteredLeads = [];
  let selectedStore = null;
  let selectedLead = null;
  let viewMode = 'grid'; // 'grid' or 'detail'
  let currentSection = 'approved'; // 'approved' or 'pending' or 'submit'
  let searchText = '';
  let allStores = [];
  let pendingCount = 0;
  
  // Email template variables
  let contactName = '';
  let emailToSend = '';
  
  onMount(async () => {
    try {
      const response = await fetch('/data/hot_leads.json');
      let allLeads = await response.json();
      
      // Check if user is manager (Tyler)
      const isManager = user?.name?.toLowerCase().includes('tyler') || user?.role === 'manager' || user?.role === 'admin';
      
      // If rep (not manager), filter to only their stores
      if (!isManager && user?.assigned_stores) {
        // User has list of assigned store IDs
        const assignedStoreIds = Array.isArray(user.assigned_stores) 
          ? user.assigned_stores 
          : [user.assigned_stores];
        hotLeads = allLeads.filter(l => assignedStoreIds.includes(l.store_id));
      } else if (!isManager) {
        // Rep with no assigned_stores visible → empty list with message
        hotLeads = [];
      } else {
        // Manager sees all
        hotLeads = allLeads;
      }
      
      // Get unique stores
      allStores = [...new Set(hotLeads.map(l => l.store_id))].sort();
      
      // Sort by store
      hotLeads.sort((a, b) => a.store_id.localeCompare(b.store_id));
      filterLeads();
    } catch (error) {
      console.error('Error loading hot leads:', error);
    }
  });
  
  function filterLeads() {
    let filtered = hotLeads;
    
    if (selectedStore) {
      filtered = filtered.filter(l => l.store_id === selectedStore);
    }
    
    if (searchText) {
      const search = searchText.toLowerCase();
      filtered = filtered.filter(l => 
        l.business_name.toLowerCase().includes(search) ||
        l.category.toLowerCase().includes(search) ||
        l.address.toLowerCase().includes(search)
      );
    }
    
    filteredLeads = filtered;
  }
  
  function selectLead(lead) {
    selectedLead = lead;
    viewMode = 'detail';
    contactName = '';
    emailToSend = '';
  }
  
  function backToGrid() {
    viewMode = 'grid';
    selectedLead = null;
  }
  
  function renderEmailTemplate(lead, contact = '[Contact Name]', rep = user?.name || 'Your Rep') {
    const template = lead._email_body_template || '';
    return template
      .replace(/\{business\}/g, lead.business_name)
      .replace(/\{contact\}/g, contact)
      .replace(/\{rep\}/g, rep);
  }
  
  function renderSubjectTemplate(lead) {
    const template = lead._email_subject_template || '';
    return template.replace(/\{business\}/g, lead.business_name);
  }
  
  function callBusiness(phone) {
    window.location.href = `tel:${phone}`;
  }
  
  function emailBusiness(email) {
    const subject = encodeURIComponent(renderSubjectTemplate(selectedLead));
    const body = encodeURIComponent(renderEmailTemplate(selectedLead, contactName, user?.name || 'Your Rep'));
    window.location.href = `mailto:${email}?subject=${subject}&body=${body}`;
  }
  
  function copyToClipboard(text, type = 'text') {
    navigator.clipboard.writeText(text);
    const msg = type === 'email' ? 'Email copied!' : 'Copied!';
    alert(msg);
  }
  
  $: if (hotLeads.length > 0) filterLeads();
</script>

<div class="hot-leads-container">
  <div class="header">
    <h2>🔥 Hot Leads</h2>
    <p class="subtitle">Max 5 per store • Phone + Email ready • {hotLeads.length} total
      {#if user?.name?.toLowerCase().includes('tyler') || user?.role === 'manager'}
        <span class="manager-badge">👤 MANAGER VIEW (all reps)</span>
      {/if}
    </p>
  </div>
  
  <div class="section-tabs">
    <button 
      class="section-tab"
      class:active={currentSection === 'approved'}
      on:click={() => { currentSection = 'approved'; viewMode = 'grid'; }}
    >
      ✅ Approved ({hotLeads.length})
    </button>
    <button 
      class="section-tab"
      class:active={currentSection === 'pending'}
      on:click={() => { currentSection = 'pending'; }}
    >
      ⏳ Pending {#if pendingCount > 0}({pendingCount}){/if}
    </button>
    <button 
      class="section-tab"
      class:active={currentSection === 'submit'}
      on:click={() => { currentSection = 'submit'; }}
    >
      ➕ Add Lead
    </button>
  </div>
  
  {#if currentSection === 'approved' && viewMode === 'grid'}
    <div class="controls">
      <div class="filter-group">
        <select bind:value={selectedStore} on:change={filterLeads}>
          <option value="">All Stores</option>
          {#each allStores as store}
            <option value={store}>{store}</option>
          {/each}
        </select>
        
        <input
          type="text"
          placeholder="Search business name..."
          bind:value={searchText}
          on:input={filterLeads}
          class="search-input"
        />
      </div>
      
      <div class="view-toggle">
        <span class="count">{filteredLeads.length} leads</span>
      </div>
    </div>
    
    {#if hotLeads.length === 0 && !selectedStore && !searchText}
      <div class="no-results">
        <p>No Hot Leads assigned to you yet. Check back soon!</p>
      </div>
    {:else if filteredLeads.length === 0}
      <div class="no-results">
        <p>No leads found. Try adjusting your filters.</p>
      </div>
    {:else}
      <div class="leads-grid">
        {#each filteredLeads as lead}
          <div class="lead-card" on:click={() => selectLead(lead)}>
            <div class="lead-header">
              <h3>{lead.business_name}</h3>
              <span class="rating">⭐{lead.rating}</span>
            </div>
            
            <div class="lead-meta">
              <span class="category">{lead.category}</span>
              <span class="distance">{lead.distance_mi} mi</span>
            </div>
            
            <div class="store-info">
              <small>{lead.store_chain} {lead.store_city} • {lead.store_tier}</small>
            </div>
            
            <div class="hook">
              <p>"{lead._hook}"</p>
            </div>
            
            <div class="contact-info">
              <a href="tel:{lead.phone}" class="phone" on:click|stopPropagation={() => callBusiness(lead.phone)}>
                📞 {lead.phone}
              </a>
              <a href="mailto:{lead._email}" class="email" on:click|stopPropagation={() => emailBusiness(lead._email)}>
                📧 {lead._email}
              </a>
            </div>
            
            <div class="footer">
              <small class="reviews">{lead.reviews} reviews</small>
              <small class="template">📧 {lead._email_template_type.toUpperCase()}</small>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  {:else if currentSection === 'approved' && viewMode === 'detail' && selectedLead}
    <div class="detail-view">
      <button class="back-btn" on:click={backToGrid}>← Back to Leads</button>
      
      <div class="detail-header">
        <h2>{selectedLead.business_name}</h2>
        <div class="detail-meta">
          <span class="category">{selectedLead.category}</span>
          <span class="rating">⭐{selectedLead.rating} ({selectedLead.reviews} reviews)</span>
        </div>
      </div>
      
      <div class="store-highlight">
        <h4>{selectedLead.store_chain} {selectedLead.store_city}</h4>
        <p>{selectedLead.store_tier} store • {selectedLead.store_cases} cases • {selectedLead.distance_mi} mi away</p>
      </div>
      
      <div class="hook-section">
        <h4>Your Hook</h4>
        <div class="hook-text">
          <p>"{selectedLead._hook}"</p>
          <button class="copy-btn" on:click={() => copyToClipboard(selectedLead._hook)}>📋 Copy</button>
        </div>
      </div>
      
      <div class="contact-section">
        <h4>Contact</h4>
        <div class="address">
          <p>📍 {selectedLead.address}</p>
        </div>
        
        <div class="action-buttons">
          <button class="btn call" on:click={() => callBusiness(selectedLead.phone)}>
            📞 Call: {selectedLead.phone}
          </button>
          <button class="btn email" on:click={() => emailBusiness(selectedLead._email)}>
            📧 Email: {selectedLead._email}
          </button>
        </div>
      </div>
      
      <div class="email-section">
        <h4>Email Template</h4>
        
        <div class="personalize">
          <input
            type="text"
            placeholder="Contact's first name (optional)"
            bind:value={contactName}
          />
        </div>
        
        <div class="email-preview">
          <div class="subject-line">
            <strong>Subject:</strong> {renderSubjectTemplate(selectedLead)}
            <button class="copy-btn" on:click={() => copyToClipboard(renderSubjectTemplate(selectedLead))}>📋</button>
          </div>
          
          <div class="body-text">
            {renderEmailTemplate(selectedLead, contactName || '[Contact Name]', user?.name || 'Your Rep')}
            <button class="copy-btn full-width" on:click={() => copyToClipboard(renderEmailTemplate(selectedLead, contactName || '[Contact Name]', user?.name || 'Your Rep'), 'email')}>📋 Copy Full Email</button>
          </div>
        </div>
      </div>
    </div>
  {:else if currentSection === 'pending'}
    <PendingLeads
      onLeadApproved={() => {
        // Reload hot leads to get newly approved ones
        location.reload();
      }}
    />
  {:else if currentSection === 'submit'}
    <HotLeadsSubmit
      {user}
      onLeadSubmitted={() => {
        currentSection = 'pending';
      }}
    />
  {/if}
</div>

<style>
  .hot-leads-container {
    padding: 16px;
    max-width: 1200px;
    margin: 0 auto;
  }
  
  .section-tabs {
    display: flex;
    gap: 12px;
    margin-bottom: 24px;
    border-bottom: 2px solid #e0e0e0;
  }
  
  .section-tab {
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
  
  .section-tab.active {
    color: #CC0000;
    border-bottom-color: #CC0000;
  }
  
  .section-tab:hover {
    color: #333;
  }
  
  .header {
    margin-bottom: 24px;
  }
  
  .header h2 {
    margin: 0;
    font-size: 28px;
    color: #333;
  }
  
  .subtitle {
    margin: 4px 0 0 0;
    color: #666;
    font-size: 14px;
  }
  
  .manager-badge {
    display: inline-block;
    margin-left: 12px;
    padding: 4px 8px;
    background: #fff5f5;
    color: #CC0000;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
    border: 1px solid #ffe0e0;
  }
  
  .controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    margin-bottom: 20px;
    flex-wrap: wrap;
  }
  
  .filter-group {
    display: flex;
    gap: 12px;
    flex: 1;
    min-width: 300px;
  }
  
  select, .search-input {
    padding: 10px 14px;
    border: 2px solid #ddd;
    border-radius: 8px;
    font-size: 14px;
    font-family: inherit;
  }
  
  select {
    min-width: 150px;
  }
  
  .search-input {
    flex: 1;
    min-width: 200px;
  }
  
  select:focus, .search-input:focus {
    outline: none;
    border-color: #CC0000;
  }
  
  .view-toggle {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  
  .count {
    font-size: 14px;
    color: #666;
    font-weight: 600;
  }
  
  .no-results {
    text-align: center;
    padding: 60px 20px;
    color: #999;
  }
  
  /* Grid View */
  .leads-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 16px;
  }
  
  .lead-card {
    background: white;
    border: 2px solid #e0e0e0;
    border-radius: 12px;
    padding: 16px;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  
  .lead-card:hover {
    border-color: #CC0000;
    box-shadow: 0 4px 16px rgba(204, 0, 0, 0.15);
    transform: translateY(-2px);
  }
  
  .lead-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 8px;
  }
  
  .lead-header h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 700;
    color: #333;
    flex: 1;
  }
  
  .rating {
    font-size: 14px;
    font-weight: 600;
    white-space: nowrap;
  }
  
  .lead-meta {
    display: flex;
    gap: 12px;
    font-size: 12px;
  }
  
  .category {
    background: #f0f0f0;
    padding: 4px 8px;
    border-radius: 4px;
    color: #666;
  }
  
  .distance {
    color: #999;
  }
  
  .store-info {
    padding: 8px 12px;
    background: #f9f9f9;
    border-left: 4px solid #CC0000;
    border-radius: 4px;
  }
  
  .store-info small {
    color: #666;
    font-size: 13px;
  }
  
  .hook {
    padding: 10px;
    background: #fff5f5;
    border-radius: 6px;
    border: 1px solid #ffe0e0;
  }
  
  .hook p {
    margin: 0;
    font-size: 13px;
    color: #333;
    font-style: italic;
    line-height: 1.5;
  }
  
  .contact-info {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  
  .phone, .email {
    padding: 8px;
    background: #f0f0f0;
    border-radius: 6px;
    text-decoration: none;
    color: #333;
    font-size: 13px;
    border: 1px solid #ddd;
    transition: all 0.2s;
  }
  
  .phone:hover, .email:hover {
    background: #CC0000;
    color: white;
    border-color: #CC0000;
  }
  
  .footer {
    display: flex;
    justify-content: space-between;
    padding-top: 8px;
    border-top: 1px solid #e0e0e0;
    font-size: 12px;
    color: #999;
  }
  
  /* Detail View */
  .detail-view {
    background: white;
    border-radius: 12px;
    padding: 24px;
    max-width: 700px;
  }
  
  .back-btn {
    background: none;
    border: none;
    color: #CC0000;
    font-weight: 600;
    cursor: pointer;
    padding: 0;
    margin-bottom: 20px;
    font-size: 14px;
  }
  
  .detail-header {
    margin-bottom: 24px;
  }
  
  .detail-header h2 {
    margin: 0 0 8px 0;
    font-size: 28px;
    color: #333;
  }
  
  .detail-meta {
    display: flex;
    gap: 16px;
    font-size: 14px;
    color: #666;
  }
  
  .store-highlight {
    background: #f9f9f9;
    padding: 16px;
    border-radius: 8px;
    border-left: 4px solid #CC0000;
    margin-bottom: 20px;
  }
  
  .store-highlight h4 {
    margin: 0 0 4px 0;
    font-size: 16px;
    color: #333;
  }
  
  .store-highlight p {
    margin: 0;
    font-size: 13px;
    color: #666;
  }
  
  .hook-section, .contact-section, .email-section {
    margin-bottom: 24px;
  }
  
  .hook-section h4, .contact-section h4, .email-section h4 {
    margin: 0 0 12px 0;
    font-size: 16px;
    color: #333;
  }
  
  .hook-text {
    background: #fff5f5;
    padding: 14px;
    border-radius: 8px;
    border: 1px solid #ffe0e0;
    position: relative;
  }
  
  .hook-text p {
    margin: 0;
    font-size: 14px;
    color: #333;
    line-height: 1.6;
    font-style: italic;
  }
  
  .address {
    background: #f9f9f9;
    padding: 12px;
    border-radius: 6px;
    margin-bottom: 12px;
  }
  
  .address p {
    margin: 0;
    font-size: 13px;
    color: #666;
  }
  
  .action-buttons {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  
  .btn {
    padding: 12px 16px;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 14px;
  }
  
  .btn.call {
    background: #CC0000;
    color: white;
  }
  
  .btn.call:hover {
    background: #990000;
  }
  
  .btn.email {
    background: #007bff;
    color: white;
  }
  
  .btn.email:hover {
    background: #0056b3;
  }
  
  .personalize {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
  }
  
  .personalize input {
    flex: 1;
    padding: 10px 12px;
    border: 2px solid #ddd;
    border-radius: 6px;
    font-size: 13px;
  }
  
  .personalize input:focus {
    outline: none;
    border-color: #CC0000;
  }
  
  .email-preview {
    background: #f9f9f9;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #e0e0e0;
  }
  
  .subject-line {
    padding: 12px 14px;
    background: #f0f0f0;
    border-bottom: 1px solid #ddd;
    font-size: 13px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    word-break: break-word;
  }
  
  .body-text {
    padding: 16px;
    font-size: 13px;
    line-height: 1.6;
    white-space: pre-wrap;
    color: #333;
  }
  
  .copy-btn {
    background: white;
    border: 1px solid #ddd;
    padding: 4px 8px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    transition: all 0.2s;
  }
  
  .copy-btn:hover {
    background: #CC0000;
    color: white;
    border-color: #CC0000;
  }
  
  .copy-btn.full-width {
    display: block;
    width: 100%;
    margin-top: 12px;
    padding: 10px;
  }
  
  @media (max-width: 768px) {
    .leads-grid {
      grid-template-columns: 1fr;
    }
    
    .controls {
      flex-direction: column;
    }
    
    .filter-group {
      flex-direction: column;
      min-width: unset;
    }
    
    .detail-view {
      padding: 16px;
    }
    
    .detail-meta {
      flex-direction: column;
      gap: 8px;
    }
  }
</style>
