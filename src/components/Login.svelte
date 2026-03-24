<script>
  import { createEventDispatcher } from 'svelte';
  import { error, setUser } from '../lib/stores.js';

  let selectedRep = '';
  let isLoading = true;
  let reps = [];
  let showRegister = false;
  let newRep = { name: '', email: '', location: '' };
  let registerSuccess = '';
  let registerError = '';

  import { onMount } from 'svelte';

  onMount(async () => {
    await loadReps();
  });

  async function loadReps() {
    try {
      const response = await fetch('/data/rep_registry.json');
      const data = await response.json();

      // Merge locally registered reps
      const localReps = JSON.parse(localStorage.getItem('local_reps') || '{}');
      const merged = { ...data, ...localReps };
      
      reps = Object.entries(merged).map(([id, rep]) => ({
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
      
      console.log(`Loaded ${reps.length} reps (${Object.keys(localReps).length} local)`);
    } catch (err) {
      console.error('Failed to load reps:', err);
      reps = [
        { id: '1', name: 'Tyler Van Sant', role: 'manager', base_location: 'Ridgefield, WA' }
      ];
    } finally {
      isLoading = false;
    }
  }

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

  async function handleRegister() {
    registerError = '';
    registerSuccess = '';

    if (!newRep.name.trim()) {
      registerError = 'Please enter your full name';
      return;
    }

    // Create a simple ID from the name
    const repId = newRep.name.trim().toLowerCase().replace(/\s+/g, '_');

    // Check for duplicates
    const exists = reps.find(r => 
      r.name.toLowerCase() === newRep.name.trim().toLowerCase() ||
      r.id === repId
    );
    if (exists) {
      registerError = 'A rep with this name already exists. Please select from the list.';
      return;
    }

    try {
      // Fetch current registry
      const response = await fetch('/data/rep_registry.json');
      const registry = await response.json();

      // Add new rep
      registry[repId] = {
        contract_name: newRep.name.trim(),
        display_name: newRep.name.trim(),
        email: newRep.email.trim() || '',
        role: 'rep',
        registered_at: new Date().toISOString().split('T')[0],
        base_location: newRep.location.trim() || 'Territory TBD'
      };

      // Save to localStorage as pending registration
      // (Can't write to server from static site, so we store locally)
      const pending = JSON.parse(localStorage.getItem('pending_registrations') || '[]');
      pending.push(registry[repId]);
      localStorage.setItem('pending_registrations', JSON.stringify(pending));

      // Add to local reps list immediately so they can sign in
      const localReps = JSON.parse(localStorage.getItem('local_reps') || '{}');
      localReps[repId] = registry[repId];
      localStorage.setItem('local_reps', JSON.stringify(localReps));

      // Add to current reps list
      reps = [...reps, {
        id: repId,
        name: newRep.name.trim(),
        role: 'rep',
        base_location: newRep.location.trim() || 'Territory TBD'
      }].sort((a, b) => {
        if (a.role === 'manager' && b.role !== 'manager') return -1;
        if (b.role === 'manager' && a.role !== 'manager') return 1;
        return a.name.localeCompare(b.name);
      });

      registerSuccess = `✅ Welcome, ${newRep.name.trim()}! You can now sign in.`;
      selectedRep = repId;
      
      // Reset form after delay
      setTimeout(() => {
        showRegister = false;
        registerSuccess = '';
      }, 2000);

    } catch (err) {
      registerError = 'Registration failed. Please try again.';
      console.error('Registration error:', err);
    }
  }
</script>

<div class="login-page">
  <div class="login-wrapper">
    <!-- Logo Section -->
    <div class="logo-section">
      <img src="/logo.png?v=2" alt="IndoorMedia" class="logo-img" />
      <p class="pro-text">pro</p>
    </div>

    <!-- Content -->
    <div class="login-content">
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

      <div class="divider">
        <span>or</span>
      </div>

      {#if !showRegister}
        <button class="register-toggle" on:click={() => showRegister = true}>
          + New Rep? Register Here
        </button>
      {:else}
        <div class="register-form">
          <h3>New Rep Registration</h3>
          
          <div class="form-group">
            <label for="reg-name">Full Name *</label>
            <input 
              id="reg-name"
              type="text" 
              placeholder="e.g. John Smith"
              bind:value={newRep.name}
              class="reg-input"
            />
          </div>

          <div class="form-group">
            <label for="reg-email">Email</label>
            <input 
              id="reg-email"
              type="email" 
              placeholder="e.g. john.smith@indoormedia.com"
              bind:value={newRep.email}
              class="reg-input"
            />
          </div>

          <div class="form-group">
            <label for="reg-location">Territory / Base City</label>
            <input 
              id="reg-location"
              type="text" 
              placeholder="e.g. Portland, OR"
              bind:value={newRep.location}
              class="reg-input"
            />
          </div>

          {#if registerError}
            <div class="error-message">
              <span class="error-icon">⚠️</span>
              {registerError}
            </div>
          {/if}

          {#if registerSuccess}
            <div class="success-message">
              {registerSuccess}
            </div>
          {/if}

          <button class="register-btn" on:click={handleRegister} disabled={!newRep.name.trim()}>
            ✅ Register & Sign In
          </button>

          <button class="cancel-link" on:click={() => { showRegister = false; registerError = ''; }}>
            ← Back to Sign In
          </button>
        </div>
      {/if}
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
    background: #CC0000;
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

  .pro-text {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    color: white;
    font-style: italic;
    letter-spacing: 1px;
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

  /* Divider */
  .divider {
    display: flex;
    align-items: center;
    margin: 24px 0;
    gap: 12px;
  }

  .divider::before, .divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #e0e0e0;
  }

  .divider span {
    font-size: 12px;
    color: #999;
    text-transform: uppercase;
    letter-spacing: 1px;
  }

  /* Register Toggle */
  .register-toggle {
    width: 100%;
    padding: 12px;
    background: none;
    border: 2px dashed #CC0000;
    border-radius: 10px;
    color: #CC0000;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .register-toggle:hover {
    background: #fff5f5;
  }

  /* Register Form */
  .register-form {
    background: #f9f9f9;
    border-radius: 12px;
    padding: 20px;
    border: 1px solid #e0e0e0;
  }

  .register-form h3 {
    margin: 0 0 16px;
    font-size: 18px;
    color: #333;
    font-weight: 700;
  }

  .reg-input {
    width: 100%;
    padding: 12px 14px;
    border: 2px solid #ddd;
    border-radius: 10px;
    font-size: 15px;
    font-family: inherit;
    background: white;
    color: #1a1a1a;
    transition: all 0.2s;
    box-sizing: border-box;
  }

  .reg-input:focus {
    outline: none;
    border-color: #CC0000;
    box-shadow: 0 0 0 3px rgba(204, 0, 0, 0.1);
  }

  .register-btn {
    width: 100%;
    padding: 14px;
    background: linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%);
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s;
    margin-top: 8px;
    box-shadow: 0 4px 12px rgba(46, 125, 50, 0.3);
  }

  .register-btn:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(46, 125, 50, 0.4);
  }

  .register-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .cancel-link {
    width: 100%;
    padding: 10px;
    background: none;
    border: none;
    color: #666;
    font-size: 13px;
    cursor: pointer;
    margin-top: 8px;
    text-decoration: underline;
  }

  .cancel-link:hover {
    color: #CC0000;
  }

  .success-message {
    padding: 12px;
    background: #e8f5e9;
    border: 1px solid #a5d6a7;
    border-radius: 8px;
    color: #2e7d32;
    font-size: 13px;
    font-weight: 600;
    text-align: center;
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
