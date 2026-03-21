<script>
  import { onMount } from 'svelte';
  import Login from './components/Login.svelte';
  import Main from './components/Main.svelte';
  import { currentUser, setUser } from './lib/stores.js';

  function handleLogin(event) {
    console.log('[App] handleLogin called with:', event.detail);
    setUser(event.detail);
  }

  function handleLogout() {
    console.log('[App] handleLogout called');
    setUser(null);
  }

  onMount(() => {
    // Check localStorage on mount
    const saved = localStorage.getItem('user');
    if (saved) {
      console.log('[App] Restoring user from localStorage:', saved);
      setUser(JSON.parse(saved));
    }
  });
</script>

<main>
  {#if $currentUser}
    <Main user={$currentUser} on:logout={handleLogout} />
  {:else}
    <Login on:login={handleLogin} />
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
