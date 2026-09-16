<script>
  import { onMount } from 'svelte';
  import Login from './components/Login.svelte';
  import Main from './components/Main.svelte';
  import { currentUser, setUser } from './lib/stores.js';

  function handleLogin(event) {
    console.log('[App] handleLogin - event:', event);
    console.log('[App] handleLogin - event.detail:', event.detail);
    setUser(event.detail);
    console.log('[App] handleLogin - setUser completed');
  }

  function handleLogout() {
    console.log('[App] handleLogout called');
    setUser(null);
  }

  // ---- PWA install prompt state ----
  let deferredPrompt = null;
  let showInstall = false;

  function isStandalone() {
    return (
      window.matchMedia('(display-mode: standalone)').matches ||
      window.matchMedia('(display-mode: minimal-ui)').matches ||
      window.navigator.standalone === true
    );
  }

  async function installApp() {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    try {
      const { outcome } = await deferredPrompt.userChoice;
      console.log('[PWA] install outcome:', outcome);
    } catch (e) {}
    deferredPrompt = null;
    showInstall = false;
  }

  function dismissInstall() {
    showInstall = false;
    try { localStorage.setItem('pwa_install_dismissed', String(Date.now())); } catch (e) {}
  }

  onMount(() => {
    // Check localStorage on mount
    console.log('[App] onMount - checking localStorage');
    const saved = localStorage.getItem('user');
    console.log('[App] localStorage.getItem("user"):', saved);
    
    if (saved) {
      try {
        const user = JSON.parse(saved);
        console.log('[App] Parsed user:', user);
        setUser(user);
        console.log('[App] setUser called');
      } catch (e) {
        console.error('[App] Error parsing localStorage user:', e);
      }
    } else {
      console.log('[App] No user in localStorage');
    }

    // PWA install prompt wiring
    if (isStandalone()) return; // already installed/running as app

    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      deferredPrompt = e;
      // respect a recent dismissal (24h)
      let dismissed = 0;
      try { dismissed = parseInt(localStorage.getItem('pwa_install_dismissed') || '0', 10); } catch (e2) {}
      if (!dismissed || (Date.now() - dismissed) > 24 * 60 * 60 * 1000) {
        showInstall = true;
      }
    });

    window.addEventListener('appinstalled', () => {
      showInstall = false;
      deferredPrompt = null;
      console.log('[PWA] app installed');
    });
  });
</script>

<main>
  {#if showInstall}
    <div class="pwa-install-banner">
      <span class="pwa-install-icon">📲</span>
      <div class="pwa-install-text">
        <strong>Install IndoorMedia</strong>
        <span>Open fullscreen with no browser bar</span>
      </div>
      <button class="pwa-install-btn" on:click={installApp}>Install</button>
      <button class="pwa-install-close" on:click={dismissInstall} aria-label="Dismiss">✕</button>
    </div>
  {/if}

  {#if $currentUser}
    <Main user={$currentUser} on:logout={handleLogout} />
  {:else}
    <Login />
  {/if}
</main>

<style>
  :global(html) {
    /* status-bar / safe-area strip sits above the always-dark header, so keep
       it black to match the header (was showing a white bar in dark mode) */
    background: #000000;
  }
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    /* theme-aware (was hardcoded #f5f5f5, which showed as a white bar in dark mode) */
    background: var(--bg-primary, #ededf0);
  }

  :global(*) {
    box-sizing: border-box;
  }

  main {
    width: 100%;
    height: 100vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    background: var(--bg-primary, #ededf0);
  }

  .pwa-install-banner {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    padding-top: calc(10px + env(safe-area-inset-top));
    background: #CC0000;
    color: #fff;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    z-index: 9999;
    flex-shrink: 0;
  }
  .pwa-install-icon {
    font-size: 24px;
    line-height: 1;
  }
  .pwa-install-text {
    display: flex;
    flex-direction: column;
    line-height: 1.2;
    flex: 1;
    min-width: 0;
  }
  .pwa-install-text strong { font-size: 14px; }
  .pwa-install-text span { font-size: 11px; opacity: 0.9; }
  .pwa-install-btn {
    background: #fff;
    color: #CC0000;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 700;
    font-size: 14px;
    cursor: pointer;
    flex-shrink: 0;
  }
  .pwa-install-btn:active { transform: scale(0.96); }
  .pwa-install-close {
    background: transparent;
    border: none;
    color: #fff;
    font-size: 16px;
    padding: 4px 6px;
    cursor: pointer;
    opacity: 0.85;
    flex-shrink: 0;
  }
</style>
