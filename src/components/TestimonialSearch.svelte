<script>
  import { searchResults, loading, error, setLoading, setError } from '../lib/stores.js';
  import { onMount } from 'svelte';

  let searchTerm = '';
  let allTestimonials = [];
  let filtered = [];

  async function loadTestimonials() {
    try {
      setLoading(true);
      const response = await fetch(import.meta.env.BASE_URL + 'data/testimonials_cache.json?t=' + Date.now());
      if (!response.ok) throw new Error('Failed to load testimonials');
      const data = await response.json();
      allTestimonials = Array.isArray(data) ? data : data.testimonials || [];
    } catch (err) {
      setError('Failed to load testimonials: ' + err.message);
    } finally {
      setLoading(false);
    }
  }

  function filterTestimonials() {
    if (!searchTerm.trim()) {
      filtered = [];
      return;
    }

    const term = searchTerm.toLowerCase();
    filtered = allTestimonials.filter(t => {
      const comment = t.comment || t.comments || '';
      const business = t.business || t.business_name || '';
      const searchable = t.searchable || '';
      return (
        comment.toLowerCase().includes(term) ||
        business.toLowerCase().includes(term) ||
        searchable.toLowerCase().includes(term)
      );
    }).slice(0, 20);

    // Normalize field names for display
    filtered = filtered.map(t => ({
      ...t,
      comment: t.comment || t.comments || '',
      business: t.business || t.business_name || 'Unknown Business',
    }));

    searchResults.set(filtered);
  }

  function openAllTabs() {
    const urls = filtered.filter(t => t.url).map(t => t.url);
    urls.forEach(url => window.open(url, '_blank'));
  }

  onMount(loadTestimonials);
</script>

<div class="search-container">
  <div class="search-box">
    <input
      type="text"
      placeholder="Search testimonials by keyword, author, or location..."
      bind:value={searchTerm}
      on:input={filterTestimonials}
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
      <p class="loading">Loading testimonials...</p>
    {:else if filtered.length === 0 && searchTerm}
      <p class="no-results">No testimonials found matching "{searchTerm}"</p>
    {:else if filtered.length === 0}
      <p class="hint">Start typing to search for testimonials</p>
    {:else}
      <div class="results-header">
        <span class="results-count">{filtered.length} result{filtered.length === 1 ? '' : 's'}</span>
        {#if filtered.filter(t => t.url).length > 1}
          <button class="open-all-btn" on:click={openAllTabs}>
            📂 Open All ({filtered.filter(t => t.url).length})
          </button>
        {/if}
      </div>
      <div class="testimonial-list">
        {#each filtered as testimonial (testimonial.id)}
          <div class="testimonial-card" class:clickable={testimonial.url} on:click={() => testimonial.url && window.open(testimonial.url, '_blank')}>
            <div class="card-body">
              <p class="testimonial-text">"{testimonial.comment}"</p>
              <div class="testimonial-author">
                <strong>{testimonial.business}</strong>
              </div>
            </div>
            {#if testimonial.url}
              <div class="card-link-hint">
                <span>View on IndoorMedia →</span>
                <span class="open-icon">↗</span>
              </div>
            {/if}
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
    box-shadow: 0 0 0 3px rgba(204, 0, 0, 0.1);
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

  .testimonial-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .testimonial-card {
    background: white;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    border-left: 4px solid #CC0000;
  }

  .stars {
    margin-bottom: 8px;
    font-size: 14px;
  }

  .testimonial-text {
    margin: 8px 0;
    font-size: 14px;
    line-height: 1.5;
    color: #333;
    font-style: italic;
  }

  .testimonial-author {
    margin: 12px 0 8px 0;
    font-size: 13px;
  }

  .testimonial-author strong {
    color: #1a1a1a;
    display: block;
    margin-bottom: 2px;
  }

  .business {
    color: #666;
    font-size: 12px;
  }

  .location {
    font-size: 12px;
    color: #999;
    margin: 0;
  }

  .results-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }

  .results-count {
    font-size: 13px;
    color: #888;
    font-weight: 500;
  }

  .open-all-btn {
    padding: 8px 16px;
    border-radius: 20px;
    border: 2px solid #CC0000;
    background: white;
    color: #CC0000;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .open-all-btn:hover {
    background: #CC0000;
    color: white;
  }

  .testimonial-card.clickable {
    cursor: pointer;
    transition: transform 0.15s, box-shadow 0.15s;
  }

  .testimonial-card.clickable:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
  }

  .testimonial-card.clickable:active {
    transform: scale(0.99);
  }

  .card-link-hint {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid #f0f0f0;
    font-size: 13px;
    color: #CC0000;
    font-weight: 500;
  }

  .open-icon {
    font-size: 16px;
    font-weight: 700;
  }
</style>
