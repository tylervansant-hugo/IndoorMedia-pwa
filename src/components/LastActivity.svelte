<script>
  import { onMount } from 'svelte';
  import { user } from '../lib/stores.js';
  import { logActivity, getRecentActivity } from '../lib/activity.js';

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
    // Refresh relative time + pick up new activity every 30s.
    const t = setInterval(refresh, 30000);
    // Cross-tab / cross-component updates (activity + status both write localStorage).
    window.addEventListener('storage', refresh);
    // When the rep returns to the Home tab, re-read the log.
    document.addEventListener('visibilitychange', refresh);
    return () => {
      clearInterval(t);
      window.removeEventListener('storage', refresh);
      document.removeEventListener('visibilitychange', refresh);
    };
  });

  $: statusAgo = status ? (now, ago(status.ts)) : '';
</script>

<div class="la-widget">
  <div class="la-head">
    <span class="la-title">📍 Last Activity</span>
    <button class="la-refresh" on:click={refresh} title="Refresh">Refresh</button>
  </div>

  {#if feed.length}
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
