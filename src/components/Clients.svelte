<script>
  import { onMount } from 'svelte';
  import { user } from '../lib/stores.js';

  let view = 'main'; // main, customers, sales
  let contracts = [];
  let calendarEvents = [];
  let loading = true;
  let searchQuery = '';

  onMount(async () => {
    try {
      const [contractsRes, calendarRes] = await Promise.all([
        fetch('/data/contracts.json'),
        fetch('/data/calendar.json')
      ]);
      const contractsData = await contractsRes.json();
      contracts = contractsData.contracts || [];
      calendarEvents = await calendarRes.json().catch(() => []);
    } catch (err) {
      console.error('Failed to load data:', err);
    }
    loading = false;
  });

  function formatEventTime(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    const isToday = d.toDateString() === today.toDateString();
    const isTomorrow = d.toDateString() === tomorrow.toDateString();
    
    const time = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    
    if (isToday) return `Today ${time}`;
    if (isTomorrow) return `Tomorrow ${time}`;
    return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }) + ' ' + time;
  }

  $: repName = $user?.name || $user?.first_name || '';
  $: isManager = repName?.toLowerCase().includes('tyler');

  // My Customers = closed deals for this rep (or all for manager)
  $: myCustomers = isManager
    ? contracts
    : contracts.filter(c => {
        const rep = (c.sales_rep || '').toLowerCase();
        return rep.includes((repName || '').toLowerCase().split(' ')[0]);
      });

  // My Sales = same data but focused on amounts
  $: mySales = myCustomers;

  $: totalRevenue = mySales.reduce((sum, c) => sum + (c.total_amount || 0), 0);

  $: filteredCustomers = searchQuery
    ? myCustomers.filter(c =>
        (c.business_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (c.contact_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (c.store_name || '').toLowerCase().includes(searchQuery.toLowerCase())
      )
    : myCustomers;

  function goBack() {
    view = 'main';
    searchQuery = '';
  }
</script>

<div class="clients-container">
  {#if view === 'main'}
    <h2>Clients</h2>
    <p class="subtitle">Manage customers & sales</p>

    <div class="menu-grid">
      <button class="menu-btn" on:click={() => view = 'customers'}>
        <div class="menu-emoji">👥</div>
        <h4>My Customers</h4>
        <p>{myCustomers.length} closed deals</p>
      </button>

      <button class="menu-btn" on:click={() => view = 'sales'}>
        <div class="menu-emoji">💳</div>
        <h4>My Sales</h4>
        <p>${totalRevenue.toLocaleString()} total</p>
      </button>
    </div>

    <!-- Upcoming Calendar Events -->
    {#if calendarEvents.length > 0}
      <div class="calendar-section">
        <h3>📅 Upcoming Events</h3>
        <div class="event-list">
          {#each calendarEvents as event}
            <div class="event-card">
              <div class="event-time">{formatEventTime(event.start)}</div>
              <div class="event-details">
                <h4>{event.title}</h4>
                {#if event.location}
                  <p class="event-location">📍 {event.location}</p>
                {/if}
                {#if event.attendees && event.attendees.length > 0}
                  <p class="event-attendees">👥 {event.attendees.join(', ')}</p>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/if}
  {/if}

  <!-- My Customers -->
  {#if view === 'customers'}
    <button class="back-btn" on:click={goBack}>&larr; Back</button>
    <h2>My Customers</h2>
    <p class="subtitle">{myCustomers.length} closed deals</p>

    <div class="search-box">
      <input type="text" placeholder="Search customers..." bind:value={searchQuery} />
    </div>

    {#if loading}
      <p>Loading...</p>
    {:else if filteredCustomers.length === 0}
      <p class="empty">No customers found. Sales sync from Gmail contracts nightly.</p>
    {:else}
      <div class="customer-list">
        {#each filteredCustomers as c}
          <div class="customer-card">
            <div class="card-header">
              <h4>{c.business_name || 'Unknown'}</h4>
              <span class="amount">${(c.total_amount || 0).toLocaleString()}</span>
            </div>
            <p class="contact">{c.contact_name || ''}</p>
            {#if c.contact_phone}
              <p class="phone">📞 {c.contact_phone}</p>
            {/if}
            {#if c.contact_email}
              <p class="email">📧 {c.contact_email}</p>
            {/if}
            <div class="card-meta">
              <span>🏪 {c.store_name || ''} #{c.store_number || ''}</span>
              <span>📋 {c.product_description || ''}</span>
              <span>📅 {c.date ? c.date.split(' ')[0] : ''}</span>
            </div>
            {#if c.address}
              <p class="address">📍 {c.address}</p>
            {/if}
            {#if isManager && c.sales_rep}
              <p class="rep-tag">Rep: {c.sales_rep}</p>
            {/if}
            <div class="card-actions">
              {#if c.contact_phone}
                <a href="tel:{c.contact_phone}" class="action-btn call">📞 Call</a>
              {/if}
              {#if c.contact_email}
                <a href="mailto:{c.contact_email}" class="action-btn">📧 Email</a>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    {/if}
  {/if}

  <!-- My Sales -->
  {#if view === 'sales'}
    <button class="back-btn" on:click={goBack}>&larr; Back</button>
    <h2>My Sales</h2>
    <p class="subtitle">{mySales.length} deals &bull; ${totalRevenue.toLocaleString()} total</p>

    {#if loading}
      <p>Loading...</p>
    {:else if mySales.length === 0}
      <p class="empty">No sales found. Sales data syncs from Gmail contracts nightly at 8 PM.</p>
    {:else}
      <div class="sales-summary">
        <div class="stat">
          <span class="stat-value">{mySales.length}</span>
          <span class="stat-label">Deals</span>
        </div>
        <div class="stat">
          <span class="stat-value">${totalRevenue.toLocaleString()}</span>
          <span class="stat-label">Revenue</span>
        </div>
        <div class="stat">
          <span class="stat-value">${mySales.length ? Math.round(totalRevenue / mySales.length).toLocaleString() : 0}</span>
          <span class="stat-label">Avg Deal</span>
        </div>
      </div>

      <div class="sales-list">
        {#each mySales.sort((a, b) => (b.date || '').localeCompare(a.date || '')) as sale}
          <div class="sale-row">
            <div class="sale-info">
              <span class="sale-name">{sale.business_name || 'Unknown'}</span>
              <span class="sale-meta">{sale.store_name || ''} &bull; {sale.product_description || ''} &bull; {sale.date ? sale.date.split(' ')[0] : ''}</span>
            </div>
            <span class="sale-amount">${(sale.total_amount || 0).toLocaleString()}</span>
          </div>
        {/each}
      </div>
    {/if}
  {/if}
</div>

<style>
  .clients-container { padding: 20px; max-width: 600px; margin: 0 auto; }
  h2 { margin: 0 0 6px; font-size: 24px; color: var(--text-primary); font-weight: 700; }
  .subtitle { margin: 0 0 16px; color: var(--text-secondary); font-size: 14px; }
  .back-btn { background: none; border: none; color: #CC0000; font-size: 14px; font-weight: 600; cursor: pointer; padding: 10px 0; margin-bottom: 16px; }

  .menu-grid { display: flex; flex-direction: column; gap: 12px; margin-top: 16px; }
  .menu-btn { background: white; border: 1px solid #e0e0e0; border-radius: 12px; padding: 16px; text-align: left; cursor: pointer; transition: all 0.2s; }
  .menu-btn:hover { border-color: #CC0000; background: #fff5f5; box-shadow: 0 2px 8px rgba(204, 0, 0, 0.1); }
  .menu-emoji { font-size: 28px; margin-bottom: 8px; }
  .menu-btn h4 { margin: 0 0 4px; color: #333; font-size: 16px; font-weight: 700; }
  .menu-btn p { margin: 0; color: #666; font-size: 13px; }

  .search-box { margin: 15px 0; }
  .search-box input { width: 100%; padding: 12px 16px; border: 1px solid #e0e0e0; border-radius: 8px; font-size: 14px; box-sizing: border-box; height: 44px; }

  .customer-list { display: flex; flex-direction: column; gap: 12px; }
  .customer-card { background: white; border: 1px solid #e0e0e0; border-radius: 12px; padding: 16px; }
  .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
  .card-header h4 { margin: 0; font-size: 16px; color: #333; font-weight: 700; flex: 1; }
  .amount { font-weight: 700; color: #CC0000; font-size: 16px; white-space: nowrap; margin-left: 8px; }
  .contact { margin: 0 0 4px; font-size: 13px; color: #555; font-weight: 600; }
  .phone, .email { margin: 2px 0; font-size: 13px; color: #555; }
  .card-meta { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0; font-size: 11px; color: #888; }
  .address { margin: 4px 0; font-size: 12px; color: #888; }
  .rep-tag { margin: 4px 0 0; font-size: 11px; color: #CC0000; font-weight: 600; }
  .card-actions { display: flex; gap: 8px; margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee; }
  .action-btn { flex: 1; padding: 8px; border: 1px solid #ddd; border-radius: 8px; text-align: center; text-decoration: none; font-size: 13px; font-weight: 600; color: #333; background: #f9f9f9; }
  .action-btn.call { background: #2e7d32; color: white; border-color: #2e7d32; }

  .empty { color: #999; font-style: italic; text-align: center; margin: 40px 0; }

  .info-card { background: #f9f9f9; border-radius: 12px; padding: 16px; margin-top: 15px; }
  .info-card p { margin: 0 0 10px; color: #555; font-size: 13px; }
  .info-card ul { margin: 0; padding-left: 20px; font-size: 13px; color: #555; }
  .info-card li { margin: 4px 0; }
  .note { color: #999; font-style: italic; font-size: 12px !important; }

  .sales-summary { display: flex; gap: 12px; margin-bottom: 20px; }
  .stat { flex: 1; background: white; border: 1px solid #eee; border-radius: 10px; padding: 14px; text-align: center; }
  .stat-value { display: block; font-size: 20px; font-weight: 700; color: #CC0000; }
  .stat-label { display: block; font-size: 11px; color: #888; margin-top: 4px; text-transform: uppercase; }

  .sales-list { display: flex; flex-direction: column; gap: 8px; }
  .sale-row { display: flex; justify-content: space-between; align-items: center; padding: 12px; background: white; border: 1px solid #eee; border-radius: 8px; }
  .sale-info { display: flex; flex-direction: column; flex: 1; }
  .sale-name { font-weight: 600; font-size: 14px; color: #333; }
  .sale-meta { font-size: 11px; color: #888; margin-top: 4px; }
  .sale-amount { font-weight: 700; font-size: 16px; color: #CC0000; margin-left: 12px; }

  /* Calendar */
  .calendar-section { margin-top: 28px; }
  .calendar-section h3 { margin: 0 0 12px; font-size: 18px; font-weight: 700; color: var(--text-primary); }
  .event-list { display: flex; flex-direction: column; gap: 10px; }
  .event-card {
    display: flex;
    gap: 14px;
    padding: 14px;
    background: var(--card-bg, white);
    border: 1px solid var(--border-color, #eee);
    border-radius: 10px;
    border-left: 4px solid #CC0000;
  }
  .event-time {
    font-size: 12px;
    font-weight: 700;
    color: #CC0000;
    min-width: 90px;
    white-space: nowrap;
  }
  .event-details { flex: 1; }
  .event-details h4 { margin: 0 0 4px; font-size: 14px; font-weight: 600; color: var(--text-primary); }
  .event-location { margin: 2px 0; font-size: 12px; color: var(--text-secondary); }
  .event-attendees { margin: 4px 0 0; font-size: 11px; color: var(--text-tertiary, #999); }
</style>
