<script>
  import { user } from '../lib/stores.js';
  import { getRepActivityReport, getDailySummaries } from '../lib/activity.js';
  import { isFirebaseReady, getAllRepActivity } from '../lib/firebase.js';

  export let contracts = [];

  // Parse contract dates safely
  function parseContractDate(dateStr) {
    if (!dateStr) return new Date(0);
    const dateOnly = dateStr.split(' ')[0];
    const parts = dateOnly.includes('-') ? dateOnly.split('-') : null;
    if (parts && parts.length === 3) {
      return new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]), 12, 0, 0);
    }
    const slashParts = dateOnly.split('/');
    if (slashParts.length === 3) {
      return new Date(parseInt(slashParts[2]), parseInt(slashParts[0]) - 1, parseInt(slashParts[1]), 12, 0, 0);
    }
    return new Date(dateStr);
  }

  let analyticsView = 'year';
  let analyticsZone = 'all';
  let analyticsExpandedRep = null;

  $: filteredContracts = analyticsZone === 'all' ? contracts : contracts.filter(c => (c.zone || '') === analyticsZone);
  $: yearlyStats = calcYearlyStats(filteredContracts);
  $: monthlyStats = calcMonthlyStats(filteredContracts);
  $: repStats = calcRepStats(filteredContracts);

  function getAvailableZones() {
    const zones = new Set();
    contracts.forEach(c => { if (c.zone) zones.add(c.zone); });
    return Array.from(zones).sort();
  }

  function calcYearlyStats(filtered) {
    const byYear = {};
    filtered.forEach(c => {
      const date = c.date || '';
      if (!date) return;
      try {
        const year = date.includes('/') ? new Date(date).getFullYear() : parseInt(date.substring(0, 4));
        if (!byYear[year]) byYear[year] = { year, total: 0, count: 0 };
        byYear[year].total += c.total_amount || 0;
        byYear[year].count += 1;
      } catch {}
    });
    const sorted = Object.values(byYear).sort((a, b) => b.year - a.year);
    sorted.forEach((stat, i) => {
      const prior = sorted[i + 1];
      stat.change = prior ? ((stat.total - prior.total) / prior.total) * 100 : null;
    });
    return sorted;
  }

  function calcMonthlyStats(filtered) {
    const byMonth = {};
    filtered.forEach(c => {
      const date = c.date || '';
      if (!date) return;
      try {
        const d = date.includes('/') ? new Date(date) : new Date(date.substring(0, 10));
        const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
        if (!byMonth[key]) byMonth[key] = { key, total: 0, count: 0 };
        byMonth[key].total += c.total_amount || 0;
        byMonth[key].count += 1;
      } catch {}
    });
    return Object.values(byMonth).sort((a, b) => b.key.localeCompare(a.key)).map(m => ({
      ...m,
      label: new Date(m.key + '-01').toLocaleDateString('en-US', { year: 'numeric', month: 'short' })
    }));
  }

  function calcRepStats(filtered) {
    const byRep = {};
    filtered.forEach(c => {
      const rep = c.sales_rep || 'Unknown';
      const date = c.date || '';
      let year = 0;
      try {
        year = date.includes('/') ? new Date(date).getFullYear() : parseInt(date.substring(0, 4));
      } catch {}
      if (!byRep[rep]) byRep[rep] = { rep, y2025: 0, y2026: 0, total: 0, count: 0 };
      const amt = c.total_amount || 0;
      byRep[rep].total += amt;
      byRep[rep].count += 1;
      if (year === 2025) byRep[rep].y2025 += amt;
      if (year === 2026) byRep[rep].y2026 += amt;
    });
    return Object.values(byRep).sort((a, b) => b.total - a.total);
  }

  async function getActivityData() {
    const local = getRepActivityReport();
    
    if (isFirebaseReady()) {
      try {
        const allActivity = await getAllRepActivity(7);
        if (allActivity.length > 0) {
          const byRep = {};
          allActivity.forEach(a => {
            if (!byRep[a.repName]) byRep[a.repName] = { logins: 0, pageViews: 0, searches: 0, calls: 0, emails: 0, lastActive: '', days: new Set() };
            const r = byRep[a.repName];
            r.logins += a.logins || 0;
            r.pageViews += a.pageViews || 0;
            r.searches += a.searches || 0;
            r.calls += a.calls || 0;
            r.emails += a.emails || 0;
            r.days.add(a.date);
            if (a.lastActive > r.lastActive) r.lastActive = a.lastActive;
          });
          
          local.allReps = Object.entries(byRep).map(([name, data]) => ({
            name,
            ...data,
            activeDays: data.days.size,
            lastActive: data.lastActive ? new Date(data.lastActive).toLocaleString() : 'Never'
          })).sort((a, b) => b.pageViews - a.pageViews);
          
          local.firebaseConnected = true;
        }
      } catch (e) {
        console.warn('Firebase activity fetch error:', e);
      }
    }
    
    local.firebaseConnected = local.firebaseConnected || false;
    local.allReps = local.allReps || [];
    return local;
  }
</script>

<div class="analytics-container">
  <h2 class="typo-page-title">📊 Sales Analytics</h2>
  
  <!-- View selector -->
  <div class="period-selector">
    <button class="period-btn" class:active={analyticsView === 'year'} on:click={() => analyticsView = 'year'}>By Year</button>
    <button class="period-btn" class:active={analyticsView === 'month'} on:click={() => analyticsView = 'month'}>By Month</button>
    <button class="period-btn" class:active={analyticsView === 'rep'} on:click={() => analyticsView = 'rep'}>By Rep</button>
    {#if $user?.role === 'manager'}
      <button class="period-btn" class:active={analyticsView === 'activity'} on:click={() => analyticsView = 'activity'}>📱 App Usage</button>
    {/if}
  </div>

  <!-- Zone filter -->
  <div class="zone-filter">
    <span class="zone-label">Zone:</span>
    <button class="zone-btn" class:active={analyticsZone === 'all'} on:click={() => analyticsZone = 'all'}>All</button>
    {#each getAvailableZones() as zone}
      <button class="zone-btn" class:active={analyticsZone === zone} on:click={() => analyticsZone = zone}>{zone}</button>
    {/each}
  </div>

  {#if analyticsZone !== 'all'}
    <p class="zone-active-label">Filtered: Zone {analyticsZone} ({filteredContracts.length} contracts, ${filteredContracts.reduce((s,c) => s + (c.total_amount||0), 0).toLocaleString()})</p>
  {/if}

  {#if analyticsView === 'year'}
    <div class="analytics-cards">
      {#each yearlyStats as stat}
        <div class="analytics-card">
          <div class="analytics-year">{stat.year}</div>
          <div class="analytics-amount">${(stat.total / 1000).toFixed(0)}K</div>
          <div class="analytics-count">{stat.count} contracts</div>
          {#if stat.change !== null}
            <div class="analytics-change" class:positive={stat.change > 0} class:negative={stat.change < 0}>
              {stat.change > 0 ? '↑' : '↓'} {Math.abs(stat.change).toFixed(1)}%
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {:else if analyticsView === 'month'}
    <div class="month-table">
      <table>
        <thead><tr><th>Month</th><th>Revenue</th><th>Contracts</th><th>Avg Deal</th></tr></thead>
        <tbody>
          {#each monthlyStats as stat}
            <tr>
              <td>{stat.label}</td>
              <td>${stat.total.toLocaleString()}</td>
              <td>{stat.count}</td>
              <td>${(stat.total / stat.count).toLocaleString(undefined, {maximumFractionDigits: 0})}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else if analyticsView === 'rep'}
    <div class="rep-table">
      <table>
        <thead><tr><th>Rep</th><th>2025</th><th>2026 YTD</th><th>Total</th><th>Deals</th></tr></thead>
        <tbody>
          {#each repStats as stat}
            <tr>
              <td>{stat.rep}</td>
              <td>${stat.y2025.toLocaleString()}</td>
              <td>${stat.y2026.toLocaleString()}</td>
              <td>${stat.total.toLocaleString()}</td>
              <td>{stat.count}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else if analyticsView === 'activity'}
    <div class="activity-section">
      <h3>📱 Rep App Usage</h3>
      <p class="activity-note">Activity tracked per device. Data shown for current device — multi-device rollup coming soon.</p>
      
      {#await getActivityData() then actData}
        <div class="activity-summary">
          <div class="activity-card">
            <div class="activity-icon">📊</div>
            <div class="activity-stat">{actData.today.pageViews || 0}</div>
            <div class="activity-label">Page Views Today</div>
          </div>
          <div class="activity-card">
            <div class="activity-icon">🔍</div>
            <div class="activity-stat">{actData.today.searches || 0}</div>
            <div class="activity-label">Searches Today</div>
          </div>
          <div class="activity-card">
            <div class="activity-icon">📞</div>
            <div class="activity-stat">{actData.today.calls || 0}</div>
            <div class="activity-label">Calls Today</div>
          </div>
          <div class="activity-card">
            <div class="activity-icon">🔐</div>
            <div class="activity-stat">{actData.today.logins || 0}</div>
            <div class="activity-label">Logins Today</div>
          </div>
        </div>

        <h4>Last 7 Days</h4>
        <div class="activity-table-wrap">
          <table class="activity-table">
            <thead><tr><th>Date</th><th>Views</th><th>Searches</th><th>Calls</th><th>Logins</th></tr></thead>
            <tbody>
              {#each actData.dailyBreakdown as day}
                <tr>
                  <td>{new Date(day.date + 'T12:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</td>
                  <td>{day.pageViews || 0}</td>
                  <td>{day.searches || 0}</td>
                  <td>{day.calls || 0}</td>
                  <td>{day.logins || 0}</td>
                </tr>
              {/each}
              {#if actData.dailyBreakdown.length === 0}
                <tr><td colspan="5" style="text-align:center; color: var(--text-secondary);">No activity data yet. Usage will appear as reps use the app.</td></tr>
              {/if}
            </tbody>
          </table>
        </div>

        {#if actData.firebaseConnected && actData.allReps.length > 0}
          <h4>👥 All Reps — Last 7 Days</h4>
          <div class="activity-table-wrap">
            <table class="activity-table">
              <thead><tr><th>Rep</th><th>Days Active</th><th>Views</th><th>Searches</th><th>Calls</th><th>Last Active</th></tr></thead>
              <tbody>
                {#each actData.allReps as rep}
                  <tr>
                    <td><strong>{rep.name}</strong></td>
                    <td>{rep.activeDays}/7</td>
                    <td>{rep.pageViews}</td>
                    <td>{rep.searches}</td>
                    <td>{rep.calls}</td>
                    <td style="font-size:11px;">{rep.lastActive}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {:else if !actData.firebaseConnected}
          <div class="firebase-setup-prompt">
            <h4>🔗 Enable Cross-Device Tracking</h4>
            <p>To see all reps' activity in one place, connect Firebase:</p>
            <button class="book-appt-btn" on:click={() => window.open(import.meta.env.BASE_URL + 'setup-firebase.html', '_blank')}>⚙️ Set Up Firebase</button>
          </div>
        {/if}

        <h4>📊 Your Device — 30-Day Totals</h4>
        <div class="activity-totals">
          <div><strong>Page Views:</strong> {actData.last30days.pageViews || 0}</div>
          <div><strong>Searches:</strong> {actData.last30days.searches || 0}</div>
          <div><strong>Calls Made:</strong> {actData.last30days.calls || 0}</div>
          <div><strong>Emails Sent:</strong> {actData.last30days.emails || 0}</div>
          <div><strong>Logins:</strong> {actData.last30days.logins || 0}</div>
        </div>
      {/await}

      <!-- Closed Deals by Rep -->
      <h4>💰 Closed Deals — This Month</h4>
      {#if true}
        {@const now = new Date()}
        {@const thisMonth = now.getMonth()}
        {@const thisYear = now.getFullYear()}
        {@const monthContracts = contracts.filter(c => { const d = parseContractDate(c.date); return d.getMonth() === thisMonth && d.getFullYear() === thisYear; })}
        {@const repDeals = (() => {
          const map = {};
          monthContracts.forEach(c => {
            const rep = c.sales_rep || 'Unknown';
            if (!map[rep]) map[rep] = { name: rep, deals: 0, revenue: 0, businesses: [] };
            map[rep].deals++;
            map[rep].revenue += (c.total_amount || 0);
            const biz = c.business_name || 'Unknown';
            if (!map[rep].businesses.find(b => b.name === biz)) {
              map[rep].businesses.push({ name: biz, amount: c.total_amount || 0, store: c.store_number || '', date: c.date || '' });
            }
          });
          return Object.values(map).sort((a, b) => b.revenue - a.revenue);
        })()}
        {#if repDeals.length > 0}
          <div class="deals-summary">
            <div class="deals-total">
              <span class="deals-total-value">${monthContracts.reduce((s,c) => s + (c.total_amount||0), 0).toLocaleString()}</span>
              <span class="deals-total-label">{monthContracts.length} deals this month</span>
            </div>
          </div>
          <div class="activity-table-wrap">
            <table class="activity-table">
              <thead><tr><th>Rep</th><th>Deals</th><th>Revenue</th></tr></thead>
              <tbody>
                {#each repDeals as rep}
                  <tr on:click={() => analyticsExpandedRep = analyticsExpandedRep === rep.name ? null : rep.name} style="cursor:pointer;">
                    <td><strong>{rep.name}</strong></td>
                    <td>{rep.deals}</td>
                    <td class="profit">${rep.revenue.toLocaleString()}</td>
                  </tr>
                  {#if analyticsExpandedRep === rep.name}
                    {#each rep.businesses.sort((a,b) => b.amount - a.amount) as biz}
                      <tr class="deal-detail-row">
                        <td style="padding-left:24px;font-size:12px;color:var(--text-secondary);">{biz.name}</td>
                        <td style="font-size:12px;color:var(--text-secondary);">{biz.store ? `#${biz.store}` : ''}</td>
                        <td style="font-size:12px;color:#2E7D32;">${biz.amount.toLocaleString()}</td>
                      </tr>
                    {/each}
                  {/if}
                {/each}
              </tbody>
            </table>
          </div>
        {:else}
          <p class="subtitle" style="font-size:13px;">No contracts this month yet.</p>
        {/if}
      {/if}
    </div>
  {/if}
</div>

<style>
  .analytics-container { padding: 16px; padding-bottom: 140px; max-width: 100%; margin: 0 auto; width: 100%; }
  .period-selector { display: flex; gap: 8px; margin-bottom: 12px; }
  .zone-filter { display: flex; align-items: center; gap: 6px; margin-bottom: 16px; overflow-x: auto; white-space: nowrap; padding-bottom: 4px; }
  .zone-label { font-size: 12px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; flex-shrink: 0; }
  .zone-btn { padding: 5px 12px; border: 1px solid var(--border-color); border-radius: 16px; background: var(--card-bg); font-size: 12px; font-weight: 600; cursor: pointer; color: var(--text-secondary); transition: all 0.2s; flex-shrink: 0; }
  .zone-btn.active { background: #1a237e; color: white; border-color: #1a237e; }
  .zone-btn:hover:not(.active) { border-color: #1a237e; color: #1a237e; }
  .zone-active-label { font-size: 13px; color: #1a237e; font-weight: 600; margin-bottom: 16px; }
  .period-btn { padding: 8px 16px; border: 1px solid var(--border-color); border-radius: 20px; background: var(--card-bg); color: var(--text-secondary); font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
  .period-btn.active { background: #CC0000; color: white; border-color: #CC0000; }
  .analytics-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; }
  .analytics-card { background: var(--card-bg, #ffffff); border: 1px solid #e8e8e8; border-radius: 12px; padding: 16px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.06); transition: box-shadow 0.2s; }
  .analytics-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
  :global([data-theme='dark']) .analytics-card { background: #1e1e1e; border-color: #333; }
  .analytics-year { font-size: 18px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px; }
  .analytics-amount { font-size: 28px; font-weight: 800; color: #CC0000; margin-bottom: 4px; }
  .analytics-count { font-size: 12px; color: var(--text-secondary); margin-bottom: 8px; }
  .analytics-change { font-size: 14px; font-weight: 600; padding: 4px 8px; border-radius: 8px; display: inline-block; }
  .analytics-change.positive { background: #e8f5e9; color: #2e7d32; }
  .analytics-change.negative { background: #ffebee; color: #c62828; }
  
  .activity-section h3 { font-size: 17px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary); }
  .activity-section h4 { font-size: 15px; font-weight: 600; margin: 20px 0 10px; color: var(--text-primary); }
  .activity-note { font-size: 12px; color: var(--text-secondary); margin-bottom: 16px; }
  .activity-summary { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 20px; }
  .activity-card { background: var(--card-bg, #ffffff); border: 1px solid #e8e8e8; border-radius: 12px; padding: 16px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
  :global([data-theme='dark']) .activity-card { background: #1e1e1e; border-color: #333; }
  .activity-icon { font-size: 28px; margin-bottom: 6px; }
  .activity-stat { font-size: 28px; font-weight: 800; color: #CC0000; }
  .activity-label { font-size: 12px; color: var(--text-secondary); font-weight: 600; margin-top: 4px; }
  .activity-table-wrap { overflow-x: auto; }
  .activity-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .activity-table th { background: var(--bg-secondary, #f5f5f5); padding: 8px 10px; text-align: left; font-weight: 700; color: var(--text-secondary); border-bottom: 2px solid var(--border-color); }
  .activity-table td { padding: 8px 10px; border-bottom: 1px solid var(--border-color); color: var(--text-primary); }
  .activity-totals { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 14px; color: var(--text-primary); }
  .activity-totals strong { color: var(--text-secondary); }
  .deals-summary { margin-bottom: 12px; }
  .deals-total { text-align: center; padding: 14px; background: #E8F5E9; border-radius: 10px; border: 1px solid #2E7D32; }
  .deals-total-value { font-size: 24px; font-weight: 800; color: #2E7D32; display: block; }
  .deals-total-label { font-size: 12px; color: #2E7D32; font-weight: 600; }
  .deal-detail-row { background: var(--bg-secondary, #f9f9f9) !important; }
  .profit { color: #2E7D32; font-weight: 700; }
  .firebase-setup-prompt { background: var(--card-bg); border: 2px dashed var(--border-color); border-radius: 12px; padding: 20px; text-align: center; margin: 16px 0; }
  .firebase-setup-prompt h4 { margin: 0 0 8px; color: var(--text-primary); }
  .firebase-setup-prompt p { font-size: 13px; color: var(--text-secondary); margin: 0 0 12px; }
  .month-table, .rep-table { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; overflow: hidden; }
  .month-table table, .rep-table table { width: 100%; border-collapse: collapse; }
  .month-table th, .rep-table th { background: var(--bg-secondary); padding: 12px; text-align: left; font-weight: 700; font-size: 12px; color: var(--text-secondary); text-transform: uppercase; border-bottom: 1px solid var(--border-color); }
  .month-table td, .rep-table td { padding: 12px; border-bottom: 1px solid var(--border-color); color: var(--text-primary); }
  .month-table tr:last-child td, .rep-table tr:last-child td { border-bottom: none; }
  .month-table tr:hover, .rep-table tr:hover { background: var(--bg-secondary); }
  .subtitle { font-size: 13px; color: var(--text-secondary); }
  .book-appt-btn { background: #CC0000; color: white; border: none; border-radius: 8px; padding: 10px 20px; font-size: 14px; font-weight: 600; cursor: pointer; }
  .typo-page-title { font-size: 22px; font-weight: 800; color: var(--text-primary); margin-bottom: 12px; }
</style>
