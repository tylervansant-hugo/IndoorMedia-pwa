<script>
  import { searchResults, loading, error, setLoading, setError, addToCart } from '../lib/stores.js';
  import { onMount } from 'svelte';

  let searchTerm = '';
  let allProspects = [];
  let filtered = [];

  async function loadProspects() {
    try {
      setLoading(true);
      const response = await fetch('/data/prospect_data.json');
      if (!response.ok) throw new Error('Failed to load prospects');
      const data = await response.json();
      
      // Flatten all reps' saved prospects into one list
      const reps = data.reps || {};
      allProspects = [];
      for (const [repId, rep] of Object.entries(reps)) {
        const saved = rep.saved_prospects || {};
        for (const [pid, prospect] of Object.entries(saved)) {
          allProspects.push({
            id: pid,
            repName: rep.name,
            name: prospect.name || '',
            address: prospect.address || '',
            phone: prospect.phone || '',
            score: prospect.score || 0,
            status: prospect.status || 'new',
            store: prospect.store || '',
            category: prospect.category || '',
            notes: prospect.notes || []
          });
        }
      }
      console.log(`Loaded ${allProspects.length} prospects`);
    } catch (err) {
      setError('Failed to load prospects: ' + err.message);
    } finally {
      setLoading(false);
    }
  }

  function filterProspects() {
    if (!searchTerm.trim()) {
      // Show all prospects when no search term
      filtered = allProspects.slice(0, 20);
      return;
    }

    const term = searchTerm.toLowerCase();
    filtered = allProspects.filter(prospect =>
      (prospect.name && prospect.name.toLowerCase().includes(term)) ||
      (prospect.address && prospect.address.toLowerCase().includes(term)) ||
      (prospect.category && prospect.category.toLowerCase().includes(term)) ||
      (prospect.repName && prospect.repName.toLowerCase().includes(term)) ||
      (prospect.store && prospect.store.toLowerCase().includes(term))
    ).slice(0, 20);

    searchResults.set(filtered);
  }

  onMount(loadProspects);
</script>

<div class="search-container">
  <div class="search-box">
    <input
      type="text"
      placeholder="Search saved prospects by name, address, or store..."
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
      <p class="hint">Search saved prospects or leave blank to see all</p>
    {:else}
      <div class="prospect-list">
        {#each filtered as prospect (prospect.id)}
          <div class="prospect-card">
            <div class="prospect-header">
              <h3>{prospect.name}</h3>
              {#if prospect.score}
                <span class="score" class:high={prospect.score >= 70} class:mid={prospect.score >= 40 && prospect.score < 70} class:low={prospect.score < 40}>
                  {prospect.score.toFixed(0)}%
                </span>
              {/if}
            </div>
            <div class="prospect-info">
              {#if prospect.address}
                <p class="address">📍 {prospect.address}</p>
              {/if}
              {#if prospect.phone}
                <p class="phone">📞 <a href="tel:{prospect.phone}">{prospect.phone}</a></p>
              {/if}
              {#if prospect.store}
                <p class="store">🏪 {prospect.store}</p>
              {/if}
              {#if prospect.category}
                <p class="category">📊 {prospect.category}</p>
              {/if}
              <p class="rep">👤 {prospect.repName}</p>
              {#if prospect.status}
                <span class="status-badge" class:interested={prospect.status === 'interested'}
                  class:followup={prospect.status === 'follow-up'}
                  class:closed={prospect.status === 'closed'}>
                  {prospect.status}
                </span>
              {/if}
            </div>
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
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }

  .prospect-header h3 {
    margin: 0;
    font-size: 16px;
    color: #1a1a1a;
  }

  .score {
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 700;
  }

  .score.high { background: #e8f5e9; color: #2e7d32; }
  .score.mid { background: #fff3e0; color: #e65100; }
  .score.low { background: #fce4ec; color: #c62828; }

  .prospect-info {
    margin-bottom: 8px;
  }

  .prospect-info p {
    margin: 4px 0;
    font-size: 13px;
    color: #666;
  }

  .prospect-info a {
    color: #CC0000;
    text-decoration: none;
  }

  .status-badge {
    display: inline-block;
    margin-top: 8px;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
    text-transform: capitalize;
    background: #e0e0e0;
    color: #666;
  }

  .status-badge.interested { background: #e3f2fd; color: #1565c0; }
  .status-badge.followup { background: #fff3e0; color: #e65100; }
  .status-badge.closed { background: #e8f5e9; color: #2e7d32; }
</style>
