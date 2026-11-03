<script>
  // Walkthrough.svelte — "How to use imPRO" welcome carousel.
  //
  // A full-screen, swipeable intro overlay that orients a new rep on the 5
  // tabs + key flows. Shown automatically on first login (gated by the
  // `impro_seen_walkthrough` localStorage key) and re-openable any time from
  // Tools → Help / Walkthrough.
  //
  // Self-contained + theme-aware: it reuses the global Liquid Glass tokens
  // (--glass-fill, --accent, --text-primary, etc.) so it matches whatever
  // theme/surface the rep has selected, with safe fallbacks.
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';

  export let open = false;

  const dispatch = createEventDispatcher();
  const SEEN_KEY = 'impro_seen_walkthrough';

  // The slides. Keep copy punchy — one job per screen. Icons map to the real
  // bottom-nav tabs + the counter-sign flow.
  const slides = [
    {
      logo: true,
      title: 'Welcome to imPRO',
      body: 'Your all-in-one field toolkit — find prospects, present rates, close deals, and manage clients right from your phone. Here\u2019s the 60-second tour.',
    },
    {
      icon: '🏠',
      title: 'Home',
      body: 'Your cockpit. See today\u2019s goals, revenue, call-in leads, and recent activity at a glance. Tap \u201cEdit Home\u201d to rearrange or hide cards however you like.',
    },
    {
      icon: '🎯',
      title: 'Prospect',
      body: 'Search the full store network, pull up any store\u2019s rates, cycle, and details, and work your saved, imported, and call-in leads — all from the Prospect tab.',
    },
    {
      icon: '📊',
      title: 'Products',
      body: 'Walk a business through pricing, ROI, and sample ads on the spot. Everything you need to make the pitch — no printouts required.',
    },
    {
      icon: '👥',
      title: 'Clients',
      body: 'Keep your book of business in one place — your customers, their contracts, renewals, and history, ready whenever you need them.',
    },
    {
      icon: '🛠️',
      title: 'Tools & Training',
      body: 'ROI calculator, sales scripts, testimonials, the training library, appearance themes, and the \u201cShare / Install App\u201d QR code all live here. It\u2019s also where you\u2019ll Counter-Sign — generate and sign contracts step-by-step to close right on the counter.',
    },
    {
      icon: '🚀',
      title: 'You\u2019re all set!',
      body: 'That\u2019s the tour. You can replay it anytime from Tools \u2192 How to Use imPRO. Now go close some deals.',
    },
  ];

  let index = 0;
  $: last = index === slides.length - 1;
  $: first = index === 0;

  function next() {
    if (last) { finish(); return; }
    index = Math.min(index + 1, slides.length - 1);
  }
  function prev() {
    index = Math.max(index - 1, 0);
  }
  function goTo(i) { index = i; }

  function finish() {
    try { localStorage.setItem(SEEN_KEY, '1'); } catch (_) {}
    index = 0;
    dispatch('close');
  }
  // "Skip" and "Done" both mark seen + close. Keeping them distinct lets us
  // label the buttons differently without changing behavior.
  const skip = finish;

  // --- Swipe handling (touch) ---
  let startX = 0;
  let dx = 0;
  let swiping = false;
  function onTouchStart(e) { startX = e.touches[0].clientX; dx = 0; swiping = true; }
  function onTouchMove(e) { if (swiping) dx = e.touches[0].clientX - startX; }
  function onTouchEnd() {
    if (!swiping) return;
    if (dx < -50) next();
    else if (dx > 50) prev();
    swiping = false; dx = 0;
  }

  // Keyboard arrows for desktop testing.
  function onKey(e) {
    if (!open) return;
    if (e.key === 'ArrowRight') next();
    else if (e.key === 'ArrowLeft') prev();
    else if (e.key === 'Escape') skip();
  }
  onMount(() => { if (typeof window !== 'undefined') window.addEventListener('keydown', onKey); });
  onDestroy(() => { if (typeof window !== 'undefined') window.removeEventListener('keydown', onKey); });

  // Reset to the first slide each time it (re)opens.
  $: if (open) { /* no-op; index reset on finish */ }
</script>

{#if open}
  <div class="wt-backdrop" on:click|self={skip} role="dialog" aria-modal="true" aria-label="How to use imPRO">
    <div
      class="wt-card"
      on:touchstart|passive={onTouchStart}
      on:touchmove|passive={onTouchMove}
      on:touchend={onTouchEnd}
    >
      <button class="wt-skip" on:click={skip} aria-label="Skip walkthrough">Skip ✕</button>

      <div class="wt-stage">
        {#key index}
          <div class="wt-slide">
            {#if slides[index].logo}
              <div class="wt-logo-row">
                <div class="wt-logo-backdrop">
                  <img src="{import.meta.env.BASE_URL}logo.png?v=2" alt="IndoorMedia" class="wt-logo-img" />
                </div>
                <span class="wt-logo-text">imPro</span>
              </div>
            {:else}
              <div class="wt-icon">{slides[index].icon}</div>
            {/if}
            <h2 class="wt-title">{slides[index].title}</h2>
            <p class="wt-body">{slides[index].body}</p>
          </div>
        {/key}
      </div>

      <div class="wt-dots" role="tablist">
        {#each slides as _, i}
          <button
            class="wt-dot"
            class:active={i === index}
            on:click={() => goTo(i)}
            aria-label={`Go to step ${i + 1}`}
          ></button>
        {/each}
      </div>

      <div class="wt-nav">
        <button class="wt-btn ghost" on:click={prev} disabled={first}>← Back</button>
        <span class="wt-count">{index + 1} / {slides.length}</span>
        <button class="wt-btn primary" on:click={next}>{last ? 'Get Started 🚀' : 'Next →'}</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .wt-backdrop {
    position: fixed;
    inset: 0;
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    background: rgba(0, 0, 0, 0.55);
    backdrop-filter: blur(6px) saturate(1.1);
    -webkit-backdrop-filter: blur(6px) saturate(1.1);
    animation: wt-fade 0.2s ease;
  }
  @keyframes wt-fade { from { opacity: 0; } to { opacity: 1; } }

  .wt-card {
    position: relative;
    width: 100%;
    max-width: 420px;
    border-radius: 24px;
    padding: 28px 24px 22px;
    box-sizing: border-box;
    background:
      linear-gradient(var(--glass-fill, rgba(255,255,255,0.72)), var(--glass-fill, rgba(255,255,255,0.72))),
      var(--header-bg, linear-gradient(135deg, var(--accent, #CC0000), #990000));
    color: var(--text-primary, #1a1a1a);
    border: 1px solid var(--glass-border, rgba(255,255,255,0.4));
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.35);
    backdrop-filter: blur(22px) saturate(1.3);
    -webkit-backdrop-filter: blur(22px) saturate(1.3);
    animation: wt-pop 0.25s cubic-bezier(0.2, 0.8, 0.2, 1);
  }
  @keyframes wt-pop { from { transform: translateY(14px) scale(0.97); opacity: 0; } to { transform: none; opacity: 1; } }

  .wt-skip {
    position: absolute;
    top: 14px;
    right: 14px;
    background: var(--glass-fill-strong, rgba(0,0,0,0.06));
    color: var(--text-secondary, #666);
    border: none;
    border-radius: 999px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
  }
  .wt-skip:hover { filter: brightness(0.95); }

  .wt-stage {
    min-height: 260px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 18px 4px 6px;
  }
  .wt-slide { animation: wt-slidein 0.3s ease; }
  @keyframes wt-slidein { from { opacity: 0; transform: translateX(16px); } to { opacity: 1; transform: none; } }

  .wt-icon {
    font-size: 64px;
    line-height: 1;
    margin-bottom: 16px;
    filter: drop-shadow(0 6px 14px rgba(0,0,0,0.18));
  }
  .wt-logo-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    margin-bottom: 18px;
  }
  .wt-logo-backdrop {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 64px;
    height: 64px;
    border-radius: 16px;
    background: #fff;
    box-shadow: 0 6px 16px rgba(0,0,0,0.18);
  }
  .wt-logo-img {
    width: 52px;
    height: 52px;
    object-fit: contain;
  }
  .wt-logo-text {
    font-size: 34px;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: var(--text-primary, #1a1a1a);
  }
  .wt-title {
    font-size: 24px;
    font-weight: 800;
    margin: 0 0 10px;
    color: var(--text-primary, #1a1a1a);
  }
  .wt-body {
    font-size: 15px;
    line-height: 1.5;
    color: var(--text-secondary, #555);
    margin: 0;
    max-width: 340px;
  }

  .wt-dots {
    display: flex;
    justify-content: center;
    gap: 8px;
    margin: 6px 0 18px;
  }
  .wt-dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    border: none;
    padding: 0;
    background: var(--text-secondary, #bbb);
    opacity: 0.4;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .wt-dot.active {
    opacity: 1;
    width: 22px;
    background: var(--accent, #CC0000);
  }

  .wt-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }
  .wt-count {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary, #888);
    white-space: nowrap;
  }
  .wt-btn {
    border: none;
    border-radius: 14px;
    padding: 12px 18px;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
    transition: transform 0.08s ease, filter 0.15s ease;
  }
  .wt-btn:active { transform: scale(0.97); }
  .wt-btn.primary {
    background: var(--accent, #CC0000);
    color: var(--accent-contrast, #fff);
    box-shadow: 0 6px 16px rgba(0,0,0,0.2);
  }
  .wt-btn.primary:hover { filter: brightness(1.05); }
  .wt-btn.ghost {
    background: var(--glass-fill-strong, rgba(0,0,0,0.05));
    color: var(--text-primary, #333);
  }
  .wt-btn.ghost:disabled { opacity: 0.35; cursor: default; }
</style>
