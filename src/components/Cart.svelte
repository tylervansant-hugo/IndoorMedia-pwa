<script>
  import { onMount, onDestroy } from 'svelte';
  import { padAmount, user } from '../lib/stores.js';

  // When true, this tab is the active/visible one. Reload from storage on show
  // so items added from other tabs (which stay mounted) appear immediately.
  export let active = false;
  import { PDFDocument, rgb, StandardFonts } from 'pdf-lib';
  import StoreSearchInput from '../lib/StoreSearchInput.svelte';

  let cartItems = [];
  let allStores = [];
  let showAddProduct = false;
  let addStep = 'type'; // type, store, plan, confirm
  let newItem = { type: '', store: null, plan: '', pins: 1, price: '' };
  let storeSearch = '';
  let cartAdType = 'single'; // single or double
  let businessName = '';

  // Drag-and-drop reorder state
  let dragIndex = null;
  let dragOverIndex = null;
  let touchStartY = 0;
  let isDragging = false;

  function handleDragStart(e, index) {
    dragIndex = index;
    isDragging = true;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', index);
  }

  function handleDragOver(e, index) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    dragOverIndex = index;
  }

  function handleDragLeave() {
    dragOverIndex = null;
  }

  function handleDrop(e, index) {
    e.preventDefault();
    if (dragIndex !== null && dragIndex !== index) {
      reorderItems(dragIndex, index);
    }
    dragIndex = null;
    dragOverIndex = null;
    isDragging = false;
  }

  function handleDragEnd() {
    dragIndex = null;
    dragOverIndex = null;
    isDragging = false;
  }

  // Touch handlers for mobile drag
  function handleTouchStart(e, index) {
    dragIndex = index;
    touchStartY = e.touches[0].clientY;
  }

  function handleTouchMove(e, index) {
    if (dragIndex === null) return;
    const touch = e.touches[0];
    const elements = document.querySelectorAll('.quote-item');
    
    for (let i = 0; i < elements.length; i++) {
      const rect = elements[i].getBoundingClientRect();
      if (touch.clientY >= rect.top && touch.clientY <= rect.bottom) {
        dragOverIndex = i;
        break;
      }
    }
  }

  function handleTouchEnd() {
    if (dragIndex !== null && dragOverIndex !== null && dragIndex !== dragOverIndex) {
      reorderItems(dragIndex, dragOverIndex);
    }
    dragIndex = null;
    dragOverIndex = null;
  }

  function reorderItems(fromIndex, toIndex) {
    const items = [...cartItems];
    const [moved] = items.splice(fromIndex, 1);
    items.splice(toIndex, 0, moved);
    cartItems = items;
    saveCart();
  }

  function moveItem(index, direction) {
    const newIndex = index + direction;
    if (newIndex < 0 || newIndex >= cartItems.length) return;
    reorderItems(index, newIndex);
  }

  // Zone 07 cycle launch dates (7th of each month)
  const CYCLE_MONTHS = { 'A': [0,3,6,9], 'B': [1,4,7,10], 'C': [2,5,8,11] };

  function getNextLaunch(cycle) {
    const months = CYCLE_MONTHS[cycle?.toUpperCase()];
    if (!months) return '';
    const now = new Date();
    for (let offset = 0; offset < 12; offset++) {
      const m = (now.getMonth() + offset) % 12;
      if (months.includes(m)) {
        const y = now.getFullYear() + Math.floor((now.getMonth() + offset) / 12);
        const d = new Date(y, m, 7);
        if (d > now || (d.getMonth() === now.getMonth() && d.getDate() >= now.getDate())) {
          return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        }
      }
    }
    return '';
  }

  const PRODUCT_TYPES = [
    { id: 'tape_single', name: 'Register Tape — Single Ad', emoji: '🧾', needsStore: true, adSize: 'single' },
    { id: 'tape_double', name: 'Register Tape — Double Ad', emoji: '🧾', needsStore: true, adSize: 'double' },
    { id: 'tape_coop', name: 'Register Tape — Co-Op', emoji: '🧾', needsStore: true },
    { id: 'tape_exclusive', name: 'Register Tape — Exclusive', emoji: '🧾', needsStore: true },
    { id: 'tape_contractor', name: 'Register Tape — Contractors', emoji: '🧾', needsStore: true },
    { id: 'cart_20_single', name: 'Cartvertising — 20% Front OR Directory', emoji: '🛒', price: '$2,995', needsStore: true, skipPlan: true },
    { id: 'cart_40_both', name: 'Cartvertising — 40% (20%+20%)', emoji: '🛒', price: '$4,795', needsStore: true, skipPlan: true },
    { id: 'cart_60_both', name: 'Cartvertising — 60% (40%+20%)', emoji: '🛒', price: '$5,995', needsStore: true, skipPlan: true },
    { id: 'cart_80_both', name: 'Cartvertising — 80% (40%+40%)', emoji: '🛒', price: '$7,395', needsStore: true, skipPlan: true },
    { id: 'cart_100_both', name: 'Cartvertising — 100% (60%+40%)', emoji: '🛒', price: '$8,795', needsStore: true, skipPlan: true },
    { id: 'cart_200_both', name: 'Cartvertising — 200% (100% Both)', emoji: '🛒', price: '$12,995', needsStore: true, skipPlan: true },
    { id: 'cart_header_50', name: 'Cartvertising — Header 50%', emoji: '🛒', price: '$2,995', needsStore: true, skipPlan: true },
    { id: 'cart_header_100', name: 'Cartvertising — Header 100%', emoji: '🛒', price: '$4,795', needsStore: true, skipPlan: true },
    { id: 'digitalboost', name: 'DigitalBoost', emoji: '🚀', price: '$3,600/pin', needsStore: true, skipPlan: true, hasPins: true, hasMap: true },
    { id: 'findlocal', name: 'FindLocal', emoji: '📍', price: '$695/location', needsStore: true, skipPlan: true, hasMap: true },
    { id: 'reviewboost', name: 'ReviewBoost', emoji: '⭐', price: '$695', needsStore: true, skipPlan: true },
    { id: 'loyaltyboost', name: 'LoyaltyBoost', emoji: '💎', price: '$3,600/year', needsStore: true, skipPlan: true },
  ];

  // Payment plans: base = raw store price, pad = rep's pad amount, prod = $125 production
  // Co-op plans use pad=0; standard plans use the rep's configured pad
  $: PAYMENT_PLANS = (() => {
    const pad = $padAmount != null ? $padAmount : 1200;
    const prod = 125;
    return {
      tape_single: [
        { id: 'monthly', name: 'Monthly (12 payments)', calc: (base) => { const t = base + pad + prod; return (t / 12).toFixed(2) + '/mo × 12 = $' + t.toFixed(2); } },
        { id: '3month', name: '3-Month (10% off)', calc: (base) => { const t = ((base + pad) * 0.90) + prod; return (t / 3).toFixed(2) + '/payment × 3 = $' + t.toFixed(2); } },
        { id: '6month', name: '6-Month (7.5% off)', calc: (base) => { const t = ((base + pad) * 0.925) + prod; return (t / 6).toFixed(2) + '/payment × 6 = $' + t.toFixed(2); } },
        { id: 'pif', name: 'Paid-in-Full (15% off)', calc: (base) => '$' + (((base + pad) * 0.85) + prod).toFixed(2) },
      ],
      tape_double: [
        { id: 'monthly', name: 'Monthly (12 payments)', calc: (base) => { const t = base + pad + prod; return (t / 12).toFixed(2) + '/mo × 12 = $' + t.toFixed(2); } },
        { id: '3month', name: '3-Month (10% off)', calc: (base) => { const t = ((base + pad) * 0.90) + prod; return (t / 3).toFixed(2) + '/payment × 3 = $' + t.toFixed(2); } },
        { id: '6month', name: '6-Month (7.5% off)', calc: (base) => { const t = ((base + pad) * 0.925) + prod; return (t / 6).toFixed(2) + '/payment × 6 = $' + t.toFixed(2); } },
        { id: 'pif', name: 'Paid-in-Full (15% off)', calc: (base) => '$' + (((base + pad) * 0.85) + prod).toFixed(2) },
      ],
      tape_coop: [
        { id: 'monthly', name: 'Monthly (12 payments)', calc: (base) => { const t = base + prod; return (t / 12).toFixed(2) + '/mo × 12 = $' + t.toFixed(2); } },
        { id: '3month', name: '3-Month (10% off)', calc: (base) => { const t = (base * 0.90) + prod; return (t / 3).toFixed(2) + '/payment × 3 = $' + t.toFixed(2); } },
        { id: '6month', name: '6-Month (7.5% off)', calc: (base) => { const t = (base * 0.925) + prod; return (t / 6).toFixed(2) + '/payment × 6 = $' + t.toFixed(2); } },
        { id: 'pif', name: 'Paid-in-Full (15% off)', calc: (base) => '$' + ((base * 0.85) + prod).toFixed(2) },
      ],
      tape_exclusive: [
        { id: 'monthly', name: 'Monthly', calc: (base) => { const t = base + pad + prod; return (t / 12).toFixed(2) + '/mo × 12 = $' + t.toFixed(2); } },
        { id: 'pif', name: 'Paid-in-Full (5% off)', calc: (base) => '$' + ((base + pad) * 0.95).toFixed(2) },
      ],
      tape_contractor: [
        { id: '3month', name: '3-Month', calc: (base) => { const t = base + pad + prod; return (t / 3).toFixed(2) + '/payment × 3 = $' + t.toFixed(2); } },
        { id: 'pif', name: 'Paid-in-Full (5% off)', calc: (base) => '$' + ((base + pad) * 0.95).toFixed(2) },
      ],
    };
  })();

  let _lastActive = false;
  // Reload whenever this tab transitions from hidden -> visible.
  $: if (active && !_lastActive) { loadCart(); _lastActive = true; }
  $: if (!active) { _lastActive = false; }

  function onCartUpdated() { loadCart(); }

  onMount(async () => {
    loadCart();
    // Live refresh: other components dispatch this after writing the cart.
    window.addEventListener('cart-updated', onCartUpdated);
    // Cross-document changes (rare, multi-tab) still work via storage event.
    window.addEventListener('storage', onCartUpdated);
    try {
      const res = await fetch(import.meta.env.BASE_URL + 'data/stores.json?t=' + Date.now());
      allStores = await res.json();
    } catch {}
  });

  onDestroy(() => {
    window.removeEventListener('cart-updated', onCartUpdated);
    window.removeEventListener('storage', onCartUpdated);
  });

  function loadCart() {
    try { cartItems = JSON.parse(localStorage.getItem('indoormedia_cart') || '[]'); } catch { cartItems = []; }
  }

  function saveCart() {
    localStorage.setItem('indoormedia_cart', JSON.stringify(cartItems));
    try { window.dispatchEvent(new Event('cart-updated')); } catch {}
  }

  function removeItem(index) {
    cartItems.splice(index, 1);
    cartItems = [...cartItems];
    saveCart();
  }

  function updateItemPrice(index, newPrice) {
    cartItems[index].price = newPrice;
    cartItems = [...cartItems];
    saveCart();
  }

  function clearCart() {
    if (confirm('Clear entire quote?')) {
      cartItems = [];
      saveCart();
    }
  }

  let filteredStores = [];
  function onCartStoreResults(e) { filteredStores = e.detail || []; }
  let storeSearchInput;

  function startAdd() {
    showAddProduct = true;
    addStep = 'type';
    newItem = { type: '', store: null, plan: '', pins: 1, price: '' };
    storeSearch = '';
  }

  function selectType(type) {
    newItem.type = type.id;
    newItem.typeName = type.name;
    newItem.emoji = type.emoji;
    newItem.price = type.price || '';
    newItem.hasPins = type.hasPins || false;
    newItem.skipPlan = type.skipPlan || false;
    newItem.hasMap = type.hasMap || false;

    if (type.needsStore) {
      addStep = 'store';
    } else if (type.hasPins) {
      addStep = 'pins';
    } else {
      addItem();
    }
  }

  function selectStore(store) {
    newItem.store = store;
    newItem.storeNum = store.StoreName;
    newItem.storeAddress = store.Address || '';
    newItem.storeCycle = store.Cycle || '?';
    newItem.storeName = store.GroceryChain + ' - ' + store.City;

    if (newItem.hasPins) {
      addStep = 'pins';
    } else if (newItem.skipPlan) {
      addItem();
    } else {
      addStep = 'plan';
    }
  }

  function useMapArea() {
    // Open Google Maps for area selection, then continue without a specific store
    newItem.store = null;
    newItem.storeNum = 'MAP AREA';
    newItem.storeAddress = 'Custom map area';
    newItem.storeCycle = '-';
    newItem.storeName = 'Custom Area (see map)';
    
    if (newItem.hasPins) {
      addStep = 'pins';
    } else {
      addItem();
    }
  }

  function selectPlan(plan) {
    // Determine base price: use product adSize if set, otherwise use cart toggle
    const productType = PRODUCT_TYPES.find(t => t.id === newItem.type);
    let adSel = productType?.adSize || cartAdType;
    const base = adSel === 'double' && newItem.store?.DoubleAd ? newItem.store.DoubleAd : (newItem.store?.SingleAd || 0);
    newItem.plan = plan.name;
    newItem.adType = adSel === 'double' ? 'Double Ad' : 'Single Ad';
    newItem.planCalc = plan.calc(base);
    newItem.priceText = plan.calc(base);
    addStep = 'confirm';
  }

  function confirmPlan() {
    newItem.price = newItem.priceText;
    addItem();
  }

  function addItem() {
    const item = {
      id: Date.now(),
      name: newItem.typeName,
      emoji: newItem.emoji,
      store: newItem.storeName || '',
      storeNum: newItem.storeNum || '',
      storeAddress: newItem.storeAddress || '',
      storeCycle: newItem.storeCycle || '',
      plan: newItem.plan || '',
      price: newItem.price,
      pins: newItem.hasPins ? newItem.pins : null,
      addedAt: new Date().toISOString(),
    };

    if (newItem.hasPins) {
      const pinPrice = newItem.type === 'digitalboost' ? 3600 : 0;
      const production = 395;
      const total = (pinPrice * newItem.pins) + production;
      item.price = `$${total.toLocaleString()} (${newItem.pins} pin${newItem.pins > 1 ? 's' : ''} + $395 production)`;
      item.name = `DigitalBoost — ${newItem.pins} Pin${newItem.pins > 1 ? 's' : ''}`;
    }

    cartItems = [...cartItems, item];
    saveCart();
    showAddProduct = false;
    addStep = 'type';
  }

  function parseAnnualPrice(item) {
    // Extract annual total from price strings
    const price = item.price || '';
    const plan = item.plan || '';
    // Look for "= $X,XXX" pattern (the total after =)
    const eqMatch = price.match(/=\s*\$([0-9,]+)/);
    if (eqMatch) return parseFloat(eqMatch[1].replace(/,/g, ''));
    // Plain "$X,XXX" (PIF)
    const plainMatch = price.match(/\$([0-9,]+)/);
    if (!plainMatch) return 0;
    const val = parseFloat(plainMatch[1].replace(/,/g, ''));
    // Determine multiplier from plan
    if (plan.toLowerCase().includes('monthly') || plan.toLowerCase().includes('12 payment')) return val * 12;
    if (plan.toLowerCase().includes('3-month')) return val * 4;
    if (plan.toLowerCase().includes('6-month')) return val * 2;
    return val;
  }

  function getImpressions(item) {
    const name = (item.name || '').toLowerCase();
    if (name.includes('register tape')) {
      // Try item.storeCases first, then look up from allStores by store number
      let cases = item.storeCases || 0;
      if (!cases && item.storeNum) {
        const store = allStores.find(s => s.StoreName === item.storeNum);
        if (store) cases = parseInt(store['Case Count']) || 0;
      }
      const daily = cases * 150;
      return { daily, monthly: Math.round(daily * 30.4), annual: daily * 365 };
    }
    if (name.includes('cartvertising')) {
      // Cartvertising is measured by carts showing the ad, not impressions.
      return null;
    }
    if (name.includes('digitalboost') || name.includes('digital boost')) {
      const pins = 1; // default
      return { daily: 660 * pins, monthly: 20000 * pins, annual: 240000 * pins };
    }
    return null; // other digital products - skip
  }

  // For a Cartvertising item, describe how many carts will show the ad.
  function getCartCoverage(item) {
    const name = (item.name || '').toLowerCase();
    if (!name.includes('cartvertising')) return null;
    const total = parseInt(item.storeCartCount) || 0;
    const pct = parseInt(item.cartPct) || 0;
    if (!total || !pct) return null;
    const showing = item.cartsShowingAd != null ? item.cartsShowingAd : Math.round(total * (pct / 100));
    return { total, pct, showing, isHeader: item.cartKind === 'header' };
  }

  async function exportQuotePdf() {
    if (cartItems.length === 0) return;

    const pdfDoc = await PDFDocument.create();
    const bold = await pdfDoc.embedFont(StandardFonts.HelveticaBold);
    const regular = await pdfDoc.embedFont(StandardFonts.Helvetica);
    const red = rgb(0.8, 0, 0);
    const white = rgb(1, 1, 1);
    const black = rgb(0, 0, 0);
    const gray = rgb(0.3, 0.3, 0.3);
    const green = rgb(0.18, 0.49, 0.2);
    const lightGray = rgb(0.95, 0.95, 0.95);
    const dateStr = new Date().toLocaleDateString('en-US', { year:'numeric', month:'long', day:'numeric' });
    const rep = $user?.name || $user?.first_name || localStorage.getItem('impro_rep_name') || 'Your IndoorMedia Rep';

    let page = pdfDoc.addPage([612, 792]);
    let y = 792;
    let pageNum = 1;

    function checkPage(needed) {
      if (y - needed < 60) {
        // Footer on current page
        page.drawText('IndoorMedia  |  indoormedia.com', { x: 612/2 - regular.widthOfTextAtSize('IndoorMedia  |  indoormedia.com', 9)/2, y: 30, size: 9, font: regular, color: gray });
        page = pdfDoc.addPage([612, 792]);
        y = 770;
        pageNum++;
      }
    }

    // Header bar
    page.drawRectangle({ x: 0, y: y - 80, width: 612, height: 80, color: red });
    page.drawText('QUOTE', { x: 30, y: y - 45, size: 30, font: bold, color: white });
    page.drawText('IndoorMedia', { x: 30, y: y - 65, size: 12, font: regular, color: white });
    page.drawText(dateStr, { x: 612 - bold.widthOfTextAtSize(dateStr, 10) - 30, y: y - 45, size: 10, font: bold, color: white });
    y -= 100;

    // Customer section
    if (businessName.trim()) {
      page.drawText('Prepared for: ' + businessName.trim(), { x: 30, y, size: 13, font: bold, color: black });
      y -= 20;
    }
    page.drawText('Prepared by: ' + rep, { x: 30, y, size: 11, font: regular, color: gray });
    y -= 30;

    // Line items
    page.drawText('Line Items', { x: 30, y, size: 14, font: bold, color: red });
    y -= 6;
    // Separator
    page.drawRectangle({ x: 30, y: y - 2, width: 552, height: 1, color: rgb(0.8, 0.8, 0.8) });
    y -= 14;

    let totalDaily = 0, totalMonthly = 0, totalAnnual = 0, totalPrice = 0;

    for (let i = 0; i < cartItems.length; i++) {
      const item = cartItems[i];
      const imp = getImpressions(item);
      const annualPrice = parseAnnualPrice(item);
      totalPrice += annualPrice;

      if (imp) {
        totalDaily += imp.daily;
        totalMonthly += imp.monthly;
        totalAnnual += imp.annual;
      }

      checkPage(90);

      // Item number + product
      page.drawText((i + 1) + '.', { x: 30, y, size: 11, font: bold, color: black });
      page.drawText((item.name || '').replace(/[^\x20-\x7E]/g, ''), { x: 46, y, size: 11, font: bold, color: black });
      if (item.plan) {
        const planText = ' -- ' + item.plan;
        const nameW = bold.widthOfTextAtSize((item.name || '').replace(/[^\x20-\x7E]/g, ''), 11);
        page.drawText(planText, { x: 46 + nameW, y, size: 10, font: regular, color: gray });
      }
      y -= 16;

      // Store info
      if (item.store) {
        page.drawText('Store: ' + item.store + (item.storeNum ? ' (#' + item.storeNum + ')' : ''), { x: 46, y, size: 10, font: regular, color: gray });
        y -= 14;
      }
      if (item.storeAddress) {
        page.drawText(item.storeAddress + (item.storeCycle ? '  |  Cycle ' + item.storeCycle : ''), { x: 46, y, size: 10, font: regular, color: gray });
        y -= 14;
      }

      // Impressions (skip for Cartvertising — shown as cart coverage instead)
      if (imp) {
        page.drawText('Impressions:  Daily ' + imp.daily.toLocaleString() + '  |  Monthly ' + imp.monthly.toLocaleString() + '  |  Annual ' + imp.annual.toLocaleString(), { x: 46, y, size: 10, font: regular, color: rgb(0.18, 0.49, 0.2) });
        y -= 14;
      }

      // Cartvertising coverage — how many carts will display the ad
      const cov = getCartCoverage(item);
      if (cov) {
        const verb = cov.isHeader ? 'header ad' : 'ad';
        const covText = cov.showing.toLocaleString() + ' of ' + cov.total.toLocaleString() +
          ' shopping carts will display your ' + verb + ' (' + cov.pct + '% of all carts)';
        page.drawText(covText, { x: 46, y, size: 10, font: bold, color: rgb(0.18, 0.49, 0.2) });
        y -= 14;
      }

      // Price
      if (item.price) {
        page.drawText('Price: ' + item.price, { x: 46, y, size: 10, font: bold, color: black });
        y -= 14;
      }

      y -= 8;
    }

    // Grand totals
    checkPage(100);
    page.drawRectangle({ x: 30, y: y - 2, width: 552, height: 1, color: rgb(0.8, 0.8, 0.8) });
    y -= 16;
    page.drawText('TOTALS', { x: 30, y, size: 13, font: bold, color: red });
    y -= 20;

    if (totalDaily > 0) {
      page.drawText('Total Daily Impressions:', { x: 40, y, size: 11, font: bold, color: black });
      page.drawText(totalDaily.toLocaleString(), { x: 250, y, size: 11, font: regular, color: black });
      y -= 16;
      page.drawText('Total Monthly Impressions:', { x: 40, y, size: 11, font: bold, color: black });
      page.drawText(totalMonthly.toLocaleString(), { x: 250, y, size: 11, font: regular, color: black });
      y -= 16;
      page.drawText('Total Annual Impressions:', { x: 40, y, size: 11, font: bold, color: black });
      page.drawText(totalAnnual.toLocaleString(), { x: 250, y, size: 11, font: regular, color: black });
      y -= 22;
    }

    const dailyInv = totalPrice / 365;
    const monthlyInv = totalPrice / 12;
    page.drawText('Daily Investment:', { x: 40, y, size: 11, font: bold, color: black });
    page.drawText('$' + dailyInv.toFixed(2), { x: 250, y, size: 11, font: regular, color: black });
    y -= 16;
    page.drawText('Monthly Investment:', { x: 40, y, size: 11, font: bold, color: black });
    page.drawText('$' + monthlyInv.toFixed(2), { x: 250, y, size: 11, font: regular, color: black });
    y -= 16;
    page.drawText('Annual Investment:', { x: 40, y, size: 11, font: bold, color: black });
    page.drawText('$' + totalPrice.toLocaleString(), { x: 250, y, size: 11, font: bold, color: red });
    y -= 30;

    // Product highlights
    const hasRT = cartItems.some(i => (i.name || '').toLowerCase().includes('register tape'));
    const hasCart = cartItems.some(i => (i.name || '').toLowerCase().includes('cartvertising'));
    const hasDigi = cartItems.some(i => {
      const n = (i.name || '').toLowerCase();
      return n.includes('digitalboost') || n.includes('digital boost') || n.includes('findlocal') || n.includes('reviewboost') || n.includes('loyaltyboost');
    });

    function drawHighlights(title, items) {
      checkPage(30 + items.length * 18);
      page.drawText(title, { x: 30, y, size: 13, font: bold, color: red });
      y -= 20;
      for (const txt of items) {
        page.drawRectangle({ x: 40, y: y + 2, width: 6, height: 6, color: green });
        page.drawText('  ' + txt, { x: 50, y, size: 11, font: regular, color: black });
        y -= 18;
      }
      y -= 8;
    }

    if (hasRT) {
      drawHighlights('Register Tape Highlights', [
        '100% Reach -- every customer gets a receipt with your ad',
        'Hyper-Local -- target shoppers at stores near your business',
        'Affordable -- fraction of the cost of direct mail or digital',
        'Trackable -- coupon codes measure real customer response',
      ]);
    }
    // Cartvertising "Front vs Directory" explainer diagram (vector, no percentages)
    function drawCartDiagram() {
      const boxW = 150, boxH = 92, gap = 70;
      const leftX = 30, rightX = leftX + boxW + gap;
      checkPage(boxH + 90);
      // Title
      page.drawText('Ad Placement: Front vs Directory', { x: 30, y, size: 13, font: bold, color: red });
      y -= 42;                   // clearance so the column headers don't collide with the title
      const topY = y;            // top edge of the two boxes
      const boxBottom = topY - boxH;
      // Column headers (red, centered over each box)
      const h1a = 'Front Side', h1b = '(faces oncoming shoppers)';
      const h2a = 'Directory Side', h2b = '(faces toward the shopper)';
      const ch = (txt, cx, size, fnt, col) => page.drawText(txt, { x: cx - fnt.widthOfTextAtSize(txt, size) / 2, y: topY + 14, size, font: fnt, color: col });
      // header line 1
      page.drawText(h1a, { x: leftX + boxW/2 - bold.widthOfTextAtSize(h1a, 9)/2, y: topY + 20, size: 9, font: bold, color: red });
      page.drawText(h1b, { x: leftX + boxW/2 - regular.widthOfTextAtSize(h1b, 7)/2, y: topY + 10, size: 7, font: regular, color: gray });
      page.drawText(h2a, { x: rightX + boxW/2 - bold.widthOfTextAtSize(h2a, 9)/2, y: topY + 20, size: 9, font: bold, color: red });
      page.drawText(h2b, { x: rightX + boxW/2 - regular.widthOfTextAtSize(h2b, 7)/2, y: topY + 10, size: 7, font: regular, color: gray });

      // ─ Front Side box (single white panel, black border) ─
      page.drawRectangle({ x: leftX, y: boxBottom, width: boxW, height: boxH, borderColor: black, borderWidth: 2.5, color: white });
      page.drawRectangle({ x: leftX + 4, y: boxBottom + 4, width: boxW - 8, height: boxH - 8, borderColor: rgb(0.75,0.75,0.75), borderWidth: 0.75 });
      page.drawText('Front Side', { x: leftX + boxW/2 - bold.widthOfTextAtSize('Front Side', 11)/2, y: topY - 20, size: 11, font: bold, color: black });
      page.drawText('This side points out', { x: leftX + boxW/2 - regular.widthOfTextAtSize('This side points out', 8)/2, y: boxBottom + 30, size: 8, font: regular, color: gray });
      page.drawText('the front of the cart', { x: leftX + boxW/2 - regular.widthOfTextAtSize('the front of the cart', 8)/2, y: boxBottom + 18, size: 8, font: regular, color: gray });

      // ─ OR arrow between boxes ─
      const arrY = boxBottom + boxH/2;
      page.drawText('OR', { x: leftX + boxW + gap/2 - bold.widthOfTextAtSize('OR', 11)/2, y: arrY - 4, size: 11, font: bold, color: red });
      page.drawLine({ start: { x: leftX + boxW + 6, y: arrY }, end: { x: leftX + boxW + gap/2 - 12, y: arrY }, thickness: 1, color: red });
      page.drawLine({ start: { x: leftX + boxW + gap/2 + 12, y: arrY }, end: { x: rightX - 6, y: arrY }, thickness: 1, color: red });
      // arrowhead into the right box
      page.drawLine({ start: { x: rightX - 6, y: arrY }, end: { x: rightX - 12, y: arrY + 4 }, thickness: 1, color: red });
      page.drawLine({ start: { x: rightX - 6, y: arrY }, end: { x: rightX - 12, y: arrY - 4 }, thickness: 1, color: red });

      // ─ Directory Side box (split: narrow left label + wider Store Directory) ─
      page.drawRectangle({ x: rightX, y: boxBottom, width: boxW, height: boxH, borderColor: black, borderWidth: 2.5, color: white });
      page.drawRectangle({ x: rightX + 4, y: boxBottom + 4, width: boxW - 8, height: boxH - 8, borderColor: rgb(0.75,0.75,0.75), borderWidth: 0.75 });
      const splitX = rightX + boxW * 0.42;
      page.drawLine({ start: { x: splitX, y: boxBottom + 6 }, end: { x: splitX, y: topY - 6 }, thickness: 0.75, color: rgb(0.7,0.7,0.7) });
      // left (narrow) label
      page.drawText('Directory', { x: rightX + (splitX - rightX)/2 - bold.widthOfTextAtSize('Directory', 8)/2, y: topY - 20, size: 8, font: bold, color: black });
      page.drawText('Side', { x: rightX + (splitX - rightX)/2 - bold.widthOfTextAtSize('Side', 8)/2, y: topY - 30, size: 8, font: bold, color: black });
      // right (wide) Store Directory box, split with a horizontal line near the top
      const sdTop = topY - 12;
      page.drawLine({ start: { x: splitX + 6, y: sdTop - 18 }, end: { x: rightX + boxW - 8, y: sdTop - 18 }, thickness: 0.6, color: rgb(0.8,0.8,0.8) });
      page.drawText('Store', { x: (splitX + rightX + boxW)/2 - regular.widthOfTextAtSize('Store', 8)/2, y: boxBottom + 42, size: 8, font: regular, color: rgb(0.6,0.6,0.6) });
      page.drawText('Directory', { x: (splitX + rightX + boxW)/2 - regular.widthOfTextAtSize('Directory', 8)/2, y: boxBottom + 32, size: 8, font: regular, color: rgb(0.6,0.6,0.6) });
      // caption under the right box
      page.drawText('Rides next to the store directory, facing the shopper', { x: rightX + boxW/2 - regular.widthOfTextAtSize('Rides next to the store directory, facing the shopper', 7)/2, y: boxBottom - 12, size: 7, font: regular, color: gray });

      y = boxBottom - 30;
    }

    // Header ad explainer — ad rides in the top-right corner (and footer at 100%)
    function drawHeaderDiagram() {
      const boxW = 150, boxH = 92;
      const leftX = 30, rightX = leftX + boxW + 70;
      checkPage(boxH + 80);
      page.drawText('Header Ads', { x: 30, y, size: 13, font: bold, color: red });
      y -= 40;
      const topY = y, boxBottom = topY - boxH;
      // headers
      page.drawText('Header 50%', { x: leftX + boxW/2 - bold.widthOfTextAtSize('Header 50%', 9)/2, y: topY + 20, size: 9, font: bold, color: red });
      page.drawText('(every other cart)', { x: leftX + boxW/2 - regular.widthOfTextAtSize('(every other cart)', 7)/2, y: topY + 10, size: 7, font: regular, color: gray });
      page.drawText('Header 100%', { x: rightX + boxW/2 - bold.widthOfTextAtSize('Header 100%', 9)/2, y: topY + 20, size: 9, font: bold, color: red });
      page.drawText('(every cart — header + footer)', { x: rightX + boxW/2 - regular.widthOfTextAtSize('(every cart — header + footer)', 7)/2, y: topY + 10, size: 7, font: regular, color: gray });

      // 50% panel: header block top-right
      page.drawRectangle({ x: leftX, y: boxBottom, width: boxW, height: boxH, borderColor: black, borderWidth: 2.5, color: white });
      page.drawRectangle({ x: leftX + boxW - 62, y: topY - 26, width: 54, height: 16, borderColor: black, borderWidth: 1, color: rgb(0.93,0.93,0.93) });
      page.drawText('Header', { x: leftX + boxW - 60, y: topY - 22, size: 8, font: bold, color: black });
      page.drawText('Store', { x: leftX + boxW - 58, y: boxBottom + 40, size: 7, font: regular, color: rgb(0.65,0.65,0.65) });
      page.drawText('Directory', { x: leftX + boxW - 64, y: boxBottom + 31, size: 7, font: regular, color: rgb(0.65,0.65,0.65) });
      page.drawText('Top-right of every other cart', { x: leftX + boxW/2 - regular.widthOfTextAtSize('Top-right of every other cart', 7)/2, y: boxBottom - 12, size: 7, font: regular, color: gray });

      // 100% panel: header top-right + footer bottom
      page.drawRectangle({ x: rightX, y: boxBottom, width: boxW, height: boxH, borderColor: black, borderWidth: 2.5, color: white });
      page.drawRectangle({ x: rightX + boxW - 62, y: topY - 26, width: 54, height: 16, borderColor: black, borderWidth: 1, color: rgb(0.93,0.93,0.93) });
      page.drawText('Header', { x: rightX + boxW - 60, y: topY - 22, size: 8, font: bold, color: black });
      page.drawRectangle({ x: rightX + boxW - 62, y: boxBottom + 8, width: 54, height: 16, borderColor: black, borderWidth: 1, color: rgb(0.93,0.93,0.93) });
      page.drawText('Footer', { x: rightX + boxW - 60, y: boxBottom + 12, size: 8, font: bold, color: black });
      page.drawText('Header + footer on every cart', { x: rightX + boxW/2 - regular.widthOfTextAtSize('Header + footer on every cart', 7)/2, y: boxBottom - 12, size: 7, font: regular, color: gray });

      y = boxBottom - 30;
    }

    const hasHeaderAd = cartItems.some(i => (i.cartKind === 'header') || /header/i.test(i.plan || ''));

    if (hasCart) {
      drawHighlights('Cartvertising Highlights', [
        'Eye-Level -- ads mounted right where shoppers look',
        '40+ Minutes -- your ad stays the entire shopping trip',
        'Full Color -- high-quality printing for maximum impact',
        'Massive Reach -- thousands of shoppers per cart',
      ]);
      drawCartDiagram();
      if (hasHeaderAd) drawHeaderDiagram();
    }
    if (hasDigi) {
      drawHighlights('Digital Product Highlights', [
        'Geofencing -- target customers near your business',
        'Digital Ads -- banner ads on mobile apps and websites',
        'Monthly Reports -- track performance and ROI',
      ]);
    }

    // Footer
    page.drawText('IndoorMedia  |  indoormedia.com', { x: 612/2 - regular.widthOfTextAtSize('IndoorMedia  |  indoormedia.com', 9)/2, y: 30, size: 9, font: regular, color: gray });

    // Save and share/download
    const bytes = await pdfDoc.save();
    const filename = 'IndoorMedia_Quote_' + new Date().toISOString().split('T')[0] + '.pdf';

    if (navigator.share && /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)) {
      try {
        const file = new File([bytes], filename, { type: 'application/pdf' });
        await navigator.share({ files: [file], title: filename });
        return;
      } catch (e) { /* fallback below */ }
    }

    const blob = new Blob([bytes], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
  }
</script>

<div class="quote-container">
  <h2>Build Quote</h2>
  <p class="subtitle">Add products to build a customer quote</p>

  <button class="add-btn" on:click={startAdd}>+ Add Product</button>

  {#if showAddProduct}
    <div class="add-modal">
      {#if addStep === 'type'}
        <h3>Select Product</h3>
        <div class="type-list">
          {#each PRODUCT_TYPES as type}
            <button class="type-btn" on:click={() => selectType(type)}>
              <span class="type-emoji">{type.emoji}</span>
              <span class="type-name">{type.name}</span>
              {#if type.price}<span class="type-price">{type.price}</span>{/if}
            </button>
          {/each}
        </div>
        <button class="cancel-btn" on:click={() => showAddProduct = false}>Cancel</button>
      {/if}

      {#if addStep === 'store'}
        <h3>Select Store</h3>
        {#if newItem.hasMap}
          <button class="map-btn" on:click={useMapArea}>🗺️ Choose Area on Map Instead</button>
        {/if}
        <StoreSearchInput
          bind:this={storeSearchInput}
          stores={allStores}
          placeholder="Search store by name, city, address, zip, or number..."
          maxResults={15}
          showGeo={true}
          on:select={e => selectStore(e.detail)}
          on:results={onCartStoreResults}
        />
        <div class="store-list">
          {#each filteredStores as store}
            <button class="store-btn" on:click={() => selectStore(store)}>
              <div class="store-top">
                <span class="store-name">{store.GroceryChain} - {store.City}, {store.State}</span>
                <span class="store-cycle">Cycle {store.Cycle || '?'}</span>
              </div>
              <span class="store-addr">{store.Address || ''}</span>
              <div class="store-bottom">
                <span class="store-num">{store.StoreName}</span>
                <span class="store-price">Single: ${store.SingleAd?.toLocaleString()} | Double: ${store.DoubleAd?.toLocaleString()}</span>
              </div>
              {#if store.Cycle}
                <span class="store-launch">Next launch: {getNextLaunch(store.Cycle)}</span>
              {/if}
              {#if store._dist !== undefined}
                <span class="store-distance">📍 {store._dist.toFixed(1)} mi</span>
              {/if}
            </button>
          {/each}
        </div>
        <button class="cancel-btn" on:click={() => { addStep = 'type'; storeSearch = ''; if (storeSearchInput) storeSearchInput.clear(); }}>Back</button>
      {/if}

      {#if addStep === 'plan'}
        <h3>Payment Plan</h3>
        <p class="plan-store">{newItem.storeName} ({newItem.storeNum})</p>
        
        {#if newItem.store?.DoubleAd}
          <div class="ad-type-toggle">
            <button class="ad-toggle-btn" class:active={cartAdType === 'single'} on:click={() => cartAdType = 'single'}>
              Single Ad — ${newItem.store.SingleAd?.toLocaleString()}
            </button>
            <button class="ad-toggle-btn" class:active={cartAdType === 'double'} on:click={() => cartAdType = 'double'}>
              Double Ad — ${newItem.store.DoubleAd?.toLocaleString()}
            </button>
          </div>
        {/if}

        {@const productType = PRODUCT_TYPES.find(t => t.id === newItem.type)}
        {@const adSel = productType?.adSize || cartAdType}
        {@const basePrice = adSel === 'double' && newItem.store?.DoubleAd ? newItem.store.DoubleAd : (newItem.store?.SingleAd || 0)}
        <div class="plan-list">
          {#each PAYMENT_PLANS[newItem.type] || [] as plan}
            <button class="plan-btn" on:click={() => selectPlan(plan)}>
              <span class="plan-name">{plan.name}</span>
              <span class="plan-price">{plan.calc(basePrice)}</span>
            </button>
          {/each}
        </div>
        <button class="cancel-btn" on:click={() => { addStep = 'store'; cartAdType = 'single'; }}>Back</button>
      {/if}

      {#if addStep === 'confirm'}
        <h3>Confirm & Customize Price</h3>
        <div class="confirm-box">
          <p class="confirm-label">Product</p>
          <p class="confirm-value">{newItem.typeName}</p>
          <p class="confirm-label">Store</p>
          <p class="confirm-value">{newItem.storeName}</p>
          <p class="confirm-label">Plan</p>
          <p class="confirm-value">{newItem.plan}</p>
          <p class="confirm-label">Price</p>
          <input type="text" bind:value={newItem.priceText} class="price-input" />
        </div>
        <button class="add-confirm-btn" on:click={confirmPlan}>Add to Quote</button>
        <button class="cancel-btn" on:click={() => { addStep = 'plan'; }}>Back</button>
      {/if}

      {#if addStep === 'pins'}
        <h3>DigitalBoost — How Many Pins?</h3>
        <div class="pins-grid">
          {#each [1,2,3,4,5] as n}
            <button class="pin-btn" class:selected={newItem.pins === n} on:click={() => { newItem.pins = n; }}>
              {n} Pin{n > 1 ? 's' : ''}
              <span class="pin-price">${((n * 3600) + 395).toLocaleString()}</span>
            </button>
          {/each}
        </div>
        <button class="add-confirm-btn" on:click={addItem}>Add to Quote</button>
        <button class="cancel-btn" on:click={() => { addStep = 'type'; }}>Back</button>
      {/if}
    </div>
  {/if}

  {#if cartItems.length > 0}
    <div class="quote-items">
      {#each cartItems as item, i}
        <div 
          class="quote-item"
          class:dragging={dragIndex === i}
          class:drag-over={dragOverIndex === i && dragIndex !== i}
          draggable="true"
          on:dragstart={(e) => handleDragStart(e, i)}
          on:dragover={(e) => handleDragOver(e, i)}
          on:dragleave={handleDragLeave}
          on:drop={(e) => handleDrop(e, i)}
          on:dragend={handleDragEnd}
          on:touchstart={(e) => handleTouchStart(e, i)}
          on:touchmove={(e) => handleTouchMove(e, i)}
          on:touchend={handleTouchEnd}
        >
          <div class="reorder-controls">
            <button class="reorder-btn" on:click={() => moveItem(i, -1)} disabled={i === 0}>▲</button>
            <span class="drag-handle">☰</span>
            <button class="reorder-btn" on:click={() => moveItem(i, 1)} disabled={i === cartItems.length - 1}>▼</button>
          </div>
          <div class="item-info">
            <h4>{item.emoji || ''} {item.name}</h4>
            {#if item.promoMode}<p class="item-promo-badge">🎁 Free quarter included · 🏆 Summer Contest</p>{/if}
            {#if item.store}<p class="item-store">{item.store} ({item.storeNum}){#if item.storeCycle} — Cycle {item.storeCycle}{/if}</p>{/if}
            {#if item.storeAddress}<p class="item-addr">{item.storeAddress}</p>{/if}
            {#if item.storeCycle}<p class="item-launch">Next launch: {getNextLaunch(item.storeCycle)}</p>{/if}
            {#if item.plan}<p class="item-plan">{item.plan}</p>{/if}
            {#if getCartCoverage(item)}
              {@const cov = getCartCoverage(item)}
              <p class="item-cart-coverage">🛒 {cov.showing.toLocaleString()} of {cov.total.toLocaleString()} carts show your {cov.isHeader ? 'header ad' : 'ad'} ({cov.pct}% of all carts)</p>
            {:else if (item.name || '').toLowerCase().includes('cartvertising') && !item.storeCartCount}
              <p class="item-cart-coverage item-cart-missing">🛒 Add this store's cart count (re-add from the store card) to show cart coverage on the quote</p>
            {/if}
            <div class="price-edit">
              <label>Price</label>
              <input type="text" value={item.price} on:change={(e) => updateItemPrice(i, e.target.value)} class="price-field" />
            </div>
          </div>
          <button class="remove-btn" on:click={() => removeItem(i)}>✕</button>
        </div>
      {/each}
    </div>

    <!-- Summer Contest Points & Free Quarters -->
    {@const promoItems = cartItems.filter(i => i.promoMode)}
    {@const hasDigitalBoost = cartItems.some(i => (i.name || '').toLowerCase().includes('digitalboost'))}
    {@const pifPromoItems = promoItems.filter(i => i.pifPlan)}
    {@const contestPoints = promoItems.length + (hasDigitalBoost && promoItems.length > 0 ? 1 : 0) + pifPromoItems.length}
    {#if promoItems.length > 0}
      <div class="contest-summary">
        <div class="contest-summary-header">🏆 Summer Contest Tracker</div>
        <div class="contest-points-row">
          <span>Full Rate Cards</span><span>{promoItems.length} pt{promoItems.length !== 1 ? 's' : ''}</span>
        </div>
        {#if hasDigitalBoost}
          <div class="contest-points-row"><span>+ DigitalBoost</span><span>1 pt</span></div>
        {/if}
        {#if pifPromoItems.length > 0}
          <div class="contest-points-row"><span>PIF Contracts</span><span>{pifPromoItems.length} pt{pifPromoItems.length !== 1 ? 's' : ''}</span></div>
        {/if}
        <div class="contest-points-total">Total Points: {contestPoints}</div>
        {#if promoItems.length > 1}
          <div class="free-quarters-note">🎁 {promoItems.length} free quarters earned ({promoItems.length} stores purchased)</div>
        {:else}
          <div class="free-quarters-note">🎁 1 free quarter earned</div>
        {/if}
      </div>
    {/if}

    {#if cartItems.some(i => (i.name || '').toLowerCase().includes('cartvertising'))}
      <div class="cart-diagram">
        <div class="cd-title">🛒 Ad Placement: Front vs Directory</div>
        <div class="cd-row">
          <div class="cd-col">
            <div class="cd-head">Front Side</div>
            <div class="cd-sub">faces oncoming shoppers</div>
            <div class="cd-panel">
              <span class="cd-panel-label">Front Side</span>
              <span class="cd-panel-note">points out the front of the cart</span>
            </div>
          </div>
          <div class="cd-or">OR</div>
          <div class="cd-col">
            <div class="cd-head">Directory Side</div>
            <div class="cd-sub">faces toward the shopper</div>
            <div class="cd-panel cd-panel-split">
              <div class="cd-split-left">Directory<br>Side</div>
              <div class="cd-split-right">
                <div class="cd-split-top"></div>
                <div class="cd-split-bottom">Store<br>Directory</div>
              </div>
            </div>
            <div class="cd-caption">rides by the store directory, facing the shopper</div>
          </div>
        </div>
        {#if cartItems.some(i => (i.cartKind === 'header') || /header/i.test(i.plan || ''))}
          <div class="cd-title cd-title-header">🧾 Header Ads</div>
          <div class="cd-row">
            <div class="cd-col">
              <div class="cd-head">Header 50%</div>
              <div class="cd-sub">every other cart</div>
              <div class="cd-panel cd-panel-header">
                <div class="cd-header-tag">Header</div>
                <div class="cd-header-dir">Store<br>Directory</div>
              </div>
              <div class="cd-caption">top-right corner of every other cart</div>
            </div>
            <div class="cd-col">
              <div class="cd-head">Header 100%</div>
              <div class="cd-sub">every cart — header + footer</div>
              <div class="cd-panel cd-panel-header">
                <div class="cd-header-tag">Header</div>
                <div class="cd-footer-tag">Footer</div>
              </div>
              <div class="cd-caption">header + footer on every cart</div>
            </div>
          </div>
        {/if}
      </div>
    {/if}

    <div class="quote-footer">
      <div class="business-name-row">
        <input type="text" class="business-name-input" placeholder="Business name (for quote)" bind:value={businessName} />
      </div>
      <div class="footer-actions">
        <button class="export-btn" on:click={exportQuotePdf}>📄 Download Quote PDF</button>
        <button class="clear-btn" on:click={clearCart}>🗑️ Clear</button>
      </div>
    </div>
  {:else if !showAddProduct}
    <div class="empty">
      <p>No products in quote yet</p>
      <p class="hint">Tap "+ Add Product" to start building</p>
    </div>
  {/if}
</div>

<style>
  .quote-container { padding: 20px 20px 140px; max-width: 100%; margin: 0 auto; }

  /* Cartvertising Front vs Directory explainer */
  .cart-diagram {
    margin: 16px 0;
    padding: 14px 12px;
    background: var(--bg-secondary, #f7f7f7);
    border: 1px solid var(--border-color, #e0e0e0);
    border-radius: 12px;
  }
  .cd-title { font-size: 14px; font-weight: 800; color: #CC0000; text-align: center; margin-bottom: 12px; }
  .cd-row { display: flex; align-items: center; justify-content: center; gap: 10px; }
  .cd-col { flex: 1; max-width: 160px; text-align: center; }
  .cd-head { font-size: 12px; font-weight: 800; color: #CC0000; line-height: 1.15; }
  .cd-sub { font-size: 9px; color: var(--text-secondary, #777); margin-bottom: 6px; }
  .cd-panel {
    position: relative;
    height: 78px;
    background: #fff;
    border: 3px solid #111;
    border-radius: 10px;
    box-shadow: inset 0 0 0 1px #ccc;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 4px;
  }
  .cd-panel-label { font-size: 12px; font-weight: 800; color: #111; }
  .cd-panel-note { font-size: 8px; color: #888; margin-top: 4px; line-height: 1.2; }
  .cd-panel-split { flex-direction: row; padding: 0; overflow: hidden; }
  .cd-split-left {
    width: 40%;
    display: flex; align-items: center; justify-content: center;
    font-size: 10px; font-weight: 800; color: #111;
    border-right: 1px solid #bbb;
    line-height: 1.1;
  }
  .cd-split-right { width: 60%; display: flex; flex-direction: column; }
  .cd-split-top { height: 26%; border-bottom: 1px solid #ddd; }
  .cd-split-bottom {
    flex: 1;
    display: flex; align-items: center; justify-content: center;
    font-size: 9px; color: #aaa; text-align: center; line-height: 1.15;
  }
  .cd-caption { font-size: 8px; color: var(--text-secondary, #777); margin-top: 5px; line-height: 1.2; }
  .cd-or {
    font-size: 13px; font-weight: 900; color: #fff;
    background: #CC0000; border-radius: 4px;
    padding: 3px 7px; flex-shrink: 0;
  }
  .cd-title-header { margin-top: 16px; }
  .cd-panel-header { position: relative; }
  .cd-header-tag {
    position: absolute; top: 6px; right: 6px;
    background: #eee; border: 1px solid #111;
    font-size: 8px; font-weight: 800; color: #111;
    padding: 2px 6px; border-radius: 2px;
  }
  .cd-footer-tag {
    position: absolute; bottom: 6px; right: 6px;
    background: #eee; border: 1px solid #111;
    font-size: 8px; font-weight: 800; color: #111;
    padding: 2px 6px; border-radius: 2px;
  }
  .cd-header-dir {
    position: absolute; bottom: 8px; left: 8px;
    font-size: 8px; color: #aaa; line-height: 1.1; text-align: left;
  }
  .item-cart-coverage {
    font-size: 12px; font-weight: 700; color: #0a7d2c;
    margin: 2px 0 4px;
  }
  .item-cart-missing { color: #b58900; font-weight: 600; }
  h2 { margin: 0 0 6px; font-size: 22px; font-weight: 700; color: var(--text-primary); }
  h3 { margin: 0 0 12px; font-size: 18px; font-weight: 700; color: #333; }
  .subtitle { margin: 0 0 16px; color: var(--text-secondary); font-size: 14px; }

  .add-btn { width: 100%; padding: 14px; background: #CC0000; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: 700; cursor: pointer; margin-bottom: 16px; }
  .add-btn:hover { background: #990000; }

  .add-modal { background: #f5f5f5; border-radius: 12px; padding: 16px; margin-bottom: 16px; }

  .type-list { display: flex; flex-direction: column; gap: 8px; max-height: 400px; overflow-y: auto; }
  .type-btn { display: flex; align-items: center; gap: 10px; padding: 12px; background: white; border: 1px solid #e0e0e0; border-radius: 8px; cursor: pointer; text-align: left; }
  .type-btn:hover { border-color: #CC0000; }
  .type-emoji { font-size: 20px; }
  .type-name { flex: 1; font-weight: 600; font-size: 13px; color: #333; }
  .type-price { font-size: 12px; color: #CC0000; font-weight: 600; }

  .search-input { width: 100%; padding: 12px; border: 1px solid #e0e0e0; border-radius: 8px; font-size: 14px; margin-bottom: 12px; box-sizing: border-box; }

  .store-list { display: flex; flex-direction: column; gap: 8px; max-height: 300px; overflow-y: auto; }
  .store-btn { display: flex; flex-direction: column; padding: 10px; background: white; border: 1px solid #e0e0e0; border-radius: 8px; cursor: pointer; text-align: left; }
  .store-btn:hover { border-color: #CC0000; }
  .store-top { display: flex; justify-content: space-between; align-items: center; }
  .store-name { font-weight: 600; font-size: 14px; color: #333; }
  .store-cycle { font-size: 11px; font-weight: 600; color: #CC0000; background: #fff5f5; padding: 2px 8px; border-radius: 4px; }
  .store-addr { font-size: 12px; color: #888; margin-top: 2px; }
  .store-bottom { display: flex; justify-content: space-between; align-items: center; margin-top: 4px; }
  .store-num { font-size: 12px; color: #666; }
  .store-price { font-size: 11px; color: #CC0000; font-weight: 600; }

  .map-btn { width: 100%; padding: 14px; background: #1565c0; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; margin-bottom: 12px; }
  .map-btn:hover { background: #0d47a1; }

  .item-addr { margin: 0 0 2px; font-size: 11px; color: #999; }
  .item-launch { margin: 0 0 2px; font-size: 11px; color: #2e7d32; font-weight: 600; }
  .store-launch { font-size: 11px; color: #2e7d32; font-weight: 600; margin-top: 4px; }

  .plan-store { margin: 0 0 12px; font-size: 13px; color: #666; }
  .plan-list { display: flex; flex-direction: column; gap: 8px; }
  .ad-type-toggle { display: flex; gap: 8px; margin-bottom: 12px; }
  .ad-toggle-btn { flex: 1; padding: 10px; border: 2px solid #ddd; border-radius: 8px; background: white; font-size: 13px; font-weight: 600; color: #666; cursor: pointer; transition: all 0.2s; }
  .ad-toggle-btn.active { background: #CC0000; color: white; border-color: #CC0000; }
  .ad-toggle-btn:hover:not(.active) { border-color: #CC0000; color: #CC0000; }
  .plan-btn { display: flex; flex-direction: column; padding: 12px; background: white; border: 1px solid #e0e0e0; border-radius: 8px; cursor: pointer; text-align: left; }
  .plan-btn:hover { border-color: #CC0000; }
  .plan-name { font-weight: 600; font-size: 14px; color: #333; }
  .plan-price { font-size: 13px; color: #CC0000; margin-top: 4px; }

  .pins-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px; }
  .pin-btn { padding: 16px; background: white; border: 2px solid #e0e0e0; border-radius: 8px; cursor: pointer; text-align: center; font-weight: 700; font-size: 15px; color: #333; }
  .pin-btn.selected { border-color: #CC0000; background: #fff5f5; }
  .pin-price { display: block; font-size: 12px; color: #CC0000; margin-top: 4px; }

  .add-confirm-btn { width: 100%; padding: 14px; background: #CC0000; color: white; border: none; border-radius: 8px; font-size: 15px; font-weight: 700; cursor: pointer; margin-bottom: 8px; }

  .cancel-btn { width: 100%; padding: 10px; background: none; border: 1px solid #e0e0e0; border-radius: 8px; color: #666; font-size: 13px; cursor: pointer; margin-top: 8px; }

  .quote-items { display: flex; flex-direction: column; gap: 12px; margin-bottom: 16px; }
  .quote-item { display: flex; justify-content: space-between; align-items: flex-start; background: var(--card-bg, #ffffff); border: 1px solid #e8e8e8; border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); cursor: grab; transition: box-shadow 0.2s; }
  .quote-item:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
  :global([data-theme='dark']) .quote-item { background: #1e1e1e; border-color: #333; }
  .quote-item:active { cursor: grabbing; }
  .quote-item.dragging { opacity: 0.4; border-color: #CC0000; }
  .quote-item.drag-over { border-color: #CC0000; border-style: dashed; background: #fff5f5; }

  .reorder-controls { display: flex; flex-direction: column; align-items: center; gap: 2px; margin-right: 10px; min-width: 28px; }
  .reorder-btn { width: 28px; height: 22px; border: 1px solid #ddd; border-radius: 4px; background: #f9f9f9; cursor: pointer; font-size: 10px; display: flex; align-items: center; justify-content: center; padding: 0; }
  .reorder-btn:hover:not(:disabled) { background: #CC0000; color: white; border-color: #CC0000; }
  .reorder-btn:disabled { opacity: 0.3; cursor: not-allowed; }
  .drag-handle { font-size: 16px; color: #999; cursor: grab; user-select: none; }
  .item-info { flex: 1; }
  .quote-item h4 { margin: 0 0 4px; font-size: 15px; font-weight: 600; color: var(--text-primary, #333); }
  .item-store { margin: 0 0 2px; font-size: 12px; color: #666; }
  .item-plan { margin: 0 0 2px; font-size: 12px; color: #888; }
  .price-edit { margin-top: 8px; }
  .price-edit label { display: block; font-size: 11px; font-weight: 700; color: #666; margin-bottom: 4px; }
  .price-field { width: 100%; padding: 8px; border: 1px solid #CC0000; border-radius: 6px; font-size: 14px; font-weight: 700; color: #CC0000; box-sizing: border-box; }
  .price-field:focus { outline: none; border-color: #990000; }

  .confirm-box { background: white; border-radius: 8px; padding: 16px; margin-bottom: 16px; border: 1px solid #e0e0e0; }
  .confirm-label { font-size: 11px; font-weight: 700; color: #888; text-transform: uppercase; margin: 12px 0 4px; }
  .confirm-value { margin: 0; font-size: 14px; color: #333; font-weight: 600; }
  .price-input { width: 100%; padding: 10px; border: 1px solid #CC0000; border-radius: 6px; font-size: 16px; font-weight: 700; color: #CC0000; box-sizing: border-box; }

  .remove-btn { background: none; border: none; color: #ccc; font-size: 20px; cursor: pointer; }
  .remove-btn:hover { color: #CC0000; }

  .quote-footer { padding: 16px; background: #f5f5f5; border-radius: 12px; }
  .footer-actions { display: flex; gap: 8px; }
  .business-name-row { margin-bottom: 10px; }
  .business-name-input { width: 100%; padding: 10px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; box-sizing: border-box; }
  .business-name-input::placeholder { color: #999; }
  .export-btn { flex: 1; padding: 12px; background: #CC0000; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; }
  .export-btn:hover { background: #990000; }
  .clear-btn { padding: 12px; background: white; border: 1px solid #e0e0e0; border-radius: 8px; color: #666; font-size: 14px; cursor: pointer; }

  .empty { text-align: center; padding: 40px 20px; color: #999; }
  .hint { font-size: 13px; color: #bbb; }

  /* Promo & Contest */
  .item-promo-badge { margin: 0 0 4px; font-size: 11px; font-weight: 700; color: #2e7d32; background: #e8f5e9; padding: 2px 8px; border-radius: 4px; display: inline-block; }
  :global([data-theme='dark']) .item-promo-badge { background: #1b3a1b; color: #66bb6a; }
  .contest-summary { background: linear-gradient(135deg, #fff8e1, #fff3e0); border: 1px solid #ffcc02; border-radius: 12px; padding: 14px; margin-bottom: 12px; }
  :global([data-theme='dark']) .contest-summary { background: linear-gradient(135deg, #3e3200, #3e2200); border-color: #665500; }
  .contest-summary-header { font-size: 15px; font-weight: 800; color: #e65100; margin-bottom: 8px; }
  .contest-points-row { display: flex; justify-content: space-between; font-size: 13px; color: #555; padding: 2px 0; }
  :global([data-theme='dark']) .contest-points-row { color: #ccc; }
  .contest-points-total { font-size: 16px; font-weight: 800; color: #cc0000; margin-top: 6px; padding-top: 6px; border-top: 1px solid #ffcc02; }
  .free-quarters-note { font-size: 12px; color: #2e7d32; font-weight: 600; margin-top: 6px; }
</style>
