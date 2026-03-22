<script>
  import { createEventDispatcher } from 'svelte';
  import { error, setLoading, setUser } from '../lib/stores.js';

  const dispatch = createEventDispatcher();

  import { onMount } from 'svelte';

  let selectedRep = '';
  let isLoading = true;
  let reps = [];

  onMount(async () => {
    try {
      const response = await fetch('/data/rep_registry.json');
      const data = await response.json();
      
      // Convert object format to array
      reps = Object.entries(data).map(([id, rep]) => ({
        id: id,
        name: rep.display_name || rep.contract_name,
        role: rep.role || 'rep',
        base_location: rep.base_location || ''
      }));
      
      // Sort: managers first, then alphabetical
      reps.sort((a, b) => {
        if (a.role === 'manager' && b.role !== 'manager') return -1;
        if (b.role === 'manager' && a.role !== 'manager') return 1;
        return a.name.localeCompare(b.name);
      });
      
      console.log(`Loaded ${reps.length} reps`);
    } catch (err) {
      console.error('Failed to load reps:', err);
      // Fallback
      reps = [
        { id: '1', name: 'Tyler Van Sant', role: 'manager', base_location: 'Ridgefield, WA' }
      ];
    } finally {
      isLoading = false;
    }
  });

  function handleLogin() {
    if (!selectedRep || selectedRep === '') {
      $error = 'Please select a representative';
      return;
    }

    const rep = reps.find(r => r.id === selectedRep);
    
    if (rep) {
      console.log('Login SUCCESS:', rep.name);
      setUser(rep);
    } else {
      $error = 'Representative not found';
    }
  }
</script>

<div class="login-container">
  <div class="login-card">
    <div class="logo">IM</div>
    <h1>IndoorMedia</h1>
    <p class="subtitle">Sales Portal</p>

    <form on:submit|preventDefault={handleLogin}>
      <div class="form-group">
        <label for="rep-select">Select Your Name:</label>
        <select
          id="rep-select"
          bind:value={selectedRep}
          disabled={isLoading}
        >
          <option value="">-- Choose a representative --</option>
          {#each reps as rep (rep.id)}
            <option value={rep.id}>
              {rep.name} — {rep.base_location}
            </option>
          {/each}
        </select>
      </div>

      {#if $error}
        <div class="error-message">{$error}</div>
      {/if}

      <button type="submit" disabled={selectedRep === '' || isLoading}>
        {isLoading ? 'Loading...' : 'Sign In'}
      </button>
    </form>

    <div class="footer">
      <p>Rep Portal v1.0</p>
    </div>
  </div>
</div>

<style>
  .login-container {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #CC0000 0%, #1a1a1a 100%);
    padding: 20px;
  }

  .login-card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
    padding: 40px;
    width: 100%;
    max-width: 400px;
    text-align: center;
  }

  .logo {
    width: 80px;
    height: 80px;
    margin: 0 auto 20px;
    background: #CC0000;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 40px;
    font-weight: bold;
    color: white;
  }

  h1 {
    margin: 0 0 5px;
    color: #1a1a1a;
    font-size: 28px;
  }

  .subtitle {
    margin: 0 0 30px;
    color: #666;
    font-size: 14px;
  }

  .form-group {
    margin-bottom: 20px;
    text-align: left;
  }

  label {
    display: block;
    margin-bottom: 8px;
    font-weight: 500;
    color: #333;
    font-size: 14px;
  }

  select {
    width: 100%;
    padding: 12px;
    border: 2px solid #ddd;
    border-radius: 6px;
    font-size: 14px;
    font-family: inherit;
    cursor: pointer;
    transition: border-color 0.3s;
  }

  select:hover {
    border-color: #CC0000;
  }

  select:focus {
    outline: none;
    border-color: #CC0000;
    box-shadow: 0 0 0 3px rgba(255, 107, 53, 0.1);
  }

  select:disabled {
    background: #f5f5f5;
    cursor: not-allowed;
    color: #999;
  }

  button {
    width: 100%;
    padding: 12px;
    background: #CC0000;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.3s, transform 0.1s;
  }

  button:hover:not(:disabled) {
    background: #990000;
    transform: translateY(-2px);
  }

  button:active:not(:disabled) {
    transform: translateY(0);
  }

  button:disabled {
    background: #ccc;
    cursor: not-allowed;
  }

  .error-message {
    background: #fee;
    color: #c33;
    padding: 12px;
    border-radius: 6px;
    margin-bottom: 15px;
    font-size: 14px;
  }

  .footer {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid #eee;
    color: #999;
    font-size: 12px;
  }

  @media (max-width: 480px) {
    .login-card {
      padding: 30px 20px;
    }

    h1 {
      font-size: 24px;
    }

    .logo {
      width: 60px;
      height: 60px;
      font-size: 32px;
    }
  }
</style>
