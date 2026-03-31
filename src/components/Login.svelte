<script>
  import { createEventDispatcher } from 'svelte';
  import { error, setUser } from '../lib/stores.js';

  let email = '';
  let password = '';
  let isLoading = false;
  let loginError = '';

  async function handleLogin() {
    if (!email || !password) {
      loginError = 'Please enter both email and password';
      return;
    }

    if (!email.endsWith('@indoormedia.com')) {
      loginError = 'Please use your IndoorMedia email (@indoormedia.com)';
      return;
    }

    isLoading = true;
    loginError = '';

    try {
      // Authenticate with IndoorMedia system via server
      const response = await fetch(import.meta.env.BASE_URL + 'api/authenticate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (!response.ok) {
        const data = await response.json();
        loginError = data.error || 'Login failed. Please check your credentials.';
        isLoading = false;
        return;
      }

      const data = await response.json();
      
      // Store user session (NOT the password)
      setUser({
        id: data.id || email,
        name: data.name || email.split('@')[0],
        email: email,
        sessionToken: data.sessionToken,
        role: data.role || 'rep',
        base_location: data.base_location || 'Territory TBD'
      });

      // Clear password from memory
      password = '';
      email = '';
      loginError = '';

    } catch (err) {
      console.error('Login error:', err);
      loginError = 'Connection error. Please try again.';
      isLoading = false;
    }
  }

  function handleKeypress(e) {
    if (e.key === 'Enter' && email && password) {
      handleLogin();
    }
  }
</script>

<main class="login-container">
  <div class="login-card">
    <div class="header">
      <img src={import.meta.env.BASE_URL + 'impro-logo.svg'} alt="IndoorMedia" class="logo" />
      <p class="tagline">imPro Sales Portal</p>
    </div>

    <div class="login-form">
      <h2>IndoorMedia Login</h2>
      <p class="subtitle">Sign in with your IndoorMedia credentials</p>

      {#if loginError}
        <div class="error-message">⚠️ {loginError}</div>
      {/if}

      <div class="form-group">
        <label for="email">Email</label>
        <input
          id="email"
          type="email"
          placeholder="your.name@indoormedia.com"
          bind:value={email}
          on:keypress={handleKeypress}
          disabled={isLoading}
        />
      </div>

      <div class="form-group">
        <label for="password">Password</label>
        <input
          id="password"
          type="password"
          placeholder="Your IndoorMedia password"
          bind:value={password}
          on:keypress={handleKeypress}
          disabled={isLoading}
        />
      </div>

      <button
        class="login-btn"
        on:click={handleLogin}
        disabled={isLoading || !email || !password}
      >
        {#if isLoading}
          ⏳ Authenticating...
        {:else}
          → Sign In
        {/if}
      </button>

      <p class="help-text">
        Use the same email and password you use for Mappoint, Rogue, and internal systems.
      </p>
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
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
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

  .subtitle {
    margin: 0 0 24px;
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

  .form-group input {
    width: 100%;
    padding: 12px;
    border: 1px solid #ddd;
    border-radius: 8px;
    font-size: 14px;
    box-sizing: border-box;
    transition: border-color 0.2s;
  }

  .form-group input:focus {
    outline: none;
    border-color: #CC0000;
    box-shadow: 0 0 0 3px rgba(204, 0, 0, 0.1);
  }

  .form-group input:disabled {
    background: #f5f5f5;
    cursor: not-allowed;
  }

  .login-btn {
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
  }

  .login-btn:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(204, 0, 0, 0.3);
  }

  .login-btn:active:not(:disabled) {
    transform: translateY(0);
  }

  .login-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .help-text {
    margin: 16px 0 0;
    font-size: 13px;
    color: #999;
    text-align: center;
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
