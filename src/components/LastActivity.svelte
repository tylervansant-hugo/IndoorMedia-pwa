<script>
  import { onMount } from 'svelte';
  import { user } from '../lib/stores.js';
  import { logActivity, getRecentActivity } from '../lib/activity.js';
  import { isFirebaseReady, getAllRepActivity, getRepDayEvents } from '../lib/firebase.js';

  // Manager view: Tyler (or role manager/admin) can select a rep to see their
  // recent activity. Individual feed events live only in each rep's local
  // device, but per-rep DAILY activity summaries are synced to Firebase, so for
  // another rep we show their day-by-day activity breakdown + last-active time.
  $: repName_me = ($user?.name || $user?.first_name || '').trim();
  $: isManager = repName_me.toLowerCase().includes('tyler') || $user?.role === 'manager' || $user?.role === 'admin';

  let repOptions = [];        // [{name}] from Firebase activity (managers)
  let selectedRep = '__me__'; // '__me__' = my own live feed
  let repReport = null;       // { days:[{date,...}], lastActive } for selected rep
  let repLoading = false;
  let repAllActivity = [];    // raw Firebase docs cache

  async function loadRepOptions() {
    if (!isManager || !isFirebaseReady()) return;
    try {
      repAllActivity = await getAllRepActivity(30);
      const names = [...new Set(repAllActivity.map(a => a.repName).filter(Boolean))].sort();
      repOptions = names.map(name => ({ name }));
    } catch { repOptions = []; }
  }

  function buildRepReport(name) {
    const rows = repAllActivity.filter(a => a.repName === name);
    if (!rows.length) return { days: [], lastActive: '', totals: null };
    const days = rows
      .map(a => ({
        date: a.date,
        searches: a.searches || 0,
        calls: a.calls || 0,
        emails: a.emails || 0,
        storeViews: a.storeViews || 0,
        prospectViews: a.prospectViews || 0,
        renewalViews: a.renewalViews || 0,
        appointments: a.appointments || 0,
        pageViews: a.pageViews || 0,
        lastActive: a.lastActive || '',
      }))
      .sort((a, b) => (a.date < b.date ? 1 : -1));
    const lastActive = days.reduce((m, d) => (d.lastActive > m ? d.lastActive : m), '');
    const totals = days.reduce((t, d) => {
      for (const k of ['searches','calls','emails','storeViews','prospectViews','renewalViews','appointments']) t[k] = (t[k]||0) + d[k];
      return t;
    }, {});
    return { days: days.slice(0, 14), lastActive, totals };
  }

  async function onRepChange() {
    expandedDay = null; dayEvents = [];
    if (selectedRep === '__me__') { repReport = null; loadFeed(); return; }
    repLoading = true;
    try {
      if (!repAllActivity.length) await loadRepOptions();
      repReport = buildRepReport(selectedRep);
    } finally { repLoading = false; }
  }

  // ── Day drill-down: itemized events for a rep on a specific day ──
  let expandedDay = null;   // date string currently expanded
  let dayEvents = [];       // itemized events for expandedDay
  let dayLoading = false;

  // Resolve the selected rep's repId the same way activity.js derives it, so
  // the fast doc-id lookup hits; falls back to repName query inside firebase.
  function repIdFor(name) {
    // Prefer the id stored on any synced daily doc for this rep.
    const row = repAllActivity.find(a => a.repName === name && a.repId);
    if (row && row.repId) return row.repId;
    return (name || '').toLowerCase().replace(/\s+/g, '_');
  }

  async function toggleDay(date) {
    if (expandedDay === date) { expandedDay = null; dayEvents = []; return; }
    expandedDay = date;
    dayEvents = [];
    dayLoading = true;
    try {
      const evs = await getRepDayEvents({ repId: repIdFor(selectedRep), repName: selectedRep, date });
      // Newest first.
      dayEvents = (evs || []).slice().sort((a, b) => (a.timestamp < b.timestamp ? 1 : -1));
    } catch { dayEvents = []; }
    finally { dayLoading = false; }
  }

  function evTime(ts) {
    try { return new Date(ts).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }); }
    catch { return ''; }
  }

  function fmtDay(iso) {
    try { return new Date(iso + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }); }
    catch { return iso; }
  }
  function fmtLast(iso) {
    if (!iso) return 'Never';
    try { return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }); }
    catch { return iso; }
  }

  // The Home "Last Activity" card now shows the rep's REAL recent actions in the
  // app — stores looked up, prospects called, emails/texts sent, quotes built,
  // contracts written — pulled from the activity log (localStorage, synced to
  // Firebase). The old manual "what am I doing" status picker is preserved but
  // tucked away behind a collapsible "Set status" section.
  const KEY = 'home_status';

  const PRESETS = [
    { emoji: '🚗', text: 'On the road' },
    { emoji: '🤝', text: 'In a meeting' },
    { emoji: '📞', text: 'Making calls' },
    { emoji: '🏪', text: 'Prospecting stores' },
    { emoji: '📝', text: 'Writing a contract' },
    { emoji: '🍽️', text: 'On a break' },
    { emoji: '🏁', text: 'Wrapping up' },
    { emoji: '✅', text: 'Available' },
  ];

  // How each logged action renders in the feed. `tap` describes what happens
  // when the item is clicked (routed via the `open-activity` event in Main).
  function describe(e) {
    const who = (e.store || e.business || '').trim();
    switch (e.action) {
      case 'call':
        return { emoji: '📞', verb: 'Called', target: who || 'a prospect', tap: e.phone ? 'Call again' : '', can: !!e.phone };
      case 'email':
        return { emoji: '✉️', verb: e.kind === 'renewal' ? 'Emailed renewal to' : 'Emailed', target: who || 'a contact', tap: e.email ? 'Email again' : '', can: !!e.email };
      case 'text':
        return { emoji: '💬', verb: 'Texted', target: who || 'a contact', tap: e.phone ? 'Text again' : '', can: !!e.phone };
      case 'quote':
        return { emoji: '🧾', verb: 'Built a quote', target: who ? `for ${who}` : `(${e.items || 0} item${e.items === 1 ? '' : 's'})`, tap: 'Open cart', can: true };
      case 'contract':
        return { emoji: '📝', verb: 'Contract', target: who || 'submitted', tap: '', can: false };
      case 'appointment':
        return { emoji: '📅', verb: 'Booked appt', target: who ? `with ${who}` : '', tap: '', can: false };
      case 'store_view':
        return { emoji: '🏪', verb: 'Looked up store', target: who || '', tap: who ? 'Reopen store' : '', can: !!who };
      case 'prospect_view':
        return { emoji: '🎯', verb: 'Viewed prospect', target: who || '', tap: who ? 'Reopen' : '', can: !!who };
      case 'renewal_view':
        return { emoji: '🔄', verb: 'Reviewed renewal', target: who || '', tap: 'Open renewals', can: true };
      case 'search': {
        const t = (e.store || e.subcategory || e.category || '').trim();
        return { emoji: '🔍', verb: 'Searched', target: t || '', tap: e.storeName || e.store ? 'Rerun search' : '', can: !!(e.storeName || e.store) };
      }
      default:
        return { emoji: '•', verb: e.action, target: who, tap: '', can: false };
    }
  }

  // Fire the app-wide router (handled in Main.svelte) to reopen this item.
  function openItem(e) {
    try {
      document.dispatchEvent(new CustomEvent('open-activity', { detail: e }));
    } catch {}
  }

  let feed = [];
  let status = null;      // { text, emoji, ts }
  let showStatus = false; // collapsed by default
  let editing = false;
  let draftText = '';
  let draftEmoji = '💬';

  function loadFeed() {
    try { feed = getRecentActivity(8); } catch { feed = []; }
  }

  function loadStatus() {
    try {
      const raw = localStorage.getItem(KEY);
      status = raw ? JSON.parse(raw) : null;
    } catch { status = null; }
  }

  function refresh() { loadFeed(); loadStatus(); now = Date.now(); }

  function save(next) {
    status = next;
    try { localStorage.setItem(KEY, JSON.stringify(next)); } catch {}
    const repName = $user?.name || $user?.first_name || 'unknown';
    logActivity('status_update', {
      rep: repName,
      repId: $user?.id,
      status: next.text,
      emoji: next.emoji,
    });
  }

  function setPreset(p) {
    save({ text: p.text, emoji: p.emoji, ts: Date.now() });
    editing = false;
  }

  function startCustom() {
    draftText = status?.text || '';
    draftEmoji = status?.emoji || '💬';
    editing = true;
    showStatus = true;
  }

  function saveCustom() {
    const t = draftText.trim();
    if (!t) { editing = false; return; }
    save({ text: t.slice(0, 60), emoji: draftEmoji || '💬', ts: Date.now() });
    editing = false;
  }

  function clearStatus() {
    status = null;
    try { localStorage.removeItem(KEY); } catch {}
    editing = false;
  }

  // "3m ago", "2h ago", "yesterday"…
  function ago(ts) {
    if (!ts) return '';
    const s = Math.floor((Date.now() - ts) / 1000);
    if (s < 45) return 'just now';
    const m = Math.floor(s / 60);
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ago`;
    const d = Math.floor(h / 24);
    return d === 1 ? 'yesterday' : `${d}d ago`;
  }

  const EMOJI_CHOICES = ['💬', '🚗', '🤝', '📞', '🏪', '📝', '🍽️', '🏁', '✅', '🔥', '💪', '☕'];

  let now = Date.now();
  onMount(() => {
    refresh();
    loadRepOptions();
    // Refresh relative time + pick up new activity every 30s — but PAUSE the
    // timer while the tab is hidden/backgrounded so it doesn't drain battery.
    let t = null;
    const start = () => { if (t == null && document.visibilityState === 'visible') t = setInterval(refresh, 30000); };
    const stop = () => { if (t != null) { clearInterval(t); t = null; } };
    const onVis = () => { if (document.visibilityState === 'visible') { refresh(); start(); } else { stop(); } };
    start();
    // Cross-tab / cross-component updates (activity + status both write localStorage).
    window.addEventListener('storage', refresh);
    // When the rep returns to the Home tab, re-read the log + resume polling.
    document.addEventListener('visibilitychange', onVis);
    return () => {
      stop();
      window.removeEventListener('storage', refresh);
      document.removeEventListener('visibilitychange', onVis);
    };
  });

  $: statusAgo = status ? (now, ago(status.ts)) : '';
</script>

<div class="la-widget">
  <div class="la-head">
    <span class="la-title">📍 Last Activity</span>
    <button class="la-refresh" on:click={refresh} title="Refresh">Refresh</button>
  </div>

  {#if isManager && repOptions.length}
    <div class="la-reppick">
      <label for="la-rep-select">View:</label>
      <select id="la-rep-select" bind:value={selectedRep} on:change={onRepChange}>
        <option value="__me__">👤 Me ({repName_me || 'My activity'})</option>
        {#each repOptions as r}
          <option value={r.name}>{r.name}</option>
        {/each}
      </select>
    </div>
  {/if}

  {#if selectedRep !== '__me__'}
    <!-- Manager: selected rep's activity (daily summary, synced cross-device) -->
    {#if repLoading}
      <p class="la-empty">⏳ Loading {selectedRep}'s activity…</p>
    {:else if repReport && repReport.days.length}
      <p class="la-rep-last">Last active: <strong>{fmtLast(repReport.lastActive)}</strong></p>
      {#if repReport.totals}
        <div class="la-rep-totals">
          <span>🔍 {repReport.totals.searches} searches</span>
          <span>📞 {repReport.totals.calls} calls</span>
          <span>✉️ {repReport.totals.emails} emails</span>
          <span>🏪 {repReport.totals.storeViews} stores</span>
          <span>🎯 {repReport.totals.prospectViews} prospects</span>
          <span>📅 {repReport.totals.appointments} appts</span>
        </div>
      {/if}
      <ul class="la-feed">
        {#each repReport.days as d}
          {@const hasAny = d.searches || d.calls || d.emails || d.storeViews || d.prospectViews || d.appointments || d.renewalViews}
          <li class="la-item">
            <button class="la-repday la-repday-btn" class:tappable={hasAny} disabled={!hasAny} on:click={() => hasAny && toggleDay(d.date)}>
              <span class="la-repday-date">{fmtDay(d.date)}</span>
              <span class="la-repday-stats">
                {#if d.searches}🔍{d.searches} {/if}{#if d.calls}📞{d.calls} {/if}{#if d.emails}✉️{d.emails} {/if}{#if d.storeViews}🏪{d.storeViews} {/if}{#if d.prospectViews}🎯{d.prospectViews} {/if}{#if d.appointments}📅{d.appointments} {/if}{#if d.renewalViews}🔄{d.renewalViews} {/if}
                {#if !hasAny}—{/if}
              </span>
              {#if hasAny}<span class="la-repday-caret" class:open={expandedDay === d.date}>›</span>{/if}
            </button>
            {#if expandedDay === d.date}
              <div class="la-day-detail">
                {#if dayLoading}
                  <p class="la-day-loading">⏳ Loading…</p>
                {:else if dayEvents.length}
                  <ul class="la-day-events">
                    {#each dayEvents as ev}
                      {@const dd = describe(ev)}
                      <li class="la-day-ev">
                        <span class="la-day-ev-emoji">{dd.emoji}</span>
                        <span class="la-day-ev-text"><span class="la-item-verb">{dd.verb}</span>{#if dd.target}<span class="la-item-target"> {dd.target}</span>{/if}</span>
                        <span class="la-day-ev-time">{evTime(ev.timestamp)}</span>
                      </li>
                    {/each}
                  </ul>
                {:else}
                  <p class="la-day-loading">No itemized detail synced for this day. (Older activity may only have daily totals.)</p>
                {/if}
              </div>
            {/if}
          </li>
        {/each}
      </ul>
      <p class="la-rep-note">Showing {selectedRep}'s synced activity — tap any day to see itemized actions.</p>
    {:else}
      <p class="la-empty">No synced activity found for {selectedRep} yet.</p>
    {/if}
  {:else if feed.length}
    <ul class="la-feed">
      {#each feed as e}
        {@const d = describe(e)}
        <li class="la-item">
          <button
            class="la-item-btn"
            class:tappable={d.can}
            disabled={!d.can}
            on:click={() => d.can && openItem(e)}
            title={d.can ? d.tap : ''}
          >
            <span class="la-item-emoji">{d.emoji}</span>
            <span class="la-item-body">
              <span class="la-item-text">
                <span class="la-item-verb">{d.verb}</span>
                {#if d.target}<span class="la-item-target"> {d.target}</span>{/if}
              </span>
              <span class="la-item-meta">
                {#if d.can}<span class="la-item-tap">{d.tap}</span>{/if}
                <span class="la-item-ago">{(now, ago(new Date(e.timestamp).getTime()))}</span>
              </span>
            </span>
            {#if d.can}<span class="la-item-arrow">›</span>{/if}
          </button>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="la-empty">Your recent activity will show up here — the stores you look up, prospects you call, and emails, texts &amp; quotes you send from the app.</p>
  {/if}

  <!-- Manual status (collapsed by default) -->
  <div class="la-status-wrap">
    <button class="la-status-toggle" on:click={() => (showStatus = !showStatus)}>
      <span>{status ? `${status.emoji} ${status.text}` : '💬 Set your status'}</span>
      <span class="la-caret" class:open={showStatus}>▾</span>
    </button>

    {#if showStatus}
      {#if editing}
        <div class="la-editor">
          <div class="la-emoji-row">
            {#each EMOJI_CHOICES as em}
              <button class="la-emoji" class:sel={draftEmoji === em} on:click={() => (draftEmoji = em)}>{em}</button>
            {/each}
          </div>
          <div class="la-input-row">
            <span class="la-input-emoji">{draftEmoji}</span>
            <input
              class="la-input"
              type="text"
              maxlength="60"
              placeholder="What are you up to?"
              bind:value={draftText}
              on:keydown={(e) => e.key === 'Enter' && saveCustom()}
            />
          </div>
          <div class="la-actions">
            <button class="la-save" on:click={saveCustom}>Save status</button>
            <button class="la-cancel" on:click={() => (editing = false)}>Cancel</button>
            {#if status}<button class="la-clear" on:click={clearStatus}>Clear</button>{/if}
          </div>
        </div>
      {:else}
        {#if status}
          <div class="la-status-current">
            <span class="la-status-ago">Set {statusAgo}</span>
            <button class="la-edit" on:click={startCustom}>Update</button>
          </div>
        {/if}
        <div class="la-presets">
          {#each PRESETS as p}
            <button
              class="la-chip"
              class:active={status && status.text === p.text}
              on:click={() => setPreset(p)}
            >
              <span class="la-chip-emoji">{p.emoji}</span>{p.text}
            </button>
          {/each}
          <button class="la-chip la-chip-custom" on:click={startCustom}>✏️ Custom…</button>
        </div>
      {/if}
    {/if}
  </div>
</div>

<style>
  .la-widget {
    background: var(--card-bg, #fff);
    border: 1px solid var(--border-color, #e0e0e0);
    border-radius: 16px;
    padding: 14px 16px 16px;
    margin-bottom: 16px;
    box-shadow: 0 1px 3px var(--card-shadow, rgba(0,0,0,0.06));
  }
  .la-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
  .la-title { font-weight: 800; font-size: 15px; color: var(--text-primary, #1a1a1a); }
  .la-refresh {
    border: 1px solid var(--border-color, #ddd); background: transparent;
    color: var(--accent, #cc0000); font-weight: 700; font-size: 13px;
    padding: 4px 12px; border-radius: 8px; cursor: pointer;
  }
  .la-empty { font-size: 13px; color: var(--text-secondary, #888); margin: 4px 0 12px; line-height: 1.5; }

  /* Manager rep picker */
  .la-reppick { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
  .la-reppick label { font-size: 13px; font-weight: 700; color: var(--text-secondary, #666); }
  .la-reppick select {
    flex: 1; min-width: 0; padding: 8px 10px; border-radius: 8px;
    border: 1px solid var(--border-color, #ddd); background: var(--input-bg, #fff);
    color: var(--text-primary, #222); font-size: 13px; font-weight: 600;
  }
  .la-rep-last { font-size: 13px; color: var(--text-secondary, #666); margin: 0 0 8px; }
  .la-rep-totals { display: flex; flex-wrap: wrap; gap: 6px 12px; margin: 0 0 10px; font-size: 12px; font-weight: 600; color: var(--text-primary, #333); }
  .la-rep-totals span { background: var(--bg-secondary, #f4f4f6); border-radius: 12px; padding: 4px 9px; }
  .la-repday { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 9px 4px; }
  .la-repday-btn { width: 100%; background: transparent; border: none; text-align: left; color: inherit; font: inherit; border-radius: 8px; }
  .la-repday-btn.tappable { cursor: pointer; }
  .la-repday-btn.tappable:active { background: var(--bg-secondary, #f2f2f4); }
  .la-repday-btn:disabled { cursor: default; opacity: 0.7; }
  .la-repday-date { font-size: 14px; font-weight: 700; color: var(--text-primary, #1a1a1a); }
  .la-repday-stats { font-size: 13px; color: var(--text-secondary, #555); text-align: right; flex: 1; }
  .la-repday-caret { font-size: 18px; color: var(--text-secondary, #bbb); line-height: 1; transition: transform .15s; }
  .la-repday-caret.open { transform: rotate(90deg); }
  .la-rep-note { font-size: 11px; color: var(--text-secondary, #999); margin: 8px 0 12px; line-height: 1.4; }

  /* Day drill-down */
  .la-day-detail { padding: 2px 4px 10px 8px; }
  .la-day-loading { font-size: 12px; color: var(--text-secondary, #999); margin: 6px 0; }
  .la-day-events { list-style: none; margin: 4px 0 0; padding: 0; display: flex; flex-direction: column; gap: 2px; border-left: 2px solid var(--border-color, #eee); }
  .la-day-ev { display: flex; align-items: baseline; gap: 9px; padding: 6px 4px 6px 10px; }
  .la-day-ev-emoji { font-size: 15px; width: 18px; text-align: center; flex-shrink: 0; }
  .la-day-ev-text { flex: 1; min-width: 0; font-size: 13px; color: var(--text-primary, #1a1a1a); line-height: 1.3; overflow-wrap: break-word; }
  .la-day-ev-time { font-size: 11px; color: var(--text-secondary, #999); flex-shrink: 0; white-space: nowrap; }

  /* Feed */
  .la-feed { list-style: none; margin: 0 0 12px; padding: 0; display: flex; flex-direction: column; }
  .la-item { border-bottom: 1px solid var(--border-color, #f0f0f0); }
  .la-item:last-child { border-bottom: none; }
  .la-item-btn {
    display: flex; align-items: center; gap: 11px; width: 100%;
    padding: 9px 4px; background: transparent; border: none; text-align: left;
    color: inherit; font: inherit; border-radius: 8px;
  }
  .la-item-btn.tappable { cursor: pointer; }
  .la-item-btn.tappable:active { background: var(--bg-secondary, #f2f2f4); transform: scale(0.995); }
  .la-item-btn:disabled { cursor: default; }
  .la-item-emoji { font-size: 19px; line-height: 1.3; flex-shrink: 0; width: 22px; text-align: center; }
  .la-item-body { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; flex: 1; min-width: 0; }
  .la-item-text { font-size: 14px; color: var(--text-primary, #1a1a1a); line-height: 1.35; min-width: 0; overflow-wrap: break-word; }
  .la-item-verb { font-weight: 700; }
  .la-item-target { color: var(--text-secondary, #555); font-weight: 500; }
  .la-item-meta { display: flex; align-items: baseline; gap: 8px; flex-shrink: 0; }
  .la-item-tap { font-size: 11px; font-weight: 700; color: var(--accent, #cc0000); white-space: nowrap; }
  .la-item-ago { font-size: 12px; color: var(--text-secondary, #999); flex-shrink: 0; white-space: nowrap; }
  .la-item-arrow { font-size: 18px; color: var(--text-secondary, #bbb); flex-shrink: 0; line-height: 1; }

  /* Status toggle */
  .la-status-wrap { border-top: 1px solid var(--border-color, #eee); padding-top: 10px; }
  .la-status-toggle {
    width: 100%; display: flex; align-items: center; justify-content: space-between;
    background: var(--bg-secondary, #f6f6f8); border: 1px solid var(--border-color, #e8e8e8);
    border-radius: 10px; padding: 10px 12px; cursor: pointer;
    color: var(--text-primary, #333); font-weight: 600; font-size: 14px;
  }
  .la-caret { transition: transform .15s; color: var(--text-secondary, #888); }
  .la-caret.open { transform: rotate(180deg); }

  .la-status-current { display: flex; align-items: center; justify-content: space-between; margin: 10px 0 6px; }
  .la-status-ago { font-size: 12px; color: var(--text-secondary, #888); }
  .la-edit {
    border: 1px solid var(--border-color, #ddd); background: transparent;
    color: var(--accent, #cc0000); font-weight: 700; font-size: 12px;
    padding: 3px 10px; border-radius: 8px; cursor: pointer;
  }

  .la-presets { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
  .la-chip {
    display: inline-flex; align-items: center; gap: 5px;
    border: 1px solid var(--border-color, #ddd); background: var(--card-bg, #fff);
    color: var(--text-primary, #333); font-size: 13px; font-weight: 600;
    padding: 7px 12px; border-radius: 18px; cursor: pointer;
    transition: border-color .15s, background .15s;
  }
  .la-chip:active { transform: scale(0.96); }
  .la-chip.active { border-color: var(--accent, #cc0000); background: color-mix(in srgb, var(--accent, #cc0000) 12%, transparent); }
  .la-chip-emoji { font-size: 15px; }
  .la-chip-custom { color: var(--text-secondary, #666); }

  /* Editor */
  .la-editor { display: flex; flex-direction: column; gap: 12px; margin-top: 10px; }
  .la-emoji-row { display: flex; flex-wrap: wrap; gap: 6px; }
  .la-emoji {
    width: 38px; height: 38px; border-radius: 10px; font-size: 20px;
    border: 1px solid var(--border-color, #ddd); background: var(--card-bg, #fff);
    cursor: pointer; line-height: 1;
  }
  .la-emoji.sel { border-color: var(--accent, #cc0000); outline: 2px solid var(--accent, #cc0000); outline-offset: 1px; }
  .la-input-row { display: flex; align-items: center; gap: 8px; }
  .la-input-emoji { font-size: 22px; }
  .la-input {
    flex: 1; padding: 10px 12px; border-radius: 10px;
    border: 1px solid var(--border-color, #ddd); background: var(--input-bg, #fff);
    color: var(--text-primary, #1a1a1a); font-size: 15px;
  }
  .la-actions { display: flex; gap: 8px; flex-wrap: wrap; }
  .la-save {
    flex: 1; min-width: 120px; padding: 10px; border-radius: 10px; border: none;
    background: var(--accent, #cc0000); color: #fff; font-weight: 700; font-size: 14px; cursor: pointer;
  }
  .la-cancel, .la-clear {
    padding: 10px 14px; border-radius: 10px; border: 1px solid var(--border-color, #ddd);
    background: transparent; color: var(--text-secondary, #666); font-weight: 600; font-size: 14px; cursor: pointer;
  }
  .la-clear { color: #cc0000; }
</style>
