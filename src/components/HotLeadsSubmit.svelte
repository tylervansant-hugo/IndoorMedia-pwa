<script>
  import { onMount, onDestroy } from 'svelte';
  import StoreSearchInput from '../lib/StoreSearchInput.svelte';
  import { saveLeadData, whenFirebaseReady, isFirebaseReady } from '../lib/firebase.js';

  export let user;
  export let onLeadSubmitted = () => {};

  // Shared Places key (same key used across the PWA)
  const PLACES_API_KEY = 'AIzaSyBoslNJj8aO6wkQOfkH9e4qTVJZ-G9nOuA';

  let submitMode = 'card'; // 'manual' or 'card'
  let formData = {
    business_name: '',
    contact_name: '',
    title: '',
    category: 'Restaurant / Casual Dining',
    phone: '',
    email: '',
    website: '',
    address: '',
    store_id: '',
    store_chain: '',
    store_city: '',
    distance_mi: ''
  };

  let cardImage = null;
  let cardImagePreview = null;
  let processedPreview = null;
  let ocrLoading = false;
  let ocrProgress = 0;
  let ocrStage = '';
  let ocrText = '';
  let extractedData = null;
  let submitting = false;
  let submitMessage = '';
  let tesseractReady = false;
  let tessWorker = null;

  // Business matching (against prospects / Google Places)
  let matchLoading = false;
  let matchCandidates = [];       // businesses found near the card address
  let matchedBusiness = null;     // the confirmed match
  let nearestStores = [];         // [{...store, distance}] top 3
  let showRawText = false;

  let allStores = [];      // mapped format for matching (real field names kept)
  let allStoresRaw = [];   // original format for StoreSearchInput
  let storeSearchText = '';

  const categories = [
    'Auto / Accessories / Parts',
    'Auto / Car Wash / Detailing',
    'Auto / Inspection / Testing / Smog',
    'Auto / Repair / Body / Maintenance',
    'Auto / Sales / Leasing / Rental',
    'Auto / Towing / Storage',
    'Beauty / Beauty & Health',
    'Beauty / Hair / Nails / Spa / Tanning',
    'Education / School',
    'Entertainment / Bar / Night Club',
    'Entertainment / Dance Studio / Classes',
    'Entertainment / Family Entertainment',
    'Entertainment / Gaming / Casinos',
    'Entertainment / Golf Courses / Supplies',
    'Entertainment / Hotel / Motel',
    'Entertainment / Martial Arts',
    'Entertainment / Music / Lessons',
    'Entertainment / Party Supplies / Planning',
    'Entertainment / Recreation Centers / Halls',
    'Entertainment / Sports Bar / Lounge / Winery',
    'Entertainment / Tattoos & Piercing',
    'Entertainment / Travel Agencies',
    'General / Child Care',
    'General / Community Services',
    'Health / Blood / Plasma Donations',
    'Health / CBD',
    'Health / Dental / Orthodontics',
    'Health / Dispensary',
    'Health / Fitness & Health',
    'Health / Hearing Aids / Devices',
    'Health / Medical',
    'Health / Optical',
    'Health / Pharmaceuticals',
    'Health / Senior Care / Living',
    'Home Services / Cleaning / Maid Service',
    'Home Services / Dry Cleaning / Laundry / Tailors',
    'Home Services / Energy',
    'Home Services / Funeral Home / Cemetery',
    'Home Services / Glass Repair',
    'Home Services / Home Improvement / Contracting',
    'Home Services / Pet Care',
    'Home Services / Propane & Natural Gas',
    'Home Services / Real Estate / Realtors',
    'Home Services / Recycling / Salvage',
    'Home Services / Rental Services',
    'Home Services / Storage',
    'Home Services / Tool Repair & Parts',
    'Home Services / Vehicle & License Registration',
    'Home Services / Video / Production',
    'Home Services / Water Delivery',
    'Legal / Attorney / Law Firm',
    'Legal / Mortgage',
    'Insurance',
    'Personal Finance / Financial',
    'Professional Services / Audio / Video Equipment',
    'Professional Services / Computers / Repair',
    'Professional Services / Printing / Supplies',
    'Professional Services / Recruiting',
    'Professional Services / Restaurant Equipment',
    'Professional Services / Transportation / Delivery',
    'Professional Services / Water Treatment',
    'Restaurant / Asian',
    'Restaurant / Bakery',
    'Restaurant / Breweries',
    'Restaurant / Casual Dining',
    'Restaurant / Catering',
    'Restaurant / Coffee Shops',
    'Restaurant / Cultural Dining',
    'Restaurant / Deli',
    'Restaurant / Donut Shops',
    'Restaurant / Fast Food',
    'Restaurant / Fine Dining',
    'Restaurant / Food Delivery',
    'Restaurant / Ice Cream / Yogurt Shops',
    'Restaurant / Mexican',
    'Restaurant / Pizza',
    'Restaurant / Sandwich Shops',
    'Retail / Antiques & Collectibles',
    'Retail / Arts & Crafts',
    'Retail / Barbeque Grills & Supplies',
    'Retail / Battery Supplies',
    'Retail / Bicycle Shop',
    'Retail / Candy & Sweets',
    'Retail / Communication',
    'Retail / Convenience Store / Gas Station',
    'Retail / Feed Store / Farm Equipment',
    'Retail / Florists',
    'Retail / Framing',
    'Retail / Furniture',
    'Retail / Grocery Store',
    'Retail / Hobby Shops / Equipment',
    'Retail / Jewelry / Watch Repair',
    'Retail / Liquor Store',
    'Retail / Pawn Shops / Gold & Silver',
    'Retail / Pet Supply Store',
    'Retail / Shopping / Boutique',
    'Retail / Sewing Machines / Contractors',
    'Retail / Shipping / Postal Services',
    'Retail / Smoke Shop',
    'Retail / Specialty Foods',
    'Retail / Sporting / Military Goods',
    'Retail / Toys / Games',
    'Retail / Vacuums',
    'Other / Unknown',
  ];

  // ---------- Tesseract loader (with worker reuse) ----------
  async function loadTesseract() {
    if (window.Tesseract) { tesseractReady = true; return; }
    await new Promise((resolve) => {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js';
      script.onload = () => { tesseractReady = true; resolve(); };
      script.onerror = () => { console.error('Failed to load Tesseract'); resolve(); };
      document.head.appendChild(script);
    });
  }

  onMount(async () => {
    try {
      const response = await fetch(import.meta.env.BASE_URL + 'data/stores.json?t=' + Date.now());
      const stores = await response.json();
      allStoresRaw = stores;
      // Keep the REAL field names so distance/state matching actually works
      allStores = stores;
      console.log(`Loaded ${allStores.length} stores for matching`);
    } catch (err) {
      console.error('Error loading stores:', err);
    }
    // Warm up OCR in the background
    loadTesseract();
  });

  onDestroy(async () => {
    if (tessWorker) { try { await tessWorker.terminate(); } catch {} }
  });

  function handleCardImageSelect(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    cardImage = file;
    extractedData = null;
    ocrText = '';
    matchCandidates = [];
    matchedBusiness = null;
    nearestStores = [];
    const reader = new FileReader();
    reader.onload = (event) => {
      cardImagePreview = event.target?.result;
      processedPreview = null;
    };
    reader.readAsDataURL(file);
  }

  // ---------- Image preprocessing for better OCR ----------
  // Upscale small images, convert to grayscale, boost contrast.
  async function preprocessImage(dataUrl) {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        try {
          // Target ~1600px on the long edge for crisp text
          const maxEdge = 1600;
          const scale = Math.min(3, Math.max(1, maxEdge / Math.max(img.width, img.height)));
          const w = Math.round(img.width * scale);
          const h = Math.round(img.height * scale);
          const canvas = document.createElement('canvas');
          canvas.width = w;
          canvas.height = h;
          const ctx = canvas.getContext('2d');
          ctx.imageSmoothingEnabled = true;
          ctx.imageSmoothingQuality = 'high';
          ctx.drawImage(img, 0, 0, w, h);

          const imgData = ctx.getImageData(0, 0, w, h);
          const d = imgData.data;
          // Grayscale + contrast stretch
          const contrast = 1.35;
          const intercept = 128 * (1 - contrast);
          for (let i = 0; i < d.length; i += 4) {
            let gray = 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
            gray = gray * contrast + intercept;
            gray = gray < 0 ? 0 : gray > 255 ? 255 : gray;
            d[i] = d[i + 1] = d[i + 2] = gray;
          }
          ctx.putImageData(imgData, 0, 0);
          resolve(canvas.toDataURL('image/png'));
        } catch (e) {
          console.warn('preprocess failed, using original', e);
          resolve(dataUrl);
        }
      };
      img.onerror = () => resolve(dataUrl);
      img.src = dataUrl;
    });
  }

  // ---------- OCR ----------
  async function extractFromCard() {
    if (!cardImage) return;
    ocrLoading = true;
    ocrProgress = 0;
    ocrStage = 'Loading OCR engine…';
    submitMessage = '';

    try {
      await loadTesseract();
      if (!window.Tesseract) {
        submitMessage = '⚠️ OCR engine unavailable. Please fill in info manually.';
        ocrLoading = false;
        return;
      }

      ocrStage = 'Sharpening image…';
      const cleaned = await preprocessImage(cardImagePreview);
      processedPreview = cleaned;

      ocrStage = 'Reading card…';
      // Use a reusable worker with logger for progress
      if (!tessWorker) {
        tessWorker = await window.Tesseract.createWorker('eng', 1, {
          logger: (m) => {
            if (m.status === 'recognizing text') {
              ocrProgress = Math.round((m.progress || 0) * 100);
            }
          }
        });
        // Assume a block of text; keep default OEM
        await tessWorker.setParameters({
          preserve_interword_spaces: '1'
        });
      }

      const { data: { text } } = await tessWorker.recognize(cleaned);
      ocrText = (text || '').trim();

      extractedData = parseBusinessCard(ocrText);
      applyExtracted(extractedData);

      submitMessage = '✓ Card read. Confirm the business below.';
      ocrLoading = false;

      // Kick off business matching automatically if we have a name
      if (formData.business_name) {
        matchAgainstProspects();
      }
    } catch (err) {
      console.error('OCR error:', err);
      submitMessage = `Error reading card: ${err.message || 'Unknown error'}. Please fill in manually.`;
      ocrLoading = false;
    }
  }

  function applyExtracted(d) {
    if (!d) return;
    if (d.business_name) formData.business_name = d.business_name;
    if (d.contact_name) formData.contact_name = d.contact_name;
    if (d.title) formData.title = d.title;
    if (d.phone) formData.phone = d.phone;
    if (d.email) formData.email = d.email;
    if (d.website) formData.website = d.website;
    if (d.address) formData.address = d.address;
  }

  // ---------- Human-like business-card parser ----------
  const ROLE_WORDS = ['owner','president','ceo','founder','manager','director','partner','principal','proprietor','gm','general manager','vp','vice president','sales','account','agent','broker','realtor','dds','dmd','md','esq','attorney','consultant','specialist','coordinator','representative','rep','supervisor','operator','chef','stylist'];
  const BIZ_SUFFIX = /\b(inc|inc\.|llc|l\.l\.c|ltd|co\.|company|corp|corporation|group|services|service|restaurant|cafe|café|grill|bar|salon|spa|dental|dentistry|auto|automotive|motors|realty|real estate|insurance|law|firm|clinic|shop|store|market|bakery|pizza|pizzeria|barber|studio|fitness|gym|boutique|jewelers|jewelry|floral|florist|pharmacy|towing|repair|construction|contracting|landscaping|cleaners|cleaning|academy)\b/i;
  const STREET_SUFFIX = /\b(st|street|ave|avenue|blvd|boulevard|dr|drive|rd|road|ln|lane|way|ct|court|pl|place|pkwy|parkway|hwy|highway|sq|square|ste|suite|unit|cir|circle|ter|terrace|trl|trail|loop)\b/i;
  const NON_NAME = /\b(www|http|\.com|\.net|\.org|phone|cell|mobile|office|fax|tel|email|e-mail|call|text|hours|open|mon|tue|wed|thu|fri|sat|sun)\b/i;

  function titleCaseScore(line) {
    const words = line.split(/\s+/).filter(Boolean);
    if (!words.length) return 0;
    const capped = words.filter(w => /^[A-Z][a-z'’.-]*$/.test(w)).length;
    return capped / words.length;
  }

  function parseBusinessCard(text) {
    const rawLines = text.split('\n').map(l => l.replace(/\s+/g, ' ').trim()).filter(l => l.length > 1);

    // --- Phones: collect all, prefer labeled (office/main) over cell/fax ---
    const phones = [];
    const phoneRe = /(?:\+?1[\s.-]?)?\(?(\d{3})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})/g;
    for (const line of rawLines) {
      let m;
      const local = new RegExp(phoneRe.source, 'g');
      while ((m = local.exec(line)) !== null) {
        const norm = `(${m[1]}) ${m[2]}-${m[3]}`;
        const lower = line.toLowerCase();
        let weight = 3;
        if (/\b(office|main|tel|phone|call|direct)\b/.test(lower)) weight = 5;
        else if (/\b(cell|mobile|text)\b/.test(lower)) weight = 4;
        else if (/\bfax\b/.test(lower)) weight = 1;
        phones.push({ norm, weight });
      }
    }
    phones.sort((a, b) => b.weight - a.weight);
    const phone = phones.length ? phones[0].norm : '';

    // --- Email ---
    const emailMatch = text.match(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/);
    let email = emailMatch ? emailMatch[0].toLowerCase() : '';
    email = email.replace(/[).,;]+$/, '');

    // --- Website ---
    let website = '';
    const wwwMatch = text.match(/\b((?:https?:\/\/)?(?:www\.)?[A-Za-z0-9-]+\.(?:com|net|org|biz|us|co|io)(?:\/[^\s]*)?)\b/i);
    if (wwwMatch) {
      website = wwwMatch[1];
      // Don't mistake the email domain for the website
      if (email && website.includes(email.split('@')[1])) {
        // still fine — many cards use same domain; keep it
      }
      if (!/^https?:\/\//i.test(website)) website = 'https://' + website.replace(/^www\./i, 'www.');
    }

    // --- Address: find a line with a street number + suffix, join with the city/state/zip line ---
    let address = '';
    const zipRe = /\b\d{5}(?:-\d{4})?\b/;
    const stateZipRe = /\b([A-Z]{2})\s*,?\s*(\d{5}(?:-\d{4})?)\b/;
    let streetIdx = -1;
    for (let i = 0; i < rawLines.length; i++) {
      const l = rawLines[i];
      if (/^\d+\s+\S/.test(l) && STREET_SUFFIX.test(l)) { streetIdx = i; break; }
    }
    if (streetIdx >= 0) {
      let addr = rawLines[streetIdx];
      // Append following lines until we hit a state+zip
      for (let j = streetIdx + 1; j < Math.min(streetIdx + 3, rawLines.length); j++) {
        addr += ', ' + rawLines[j];
        if (stateZipRe.test(rawLines[j])) break;
      }
      address = addr.replace(/\s*,\s*,/g, ',').trim();
    } else {
      // Fallback: any single line containing a state+zip
      const czLine = rawLines.find(l => stateZipRe.test(l));
      if (czLine) address = czLine;
    }

    // --- Business name & contact name scoring ---
    // Skip lines that are clearly contact info
    const infoIdx = new Set();
    rawLines.forEach((l, i) => {
      if (/@/.test(l) || phoneRe.test(l) || NON_NAME.test(l) || (address && address.includes(l)) || zipRe.test(l)) {
        infoIdx.add(i);
      }
    });

    // Business name: prefer a line with a business suffix, else the first strong (ALL CAPS or top) line
    let business_name = '';
    let bizIdx = -1;
    for (let i = 0; i < rawLines.length; i++) {
      if (infoIdx.has(i)) continue;
      if (BIZ_SUFFIX.test(rawLines[i])) { business_name = rawLines[i]; bizIdx = i; break; }
    }
    if (!business_name) {
      // ALL-CAPS multi-char line near the top is often the business
      for (let i = 0; i < Math.min(4, rawLines.length); i++) {
        if (infoIdx.has(i)) continue;
        const l = rawLines[i];
        const letters = l.replace(/[^A-Za-z]/g, '');
        if (letters.length >= 3 && l === l.toUpperCase() && /[A-Z]/.test(l)) { business_name = l; bizIdx = i; break; }
      }
    }
    if (!business_name) {
      // First non-info line
      for (let i = 0; i < rawLines.length; i++) {
        if (infoIdx.has(i)) continue;
        business_name = rawLines[i]; bizIdx = i; break;
      }
    }

    // Contact name: a title-case 2-3 word line that isn't the business, ideally adjacent to a role word
    let contact_name = '';
    let title = '';
    let bestScore = 0;
    for (let i = 0; i < rawLines.length; i++) {
      if (infoIdx.has(i) || i === bizIdx) continue;
      const l = rawLines[i];
      const words = l.split(/\s+/).filter(Boolean);
      if (words.length < 2 || words.length > 4) continue;
      if (BIZ_SUFFIX.test(l)) continue;
      const tc = titleCaseScore(l);
      if (tc < 0.5) continue;
      let score = tc;
      const lower = l.toLowerCase();
      // Role word on same line → strip it into title
      const roleOnLine = ROLE_WORDS.find(r => new RegExp('\\b' + r + '\\b').test(lower));
      if (roleOnLine) score += 0.4;
      // Role word on adjacent line boosts confidence
      const near = (rawLines[i - 1] || '') + ' ' + (rawLines[i + 1] || '');
      if (ROLE_WORDS.some(r => new RegExp('\\b' + r + '\\b').test(near.toLowerCase()))) score += 0.3;
      if (score > bestScore) {
        bestScore = score;
        // If role word is embedded, split name vs title
        if (roleOnLine) {
          const idx = lower.indexOf(roleOnLine);
          contact_name = l.slice(0, idx).replace(/[,-]\s*$/, '').trim();
          title = l.slice(idx).trim();
          if (!contact_name) { contact_name = l; title = ''; }
        } else {
          contact_name = l;
          // grab a title from an adjacent line if present
          const adj = ROLE_WORDS.find(r => new RegExp('\\b' + r + '\\b').test((rawLines[i + 1] || '').toLowerCase()));
          if (adj) title = rawLines[i + 1];
        }
      }
    }

    return { business_name, contact_name, title, phone, email, website, address, raw_text: text };
  }

  // ---------- Match against real businesses (Google Places / prospect DB) ----------
  async function matchAgainstProspects() {
    const name = formData.business_name?.trim();
    if (!name) { submitMessage = 'Enter a business name first to search.'; return; }
    matchLoading = true;
    matchCandidates = [];
    matchedBusiness = null;
    submitMessage = `Searching for "${name}"…`;

    try {
      // Build a location-aware query from any address/city/zip we have
      const addr = formData.address || '';
      const zipMatch = addr.match(/\b\d{5}\b/);
      const stateMatch = addr.match(/\b([A-Z]{2})\b(?=\s*\d{5})/);
      let textQuery = name;
      if (addr) textQuery = `${name}, ${addr}`;
      else if (formData.store_city) textQuery = `${name} near ${formData.store_city}`;

      const body = { textQuery, maxResultCount: 5 };

      const resp = await fetch('https://places.googleapis.com/v1/places:searchText', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Goog-Api-Key': PLACES_API_KEY,
          'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.location,places.businessStatus,places.nationalPhoneNumber,places.websiteUri,places.googleMapsUri,places.primaryTypeDisplayName,places.types'
        },
        body: JSON.stringify(body)
      });

      if (!resp.ok) {
        const t = await resp.text();
        console.error('Places match error', resp.status, t);
        submitMessage = 'Could not reach business lookup. You can still submit manually.';
        matchLoading = false;
        return;
      }
      const data = await resp.json();
      matchCandidates = (data.places || []).map(p => ({
        name: p.displayName?.text || 'Unnamed',
        address: p.formattedAddress || '',
        rating: p.rating || 0,
        reviews: p.userRatingCount || 0,
        phone: p.nationalPhoneNumber || '',
        website: p.websiteUri || '',
        mapsUrl: p.googleMapsUri || '',
        type: p.primaryTypeDisplayName?.text || '',
        types: p.types || [],
        lat: p.location?.latitude || 0,
        lng: p.location?.longitude || 0
      }));

      if (matchCandidates.length === 0) {
        submitMessage = `No match found for "${name}". Fill in details manually.`;
      } else {
        submitMessage = `Found ${matchCandidates.length} possible match${matchCandidates.length > 1 ? 'es' : ''} — pick the right one.`;
        // Auto-select if the top result name is a strong match
        if (nameSimilarity(name, matchCandidates[0].name) > 0.6) {
          confirmMatch(matchCandidates[0]);
        }
      }
    } catch (err) {
      console.error('match error', err);
      submitMessage = 'Business lookup failed. You can still submit manually.';
    } finally {
      matchLoading = false;
    }
  }

  function nameSimilarity(a, b) {
    const norm = s => s.toLowerCase().replace(/[^a-z0-9 ]/g, '').replace(/\b(the|inc|llc|co|company|restaurant|grill|cafe)\b/g, '').trim();
    const wa = new Set(norm(a).split(/\s+/).filter(Boolean));
    const wb = new Set(norm(b).split(/\s+/).filter(Boolean));
    if (!wa.size || !wb.size) return 0;
    let inter = 0;
    wa.forEach(w => { if (wb.has(w)) inter++; });
    return inter / Math.max(wa.size, wb.size);
  }

  function confirmMatch(cand) {
    matchedBusiness = cand;
    formData.business_name = cand.name;
    if (cand.address) formData.address = cand.address;
    if (cand.phone && !formData.phone) formData.phone = cand.phone;
    if (cand.website && !formData.website) formData.website = cand.website;
    const cat = mapCategory(cand);
    if (cat) formData.category = cat;
    // Now find nearest stores by real coordinates
    if (cand.lat && cand.lng) findNearestStoresByCoords(cand.lat, cand.lng);
    submitMessage = `✓ Matched to ${cand.name}.`;
  }

  // Map Google Places types → our category list (best-effort)
  function mapCategory(cand) {
    const hay = ((cand.type || '') + ' ' + (cand.types || []).join(' ')).toLowerCase();
    const rules = [
      [/pizza/, 'Restaurant / Pizza'],
      [/mexican|taco/, 'Restaurant / Mexican'],
      [/chinese|japanese|thai|sushi|asian|korean|vietnam/, 'Restaurant / Asian'],
      [/bakery|bakeries/, 'Restaurant / Bakery'],
      [/coffee|cafe|espresso/, 'Restaurant / Coffee Shops'],
      [/fast.?food|burger/, 'Restaurant / Fast Food'],
      [/bar|pub|brewery|brewpub/, 'Entertainment / Bar / Night Club'],
      [/restaurant|dining|food/, 'Restaurant / Casual Dining'],
      [/dental|dentist|orthodont/, 'Health / Dental / Orthodontics'],
      [/doctor|medical|clinic|physician/, 'Health / Medical'],
      [/optical|optomet|eye/, 'Health / Optical'],
      [/gym|fitness|yoga/, 'Health / Fitness & Health'],
      [/hair|salon|barber|nail|spa|tanning/, 'Beauty / Hair / Nails / Spa / Tanning'],
      [/car.?wash|detail/, 'Auto / Car Wash / Detailing'],
      [/car.?repair|auto.?repair|mechanic|body.?shop/, 'Auto / Repair / Body / Maintenance'],
      [/car.?dealer|auto.?dealer|used.?car/, 'Auto / Sales / Leasing / Rental'],
      [/real.?estate|realtor/, 'Home Services / Real Estate / Realtors'],
      [/insurance/, 'Insurance'],
      [/lawyer|attorney|legal/, 'Legal / Attorney / Law Firm'],
      [/jewel/, 'Retail / Jewelry / Watch Repair'],
      [/florist|flower/, 'Retail / Florists'],
      [/furniture/, 'Retail / Furniture'],
      [/grocery|supermarket/, 'Retail / Grocery Store'],
      [/pet.?store|pet.?supply/, 'Retail / Pet Supply Store'],
      [/veterin|pet/, 'Home Services / Pet Care'],
      [/tattoo/, 'Entertainment / Tattoos & Piercing'],
    ];
    for (const [re, cat] of rules) if (re.test(hay)) return cat;
    return '';
  }

  // ---------- Store distance matching (haversine, real fields) ----------
  function haversine(lat1, lon1, lat2, lon2) {
    const R = 3958.8; // miles
    const toRad = d => (d * Math.PI) / 180;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  function findNearestStoresByCoords(lat, lng) {
    if (!allStores.length) return;
    const scored = allStores
      .filter(s => s.latitude && s.longitude)
      .map(s => ({ store: s, distance: haversine(lat, lng, s.latitude, s.longitude) }))
      .filter(x => x.distance <= 60)
      .sort((a, b) => a.distance - b.distance)
      .slice(0, 3);
    nearestStores = scored;
    if (scored.length) selectNearestStore(scored[0]);
  }

  function selectNearestStore(entry) {
    const s = entry.store;
    formData.store_id = s.StoreName;
    formData.store_chain = s.GroceryChain;
    formData.store_city = s.City;
    formData.distance_mi = Math.round(entry.distance * 10) / 10;
    storeSearchText = `${s.GroceryChain} — ${s.City}, ${s.State} (${s.StoreName})`;
  }

  function selectStoreFromSearch(store) {
    formData.store_id = store.StoreName || store.id;
    formData.store_chain = store.GroceryChain || store.chain;
    formData.store_city = store.City || store.city;
    formData.distance_mi = '';
    storeSearchText = `${formData.store_chain} — ${formData.store_city}, ${store.State || store.state} (${formData.store_id})`;
  }

  // ---------- Submit ----------
  async function submitLead() {
    if (!formData.business_name || (!formData.phone && !formData.email)) {
      alert('Please provide a Business Name and at least a Phone or Email.');
      return;
    }
    submitting = true;
    submitMessage = 'Saving lead…';

    const newLead = {
      ...formData,
      contact_name: formData.contact_name || '',
      submitted_by: user?.name || 'Unknown',
      submitted_by_id: user?.id || '',
      submitted_at: new Date().toISOString(),
      source: 'business_card',
      matched: !!matchedBusiness,
      status: 'approved',
      _hook: `Submitted by ${user?.name || 'rep'}${matchedBusiness ? ' (verified)' : ''}`
    };

    try {
      // 1) Local cache (immediate, offline-safe)
      const leads = JSON.parse(localStorage.getItem('submitted_leads') || '[]');
      leads.push(newLead);
      localStorage.setItem('submitted_leads', JSON.stringify(leads));

      // 2) Firebase sync so it shows on other devices (best-effort)
      try {
        await whenFirebaseReady(4000);
        if (isFirebaseReady()) {
          await saveLeadData(newLead.business_name, newLead.address || '', {
            ...newLead,
            leadType: 'submitted',
            contactName: newLead.contact_name,
            contactPhone: newLead.phone,
            contactEmail: newLead.email
          });
        }
      } catch (e) {
        console.warn('Firebase sync skipped:', e);
      }

      submitMessage = '✅ Lead saved to Hot Leads!';
      setTimeout(() => {
        resetForm();
        onLeadSubmitted();
      }, 1600);
    } catch (err) {
      submitMessage = `Error: ${err.message}`;
      submitting = false;
    }
  }

  function resetForm() {
    formData = {
      business_name: '', contact_name: '', title: '', category: 'Restaurant / Casual Dining',
      phone: '', email: '', website: '', address: '',
      store_id: '', store_chain: '', store_city: '', distance_mi: ''
    };
    cardImage = null; cardImagePreview = null; processedPreview = null;
    ocrText = ''; extractedData = null;
    matchCandidates = []; matchedBusiness = null; nearestStores = [];
    storeSearchText = ''; submitMessage = ''; submitting = false;
  }
</script>

<div class="submit-container">
  <div class="submit-header">
    <h3>➕ Submit New Lead</h3>
    <p>Snap a business card — I'll read it and match the business for you.</p>
  </div>

  <div class="mode-toggle">
    <button class="mode-btn" class:active={submitMode === 'card'} on:click={() => submitMode = 'card'}>
      📷 Business Card
    </button>
    <button class="mode-btn" class:active={submitMode === 'manual'} on:click={() => submitMode = 'manual'}>
      ✍️ Manual Entry
    </button>
  </div>

  {#if submitMode === 'card'}
    <div class="card-upload">
      <div class="upload-area">
        <input id="card-file" type="file" accept="image/*" capture="environment"
          on:change={handleCardImageSelect} class="file-input" />
        <label for="card-file" class="upload-label">
          📸 {cardImagePreview ? 'Choose a different photo' : 'Take / upload business card'}
        </label>
        {#if cardImagePreview}
          <div class="preview">
            <img src={cardImagePreview} alt="Card preview" />
          </div>
        {/if}
      </div>

      {#if cardImage}
        <button class="extract-btn" on:click={extractFromCard} disabled={ocrLoading}>
          {#if ocrLoading}
            {ocrStage} {ocrProgress > 0 ? `${ocrProgress}%` : ''}
          {:else}
            🔍 Read Card
          {/if}
        </button>
      {/if}

      {#if ocrLoading && ocrProgress > 0}
        <div class="progress-bar"><div class="progress-fill" style="width:{ocrProgress}%"></div></div>
      {/if}

      {#if ocrText}
        <button class="link-btn" on:click={() => showRawText = !showRawText}>
          {showRawText ? 'Hide' : 'Show'} raw text
        </button>
        {#if showRawText}
          <div class="ocr-result"><pre>{ocrText}</pre></div>
        {/if}
      {/if}
    </div>
  {/if}

  <!-- Business match panel -->
  {#if matchCandidates.length > 0}
    <div class="match-panel">
      <div class="match-title">🔎 Matching business</div>
      {#each matchCandidates as c}
        <button class="match-card" class:selected={matchedBusiness && matchedBusiness.name === c.name && matchedBusiness.address === c.address}
          on:click={() => confirmMatch(c)}>
          <div class="mc-name">{c.name} {#if matchedBusiness && matchedBusiness.name === c.name}✅{/if}</div>
          <div class="mc-addr">{c.address}</div>
          <div class="mc-meta">
            {#if c.rating}⭐ {c.rating} ({c.reviews}){/if}
            {#if c.type} · {c.type}{/if}
            {#if c.phone} · {c.phone}{/if}
          </div>
        </button>
      {/each}
    </div>
  {/if}

  <div class="form-section">
    <div class="form-group">
      <label>Business Name *</label>
      <div class="inline-input">
        <input type="text" placeholder="e.g., Golden Star Chinese Restaurant" bind:value={formData.business_name} />
        <button class="find-btn" on:click={matchAgainstProspects} disabled={matchLoading || !formData.business_name}>
          {matchLoading ? '…' : '🔎 Match'}
        </button>
      </div>
    </div>

    <div class="form-row">
      <div class="form-group">
        <label>Contact Name</label>
        <input type="text" placeholder="e.g., John Smith" bind:value={formData.contact_name} />
      </div>
      <div class="form-group">
        <label>Title / Role</label>
        <input type="text" placeholder="e.g., Owner" bind:value={formData.title} />
      </div>
    </div>

    <div class="form-group">
      <label>Category</label>
      <select bind:value={formData.category}>
        {#each categories as cat}<option>{cat}</option>{/each}
      </select>
    </div>

    <div class="form-row">
      <div class="form-group">
        <label>Phone *</label>
        <input type="tel" placeholder="(360) 373-1320" bind:value={formData.phone} />
      </div>
      <div class="form-group">
        <label>Email</label>
        <input type="email" placeholder="info@business.com" bind:value={formData.email} />
      </div>
    </div>

    <div class="form-group">
      <label>Website</label>
      <input type="text" placeholder="https://business.com" bind:value={formData.website} />
    </div>

    <div class="form-group">
      <label>Address</label>
      <input type="text" placeholder="123 Main St, City, WA 98000" bind:value={formData.address} />
    </div>

    <!-- Nearest store suggestions from match -->
    {#if nearestStores.length > 0}
      <div class="form-group">
        <label>Nearest stores (by distance)</label>
        <div class="near-stores">
          {#each nearestStores as ns}
            <button class="near-store" class:selected={formData.store_id === ns.store.StoreName}
              on:click={() => selectNearestStore(ns)}>
              <strong>{ns.store.GroceryChain}</strong> — {ns.store.City}, {ns.store.State}
              <span class="ns-dist">{Math.round(ns.distance * 10) / 10} mi</span>
              <small>{ns.store.StoreName} · Cycle {ns.store.Cycle}</small>
            </button>
          {/each}
        </div>
      </div>
    {/if}

    <div class="form-group">
      <label>Store Reference {nearestStores.length ? '(or search another)' : '(optional)'}</label>
      <StoreSearchInput
        stores={allStoresRaw}
        placeholder="Search by store ID, chain, city, address, or zip..."
        maxResults={8}
        showGeo={true}
        on:select={e => selectStoreFromSearch(e.detail)}
      />
      {#if formData.store_id}
        <div class="selected-store">
          ✅ {formData.store_chain} — {formData.store_city} ({formData.store_id})
          {#if formData.distance_mi !== ''} · {formData.distance_mi} mi{/if}
        </div>
      {/if}
    </div>

    {#if submitMessage}
      <div class="message" class:loading={submitting || ocrLoading || matchLoading} class:success={submitMessage.includes('✅') || submitMessage.includes('✓')}>
        {submitMessage}
      </div>
    {/if}
  </div>

  <div class="submit-footer">
    <button class="submit-btn" on:click={submitLead}
      disabled={submitting || !formData.business_name || (!formData.phone && !formData.email)}>
      {submitting ? '⏳ Saving…' : '📤 Submit Lead'}
    </button>
  </div>
</div>

<style>
  .submit-container {
    background: white; border-radius: 12px; padding: 24px; max-width: 800px;
    margin: 0 auto; width: 100%; box-sizing: border-box; display: flex;
    flex-direction: column; height: 100%; overflow-y: auto; -webkit-overflow-scrolling: touch;
  }
  .submit-header { margin-bottom: 20px; }
  .submit-header h3 { margin: 0 0 4px 0; font-size: 20px; color: #333; }
  .submit-header p { margin: 0; font-size: 14px; color: #666; }
  .mode-toggle { display: flex; gap: 12px; margin-bottom: 20px; border-bottom: 2px solid #e0e0e0; }
  .mode-btn { background: none; border: none; padding: 12px 16px; font-size: 14px; font-weight: 600;
    cursor: pointer; color: #999; border-bottom: 3px solid transparent; transition: all 0.2s; }
  .mode-btn.active { color: #CC0000; border-bottom-color: #CC0000; }
  .card-upload { margin-bottom: 20px; padding: 16px; background: #f9f9f9; border-radius: 8px; }
  .upload-area { position: relative; }
  .file-input { display: none; }
  .upload-label { display: block; padding: 20px; border: 2px dashed #ddd; border-radius: 8px;
    text-align: center; font-weight: 600; cursor: pointer; transition: all 0.2s; }
  .file-input:hover + .upload-label, .file-input:focus + .upload-label { border-color: #CC0000; background: #fff5f5; }
  .upload-label:active { transform: scale(0.98); }
  .preview { margin-top: 12px; max-width: 320px; }
  .preview img { width: 100%; border-radius: 6px; border: 1px solid #ddd; }
  .extract-btn { margin-top: 12px; width: 100%; padding: 12px; background: #CC0000; color: white;
    border: none; border-radius: 6px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
  .extract-btn:hover:not(:disabled) { background: #990000; }
  .extract-btn:disabled { opacity: 0.7; }
  .progress-bar { margin-top: 8px; height: 6px; background: #eee; border-radius: 3px; overflow: hidden; }
  .progress-fill { height: 100%; background: #CC0000; transition: width 0.2s; }
  .link-btn { margin-top: 10px; background: none; border: none; color: #1565c0; font-size: 12px;
    cursor: pointer; text-decoration: underline; padding: 0; }
  .ocr-result { margin-top: 8px; padding: 12px; background: white; border-radius: 6px; }
  .ocr-result pre { margin: 0; font-size: 12px; max-height: 200px; overflow-y: auto;
    background: #f9f9f9; padding: 8px; border-radius: 4px; white-space: pre-wrap; }

  .match-panel { margin-bottom: 20px; padding: 12px; background: #f0f7ff; border: 1px solid #cfe3ff;
    border-radius: 10px; }
  .match-title { font-size: 13px; font-weight: 700; color: #1565c0; margin-bottom: 8px; }
  .match-card { display: block; width: 100%; text-align: left; background: white; border: 2px solid #e0e0e0;
    border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; cursor: pointer; transition: all 0.15s; }
  .match-card:hover { border-color: #1565c0; }
  .match-card.selected { border-color: #2e7d32; background: #e8f5e9; }
  .mc-name { font-weight: 700; color: #222; font-size: 14px; }
  .mc-addr { font-size: 12px; color: #555; margin-top: 2px; }
  .mc-meta { font-size: 11px; color: #888; margin-top: 3px; }

  .form-section { display: flex; flex-direction: column; gap: 16px; }
  .form-group { display: flex; flex-direction: column; gap: 6px; position: relative; }
  .form-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
  label { font-size: 13px; font-weight: 600; color: #333; }
  input, select { padding: 10px 12px; border: 2px solid #ddd; border-radius: 6px; font-size: 13px; font-family: inherit; }
  input:focus, select:focus { outline: none; border-color: #CC0000; }
  .inline-input { display: flex; gap: 8px; }
  .inline-input input { flex: 1; }
  .find-btn { white-space: nowrap; padding: 0 14px; background: #1565c0; color: white; border: none;
    border-radius: 6px; font-weight: 600; font-size: 13px; cursor: pointer; }
  .find-btn:disabled { opacity: 0.5; }

  .near-stores { display: flex; flex-direction: column; gap: 8px; }
  .near-store { text-align: left; background: white; border: 2px solid #e0e0e0; border-radius: 8px;
    padding: 10px 12px; cursor: pointer; font-size: 13px; transition: all 0.15s; position: relative; }
  .near-store:hover { border-color: #2e7d32; }
  .near-store.selected { border-color: #2e7d32; background: #e8f5e9; }
  .near-store small { display: block; color: #888; font-size: 11px; margin-top: 2px; }
  .ns-dist { position: absolute; top: 10px; right: 12px; font-weight: 700; color: #2e7d32; font-size: 12px; }

  .selected-store { padding: 10px 14px; background: #e8f5e9; border-radius: 8px; font-size: 14px;
    color: #2e7d32; font-weight: 600; margin-top: 4px; }
  .message { padding: 12px; border-radius: 6px; font-size: 13px; background: #e8f5e9; color: #2e7d32; border: 1px solid #81c784; }
  .message.loading { background: #e3f2fd; color: #1565c0; border-color: #64b5f6; }
  .submit-footer { position: sticky; bottom: 0; background: white; padding: 16px 24px;
    border-top: 2px solid #e0e0e0; margin: 16px -24px -24px -24px; padding-bottom: calc(16px + env(safe-area-inset-bottom)); }
  .submit-btn { width: 100%; padding: 12px 16px; background: #CC0000; color: white; border: none;
    border-radius: 6px; font-weight: 600; font-size: 14px; cursor: pointer; transition: all 0.2s; }
  .submit-btn:hover:not(:disabled) { background: #990000; }
  .submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }
  @media (max-width: 480px) {
    .submit-container { padding: 16px; }
    .form-row { grid-template-columns: 1fr; }
  }
</style>
