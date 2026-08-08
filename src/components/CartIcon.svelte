<script>
  // Shared shopping-cart icon so every cart icon in the app matches the one in
  // the header (Main.svelte). Same Feather-style cart SVG.
  export let size = 18;        // px
  export let color = 'currentColor';
  export let strokeWidth = 2;
</script>

<svg
  class="cart-icon"
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
  <circle cx="9" cy="21" r="1" />
  <circle cx="20" cy="21" r="1" />
  <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
</svg>

<style>
  .cart-icon {
    display: inline-block;
    vertical-align: -0.15em;
    flex-shrink: 0;
  }
</style>
