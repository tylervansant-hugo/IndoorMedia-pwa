<script>
  import { loading, error, setLoading, setError } from '../lib/stores.js';
  import { onMount } from 'svelte';

  const CATEGORIES = {
    "🍽️ Restaurants": ["Mexican", "Pizza", "Coffee/Café", "Sushi/Japanese", "Fast Food", "Chinese", "Thai", "Indian", "BBQ/Steakhouse", "Italian", "Bakery", "Bar/Pub", "All Restaurants"],
    "🚗 Automotive": ["Oil Change/Lube", "Car Wash", "Auto Repair", "Tires", "Car Dealer", "Body Shop", "Transmission"],
    "💄 Beauty & Wellness": ["Hair Salon", "Barber", "Nail Salon", "Spa/Massage", "Gym/Fitness", "Yoga/Pilates", "Tanning"],
    "🏥 Health/Medical": ["Dentist", "Chiropractor", "Veterinarian", "Physical Therapy", "Optical", "Urgent Care"],
    "🛍️ Retail": ["Clothing/Apparel", "Home & Garden", "Electronics", "Books/Music", "Sporting Goods", "General Retail"],
    "🏠 Home Services": ["Plumbing", "HVAC", "Roofing", "Landscaping", "Cleaning", "Electrician"],
    "📱 Services": ["Phone/Telecom", "Insurance", "Real Estate", "Financial", "Legal", "Accounting"]
  };

  let searchTerm = '';
  let selectedCategory = '';
  let selectedSubcategory = '';
  let allProspects = [];
  let filtered = [];
  let userLocation = null;
  let useGeolocation = false;
  let view = 'categories'; // 'categories', 'subcategories', 'results'

  onMount(async () => {
    try {
      setLoading(true);
      const response = await fetch('/data/prospect_data.json');
      if (!response.ok) throw new Error('Failed to load prospects');
      const data = response.json ? response.json() : JSON.parse(response);
      
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
            category: prospect.category || '',
            latitude: prospect.latitude || 0,
            longitude: prospect.longitude || 0,
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
  });

  function selectCategory(cat) {
    selectedCategory = cat;
    view = 'subcategories';
  }

  function selectSubcategory(subcat) {
    selectedSubcategory = subcat;
    view = 'results';
    // Filter by category keyword
    const keyword = subcat.toLowerCase();
    filtered = allProspects
      .filter(p => p.category?.toLowerCase().includes(keyword) || p.name?.toLowerCase().includes(keyword))
      .sort((a, b) => b.score - a.score)
      .slice(0, 20);
  }

  function findNearby() {
    if (!navigator.geolocation) {
      setError('Geolocation not supported');
      return;
    }

    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      position => {
        const { latitude, longitude } = position.coords;
        userLocation = { lat: latitude, lng: longitude };
        useGeolocation = true;

        // Sort by distance
        filtered = allProspects
          .filter(p => p.latitude && p.longitude)
          .map(p => ({
            ...p,
            _dist: Math.sqrt(Math.pow(p.latitude - latitude, 2) + Math.pow(p.longitude - longitude, 2))
          }))
          .sort((a, b) => a._dist - b._dist)
          .slice(0, 20);

        view = 'results';
        setLoading(false);
      },
      err => {
        setError('Unable to access location');
        setLoading(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  function goBack() {
    if (view === 'results') {
      view = 'subcategories';
    } else if (view === 'subcategories') {
      view = 'categories';
      selectedCategory = '';
    } else {
      searchTerm = '';
    }
  }

  function getStatusBadge(status) {
    const badges = {
      'new': '🆕',
      'interested': '✅',
      'contacted': '⏳',
      'proposal': '📋',
      'closed': '🎉'
    };
    return badges[status] || '◯';
  }
</script>

<div class="prospect-container">
  {#if view === 'categories'}
    <div class="header">
      <h2>🎯 Find Prospects</h2>
      <button class="nearby-btn" on:click={findNearby} disabled={$loading}>
        📍 Find Nearby
      </button>
    </div>

    <div class="category-grid">
      {#each Object.keys(CATEGORIES) as cat}
        <button class="category-card" on:click={() => selectCategory(cat)}>
          {cat}
        </button>
      {/each}
    </div>

  {:else if view === 'subcategories'}
    <button class="back-btn" on:click={goBack}>← {selectedCategory}</button>
    
    <div class="subcat-grid">
      {#each CATEGORIES[selectedCategory] || [] as subcat}
        <button class="subcat-card" on:click={() => selectSubcategory(subcat)}>
          {subcat}
        </button>
      {/each}
    </div>

  {:else if view === 'results'}
    <button class="back-btn" on:click={goBack}>← Back</button>

    {#if $loading}
      <p class="loading">Loading prospects...</p>
    {:else if filtered.length === 0}
      <p class="no-results">No prospects found</p>
    {:else}
      <div class="prospect-list">
        {#each filtered as prospect (prospect.id)}
          <div class="prospect-card">
            <div class="prospect-header">
              <h3>{prospect.name}</h3>
              <span class="status-badge">{getStatusBadge(prospect.status)}</span>
            </div>
            <p class="prospect-address">{prospect.address}</p>
            <div class="prospect-footer">
              <div class="score">
                <span class="score-label">Score:</span>
                <span class="score-value">{Math.round(prospect.score)}</span>
              </div>
              {#if prospect.phone}
                <a href="tel:{prospect.phone}" class="phone-link">📞 Call</a>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    {/if}
  {/if}

  {#if $error}
    <div class="error-box">{$error}</div>
  {/if}
</div>

<style>
  .prospect-container { max-width: 700px; margin: 0 auto; }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }

  h2 { margin: 0; font-size: 20px; }

  .nearby-btn {
    padding: 10px 16px;
    background: #CC0000;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
  }

  .nearby-btn:hover { background: #990000; }

  .category-grid, .subcat-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .category-card, .subcat-card {
    background: white;
    border: 2px solid #e0e0e0;
    border-radius: 12px;
    padding: 16px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
    transition: all 0.2s;
    text-align: center;
  }

  .category-card:hover, .subcat-card:hover {
    border-color: #CC0000;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  }

  .back-btn {
    padding: 10px 14px;
    background: none;
    border: none;
    color: #CC0000;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    margin-bottom: 16px;
  }

  .prospect-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .prospect-card {
    background: white;
    border-radius: 10px;
    padding: 14px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border-left: 4px solid #CC0000;
  }

  .prospect-header {
    display: flex;
    justify-content: space-between;
    align-items: start;
    margin-bottom: 6px;
  }

  .prospect-header h3 { margin: 0; font-size: 15px; color: #1a1a1a; }

  .status-badge { font-size: 18px; }

  .prospect-address { margin: 4px 0; font-size: 12px; color: #666; }

  .prospect-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 10px;
  }

  .score { display: flex; align-items: center; gap: 4px; font-size: 12px; }
  .score-label { color: #999; }
  .score-value { font-weight: 700; color: #CC0000; }

  .phone-link {
    padding: 6px 12px;
    background: #4CAF50;
    color: white;
    text-decoration: none;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
  }

  .phone-link:hover { background: #45a049; }

  .error-box {
    background: #fee;
    color: #c33;
    padding: 12px;
    border-radius: 8px;
    font-size: 13px;
    margin-top: 16px;
  }

  .loading, .no-results {
    text-align: center;
    color: #999;
    padding: 40px 20px;
    font-size: 14px;
  }

  @media (max-width: 480px) {
    .category-grid, .subcat-grid { grid-template-columns: 1fr; }
    .header { flex-direction: column; gap: 12px; align-items: stretch; }
    .nearby-btn { width: 100%; }
  }
</style>
