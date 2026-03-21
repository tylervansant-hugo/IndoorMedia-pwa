<script>
  import Login from './components/Login.svelte';
  import Main from './components/Main.svelte';
  import { currentUser, setUser } from './lib/stores.js';

  let user = null;

  currentUser.subscribe(value => {
    user = value;
  });

  function handleLogin(event) {
    console.log('[App] handleLogin called with:', event.detail);
    setUser(event.detail);
    console.log('[App] User set, current user:', user);
  }

  function handleLogout() {
    setUser(null);
  }
</script>

<main>
  {#if user}
    <Main {user} on:logout={handleLogout} />
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
