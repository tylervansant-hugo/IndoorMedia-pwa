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
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    background: #f5f5f5;
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
  }
</style>
