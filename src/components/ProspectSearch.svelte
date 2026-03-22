<script>
  import { loading, error, setLoading, setError } from '../lib/stores.js';
  import { onMount } from 'svelte';
  import { 
    searchNearbyPlaces, 
    getPlaceDetails, 
    calculateLikelihoodScore,
    getOpenNowStatus,
    geocodeAddress 
  } from '../lib/google-places.js';
  import {
    initDB,
    getAllProspects,
    getProspectsByStatus,
    searchProspects,
    saveProspect,
    updateProspectStatus,
    addProspectNote,
    markContacted,
    deleteProspect,
    getStats,
    STATUS
  } from '../lib/prospects-db.js';

  let CATEGORIES = {};
  let prospects = [];
  let savedProspects = [];
  let stats = {};

  // UI state
  let view = 'search'; // 'search', 'categories', 'subcategories', 'results', 'saved'
  let userLocation = null;
  let userCity = '';
  let searchTerm = '';
  let selectedCategory = '';
  let selectedSubcategory = '';
  let filtered = [];
  let expandedProspectId = null;
  let savedStatusFilter = STATUS.NEW;
  let prospectSearchQuery = '';

  // Saved prospect editing
  let editingNoteId = null;
  let editingNote = '';

  onMount(async () => {
    initDB();
    loadCategories();
    loadSavedProspects();
    updateStats();
  });

  async function loadCategories() {
    try {
      const res = await fetch('/data/prospect-categories.json');
      CATEGORIES = await res.json();
    } catch (err) {
      console.error('Failed to load categories:', err);
      setError('Failed to load categories');
    }
  }

  function loadSavedProspects() {
    savedProspects = getAllProspects();
  }

  function updateStats() {
    stats = getStats();
  }

  // --- Search Flow ---
  function handleSearch() {
    if (!searchTerm.trim()) {
      setError('Please enter a location');
      return;
    }

    userCity = searchTerm;
    getLocation();
  }

  function getLocation() {
    if (!navigator.geolocation) {
      setError('Geolocation not supported in this browser');
      return;
    }

    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      position => {
        userLocation = position.coords;
        view = 'categories';
        setLoading(false);
      },
      err => {
        setError('Unable to get your location. Enable location services and try again.');
        setLoading(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  function selectCategory(cat) {
    selectedCategory = cat;
    view = 'subcategories';
  }

  async function selectSubcategory(subcat) {
    selectedSubcategory = subcat;
    view = 'results';
    await performSearch();
  }

  async function performSearch() {
    if (!userLocation) {
      setError('Location not available');
      return;
    }

    setLoading(true);
    
    try {
      const categoryData = CATEGORIES[selectedCategory][selectedSubcategory];
      const results = await searchNearbyPlaces(
        userLocation.latitude,
        userLocation.longitude,
        categoryData.keyword,
        categoryData.types
      );

      // Filter out excluded results
      const excludeTerms = categoryData.exclude || [];
      filtered = results
        .filter(place => {
          const name = place.name.toLowerCase();
          return !excludeTerms.some(term => name.includes(term.toLowerCase()));
        })
        .map(place => ({
          ...place,
          likelihoodScore: calculateLikelihoodScore(place),
          category: selectedCategory,
          subcategory: selectedSubcategory
        }))
        .sort((a, b) => b.likelihoodScore - a.likelihoodScore)
        .slice(0, 10);

      if (filtered.length === 0) {
        setError('No results found. Try a different category or location.');
      }
    } catch (err) {
      console.error('Search failed:', err);
      setError('Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  // --- Prospect Card Actions ---
  function toggleExpand(id) {
    expandedProspectId = expandedProspectId === id ? null : id;
  }

  async function handleSaveProspect(place) {
    try {
      const saved = saveProspect(place, selectedCategory, selectedSubcategory);
      setLoading(false);
      alert(`✅ Saved: ${place.name}`);
      loadSavedProspects();
      updateStats();
    } catch (err) {
      setError('Failed to save prospect');
    }
  }

  function openGoogleMaps(place) {
    window.open(place.mapsUrl, '_blank');
  }

  function openMappoint(place) {
    // IndoorMedia MapPoint link
    const mappointUrl = `https://mappoint.indoormedia.com/?q=${encodeURIComponent(place.name)}&lat=${place.latitude || ''}&lng=${place.longitude || ''}`;
    window.open(mappointUrl, '_blank');
  }

  function openCall(phone) {
    if (!phone) return;
    window.location.href = `tel:${phone}`;
  }

  function openWebsite(url) {
    if (!url) return;
    window.open(url, '_blank');
  }

  function draftEmail(place) {
    const subject = encodeURIComponent(`IndoorMedia Advertising Opportunity - ${place.name}`);
    const body = encodeURIComponent(
      `Hello ${place.name},\n\n` +
      `We are IndoorMedia, a leading digital display advertising network.\n\n` +
      `We believe your location would be an excellent fit for our premium advertising placements.\n\n` +
      `Location: ${place.address}\n` +
      `Likelihood Score: ${place.likelihoodScore || 'N/A'}/100\n\n` +
      `We'd love to discuss how we can help increase foot traffic and customer engagement.\n\n` +
      `Best regards,\n` +
      `IndoorMedia Sales Team`
    );
    window.location.href = `mailto:${place.phone.replace(/\D/g, '')}@placeholder.com?subject=${subject}&body=${body}`;
  }

  function draftGoogleCalendar(place) {
    const event = {
      title: `Follow-up: ${place.name}`,
      location: place.address,
      description: `Prospect: ${place.name}\nLikelihood: ${place.likelihoodScore}/100\nCategory: ${selectedSubcategory}`
    };

    const googleCalendarUrl = `https://calendar.google.com/calendar/u/0/r/eventedit?title=${encodeURIComponent(event.title)}&location=${encodeURIComponent(event.location)}&details=${encodeURIComponent(event.description)}`;
    window.open(googleCalendarUrl, '_blank');
  }

  // --- Saved Prospects Management ---
  function switchToSaved() {
    view = 'saved';
    expandedProspectId = null;
  }

  function switchToSearch() {
    view = 'search';
    expandedProspectId = null;
    searchTerm = '';
    selectedCategory = '';
    selectedSubcategory = '';
    userLocation = null;
  }

  function filterSavedProspects() {
    const filtered = getProspectsByStatus(savedStatusFilter);
    return filtered.filter(p => {
      if (!prospectSearchQuery) return true;
      return p.name.toLowerCase().includes(prospectSearchQuery.toLowerCase()) ||
             p.address.toLowerCase().includes(prospectSearchQuery.toLowerCase()) ||
             p.category.toLowerCase().includes(prospectSearchQuery.toLowerCase());
    });
  }

  function updateStatus(prospectId, newStatus) {
    updateProspectStatus(prospectId, newStatus);
    loadSavedProspects();
    updateStats();
  }

  function startEditNote(prospectId, currentNote) {
    editingNoteId = prospectId;
    editingNote = currentNote;
  }

  function saveNote(prospectId) {
    addProspectNote(prospectId, editingNote);
    editingNoteId = null;
    loadSavedProspects();
  }

  function markAsContacted(prospectId, method = 'phone') {
    markContacted(prospectId, method);
    loadSavedProspects();
  }

  function removeSavedProspect(prospectId) {
    if (confirm('Delete this prospect?')) {
      deleteProspect(prospectId);
      loadSavedProspects();
      updateStats();
    }
  }

  function getStatusColor(status) {
    const colors = {
      [STATUS.NEW]: '#dc2626',
      [STATUS.CONTACTED]: '#f59e0b',
      [STATUS.PROPOSAL]: '#3b82f6',
      [STATUS.CLOSED]: '#10b981'
    };
    return colors[status] || '#6b7280';
  }
</script>

<style>
  .prospect-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1rem;
  }

  .view-toggle {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }

  .toggle-btn {
    flex: 1;
    padding: 0.75rem;
    border: 2px solid #dc2626;
    background: white;
    color: #dc2626;
    border-radius: 0.5rem;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.2s;
  }

  .toggle-btn.active {
    background: #dc2626;
    color: white;
  }

  .toggle-btn:hover {
    transform: translateY(-2px);
  }

  /* Search View */
  .search-container {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 2rem;
  }

  .search-input {
    flex: 1;
    padding: 0.75rem;
    border: 2px solid #dc2626;
    border-radius: 0.5rem;
    font-size: 1rem;
  }

  .search-btn {
    padding: 0.75rem 1.5rem;
    background: #dc2626;
    color: white;
    border: none;
    border-radius: 0.5rem;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.2s;
  }

  .search-btn:hover {
    background: #b91c1c;
  }

  .search-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  /* Categories & Subcategories */
  .category-grid,
  .subcategory-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1rem;
    margin-top: 2rem;
  }

  .category-btn,
  .subcategory-btn {
    padding: 1.5rem;
    background: white;
    border: 2px solid #e5e7eb;
    border-radius: 0.5rem;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.2s;
    text-align: center;
  }

  .category-btn:hover,
  .subcategory-btn:hover {
    border-color: #dc2626;
    transform: translateY(-2px);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }

  /* Prospect Cards */
  .results-container {
    display: grid;
    gap: 1rem;
  }

  .prospect-card {
    background: white;
    border: 2px solid #e5e7eb;
    border-radius: 0.5rem;
    overflow: hidden;
    transition: all 0.2s;
  }

  .prospect-card:hover {
    border-color: #dc2626;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  .prospect-header {
    padding: 1rem;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .prospect-info {
    flex: 1;
  }

  .prospect-name {
    font-size: 1.125rem;
    font-weight: 700;
    color: #1f2937;
    margin-bottom: 0.25rem;
  }

  .prospect-address {
    font-size: 0.875rem;
    color: #6b7280;
    margin-bottom: 0.5rem;
  }

  .prospect-meta {
    display: flex;
    gap: 1rem;
    font-size: 0.875rem;
  }

  .score-badge {
    background: #dc2626;
    color: white;
    padding: 0.25rem 0.75rem;
    border-radius: 0.25rem;
    font-weight: 600;
  }

  .open-badge {
    padding: 0.25rem 0.75rem;
    border-radius: 0.25rem;
    font-weight: 600;
    font-size: 0.875rem;
  }

  .open-badge.open {
    background: #d1fae5;
    color: #065f46;
  }

  .open-badge.closed {
    background: #fee2e2;
    color: #991b1b;
  }

  .expand-icon {
    font-size: 1.5rem;
    color: #dc2626;
    transition: transform 0.2s;
  }

  .expand-icon.expanded {
    transform: rotate(180deg);
  }

  .prospect-expanded {
    padding: 1rem;
    background: #f9fafb;
    border-top: 2px solid #e5e7eb;
  }

  .action-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 0.5rem;
    margin: 1rem 0;
  }

  .action-btn {
    padding: 0.5rem;
    border: 1px solid #dc2626;
    background: white;
    color: #dc2626;
    border-radius: 0.25rem;
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: 600;
    transition: all 0.2s;
  }

  .action-btn:hover {
    background: #dc2626;
    color: white;
  }

  .action-btn.primary {
    background: #dc2626;
    color: white;
  }

  /* Business Hours */
  .hours-list {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 0.25rem;
    padding: 0.75rem;
    margin: 0.5rem 0;
    font-size: 0.875rem;
  }

  .hours-list div {
    display: flex;
    justify-content: space-between;
    padding: 0.25rem 0;
  }

  /* Saved Prospects View */
  .saved-header {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .stats-box {
    background: white;
    border: 2px solid #e5e7eb;
    border-radius: 0.5rem;
    padding: 1rem;
    text-align: center;
  }

  .stat-number {
    font-size: 1.5rem;
    font-weight: 700;
    color: #dc2626;
  }

  .stat-label {
    font-size: 0.875rem;
    color: #6b7280;
    margin-top: 0.25rem;
  }

  .filter-controls {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
  }

  .filter-btn {
    padding: 0.5rem 1rem;
    border: 2px solid #e5e7eb;
    background: white;
    border-radius: 0.25rem;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.2s;
  }

  .filter-btn.active {
    border-color: #dc2626;
    background: #dc2626;
    color: white;
  }

  .saved-prospect-card {
    background: white;
    border-left: 4px solid;
    border-radius: 0.5rem;
    padding: 1rem;
    margin-bottom: 1rem;
  }

  .status-selector {
    display: flex;
    gap: 0.25rem;
    margin-bottom: 0.75rem;
  }

  .status-btn {
    flex: 1;
    padding: 0.5rem;
    border: 1px solid #e5e7eb;
    background: white;
    border-radius: 0.25rem;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .status-btn.active {
    color: white;
  }

  .note-editor {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #e5e7eb;
    border-radius: 0.25rem;
    font-size: 0.875rem;
    font-family: inherit;
    margin-bottom: 0.5rem;
  }

  .note-text {
    background: #f9fafb;
    padding: 0.5rem;
    border-radius: 0.25rem;
    font-size: 0.875rem;
    margin-bottom: 0.5rem;
  }

  /* Responsive */
  @media (max-width: 768px) {
    .category-grid,
    .subcategory-grid {
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    }

    .action-grid {
      grid-template-columns: repeat(2, 1fr);
    }

    .saved-header {
      grid-template-columns: 1fr;
    }
  }

  /* Loading & Error */
  .loading {
    text-align: center;
    padding: 2rem;
    color: #6b7280;
  }

  .error {
    background: #fee2e2;
    color: #991b1b;
    padding: 1rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
    border-left: 4px solid #dc2626;
  }

  .nav-buttons {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }

  .back-btn {
    padding: 0.5rem 1rem;
    background: white;
    border: 2px solid #e5e7eb;
    border-radius: 0.25rem;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.2s;
  }

  .back-btn:hover {
    border-color: #dc2626;
    color: #dc2626;
  }
</style>

<div class="prospect-container">
  <!-- View Toggle -->
  <div class="view-toggle">
    <button
      class="toggle-btn {view !== 'saved' ? 'active' : ''}"
      on:click={switchToSearch}
    >
      🔍 Find Prospects
    </button>
    <button
      class="toggle-btn {view === 'saved' ? 'active' : ''}"
      on:click={switchToSaved}
    >
      💾 Saved ({savedProspects.length})
    </button>
  </div>

  {#if $loading}
    <div class="loading">⏳ Searching...</div>
  {/if}

  {#if $error}
    <div class="error">❌ {$error}</div>
  {/if}

  <!-- Search View -->
  {#if view === 'search'}
    <div>
      <h2 style="margin-bottom: 1rem; color: #1f2937;">Find Prospects</h2>

      {#if view === 'search' && selectedCategory === ''}
        <div class="search-container">
          <input
            type="text"
            class="search-input"
            placeholder="Enter your city name..."
            bind:value={searchTerm}
            on:keydown={e => e.key === 'Enter' && handleSearch()}
          />
          <button class="search-btn" on:click={handleSearch} disabled={$loading}>
            Search
          </button>
        </div>
      {/if}

      {#if userLocation && selectedCategory === ''}
        <div style="text-align: center; color: #6b7280; margin-bottom: 2rem;">
          📍 Searching near: {userCity}
        </div>

        <h3 style="color: #1f2937; margin-bottom: 1rem;">Select a Category</h3>
        <div class="category-grid">
          {#each Object.keys(CATEGORIES) as category}
            <button
              class="category-btn"
              on:click={() => selectCategory(category)}
            >
              {category}
            </button>
          {/each}
        </div>
      {/if}

      {#if selectedCategory && selectedSubcategory === ''}
        <div class="nav-buttons">
          <button class="back-btn" on:click={() => {
            selectedCategory = '';
            selectedSubcategory = '';
          }}>
            ← Back to Categories
          </button>
        </div>

        <h3 style="color: #1f2937; margin-bottom: 1rem;">
          {selectedCategory}
        </h3>
        <div class="subcategory-grid">
          {#each Object.keys(CATEGORIES[selectedCategory]) as subcat}
            <button
              class="subcategory-btn"
              on:click={() => selectSubcategory(subcat)}
            >
              {subcat}
            </button>
          {/each}
        </div>
      {/if}

      {#if view === 'results' && filtered.length > 0}
        <div class="nav-buttons">
          <button class="back-btn" on:click={() => {
            selectedSubcategory = '';
            filtered = [];
          }}>
            ← Back to Subcategories
          </button>
        </div>

        <h3 style="color: #1f2937; margin-bottom: 1rem;">
          Results for {selectedCategory} → {selectedSubcategory}
        </h3>

        <div class="results-container">
          {#each filtered as prospect (prospect.placeId)}
            <div class="prospect-card">
              <div
                class="prospect-header"
                on:click={() => toggleExpand(prospect.placeId)}
              >
                <div class="prospect-info">
                  <div class="prospect-name">{prospect.name}</div>
                  <div class="prospect-address">{prospect.address}</div>
                  <div class="prospect-meta">
                    <span class="score-badge">
                      🎯 {prospect.likelihoodScore}%
                    </span>
                    {#if prospect.isOpen !== null}
                      <span class="open-badge {prospect.isOpen ? 'open' : 'closed'}">
                        {prospect.isOpen ? '✅ Open' : '❌ Closed'}
                      </span>
                    {/if}
                    {#if prospect.rating > 0}
                      <span style="color: #6b7280;">
                        ⭐ {prospect.rating.toFixed(1)} ({prospect.reviewCount})
                      </span>
                    {/if}
                  </div>
                </div>
                <span class="expand-icon {expandedProspectId === prospect.placeId ? 'expanded' : ''}">
                  ▼
                </span>
              </div>

              {#if expandedProspectId === prospect.placeId}
                <div class="prospect-expanded">
                  <!-- Business Info -->
                  {#if prospect.phone}
                    <div style="margin-bottom: 0.5rem;">
                      <strong>📞 Phone:</strong> {prospect.phone}
                    </div>
                  {/if}

                  {#if prospect.website}
                    <div style="margin-bottom: 0.5rem;">
                      <strong>🌐 Website:</strong>
                      <a href={prospect.website} target="_blank" rel="noopener">
                        {prospect.website.replace(/^https?:\/\//, '')}
                      </a>
                    </div>
                  {/if}

                  <!-- Business Hours -->
                  {#if prospect.hours.length > 0}
                    <div style="margin-bottom: 1rem;">
                      <strong>⏰ Hours:</strong>
                      <div class="hours-list">
                        {#each prospect.hours as hour}
                          <div>{hour}</div>
                        {/each}
                      </div>
                    </div>
                  {/if}

                  <!-- Action Buttons -->
                  <div class="action-grid">
                    <button
                      class="action-btn primary"
                      on:click={() => handleSaveProspect(prospect)}
                    >
                      💾 Save
                    </button>
                    {#if prospect.phone}
                      <button
                        class="action-btn"
                        on:click={() => openCall(prospect.phone)}
                      >
                        📞 Call
                      </button>
                    {/if}
                    {#if prospect.website}
                      <button
                        class="action-btn"
                        on:click={() => openWebsite(prospect.website)}
                      >
                        🌐 Website
                      </button>
                    {/if}
                    <button
                      class="action-btn"
                      on:click={() => openGoogleMaps(prospect)}
                    >
                      📍 Maps
                    </button>
                    <button
                      class="action-btn"
                      on:click={() => openMappoint(prospect)}
                    >
                      🗺️ MapPoint
                    </button>
                    <button
                      class="action-btn"
                      on:click={() => draftEmail(prospect)}
                    >
                      📧 Email
                    </button>
                    <button
                      class="action-btn"
                      on:click={() => draftGoogleCalendar(prospect)}
                    >
                      📅 Calendar
                    </button>
                    <button
                      class="action-btn"
                      on:click={() => {
                        const note = prompt('Add a quick note:');
                        if (note) {
                          const saved = saveProspect(prospect, selectedCategory, selectedSubcategory);
                          addProspectNote(saved.id, note);
                          loadSavedProspects();
                        }
                      }}
                    >
                      📝 Notes
                    </button>
                  </div>
                </div>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}

  <!-- Saved Prospects View -->
  {#if view === 'saved'}
    <div>
      <h2 style="margin-bottom: 1rem; color: #1f2937;">Saved Prospects</h2>

      <div class="saved-header">
        <div class="stats-box">
          <div class="stat-number">{stats.total || 0}</div>
          <div class="stat-label">Total Prospects</div>
        </div>
        <div class="stats-box">
          <div class="stat-number">{stats.new || 0}</div>
          <div class="stat-label">New</div>
        </div>
        <div class="stats-box">
          <div class="stat-number">{stats.contacted || 0}</div>
          <div class="stat-label">Contacted</div>
        </div>
        <div class="stats-box">
          <div class="stat-number">{stats.proposal || 0}</div>
          <div class="stat-label">Proposal</div>
        </div>
        <div class="stats-box">
          <div class="stat-number">{stats.closed || 0}</div>
          <div class="stat-label">Closed</div>
        </div>
      </div>

      <!-- Filters -->
      <div class="filter-controls">
        <input
          type="text"
          class="search-input"
          style="flex: 1;"
          placeholder="Search prospects..."
          bind:value={prospectSearchQuery}
        />
      </div>

      <div class="filter-controls">
        {#each Object.values(STATUS) as status}
          <button
            class="filter-btn {savedStatusFilter === status ? 'active' : ''}"
            on:click={() => savedStatusFilter = status}
          >
            {status}
          </button>
        {/each}
      </div>

      <!-- Prospects List -->
      {#if filterSavedProspects().length === 0}
        <div style="text-align: center; color: #6b7280; padding: 2rem;">
          No prospects found
        </div>
      {/if}

      {#each filterSavedProspects() as prospect (prospect.id)}
        <div
          class="saved-prospect-card"
          style="border-color: {getStatusColor(prospect.status)}"
        >
          <div
            style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.75rem;"
          >
            <div>
              <div class="prospect-name">{prospect.name}</div>
              <div class="prospect-address">{prospect.address}</div>
              <div class="prospect-meta">
                <span style="color: #6b7280;">{prospect.category}</span>
                <span style="color: #dc2626; font-weight: 600;">
                  🎯 {prospect.likelihoodScore}%
                </span>
              </div>
            </div>
            <button
              class="action-btn"
              style="padding: 0.25rem 0.5rem;"
              on:click={() => removeSavedProspect(prospect.id)}
            >
              ✕
            </button>
          </div>

          <!-- Status Workflow -->
          <div class="status-selector">
            {#each Object.values(STATUS) as status}
              <button
                class="status-btn {prospect.status === status ? 'active' : ''}"
                style="border-color: {getStatusColor(status)}; background: {prospect.status === status ? getStatusColor(status) : 'white'}; color: {prospect.status === status ? 'white' : getStatusColor(status)};"
                on:click={() => updateStatus(prospect.id, status)}
              >
                {status}
              </button>
            {/each}
          </div>

          <!-- Notes -->
          {#if editingNoteId === prospect.id}
            <textarea
              class="note-editor"
              bind:value={editingNote}
              placeholder="Add notes..."
            />
            <div style="display: flex; gap: 0.5rem; margin-bottom: 0.75rem;">
              <button
                class="action-btn primary"
                style="flex: 1;"
                on:click={() => saveNote(prospect.id)}
              >
                Save
              </button>
              <button
                class="action-btn"
                style="flex: 1;"
                on:click={() => editingNoteId = null}
              >
                Cancel
              </button>
            </div>
          {:else if prospect.notes}
            <div class="note-text">📝 {prospect.notes}</div>
            <button
              class="action-btn"
              style="width: 100%; margin-bottom: 0.75rem;"
              on:click={() => startEditNote(prospect.id, prospect.notes)}
            >
              Edit Notes
            </button>
          {:else}
            <button
              class="action-btn"
              style="width: 100%; margin-bottom: 0.75rem;"
              on:click={() => startEditNote(prospect.id, '')}
            >
              Add Notes
            </button>
          {/if}

          <!-- Quick Actions -->
          <div class="action-grid">
            {#if prospect.phone}
              <button
                class="action-btn"
                on:click={() => {
                  markAsContacted(prospect.id, 'phone');
                  openCall(prospect.phone);
                }}
              >
                📞 Call
              </button>
            {/if}
            {#if prospect.website}
              <button
                class="action-btn"
                on:click={() => openWebsite(prospect.website)}
              >
                🌐 Web
              </button>
            {/if}
            <button
              class="action-btn"
              on:click={() => {
                markAsContacted(prospect.id, 'email');
                draftEmail(prospect);
              }}
            >
              📧 Email
            </button>
            <button
              class="action-btn"
              on:click={() => draftGoogleCalendar(prospect)}
            >
              📅 Cal
            </button>
            <button
              class="action-btn"
              on:click={() => openGoogleMaps(prospect)}
            >
              📍 Maps
            </button>
            <button
              class="action-btn"
              on:click={() => openMappoint(prospect)}
            >
              🗺️ MapPoint
            </button>
          </div>

          <!-- Contact History -->
          {#if prospect.lastContactedAt}
            <div style="font-size: 0.875rem; color: #6b7280; margin-top: 0.5rem;">
              Last contacted: {new Date(prospect.lastContactedAt).toLocaleDateString()}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>
