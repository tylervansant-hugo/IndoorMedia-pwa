<script>
  import { searchResults, loading, error, setLoading, setError } from '../lib/stores.js';
  import { onMount } from 'svelte';

  let searchTerm = '';
  let allTestimonials = [];
  let filtered = [];

  async function loadTestimonials() {
    try {
      setLoading(true);
      const response = await fetch('/data/testimonials_cache.json');
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
      const fullData = t.full || t;
      return (
        (fullData.text && fullData.text.toLowerCase().includes(term)) ||
        (fullData.author && fullData.author.toLowerCase().includes(term)) ||
        (fullData.business && fullData.business.toLowerCase().includes(term)) ||
        (fullData.city && fullData.city.toLowerCase().includes(term))
      );
    }).slice(0, 20);

    searchResults.set(filtered);
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
      <div class="testimonial-list">
        {#each filtered as testimonial (testimonial.id || testimonial.full?.id)}
          <div class="testimonial-card">
            <div class="stars">
              {'⭐'.repeat(testimonial.rating || 5)}
            </div>
            <p class="testimonial-text">"{(testimonial.full?.text || testimonial.text).substring(0, 200)}"</p>
            <div class="testimonial-author">
              <strong>{testimonial.full?.author || testimonial.author}</strong>
              <span class="business">{testimonial.full?.business || testimonial.business}</span>
            </div>
            {#if testimonial.full?.city || testimonial.city}
              <p class="location">📍 {testimonial.full?.city || testimonial.city}</p>
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
</style>
