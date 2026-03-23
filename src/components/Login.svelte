<script>
  import { createEventDispatcher } from 'svelte';
  import { error, setUser } from '../lib/stores.js';

  let selectedRep = '';
  let isLoading = true;
  let reps = [];

  import { onMount } from 'svelte';

  onMount(async () => {
    try {
      const response = await fetch('/data/rep_registry.json');
      const data = await response.json();
      
      reps = Object.entries(data).map(([id, rep]) => ({
        id: id,
        name: rep.display_name || rep.contract_name,
        role: rep.role || 'rep',
        base_location: rep.base_location || 'Territory TBD'
      }));
      
      reps.sort((a, b) => {
        if (a.role === 'manager' && b.role !== 'manager') return -1;
        if (b.role === 'manager' && a.role !== 'manager') return 1;
        return a.name.localeCompare(b.name);
      });
      
      console.log(`Loaded ${reps.length} reps`);
    } catch (err) {
      console.error('Failed to load reps:', err);
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

<div class="login-page">
  <div class="login-wrapper">
    <!-- Logo Section -->
    <div class="logo-section">
      <img src="/logo.jpg" alt="IndoorMedia" class="logo-img" />
      <h2 class="app-name">imPro</h2>
    </div>

    <!-- Content -->
    <div class="login-content">
      <h1>Sales Portal</h1>
      <p class="subtitle">Select your profile to continue</p>

      <form on:submit|preventDefault={handleLogin} class="login-form">
        <div class="form-group">
          <label for="rep-select">Representative</label>
          <div class="select-wrapper">
            <select
              id="rep-select"
              bind:value={selectedRep}
              disabled={isLoading}
              class="rep-select"
            >
              <option value="">Choose your name...</option>
              {#each reps as rep (rep.id)}
                <option value={rep.id}>
                  {rep.name}
                </option>
              {/each}
            </select>
            <span class="select-icon">▼</span>
          </div>
          
          {#if selectedRep}
            <div class="rep-details">
              <p class="location">📍 {reps.find(r => r.id === selectedRep)?.base_location}</p>
            </div>
          {/if}
        </div>

        {#if $error}
          <div class="error-message">
            <span class="error-icon">⚠️</span>
            {$error}
          </div>
        {/if}

        <button 
          type="submit" 
          disabled={selectedRep === '' || isLoading}
          class="signin-button"
        >
          {isLoading ? '⏳ Loading...' : '→ Sign In'}
        </button>
      </form>
    </div>

    <!-- Footer -->
    <div class="login-footer">
      <p class="version">imPro v2.0</p>
      <p class="tagline">IndoorMedia Sales Portal</p>
    </div>
  </div>
</div>

<style>
  .login-page {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #CC0000 0%, #1a1a1a 100%);
    min-height: 100vh;
    padding: 20px;
  }

  .login-wrapper {
    background: white;
    border-radius: 20px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    width: 100%;
    max-width: 420px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  /* Logo Section */
  .logo-section {
    background: linear-gradient(135deg, #CC0000 0%, #990000 100%);
    padding: 40px 20px;
    text-align: center;
    color: white;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
  }

  .logo-img {
    width: 140px;
    height: 140px;
    object-fit: contain;
  }

  .app-name {
    margin: 0;
    font-size: 24px;
    font-weight: 700;
    letter-spacing: -0.5px;
  }

  /* Content */
  .login-content {
    padding: 40px;
    flex: 1;
  }

  h1 {
    margin: 0 0 8px;
    font-size: 28px;
    color: #1a1a1a;
    font-weight: 700;
  }

  .subtitle {
    margin: 0 0 30px;
    color: #666;
    font-size: 14px;
  }

  /* Form */
  .login-form {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  label {
    font-weight: 600;
    font-size: 13px;
    color: #333;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .select-wrapper {
    position: relative;
  }

  .rep-select {
    width: 100%;
    padding: 12px 14px;
    border: 2px solid #ddd;
    border-radius: 10px;
    font-size: 15px;
    font-family: inherit;
    background: white;
    color: #1a1a1a;
    cursor: pointer;
    transition: all 0.2s;
    appearance: none;
    padding-right: 40px;
  }

  .rep-select:hover {
    border-color: #CC0000;
  }

  .rep-select:focus {
    outline: none;
    border-color: #CC0000;
    box-shadow: 0 0 0 3px rgba(204, 0, 0, 0.1);
  }

  .select-icon {
    position: absolute;
    right: 14px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 12px;
    color: #999;
    pointer-events: none;
  }

  .rep-details {
    margin-top: 8px;
    padding: 10px;
    background: #f9f9f9;
    border-radius: 8px;
    border-left: 3px solid #CC0000;
  }

  .location {
    margin: 0;
    font-size: 13px;
    color: #666;
  }

  /* Error */
  .error-message {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px;
    background: #ffebee;
    border: 1px solid #ffcdd2;
    border-radius: 8px;
    color: #c62828;
    font-size: 13px;
    font-weight: 500;
  }

  .error-icon {
    font-size: 16px;
  }

  /* Button */
  .signin-button {
    background: linear-gradient(135deg, #CC0000 0%, #990000 100%);
    color: white;
    border: none;
    padding: 14px;
    border-radius: 10px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    box-shadow: 0 4px 12px rgba(204, 0, 0, 0.3);
  }

  .signin-button:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(204, 0, 0, 0.4);
  }

  .signin-button:active:not(:disabled) {
    transform: translateY(0);
  }

  .signin-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  /* Footer */
  .login-footer {
    background: #f9f9f9;
    padding: 20px;
    text-align: center;
    border-top: 1px solid #eee;
  }

  .version {
    margin: 0 0 4px;
    font-size: 12px;
    font-weight: 600;
    color: #CC0000;
  }

  .tagline {
    margin: 0;
    font-size: 11px;
    color: #999;
  }

  @media (max-width: 480px) {
    .login-wrapper {
      max-width: 100%;
      border-radius: 12px;
    }

    .logo-section {
      padding: 30px 20px;
    }

    .logo {
      width: 100px;
      height: 100px;
    }

    .login-content {
      padding: 30px 20px;
    }

    h1 {
      font-size: 24px;
    }

    .signin-button {
      padding: 12px;
      font-size: 14px;
    }
  }
</style>
