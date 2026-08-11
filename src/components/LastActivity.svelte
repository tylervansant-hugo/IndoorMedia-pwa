<script>
  import { onMount } from 'svelte';
  import { user } from '../lib/stores.js';
  import { logActivity } from '../lib/activity.js';

  // A lightweight "what am I doing right now" status the rep can update from the
  // Home Screen. Persisted per-device to localStorage so it survives reloads.
  //   home_status -> { text, emoji, ts }
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

  let status = null;      // { text, emoji, ts }
  let editing = false;
  let draftText = '';
  let draftEmoji = '💬';

  function load() {
    try {
      const raw = localStorage.getItem(KEY);
      status = raw ? JSON.parse(raw) : null;
    } catch { status = null; }
  }

  function save(next) {
    status = next;
    try { localStorage.setItem(KEY, JSON.stringify(next)); } catch {}
    // Log it so managers can see rep activity cross-device.
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
    if (s < 60) return 'just now';
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
    load();
    // Refresh the relative "ago" label every minute.
    const t = setInterval(() => { now = Date.now(); }, 60000);
    window.addEventListener('storage', load);
    return () => { clearInterval(t); window.removeEventListener('storage', load); };
  });
  // Reference `now` so the label recomputes on the interval tick.
  $: agoLabel = status ? (now, ago(status.ts)) : '';
</script>

<div class="la-widget">
  <div class="la-head">
    <span class="la-title">📍 Last Activity</span>
    {#if status && !editing}
      <button class="la-edit" on:click={startCustom}>Update</button>
    {/if}
  </div>

  {#if editing}
    <div class="la-editor">
      <div class="la-emoji-row">
        {#each EMOJI_CHOICES as e}
          <button class="la-emoji" class:sel={draftEmoji === e} on:click={() => draftEmoji = e}>{e}</button>
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
        <button class="la-cancel" on:click={() => editing = false}>Cancel</button>
        {#if status}<button class="la-clear" on:click={clearStatus}>Clear</button>{/if}
      </div>
    </div>
  {:else if status}
    <button class="la-current" on:click={startCustom}>
      <span class="la-current-emoji">{status.emoji}</span>
      <span class="la-current-body">
        <span class="la-current-text">{status.text}</span>
        <span class="la-current-ago">Updated {agoLabel}</span>
      </span>
      <span class="la-current-arrow">✎</span>
    </button>
  {:else}
    <p class="la-empty">Set your current status so your team knows what you're working on.</p>
  {/if}

  {#if !editing}
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
  .la-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
  .la-title { font-weight: 800; font-size: 15px; color: var(--text-primary, #1a1a1a); }
  .la-edit {
    border: 1px solid var(--border-color, #ddd); background: transparent;
    color: var(--accent, #cc0000); font-weight: 700; font-size: 13px;
    padding: 4px 12px; border-radius: 8px; cursor: pointer;
  }
  .la-empty { font-size: 13px; color: var(--text-secondary, #888); margin: 0 0 12px; line-height: 1.5; }

  .la-current {
    display: flex; align-items: center; gap: 12px; width: 100%;
    background: var(--bg-secondary, #f6f6f8); border: 1px solid var(--border-color, #e8e8e8);
    border-radius: 12px; padding: 12px 14px; margin-bottom: 12px;
    cursor: pointer; text-align: left; color: inherit;
  }
  .la-current:active { transform: scale(0.99); }
  .la-current-emoji { font-size: 28px; line-height: 1; flex-shrink: 0; }
  .la-current-body { display: flex; flex-direction: column; gap: 2px; flex: 1; min-width: 0; }
  .la-current-text { font-weight: 700; font-size: 15px; color: var(--text-primary, #1a1a1a); overflow: hidden; text-overflow: ellipsis; }
  .la-current-ago { font-size: 12px; color: var(--text-secondary, #888); }
  .la-current-arrow { font-size: 16px; color: var(--text-secondary, #999); flex-shrink: 0; }

  .la-presets { display: flex; flex-wrap: wrap; gap: 8px; }
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
  .la-editor { display: flex; flex-direction: column; gap: 12px; }
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
