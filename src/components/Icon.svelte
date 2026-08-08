<script>
  // Shared Feather-style line icons so button icons across the app match the
  // clean cart icon in the header (see CartIcon.svelte). Same 24x24 viewBox,
  // 2px round stroke, currentColor by default.
  export let name = '';
  export let size = 18;
  export let color = 'currentColor';
  export let strokeWidth = 2;
</script>

<svg
  class="app-icon"
  width={size}
  height={size}
  viewBox="0 0 24 24"
  fill="none"
  stroke={color}
  stroke-width={strokeWidth}
  stroke-linecap="round"
  stroke-linejoin="round"
  aria-hidden="true"
  focusable="false"
>
  {#if name === 'target'}
    <circle cx="12" cy="12" r="10" />
    <circle cx="12" cy="12" r="6" />
    <circle cx="12" cy="12" r="2" />
  {:else if name === 'compass'}
    <circle cx="12" cy="12" r="10" />
    <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
  {:else if name === 'receipt'}
    <!-- register-tape / receipt -->
    <path d="M6 2h12v20l-3-2-3 2-3-2-3 2V2z" />
    <line x1="9" y1="7" x2="15" y2="7" />
    <line x1="9" y1="11" x2="15" y2="11" />
    <line x1="9" y1="15" x2="13" y2="15" />
  {:else if name === 'smartphone'}
    <rect x="6" y="2" width="12" height="20" rx="2" ry="2" />
    <line x1="11" y1="18" x2="13" y2="18" />
  {:else if name === 'lock'}
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  {:else if name === 'x'}
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  {/if}
</svg>

<style>
  .app-icon {
    display: inline-block;
    vertical-align: -0.15em;
    flex-shrink: 0;
  }
</style>
