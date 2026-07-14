<script>
  import { user } from '../lib/stores.js';
  import { onMount } from 'svelte';
  import StoreSearchInput from '../lib/StoreSearchInput.svelte';

  export let onBack = () => {};
  // Optional: prefill from a prospect card and auto-run the prep.
  // Shape: { name, address, phone, category, website, types, store }
  export let prefill = null;

  let businessName = '';
  let businessAddress = '';
  let businessPhone = '';
  let businessCategory = '';
  let businessWebsite = '';
  let businessTypes = []; // Google Places types for smarter matching
  let additionalInfo = '';
  let storeSearch = '';
  let selectedStore = null;
  let allStores = [];
  let storeResults = [];
  let showStoreDropdown = false;

  let step = 'search'; // search, loading, results
  let loadingStatus = '';
  let loadingStep = 0;

  // Results
  let businessInfo = null;
  let matchedTestimonials = [];
  let localTestimonial = null;
  let searchResults = [];
  let searching = false;
  let allTestimonials = [];
  let showTestimonialModal = false;

  onMount(async () => {
    try {
      const storeRes = await fetch(import.meta.env.BASE_URL + 'data/stores.json?t=' + Date.now());
      allStores = await storeRes.json();
    } catch {}
    // Load testimonials lazily (don't block UI)
    try {
      const testRes = await fetch(import.meta.env.BASE_URL + 'data/testimonials_slim.json?t=' + Date.now());
      allTestimonials = await testRes.json();
    } catch {
      // Fallback to full cache
      try {
        const testRes2 = await fetch(import.meta.env.BASE_URL + 'data/testimonials_cache.json?t=' + Date.now());
        allTestimonials = await testRes2.json();
      } catch {}
    }

    // If launched from a prospect card, prefill fields and run prep automatically.
    if (prefill && prefill.name) {
      businessName = prefill.name || '';
      businessAddress = prefill.address || '';
      businessPhone = prefill.phone || '';
      businessCategory = prefill.category || '';
      businessWebsite = prefill.website || '';
      businessTypes = prefill.types || [];
      if (prefill.store) selectStore(prefill.store);
      searchResults = [];
      await runPrep();
    }
  });

  function selectStore(store) {
    selectedStore = store;
    storeSearch = `${store.GroceryChain} — ${store.City}, ${store.State} (${store.StoreName})`;
  }

  // Business search with location bias
  async function searchBusiness() {
    if (!businessName.trim() || businessName.length < 3) return;
    searching = true;
    try {
      const apiKey = import.meta.env.VITE_GOOGLE_PLACES_API_KEY || 'AIzaSyBNR8M1VG5DccJmK6ZzJOam9mF8jOCEEqM';
      const body = { textQuery: businessName, maxResultCount: 5 };
      if (selectedStore?.latitude && selectedStore?.longitude) {
        body.locationBias = { circle: { center: { latitude: selectedStore.latitude, longitude: selectedStore.longitude }, radius: 8000.0 } };
      }
      const res = await fetch('https://places.googleapis.com/v1/places:searchText', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Goog-Api-Key': apiKey,
          'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.primaryTypeDisplayName,places.types' },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      searchResults = (data.places || []).map(p => ({
        name: p.displayName?.text || '', address: p.formattedAddress || '',
        phone: p.nationalPhoneNumber || '', website: p.websiteUri || '',
        category: p.primaryTypeDisplayName?.text || '',
        types: p.types || []
      }));
    } catch { searchResults = []; }
    searching = false;
  }

  function selectBusiness(biz) {
    businessName = biz.name; businessAddress = biz.address; businessPhone = biz.phone;
    businessCategory = biz.category; businessWebsite = biz.website;
    businessTypes = biz.types || [];
    searchResults = [];
  }

  // ===== MAIN PREP FUNCTION =====
  async function runPrep() {
    if (!businessName.trim()) return alert('Please enter a business name');
    step = 'loading';
    loadingStep = 1;
    loadingStatus = '🔍 Looking up business details...';
    
    businessInfo = {
      name: businessName,
      address: businessAddress,
      phone: businessPhone,
      category: businessCategory,
      website: businessWebsite,
      services: [],
      menuItems: [],
      websiteData: null
    };

    // Step 1: Try to scrape website for services/menu
    loadingStep = 2;
    loadingStatus = '🌐 Checking website & social media...';
    
    if (businessWebsite) {
      businessInfo.websiteData = businessWebsite;
    }

    // Find category-matched testimonials
    loadingStep = 3;
    loadingStatus = '📝 Finding matching testimonials...';
    await new Promise(r => setTimeout(r, 100)); // brief yield for UI update
    
    const detectedCats = detectProspectCategories(businessCategory, businessName, businessTypes);
    const { keywords: categoryKeywords, exclude: excludeWords } = extractCategoryKeywords(businessCategory, businessName, businessTypes);
    matchedTestimonials = findMatchingTestimonials(detectedCats, categoryKeywords, excludeWords, businessName, additionalInfo);

    // Find local testimonial
    loadingStep = 4;
    loadingStatus = '📍 Finding local testimonials...';
    localTestimonial = findLocalTestimonial(detectedCats);

    step = 'results';
  }

  // ===== Category taxonomy — MUST match tags produced by scripts/enrich_testimonials.py =====
  // Maps Google Places category text / types / business name -> enrichment category tags.
  function detectProspectCategories(category, name, placeTypes = []) {
    const combined = (String(category || '') + ' ' + String(name || '') + ' ' + (placeTypes || []).join(' ')).toLowerCase();
    // tag -> substrings that imply it (checked against Google category/name/types)
    const map = {
      pizza:            ['pizza', 'pizzeria'],
      mexican:          ['mexican', 'taco', 'taqueria', 'burrito', 'cantina', 'enchilada'],
      sushi_japanese:   ['sushi', 'japanese', 'ramen', 'teriyaki', 'hibachi', 'poke'],
      chinese:          ['chinese', 'wok', 'dim sum', 'szechuan', 'hunan'],
      thai:             ['thai'],
      indian:           ['indian', 'tandoori', 'masala', 'biryani', 'curry'],
      bbq_burger:       ['burger', 'bbq', 'barbecue', 'barbeque', 'smokehouse', 'wings', 'ribs', 'brisket'],
      seafood:          ['seafood', 'fish', 'crab', 'lobster', 'oyster', 'shrimp'],
      coffee:           ['coffee', 'espresso', 'cafe', 'café', 'tea house', 'roaster'],
      bakery:           ['bakery', 'donut', 'doughnut', 'pastry', 'cake', 'bagel', 'patisserie'],
      dessert:          ['ice cream', 'frozen yogurt', 'gelato', 'creamery', 'custard', 'smoothie', 'dessert', 'candy', 'chocolate'],
      sandwich_deli:    ['sandwich', 'sub ', 'subs', 'deli', 'hoagie', 'cheesesteak'],
      bar_brewery:      ['bar', 'pub', 'tavern', 'taproom', 'brewery', 'brewing', 'alehouse', 'saloon', 'lounge', 'nightclub', 'cocktail', 'wine bar', 'barrel'],
      restaurant:       ['restaurant', 'diner', 'bistro', 'eatery', 'kitchen', 'grill', 'cuisine', 'steakhouse', 'buffet', 'food', 'meal_'],
      salon_beauty:     ['salon', 'hair', 'beauty', 'lash', 'brow', 'stylist', 'waxing', 'skincare', 'esthetic'],
      barber:           ['barber', 'barbershop'],
      nails:            ['nail', 'manicure', 'pedicure'],
      spa_massage:      ['massage', 'spa', 'reflexology', 'facial', 'wellness'],
      auto_repair:      ['auto', 'automotive', 'mechanic', 'oil change', 'brake', 'transmission', 'car_repair', 'muffler', 'smog', 'collision', 'body shop', 'lube'],
      tires:            ['tire', 'wheel'],
      car_wash:         ['car wash', 'carwash', 'detailing', 'auto detail'],
      dental:           ['dental', 'dentist', 'orthodont', 'endodont'],
      medical:          ['medical', 'clinic', 'urgent care', 'physician', 'doctor', 'health', 'pediatric', 'dermatolog', 'optometry', 'eye care', 'pharmacy'],
      chiropractic:     ['chiropract', 'spine'],
      gym_fitness:      ['gym', 'fitness', 'crossfit', 'yoga', 'pilates', 'martial arts', 'jiu jitsu', 'boxing'],
      vet_pet:          ['vet', 'veterinar', 'pet', 'animal', 'grooming', 'kennel'],
      insurance:        ['insurance', 'allstate', 'state farm', 'geico', 'agency'],
      real_estate:      ['real estate', 'realtor', 'realty', 'properties', 'brokerage'],
      mortgage:         ['mortgage', 'lending', 'loan', 'escrow'],
      cleaning:         ['cleaning', 'maid', 'janitorial', 'housekeeping'],
      plumbing:         ['plumb', 'drain', 'rooter', 'sewer'],
      hvac:             ['hvac', 'heating', 'air condition', 'furnace', 'cooling', 'refrigeration'],
      electrical:       ['electric', 'electrician', 'wiring'],
      roofing:          ['roof', 'gutter'],
      landscaping:      ['landscap', 'lawn', 'tree service', 'nursery', 'garden center', 'sprinkler', 'irrigation'],
      pest_control:     ['pest', 'exterminat', 'termite'],
      tax_accounting:   ['tax', 'accounting', 'cpa', 'bookkeep', 'payroll'],
      florist:          ['florist', 'floral', 'flower', 'bouquet'],
      jewelry:          ['jewelry', 'jeweler', 'diamond', 'watch'],
      retail:           ['boutique', 'furniture', 'mattress', 'apparel', 'clothing', 'store', 'shop', 'hardware'],
      dry_cleaning:     ['dry clean', 'cleaners', 'laundry', 'laundromat'],
      daycare_education:['daycare', 'preschool', 'learning center', 'academy', 'tutoring', 'child care', 'childcare', 'montessori', 'school'],
      legal:            ['law', 'lawyer', 'attorney', 'legal'],
      tattoo:           ['tattoo', 'piercing'],
      smoke_vape:       ['smoke shop', 'vape', 'vapor', 'cigar', 'tobacco', 'hookah'],
      cannabis:         ['cannabis', 'dispensary', 'marijuana', 'cbd'],
      liquor_store:     ['liquor', 'wine and spirits', 'wine & spirits', 'spirits', 'bottle shop', 'wine shop'],
      phone_repair:     ['phone repair', 'cell phone', 'iphone repair', 'screen repair', 'computer repair'],
      home_services:    ['handyman', 'remodel', 'contractor', 'construction', 'flooring', 'painting', 'fence', 'garage door', 'concrete', 'paving', 'pool service'],
    };
    const tags = [];
    for (const [tag, subs] of Object.entries(map)) {
      if (subs.some(s => combined.includes(s))) tags.push(tag);
    }
    // If any specific cuisine matched, ensure generic restaurant is present too
    const cuisine = ['pizza','mexican','sushi_japanese','chinese','thai','indian','bbq_burger','seafood','sandwich_deli'];
    if (tags.some(t => cuisine.includes(t)) && !tags.includes('restaurant')) tags.push('restaurant');
    return [...new Set(tags)];
  }

  // ===== Grocery chain family normalization =====
  // Reconciles store GroceryChain values with testimonial chain tokens (t.ch),
  // and groups banners into parent companies for softer matches.
  function normalizeChain(raw) {
    let t = String(raw || '').toLowerCase().replace(/&amp;/g, '&').replace(/[.,]+$/, '').trim();
    const alias = {
      "fry's": 'fry', 'frys': 'fry', 'fry': 'fry', 'frys food': 'fry',
      'food 4 less': 'food4less', 'food4less': 'food4less',
      'stater bros.': 'stater bros', 'stater bros': 'stater bros',
      'dillon stores': 'dillon', 'dillion stores': 'dillon', 'dillons': 'dillon', 'dillon': 'dillon', 'gerbes-dillon': 'dillon',
      'quality food center': 'qfc', 'qfc': 'qfc',
      "ralph's": 'ralphs', 'ralphs': 'ralphs',
      'jewel-osco': 'jewel', 'jewel osco': 'jewel', 'jewel': 'jewel',
      "von's": 'vons', 'vons': 'vons',
      "shaw's": 'shaws', 'shaws': 'shaws',
      "baker's": 'bakers', 'bakers': 'bakers',
      "smith's": 'smiths', 'smiths': 'smiths',
    };
    return alias[t] || t;
  }
  const CHAIN_FAMILY = {
    kroger:        'kroger', 'fred meyer': 'kroger', qfc: 'kroger', ralphs: 'kroger',
    fry: 'kroger', food4less: 'kroger', 'king soopers': 'kroger', smiths: 'kroger',
    dillon: 'kroger', bakers: 'kroger', 'city market': 'kroger', 'jay c': 'kroger',
    'quality food center': 'kroger', gerbes: 'kroger', mariano: 'kroger', 'pick n save': 'kroger',
    'metro market': 'kroger', 'harris teeter': 'kroger',
    albertsons: 'albertsons', safeway: 'albertsons', vons: 'albertsons', jewel: 'albertsons',
    acme: 'albertsons', shaws: 'albertsons', pavilions: 'albertsons', randalls: 'albertsons',
    carrs: 'albertsons', 'tom thumb': 'albertsons', 'star market': 'albertsons', andronicos: 'albertsons',
  };
  function chainFamily(normChain) {
    return CHAIN_FAMILY[normChain] || null;
  }

  // Use Google Places types + category + name to find the BEST category keywords
  // This is intentionally broad — "J Squared Barrel Room" should match bar, wine, pizza, etc.
  function extractCategoryKeywords(category, name, placeTypes = []) {
    const combined = (category + ' ' + name + ' ' + placeTypes.join(' ')).toLowerCase();
    
    // Category definitions — a business can match MULTIPLE categories
    const categoryMap = [
      { match: ['bar', 'pub', 'tavern', 'taproom', 'brewery', 'brew', 'barrel', 'wine_bar', 'wine bar', 'lounge', 'nightclub', 'alehouse', 'saloon', 'cocktail', 'spirits'], 
        keywords: ['bar', 'grill', 'pub', 'tavern', 'brew', 'taproom', 'wine', 'alehouse', 'lounge', 'cocktail', 'pizza', 'sandwich', 'beer', 'wing'] },
      { match: ['pizza', 'pizzeria'], keywords: ['pizza', 'pizzeria', 'pie', 'slice'] },
      { match: ['restaurant', 'food', 'dining', 'eatery', 'bistro', 'kitchen', 'diner', 'grill', 'cafe', 'meal_delivery', 'meal_takeaway'],
        keywords: ['restaurant', 'grill', 'kitchen', 'diner', 'bistro', 'cafe', 'food'] },
      { match: ['taco', 'mexican', 'taqueria', 'burrito', 'enchilada', 'cantina'], keywords: ['mexican', 'taco', 'taqueria', 'burrito', 'cantina'] },
      { match: ['sushi', 'japanese', 'ramen', 'teriyaki'], keywords: ['sushi', 'japanese', 'ramen', 'teriyaki'] },
      { match: ['chinese', 'wok', 'noodle', 'dim sum'], keywords: ['chinese', 'asian', 'wok', 'noodle'] },
      { match: ['thai'], keywords: ['thai', 'curry', 'pad thai'] },
      { match: ['indian', 'tandoori', 'masala', 'naan'], keywords: ['indian', 'curry', 'tandoori'] },
      { match: ['burger', 'bbq', 'barbecue', 'wing', 'smokehouse'], keywords: ['burger', 'bbq', 'wing', 'grill', 'smokehouse'] },
      { match: ['seafood', 'fish', 'crab', 'lobster', 'oyster'], keywords: ['seafood', 'fish', 'shrimp', 'crab'] },
      { match: ['coffee', 'espresso', 'cafe', 'tea house'], keywords: ['coffee', 'cafe', 'espresso', 'tea'] },
      { match: ['bakery', 'donut', 'pastry', 'cookie', 'cake'], keywords: ['bakery', 'donut', 'cookie', 'pastry', 'cake'] },
      { match: ['ice cream', 'frozen yogurt', 'gelato', 'smoothie'], keywords: ['ice cream', 'frozen', 'yogurt', 'gelato', 'smoothie'] },
      { match: ['sandwich', 'sub', 'deli'], keywords: ['sandwich', 'sub', 'deli'] },
      { match: ['salon', 'hair', 'beauty', 'nail', 'lash', 'brow'], keywords: ['salon', 'hair', 'beauty', 'nail'] },
      { match: ['barber'], keywords: ['barber', 'barbershop', 'haircut'] },
      { match: ['auto', 'mechanic', 'oil change', 'tire', 'brake', 'transmission', 'car_repair'], keywords: ['auto', 'mechanic', 'oil change', 'tire', 'brake', 'repair'] },
      { match: ['dental', 'dentist'], keywords: ['dental', 'dentist', 'teeth'] },
      { match: ['gym', 'fitness', 'crossfit', 'training'], keywords: ['gym', 'fitness', 'training'] },
      { match: ['vet', 'veterinar', 'pet', 'animal', 'pet_store'], keywords: ['vet', 'pet', 'animal', 'dog'] },
      { match: ['chiropractic', 'chiropractor'], keywords: ['chiropractic', 'chiropractor'] },
      { match: ['massage', 'spa', 'wellness'], keywords: ['massage', 'spa', 'wellness'] },
      { match: ['dry clean', 'laundry'], keywords: ['dry clean', 'laundry'] },
      { match: ['insurance'], keywords: ['insurance', 'allstate', 'state farm'] },
      { match: ['real estate', 'realtor', 'realty'], keywords: ['real estate', 'realtor', 'realty'] },
      { match: ['cleaning', 'maid', 'janitorial'], keywords: ['cleaning', 'maid', 'janitorial'] },
      { match: ['plumb'], keywords: ['plumb', 'drain', 'pipe'] },
      { match: ['hvac', 'heating', 'air condition', 'furnace'], keywords: ['hvac', 'heating', 'air', 'furnace'] },
      { match: ['electric', 'electrician'], keywords: ['electric', 'electrician', 'wiring'] },
      { match: ['roofing', 'roof'], keywords: ['roof', 'roofing'] },
      { match: ['landscap', 'lawn', 'tree service', 'yard'], keywords: ['landscap', 'lawn', 'tree', 'yard', 'mowing'] },
      { match: ['tax', 'accounting', 'cpa', 'bookkeep'], keywords: ['tax', 'accounting', 'cpa', 'bookkeep'] },
      { match: ['flower', 'florist', 'floral'], keywords: ['flower', 'florist', 'floral', 'bouquet'] },
    ];

    let matchedKeywords = [];
    let matchCount = 0;
    
    // Match ALL applicable categories (not just the first one)
    for (const cat of categoryMap) {
      if (cat.match.some(m => combined.includes(m))) {
        matchedKeywords.push(...cat.keywords);
        matchCount++;
      }
    }
    
    // If nothing matched, try to extract useful words from name + category
    if (matchCount === 0) {
      const stopWords = ['the', 'and', 'bar', 'restaurant', 'inc', 'llc', 'cafe', 'room', 'house', 'shop', 'store', 'place', 'squared'];
      name.toLowerCase().split(/\s+/).forEach(w => {
        if (w.length > 3 && !stopWords.includes(w)) matchedKeywords.push(w);
      });
      if (category) {
        category.toLowerCase().split(/\s+/).forEach(w => {
          if (w.length > 3) matchedKeywords.push(w);
        });
      }
      // For generic restaurants/bars, add broad food keywords
      if (combined.includes('restaurant') || combined.includes('bar') || combined.includes('food')) {
        matchedKeywords.push('restaurant', 'grill', 'kitchen', 'diner', 'food');
      }
    }

    return { keywords: [...new Set(matchedKeywords)], exclude: [] };
  }

  function findMatchingTestimonials(detectedCats = [], keywords, exclude = [], name, info = '') {
    if (!allTestimonials.length) return [];
    const catSet = new Set(detectedCats);

    const infoLower = (info || '').toLowerCase();
    // Extract bonus keywords from additional info
    const infoBonus = {
      'new business': ['new', 'just started', 'first year', 'started', 'opened'],
      'several locations': ['location', 'multiple', 'stores', 'franchise', '2 stores', '3 stores', '5 stores'],
      'franchise': ['franchise', 'location', 'multiple', 'chain'],
      'parking lot': ['parking lot', 'plaza', 'same plaza', 'next to', 'nearby'],
      'across the street': ['across', 'nearby', 'close to', 'next to', 'same area'],
      'family': ['family', 'husband', 'wife', 'son', 'daughter', 'brother'],
      '10+ years': ['years', 'decade', 'long time', '10 year', '15 year', '20 year'],
      'just opened': ['new', 'just opened', 'grand opening', 'first year', 'started'],
    };

    let bonusKeywords = [];
    for (const [trigger, words] of Object.entries(infoBonus)) {
      if (infoLower.includes(trigger)) bonusKeywords.push(...words);
    }

    const scored = allTestimonials.map(t => {
      const biz = t.b || t.business || '';
      const comment = t.c || t.comment || '';
      const bizLower = biz.toLowerCase();
      const commentLower = comment.toLowerCase();
      let score = 0;
      
      // EXCLUDE penalty — if business name contains an excluded word, heavy penalty
      let excluded = false;
      exclude.forEach(ex => {
        if (bizLower.includes(ex)) { score -= 50; excluded = true; }
      });
      if (excluded) return { business: biz, comment, url: t.u || t.url || '', id: t.id, score };

      // ===== Precomputed category-tag matching (primary signal) =====
      const tCat = Array.isArray(t.cat) ? t.cat : [];
      const tCatName = Array.isArray(t.catn) ? t.catn : [];
      if (catSet.size && tCat.length) {
        let tagHits = 0;
        for (const tag of tCat) {
          if (catSet.has(tag)) {
            // name-matched tag on the testimonial is a stronger signal
            score += tCatName.includes(tag) ? 12 : 8;
            tagHits++;
            if (tagHits >= 3) break; // cap tag contribution
          }
        }
      }

      // Business name / comment keyword fallback (still useful, lower weight,
      // and the main path for records lacking cat tags).
      keywords.forEach(kw => {
        if (bizLower.includes(kw)) score += 5;
        else if (commentLower.includes(kw)) score += 1;
      });

      // Bonus from additional info context
      bonusKeywords.forEach(bk => {
        if (commentLower.includes(bk)) score += 2;
      });

      // Quality bonuses
      if (/\d+ coupon/i.test(comment)) score += 2;
      if (/return on/i.test(comment)) score += 2;
      if (/\$\d/i.test(comment)) score += 1;
      if (/renew/i.test(comment)) score += 1;
      if (comment.length > 200) score += 1;
      if (comment.length > 400) score += 1;

      return { business: biz, comment, url: t.u || t.url || '', id: t.id, score };
    }).filter(t => t.score > 4)
      .sort((a, b) => b.score - a.score);

    const seen = new Set();
    const results = [];
    for (const t of scored) {
      const bizKey = t.business.toLowerCase().split('-')[0].trim();
      if (seen.has(bizKey)) continue;
      seen.add(bizKey);
      results.push(t);
      if (results.length >= 4) break;
    }
    return results;
  }

  function findLocalTestimonial(detectedCats = []) {
    if (!selectedStore || !allTestimonials.length) return null;

    const city = (selectedStore.City || '').toLowerCase().trim();
    const state = (selectedStore.State || '').toLowerCase().trim();
    const rawChain = selectedStore.GroceryChain || '';
    const chainNorm = normalizeChain(rawChain);
    const family = chainFamily(chainNorm);
    const catSet = new Set(detectedCats);

    // Build list of nearby cities from the stores database (within ~50 mi via lat/lng)
    const nearbyCities = new Set();
    if (selectedStore.latitude && selectedStore.longitude) {
      const lat = parseFloat(selectedStore.latitude);
      const lng = parseFloat(selectedStore.longitude);
      allStores.forEach(s => {
        if (s.latitude && s.longitude && s.City) {
          const dlat = parseFloat(s.latitude) - lat;
          const dlng = parseFloat(s.longitude) - lng;
          const distMiles = Math.sqrt(dlat * dlat + dlng * dlng) * 69; // rough miles
          if (distMiles < 50) nearbyCities.add(s.City.toLowerCase().trim());
        }
      });
    } else {
      allStores.forEach(s => {
        if ((s.State || '').toLowerCase() === state && s.City) {
          nearbyCities.add(s.City.toLowerCase().trim());
        }
      });
    }
    nearbyCities.delete(city); // keep exact-city separate

    const matchedIds = new Set(matchedTestimonials.map(t => t.id));
    const scored = allTestimonials.map(t => {
      if (matchedIds.has(t.id)) return null;
      const biz = t.b || t.business || '';
      const comment = t.c || t.comment || '';
      // Prefer precomputed cities; fall back to substring scan for old records.
      const tCities = Array.isArray(t.cities) ? t.cities : null;
      const search = (biz + ' ' + comment).toLowerCase();
      let score = 0;

      // ---- Locality (city in comment) ----
      if (city) {
        if (tCities ? tCities.includes(city) : search.includes(city)) score += 20;
        else {
          for (const nc of nearbyCities) {
            if (!nc) continue;
            if (tCities ? tCities.includes(nc) : search.includes(nc)) { score += 10; break; }
          }
        }
      }

      // ---- Chain match (from parsed t.ch tokens) ----
      const tCh = Array.isArray(t.ch) ? t.ch : [];
      if (tCh.length) {
        const tNorm = tCh.map(normalizeChain);
        if (tNorm.includes(chainNorm)) score += 8;               // exact banner
        else if (family && tNorm.some(c => chainFamily(c) === family)) score += 4; // same parent co.
      } else if (chainNorm && search.includes(chainNorm)) {
        score += 6; // legacy fallback
      }

      // ---- Same state mention ----
      if (state && search.includes(state)) score += 2;

      // ---- Relevance + quality tiebreakers ----
      if (catSet.size && Array.isArray(t.cat) && t.cat.some(tag => catSet.has(tag))) score += 3;
      if (comment.length > 150) score += 1;
      if (comment.length > 300) score += 1;

      if (score <= 0) return null;
      return { business: biz, comment, url: t.u || t.url || '', id: t.id, score };
    }).filter(Boolean).sort((a, b) => b.score - a.score);

    return scored[0] || null;
  }

  function cleanBizName(name) {
    return (name || '').replace(/&#x27;/g, "'").replace(/&#x9;/g, '').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/\s+-\s+/g, ' — ').trim();
  }

  async function downloadTestimonialsPdf() {
    const { PDFDocument, rgb, StandardFonts } = await import('pdf-lib');
    const doc = await PDFDocument.create();
    const regular = await doc.embedFont(StandardFonts.Helvetica);
    const bold = await doc.embedFont(StandardFonts.HelveticaBold);
    const italic = await doc.embedFont(StandardFonts.HelveticaOblique);

    const pageW = 612; const pageH = 792;
    const margin = 50;
    const maxW = pageW - margin * 2;
    let page = doc.addPage([pageW, pageH]);
    let y = pageH - margin;

    function checkPage(need) {
      if (y < need + margin) {
        page = doc.addPage([pageW, pageH]);
        y = pageH - margin;
      }
    }

    // Wrap text to fit width
    function wrapText(text, font, size, maxWidth) {
      const words = text.split(' ');
      const lines = [];
      let current = '';
      for (const word of words) {
        const test = current ? current + ' ' + word : word;
        if (font.widthOfTextAtSize(test, size) > maxWidth) {
          if (current) lines.push(current);
          current = word;
        } else {
          current = test;
        }
      }
      if (current) lines.push(current);
      return lines;
    }

    // Header bar
    page.drawRectangle({ x: 0, y: pageH - 80, width: pageW, height: 80, color: rgb(0.8, 0, 0) });
    page.drawText('IndoorMedia', { x: margin, y: pageH - 35, size: 22, font: bold, color: rgb(1, 1, 1) });
    page.drawText('Testimonials for Meeting Prep', { x: margin, y: pageH - 55, size: 12, font: regular, color: rgb(1, 0.9, 0.9) });
    page.drawText(new Date().toLocaleDateString(), { x: pageW - margin - 80, y: pageH - 35, size: 10, font: regular, color: rgb(1, 0.9, 0.9) });
    y = pageH - 100;

    // Business info
    page.drawText(businessName || 'Business', { x: margin, y, size: 16, font: bold, color: rgb(0.1, 0.1, 0.1) });
    y -= 18;
    if (businessCategory) { page.drawText(`Category: ${businessCategory}`, { x: margin, y, size: 10, font: regular, color: rgb(0.4, 0.4, 0.4) }); y -= 14; }
    if (selectedStore) { page.drawText(`Store: ${selectedStore.GroceryChain} ${selectedStore.City} (${selectedStore.StoreName})`, { x: margin, y, size: 10, font: regular, color: rgb(0.4, 0.4, 0.4) }); y -= 14; }
    if (businessAddress) { page.drawText(`Address: ${businessAddress}`, { x: margin, y, size: 10, font: regular, color: rgb(0.4, 0.4, 0.4) }); y -= 14; }
    y -= 10;

    // Section header
    function sectionHeader(text) {
      checkPage(40);
      page.drawRectangle({ x: margin, y: y - 2, width: maxW, height: 22, color: rgb(0.96, 0.96, 0.96) });
      page.drawText(text, { x: margin + 8, y: y + 3, size: 12, font: bold, color: rgb(0.2, 0.2, 0.2) });
      y -= 30;
    }

    // Testimonial block
    function addTestimonial(num, t) {
      const bizName = cleanBizName(t.business);
      const quote = `"${t.comment}"`;
      const quoteLines = wrapText(quote, italic, 10, maxW - 30);
      const needed = 20 + (quoteLines.length * 14) + 20;
      checkPage(needed);

      // Number circle
      page.drawCircle({ x: margin + 8, y: y - 4, size: 8, color: rgb(0.8, 0, 0) });
      page.drawText(String(num), { x: margin + 5, y: y - 8, size: 9, font: bold, color: rgb(1, 1, 1) });

      // Business name
      page.drawText(bizName, { x: margin + 24, y, size: 11, font: bold, color: rgb(0.15, 0.15, 0.15) });
      y -= 18;

      // Quote
      for (const line of quoteLines) {
        page.drawText(line, { x: margin + 24, y, size: 10, font: italic, color: rgb(0.35, 0.35, 0.35) });
        y -= 14;
      }

      // URL
      if (t.url) {
        page.drawText(`View: ${t.url}`, { x: margin + 24, y, size: 8, font: regular, color: rgb(0.08, 0.38, 0.75) });
        y -= 12;
      }
      y -= 8;
    }

    sectionHeader('Similar Business Testimonials');
    matchedTestimonials.forEach((t, i) => addTestimonial(i + 1, t));

    if (localTestimonial) {
      sectionHeader('Local Testimonial');
      const bizName = cleanBizName(localTestimonial.business);
      const quote = `"${localTestimonial.comment}"`;
      const quoteLines = wrapText(quote, italic, 10, maxW - 30);
      checkPage(20 + quoteLines.length * 14 + 20);

      page.drawText('📍', { x: margin + 2, y, size: 12, font: regular });
      page.drawText(bizName, { x: margin + 24, y, size: 11, font: bold, color: rgb(0.08, 0.38, 0.75) });
      y -= 18;
      for (const line of quoteLines) {
        page.drawText(line, { x: margin + 24, y, size: 10, font: italic, color: rgb(0.35, 0.35, 0.35) });
        y -= 14;
      }
      if (localTestimonial.url) {
        page.drawText(`View: ${localTestimonial.url}`, { x: margin + 24, y, size: 8, font: regular, color: rgb(0.08, 0.38, 0.75) });
        y -= 12;
      }
    }

    // Footer
    checkPage(30);
    y -= 10;
    page.drawLine({ start: { x: margin, y: y + 5 }, end: { x: pageW - margin, y: y + 5 }, thickness: 0.5, color: rgb(0.8, 0.8, 0.8) });
    page.drawText(`Generated by imPro Sales Portal — ${new Date().toLocaleString()}`, { x: margin, y: y - 10, size: 8, font: regular, color: rgb(0.6, 0.6, 0.6) });

    const bytes = await doc.save();
    const blob = new Blob([bytes], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Testimonials - ${businessName || 'Meeting Prep'}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function copyTestimonials() {
    const lines = [];
    lines.push(`MEETING PREP: ${businessName}`);
    lines.push(`Category: ${businessCategory}`);
    lines.push(`Store: ${storeSearch}`);
    lines.push('');
    lines.push('--- MATCHING TESTIMONIALS ---');
    matchedTestimonials.forEach((t, i) => {
      lines.push(`\n${i+1}. ${cleanBizName(t.business)}`);
      lines.push(`"${t.comment}"`);
    });
    if (localTestimonial) {
      lines.push('\n--- LOCAL TESTIMONIAL ---');
      lines.push(`${cleanBizName(localTestimonial.business)}`);
      lines.push(`"${localTestimonial.comment}"`);
    }
    navigator.clipboard.writeText(lines.join('\n'));
    alert('✅ Copied to clipboard!');
  }
</script>

<div class="prep">
  {#if step === 'search'}
    <button class="back-btn" on:click={onBack}>← Back</button>
    <h2>📋 Meeting Prep</h2>
    <p class="sub">Look up the business and we'll find the best testimonials to match</p>

    <div class="f rel">
      <label>Nearby Store (select first for better results)</label>
      <StoreSearchInput
        stores={allStores}
        placeholder="City, zip, store #, address..."
        maxResults={10}
        showGeo={true}
        on:select={e => selectStore(e.detail)}
      />
    </div>

    <div class="f rel">
      <label>Business Name *</label>
      <input type="text" bind:value={businessName} placeholder="e.g. Wow Cow, Joe's Pizza..." on:input={() => { if (businessName.length >= 3) searchBusiness(); }} />
      {#if searching}<span class="spin">🔍</span>{/if}
      {#if searchResults.length > 0}
        <div class="dd">
          {#each searchResults as b}
            <button class="ddi" on:click={() => selectBusiness(b)}><strong>{b.name}</strong><small>{b.address} {b.phone ? '• ' + b.phone : ''}</small>{#if b.category}<small class="cat-tag">{b.category}</small>{/if}</button>
          {/each}
        </div>
      {/if}
    </div>

    {#if businessAddress}
      <div class="biz-preview">
        <div class="biz-p-name">{businessName}</div>
        <div class="biz-p-info">{businessCategory} • {businessAddress}</div>
        {#if businessPhone}<div class="biz-p-info">{businessPhone}</div>{/if}
        {#if businessWebsite}<div class="biz-p-info"><a href={businessWebsite} target="_blank">{businessWebsite.replace('https://', '').replace('http://', '').split('/')[0]}</a></div>{/if}
      </div>
    {/if}

    <div class="f">
      <label>Additional Info (helps find better matches)</label>
      <input type="text" bind:value={additionalInfo} placeholder="e.g. in the parking lot, new business, several locations, across the street..." />
      <div class="info-tags">
        {#each ['In the parking lot', 'Across the street', 'New business', 'Several locations', 'Family owned', 'Franchise', 'Been open 10+ years', 'Just opened'] as tag}
          <button class="info-tag" class:active={additionalInfo.includes(tag)} on:click={() => { additionalInfo = additionalInfo ? additionalInfo + ', ' + tag : tag; }}>{tag}</button>
        {/each}
      </div>
    </div>

    <button class="btn-go" on:click={runPrep}>🔍 Run Meeting Prep</button>
    <div style="height:80px;"></div>

  {:else if step === 'loading'}
    <div class="loading">
      <div class="loading-icon">⏳</div>
      <h3>{loadingStatus}</h3>
      <div class="progress-bar"><div class="progress-fill" style="width:{loadingStep * 20}%;"></div></div>
      <p class="loading-sub">Analyzing {businessName}...</p>
    </div>

  {:else if step === 'results'}
    <button class="back-btn" on:click={() => step = 'search'}>← New Search</button>
    <h2>📋 Meeting Prep: {businessName}</h2>
    
    <div class="result-card info-card">
      <h3>🏢 Business Info</h3>
      <div class="info-row"><span class="info-label">Category:</span><span>{businessCategory || 'N/A'}</span></div>
      <div class="info-row"><span class="info-label">Address:</span><span>{businessAddress || 'N/A'}</span></div>
      {#if businessPhone}<div class="info-row"><span class="info-label">Phone:</span><span>{businessPhone}</span></div>{/if}
      {#if businessWebsite}<div class="info-row"><span class="info-label">Website:</span><a href={businessWebsite} target="_blank">{businessWebsite.replace('https://','').split('/')[0]}</a></div>{/if}
      {#if selectedStore}
        <div class="info-row"><span class="info-label">Store:</span><span>{selectedStore.GroceryChain} {selectedStore.City} ({selectedStore.StoreName})</span></div>
        {#if selectedStore.Address}
          <div class="info-row"><span class="info-label">Address:</span><span>{selectedStore.Address}, {selectedStore.City}, {selectedStore.State} {selectedStore.PostalCode}</span></div>
        {/if}
      {/if}
      {#if additionalInfo}<div class="info-row"><span class="info-label">Notes:</span><span>{additionalInfo}</span></div>{/if}
    </div>

    {#if matchedTestimonials.length > 0}
      <div class="result-card">
        <h3>⭐ Similar Business Testimonials</h3>
        <p class="result-hint">These are from businesses similar to {businessName} — use after the testimonial slide in your presentation. Tap any testimonial to view full details.</p>
        
        {#if matchedTestimonials.some(t => t.url)}
          <button class="open-all-btn" on:click={() => {
            const urls = [...matchedTestimonials, localTestimonial].filter(t => t && t.url);
            if (urls.length === 0) return;
            showTestimonialModal = true;
          }}>🔗 Open All Testimonials ({matchedTestimonials.filter(t => t.url).length + (localTestimonial?.url ? 1 : 0)})</button>
        {/if}

        {#each matchedTestimonials as t, i}
          <div class="testimonial" class:clickable={t.url} on:click={() => { if (t.url) window.open(t.url, '_blank'); }}>
            <div class="test-num">{i + 1}</div>
            <div class="test-body">
              <div class="test-biz">{cleanBizName(t.business)}</div>
              <div class="test-quote">"{t.comment}"</div>
              {#if t.url}<span class="test-link">🔗 Tap to view full testimonial →</span>{/if}
            </div>
          </div>
        {/each}
      </div>
    {:else}
      <div class="result-card empty">
        <h3>⭐ Similar Business Testimonials</h3>
        <p>No closely matching testimonials found. Try broadening the category.</p>
      </div>
    {/if}

    {#if localTestimonial}
      <div class="result-card local-card">
        <h3>📍 Local Testimonial</h3>
        <p class="result-hint">A business near {selectedStore?.City || 'this area'} — great for "right here in your neighborhood" credibility</p>
        <div class="testimonial" class:clickable={localTestimonial.url} on:click={() => { if (localTestimonial.url) window.open(localTestimonial.url, '_blank'); }}>
          <div class="test-num">📍</div>
          <div class="test-body">
            <div class="test-biz">{cleanBizName(localTestimonial.business)}</div>
            <div class="test-quote">"{localTestimonial.comment}"</div>
            {#if localTestimonial.url}<span class="test-link">🔗 Tap to view full testimonial →</span>{/if}
          </div>
        </div>
      </div>
    {/if}

    <!-- Testimonial Modal - grouped view -->
    {#if showTestimonialModal}
      <div class="modal-overlay" on:click={() => showTestimonialModal = false}>
        <div class="modal-content" on:click|stopPropagation>
          <div class="modal-header">
            <h3>📋 All Testimonials for {businessName}</h3>
            <button class="modal-close" on:click={() => showTestimonialModal = false}>✕</button>
          </div>
          <div class="modal-body">
            {#each matchedTestimonials as t, i}
              <div class="modal-testimonial">
                <div class="modal-test-header">
                  <span class="modal-test-num">{i + 1}</span>
                  <strong>{cleanBizName(t.business)}</strong>
                </div>
                <p class="modal-test-quote">"{t.comment}"</p>
                {#if t.url}
                  <a href={t.url} target="_blank" class="modal-test-link">🔗 Open Full Testimonial</a>
                {/if}
              </div>
            {/each}
            {#if localTestimonial}
              <div class="modal-testimonial local">
                <div class="modal-test-header">
                  <span class="modal-test-num">📍</span>
                  <strong>{cleanBizName(localTestimonial.business)}</strong>
                  <span class="local-tag">Local</span>
                </div>
                <p class="modal-test-quote">"{localTestimonial.comment}"</p>
                {#if localTestimonial.url}
                  <a href={localTestimonial.url} target="_blank" class="modal-test-link">🔗 Open Full Testimonial</a>
                {/if}
              </div>
            {/if}
          </div>
          <div class="modal-footer">
            <button class="btn-pdf" on:click={downloadTestimonialsPdf}>📄 PDF</button>
            <button class="btn-copy" on:click={copyTestimonials}>📋 Copy</button>
            <button class="btn-secondary" on:click={() => showTestimonialModal = false}>Close</button>
          </div>
        </div>
      </div>
    {/if}

    <button class="btn-pdf" on:click={downloadTestimonialsPdf}>📄 Download as PDF</button>
    <button class="btn-copy" on:click={copyTestimonials}>📋 Copy All to Clipboard</button>
    <button class="btn-secondary" on:click={() => step = 'search'}>🔄 New Prep</button>
    <div style="height:80px;"></div>
  {/if}
</div>

<style>
  .prep { }
  .back-btn { background:none; border:none; color:var(--text-secondary); font-size:14px; cursor:pointer; padding:8px 0; }
  .sub { font-size:13px; color:var(--text-secondary); margin:-4px 0 16px; }
  
  .f { margin-bottom:14px; }
  .f label { display:block; font-size:11px; font-weight:700; color:var(--text-secondary); margin-bottom:4px; text-transform:uppercase; letter-spacing:.3px; }
  .f input { width:100%; padding:12px; border:2px solid var(--border-color); border-radius:10px; font-size:15px; background:var(--card-bg); color:var(--text-primary); box-sizing:border-box; }
  .f input:focus { border-color:#CC0000; outline:none; }
  .rel { position:relative; }
  .spin { position:absolute; right:14px; top:38px; }
  .dd { position:absolute; top:100%; left:0; right:0; background:var(--card-bg); border:2px solid var(--border-color); border-radius:10px; margin-top:4px; max-height:220px; overflow-y:auto; z-index:100; box-shadow:0 6px 20px rgba(0,0,0,.25); }
  .ddi { display:block; width:100%; padding:12px; border:none; border-bottom:1px solid var(--border-color); background:transparent; text-align:left; cursor:pointer; color:var(--text-primary); font-size:14px; }
  .ddi:hover { background:rgba(204,0,0,.06); }
  .ddi:last-child { border-bottom:none; }
  .ddi small { display:block; font-size:12px; color:var(--text-secondary); margin-top:2px; }
  .cat-tag { color:#CC0000; font-weight:600; }

  .info-tags { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }
  .info-tag { padding:6px 12px; border:1.5px solid var(--border-color); border-radius:20px; background:var(--card-bg); font-size:12px; color:var(--text-secondary); cursor:pointer; transition:all .15s; }
  .info-tag:hover { border-color:#CC0000; color:#CC0000; }
  .info-tag.active { background:#CC0000; color:#fff; border-color:#CC0000; }

  .biz-preview { background:var(--card-bg); border:2px solid #CC0000; border-radius:12px; padding:14px; margin-bottom:16px; }
  .biz-p-name { font-size:18px; font-weight:800; color:var(--text-primary); }
  .biz-p-info { font-size:13px; color:var(--text-secondary); margin-top:4px; }
  .biz-p-info a { color:#CC0000; }

  .btn-go { width:100%; padding:16px; background:#CC0000; color:#fff; border:none; border-radius:12px; font-size:17px; font-weight:800; cursor:pointer; }
  .btn-go:hover { background:#a00; }

  /* Loading */
  .loading { text-align:center; padding:60px 20px; }
  .loading-icon { font-size:48px; margin-bottom:16px; animation:pulse 1.5s infinite; }
  @keyframes pulse { 0%,100%{transform:scale(1)} 50%{transform:scale(1.1)} }
  .loading h3 { font-size:18px; color:var(--text-primary); margin:0 0 16px; }
  .loading-sub { font-size:14px; color:var(--text-secondary); }
  .progress-bar { height:6px; background:var(--border-color); border-radius:3px; overflow:hidden; max-width:300px; margin:0 auto; }
  .progress-fill { height:100%; background:#CC0000; border-radius:3px; transition:width .5s; }

  /* Results */
  .result-card { background:var(--card-bg, #ffffff); border:1px solid #e8e8e8; border-radius:12px; box-shadow:0 1px 3px rgba(0,0,0,0.06); padding:16px; margin-bottom:16px; transition:box-shadow 0.2s; }
  .result-card:hover { box-shadow:0 2px 8px rgba(0,0,0,0.1); }
  :global([data-theme='dark']) .result-card { background:#1e1e1e; border-color:#333; }
  .result-card h3 { margin:0 0 8px; font-size:17px; font-weight:700; color:var(--text-primary); }
  .result-hint { font-size:12px; color:var(--text-secondary); margin:0 0 14px; font-style:italic; }
  .info-card { border-color:#CC000030; }
  .local-card { border-color:#1565C030; background:rgba(21,101,192,.03); }
  .info-row { display:flex; gap:8px; padding:6px 0; border-bottom:1px solid var(--border-color); font-size:13px; }
  .info-row:last-child { border-bottom:none; }
  .info-label { font-weight:700; color:var(--text-secondary); min-width:70px; }
  .info-row a { color:#CC0000; text-decoration:none; }

  .testimonial { display:flex; gap:12px; padding:12px 0; border-bottom:1px solid var(--border-color); }
  .testimonial.clickable { cursor:pointer; border-radius:8px; padding:12px; margin:0 -12px; transition: background 0.15s; }
  .testimonial.clickable:hover, .testimonial.clickable:active { background:rgba(204,0,0,0.04); }
  .open-all-btn { width:100%; padding:12px; margin-bottom:12px; background:#CC0000; color:white; border:none; border-radius:10px; font-size:14px; font-weight:700; cursor:pointer; }
  .modal-overlay { position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.6); z-index:9999; display:flex; align-items:center; justify-content:center; padding:20px; }
  .modal-content { background:var(--card-bg, white); border-radius:16px; width:100%; max-width:500px; max-height:85vh; display:flex; flex-direction:column; overflow:hidden; }
  .modal-header { display:flex; justify-content:space-between; align-items:center; padding:16px 20px; border-bottom:1px solid var(--border-color, #eee); }
  .modal-header h3 { margin:0; font-size:16px; }
  .modal-close { background:none; border:none; font-size:20px; cursor:pointer; padding:4px 8px; color:var(--text-secondary); }
  .modal-body { overflow-y:auto; padding:16px 20px; flex:1; }
  .modal-testimonial { padding:14px; margin-bottom:12px; background:var(--bg-secondary, #f9f9f9); border-radius:10px; border-left:4px solid #CC0000; }
  .modal-testimonial.local { border-left-color:#1565C0; }
  .modal-test-header { display:flex; align-items:center; gap:8px; margin-bottom:6px; font-size:14px; }
  .modal-test-num { width:24px; height:24px; background:#CC0000; color:white; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:800; flex-shrink:0; }
  .modal-test-quote { font-size:13px; font-style:italic; color:var(--text-secondary, #666); line-height:1.4; margin:0 0 8px; }
  .modal-test-link { font-size:13px; color:#CC0000; text-decoration:none; font-weight:700; display:inline-block; padding:6px 12px; background:rgba(204,0,0,0.06); border-radius:6px; }
  .local-tag { font-size:10px; padding:2px 6px; background:#E3F2FD; color:#1565C0; border-radius:4px; font-weight:700; }
  .modal-footer { padding:14px 20px; border-top:1px solid var(--border-color, #eee); display:flex; gap:10px; }
  .testimonial:last-child { border-bottom:none; }
  .test-num { width:28px; height:28px; background:#CC0000; color:#fff; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:800; flex-shrink:0; }
  .local-card .test-num { background:#1565C0; }
  .test-body { flex:1; }
  .test-biz { font-size:14px; font-weight:700; color:var(--text-primary); margin-bottom:4px; }
  .test-quote { font-size:13px; color:var(--text-secondary); line-height:1.5; font-style:italic; }
  .test-link { font-size:12px; color:#CC0000; text-decoration:none; font-weight:600; margin-top:4px; display:inline-block; }

  .empty { text-align:center; }
  .empty p { color:var(--text-secondary); font-size:14px; }

  .btn-pdf { width:100%; padding:14px; background:#CC0000; color:#fff; border:none; border-radius:10px; font-size:15px; font-weight:700; cursor:pointer; margin-bottom:8px; }
  .btn-pdf:hover { background:#990000; }
  .btn-copy { width:100%; padding:14px; background:#2E7D32; color:#fff; border:none; border-radius:10px; font-size:15px; font-weight:700; cursor:pointer; margin-bottom:8px; }
  .btn-copy:hover { background:#1B5E20; }
  .btn-secondary { width:100%; padding:12px; background:var(--card-bg); color:var(--text-primary); border:2px solid var(--border-color); border-radius:10px; font-size:14px; font-weight:600; cursor:pointer; }
</style>
