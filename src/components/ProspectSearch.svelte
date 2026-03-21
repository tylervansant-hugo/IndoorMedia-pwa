<script>
  import { searchResults, loading, error, setLoading, setError, addToCart } from '../lib/stores.js';
  import { onMount } from 'svelte';

  let searchTerm = '';
  let allProspects = [];
  let filtered = [];

  async function loadProspects() {
    try {
      setLoading(true);
      const response = await fetch('/data/prospects.json');
      if (!response.ok) throw new Error('Failed to load prospects');
      const data = await response.json();
      allProspects = data || [];
    } catch (err) {
      setError('Failed to load prospects: ' + err.message);
    } finally {
      setLoading(false);
    }
  }

  function filterProspects() {
    if (!searchTerm.trim()) {
      filtered = [];
      return;
    }

    const term = searchTerm.toLowerCase();
    filtered = allProspects.filter(prospect =>
      (prospect.name && prospect.name.toLowerCase().includes(term)) ||
      (prospect.business && prospect.business.toLowerCase().includes(term)) ||
      (prospect.industry && prospect.industry.toLowerCase().includes(term))
    ).slice(0, 20);

    searchResults.set(filtered);
  }

  function handleAddToCart(prospect) {
    addToCart({
      id: prospect.id,
      type: 'prospect',
      name: prospect.name,
      business: prospect.business,
      industry: prospect.industry
    });
    setError('Added to cart');
  }

  onMount(loadProspects);
</script>

<div class="search-container">
  <div class="search-box">
    <input
      type="text"
      placeholder="Search by business name, prospect name, or industry..."
      bind:value={searchTerm}
      on:input={filterProspects}
      disabled={$loading}
    />
    {#if $loading}
      <div class="spinner"></div>
    {/if}
  </div>

  {#if $error}
    <div class="error-box">{$error}</div>
  {/if}

  <div class="results">
    {#if $loading}
      <p class="loading">Loading prospects...</p>
    {:else if filtered.length === 0 && searchTerm}
      <p class="no-results">No prospects found matching "{searchTerm}"</p>
    {:else if filtered.length === 0}
      <p class="hint">Start typing to search for prospects</p>
    {:else}
      <div class="prospect-list">
        {#each filtered as prospect (prospect.id)}
          <div class="prospect-card">
            <div class="prospect-header">
              <h3>{prospect.name}</h3>
            </div>
            <div class="prospect-info">
              <p class="business">{prospect.business}</p>
              {#if prospect.industry}
                <p class="industry">📊 {prospect.industry}</p>
              {/if}
              {#if prospect.location}
                <p class="location">📍 {prospect.location}</p>
              {/if}
            </div>
            <button
              class="add-btn"
              on:click={() => handleAddToCart(prospect)}
            >
              + Add to Cart
            </button>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>

<style>
  .search-container {
    max-width: 900px;
    margin: 0 auto;
  }

  .search-box {
    position: relative;
    margin-bottom: 20px;
  }

  input {
    width: 100%;
    padding: 14px 16px;
    border: 2px solid #ddd;
    border-radius: 8px;
    font-size: 16px;
    font-family: inherit;
    transition: border-color 0.3s;
  }

  input:focus {
    outline: none;
    border-color: #CC0000;
    box-shadow: 0 0 0 3px rgba(255, 107, 53, 0.1);
  }

  .spinner {
    position: absolute;
    right: 14px;
    top: 50%;
    transform: translateY(-50%);
    width: 18px;
    height: 18px;
    border: 2px solid #f0f0f0;
    border-top-color: #CC0000;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: translateY(-50%) rotate(360deg); }
  }

  .error-box {
    background: #fee;
    color: #c33;
    padding: 12px;
    border-radius: 6px;
    margin-bottom: 16px;
  }

  .results {
    min-height: 200px;
  }

  .loading, .no-results, .hint {
    text-align: center;
    color: #999;
    padding: 40px 20px;
  }

  .prospect-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .prospect-card {
    background: white;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    transition: all 0.2s;
  }

  .prospect-card:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
    transform: translateY(-2px);
  }

  .prospect-header {
    margin-bottom: 12px;
  }

  .prospect-header h3 {
    margin: 0;
    font-size: 16px;
    color: #1a1a1a;
  }

  .prospect-info {
    margin-bottom: 12px;
  }

  .prospect-info p {
    margin: 4px 0;
    font-size: 14px;
    color: #666;
  }

  .business {
    font-weight: 600;
    color: #333;
  }

  .industry, .location {
    font-size: 13px;
  }

  .add-btn {
    width: 100%;
    padding: 10px;
    background: #CC0000;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
    font-size: 14px;
    transition: background 0.2s;
  }

  .add-btn:hover {
    background: #990000;
  }
</style>
