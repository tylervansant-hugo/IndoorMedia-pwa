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
  });
</script>

<main>
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
</style>
