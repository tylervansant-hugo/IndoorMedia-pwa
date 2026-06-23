<script>
  import { onMount, onDestroy } from 'svelte';
  import { user, padAmount, digitalPadAmount } from '../lib/stores.js';
  import MeetingPrep from './MeetingPrep.svelte';
  import { PDFDocument, rgb, StandardFonts } from 'pdf-lib';

  let view = 'menu'; 

  function _handleEdgeBack() { if (view !== 'menu') view = 'menu'; }
  onMount(() => { document.addEventListener('edge-swipe-back', _handleEdgeBack); });
  onDestroy(() => { document.removeEventListener('edge-swipe-back', _handleEdgeBack); });

  const VIDEO_LINKS = {
    'register-tape': {
      presentation: 'https://docs.google.com/presentation/d/1Xs60nX3i6MJkC81GgnK-50jBrkWVPu06xRpmv8z4PIc/edit?usp=sharing',
      explainer: 'https://youtu.be/_gdlyEszHfY?si=0_kHou89WrMhvNY_'
    },
    'cartvertising': {
      presentation: 'https://docs.google.com/presentation/d/1xwIF4CaTp07AKunGaJysCSIGqN7VCdbL4fgOH3XEpl4/edit?usp=sharing',
      explainer: 'https://www.youtube.com/watch?v=PduxHWy8sMc'
    },
    'digitalboost': {
      presentation: 'https://www.youtube.com/watch?v=PduxHWy8sMc',
      explainer: 'https://drive.google.com/file/d/1_QyAlgZRy1bKJSKC1058260d0jPccVTM/view?usp=share_link',
      connectionHub: 'https://drive.google.com/file/d/199IkMptOlSYviHScKNKUlqELQOhWFxnB/view?usp=sharing'
    },
    'findlocal': {
      explainer: 'https://youtu.be/5CvlhJHssMs?si=WSmoTeh6adRlc-YW'
    },
    'reviewboost': {
      explainer: 'https://youtu.be/PBpbUiIoYcM?si=XEGeu1hmbI-zAf7j'
    },
    'loyaltyboost': {
      explainer: 'https://youtu.be/gthLw2eQF1Y?si=9ggkdGIpcqlDHKaP'
    }
  };

  const products = [
    { id: 'register-tape', name: 'Register Tape', icon: '🧾',
      desc: 'Ads printed on grocery store register tape -- reaches every customer at checkout',
      features: ['Prints on every receipt', 'Targeted by store location', 'Coupon-style offers', '3-month cycles (A/B/C)'] },
    { id: 'cartvertising', name: 'Cartvertising', icon: '🛒',
      desc: 'Full-color ads displayed on shopping carts -- seen throughout the entire shopping trip',
      features: ['Eye-level visibility', 'Full-color printing', 'High impression count', 'Cart-mounted displays'] },
    { id: 'digital', name: 'Digital', icon: '📱',
      desc: 'Digital marketing solutions for local businesses',
      features: ['DigitalBoost -- Geofence Ads', 'FindLocal -- Directory Listings', 'ReviewBoost -- Reputation', 'LoyaltyBoost -- Retention'] }
  ];

  // Register Tape tiers
  const tapeTiers = {
    coop: { name: 'Manager Approved Co-Op', emoji: '🎯', desc: 'Pre-approved by store management',
      pricing: { 'Monthly': 'Base + $125', '3-Month': 'Base x 0.90 + $125 (10% off)', '6-Month': 'Base x 0.925 + $125 (7.5% off)', 'Paid-in-Full': 'Base x 0.85 + $125 (15% off)' } },
    exclusive: { name: 'Exclusive Category', emoji: '🏆', desc: 'Sole advertising category protection',
      pricing: { 'Monthly': 'Base + $125', '3-Month': 'Base + $125', '6-Month': 'Base + $125', 'Paid-in-Full': 'Base x 0.95 (5% off, no production)' } },
    contractor: { name: 'Contractors', emoji: '🔧', desc: 'Special contractor pricing',
      pricing: { '3-Month': 'Base + $125', 'Paid-in-Full': 'Base x 0.95 (5% off, no production)' } }
  };

  // Cartvertising packages
  const cartPackages = [
    { name: '20% Front OR Directory', price: '$2,995' },
    { name: '40% (20% Front + 20% Directory)', price: '$4,795' },
    { name: '60% (40% Front + 20% Directory)', price: '$5,995' },
    { name: '80% (40% Front + 40% Directory)', price: '$7,395' },
    { name: '100% (60% Front + 40% Directory)', price: '$8,795' },
    { name: '200% (100% Both Sides)', price: '$12,995' },
    { name: 'Header 50% (Every Other Cart)', price: '$2,995' },
    { name: 'Header 100% (Every Cart)', price: '$4,795' },
  ];

  // Digital products
  const digitalProducts = {
    digitalboost: { name: 'DigitalBoost', emoji: '🚀', desc: 'Geofence pin delivering digital banner ad impressions',
      details: [
        { label: 'Standalone', value: '240,000 impressions (20K/mo x 12)' },
        { label: 'Bundled w/ Tape or Cart', value: '360,000 impressions (30K/mo x 12)' },
        { label: 'Standard Pricing', value: '$3,600/pin + $395 production (up to 5 pins)' },
        { label: 'Co-Op Pricing', value: '$2,400/pin + $395 production (up to 5 pins)' },
      ],
      examples: [
        { pins: 1, standard: '$3,995', coop: '$2,795' },
        { pins: 2, standard: '$7,595', coop: '$5,195' },
        { pins: 3, standard: '$11,195', coop: '$7,595' },
        { pins: 5, standard: '$18,395', coop: '$12,395' },
      ]
    },
    findlocal: { name: 'FindLocal', emoji: '📍', desc: 'Local SEO & listings across 50+ directories',
      price: '$695/location', note: '+$195 if Google profile assistance needed',
      analysisUrl: 'https://www.indoormedia.com/local-listing-management/',
      features: ['50+ business listing submissions', 'NAP optimization', 'Hours, photos, categories management', 'Monthly progress reports', 'Google Business Profile sync'] },
    reviewboost: { name: 'ReviewBoost', emoji: '⭐', desc: 'Automated review request campaign via Email & SMS',
      price: '$695 (4-month campaign)', note: '+$495 per additional 4-month campaign',
      features: ['ReviewKit included', 'Automated 4-month campaign', 'Email & SMS review requests', 'Up to 4,000 contacts per campaign'] },
    loyaltyboost: { name: 'LoyaltyBoost', emoji: '💎', desc: 'Annual loyalty/rewards campaign per location',
      price: '$3,600/year', note: '$495 production fee (-$125 if renewal w/ testimonial)',
      features: ['Annual loyalty campaign', 'Rewards program setup', 'Paid-in-Full: 5% discount', '6-Month or 12-Month payment options'] },
  };

  let selectedTier = null;
  let selectedDigital = null;

  // Shareable marketing graphics
  const BASE = import.meta.env.BASE_URL || '/';
  const graphics = [
    { id: 'household-name', file: 'marketing/household-name.jpg', title: 'Become a Household Name',
      caption: 'Become a household name in your area. Reach every shopper, every trip -- with IndoorMedia.' },
    { id: 'grow-your-business', file: 'marketing/grow-your-business.jpg', title: 'Grow Your Business',
      caption: 'Grow your business with IndoorMedia -- register tape, cart ads & digital working together to reach local customers.' },
    { id: 'hype-fades-habits', file: 'marketing/hype-fades-habits.jpg', title: "Hype Fades. Habits Don't.",
      caption: "Hype fades. Habits don't. Unique & exclusive marketing that has worked for over three decades -- IndoorMedia." },
    { id: 'neighbors-customers', file: 'marketing/neighbors-customers.jpg', title: 'Turn Neighbors Into Customers',
      caption: 'Turn your neighbors into customers -- as low as $10/day with IndoorMedia.' },
    { id: 'billboard-vs-cart-5sec', file: 'marketing/billboard-vs-cart-5sec.jpg', title: 'Billboard 5 Sec vs Cart 30 Min',
      caption: 'A billboard gets 5 seconds. A cart ad gets 30 minutes. Put your business in front of shoppers the entire trip -- with IndoorMedia.' },
    { id: 'reach-local-families', file: 'marketing/reach-local-families.jpg', title: 'Reach Local Families Daily',
      caption: 'Reach thousands of local families every day. Get your business in front of the customers who matter most -- with IndoorMedia.' },
    { id: 'billboard-vs-cart-cost', file: 'marketing/billboard-vs-cart-cost.jpg', title: 'Billboard vs Grocery Cart',
      caption: 'Billboard vs. grocery cart advertising: 30+ minutes of attention, thousands of local homeowners, and just $10/day average. The smarter local buy -- IndoorMedia.' },
  ];

  async function shareGraphic(g) {
    const url = BASE + g.file;
    const msg = `${g.caption}\n\n-- ${repName()}, IndoorMedia`;
    try {
      // Try sharing the actual image file (mobile)
      const res = await fetch(url);
      const blob = await res.blob();
      const file = new File([blob], g.id + '.jpg', { type: 'image/jpeg' });
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file], text: msg });
        shareFeedback = '\u2705 Shared!';
        setTimeout(() => shareFeedback = '', 3000);
        return;
      }
      if (navigator.share) {
        await navigator.share({ text: msg, url: window.location.origin + url });
        shareFeedback = '\u2705 Shared!';
        setTimeout(() => shareFeedback = '', 3000);
        return;
      }
      // Desktop fallback: copy caption + open image
      await navigator.clipboard.writeText(msg);
      window.open(url, '_blank');
      shareFeedback = '\u2705 Caption copied -- image opened in new tab';
    } catch (e) {
      try { window.open(url, '_blank'); shareFeedback = '\u2705 Image opened'; }
      catch { shareFeedback = '\u274c Could not share'; }
    }
    setTimeout(() => shareFeedback = '', 4000);
  }

  async function downloadGraphic(g) {
    const url = BASE + g.file;
    try {
      const res = await fetch(url);
      const blob = await res.blob();
      if (navigator.share && /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)) {
        const file = new File([blob], g.id + '.jpg', { type: 'image/jpeg' });
        try { await navigator.share({ files: [file], title: g.title }); return; } catch {}
      }
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl; a.download = g.id + '.jpg';
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(blobUrl), 5000);
      shareFeedback = '\u2705 Downloaded!';
    } catch {
      window.open(url, '_blank');
      shareFeedback = '\u2705 Image opened';
    }
    setTimeout(() => shareFeedback = '', 3000);
  }

  function addToCart(name, price, details) {
    let cart = [];
    try { cart = JSON.parse(localStorage.getItem('indoormedia_cart') || '[]'); } catch {}
    cart.push({ id: Date.now(), name, price, details, addedAt: new Date().toISOString() });
    localStorage.setItem('indoormedia_cart', JSON.stringify(cart));
    try { window.dispatchEvent(new Event('cart-updated')); } catch {}
    alert('Added to cart: ' + name);
  }

  let shareFeedback = '';

  // Dynamic digital pricing
  $: dbStandard = 2400 + ($digitalPadAmount || 0);
  $: dbCoop = 1200 + ($digitalPadAmount || 0);
  $: lbPrice = 2400 + ($digitalPadAmount || 0);
  $: dbExamples = [
    { pins: 1, standard: '$' + (dbStandard + 395).toLocaleString(), coop: '$' + (dbCoop + 395).toLocaleString() },
    { pins: 2, standard: '$' + (dbStandard * 2 + 395).toLocaleString(), coop: '$' + (dbCoop * 2 + 395).toLocaleString() },
    { pins: 3, standard: '$' + (dbStandard * 3 + 395).toLocaleString(), coop: '$' + (dbCoop * 3 + 395).toLocaleString() },
    { pins: 5, standard: '$' + (dbStandard * 5 + 395).toLocaleString(), coop: '$' + (dbCoop * 5 + 395).toLocaleString() },
  ];

  function repName() {
    return $user?.name || $user?.first_name || localStorage.getItem('impro_rep_name') || 'Your IndoorMedia Rep';
  }

  async function shareProduct(productId) {
    const texts = {
      'register-tape': `🧾 Register Tape Advertising -- IndoorMedia\nYour ad printed on grocery store receipts -- seen by every single customer!\n\n✅ 100% reach -- every shopper gets a receipt\n✅ Hyper-local targeting at stores near your business\n✅ Affordable -- fraction of direct mail or digital\n✅ Trackable with coupon codes\n\n📐 Single Ad (2.75" x 1.75") or Double Ad (2.75" x 3.6")\n\n🎥 See how it works: ${VIDEO_LINKS['register-tape'].explainer}\n\n-- ${repName()}, IndoorMedia`,
      
      'cartvertising': `🛒 Cartvertising -- IndoorMedia\nFull-color ads mounted at eye level on shopping carts!\n\n✅ Eye-level visibility -- impossible to miss\n✅ 40+ minutes per shopping trip with your ad\n✅ Full-color, high-quality printing\n✅ Massive reach -- thousands of shoppers per cart\n\n🎥 See how it works: ${VIDEO_LINKS['cartvertising'].explainer}\n\n-- ${repName()}, IndoorMedia`,
      
      'digitalboost': `🚀 𝗗𝗶𝗴𝗶𝘁𝗮𝗹𝗕𝗼𝗼𝘀𝘁 — Targeted Digital Advertising\n━━━━━━━━━━━━━━━━━━━━\n✨ Eye-catching 𝗔𝗡𝗜𝗠𝗔𝗧𝗘𝗗 300×250 banner ads that follow your ideal customers across the web.\n\n🌐 Running on 𝟮,𝟬𝟬𝟬,𝟬𝟬𝟬+ 𝘄𝗲𝗯𝘀𝗶𝘁𝗲𝘀 & apps\n🎯 Targeting YOUR ideal customers — not just anyone\n📊 Dial it in by 𝗱𝗲𝗺𝗼𝗴𝗿𝗮𝗽𝗵𝗶𝗰𝘀 (age, gender, income, location) AND 𝗶𝗻𝘁𝗲𝗿𝗲𝘀𝘁𝘀\n📍 Geofence-targeted to a 1-mile radius of the store, your address, or chosen ZIP codes\n📈 240,000 – 360,000 impressions per pin\n📑 Monthly performance reports\n\n👀 See animated examples in action:\nhttps://www.indoormedia.com/digital-boost-ads/\n\n🎥 How it works: ${VIDEO_LINKS.digitalboost.explainer}\n\n— ${repName()}, IndoorMedia`,
      
      'findlocal': `📍 FindLocal -- Local SEO & Listings\nGet your business found everywhere customers are searching!\n\n✅ 50+ directory submissions\n✅ NAP optimization (name, address, phone)\n✅ Google Business Profile sync\n✅ Automated monthly progress reports\n\n🎥 See how it works: ${VIDEO_LINKS.findlocal.explainer}\n\n-- ${repName()}, IndoorMedia`,
      
      'reviewboost': `⭐ ReviewBoost -- Reputation Management\nAutomated review request campaigns via Email & SMS!\n\n✅ ReviewKit included\n✅ 4-month automated campaign\n✅ Email & SMS review requests\n✅ Up to 4,000 contacts per campaign\n\n🎥 See how it works: ${VIDEO_LINKS.reviewboost.explainer}\n\n-- ${repName()}, IndoorMedia`,
      
      'loyaltyboost': `💎 LoyaltyBoost -- Customer Retention\nAnnual loyalty & rewards program for your business!\n\n✅ Full loyalty program setup\n✅ Customer retention campaigns\n✅ Rewards program management\n✅ Annual program\n\n🎥 See how it works: ${VIDEO_LINKS.loyaltyboost.explainer}\n\n-- ${repName()}, IndoorMedia`,
    };

    const text = texts[productId];
    if (!text) return;

    try {
      if (navigator.share) {
        await navigator.share({ text });
        shareFeedback = '✅ Shared!';
      } else {
        await navigator.clipboard.writeText(text);
        shareFeedback = '✅ Copied to clipboard!';
      }
    } catch {
      try {
        await navigator.clipboard.writeText(text);
        shareFeedback = '✅ Copied!';
      } catch {
        shareFeedback = '❌ Could not share';
      }
    }
    setTimeout(() => shareFeedback = '', 3000);
  }

  let pdfGenerating = false;

  async function downloadProductPdf(productId) {
    if (pdfGenerating) return;
    pdfGenerating = true;
    shareFeedback = '⏳ Generating PDF...';
    try {
    const pdfDoc = await PDFDocument.create();
    const page = pdfDoc.addPage([612, 792]);
    const bold = await pdfDoc.embedFont(StandardFonts.HelveticaBold);
    const regular = await pdfDoc.embedFont(StandardFonts.Helvetica);
    const red = rgb(0.8, 0, 0);
    const white = rgb(1, 1, 1);
    const black = rgb(0, 0, 0);
    const gray = rgb(0.3, 0.3, 0.3);
    const dateStr = new Date().toLocaleDateString('en-US', { year:'numeric', month:'long', day:'numeric' });
    const rep = repName();
    const repEmail = 'tyler.vansant@indoormedia.com';
    let y = 792;

    // Header bar
    page.drawRectangle({ x:0, y:y-80, width:612, height:80, color:red });
    const configs = {
      'register-tape': { title:'Register Tape Advertising', subtitle:'IndoorMedia -- Grocery Receipt Ads' },
      'cartvertising': { title:'Cartvertising', subtitle:'IndoorMedia -- Shopping Cart Ads' },
      'digitalboost': { title:'DigitalBoost -- Digital Geofencing', subtitle:'IndoorMedia -- Targeted Digital Ads' },
      'findlocal': { title:'FindLocal', subtitle:'IndoorMedia -- Local SEO & Listings' },
      'reviewboost': { title:'ReviewBoost', subtitle:'IndoorMedia -- Reputation Management' },
      'loyaltyboost': { title:'LoyaltyBoost', subtitle:'IndoorMedia -- Customer Retention' },
    };
    const cfg = configs[productId] || { title: productId, subtitle: 'IndoorMedia' };
    page.drawText(cfg.title, { x:30, y:y-40, size:22, font:bold, color:white });
    page.drawText(cfg.subtitle, { x:30, y:y-60, size:11, font:regular, color:white });
    page.drawText(dateStr, { x:612 - bold.widthOfTextAtSize(dateStr,10) - 30, y:y-40, size:10, font:bold, color:white });
    y -= 100;

    function drawSection(title, items, startY) {
      page.drawText(title, { x:30, y:startY, size:14, font:bold, color:red });
      startY -= 22;
      for (const item of items) {
        page.drawRectangle({ x:40, y:startY+2, width:6, height:6, color:rgb(0.18, 0.49, 0.2) });
        page.drawText('  ' + item, { x:50, y:startY, size:11, font:regular, color:black });
        startY -= 18;
      }
      return startY - 8;
    }

    function drawPricing(rows, startY) {
      page.drawText('Pricing', { x:30, y:startY, size:14, font:bold, color:red });
      startY -= 22;
      for (const [label, value] of rows) {
        page.drawText(label, { x:40, y:startY, size:11, font:bold, color:black });
        page.drawText(value, { x:280, y:startY, size:11, font:regular, color:gray });
        startY -= 18;
      }
      return startY - 8;
    }

    if (productId === 'register-tape') {
      // 2x2 Value Prop Cards (matching app design)
      const cardW = 250;
      const cardH = 110;
      const cardGap = 16;
      const cardStartX = 30;
      const cardBg = rgb(0.96, 0.96, 0.96);
      const cardBorder = rgb(0.88, 0.88, 0.88);
      
      const cards = [
        { title: '100% Reach', desc: 'Every customer gets a receipt -- your ad is seen by every single shopper' },
        { title: 'Hyper-Local', desc: 'Target customers shopping at stores near your business' },
        { title: 'Affordable', desc: 'Fraction of the cost of direct mail, billboards, or digital ads' },
        { title: 'Trackable', desc: 'Coupon codes let you measure exactly how many customers respond' },
      ];
      
      for (let i = 0; i < 4; i++) {
        const col = i % 2;
        const row = Math.floor(i / 2);
        const cx = cardStartX + col * (cardW + cardGap);
        const cy = y - row * (cardH + cardGap);
        
        // Card background with rounded corners (simulated with rectangle)
        page.drawRectangle({ x:cx, y:cy-cardH, width:cardW, height:cardH, color:cardBg, borderColor:cardBorder, borderWidth:1 });
        
        // Title
        page.drawText(cards[i].title, { x:cx+16, y:cy-30, size:14, font:bold, color:black });
        
        // Description (word wrap manually)
        const words = cards[i].desc.split(' ');
        let line = '';
        let lineY = cy - 48;
        for (const word of words) {
          const test = line ? line + ' ' + word : word;
          if (regular.widthOfTextAtSize(test, 10) > cardW - 32) {
            page.drawText(line, { x:cx+16, y:lineY, size:10, font:regular, color:gray });
            lineY -= 14;
            line = word;
          } else {
            line = test;
          }
        }
        if (line) {
          page.drawText(line, { x:cx+16, y:lineY, size:10, font:regular, color:gray });
        }
      }
      
      y -= 2 * (cardH + cardGap) + 20;
      
      // Ad Size Graphics
      page.drawText('Ad Sizes (actual proportions)', { x:30, y, size:14, font:bold, color:red }); y -= 28;
      
      const scale = 50;
      const singleW = 2.75 * scale;
      const singleH = 1.75 * scale;
      const doubleW = 2.75 * scale;
      const doubleH = 3.6 * scale;
      
      // Single ad box
      const singleX = 60;
      page.drawRectangle({ x:singleX, y:y-singleH, width:singleW, height:singleH, borderColor:red, borderWidth:2, color:rgb(1, 0.95, 0.95) });
      page.drawText('SINGLE AD', { x:singleX + singleW/2 - bold.widthOfTextAtSize('SINGLE AD',12)/2, y:y-singleH/2-4, size:12, font:bold, color:red });
      page.drawText('2.75" x 1.75"', { x:singleX + singleW/2 - regular.widthOfTextAtSize('2.75" x 1.75"',9)/2, y:y-singleH/2-20, size:9, font:regular, color:gray });
      
      // Double ad box
      const doubleX = singleX + singleW + 40;
      page.drawRectangle({ x:doubleX, y:y-doubleH, width:doubleW, height:doubleH, borderColor:red, borderWidth:2, color:rgb(1, 0.95, 0.95) });
      page.drawText('DOUBLE AD', { x:doubleX + doubleW/2 - bold.widthOfTextAtSize('DOUBLE AD',12)/2, y:y-doubleH/2-4, size:12, font:bold, color:red });
      page.drawText('2.75" x 3.6"', { x:doubleX + doubleW/2 - regular.widthOfTextAtSize('2.75" x 3.6"',9)/2, y:y-doubleH/2-20, size:9, font:regular, color:gray });
      
      y -= doubleH + 24;
      page.drawText('Ask your rep about pricing for stores near your business.', { x:40, y, size:11, font:bold, color:gray }); y -= 18;
      
    } else if (productId === 'cartvertising') {
      y = drawSection('Why Cartvertising?', [
        'Eye-Level -- ads mounted right where shoppers look',
        '40+ Minutes -- your ad stays with them the entire trip',
        'Full Color -- high-quality printing for maximum impact',
        'Massive Reach -- thousands of shoppers per cart',
        '6-month campaigns available',
      ], y);
      page.drawText('Ask your rep about package options and pricing.', { x:40, y, size:11, font:bold, color:gray }); y -= 18;
    } else if (productId === 'digitalboost') {
      y = drawSection('Why DigitalBoost?', [
        'Geofence pin targets customers near your business',
        'Digital banner ads on mobile apps & websites',
        '240,000 - 360,000 ad impressions per pin',
        'Monthly performance reports included',
        'Multiple pin options available',
      ], y);
      page.drawText('Ask your rep about pricing and pin options.', { x:40, y, size:11, font:bold, color:gray }); y -= 18;
    } else if (productId === 'findlocal') {
      y = drawSection('Why FindLocal?', [
        '50+ business directory submissions',
        'NAP optimization (name, address, phone)',
        'Google Business Profile sync',
        'Automated monthly progress reports',
        'Hours, photos, and categories management',
      ], y);
      page.drawText('Ask your rep about pricing for your location.', { x:40, y, size:11, font:bold, color:gray }); y -= 18;
    } else if (productId === 'reviewboost') {
      y = drawSection('Why ReviewBoost?', [
        'ReviewKit included -- everything you need',
        'Automated 4-month Email & SMS campaign',
        'Up to 4,000 contacts per campaign',
        'Build your online reputation fast',
      ], y);
      page.drawText('Ask your rep about campaign options.', { x:40, y, size:11, font:bold, color:gray }); y -= 18;
    } else if (productId === 'loyaltyboost') {
      y = drawSection('Why LoyaltyBoost?', [
        'Annual loyalty & rewards program',
        'Full rewards program setup',
        'Customer retention campaigns',
        'Multiple payment options available',
      ], y);
      page.drawText('Ask your rep about annual program pricing.', { x:40, y, size:11, font:bold, color:gray }); y -= 18;
    }

    // CTA
    y = Math.max(y, 100);
    page.drawRectangle({ x:30, y:y-10, width:552, height:50, color:rgb(0.95, 0.95, 0.95) });
    page.drawText('Ready to get started? Contact your rep:', { x:40, y:y+20, size:12, font:bold, color:red });
    page.drawText(`${rep}  |  ${repEmail}`, { x:40, y:y+2, size:11, font:regular, color:black });
    
    // Footer
    page.drawText('IndoorMedia  |  indoormedia.com', { x:612/2 - bold.widthOfTextAtSize('IndoorMedia  |  indoormedia.com',9)/2, y:30, size:9, font:regular, color:gray });

    const bytes = await pdfDoc.save();
    const blob = new Blob([bytes], { type:'application/pdf' });
    const url = URL.createObjectURL(blob);
    const names = { 'register-tape':'RegisterTape', 'cartvertising':'Cartvertising', 'digitalboost':'DigitalBoost', 'findlocal':'FindLocal', 'reviewboost':'ReviewBoost', 'loyaltyboost':'LoyaltyBoost' };
    const filename = `IndoorMedia_${names[productId] || productId}.pdf`;
    
    // iOS Safari doesn't support programmatic download via a.click()
    // Use navigator.share for mobile if available, otherwise open in new tab
    if (navigator.share && /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)) {
      try {
        const file = new File([bytes], filename, { type: 'application/pdf' });
        await navigator.share({ files: [file], title: filename });
        URL.revokeObjectURL(url);
        return;
      } catch (e) {
        // Fallback below
      }
    }
    
    // Fallback: open PDF in new window
    window.open(url, '_blank');
    shareFeedback = '✅ PDF opened!';
    setTimeout(() => { URL.revokeObjectURL(url); shareFeedback = ''; }, 5000);
    } catch (err) {
      console.error('PDF generation error:', err);
      shareFeedback = '❌ Error: ' + (err.message || 'PDF failed');
      setTimeout(() => shareFeedback = '', 5000);
    } finally {
      pdfGenerating = false;
    }
  }
</script>

<div class="present">
  {#if view === 'menu'}
    <h2>🎤 Present</h2>
    <p class="subtitle">Choose a product to present to your prospect</p>
    <button class="prep-card" on:click={() => view = 'meeting-prep'}>
      <div class="prep-left">
        <div class="prep-icon">📋</div>
        <div>
          <h3>Meeting Prep</h3>
          <p>Look up a business, find matching testimonials, and prep for your meeting</p>
        </div>
      </div>
      <span class="arrow">→</span>
    </button>

    <button class="prep-card graphics-card" on:click={() => view = 'graphics'}>
      <div class="prep-left">
        <div class="prep-icon">🖼️</div>
        <div>
          <h3>Shareable Graphics</h3>
          <p>Send ready-made marketing images to prospects via text or email</p>
        </div>
      </div>
      <span class="arrow">→</span>
    </button>

    <div class="product-grid">
      {#each products as p}
        <button class="product-card" on:click={() => view = p.id}>
          <div class="product-icon">{p.icon}</div>
          <h3>{p.name}</h3>
          <p class="product-desc">{p.desc}</p>
          <ul class="product-features">{#each p.features as f}<li>{f}</li>{/each}</ul>
          <span class="tap-hint">Tap to present →</span>
        </button>
      {/each}
    </div>

  <!-- ========== REGISTER TAPE ========== -->
  {:else if view === 'register-tape'}
    <button class="back-btn" on:click={() => { view = selectedTier ? 'register-tape' : 'menu'; selectedTier = null; }}>← {selectedTier ? 'Back to Tiers' : 'Back'}</button>

    {#if !selectedTier}
      <h2>🧾 Register Tape Advertising</h2>

      <div class="video-links">
        <a href={VIDEO_LINKS['register-tape'].presentation} target="_blank" class="video-btn">🎬 Sales Presentation</a>
        <a href={VIDEO_LINKS['register-tape'].explainer} target="_blank" class="video-btn">📹 Explainer Video</a>
      </div>

      <div class="value-props">
        <div class="value-card"><span class="vi">🎯</span><h4>100% Reach</h4><p>Every customer gets a receipt -- your ad is seen by every single shopper</p></div>
        <div class="value-card"><span class="vi">📍</span><h4>Hyper-Local</h4><p>Target customers shopping at stores near your business</p></div>
        <div class="value-card"><span class="vi">💰</span><h4>Affordable</h4><p>Fraction of the cost of direct mail, billboards, or digital ads</p></div>
        <div class="value-card"><span class="vi">📊</span><h4>Trackable</h4><p>Coupon codes let you measure exactly how many customers respond</p></div>
      </div>

      <div class="section-divider"><h3>📐 Ad Sizes</h3></div>
      <div class="size-comparison">
        <div class="size-box"><div class="size-preview single-sz"><span>SINGLE</span></div><p><strong>Single Ad</strong></p><p class="dims">2.75" x 1.75"</p></div>
        <div class="size-box"><div class="size-preview double-sz"><span>DOUBLE</span></div><p><strong>Double Ad</strong></p><p class="dims">2.75" x 3.6"</p></div>
      </div>

      <div class="section-divider"><h3>💳 Pricing Tiers</h3></div>
      {#each Object.entries(tapeTiers) as [key, tier]}
        <button class="tier-card" on:click={() => selectedTier = key}>
          <div class="tier-left"><span class="tier-emoji">{tier.emoji}</span><div><h4>{tier.name}</h4><p>{tier.desc}</p></div></div>
          <span class="arrow">→</span>
        </button>
      {/each}
    {:else}
      <h2>{tapeTiers[selectedTier].emoji} {tapeTiers[selectedTier].name}</h2>
      <p class="subtitle">{tapeTiers[selectedTier].desc}</p>
      <div class="pricing-card">
        <h4>Payment Plans</h4>
        {#each Object.entries(tapeTiers[selectedTier].pricing) as [plan, formula]}
          <div class="pricing-row"><span class="plan">{plan}</span><span class="formula">{formula}</span></div>
        {/each}
      </div>
      <button class="cart-btn" on:click={() => addToCart('Register Tape -- ' + tapeTiers[selectedTier].name, 'Store-based', selectedTier)}>🛒 Add to Cart</button>
    {/if}
    <div class="btn-row">
      <button class="share-btn" on:click={() => shareProduct('register-tape')}>📩 Send to Customer</button>
      <button class="pdf-btn" disabled={pdfGenerating} on:click={() => downloadProductPdf('register-tape')}>{ pdfGenerating ? "⏳ Generating..." : "📄 Download PDF" }</button>
    </div>
    {#if shareFeedback}<p class="share-feedback">{shareFeedback}</p>{/if}
    <div style="height:80px;"></div>

  <!-- ========== CARTVERTISING ========== -->
  {:else if view === 'cartvertising'}
    <button class="back-btn" on:click={() => view = 'menu'}>← Back</button>
    <h2>🛒 Cartvertising</h2>

    <div class="video-links">
      <a href={VIDEO_LINKS['cartvertising'].presentation} target="_blank" class="video-btn">🎬 Sales Presentation</a>
      <a href={VIDEO_LINKS['cartvertising'].explainer} target="_blank" class="video-btn">📹 Explainer Video</a>
    </div>

    <div class="value-props">
      <div class="value-card"><span class="vi">👁️</span><h4>Eye-Level</h4><p>Ads mounted at eye level on shopping carts -- impossible to miss</p></div>
      <div class="value-card"><span class="vi">⏱️</span><h4>40+ Minutes</h4><p>Average shopping trip keeps your ad with them the whole time</p></div>
      <div class="value-card"><span class="vi">🎨</span><h4>Full Color</h4><p>High-quality, full-color printing for maximum brand impact</p></div>
      <div class="value-card"><span class="vi">🔄</span><h4>Massive Reach</h4><p>Thousands of shoppers use each cart -- huge impression volume</p></div>
    </div>

    <div class="section-divider"><h3>📦 Packages (6-Month Campaigns)</h3></div>
    {#each cartPackages as pkg}
      <div class="package-row">
        <div><h4>{pkg.name}</h4></div>
        <div class="pkg-right"><span class="pkg-price">{pkg.price}</span>
          <button class="cart-sm" on:click={() => addToCart('Cartvertising -- ' + pkg.name, pkg.price, '6-month')}>🛒</button>
        </div>
      </div>
    {/each}
    <div class="btn-row">
      <button class="share-btn" on:click={() => shareProduct('cartvertising')}>📩 Send to Customer</button>
      <button class="pdf-btn" disabled={pdfGenerating} on:click={() => downloadProductPdf('cartvertising')}>{ pdfGenerating ? "⏳ Generating..." : "📄 Download PDF" }</button>
    </div>
    {#if shareFeedback}<p class="share-feedback">{shareFeedback}</p>{/if}
    <div style="height:80px;"></div>

  <!-- ========== DIGITAL ========== -->
  {:else if view === 'digital'}
    <button class="back-btn" on:click={() => { if (selectedDigital) { selectedDigital = null; } else { view = 'menu'; } }}>← {selectedDigital ? 'Back to Digital' : 'Back'}</button>

    {#if !selectedDigital}
      <h2>📱 Digital Solutions</h2>
      <div class="digital-grid">
        {#each Object.entries(digitalProducts) as [key, dp]}
          <button class="digital-card" on:click={() => selectedDigital = key}>
            <span class="dp-emoji">{dp.emoji}</span>
            <h4>{dp.name}</h4>
            <p>{dp.desc}</p>
            {#if VIDEO_LINKS[key]?.explainer}
              <span class="vid-badge">📹 Video</span>
            {/if}
          </button>
        {/each}
      </div>

    {:else if selectedDigital === 'digitalboost'}
      <h2>🚀 DigitalBoost</h2>
      <p class="subtitle">Geofence pin delivering digital banner ad impressions</p>
      <div class="video-links">
        <a href={VIDEO_LINKS.digitalboost.presentation} target="_blank" class="video-btn">🎬 Presentation</a>
        <a href={VIDEO_LINKS.digitalboost.explainer} target="_blank" class="video-btn">📹 Video</a>
        <a href={VIDEO_LINKS.digitalboost.connectionHub} target="_blank" class="video-btn">🔗 Hub</a>
        <a href="https://www.indoormedia.com/digital-boost-ads/" target="_blank" class="video-btn">📱 DigitalBoost Examples</a>
      </div>
      <div class="pricing-card">
        <div class="pricing-row"><span class="plan">Standard (per pin)</span><span class="formula">${dbStandard.toLocaleString()}</span></div>
        <div class="pricing-row"><span class="plan">Co-Op (per pin)</span><span class="formula">${dbCoop.toLocaleString()}</span></div>
        <div class="pricing-row"><span class="plan">Production</span><span class="formula">$395 (covers 5 pins)</span></div>
        <div class="pricing-row"><span class="plan">Impressions (standalone)</span><span class="formula">240,000</span></div>
        <div class="pricing-row"><span class="plan">Impressions (bundled)</span><span class="formula">360,000</span></div>
      </div>
      <div class="section-divider"><h3>💰 Pricing Examples</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Pins</th><th>Standard</th><th>Co-Op</th></tr></thead>
        <tbody>{#each dbExamples as ex}<tr><td>{ex.pins}</td><td>{ex.standard}</td><td>{ex.coop}</td></tr>{/each}</tbody>
      </table></div>
      <button class="cart-btn" on:click={() => addToCart('DigitalBoost', '$' + dbStandard.toLocaleString() + '/pin', '240K impressions')}>🛒 Add to Cart</button>
      <div class="btn-row">
        <button class="share-btn" on:click={() => shareProduct('digitalboost')}>📩 Send to Customer</button>
        <button class="pdf-btn" disabled={pdfGenerating} on:click={() => downloadProductPdf('digitalboost')}>{ pdfGenerating ? "⏳ Generating..." : "📄 Download PDF" }</button>
      </div>
      {#if shareFeedback}<p class="share-feedback">{shareFeedback}</p>{/if}

    {:else}
      {@const dp = digitalProducts[selectedDigital]}
      <h2>{dp.emoji} {dp.name}</h2>
      <p class="subtitle">{dp.desc}</p>
      {#if VIDEO_LINKS[selectedDigital]?.explainer}
        <div class="video-links">
          <a href={VIDEO_LINKS[selectedDigital].explainer} target="_blank" class="video-btn">📹 Explainer Video</a>
        </div>
      {/if}
      <div class="pricing-card">
        <div class="pricing-row"><span class="plan">Price</span><span class="formula">{dp.price}</span></div>
        {#if dp.note}<div class="pricing-row"><span class="plan">Note</span><span class="formula">{dp.note}</span></div>{/if}
      </div>
      {#if dp.analysisUrl}
        <a href={dp.analysisUrl} target="_blank" class="analysis-btn">🔍 Run Local Listing Analysis</a>
      {/if}
      {#if dp.features}
        <div class="section-divider"><h3>✅ Features</h3></div>
        <ul class="feat-list">{#each dp.features as f}<li>✓ {f}</li>{/each}</ul>
      {/if}
      <button class="cart-btn" on:click={() => addToCart(dp.name, dp.price, dp.desc)}>🛒 Add to Cart</button>
      <div class="btn-row">
        <button class="share-btn" on:click={() => shareProduct(selectedDigital)}>📩 Send to Customer</button>
        <button class="pdf-btn" disabled={pdfGenerating} on:click={() => downloadProductPdf(selectedDigital)}>{ pdfGenerating ? "⏳ Generating..." : "📄 Download PDF" }</button>
      </div>
      {#if shareFeedback}<p class="share-feedback">{shareFeedback}</p>{/if}
    {/if}
    <div style="height:80px;"></div>

  <!-- ========== SHAREABLE GRAPHICS ========== -->
  {:else if view === 'graphics'}
    <button class="back-btn" on:click={() => view = 'menu'}>← Back</button>
    <h2>🖼️ Shareable Graphics</h2>
    <p class="subtitle">Tap Send to text/email the image, or Download to save it</p>

    <div class="graphics-grid">
      {#each graphics as g}
        <div class="graphic-item">
          <img class="graphic-img" src={BASE + g.file} alt={g.title} loading="lazy" />
          <h4>{g.title}</h4>
          <div class="btn-row">
            <button class="share-btn" on:click={() => shareGraphic(g)}>📩 Send</button>
            <button class="pdf-btn" on:click={() => downloadGraphic(g)}>⬇️ Save</button>
          </div>
        </div>
      {/each}
    </div>
    {#if shareFeedback}<p class="share-feedback">{shareFeedback}</p>{/if}
    <div style="height:80px;"></div>

  {:else if view === 'meeting-prep'}
    <MeetingPrep onBack={() => view = 'menu'} />
  {/if}
</div>

<style>
  .present { padding-bottom: 140px; }
  .subtitle { font-size:14px; color:var(--text-secondary); margin:0 0 16px; }
  .back-btn { background:none; border:none; color:var(--text-secondary); font-size:14px; cursor:pointer; padding:8px 0; }
  
  /* Meeting Prep card */
  .prep-card { display:flex; align-items:center; justify-content:space-between; width:100%; background:var(--card-bg); border:2px solid #CC0000; border-radius:16px; padding:18px; margin-bottom:20px; cursor:pointer; transition:all .2s; text-align:left; }
  .prep-card:hover { transform:translateY(-2px); box-shadow:0 4px 12px rgba(204,0,0,.15); }
  .prep-left { display:flex; align-items:center; gap:14px; }
  .prep-icon { font-size:36px; }
  .prep-card h3 { margin:0 0 4px; font-size:18px; font-weight:800; color:#CC0000; }
  .prep-card p { margin:0; font-size:13px; color:var(--text-secondary); line-height:1.3; }
  .arrow { font-size:20px; color:var(--text-tertiary); }
  
  /* Product cards */
  .product-grid { display:flex; flex-direction:column; gap:16px; }
  .product-card { background:var(--card-bg); border:2px solid var(--border-color); border-radius:16px; padding:20px; text-align:left; cursor:pointer; transition:all .2s; }
  .product-card:hover { border-color:#CC0000; transform:translateY(-2px); box-shadow:0 4px 12px rgba(0,0,0,.1); }
  .product-card:active { transform:scale(.98); }
  .product-icon { font-size:40px; margin-bottom:8px; }
  .product-card h3 { margin:0 0 6px; font-size:20px; font-weight:800; color:var(--text-primary); }
  .product-desc { font-size:13px; color:var(--text-secondary); margin:0 0 10px; line-height:1.4; }
  .product-features { margin:0 0 10px; padding-left:18px; font-size:12px; color:var(--text-tertiary); line-height:1.8; }
  .tap-hint { display:block; text-align:right; font-size:12px; color:var(--text-tertiary); margin-top:8px; }

  /* Video links */
  .video-links { display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap; }
  .video-btn { flex:1; min-width:80px; display:block; padding:10px 8px; background:var(--card-bg); border:2px solid var(--border-color); border-radius:10px; text-align:center; text-decoration:none; color:var(--text-primary); font-size:13px; font-weight:700; transition:all .2s; }
  .video-btn:hover { border-color:#CC0000; color:#CC0000; }

  /* Value props */
  .value-props { display:grid; grid-template-columns:repeat(2,1fr); gap:12px; margin:16px 0; }
  .value-card { background:var(--card-bg); border:2px solid var(--border-color); border-radius:12px; padding:14px; }
  .vi { font-size:28px; }
  .value-card h4 { margin:6px 0 4px; font-size:15px; font-weight:700; color:var(--text-primary); }
  .value-card p { margin:0; font-size:12px; color:var(--text-secondary); line-height:1.4; }

  /* Sizes */
  .section-divider { margin:20px 0 12px; }
  .section-divider h3 { font-size:17px; font-weight:700; }
  .size-comparison { display:flex; gap:16px; justify-content:center; }
  .size-box { text-align:center; flex:1; }
  .size-box p { margin:6px 0 0; font-size:14px; color:var(--text-primary); }
  .dims { font-size:12px !important; color:var(--text-secondary) !important; }
  .size-preview { background:#CC0000; color:#fff; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:14px; border-radius:4px; margin:0 auto; }
  .single-sz { width:140px; height:89px; }
  .double-sz { width:140px; height:183px; }

  /* Tiers */
  .tier-card { display:flex; align-items:center; justify-content:space-between; width:100%; background:var(--card-bg); border:2px solid var(--border-color); border-radius:12px; padding:14px; margin-bottom:10px; cursor:pointer; transition:border-color .2s; text-align:left; }
  .tier-card:hover { border-color:#CC0000; }
  .tier-left { display:flex; align-items:center; gap:12px; }
  .tier-emoji { font-size:28px; }
  .tier-card h4 { margin:0 0 2px; font-size:15px; color:var(--text-primary); }
  .tier-card p { margin:0; font-size:12px; color:var(--text-secondary); }
  .arrow { font-size:18px; color:var(--text-tertiary); }

  /* Pricing */
  .pricing-card { background:var(--card-bg); border:2px solid var(--border-color); border-radius:12px; padding:16px; margin-bottom:16px; }
  .pricing-card h4 { margin:0 0 10px; font-size:15px; color:var(--text-primary); }
  .pricing-row { display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid var(--border-color); gap:8px; }
  .pricing-row:last-child { border-bottom:none; }
  .plan { font-weight:700; font-size:13px; color:var(--text-primary); white-space:nowrap; }
  .formula { font-size:12px; color:var(--text-secondary); text-align:right; }

  /* Cart buttons */
  .cart-btn { width:100%; padding:13px; background:#CC0000; color:#fff; border:none; border-radius:10px; font-size:15px; font-weight:700; cursor:pointer; margin-top:8px; }
  .cart-btn:hover { background:#a00; }

  /* Packages */
  .package-row { display:flex; justify-content:space-between; align-items:center; background:var(--card-bg); border:2px solid var(--border-color); border-radius:10px; padding:12px 14px; margin-bottom:8px; }
  .package-row h4 { margin:0; font-size:13px; color:var(--text-primary); }
  .pkg-right { display:flex; align-items:center; gap:10px; }
  .pkg-price { font-size:15px; font-weight:800; color:#CC0000; }
  .cart-sm { background:#CC0000; color:#fff; border:none; border-radius:6px; padding:6px 10px; cursor:pointer; font-size:14px; }

  /* Digital */
  .digital-grid { display:flex; flex-direction:column; gap:12px; }
  .digital-card { background:var(--card-bg); border:2px solid var(--border-color); border-radius:12px; padding:16px; text-align:left; cursor:pointer; transition:all .2s; }
  .digital-card:hover { border-color:#CC0000; }
  .dp-emoji { font-size:28px; }
  .digital-card h4 { margin:6px 0 4px; font-size:16px; color:var(--text-primary); }
  .digital-card p { margin:0; font-size:13px; color:var(--text-secondary); line-height:1.4; }
  .vid-badge { display:inline-block; margin-top:8px; font-size:11px; font-weight:700; color:#CC0000; background:rgba(204,0,0,.1); padding:2px 8px; border-radius:4px; }

  /* Table */
  .table-wrap { overflow-x:auto; margin-bottom:16px; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th { background:var(--bg-secondary,#f5f5f5); padding:8px; text-align:left; font-weight:700; border-bottom:2px solid var(--border-color); color:var(--text-secondary); }
  td { padding:8px; border-bottom:1px solid var(--border-color); color:var(--text-primary); }

  /* Features */
  .feat-list { padding-left:0; list-style:none; }
  .feat-list li { padding:6px 0; font-size:13px; color:var(--text-primary); border-bottom:1px solid var(--border-color); }
  .feat-list li:last-child { border-bottom:none; }
  .analysis-btn { display:block; width:100%; padding:14px; background:#1565C0; color:#fff; border:none; border-radius:10px; font-size:15px; font-weight:700; text-align:center; text-decoration:none; margin:12px 0; box-sizing:border-box; }
  .analysis-btn:hover { background:#0D47A1; }
  .btn-row { display:flex; gap:8px; margin-top:10px; }
  .btn-row .share-btn { flex:1; margin-top:0; }
  .share-btn { width: 100%; padding: 14px; background: #1565C0; color: white; border: none; border-radius: 12px; font-size: 16px; font-weight: 700; cursor: pointer; margin-top: 10px; }
  .share-btn:hover { background: #0D47A1; }
  .pdf-btn { flex:0 0 auto; padding:14px 18px; background:#2e7d32; color:white; border:none; border-radius:12px; font-size:16px; font-weight:700; cursor:pointer; white-space:nowrap; }
  .pdf-btn:hover { background:#1b5e20; }
  .share-feedback { text-align: center; font-size: 14px; color: #2e7d32; font-weight: 600; margin-top: 8px; }

  /* Shareable graphics */
  .graphics-card { border-color:#1565C0; }
  .graphics-card h3 { color:#1565C0; }
  .graphics-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:14px; }
  .graphic-item { background:var(--card-bg); border:2px solid var(--border-color); border-radius:14px; padding:10px; }
  .graphic-img { width:100%; aspect-ratio:1/1; object-fit:cover; border-radius:10px; display:block; }
  .graphic-item h4 { margin:8px 0 8px; font-size:13px; font-weight:700; color:var(--text-primary); line-height:1.3; text-align:center; }
  .graphic-item .btn-row { gap:6px; }
  .graphic-item .share-btn { flex:1; margin-top:0; padding:10px 6px; font-size:13px; }
  .graphic-item .pdf-btn { flex:1; padding:10px 6px; font-size:13px; }
  @media (max-width:380px){ .graphics-grid { grid-template-columns:1fr; } }
</style>
