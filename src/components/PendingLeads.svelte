<script>
  import { onMount } from 'svelte';
  
  export let onLeadApproved = () => {};
  
  let pendingLeads = [];
  let selectedLead = null;
  let viewMode = 'list'; // 'list' or 'detail'
  let loading = true;
  
  onMount(async () => {
    loadPendingLeads();
  });
  
  async function loadPendingLeads() {
    try {
      const response = await fetch(import.meta.env.BASE_URL + 'data/pending_leads.json?t=' + Date.now());
      if (response.ok) {
        pendingLeads = await response.json();
      } else {
        pendingLeads = [];
      }
      loading = false;
    } catch (err) {
      console.error('Error loading pending leads:', err);
      pendingLeads = [];
      loading = false;
    }
  }
  
  function selectLead(lead) {
    selectedLead = lead;
    viewMode = 'detail';
  }
  
  function backToList() {
    viewMode = 'list';
    selectedLead = null;
  }
  
  async function approveLead(lead) {
    if (!confirm(`Approve "${lead.business_name}"?`)) return;
    
    try {
      const response = await fetch('/api/approve-lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...lead,
          status: 'approved'
        })
      });
      
      if (response.ok) {
        // Remove from pending
        pendingLeads = pendingLeads.filter(l => l.business_name !== lead.business_name);
        viewMode = 'list';
        selectedLead = null;
        onLeadApproved();
      } else {
        alert('Error approving lead');
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  }
  
  async function rejectLead(lead) {
    if (!confirm(`Reject "${lead.business_name}"? (Can be resubmitted)`)) return;
    
    try {
      const response = await fetch('/api/reject-lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          business_name: lead.business_name,
          reason: 'Manual rejection'
        })
      });
      
      if (response.ok) {
        pendingLeads = pendingLeads.filter(l => l.business_name !== lead.business_name);
        viewMode = 'list';
        selectedLead = null;
      } else {
        alert('Error rejecting lead');
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  }
</script>

<div class="pending-container">
  <div class="pending-header">
    <h2>⏳ Pending Leads Review</h2>
    <p class="count">
      {#if pendingLeads.length === 0}
        No pending leads
      {:else}
        {pendingLeads.length} waiting for approval
      {/if}
    </p>
  </div>
  
  {#if loading}
    <div class="loading">Loading...</div>
  {:else if viewMode === 'list'}
    {#if pendingLeads.length === 0}
      <div class="empty-state">
        <p>✓ All caught up! No pending leads.</p>
      </div>
    {:else}
      <div class="pending-list">
        {#each pendingLeads as lead}
          <div class="pending-item">
            <div class="item-header">
              <h4>{lead.business_name}</h4>
              <span class="category">{lead.category}</span>
            </div>
            
            <div class="item-meta">
              <p class="submitted">Submitted by {lead.submitted_by}</p>
              <p class="date">{new Date(lead.submitted_at).toLocaleDateString()}</p>
            </div>
            
            <div class="item-contact">
              <a href="tel:{lead.phone}" class="phone">📞 {lead.phone}</a>
              <a href="mailto:{lead.email}" class="email">📧 {lead.email}</a>
            </div>
            
            {#if lead.store_id}
              <div class="store-ref">
                <small>Store: {lead.store_chain} {lead.store_city} ({lead.store_id})</small>
              </div>
            {/if}
            
            <div class="item-actions">
              <button class="btn-details" on:click={() => selectLead(lead)}>
                View Details
              </button>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  {:else if viewMode === 'detail' && selectedLead}
    <div class="detail-view">
      <button class="back-btn" on:click={backToList}>← Back</button>
      
      <div class="detail-header">
        <h3>{selectedLead.business_name}</h3>
        <span class="category">{selectedLead.category}</span>
      </div>
      
      <div class="detail-section">
        <h4>Contact Information</h4>
        <div class="info-row">
          <span class="label">Phone:</span>
          <a href="tel:{selectedLead.phone}">{selectedLead.phone}</a>
        </div>
        <div class="info-row">
          <span class="label">Email:</span>
          <a href="mailto:{selectedLead.email}">{selectedLead.email}</a>
        </div>
        {#if selectedLead.address}
          <div class="info-row">
            <span class="label">Address:</span>
            <span>{selectedLead.address}</span>
          </div>
        {/if}
      </div>
      
      <div class="detail-section">
        <h4>Submission Info</h4>
        <div class="info-row">
          <span class="label">Submitted by:</span>
          <span>{selectedLead.submitted_by}</span>
        </div>
        <div class="info-row">
          <span class="label">Date:</span>
          <span>{new Date(selectedLead.submitted_at).toLocaleString()}</span>
        </div>
      </div>
      
      {#if selectedLead.store_id}
        <div class="detail-section">
          <h4>Store Reference</h4>
          <div class="store-info">
            <p>{selectedLead.store_chain} {selectedLead.store_city}</p>
            <p class="store-id">{selectedLead.store_id}</p>
          </div>
        </div>
      {/if}
      
      {#if selectedLead.rating || selectedLead.reviews}
        <div class="detail-section">
          <h4>Business Details</h4>
          <div class="info-row">
            <span class="label">Rating:</span>
            <span>⭐ {selectedLead.rating || 'N/A'}</span>
          </div>
          <div class="info-row">
            <span class="label">Reviews:</span>
            <span>{selectedLead.reviews || 0}</span>
          </div>
        </div>
      {/if}
      
      <div class="action-buttons">
        <button class="btn-approve" on:click={() => approveLead(selectedLead)}>
          ✅ Approve & Add to Hot Leads
        </button>
        <button class="btn-reject" on:click={() => rejectLead(selectedLead)}>
          ❌ Reject
        </button>
      </div>
    </div>
  {/if}
</div>

<style>
  .pending-container {
    padding: 16px;
  }
  
  .pending-header {
    margin-bottom: 24px;
  }
  
  .pending-header h2 {
    margin: 0 0 4px 0;
    font-size: 24px;
    color: #333;
  }
  
  .count {
    margin: 0;
    font-size: 14px;
    color: #666;
  }
  
  .loading, .empty-state {
    text-align: center;
    padding: 40px 20px;
    color: #999;
  }
  
  .pending-list {
    display: grid;
    gap: 12px;
  }
  
  .pending-item {
    background: white;
    border: 2px solid #e0e0e0;
    border-radius: 10px;
    padding: 16px;
    transition: all 0.2s;
  }
  
  .pending-item:hover {
    border-color: #CC0000;
    box-shadow: 0 2px 8px rgba(204, 0, 0, 0.1);
  }
  
  .item-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 8px;
  }
  
  .item-header h4 {
    margin: 0;
    font-size: 16px;
    color: #333;
    flex: 1;
  }
  
  .category {
    background: #f0f0f0;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    color: #666;
    white-space: nowrap;
  }
  
  .item-meta {
    display: flex;
    gap: 12px;
    margin-bottom: 8px;
    font-size: 12px;
    color: #999;
  }
  
  .item-meta p {
    margin: 0;
  }
  
  .item-contact {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 8px;
    font-size: 13px;
  }
  
  .phone, .email {
    text-decoration: none;
    color: #CC0000;
    font-weight: 500;
  }
  
  .phone:hover, .email:hover {
    text-decoration: underline;
  }
  
  .store-ref {
    padding: 8px;
    background: #f9f9f9;
    border-left: 3px solid #CC0000;
    border-radius: 4px;
    margin-bottom: 8px;
  }
  
  .store-ref small {
    color: #666;
  }
  
  .item-actions {
    display: flex;
    gap: 8px;
  }
  
  .btn-details {
    flex: 1;
    padding: 8px 12px;
    background: #f0f0f0;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    color: #333;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .btn-details:hover {
    background: #e0e0e0;
  }
  
  /* Detail View */
  .detail-view {
    background: white;
    border-radius: 12px;
    padding: 24px;
    max-width: 600px;
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
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-bottom: 24px;
  }
  
  .detail-header h3 {
    margin: 0;
    font-size: 24px;
    color: #333;
    flex: 1;
  }
  
  .detail-section {
    margin-bottom: 20px;
  }
  
  .detail-section h4 {
    margin: 0 0 12px 0;
    font-size: 14px;
    font-weight: 700;
    color: #333;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  
  .info-row {
    display: flex;
    padding: 8px 0;
    border-bottom: 1px solid #f0f0f0;
    font-size: 13px;
  }
  
  .label {
    font-weight: 600;
    color: #666;
    min-width: 120px;
  }
  
  .info-row a {
    color: #CC0000;
    text-decoration: none;
  }
  
  .info-row a:hover {
    text-decoration: underline;
  }
  
  .store-info {
    background: #f9f9f9;
    padding: 12px;
    border-radius: 6px;
  }
  
  .store-info p {
    margin: 0 0 4px 0;
    font-size: 13px;
    color: #333;
    font-weight: 600;
  }
  
  .store-id {
    font-size: 12px !important;
    color: #999 !important;
    font-weight: normal !important;
  }
  
  .action-buttons {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: 24px;
  }
  
  .btn-approve, .btn-reject {
    padding: 12px 16px;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .btn-approve {
    background: #4caf50;
    color: white;
  }
  
  .btn-approve:hover {
    background: #45a049;
  }
  
  .btn-reject {
    background: #f44336;
    color: white;
  }
  
  .btn-reject:hover {
    background: #da190b;
  }
  
  @media (max-width: 600px) {
    .detail-view {
      padding: 16px;
    }
    
    .item-header {
      flex-direction: column;
    }
  }
</style>
