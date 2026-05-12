<script>
  import { onMount, onDestroy } from 'svelte';
  import { user } from '../lib/stores.js';

  export let appointments = [];
  export let onClose = () => {};

  const PLACES_API_KEY = 'AIzaSyBoslNJj8aO6wkQOfkH9e4qTVJZ-G9nOuA';

  // State: home | listening-store | store-results | categories | subcategories | searching | prospects
  //        renewals | renewal-detail
  let phase = 'home';
  let speaking = false;
  let listening = false;
  let recognition = null;
  let wakeLock = null;
  let currentTime = new Date();
  let timeInterval;
  let statusText = '';

  // Store search
  let allStores = [];
  let matchedStores = [];
  let selectedStore = null;

  // Categories
  const CATEGORIES = {
    '🍽️ Restaurants': ['Mexican', 'Pizza', 'Coffee', 'Sushi', 'Fast Food', 'Chinese', 'Thai', 'BBQ', 'Italian', 'Bakery', 'Seafood', 'All'],
    '🚗 Auto': ['Oil Change', 'Car Wash', 'Auto Repair', 'Tires', 'Body Shop', 'Detailing'],
    '💄 Beauty': ['Hair Salon', 'Barber', 'Nails', 'Spa', 'Gym', 'Massage'],
    '🏥 Health': ['Dentist', 'Chiropractor', 'Eye Care', 'Vet', 'Pharmacy', 'Urgent Care'],
    '🏠 Home': ['Plumber', 'Electrician', 'HVAC', 'Roofing', 'Landscaping', 'Cleaning', 'Pest Control'],
    '🛍️ Retail': ['Clothing', 'Pet Store', 'Florist', 'Furniture', 'Liquor'],
    '🐾 Pets': ['Grooming', 'Boarding/Kennel', 'Dog Training', 'Vet'],
  };

  const CATEGORY_KEYWORDS = {
    'Mexican': 'mexican restaurant', 'Pizza': 'pizza restaurant', 'Coffee': 'coffee cafe',
    'Sushi': 'sushi restaurant', 'Fast Food': 'fast food restaurant', 'Chinese': 'chinese restaurant',
    'Thai': 'thai restaurant', 'BBQ': 'bbq restaurant', 'Italian': 'italian restaurant',
    'Bakery': 'bakery', 'Seafood': 'seafood restaurant', 'All': 'restaurant',
    'Oil Change': 'oil change', 'Car Wash': 'car wash', 'Auto Repair': 'auto repair',
    'Tires': 'tire shop', 'Body Shop': 'body shop', 'Detailing': 'auto detailing',
    'Hair Salon': 'hair salon', 'Barber': 'barber', 'Nails': 'nail salon',
    'Spa': 'spa massage', 'Gym': 'gym fitness', 'Massage': 'massage therapist',
    'Dentist': 'dentist', 'Chiropractor': 'chiropractor', 'Eye Care': 'optometrist eye care',
    'Vet': 'veterinarian', 'Pharmacy': 'pharmacy', 'Urgent Care': 'urgent care',
    'Plumber': 'plumber', 'Electrician': 'electrician', 'HVAC': 'hvac',
    'Roofing': 'roofing', 'Landscaping': 'landscaping', 'Cleaning': 'cleaning service',
    'Pest Control': 'pest control', 'Clothing': 'clothing store', 'Pet Store': 'pet store',
    'Florist': 'florist', 'Furniture': 'furniture store', 'Liquor': 'liquor store',
    'Grooming': 'pet grooming', 'Boarding/Kennel': 'pet boarding kennel', 'Dog Training': 'dog training',
  };

  let selectedCategory = null;
  let prospects = [];
  let currentProspectIndex = 0;
  let showNoteInput = false;
  let noteText = '';

  // Renewals
  let renewals = [];
  let filteredRenewals = [];
  let selectedRenewal = null;
  let renewalFilter = 'mine'; // mine | all

  export let onBookAppointment = null;

  $: firstName = ($user?.name || $user?.first_name || 'Rep').split(' ')[0];
  $: nextAppt = appointments.length > 0 ? appointments[0] : null;
  $: currentProspect = prospects[currentProspectIndex] || null;

  onMount(async () => {
    try {
      if ('wakeLock' in navigator) wakeLock = await navigator.wakeLock.request('screen');
    } catch {}
    timeInterval = setInterval(() => { currentTime = new Date(); }, 60000);

    // Load stores
    try {
      const res = await fetch(import.meta.env.BASE_URL + 'data/stores.json?t=' + Date.now());
      allStores = await res.json();
    } catch { allStores = []; }

    // Load pending renewals
    try {
      const res = await fetch(import.meta.env.BASE_URL + 'data/pending_renewals.json?t=' + Date.now());
      renewals = await res.json();
      filterRenewals();
    } catch { renewals = []; }

    // Setup speech recognition
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';
    }

    // Quick voice greeting
    speak(`Ready to go, ${firstName}.`);
  });

  onDestroy(() => {
    stopSpeaking();
    if (wakeLock) wakeLock.release();
    if (timeInterval) clearInterval(timeInterval);
    if (recognition) recognition.abort();
  });

  // --- Renewals ---
  function filterRenewals() {
    const repName = ($user?.name || $user?.first_name || '').toLowerCase();
    if (renewalFilter === 'mine' && repName) {
      filteredRenewals = renewals.filter(r => (r.rep || '').toLowerCase().includes(repName.split(' ')[0]));
    } else {
      filteredRenewals = [...renewals];
    }
    // Sort by end date (soonest first)
    filteredRenewals.sort((a, b) => {
      const da = new Date(a.endDate || '2099-01-01');
      const db = new Date(b.endDate || '2099-01-01');
      return da - db;
    });
  }

  function toggleRenewalFilter() {
    renewalFilter = renewalFilter === 'mine' ? 'all' : 'mine';
    filterRenewals();
  }

  function openRenewal(r) {
    selectedRenewal = r;
    phase = 'renewal-detail';
    const text = `${r.business}. ${r.adSize} ad at ${r.store.split('-')[0]}. Contract ends ${r.endDate}. ${r.contactName ? 'Contact: ' + r.contactName : ''}`;
    speak(text);
  }

  function callRenewal() {
    if (selectedRenewal?.phone) {
      window.location.href = `tel:${selectedRenewal.phone}`;
    }
  }

  function emailRenewal() {
    if (selectedRenewal?.email) {
      const subject = encodeURIComponent(`Renewal — ${selectedRenewal.business}`);
      const body = encodeURIComponent(`Hi ${selectedRenewal.contactName || ''},\n\nI wanted to reach out about renewing your IndoorMedia advertising at ${selectedRenewal.store}.\n\nLooking forward to connecting!\n\n${$user?.name || firstName}`);
      window.location.href = `mailto:${selectedRenewal.email}?subject=${subject}&body=${body}`;
    }
  }

  // --- Media TTS ---
  let ttsAudio = null;

  // SpeechSynthesis fallback voice (Zoe preferred)
  let preferredVoice = null;

  function pickBestVoice() {
    const voices = window.speechSynthesis.getVoices();
    if (!voices.length) return null;
    const preferred = [
      'Zoe (Premium)', 'Zoe (Enhanced)', 'Zoe',
      'Samantha (Enhanced)', 'Ava (Premium)', 'Ava (Enhanced)',
      'Samantha', 'Ava', 'Karen',
      'Google US English',
    ];
    for (const name of preferred) {
      const match = voices.find(v => v.name.includes(name) && v.lang.startsWith('en'));
      if (match) return match;
    }
    const english = voices.filter(v => v.lang.startsWith('en'));
    return english.find(v => v.name.includes('Enhanced') || v.name.includes('Premium')) || english[0] || voices[0];
  }

  function initVoices() {
    preferredVoice = pickBestVoice();
    if (preferredVoice) console.log('[DrivingMode] Voice:', preferredVoice.name);
  }

  if (typeof window !== 'undefined' && window.speechSynthesis) {
    window.speechSynthesis.onvoiceschanged = initVoices;
    initVoices();
  }

  function speak(text) {
    return new Promise(async (resolve) => {
      stopSpeaking();
      speaking = true;

      // Try media audio first (routes to Bluetooth)
      const success = await tryMediaTTS(text);
      if (success) { resolve(); return; }

      // Fallback: SpeechSynthesis
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      if (preferredVoice) u.voice = preferredVoice;
      u.rate = 0.95; u.pitch = 1.05;
      u.onend = () => { speaking = false; resolve(); };
      u.onerror = () => { speaking = false; resolve(); };
      window.speechSynthesis.speak(u);
    });
  }

  async function tryMediaTTS(text) {
    try {
      const chunks = splitTextForTTS(text, 190);
      for (const chunk of chunks) {
        if (!speaking) break;
        const encoded = encodeURIComponent(chunk);
        const url = `https://translate.google.com/translate_tts?ie=UTF-8&tl=en&client=tw-ob&q=${encoded}`;
        await playAudioURL(url);
      }
      speaking = false;
      return true;
    } catch {
      speaking = false;
      return false;
    }
  }

  function splitTextForTTS(text, maxLen) {
    const chunks = [];
    const sentences = text.match(/[^.!?]+[.!?]+/g) || [text];
    let current = '';
    for (const sentence of sentences) {
      if ((current + sentence).length > maxLen && current) {
        chunks.push(current.trim());
        current = '';
      }
      current += sentence;
    }
    if (current.trim()) chunks.push(current.trim());
    return chunks;
  }

  function playAudioURL(url) {
    return new Promise((resolve, reject) => {
      const audio = new Audio(url);
      ttsAudio = audio;
      audio.volume = 1.0;
      audio.onended = () => { ttsAudio = null; resolve(); };
      audio.onerror = (e) => { ttsAudio = null; reject(e); };
      audio.play().catch(reject);
    });
  }

  function stopSpeaking() {
    if (ttsAudio) { ttsAudio.pause(); ttsAudio.currentTime = 0; ttsAudio = null; }
    window.speechSynthesis.cancel();
    speaking = false;
  }

  function listen() {
    if (!recognition) { statusText = 'Voice not supported'; return Promise.resolve(''); }
    return new Promise((resolve) => {
      listening = true;
      statusText = '🎤 Listening...';
      recognition.onresult = (e) => {
        const text = e.results[0][0].transcript;
        listening = false; statusText = '';
        resolve(text);
      };
      recognition.onerror = () => { listening = false; statusText = ''; resolve(''); };
      recognition.onend = () => { if (listening) { listening = false; statusText = ''; resolve(''); } };
      recognition.start();
    });
  }

  // --- Store Search ---
  function searchStores(query) {
    if (!query || query.length < 2) return [];
    const q = query.toLowerCase().trim();
    return allStores.filter(s => {
      const searchable = `${s.GroceryChain} ${s.City} ${s.State} ${s.StoreName} ${s.Address} ${s.Zip || ''}`.toLowerCase();
      return searchable.includes(q);
    }).slice(0, 8);
  }

  async function startStoreSearch() {
    phase = 'listening-store';
    await speak('What store are you working?');
    const heard = await listen();
    if (!heard) {
      statusText = 'Didn\'t catch that';
      phase = 'home';
      return;
    }
    statusText = `Heard: "${heard}"`;
    matchedStores = searchStores(heard);

    if (matchedStores.length === 0) {
      await speak(`No stores found for "${heard}". Try again.`);
      phase = 'home';
    } else if (matchedStores.length === 1) {
      selectedStore = matchedStores[0];
      await speak(`${selectedStore.GroceryChain}, ${selectedStore.City}. Pick a category.`);
      phase = 'categories';
    } else {
      await speak(`Found ${matchedStores.length} stores. Pick one.`);
      phase = 'store-results';
    }
  }

  function pickStore(store) {
    selectedStore = store;
    speak(`${store.GroceryChain}, ${store.City}. Pick a category.`);
    phase = 'categories';
  }

  function pickCategory(cat) {
    selectedCategory = cat;
    phase = 'subcategories';
  }

  async function pickSubcategory(sub) {
    phase = 'searching';
    statusText = `Searching ${sub}...`;
    await speak(`Searching for ${sub} near ${selectedStore?.GroceryChain}.`);

    try {
      const keyword = CATEGORY_KEYWORDS[sub] || sub.toLowerCase();
      const lat = selectedStore?.latitude || selectedStore?.Latitude || 0;
      const lng = selectedStore?.longitude || selectedStore?.Longitude || 0;
      const query = `${keyword} near ${selectedStore?.Address || ''} ${selectedStore?.City || ''} ${selectedStore?.State || ''}`;

      const requestBody = { textQuery: query, maxResultCount: 10 };
      if (lat && lng) {
        requestBody.locationBias = { circle: { center: { latitude: lat, longitude: lng }, radius: 16000.0 } };
      }

      const response = await fetch('https://places.googleapis.com/v1/places:searchText', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Goog-Api-Key': PLACES_API_KEY,
          'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.nationalPhoneNumber,places.websiteUri'
        },
        body: JSON.stringify(requestBody)
      });

      const data = await response.json();
      prospects = (data.places || []).map(p => ({
        name: p.displayName?.text || 'Unknown',
        address: p.formattedAddress || '',
        rating: p.rating || 0,
        reviews: p.userRatingCount || 0,
        phone: p.nationalPhoneNumber || null,
        website: p.websiteUri || null,
      }));
      currentProspectIndex = 0;

      if (prospects.length === 0) {
        await speak(`No ${sub} businesses found nearby.`);
        phase = 'categories';
      } else {
        phase = 'prospects';
        await presentCurrentProspect();
      }
    } catch (err) {
      console.error('Places search error:', err);
      await speak('Search failed. Try again.');
      phase = 'categories';
    }
  }

  async function presentCurrentProspect() {
    const p = prospects[currentProspectIndex];
    if (!p) {
      await speak('No more prospects. Pick another category.');
      phase = 'categories';
      return;
    }
    const num = currentProspectIndex + 1;
    let text = `${num} of ${prospects.length}. ${p.name}. `;
    if (p.rating) text += `${p.rating} stars. `;
    if (p.phone) text += `${p.phone}. `;
    await speak(text);
  }

  function callProspectNow() {
    const p = prospects[currentProspectIndex];
    if (p?.phone) window.location.href = `tel:${p.phone}`;
  }

  function saveNote() {
    const p = prospects[currentProspectIndex];
    if (!p || !noteText.trim()) return;
    const key = 'impro_prospect_notes';
    let notes = {};
    try { notes = JSON.parse(localStorage.getItem(key) || '{}'); } catch {}
    const id = p.name.replace(/\s+/g, '_').toLowerCase();
    notes[id] = { name: p.name, note: noteText.trim(), date: new Date().toISOString(), store: selectedStore?.StoreName || '' };
    localStorage.setItem(key, JSON.stringify(notes));
    speak(`Note saved.`);
    noteText = '';
    showNoteInput = false;
  }

  function voiceNote() {
    if (!recognition) { showNoteInput = true; return; }
    listen().then(heard => {
      if (heard) { noteText = heard; saveNote(); }
    });
  }

  function bookProspectAppt() {
    const p = prospects[currentProspectIndex];
    if (!p) return;
    const title = `IndoorMedia — ${p.name}`;
    const location = p.address || '';
    const repName = $user?.name || $user?.first_name || '';
    const details = `Prospect: ${p.name}\nAddress: ${p.address}\nPhone: ${p.phone || 'N/A'}\nStore: ${selectedStore?.GroceryChain || ''} ${selectedStore?.StoreName || ''}\nRep: ${repName}`;

    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(10, 0, 0, 0);
    const end = new Date(tomorrow);
    end.setHours(11, 0, 0, 0);
    const fmt = d => d.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';

    const gcalUrl = `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(title)}&dates=${fmt(tomorrow)}/${fmt(end)}&details=${encodeURIComponent(details)}&location=${encodeURIComponent(location)}&add=${encodeURIComponent('tyler.vansant@indoormedia.com')}`;
    window.open(gcalUrl, '_blank');
    speak(`Booking appointment for ${p.name}.`);
  }

  async function skipProspect() {
    currentProspectIndex++;
    if (currentProspectIndex >= prospects.length) {
      await speak('No more prospects.');
      phase = 'categories';
    } else {
      await presentCurrentProspect();
    }
  }

  function navigateToAppt() {
    if (!nextAppt?.location) return;
    window.open(`https://maps.apple.com/?daddr=${encodeURIComponent(nextAppt.location)}`, '_blank');
  }

  function goHome() {
    stopSpeaking();
    if (recognition) recognition.abort();
    phase = 'home';
    prospects = [];
    selectedStore = null;
    selectedCategory = null;
    selectedRenewal = null;
    statusText = '';
  }
</script>

<div class="driving-overlay">
  <div class="driving-header">
    <div class="driving-time">{currentTime.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}</div>
    {#if phase !== 'home'}
      <button class="driving-back" on:click={goHome}>← Home</button>
    {/if}
    <button class="driving-close" on:click={onClose}>✕</button>
  </div>

  {#if statusText}
    <div class="status-bar">{statusText}</div>
  {/if}

  <!-- HOME -->
  {#if phase === 'home'}
    <div class="driving-hero">
      {#if nextAppt}
        <div class="driving-appt">
          <div class="driving-appt-label">NEXT APPOINTMENT</div>
          <div class="driving-appt-title">{nextAppt.title || 'Appointment'}</div>
          <div class="driving-appt-time">
            {new Date(nextAppt.date).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
          </div>
          {#if nextAppt.location}
            <button class="nav-btn" on:click={navigateToAppt}>🗺️ Navigate</button>
          {/if}
        </div>
      {:else}
        <div class="driving-appt">
          <div class="driving-appt-title" style="font-size: 24px;">Ready to go 🎯</div>
        </div>
      {/if}
    </div>

    <div class="driving-actions">
      <button class="driving-big-btn btn-prospect" on:click={startStoreSearch}>
        🎯 Find Prospects
      </button>
      <button class="driving-big-btn btn-renewals" on:click={() => { filterRenewals(); phase = 'renewals'; }}>
        🔄 Renewals
        {#if filteredRenewals.length > 0}
          <span class="badge">{filteredRenewals.length}</span>
        {/if}
      </button>
    </div>

  <!-- STORE RESULTS -->
  {:else if phase === 'store-results'}
    <div class="phase-title">Pick a Store</div>
    <div class="scroll-list">
      {#each matchedStores as store}
        <button class="list-card" on:click={() => pickStore(store)}>
          <div class="list-card-name">{store.GroceryChain}</div>
          <div class="list-card-detail">{store.City}, {store.State} · {store.StoreName}</div>
          <div class="list-card-sub">{store.Address}</div>
        </button>
      {/each}
    </div>

  <!-- LISTENING FOR STORE -->
  {:else if phase === 'listening-store'}
    <div class="center-phase">
      <div class="mic-pulse">🎤</div>
      <div class="center-text">Say a store name, city, or address...</div>
    </div>

  <!-- CATEGORIES -->
  {:else if phase === 'categories'}
    <div class="phase-title">{selectedStore?.GroceryChain} — {selectedStore?.City}</div>
    <div class="cat-grid">
      {#each Object.keys(CATEGORIES) as cat}
        <button class="cat-btn" on:click={() => pickCategory(cat)}>{cat}</button>
      {/each}
    </div>

  <!-- SUBCATEGORIES -->
  {:else if phase === 'subcategories'}
    <div class="phase-title">{selectedCategory}</div>
    <div class="cat-grid sub-grid">
      {#each CATEGORIES[selectedCategory] as sub}
        <button class="cat-btn sub-btn" on:click={() => pickSubcategory(sub)}>{sub}</button>
      {/each}
    </div>

  <!-- SEARCHING -->
  {:else if phase === 'searching'}
    <div class="center-phase">
      <div class="mic-pulse">🔍</div>
      <div class="center-text">Searching...</div>
    </div>

  <!-- PROSPECTS -->
  {:else if phase === 'prospects'}
    {#if currentProspect}
      <div class="prospect-display">
        <div class="prospect-counter">{currentProspectIndex + 1} / {prospects.length}</div>
        <div class="prospect-name">{currentProspect.name}</div>
        {#if currentProspect.rating}
          <div class="prospect-rating">⭐ {currentProspect.rating} ({currentProspect.reviews})</div>
        {/if}
        <div class="prospect-addr">{currentProspect.address}</div>
        {#if currentProspect.phone}
          <div class="prospect-phone">📞 {currentProspect.phone}</div>
        {/if}
      </div>

      <div class="two-btn-row">
        {#if currentProspect.phone}
          <button class="yn-btn yn-call" on:click={callProspectNow}>📞 Call</button>
        {:else}
          <button class="yn-btn yn-skip" on:click={skipProspect}>⏭️ No Phone</button>
        {/if}
        <button class="yn-btn yn-next" on:click={skipProspect}>➡️ Next</button>
      </div>

      <div class="prospect-extras">
        <button class="extra-btn" on:click={bookProspectAppt}>📅 Book</button>
        <button class="extra-btn" on:click={() => showNoteInput ? saveNote() : (showNoteInput = true)}>
          📝 {showNoteInput ? 'Save' : 'Note'}
        </button>
        <button class="extra-btn" on:click={voiceNote}>🎤 Voice Note</button>
        <button class="extra-btn" on:click={() => presentCurrentProspect()}>🔊 Replay</button>
      </div>

      {#if showNoteInput}
        <div class="note-row">
          <input class="note-input" type="text" placeholder="Type a note..." bind:value={noteText}
            on:keydown={(e) => e.key === 'Enter' && saveNote()} />
        </div>
      {/if}
    {/if}

  <!-- RENEWALS LIST -->
  {:else if phase === 'renewals'}
    <div class="phase-header">
      <div class="phase-title">🔄 Pending Renewals</div>
      <button class="filter-toggle" on:click={toggleRenewalFilter}>
        {renewalFilter === 'mine' ? '👤 Mine' : '👥 All'} ({filteredRenewals.length})
      </button>
    </div>

    {#if filteredRenewals.length === 0}
      <div class="center-phase">
        <div class="center-text">No pending renewals{renewalFilter === 'mine' ? ' for you' : ''}.</div>
      </div>
    {:else}
      <div class="scroll-list">
        {#each filteredRenewals as r}
          <button class="list-card renewal-card" on:click={() => openRenewal(r)}>
            <div class="renewal-top">
              <div class="list-card-name">{r.business}</div>
              <div class="renewal-price">${r.contractPrice?.toLocaleString() || '—'}</div>
            </div>
            <div class="list-card-detail">
              {r.adSize} · {r.store} · Ends {r.endDate}
            </div>
            {#if r.contactName}
              <div class="list-card-sub">{r.contactName} · {r.phone || 'No phone'}</div>
            {/if}
          </button>
        {/each}
      </div>
    {/if}

  <!-- RENEWAL DETAIL -->
  {:else if phase === 'renewal-detail' && selectedRenewal}
    <div class="prospect-display">
      <div class="prospect-counter">RENEWAL</div>
      <div class="prospect-name">{selectedRenewal.business}</div>
      <div class="renewal-meta">
        <span>{selectedRenewal.adSize} Ad</span> · <span>{selectedRenewal.product}</span>
      </div>
      <div class="renewal-meta">Store: {selectedRenewal.store}</div>
      <div class="renewal-meta">Contract: {selectedRenewal.contractNumber} · ${selectedRenewal.contractPrice?.toLocaleString()}</div>
      <div class="renewal-meta">{selectedRenewal.startDate} → {selectedRenewal.endDate}</div>
      {#if selectedRenewal.contactName}
        <div class="prospect-addr" style="margin-top: 12px;">{selectedRenewal.contactName}</div>
      {/if}
      {#if selectedRenewal.phone}
        <div class="prospect-phone">📞 {selectedRenewal.phone}</div>
      {/if}
      {#if selectedRenewal.email}
        <div class="renewal-email">✉️ {selectedRenewal.email}</div>
      {/if}
      {#if selectedRenewal.address}
        <div class="prospect-addr">{selectedRenewal.address}, {selectedRenewal.city}, {selectedRenewal.state} {selectedRenewal.zip}</div>
      {/if}
    </div>

    <div class="two-btn-row">
      {#if selectedRenewal.phone}
        <button class="yn-btn yn-call" on:click={callRenewal}>📞 Call</button>
      {/if}
      {#if selectedRenewal.email}
        <button class="yn-btn yn-email" on:click={emailRenewal}>✉️ Email</button>
      {/if}
    </div>
  {/if}

  {#if listening}
    <div class="listening-indicator">
      <div class="pulse-ring"></div>
      <span>🎤 Listening...</span>
    </div>
  {/if}
</div>

<style>
  .driving-overlay {
    position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 9999;
    background: #0a0a0a; color: #fff;
    display: flex; flex-direction: column; padding: 16px;
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro', sans-serif;
    overflow-y: auto; -webkit-overflow-scrolling: touch;
  }

  .driving-header {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 12px; flex-shrink: 0; gap: 8px;
  }
  .driving-time { font-size: 18px; font-weight: 300; color: #aaa; flex: 1; }
  .driving-close, .driving-back {
    font-size: 15px; padding: 8px 14px; border-radius: 20px;
    border: 1px solid #444; background: none; color: #aaa; cursor: pointer;
  }
  .driving-back { border-color: #CC0000; color: #CC0000; }

  .status-bar {
    background: #1a1a2e; padding: 8px 14px; border-radius: 10px; font-size: 13px;
    color: #aaa; margin-bottom: 12px; text-align: center;
  }

  /* Home */
  .driving-hero { flex: 1; display: flex; align-items: center; justify-content: center; }
  .driving-appt { text-align: center; width: 100%; }
  .driving-appt-label { font-size: 11px; font-weight: 700; letter-spacing: 2px; color: #CC0000; margin-bottom: 8px; }
  .driving-appt-title { font-size: 26px; font-weight: 700; margin-bottom: 8px; line-height: 1.2; }
  .driving-appt-time { font-size: 18px; color: #aaa; margin-bottom: 16px; }
  .nav-btn { background: #1a73e8; color: white; border: none; border-radius: 12px; padding: 12px 24px; font-size: 16px; font-weight: 600; cursor: pointer; }

  /* Main action buttons */
  .driving-actions {
    display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
    flex-shrink: 0; margin-bottom: 8px;
    padding-bottom: env(safe-area-inset-bottom, 16px);
  }
  .driving-big-btn {
    padding: 28px 16px; border-radius: 18px; font-size: 22px; font-weight: 700;
    border: none; cursor: pointer; text-align: center; position: relative;
  }
  .driving-big-btn:active { opacity: 0.85; transform: scale(0.97); }
  .btn-prospect { background: #CC0000; color: white; }
  .btn-renewals { background: #1a73e8; color: white; }

  .badge {
    position: absolute; top: 10px; right: 12px;
    background: #fff; color: #1a73e8; font-size: 13px; font-weight: 800;
    padding: 2px 8px; border-radius: 12px; min-width: 20px;
  }

  /* Phase header */
  .phase-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-shrink: 0; }
  .phase-title { font-size: 18px; font-weight: 700; color: #CC0000; }
  .filter-toggle {
    background: #1a1a1a; color: #aaa; border: 1px solid #333; border-radius: 20px;
    padding: 6px 14px; font-size: 13px; font-weight: 600; cursor: pointer;
  }

  /* Scroll list (stores, renewals) */
  .scroll-list { display: flex; flex-direction: column; gap: 10px; flex: 1; overflow-y: auto; padding-bottom: 20px; }
  .list-card {
    background: #1a1a1a; border: 1px solid #333; border-radius: 14px;
    padding: 16px; text-align: left; cursor: pointer; color: #fff;
  }
  .list-card:active { background: #2a2a2a; border-color: #CC0000; }
  .list-card-name { font-size: 18px; font-weight: 700; }
  .list-card-detail { font-size: 13px; color: #aaa; margin-top: 4px; }
  .list-card-sub { font-size: 12px; color: #666; margin-top: 2px; }

  .renewal-top { display: flex; justify-content: space-between; align-items: baseline; }
  .renewal-price { font-size: 16px; font-weight: 700; color: #34a853; flex-shrink: 0; }
  .renewal-meta { font-size: 14px; color: #aaa; margin-top: 4px; }
  .renewal-email { font-size: 14px; color: #5cacf8; margin-top: 4px; }

  /* Center phase (listening, searching) */
  .center-phase { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; }
  .mic-pulse { font-size: 64px; animation: pulse 1.5s ease-in-out infinite; }
  .center-text { font-size: 18px; color: #aaa; margin-top: 16px; text-align: center; }

  @keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.15); opacity: 0.7; }
  }

  /* Categories */
  .cat-grid {
    display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;
    flex: 1; overflow-y: auto; align-content: start; padding-bottom: 20px;
  }
  .cat-btn {
    background: #1a1a1a; border: 1px solid #333; border-radius: 14px;
    padding: 16px 12px; font-size: 17px; font-weight: 600; color: #fff;
    cursor: pointer; text-align: center;
  }
  .cat-btn:active { background: #CC0000; border-color: #CC0000; }
  .sub-grid { grid-template-columns: repeat(3, 1fr); }
  .sub-btn { font-size: 14px; padding: 14px 8px; }

  /* Prospect display */
  .prospect-display {
    flex: 1; display: flex; flex-direction: column; align-items: center;
    justify-content: center; text-align: center; padding: 16px 0;
  }
  .prospect-counter { font-size: 12px; color: #666; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 12px; }
  .prospect-name { font-size: 28px; font-weight: 800; line-height: 1.2; margin-bottom: 8px; }
  .prospect-rating { font-size: 16px; color: #f5a623; margin-bottom: 8px; }
  .prospect-addr { font-size: 15px; color: #aaa; margin-bottom: 8px; line-height: 1.3; }
  .prospect-phone { font-size: 20px; font-weight: 600; color: #34a853; margin-top: 8px; }

  /* Two-button rows */
  .two-btn-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; flex-shrink: 0; }
  .yn-btn {
    padding: 22px 16px; border-radius: 16px; font-size: 22px; font-weight: 700;
    border: none; cursor: pointer; text-align: center;
  }
  .yn-btn:active { transform: scale(0.96); }
  .yn-call { background: #34a853; color: white; }
  .yn-email { background: #1a73e8; color: white; }
  .yn-next { background: #333; color: #ccc; }
  .yn-skip { background: #555; color: #ccc; }

  /* Prospect extras */
  .prospect-extras {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
    margin-top: 12px; flex-shrink: 0;
  }
  .extra-btn {
    padding: 12px 6px; border-radius: 12px; font-size: 13px; font-weight: 600;
    border: 1px solid #333; background: #1a1a1a; color: #ccc; cursor: pointer;
    text-align: center;
  }
  .extra-btn:active { transform: scale(0.96); background: #2a2a2a; }

  .note-row { margin-top: 10px; flex-shrink: 0; }
  .note-input {
    width: 100%; padding: 14px; border-radius: 12px; border: 1px solid #444;
    background: #1a1a1a; color: #fff; font-size: 16px; box-sizing: border-box;
    font-family: inherit;
  }
  .note-input::placeholder { color: #666; }

  /* Listening indicator */
  .listening-indicator {
    position: fixed; bottom: 100px; left: 50%; transform: translateX(-50%);
    background: #CC0000; padding: 10px 24px; border-radius: 30px;
    font-size: 16px; font-weight: 600; display: flex; align-items: center; gap: 8px;
  }
  .pulse-ring {
    width: 12px; height: 12px; background: white; border-radius: 50%;
    animation: pulse 1s ease-in-out infinite;
  }
</style>
