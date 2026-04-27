<script>
  import { createEventDispatcher } from 'svelte';
  import { error, setUser } from '../lib/stores.js';
  import { logActivity } from '../lib/activity.js';

  let selectedRep = '';
  let isLoading = true;
  let reps = [];
  let showRegister = false;
  let newRep = { name: '', email: '', location: '', code: '' };
  const INVITE_CODE = 'IMPRO';
  let registerSuccess = '';
  let registerError = '';
  
  // Password system
  let password = '';
  let confirmPassword = '';
  let showSetPassword = false;
  let passwordError = '';

  function getPasswords() {
    try {
      const stored = JSON.parse(localStorage.getItem('impro_passwords_v2') || '{}');
      return stored;
    } catch { return {}; }
  }

  function hashPassword(pw) {
    // Simple but reliable hash - works in all browsers, no async needed
    let hash = 0;
    const str = pw + '_impro_salt_2026';
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash |= 0; // Convert to 32bit integer
    }
    return 'pw_' + Math.abs(hash).toString(36);
  }

  function hasPassword(repId) {
    const passwords = getPasswords();
    return !!passwords[repId];
  }

  import { onMount } from 'svelte';

  onMount(async () => {
    await loadReps();
  });

  async function loadReps() {
    try {
      const response = await fetch(import.meta.env.BASE_URL + 'data/rep_registry.json?t=' + Date.now());
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

  async function handleLogin() {
    if (!selectedRep || selectedRep === '') {
      $error = 'Please select a representative';
      return;
    }

    const rep = reps.find(r => r.id === selectedRep);
    if (!rep) {
      $error = 'Representative not found';
      return;
    }

    passwordError = '';
    const passwords = getPasswords();
    
    // Debug: log what we're checking
    console.log('Login attempt for:', selectedRep, 'Has password:', !!passwords[selectedRep], 'All passwords:', Object.keys(passwords));

    // If rep has a password set, verify it
    if (passwords[selectedRep]) {
      if (!password) {
        passwordError = 'Please enter your password';
        return;
      }
      const hashed = hashPassword(password);
      if (hashed !== passwords[selectedRep]) {
        passwordError = 'Incorrect password';
        return;
      }

      // Correct password - log in
      console.log('Password verified, logging in:', selectedRep);
      logActivity('login', { rep: rep.name, role: rep.role });
      setUser({
        id: selectedRep,
        name: rep.name,
        role: rep.role,
        base_location: rep.base_location
      });
      password = '';
      selectedRep = '';
    } else {
      // No password set yet - show setup screen
      console.log('No password found for', selectedRep, '- showing setup screen');
      showSetPassword = true;
    }
  }

  async function handleSetPassword() {
    if (!password || !confirmPassword) {
      passwordError = 'Please fill in both password fields';
      return;
    }
    if (password !== confirmPassword) {
      passwordError = 'Passwords do not match';
      return;
    }
    if (password.length < 4) {
      passwordError = 'Password must be at least 4 characters';
      return;
    }

    // Hash and store password
    const hashed = hashPassword(password);
    const passwords = getPasswords();
    passwords[selectedRep] = hashed;
    const savedJSON = JSON.stringify(passwords);
    localStorage.setItem('impro_passwords_v2', savedJSON);
    
    // Verify it was saved
    const verify = localStorage.getItem('impro_passwords');
    console.log('Password saved for', selectedRep, '- Stored:', savedJSON, '- Verified:', verify);

    // Log in
    const rep = reps.find(r => r.id === selectedRep);
    setUser({
      id: selectedRep,
      name: rep.name,
      role: rep.role,
      base_location: rep.base_location
    });

    password = '';
    confirmPassword = '';
    showSetPassword = false;
    selectedRep = '';
  }

  async function handleRegister() {
    if (!newRep.name || !newRep.email || !newRep.code) {
      registerError = 'Please fill in all fields';
      return;
    }
    if (newRep.code !== INVITE_CODE) {
      registerError = `Invalid invite code (try "${INVITE_CODE}")`;
      return;
    }

    // Create new rep
    const id = Date.now().toString();
    const localReps = JSON.parse(localStorage.getItem('local_reps') || '{}');
    localReps[id] = {
      display_name: newRep.name,
      contract_name: newRep.name,
      email: newRep.email,
      base_location: newRep.location || 'Territory TBD',
      role: 'rep'
    };
    localStorage.setItem('local_reps', JSON.stringify(localReps));

    registerSuccess = `✅ Welcome, ${newRep.name}! Please close this and log in.`;
    newRep = { name: '', email: '', location: '', code: '' };
    
    // Reload reps
    await loadReps();
    setTimeout(() => { showRegister = false; registerSuccess = ''; }, 2000);
  }
</script>

<main class="login-container">
  <div class="login-card">
    <div class="header">
      <img src={import.meta.env.BASE_URL + 'logo.png'} alt="IndoorMedia" class="logo" />
      <p class="tagline">imPro Sales Portal</p>
    </div>

    <div class="login-form">
      {#if !showRegister}
        <h2>Welcome to imPro</h2>
        <p class="subtitle">Select your profile to continue</p>

        {#if $error}
          <div class="error-message">⚠️ {$error}</div>
        {/if}

        {#if isLoading}
          <p class="loading">Loading representatives...</p>
        {:else}
          <div class="form-group">
            <label for="rep-select">Representative</label>
            <select id="rep-select" bind:value={selectedRep} disabled={isLoading}>
              <option value="">Choose your name...</option>
              {#each reps as rep (rep.id)}
                <option value={rep.id}>{rep.name}</option>
              {/each}
            </select>
          </div>

          {#if selectedRep && showSetPassword}
            <div class="password-setup">
              <h3>Set Your Password</h3>
              <p class="subtitle">Create a secure password for {reps.find(r => r.id === selectedRep)?.name}</p>
              
              {#if passwordError}
                <div class="error-message">{passwordError}</div>
              {/if}

              <div class="form-group">
                <label for="new-password">Password</label>
                <input
                  id="new-password"
                  type="password"
                  placeholder="Enter a password"
                  bind:value={password}
                />
              </div>

              <div class="form-group">
                <label for="confirm-password">Confirm Password</label>
                <input
                  id="confirm-password"
                  type="password"
                  placeholder="Re-enter password"
                  bind:value={confirmPassword}
                />
              </div>

              <button class="login-btn" on:click={handleSetPassword}>
                Create Password & Sign In
              </button>

              <button class="cancel-btn" on:click={() => { showSetPassword = false; password = ''; confirmPassword = ''; }}>
                Cancel
              </button>
            </div>
          {:else if selectedRep && !showSetPassword}
            <div class="form-group">
              <label for="password">Password</label>
              <input
                id="password"
                type="password"
                placeholder="Your password"
                bind:value={password}
              />
              {#if passwordError}
                <p class="error-text">{passwordError}</p>
              {/if}
            </div>

            <button class="login-btn" on:click={handleLogin} disabled={!password}>
              → Sign In
            </button>
          {/if}
        {/if}

        <p class="or-divider">— or —</p>

        <button class="register-btn" on:click={() => { showRegister = true; registerError = ''; }}>
          + New Rep? Register Here
        </button>
      {:else}
        <h2>Register New Representative</h2>
        <p class="subtitle">Join the imPro team</p>

        {#if registerSuccess}
          <div class="success-message">{registerSuccess}</div>
        {/if}

        {#if registerError}
          <div class="error-message">⚠️ {registerError}</div>
        {/if}

        <div class="form-group">
          <label for="reg-name">Full Name</label>
          <input
            id="reg-name"
            type="text"
            placeholder="Your full name"
            bind:value={newRep.name}
          />
        </div>

        <div class="form-group">
          <label for="reg-email">Email</label>
          <input
            id="reg-email"
            type="email"
            placeholder="your@email.com"
            bind:value={newRep.email}
          />
        </div>

        <div class="form-group">
          <label for="reg-location">Territory/Location</label>
          <input
            id="reg-location"
            type="text"
            placeholder="e.g., Portland, OR"
            bind:value={newRep.location}
          />
        </div>

        <div class="form-group">
          <label for="reg-code">Invite Code</label>
          <input
            id="reg-code"
            type="password"
            placeholder="Enter invite code"
            bind:value={newRep.code}
          />
        </div>

        <button class="login-btn" on:click={handleRegister}>
          Register
        </button>

        <button class="cancel-btn" on:click={() => { showRegister = false; registerError = ''; }}>
          Back to Login
        </button>
      {/if}
    </div>

    <footer>
      <p>© 2026 IndoorMedia, All Rights Reserved.</p>
    </footer>
  </div>
</main>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    min-height: 100vh;
  }

  .login-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    padding: 20px;
  }

  .login-card {
    background: white;
    border-radius: 16px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    max-width: 420px;
    width: 100%;
    overflow: hidden;
  }

  .header {
    background: linear-gradient(135deg, #CC0000 0%, #990000 100%);
    padding: 40px 30px;
    text-align: center;
    color: white;
  }

  .logo {
    width: 80px;
    height: 80px;
    margin-bottom: 12px;
  }

  .tagline {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.95);
  }

  .login-form {
    padding: 40px;
  }

  .login-form h2 {
    margin: 0 0 8px;
    font-size: 24px;
    color: #333;
  }

  .login-form h3 {
    margin: 0 0 4px;
    font-size: 18px;
    color: #333;
  }

  .subtitle {
    margin: 0 0 20px;
    color: #666;
    font-size: 14px;
  }

  .error-message {
    background: #fff3cd;
    border: 1px solid #ffc107;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 20px;
    color: #856404;
    font-size: 14px;
  }

  .success-message {
    background: #d4edda;
    border: 1px solid #28a745;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 20px;
    color: #155724;
    font-size: 14px;
  }

  .error-text {
    color: #d32f2f;
    font-size: 12px;
    margin-top: 4px;
  }

  .form-group {
    margin-bottom: 20px;
  }

  .form-group label {
    display: block;
    margin-bottom: 6px;
    font-weight: 600;
    color: #333;
    font-size: 14px;
  }

  .form-group input,
  .form-group select {
    width: 100%;
    padding: 12px;
    border: 1px solid #ddd;
    border-radius: 8px;
    font-size: 14px;
    box-sizing: border-box;
    transition: border-color 0.2s;
  }

  .form-group input:focus,
  .form-group select:focus {
    outline: none;
    border-color: #CC0000;
    box-shadow: 0 0 0 3px rgba(204, 0, 0, 0.1);
  }

  .password-setup {
    background: #f9f9f9;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
    border: 1px solid #eee;
  }

  .login-btn,
  .register-btn,
  .cancel-btn {
    width: 100%;
    padding: 14px;
    background: linear-gradient(135deg, #CC0000 0%, #990000 100%);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
    margin-bottom: 12px;
  }

  .login-btn:hover:not(:disabled),
  .register-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(204, 0, 0, 0.3);
  }

  .login-btn:active:not(:disabled),
  .register-btn:active {
    transform: translateY(0);
  }

  .login-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .cancel-btn {
    background: #999;
    margin-bottom: 0;
  }

  .cancel-btn:hover {
    background: #777;
  }

  .or-divider {
    text-align: center;
    margin: 24px 0;
    color: #999;
    font-size: 14px;
  }

  .loading {
    text-align: center;
    color: #999;
    font-size: 14px;
  }

  footer {
    padding: 20px;
    text-align: center;
    border-top: 1px solid #eee;
    background: #fafafa;
  }

  footer p {
    margin: 0;
    font-size: 12px;
    color: #999;
  }
</style>
