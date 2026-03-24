<script>
  import { onMount } from 'svelte';
  import { user } from '../lib/stores.js';

  let view = 'main'; // main, customers, sales
  let contracts = [];
  let allStores = [];
  let loading = true;
  let searchQuery = '';
  let expandedCustomer = null;
  let emailDraft = null;

  onMount(async () => {
    try {
      const [contractsRes, storesRes] = await Promise.all([
        fetch('/data/contracts.json'),
        fetch('/data/stores.json')
      ]);
      const data = await contractsRes.json();
      contracts = data.contracts || [];
      allStores = await storesRes.json().catch(() => []);
    } catch (err) {
      console.error('Failed to load data:', err);
    }
    loading = false;
  });

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

  // Calculate upcoming events for a client based on contract data
  function getClientEvents(contract) {
    const events = [];
    const today = new Date();
    const contractDate = contract.date ? new Date(contract.date) : null;
    
    if (!contractDate) return events;

    // Install date: ~30 days after contract (next cycle launch)
    const installDate = new Date(contractDate);
    installDate.setDate(installDate.getDate() + 30);
    // Snap to 7th of month (cycle launch)
    const installMonth = installDate.getDate() > 7 ? installDate.getMonth() + 1 : installDate.getMonth();
    const installLaunch = new Date(installDate.getFullYear(), installMonth, 7);
    if (installLaunch >= today) {
      events.push({ type: '📦', label: 'Install', date: installLaunch });
    }

    // Audit window: 45 days after install
    const auditDate = new Date(installLaunch);
    auditDate.setDate(auditDate.getDate() + 45);
    if (auditDate >= today) {
      events.push({ type: '🔍', label: 'Audit Due', date: auditDate });
    }

    // Renewal conversation: 10 months after contract
    const renewalDate = new Date(contractDate);
    renewalDate.setMonth(renewalDate.getMonth() + 10);
    if (renewalDate >= today) {
      events.push({ type: '🔄', label: 'Renewal Conversation', date: renewalDate });
    }

    // Contract end: 12 months after contract
    const endDate = new Date(contractDate);
    endDate.setMonth(endDate.getMonth() + 12);
    if (endDate >= today) {
      events.push({ type: '📋', label: 'Contract Ends', date: endDate });
    }

    return events.sort((a, b) => a.date - b.date);
  }

  function formatDate(d) {
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function daysFromNow(d) {
    const diff = Math.ceil((d - new Date()) / (1000 * 60 * 60 * 24));
    if (diff === 0) return 'Today';
    if (diff === 1) return 'Tomorrow';
    if (diff < 0) return `${Math.abs(diff)}d overdue`;
    if (diff <= 7) return `In ${diff} days`;
    if (diff <= 30) return `In ${Math.ceil(diff / 7)} weeks`;
    return `In ${Math.ceil(diff / 30)} months`;
  }

  function getNearbyStores(contract) {
    const storeNum = contract.store_number || '';
    // Find the customer's store
    const currentStore = allStores.find(s => s.StoreName === storeNum || (storeNum && s.StoreName?.includes(storeNum)));
    if (!currentStore) return [];

    // Find other stores in the same city
    return allStores.filter(s => 
      s.StoreName !== currentStore.StoreName &&
      s.City === currentStore.City &&
      s.State === currentStore.State
    ).slice(0, 8);
  }

  function toggleExpand(idx) {
    expandedCustomer = expandedCustomer === idx ? null : idx;
    emailDraft = null;
  }

  function showEmailDraft(contract, templateType) {
    const biz = contract.business_name || 'your business';
    const owner = contract.contact_name || '';
    const rep = repName || 'Your IndoorMedia Rep';
    const store = contract.store_name || '';

    const templates = {
      kickoff: {
        subject: `What's Next — ${biz} & IndoorMedia`,
        body: `Hi ${owner},\n\nWelcome to IndoorMedia! I wanted to reach out and let you know what happens next with your advertising at ${store}.\n\nYour ad will be printed and installed during the next cycle. Once it's live, I'll check in to make sure everything looks great.\n\nIn the meantime, if you have any questions or want to make changes to your ad, just let me know.\n\nLooking forward to a great partnership!\n\nBest,\n${rep}\nIndoorMedia`
      },
      checkin: {
        subject: `Checking in — ${biz} & IndoorMedia`,
        body: `Hi ${owner},\n\nI wanted to check in and see how things are going with your register tape ad at ${store}.\n\nHave you noticed any new customers mentioning the ad? Many of our advertisers see results within the first few weeks — I'd love to hear your experience.\n\nIf you'd like to make any changes for the next cycle, now's a great time to let me know.\n\nBest,\n${rep}\nIndoorMedia`
      },
      upsell: {
        subject: `Expansion Opportunity — ${biz}`,
        body: `Hi ${owner},\n\nYour ad at ${store} has been running great, and I wanted to share some ways to expand your reach:\n\n• Add nearby stores — reach even more shoppers in your area\n• DigitalBoost — geofenced digital ads near the store (240K impressions/mo)\n• Double Ad — upgrade to a larger ad for more visibility\n• Cartvertising — ads on shopping carts for maximum exposure\n\nWould you be open to a quick chat about growing your presence?\n\nBest,\n${rep}\nIndoorMedia`
      },
      renewal: {
        subject: `Time to Renew — ${biz} & IndoorMedia`,
        body: `Hi ${owner},\n\nYour advertising contract at ${store} is coming up for renewal. I wanted to touch base early so we can ensure there's no gap in your coverage.\n\nRenewing now locks in your current rate and keeps your ad running without interruption. Many of our advertisers also use renewal time to:\n\n• Add additional stores\n• Upgrade to a Double Ad\n• Bundle with digital products for better results\n\nCan we set up a quick call this week to discuss?\n\nBest,\n${rep}\nIndoorMedia`
      }
    };

    emailDraft = templates[templateType] || templates.kickoff;
  }

  function copyEmail() {
    if (!emailDraft) return;
    const text = `Subject: ${emailDraft.subject}\n\n${emailDraft.body}`;
    navigator.clipboard.writeText(text).then(() => {
      emailDraft = { ...emailDraft, copied: true };
      setTimeout(() => { emailDraft = { ...emailDraft, copied: false }; }, 2000);
    });
  }

  function goBack() {
    view = 'main';
    searchQuery = '';
    expandedCustomer = null;
    emailDraft = null;
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
        {#each filteredCustomers as c, i}
          {@const clientEvents = getClientEvents(c)}
          {@const nearbyStores = getNearbyStores(c)}
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
            {#if clientEvents.length > 0}
              <div class="client-events">
                <p class="events-label">Upcoming</p>
                {#each clientEvents as evt}
                  <div class="client-event" class:soon={daysFromNow(evt.date).startsWith('In') && parseInt(daysFromNow(evt.date).match(/\d+/)) <= 7 || daysFromNow(evt.date) === 'Today' || daysFromNow(evt.date) === 'Tomorrow'} class:overdue={daysFromNow(evt.date).includes('overdue')}>
                    <span class="evt-icon">{evt.type}</span>
                    <span class="evt-label">{evt.label}</span>
                    <span class="evt-date">{formatDate(evt.date)} · {daysFromNow(evt.date)}</span>
                  </div>
                {/each}
              </div>
            {/if}
            <div class="card-actions">
              {#if c.contact_phone}
                <a href="tel:{c.contact_phone}" class="action-btn call">📞 Call</a>
              {/if}
              {#if c.contact_email}
                <a href="mailto:{c.contact_email}" class="action-btn">📧 Email</a>
              {/if}
              <button class="action-btn expand-btn" on:click={() => toggleExpand(i)}>
                {expandedCustomer === i ? '▲ Less' : '🚀 More'}
              </button>
            </div>

            {#if expandedCustomer === i}
              <div class="expanded-section">
                <!-- Email Templates -->
                <div class="section-header">✉️ Draft Email</div>
                <div class="email-btns">
                  <button class="email-tmpl-btn" on:click={() => showEmailDraft(c, 'kickoff')}>🚀 Kickoff</button>
                  <button class="email-tmpl-btn" on:click={() => showEmailDraft(c, 'checkin')}>✅ Check-in</button>
                  <button class="email-tmpl-btn" on:click={() => showEmailDraft(c, 'upsell')}>⬆️ Upsell</button>
                  <button class="email-tmpl-btn" on:click={() => showEmailDraft(c, 'renewal')}>🔄 Renewal</button>
                </div>

                {#if emailDraft}
                  <div class="draft-box">
                    <p class="draft-subject"><strong>Subject:</strong> {emailDraft.subject}</p>
                    <pre class="draft-body">{emailDraft.body}</pre>
                    <button class="copy-btn" on:click={copyEmail}>
                      {emailDraft.copied ? '✅ Copied!' : '📋 Copy Email'}
                    </button>
                    {#if c.contact_email}
                      <a href="mailto:{c.contact_email}?subject={encodeURIComponent(emailDraft.subject)}&body={encodeURIComponent(emailDraft.body)}" class="send-btn">📤 Open in Mail</a>
                    {/if}
                  </div>
                {/if}

                <!-- Expansion Opportunities -->
                <div class="section-header">🚀 Expansion Opportunities</div>
                
                {#if nearbyStores.length > 0}
                  <p class="expand-label">🏪 Nearby Stores in {nearbyStores[0]?.City}</p>
                  <div class="nearby-list">
                    {#each nearbyStores as ns}
                      <div class="nearby-store">
                        <span class="ns-name">{ns.GroceryChain}</span>
                        <span class="ns-num">{ns.StoreName}</span>
                      </div>
                    {/each}
                  </div>
                {:else}
                  <p class="expand-note">No other stores found in this city</p>
                {/if}

                <p class="expand-label">📦 Product Upsells</p>
                <div class="upsell-list">
                  <div class="upsell-item">🚀 <strong>DigitalBoost</strong> — Geofence ads (240K impressions/mo)</div>
                  <div class="upsell-item">📍 <strong>FindLocal</strong> — SEO & listings ($695)</div>
                  <div class="upsell-item">⭐ <strong>ReviewBoost</strong> — Automated reviews ($695)</div>
                  <div class="upsell-item">💎 <strong>LoyaltyBoost</strong> — Loyalty program ($3,600/yr)</div>
                  <div class="upsell-item">🛒 <strong>Cartvertising</strong> — Cart ads ($2,995+)</div>
                  <div class="upsell-item">📰 <strong>Double Ad</strong> — Upgrade ad size</div>
                </div>
              </div>
            {/if}
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

  /* Client Events */
  .client-events { margin: 10px 0; padding: 10px; background: var(--bg-secondary, #f9f9f9); border-radius: 8px; }
  .events-label { margin: 0 0 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--text-tertiary, #999); letter-spacing: 0.5px; }
  .client-event { display: flex; align-items: center; gap: 6px; padding: 4px 0; font-size: 12px; }
  .evt-icon { font-size: 14px; }
  .evt-label { font-weight: 600; color: var(--text-primary); min-width: 120px; }
  .evt-date { color: var(--text-secondary); }
  .client-event.soon .evt-date { color: #CC0000; font-weight: 600; }
  .client-event.overdue .evt-date { color: #c33; font-weight: 700; }
  .client-event.overdue .evt-label { color: #c33; }

  /* Expanded Section */
  .expand-btn { background: #fff5f5 !important; color: #CC0000 !important; border-color: #CC0000 !important; font-weight: 600; }
  .expanded-section { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border-color, #eee); }
  .section-header { font-size: 13px; font-weight: 700; color: var(--text-primary); margin: 12px 0 8px; text-transform: uppercase; letter-spacing: 0.5px; }
  .section-header:first-child { margin-top: 0; }

  /* Email Templates */
  .email-btns { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
  .email-tmpl-btn { padding: 8px 12px; background: var(--card-bg, white); border: 1px solid var(--border-color, #ddd); border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.2s; color: var(--text-primary); }
  .email-tmpl-btn:hover { border-color: #CC0000; background: #fff5f5; }

  .draft-box { background: var(--bg-secondary, #f5f5f5); border-radius: 8px; padding: 12px; margin-bottom: 12px; }
  .draft-subject { margin: 0 0 8px; font-size: 13px; color: var(--text-primary); }
  .draft-body { margin: 0; font-size: 12px; color: var(--text-secondary); white-space: pre-wrap; font-family: inherit; line-height: 1.5; max-height: 200px; overflow-y: auto; }
  .copy-btn { padding: 8px 16px; background: #CC0000; color: white; border: none; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; margin-top: 8px; margin-right: 8px; }
  .send-btn { display: inline-block; padding: 8px 16px; background: #1565c0; color: white; border: none; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; margin-top: 8px; text-decoration: none; }

  /* Expansion */
  .expand-label { margin: 8px 0 6px; font-size: 12px; font-weight: 700; color: var(--text-secondary); }
  .expand-note { font-size: 12px; color: var(--text-tertiary, #999); font-style: italic; }
  .nearby-list { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; }
  .nearby-store { display: flex; justify-content: space-between; padding: 6px 10px; background: var(--card-bg, white); border: 1px solid var(--border-color, #eee); border-radius: 6px; font-size: 12px; }
  .ns-name { font-weight: 600; color: var(--text-primary); }
  .ns-num { color: #CC0000; font-weight: 600; font-size: 11px; }

  .upsell-list { display: flex; flex-direction: column; gap: 4px; }
  .upsell-item { font-size: 12px; color: var(--text-secondary); padding: 4px 0; }
  .upsell-item strong { color: var(--text-primary); }
</style>
