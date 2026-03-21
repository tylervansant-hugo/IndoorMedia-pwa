<script>
  import { createEventDispatcher } from 'svelte';
  import { error, setLoading } from '../lib/stores.js';

  const dispatch = createEventDispatcher();

  let selectedRep = '';
  let isLoading = false;

  // Mock reps data (embedded for Vercel compatibility)
  const reps = [
    { id: 1, name: 'Tyler Van Sant', email: 'tyler@indoormedia.com', first_name: 'Tyler', last_name: 'Van Sant' },
    { id: 2, name: 'Amy Dixon', email: 'amy@indoormedia.com', first_name: 'Amy', last_name: 'Dixon' },
    { id: 3, name: 'Matt', email: 'matt@indoormedia.com', first_name: 'Matt', last_name: '' }
  ];

  function handleLogin() {
    if (!selectedRep) {
      $error = 'Please select a representative';
      return;
    }

    const rep = reps.find(r => r.id == selectedRep);
    if (rep) {
      dispatch('login', rep);
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
              {rep.name}
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
    background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%);
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
    background: #FF6B35;
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
    border-color: #FF6B35;
  }

  select:focus {
    outline: none;
    border-color: #FF6B35;
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
    background: #FF6B35;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.3s, transform 0.1s;
  }

  button:hover:not(:disabled) {
    background: #E55A24;
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
