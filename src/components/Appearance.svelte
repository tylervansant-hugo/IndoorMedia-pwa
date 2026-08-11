<script>
  import {
    THEMES, MODE_OPTIONS, FONT_OPTIONS,
    getAppearance, setAppearance, resetAppearance, resolveMode,
  } from '../lib/appearance.js';

  let prefs = getAppearance();
  // Effective light/dark for the previews (follows Auto → system).
  $: effMode = resolveMode(prefs.mode);

  function pickTheme(id) { prefs = setAppearance({ theme: id }); }
  function pickMode(id) { prefs = setAppearance({ mode: id }); }
  function pickFont(id) { prefs = setAppearance({ font: id }); }
  function reset() { prefs = (resetAppearance(), getAppearance()); }

  // Build a small preview palette for a theme card in a given mode, mirroring
  // the (guaranteed-legible) math in appearance.js so swatches look accurate.
  function hexToRgb(hex) {
    let h = String(hex).replace('#', '');
    if (h.length === 3) h = h.split('').map(c => c + c).join('');
    return { r: parseInt(h.slice(0,2),16), g: parseInt(h.slice(2,4),16), b: parseInt(h.slice(4,6),16) };
  }
  function rgbToHex(r,g,b){const c=n=>Math.max(0,Math.min(255,Math.round(n))).toString(16).padStart(2,'0');return `#${c(r)}${c(g)}${c(b)}`;}
  function mix(a,b,t){return {r:a.r+(b.r-a.r)*t,g:a.g+(b.g-a.g)*t,b:a.b+(b.b-a.b)*t};}
  function lum({r,g,b}){const ch=v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4);};return 0.2126*ch(r)+0.7152*ch(g)+0.0722*ch(b);}
  const W={r:255,g:255,b:255}, K={r:17,g:17,b:17};
  function previewOf(theme, mode) {
    const isDark = mode === 'dark';
    const m = isDark ? theme.dark : theme.light;
    const base = hexToRgb(m.bg);
    const card = isDark ? mix(base, W, 0.10) : W;
    const text = lum(card) > 0.4 ? K : W;
    const sub = mix(text, card, 0.35);
    return {
      wash: m.wash || rgbToHex(base.r, base.g, base.b),
      base: rgbToHex(base.r, base.g, base.b),
      card: rgbToHex(card.r, card.g, card.b),
      text: rgbToHex(text.r, text.g, text.b),
      sub: rgbToHex(sub.r, sub.g, sub.b),
      accent: theme.accent,
    };
  }
</script>

<div class="appearance">
  <h2>🎨 Appearance</h2>
  <p class="subtitle">Pick a theme — each one is tuned to stay easy to read in both Day and Night mode. Changes apply instantly and save on this device.</p>

  <!-- Day / Night / Auto -->
  <section>
    <h3>Mode</h3>
    <div class="seg">
      {#each MODE_OPTIONS as m}
        <button class="seg-btn" class:active={prefs.mode === m.id} on:click={() => pickMode(m.id)}>
          {m.emoji} {m.label}
        </button>
      {/each}
    </div>
    <p class="hint">
      {#if prefs.mode === 'auto'}Following your device — currently <b>{effMode === 'dark' ? 'Night' : 'Day'}</b>.
      {:else}Locked to <b>{prefs.mode === 'dark' ? 'Night' : 'Day'}</b> mode.{/if}
    </p>
  </section>

  <!-- Themes -->
  <section>
    <h3>Theme</h3>
    <div class="theme-grid">
      {#each THEMES as t}
        {@const pv = previewOf(t, effMode)}
        <button
          class="theme-card"
          class:active={prefs.theme === t.id}
          on:click={() => pickTheme(t.id)}
          style="--tc-wash: {pv.wash}; --tc-base: {pv.base}; --tc-card: {pv.card}; --tc-text: {pv.text}; --tc-sub: {pv.sub}; --tc-accent: {pv.accent};"
        >
          <div class="theme-preview">
            <div class="tp-card">
              <div class="tp-line tp-title"></div>
              <div class="tp-line tp-sub"></div>
              <div class="tp-btn"></div>
            </div>
          </div>
          <div class="theme-meta">
            <span class="theme-name">{t.emoji} {t.name}</span>
            {#if prefs.theme === t.id}<span class="theme-check">✓</span>{/if}
          </div>
        </button>
      {/each}
    </div>
    <p class="hint">Every theme guarantees readable text and buttons — no washed-out or low-contrast combos.</p>
  </section>

  <!-- Font -->
  <section>
    <h3>Font</h3>
    <div class="font-grid">
      {#each FONT_OPTIONS as f}
        <button class="font-btn" class:active={prefs.font === f.id} style="font-family: {f.stack};" on:click={() => pickFont(f.id)}>
          <span class="font-sample">Aa</span>
          <span class="font-label">{f.label}</span>
        </button>
      {/each}
    </div>
  </section>

  <button class="reset-btn" on:click={reset}>↺ Reset to defaults</button>
</div>

<style>
  .appearance { padding-bottom: 30px; }
  h2 { margin: 0 0 4px; font-size: 22px; color: var(--text-primary, #1a1a1a); }
  .subtitle { margin: 0 0 18px; color: var(--text-secondary, #777); font-size: 14px; line-height: 1.5; }
  section { margin-top: 24px; }
  h3 { font-size: 15px; margin: 0 0 10px; color: var(--text-primary, #222); }
  .hint { font-size: 12px; color: var(--text-secondary, #888); margin: 10px 0 0; line-height: 1.5; }
  .hint b { color: var(--text-primary, #333); }

  /* Segmented (mode) */
  .seg { display: flex; border: 1px solid var(--border-color, #ddd); border-radius: 12px; overflow: hidden; }
  .seg-btn {
    flex: 1; padding: 11px 8px; border: none; background: var(--card-bg, #fff);
    color: var(--text-secondary, #666); font-weight: 700; font-size: 14px; cursor: pointer;
    border-right: 1px solid var(--border-color, #eee);
  }
  .seg-btn:last-child { border-right: none; }
  .seg-btn.active { background: var(--accent, #cc0000); color: #fff; }

  /* Theme grid */
  .theme-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
  .theme-card {
    border: 2px solid var(--border-color, #e2e2e2); border-radius: 16px;
    padding: 0; overflow: hidden; cursor: pointer; background: var(--card-bg, #fff);
    transition: border-color .15s, transform .1s; text-align: left;
  }
  .theme-card:active { transform: scale(0.98); }
  .theme-card.active { border-color: var(--accent, #cc0000); outline: 2px solid var(--accent, #cc0000); outline-offset: 1px; }

  .theme-preview {
    height: 92px; padding: 14px; display: flex; align-items: center; justify-content: center;
    background: var(--tc-wash);
  }
  .tp-card {
    width: 100%; background: var(--tc-card); border-radius: 10px; padding: 10px 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.14);
  }
  .tp-line { border-radius: 4px; }
  .tp-title { height: 8px; width: 70%; background: var(--tc-text); }
  .tp-sub { height: 6px; width: 45%; background: var(--tc-sub); margin-top: 6px; }
  .tp-btn { height: 14px; width: 42%; background: var(--tc-accent); border-radius: 6px; margin-top: 9px; }

  .theme-meta {
    display: flex; align-items: center; justify-content: space-between;
    padding: 9px 12px; background: var(--card-bg, #fff);
  }
  .theme-name { font-weight: 700; font-size: 13px; color: var(--text-primary, #1a1a1a); }
  .theme-check { color: var(--accent, #cc0000); font-weight: 900; }

  /* Font grid */
  .font-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
  .font-btn {
    display: flex; flex-direction: column; align-items: center; gap: 4px;
    padding: 12px 8px; border-radius: 12px;
    border: 2px solid var(--border-color, #e2e2e2);
    background: var(--card-bg, #fff); color: var(--text-primary, #222);
    cursor: pointer; transition: border-color .15s, transform .1s;
  }
  .font-btn:active { transform: scale(0.97); }
  .font-btn.active { border-color: var(--accent, #cc0000); }
  .font-sample { font-size: 24px; font-weight: 700; line-height: 1; }
  .font-label { font-size: 11px; color: var(--text-secondary, #777); }

  .reset-btn {
    margin-top: 28px; width: 100%; padding: 12px; border-radius: 10px;
    border: 1px solid var(--border-color, #ddd); background: transparent;
    color: var(--text-secondary, #666); font-weight: 600; font-size: 14px; cursor: pointer;
  }

  @media (max-width: 380px) {
    .font-grid { grid-template-columns: repeat(2, 1fr); }
  }
</style>
