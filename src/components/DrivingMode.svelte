<script>
  import { onMount, onDestroy } from 'svelte';
  import { user } from '../lib/stores.js';

  export let appointments = [];
  export let dailyGoal = { calls: 0, target: 20 };
  export let savedProspects = 0;
  export let revenueThisMonth = 0;
  export let onClose = () => {};
  export let onLogCall = () => {};

  const PLACES_API_KEY = 'AIzaSyBoslNJj8aO6wkQOfkH9e4qTVJZ-G9nOuA';

  // State machine: home | listening-store | store-results | categories | subcategories | searching | prospects | calling
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

  export let onBookAppointment = null; // passed from Main

  $: firstName = ($user?.name || $user?.first_name || 'Rep').split(' ')[0];
  $: nextAppt = appointments.length > 0 ? appointments[0] : null;
  $: goalPercent = Math.min((dailyGoal.calls / (dailyGoal.target || 20)) * 100, 100);
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

    // Setup speech recognition
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';
    }

    // Force audio to media channel (Bluetooth/car speakers)
    ensureMediaAudioRoute();

    speakBriefing();
  });

  onDestroy(() => {
    releaseMediaAudioRoute();
    if (wakeLock) wakeLock.release();
    if (timeInterval) clearInterval(timeInterval);
    if (recognition) recognition.abort();
    window.speechSynthesis.cancel();
  });

  // --- Audio routing: force Bluetooth/media channel ---
  let audioCtx = null;
  let silentSource = null;

  /**
   * On iOS and Android, SpeechSynthesis often plays through the phone earpiece/speaker
   * instead of Bluetooth because it's classified as a "telephony" or "system" sound.
   * Creating an AudioContext and playing a silent buffer forces the OS to route ALL audio
   * through the "media" channel, which goes to Bluetooth speakers/car systems.
   */
  function ensureMediaAudioRoute() {
    if (audioCtx) return; // already set up
    try {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      // Create a silent oscillator that keeps the audio session alive
      silentSource = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      gain.gain.value = 0.001; // essentially silent
      silentSource.connect(gain);
      gain.connect(audioCtx.destination);
      silentSource.start();
      console.log('[DrivingMode] Media audio route established for Bluetooth');
    } catch (e) {
      console.warn('[DrivingMode] Could not create audio context:', e);
    }
  }

  function releaseMediaAudioRoute() {
    try {
      if (silentSource) { silentSource.stop(); silentSource = null; }
      if (audioCtx) { audioCtx.close(); audioCtx = null; }
    } catch {}
  }

  // --- Speech ---
  let preferredVoice = null;

  // Rank voices by quality — iOS/macOS premium voices first
  function pickBestVoice() {
    const voices = window.speechSynthesis.getVoices();
    if (!voices.length) return null;

    // Priority list: best-sounding English voices on Apple devices
    const preferred = [
      'Samantha (Enhanced)', 'Ava (Premium)', 'Ava (Enhanced)', 'Zoe (Premium)', 'Zoe (Enhanced)',
      'Allison (Enhanced)', 'Tom (Enhanced)', 'Evan (Enhanced)',
      'Samantha', 'Ava', 'Zoe', 'Allison', 'Tom',
      'Karen', 'Daniel', 'Google US English', 'Google UK English Female',
      'Microsoft Zira', 'Microsoft David',
    ];

    for (const name of preferred) {
      const match = voices.find(v => v.name.includes(name) && v.lang.startsWith('en'));
      if (match) return match;
    }

    // Fallback: best English voice available
    const english = voices.filter(v => v.lang.startsWith('en'));
    // Prefer non-compact, non-default voices (they tend to be higher quality)
    const enhanced = english.find(v => v.name.includes('Enhanced') || v.name.includes('Premium'));
    if (enhanced) return enhanced;

    return english[0] || voices[0];
  }

  function initVoices() {
    preferredVoice = pickBestVoice();
    if (preferredVoice) console.log('[DrivingMode] Using voice:', preferredVoice.name);
  }

  // Voices load async on some browsers
  if (typeof window !== 'undefined' && window.speechSynthesis) {
    window.speechSynthesis.onvoiceschanged = initVoices;
    initVoices();
  }

  function speak(text) {
    return new Promise((resolve) => {
      // Resume audio context on user gesture (iOS requirement)
      if (audioCtx && audioCtx.state === 'suspended') {
        audioCtx.resume();
      }
      window.speechSynthesis.cancel();
      speaking = true;
      const u = new SpeechSynthesisUtterance(text);
      if (preferredVoice) u.voice = preferredVoice;
      u.rate = 0.95; u.pitch = 1.05;
      u.onend = () => { speaking = false; resolve(); };
      u.onerror = () => { speaking = false; resolve(); };
      window.speechSynthesis.speak(u);
    });
  }

  function stopSpeaking() {
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
        listening = false;
        statusText = '';
        resolve(text);
      };
      recognition.onerror = () => { listening = false; statusText = ''; resolve(''); };
      recognition.onend = () => { if (listening) { listening = false; statusText = ''; resolve(''); } };
      recognition.start();
    });
  }

  // --- Briefing ---
  async function speakBriefing() {
    const hour = new Date().getHours();
    const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
    let text = `${greeting}, ${firstName}. `;

    if (appointments.length === 0) {
      text += `No appointments on deck. `;
    } else {
      const a = appointments[0];
      const time = new Date(a.date).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
      text += `Next up: ${a.title || 'Appointment'} at ${time}. `;
      if (appointments.length > 1) text += `Plus ${appointments.length - 1} more. `;
    }

    text += `${dailyGoal.calls} of ${dailyGoal.target || 20} calls logged. `;
    if (revenueThisMonth > 0) text += `$${Math.round(revenueThisMonth / 1000)}K this month. `;
    text += `Tap Find Prospects to start voice prospecting.`;

    await speak(text);
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
    await speak('What store would you like to work? Say the city, street, store number, or chain name.');
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
      await speak(`Found ${selectedStore.GroceryChain} in ${selectedStore.City}. What category?`);
      phase = 'categories';
    } else {
      await speak(`Found ${matchedStores.length} stores. Pick one.`);
      phase = 'store-results';
    }
  }

  function pickStore(store) {
    selectedStore = store;
    speak(`${store.GroceryChain}, ${store.City}. What category?`);
    phase = 'categories';
  }

  function pickCategory(cat) {
    selectedCategory = cat;
    phase = 'subcategories';
  }

  async function pickSubcategory(sub) {
    phase = 'searching';
    statusText = `Searching ${sub} near ${selectedStore?.GroceryChain}...`;
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
        await speak(`No ${sub} businesses found nearby. Try a different category.`);
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
      await speak('That\'s all the prospects. Want to search another category?');
      phase = 'categories';
      return;
    }
    const num = currentProspectIndex + 1;
    const total = prospects.length;
    let text = `Number ${num} of ${total}. ${p.name}. `;
    if (p.rating) text += `Rated ${p.rating} stars with ${p.reviews} reviews. `;
    text += `${p.address}. `;
    if (p.phone) text += `Phone: ${p.phone}. `;
    text += `Call them now?`;
    await speak(text);
  }

  function callProspectNow() {
    const p = prospects[currentProspectIndex];
    if (p?.phone) {
      onLogCall();
      window.location.href = `tel:${p.phone}`;
    }
  }

  function saveNote() {
    const p = prospects[currentProspectIndex];
    if (!p || !noteText.trim()) return;
    // Save to localStorage keyed by prospect name
    const key = 'impro_prospect_notes';
    let notes = {};
    try { notes = JSON.parse(localStorage.getItem(key) || '{}'); } catch {}
    const id = p.name.replace(/\s+/g, '_').toLowerCase();
    notes[id] = { name: p.name, note: noteText.trim(), date: new Date().toISOString(), store: selectedStore?.StoreName || '' };
    localStorage.setItem(key, JSON.stringify(notes));
    speak(`Note saved for ${p.name}.`);
    noteText = '';
    showNoteInput = false;
  }

  function voiceNote() {
    if (!recognition) { showNoteInput = true; return; }
    listen().then(heard => {
      if (heard) {
        noteText = heard;
        saveNote();
      }
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
      await speak('No more prospects. Search another category?');
      phase = 'categories';
    } else {
      await presentCurrentProspect();
    }
  }

  // --- Voice Q&A about stores ---
  let qaAnswer = '';

  async function startAskQuestion() {
    phase = 'asking';
    await speak('What would you like to know? Ask about a store\'s case count, pricing, cycle, or anything else.');
    const heard = await listen();
    if (!heard) {
      statusText = 'Didn\'t catch that';
      phase = 'home';
      return;
    }
    statusText = `"${heard}"`;
    await answerQuestion(heard);
  }

  async function answerQuestion(question) {
    const q = question.toLowerCase();

    // Try to find a store reference in the question
    let store = null;
    if (selectedStore) {
      // If we already have a store selected, use it as default context
      store = selectedStore;
    }
    // Try to match a store from the question text
    const bestMatch = findStoreInQuestion(q);
    if (bestMatch) store = bestMatch;

    if (!store) {
      // No store found — ask them to specify
      qaAnswer = 'I couldn\'t identify a store. Try saying the store name, city, or number.';
      await speak(qaAnswer);
      phase = 'home';
      return;
    }

    // Parse what they're asking about
    if (q.includes('case count') || q.includes('cases') || q.includes('how many cases')) {
      const cases = store['Case Count'] || 'unknown';
      qaAnswer = `${store.GroceryChain} in ${store.City} has ${cases} cases.`;
    } else if (q.includes('lowest price') || q.includes('cheapest') || q.includes('co-op') || q.includes('coop') || q.includes('best price') || q.includes('minimum') || q.includes('manager approved')) {
      const singleBase = store.SingleAd || 0;
      const doubleBase = store.DoubleAd || 0;

      // Paid-in-full (15% off) + $125 production = lowest possible
      const lowestSingle = Math.round((singleBase * 0.85) + 125);
      const lowestDouble = Math.round((doubleBase * 0.85) + 125);

      // Also calculate monthly
      const monthlySingle = Math.round(((singleBase + 125) / 12));

      qaAnswer = `${store.GroceryChain} in ${store.City}. ` +
        `Single ad base price: $${singleBase.toLocaleString()}. ` +
        `Lowest paid-in-full with co-op: $${lowestSingle.toLocaleString()}. ` +
        `Monthly payment: $${monthlySingle.toLocaleString()} per month for 12 months. ` +
        `Double ad base: $${doubleBase.toLocaleString()}, lowest: $${lowestDouble.toLocaleString()}.`;
    } else if (q.includes('price') || q.includes('cost') || q.includes('how much') || q.includes('rate')) {
      const singleBase = store.SingleAd || 0;
      const doubleBase = store.DoubleAd || 0;
      const production = 125;

      const monthly = Math.round((singleBase + production) / 12);
      const threeMonth = Math.round(((singleBase * 0.90) + production) / 3);
      const sixMonth = Math.round(((singleBase * 0.925) + production) / 6);
      const paidInFull = Math.round((singleBase * 0.85) + production);

      qaAnswer = `${store.GroceryChain} in ${store.City}. Single ad: $${singleBase.toLocaleString()} base. ` +
        `Monthly: $${monthly} times 12. ` +
        `3-month: $${threeMonth} times 3, that's 10% off. ` +
        `6-month: $${sixMonth} times 6, 7 and a half percent off. ` +
        `Paid in full: $${paidInFull}, 15% off. ` +
        `Double ad base: $${doubleBase.toLocaleString()}.`;
    } else if (q.includes('cycle') || q.includes('when') || q.includes('install')) {
      qaAnswer = `${store.GroceryChain} in ${store.City} is on Cycle ${store.Cycle || '?'}. ` +
        `Zone ${store.ZoneName || '?'}. Install day: ${store.InstallDay || '?'}.`;
    } else if (q.includes('address') || q.includes('where') || q.includes('location')) {
      qaAnswer = `${store.GroceryChain} is at ${store.Address}, ${store.City}, ${store.State} ${store.PostalCode || ''}.`;
    } else if (q.includes('store number') || q.includes('store name') || q.includes('store id')) {
      qaAnswer = `Store number: ${store.StoreName}. ${store.GroceryChain}, ${store.City}, ${store.State}. Zone ${store.ZoneName || '?'}, Cycle ${store.Cycle || '?'}.`;
    } else {
      // General store info dump
      qaAnswer = `${store.GroceryChain} in ${store.City}, ${store.State}. ` +
        `Store ${store.StoreName}. ${store['Case Count'] || '?'} cases. Cycle ${store.Cycle || '?'}. ` +
        `Single ad: $${(store.SingleAd || 0).toLocaleString()}. Double ad: $${(store.DoubleAd || 0).toLocaleString()}.`;
    }

    phase = 'qa-answer';
    await speak(qaAnswer);
  }

  function findStoreInQuestion(q) {
    // Try progressively broader matching
    let best = null;
    let bestScore = 0;

    for (const s of allStores) {
      let score = 0;
      const chain = (s.GroceryChain || '').toLowerCase();
      const city = (s.City || '').toLowerCase();
      const storeNum = (s.StoreName || '').toLowerCase();
      const addr = (s.Address || '').toLowerCase();
      const zip = (s.PostalCode || '').toLowerCase();

      if (q.includes(storeNum)) score += 100;
      if (zip && q.includes(zip)) score += 50;
      if (city && q.includes(city)) score += 30;
      if (chain && q.includes(chain.split(' ')[0])) score += 20;
      // Check for partial street name matches
      const streetWords = addr.split(/\s+/).filter(w => w.length > 3);
      for (const w of streetWords) {
        if (q.includes(w)) score += 15;
      }

      if (score > bestScore) {
        bestScore = score;
        best = s;
      }
    }

    return bestScore >= 20 ? best : null;
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
    <div class="driving-section">
      {#if nextAppt}
        <div class="driving-appt">
          <div class="driving-appt-label">NEXT UP</div>
          <div class="driving-appt-title">{nextAppt.title || 'Appointment'}</div>
          <div class="driving-appt-time">
            {new Date(nextAppt.date).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
          </div>
          {#if nextAppt.location}
            <button class="driving-btn driving-btn-nav" on:click={navigateToAppt}>🗺️ Navigate</button>
          {/if}
        </div>
      {:else}
        <div class="driving-appt">
          <div class="driving-appt-title" style="font-size: 22px;">Ready to prospect 🎯</div>
        </div>
      {/if}
    </div>

    <div class="driving-stats">
      <div class="driving-stat">
        <div class="driving-stat-value">{dailyGoal.calls}/{dailyGoal.target || 20}</div>
        <div class="driving-stat-label">Calls</div>
        <div class="driving-goal-bar"><div class="driving-goal-fill" style="width: {goalPercent}%"></div></div>
      </div>
      <div class="driving-stat">
        <div class="driving-stat-value">{appointments.length}</div>
        <div class="driving-stat-label">Appts</div>
      </div>
      <div class="driving-stat">
        <div class="driving-stat-value">${(revenueThisMonth / 1000).toFixed(1)}K</div>
        <div class="driving-stat-label">Month</div>
      </div>
    </div>

    <div class="driving-actions">
      <button class="driving-big-btn driving-big-prospect" on:click={startStoreSearch}>
        🎯 Find Prospects
      </button>
      <button class="driving-big-btn driving-big-ask" on:click={startAskQuestion}>
        🗣️ Ask a Question
      </button>
    </div>
    <div class="driving-actions" style="margin-top: 0;">
      <button class="driving-big-btn driving-big-log" on:click={onLogCall}>
        📞 Log Call
      </button>
      <button class="driving-big-btn driving-big-brief" on:click={speaking ? stopSpeaking : speakBriefing}>
        {speaking ? '⏹️ Stop' : '🔊 Briefing'}
      </button>
    </div>

  <!-- STORE RESULTS (multiple matches) -->
  {:else if phase === 'store-results'}
    <div class="phase-title">Pick a Store</div>
    <div class="store-list">
      {#each matchedStores as store}
        <button class="store-pick" on:click={() => pickStore(store)}>
          <div class="store-pick-name">{store.GroceryChain}</div>
          <div class="store-pick-detail">{store.City}, {store.State} · {store.StoreName}</div>
          <div class="store-pick-addr">{store.Address}</div>
        </button>
      {/each}
    </div>

  <!-- LISTENING FOR STORE -->
  {:else if phase === 'listening-store'}
    <div class="listening-phase">
      <div class="mic-pulse">🎤</div>
      <div class="listening-text">Say a store name, city, or address...</div>
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

  <!-- ASKING A QUESTION -->
  {:else if phase === 'asking'}
    <div class="listening-phase">
      <div class="mic-pulse">🗣️</div>
      <div class="listening-text">Ask about case counts, pricing, cycles...</div>
    </div>

  <!-- Q&A ANSWER -->
  {:else if phase === 'qa-answer'}
    <div class="qa-display">
      <div class="qa-answer-text">{qaAnswer}</div>
    </div>
    <div class="driving-actions">
      <button class="driving-big-btn driving-big-ask" on:click={startAskQuestion}>
        🗣️ Ask Another
      </button>
      <button class="driving-big-btn driving-big-log" on:click={goHome}>
        🏠 Home
      </button>
    </div>
    <button class="driving-brief-btn" style="margin-top: 8px;" on:click={() => speak(qaAnswer)}>
      🔊 Read Again
    </button>

  <!-- SEARCHING -->
  {:else if phase === 'searching'}
    <div class="listening-phase">
      <div class="mic-pulse">🔍</div>
      <div class="listening-text">Searching...</div>
    </div>

  <!-- PROSPECTS — one at a time, big Yes/No -->
  {:else if phase === 'prospects'}
    {#if currentProspect}
      <div class="prospect-display">
        <div class="prospect-counter">{currentProspectIndex + 1} of {prospects.length}</div>
        <div class="prospect-name">{currentProspect.name}</div>
        {#if currentProspect.rating}
          <div class="prospect-rating">⭐ {currentProspect.rating} ({currentProspect.reviews} reviews)</div>
        {/if}
        <div class="prospect-addr">{currentProspect.address}</div>
        {#if currentProspect.phone}
          <div class="prospect-phone">📞 {currentProspect.phone}</div>
        {/if}
      </div>

      <div class="yes-no-actions">
        {#if currentProspect.phone}
          <button class="yn-btn yn-yes" on:click={callProspectNow}>
            📞 Call
          </button>
        {:else}
          <button class="yn-btn yn-skip" on:click={skipProspect}>
            ⏭️ No Phone
          </button>
        {/if}
        <button class="yn-btn yn-no" on:click={skipProspect}>
          ➡️ Skip
        </button>
      </div>

      <div class="prospect-extras">
        <button class="extra-btn extra-book" on:click={bookProspectAppt}>📅 Book Appt</button>
        <button class="extra-btn extra-note" on:click={() => showNoteInput ? saveNote() : (showNoteInput = true)}>📝 {showNoteInput ? 'Save Note' : 'Add Note'}</button>
        <button class="extra-btn extra-voice" on:click={voiceNote}>🎤 Voice Note</button>
        <button class="extra-btn extra-read" on:click={() => presentCurrentProspect()}>🔊 Replay</button>
      </div>

      {#if showNoteInput}
        <div class="note-input-row">
          <input class="note-input" type="text" placeholder="Type a note..." bind:value={noteText} on:keydown={(e) => e.key === 'Enter' && saveNote()} />
        </div>
      {/if}
    {/if}
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

  .driving-section { flex: 1; display: flex; align-items: center; justify-content: center; }

  .driving-appt { text-align: center; width: 100%; }
  .driving-appt-label { font-size: 12px; font-weight: 700; letter-spacing: 2px; color: #CC0000; margin-bottom: 8px; }
  .driving-appt-title { font-size: 26px; font-weight: 700; margin-bottom: 8px; line-height: 1.2; }
  .driving-appt-time { font-size: 18px; color: #aaa; margin-bottom: 16px; }

  .driving-btn {
    padding: 14px 28px; border-radius: 14px; font-size: 18px; font-weight: 600;
    border: none; cursor: pointer; display: inline-block; margin: 4px;
  }
  .driving-btn-nav { background: #1a73e8; color: white; }
  .driving-btn:active { opacity: 0.8; transform: scale(0.97); }

  .driving-stats {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;
    margin: 16px 0; flex-shrink: 0;
  }
  .driving-stat { background: #1a1a1a; border-radius: 14px; padding: 12px; text-align: center; }
  .driving-stat-value { font-size: 24px; font-weight: 700; }
  .driving-stat-label { font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-top: 2px; }
  .driving-goal-bar { height: 4px; background: #333; border-radius: 2px; margin-top: 6px; overflow: hidden; }
  .driving-goal-fill { height: 100%; background: #CC0000; border-radius: 2px; transition: width 0.3s; }

  .driving-actions {
    display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
    flex-shrink: 0; margin-bottom: 8px;
  }
  .driving-big-btn {
    padding: 20px; border-radius: 16px; font-size: 20px; font-weight: 700;
    border: none; cursor: pointer; text-align: center;
  }
  .driving-big-btn:active { opacity: 0.8; transform: scale(0.97); }
  .driving-big-prospect { background: #CC0000; color: white; }
  .driving-big-ask { background: #1a73e8; color: white; }
  .driving-big-log { background: #2a2a2a; color: white; border: 1px solid #444; }
  .driving-big-brief { background: #1a1a1a; color: #aaa; border: 1px solid #333; }

  /* Q&A display */
  .qa-display { flex: 1; display: flex; align-items: center; justify-content: center; padding: 20px; }
  .qa-answer-text { font-size: 20px; line-height: 1.5; text-align: center; color: #fff; }

  .driving-brief-btn {
    width: 100%; padding: 12px; border-radius: 12px; font-size: 16px; font-weight: 600;
    background: #1a1a1a; color: #aaa; border: 1px solid #333; cursor: pointer;
    margin-bottom: env(safe-area-inset-bottom, 8px);
  }

  /* Store picking */
  .phase-title {
    font-size: 18px; font-weight: 700; text-align: center; margin-bottom: 16px;
    color: #CC0000; flex-shrink: 0;
  }
  .store-list { display: flex; flex-direction: column; gap: 10px; flex: 1; overflow-y: auto; }
  .store-pick {
    background: #1a1a1a; border: 1px solid #333; border-radius: 14px;
    padding: 16px; text-align: left; cursor: pointer; color: #fff;
  }
  .store-pick:active { background: #2a2a2a; border-color: #CC0000; }
  .store-pick-name { font-size: 18px; font-weight: 700; }
  .store-pick-detail { font-size: 13px; color: #aaa; margin-top: 2px; }
  .store-pick-addr { font-size: 12px; color: #666; margin-top: 2px; }

  /* Listening state */
  .listening-phase { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; }
  .mic-pulse { font-size: 64px; animation: pulse 1.5s ease-in-out infinite; }
  .listening-text { font-size: 18px; color: #aaa; margin-top: 16px; }

  @keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.15); opacity: 0.7; }
  }

  /* Categories */
  .cat-grid {
    display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;
    flex: 1; overflow-y: auto; align-content: start;
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

  /* Yes / No */
  .yes-no-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; flex-shrink: 0; }
  .yn-btn {
    padding: 24px 16px; border-radius: 16px; font-size: 22px; font-weight: 700;
    border: none; cursor: pointer; text-align: center;
  }
  .yn-btn:active { transform: scale(0.96); }

  /* Prospect extras row */
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
  .extra-book { border-color: #1a73e8; color: #5cacf8; }
  .extra-note { border-color: #f5a623; color: #f5c869; }
  .extra-voice { border-color: #CC0000; color: #ff6666; }
  .extra-read { border-color: #555; color: #999; }

  .note-input-row { margin-top: 10px; flex-shrink: 0; }
  .note-input {
    width: 100%; padding: 14px; border-radius: 12px; border: 1px solid #444;
    background: #1a1a1a; color: #fff; font-size: 16px; box-sizing: border-box;
    font-family: inherit;
  }
  .note-input::placeholder { color: #666; }
  .yn-yes { background: #34a853; color: white; }
  .yn-no { background: #333; color: #ccc; }
  .yn-skip { background: #555; color: #ccc; }

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
