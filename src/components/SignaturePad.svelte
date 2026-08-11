<script>
  // Reusable e-signature capture.
  // Flow: customer types their printed name → the sign area unlocks → they draw
  // their signature with finger/stylus/mouse. Exposes both the typed name and a
  // PNG data URL of the drawn signature via two-way bound props + a change event.
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';

  export let name = '';          // typed printed name (bindable)
  export let signatureData = ''; // PNG data URL of the drawn signature (bindable)
  export let label = 'Customer Signature';
  export let nameLabel = "Customer's Full Name";
  export let namePlaceholder = 'Type full name to enable signing';

  const dispatch = createEventDispatcher();

  let canvas;
  let ctx;
  let drawing = false;
  let hasInk = false;
  let last = null;
  let ro; // ResizeObserver

  $: locked = !name.trim();

  function setupCanvas() {
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    // Preserve existing drawing across resize by snapshotting first.
    let prev = null;
    if (hasInk) { try { prev = canvas.toDataURL('image/png'); } catch {} }
    canvas.width = Math.max(1, Math.round(rect.width * dpr));
    canvas.height = Math.max(1, Math.round(rect.height * dpr));
    ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    ctx.lineWidth = 2.4;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = '#0a1a3a';
    if (prev) {
      const img = new Image();
      img.onload = () => ctx.drawImage(img, 0, 0, rect.width, rect.height);
      img.src = prev;
    }
  }

  onMount(() => {
    setupCanvas();
    if (window.ResizeObserver) {
      ro = new ResizeObserver(() => setupCanvas());
      ro.observe(canvas);
    }
  });
  onDestroy(() => { if (ro) ro.disconnect(); });

  function pos(e) {
    const rect = canvas.getBoundingClientRect();
    const t = e.touches && e.touches[0];
    const cx = t ? t.clientX : e.clientX;
    const cy = t ? t.clientY : e.clientY;
    return { x: cx - rect.left, y: cy - rect.top };
  }

  function start(e) {
    if (locked) return;
    e.preventDefault();
    drawing = true;
    last = pos(e);
  }

  function move(e) {
    if (!drawing || locked) return;
    e.preventDefault();
    const p = pos(e);
    ctx.beginPath();
    ctx.moveTo(last.x, last.y);
    ctx.lineTo(p.x, p.y);
    ctx.stroke();
    last = p;
    hasInk = true;
  }

  function end(e) {
    if (!drawing) return;
    e && e.preventDefault();
    drawing = false;
    if (hasInk) exportSig();
  }

  function exportSig() {
    try {
      signatureData = canvas.toDataURL('image/png');
      dispatch('change', { name, signatureData, hasInk });
    } catch {}
  }

  export function clear() {
    if (!ctx || !canvas) return;
    const rect = canvas.getBoundingClientRect();
    ctx.clearRect(0, 0, rect.width, rect.height);
    hasInk = false;
    signatureData = '';
    dispatch('change', { name, signatureData: '', hasInk: false });
  }

  function onNameInput() {
    dispatch('change', { name, signatureData, hasInk });
  }
</script>

<div class="sig-wrap">
  <label class="sig-name-label">
    {nameLabel}
    <input
      class="sig-name-input"
      bind:value={name}
      on:input={onNameInput}
      placeholder={namePlaceholder}
      autocomplete="name"
    />
  </label>

  <div class="sig-pad-label">
    <span>{label}</span>
    {#if hasInk}<button type="button" class="sig-clear" on:click={clear}>Clear</button>{/if}
  </div>

  <div class="sig-canvas-box" class:locked>
    <canvas
      bind:this={canvas}
      class="sig-canvas"
      on:mousedown={start}
      on:mousemove={move}
      on:mouseup={end}
      on:mouseleave={end}
      on:touchstart={start}
      on:touchmove={move}
      on:touchend={end}
    ></canvas>
    {#if locked}
      <div class="sig-lock-msg">✍️ Type the name above to sign here</div>
    {:else if !hasInk}
      <div class="sig-hint-line">Sign above the line with your finger</div>
    {/if}
    <div class="sig-baseline"></div>
    <span class="sig-x">✕</span>
  </div>
</div>

<style>
  .sig-wrap { margin: 4px 0 6px; }
  .sig-name-label {
    display: block; font-size: 12px; font-weight: 700;
    color: var(--text-secondary, #666); margin-bottom: 10px;
  }
  .sig-name-input {
    display: block; width: 100%; margin-top: 5px; padding: 11px 12px; box-sizing: border-box;
    border: 1px solid var(--border-color, #ddd); border-radius: 9px;
    background: var(--input-bg, #fff); color: var(--text-primary, #111);
    font-size: 16px; font-family: inherit; font-weight: 600;
  }
  .sig-pad-label {
    display: flex; justify-content: space-between; align-items: center;
    font-size: 12px; font-weight: 700; color: var(--text-secondary, #666); margin-bottom: 5px;
  }
  .sig-clear {
    border: none; background: transparent; color: var(--accent, #cc0000);
    font-weight: 700; font-size: 12px; cursor: pointer; padding: 2px 4px;
  }
  .sig-canvas-box {
    position: relative; width: 100%; height: 160px;
    border: 2px dashed var(--border-color, #cbd0d8); border-radius: 12px;
    background: var(--input-bg, #fff); overflow: hidden;
    touch-action: none;
  }
  .sig-canvas-box.locked { background: var(--border-color, #f0f0f2); opacity: 0.85; }
  .sig-canvas { position: absolute; inset: 0; width: 100%; height: 100%; display: block; cursor: crosshair; }
  .sig-baseline {
    position: absolute; left: 34px; right: 18px; bottom: 34px;
    border-bottom: 2px solid var(--text-tertiary, #b5b5b5); pointer-events: none;
  }
  .sig-x {
    position: absolute; left: 16px; bottom: 26px; font-size: 16px;
    color: var(--text-tertiary, #b5b5b5); pointer-events: none; font-weight: 700;
  }
  .sig-lock-msg, .sig-hint-line {
    position: absolute; left: 0; right: 0; top: 42%;
    text-align: center; font-size: 13px; color: var(--text-tertiary, #9aa0a8);
    pointer-events: none; font-weight: 600;
  }
  .sig-hint-line { color: var(--text-tertiary, #c2c2c2); font-weight: 500; }
</style>
