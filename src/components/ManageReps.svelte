<script>
  import { onMount } from 'svelte';
  import { user } from '../lib/stores.js';

  let pending = [];
  let registry = {};
  let allReps = [];
  let loading = true;
  let actionMsg = '';
  const MANAGER_KEY = 'indoormedia2026';

  onMount(async () => {
    await loadAll();
  });

  async function loadAll() {
    loading = true;
    try {
      // Load pending
      const pendingRes = await fetch('/api/register-rep');
      const pendingData = await pendingRes.json();
      pending = pendingData.pending || [];

      // Load registry
      const regRes = await fetch(import.meta.env.BASE_URL + 'data/rep_registry.json');
      registry = await regRes.json();
      allReps = Object.entries(registry).map(([id, rep]) => ({
        id,
        name: rep.display_name || rep.contract_name,
        email: rep.email || '',
        role: rep.role || 'rep',
        location: rep.base_location || '',
        registeredAt: rep.registered_at || ''
      })).sort((a, b) => a.name.localeCompare(b.name));

    } catch (err) {
      console.error('Failed to load:', err);
    } finally {
      loading = false;
    }
  }

  async function approveRep(rep) {
    try {
      const res = await fetch('/api/approve-rep', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': MANAGER_KEY
        },
        body: JSON.stringify({ id: rep.id, action: 'approve' })
      });
      
      if (res.ok) {
        actionMsg = `✅ ${rep.name} approved!`;
        await loadAll();
        setTimeout(() => actionMsg = '', 3000);
      } else {
        const err = await res.json().catch(() => ({}));
        actionMsg = `❌ Failed: ${err.error || 'Unknown error'}`;
      }
    } catch (err) {
      actionMsg = `❌ Error: ${err.message}`;
    }
  }

  async function rejectRep(rep) {
    if (!confirm(`Reject ${rep.name}?`)) return;
    
    try {
      const res = await fetch('/api/approve-rep', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': MANAGER_KEY
        },
        body: JSON.stringify({ id: rep.id, action: 'reject' })
      });
      
      if (res.ok) {
        actionMsg = `🗑️ ${rep.name} rejected`;
        await loadAll();
        setTimeout(() => actionMsg = '', 3000);
      }
    } catch (err) {
      actionMsg = `❌ Error: ${err.message}`;
    }
  }
</script>

<div class="manage-container">
  <h2>👥 Manage Reps</h2>
  <p class="subtitle">Approve new registrations and manage your team</p>

  {#if actionMsg}
    <div class="action-msg">{actionMsg}</div>
  {/if}

  {#if loading}
    <p class="loading">Loading...</p>
  {:else}

    <!-- Pending Approvals -->
    <div class="section">
      <h3>
        🔔 Pending Approvals
        {#if pending.length > 0}
          <span class="badge">{pending.length}</span>
        {/if}
      </h3>

      {#if pending.length === 0}
        <p class="empty">No pending registrations</p>
      {:else}
        {#each pending as rep}
          <div class="pending-card">
            <div class="rep-info">
              <h4>{rep.name}</h4>
              {#if rep.email}<p class="detail">📧 {rep.email}</p>{/if}
              {#if rep.location}<p class="detail">📍 {rep.location}</p>{/if}
              <p class="detail timestamp">Requested: {new Date(rep.requestedAt).toLocaleDateString()}</p>
            </div>
            <div class="actions">
              <button class="approve-btn" on:click={() => approveRep(rep)}>✅ Approve</button>
              <button class="reject-btn" on:click={() => rejectRep(rep)}>✕</button>
            </div>
          </div>
        {/each}
      {/if}
    </div>

    <!-- Current Team -->
    <div class="section">
      <h3>📋 Current Team ({allReps.length})</h3>
      {#each allReps as rep}
        <div class="rep-card">
          <div class="rep-info">
            <h4>
              {rep.name}
              {#if rep.role === 'manager'}
                <span class="role-badge manager">Manager</span>
              {:else if rep.role === 'admin'}
                <span class="role-badge admin">Admin</span>
              {:else}
                <span class="role-badge">Rep</span>
              {/if}
            </h4>
            {#if rep.email}<p class="detail">📧 {rep.email}</p>{/if}
            {#if rep.location}<p class="detail">📍 {rep.location}</p>{/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .manage-container { padding: 20px; max-width: 600px; margin: 0 auto; }
  h2 { margin: 0 0 6px; font-size: 24px; font-weight: 700; color: var(--text-primary); }
  h3 { margin: 0 0 12px; font-size: 16px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 8px; }
  .subtitle { margin: 0 0 24px; color: var(--text-secondary); font-size: 14px; }

  .section { margin-bottom: 32px; }

  .badge {
    background: #CC0000;
    color: white;
    font-size: 12px;
    font-weight: 700;
    min-width: 22px;
    height: 22px;
    border-radius: 11px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0 6px;
  }

  .pending-card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #fff8e1;
    border: 2px solid #ffc107;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 10px;
  }

  .rep-card {
    background: var(--card-bg, white);
    border: 1px solid var(--border-color, #e0e0e0);
    border-radius: 10px;
    padding: 14px;
    margin-bottom: 8px;
  }

  .rep-info h4 { margin: 0 0 4px; font-size: 15px; color: var(--text-primary); display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .detail { margin: 2px 0; font-size: 13px; color: var(--text-secondary); }
  .timestamp { font-size: 11px; color: #999; }

  .role-badge {
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 10px;
    background: #e0e0e0;
    color: #666;
    font-weight: 600;
    text-transform: uppercase;
  }
  .role-badge.manager { background: #CC0000; color: white; }
  .role-badge.admin { background: #1565c0; color: white; }

  .actions { display: flex; gap: 8px; flex-shrink: 0; }

  .approve-btn {
    padding: 8px 16px;
    background: #2e7d32;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
  }
  .approve-btn:hover { background: #1b5e20; }

  .reject-btn {
    padding: 8px 12px;
    background: white;
    color: #c33;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    font-size: 16px;
    cursor: pointer;
    transition: all 0.2s;
  }
  .reject-btn:hover { background: #ffebee; border-color: #c33; }

  .action-msg {
    padding: 12px;
    background: #e8f5e9;
    border: 1px solid #a5d6a7;
    border-radius: 8px;
    color: #2e7d32;
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 16px;
    text-align: center;
  }

  .loading { text-align: center; color: #999; padding: 40px; }
  .empty { color: #999; font-size: 14px; padding: 20px; text-align: center; background: var(--bg-secondary, #f9f9f9); border-radius: 8px; }
</style>
