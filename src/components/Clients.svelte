<script>
  import { onMount } from 'svelte';
  import { user } from '../lib/stores.js';
  import * as pdfjsLib from 'pdfjs-dist';
  
  // Set worker source for pdfjs
  pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.9.155/pdf.worker.min.mjs';

  let view = 'main'; // main, customers, sales, submit-contract, renewals, ad-proofs
  let contracts = [];
  let allStores = [];
  let loading = true;
  let searchQuery = '';
  let expandedCustomer = null;
  let emailDraft = null;
  
  // Pending Renewals
  let pendingRenewals = [];
  let renewalSearch = '';
  let renewalCycleFilter = 'all';
  let renewalRepFilter = 'all';
  let renewalZoneFilter = 'all';
  let expandedRenewal = null;
  let selectedRenewals = new Set();
  let selectMode = false;

  function toggleSelect(accountNumber) {
    if (selectedRenewals.has(accountNumber)) {
      selectedRenewals.delete(accountNumber);
    } else {
      selectedRenewals.add(accountNumber);
    }
    selectedRenewals = selectedRenewals; // trigger reactivity
  }

  function selectAll() {
    if (selectedRenewals.size === filteredRenewals.length) {
      selectedRenewals = new Set();
    } else {
      selectedRenewals = new Set(filteredRenewals.map(r => r.accountNumber));
    }
  }

  async function exportSelectedPdf() {
    const { PDFDocument, rgb, StandardFonts } = await import('pdf-lib');
    const selected = filteredRenewals.filter(r => selectedRenewals.has(r.accountNumber));
    if (selected.length === 0) return alert('No renewals selected');

    const pdf = await PDFDocument.create();
    const font = await pdf.embedFont(StandardFonts.Helvetica);
    const fontBold = await pdf.embedFont(StandardFonts.HelveticaBold);
    
    const pageW = 612; // Letter
    const pageH = 792;
    const margin = 50;
    let page = pdf.addPage([pageW, pageH]);
    let y = pageH - margin;

    // Title
    page.drawText('IndoorMedia — Renewal Assignments', { x: margin, y, font: fontBold, size: 18, color: rgb(0.8, 0, 0) });
    y -= 22;
    page.drawText(`Generated: ${new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })} | ${selected.length} renewal${selected.length !== 1 ? 's' : ''}`, { x: margin, y, font, size: 10, color: rgb(0.4, 0.4, 0.4) });
    y -= 8;

    // Group by rep
    const byRep = {};
    selected.forEach(r => {
      const rep = r.rep || 'Unassigned';
      if (!byRep[rep]) byRep[rep] = [];
      byRep[rep].push(r);
    });

    for (const [rep, renewals] of Object.entries(byRep)) {
      // Check if we need a new page
      if (y < 120) { page = pdf.addPage([pageW, pageH]); y = pageH - margin; }

      y -= 20;
      page.drawRectangle({ x: margin - 5, y: y - 4, width: pageW - 2 * margin + 10, height: 20, color: rgb(0.8, 0, 0) });
      page.drawText(`Rep: ${rep} (${renewals.length} renewal${renewals.length !== 1 ? 's' : ''})`, { x: margin, y, font: fontBold, size: 12, color: rgb(1, 1, 1) });
      y -= 22;

      // Column headers
      const cols = [
        { label: 'Business', x: margin, w: 130 },
        { label: 'Store', x: margin + 135, w: 85 },
        { label: 'Contact', x: margin + 225, w: 80 },
        { label: 'Phone', x: margin + 310, w: 75 },
        { label: 'Price', x: margin + 390, w: 55 },
        { label: 'Ends', x: margin + 450, w: 50 },
        { label: 'Due By', x: margin + 505, w: 55 },
      ];
      cols.forEach(c => page.drawText(c.label, { x: c.x, y, font: fontBold, size: 8, color: rgb(0.3, 0.3, 0.3) }));
      y -= 2;
      page.drawLine({ start: { x: margin, y }, end: { x: pageW - margin, y }, thickness: 0.5, color: rgb(0.7, 0.7, 0.7) });
      y -= 12;

      for (const r of renewals) {
        if (y < 60) { page = pdf.addPage([pageW, pageH]); y = pageH - margin; }

        const dl = getRenewalDeadline(r);
        const dlStr = dl ? dl.toLocaleDateString('en-US', {month:'numeric', day:'numeric', year:'2-digit'}) : '';
        const row = [
          (r.business || '').slice(0, 24),
          (r.store || '').slice(0, 15),
          (r.contactName || '').slice(0, 14),
          r.phone || '',
          fmtPrice(r.contractPrice),
          r.endDate || '',
          dlStr,
        ];
        cols.forEach((c, i) => {
          page.drawText(row[i], { x: c.x, y, font, size: 8, color: rgb(0.1, 0.1, 0.1) });
        });

        // Add category + address on second line
        y -= 10;
        const addr = [r.address, r.city, r.state].filter(Boolean).join(', ');
        page.drawText(`${r.category || ''} | ${addr}`.slice(0, 80), { x: margin + 10, y, font, size: 7, color: rgb(0.5, 0.5, 0.5) });
        
        y -= 14;
        page.drawLine({ start: { x: margin, y: y + 4 }, end: { x: pageW - margin, y: y + 4 }, thickness: 0.3, color: rgb(0.85, 0.85, 0.85) });
      }
    }

    // Footer on last page
    page.drawText('IndoorMedia imPro Sales Portal — Confidential', { x: margin, y: 30, font, size: 7, color: rgb(0.6, 0.6, 0.6) });

    const pdfBytes = await pdf.save();
    const blob = new Blob([pdfBytes], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `renewals_${new Date().toISOString().slice(0,10)}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  }
  
  // Ad Proofs
  let adProofs = [];
  let proofSearch = '';
  let proofZoneFilter = 'all';
  let proofRepFilter = 'all';
  let proofStoreFilter = 'all';
  let expandedProof = null;
  let draftPreview = null; // { subject, body, email, proofId }

  function findNearbyStores(storeField) {
    // Extract city and state from store field like "Fred Meyer 0035, 11425 SW Beaverton Hillsdale Hwy, Beaverton, OR"
    if (!storeField || !allStores.length) return [];
    const parts = storeField.replace(/^[>\s]+/, '').split(',').map(s => s.trim());
    let city = '', state = '';
    if (parts.length >= 3) {
      // Last part is state, second-to-last is city
      state = parts[parts.length - 1].replace(/\d+/g, '').trim();
      city = parts[parts.length - 2].trim();
    }
    if (!city || !state) return [];
    
    // Find stores in the same city
    const sameCityStores = allStores.filter(s => 
      s.City && s.City.toLowerCase() === city.toLowerCase() &&
      s.State && s.State.toLowerCase() === state.toLowerCase()
    );
    
    // If not enough, expand to same state
    if (sameCityStores.length < 5) {
      const sameStateStores = allStores.filter(s =>
        s.State && s.State.toLowerCase() === state.toLowerCase()
      ).slice(0, 10);
      // Combine: same city first, then same state (deduped)
      const ids = new Set(sameCityStores.map(s => s.StoreName));
      const extras = sameStateStores.filter(s => !ids.has(s.StoreName));
      return [...sameCityStores, ...extras].slice(0, 8);
    }
    return sameCityStores.slice(0, 8);
  }

  function showDraft(proof, templateType) {
    const contact = proof.contact_name || 'there';
    const biz = proof.client_name || 'your business';
    const store = proof.store?.replace(/^[>\s]+/, '') || 'the store';
    const rep = $user?.name || 'Your IndoorMedia Rep';
    const installMonth = proof.install_month || 'soon';
    const adSize = proof.ad_size || 'Single';
    
    let subject = '', body = '';
    
    if (templateType === 'ready') {
      subject = `Your Ad Design is Ready! — ${biz}`;
      body = `Hi ${contact},\n\nGreat news — your ad design for ${biz} is ready!\n\nPlease take a moment to review the proof carefully. Double check that your:\n• Business address is correct\n• Phone number is accurate\n• Any offer/coupon details are right\n• Business name spelling is correct\n\nYour ad will be placed at ${store}.\n\nIf everything looks good, just reply with your approval. If you need any changes, let me know and we'll get it updated right away.\n\nLooking forward to getting this rolling for you!\n\n${rep}`;
    } else if (templateType === 'stronger') {
      subject = `Quick Thought on Your Ad — ${biz}`;
      body = `Hi ${contact},\n\nI was looking at the proof for ${biz} and wanted to share a quick thought.\n\nThe businesses that see the best results from their register tape ads are the ones with a strong, specific offer — something that makes shoppers take action right then and there.\n\nHere are some ideas that consistently drive traffic:\n• A dollar-off or percentage discount (e.g., "$5 off your next visit")\n• A free item with purchase (e.g., "Free appetizer with any entree")\n• A limited-time seasonal offer\n• A "new customer" special\n\nThe more compelling the offer, the more customers it drives through your door. Would you like to update your ad with a stronger call to action? Happy to help refine it.\n\n${rep}`;
    } else if (templateType === 'upsell') {
      const upgradeSize = adSize === 'Double' ? 'an even more prominent placement' : 'a Double-size ad';
      subject = `Maximize Your Results — Upgrade Option for ${biz}`;
      body = `Hi ${contact},\n\nYour ad for ${biz} is looking great! Quick question — have you considered upgrading to ${upgradeSize}?\n\nHere's why our most successful advertisers go bigger:\n• Double the visibility = double the impressions\n• Your ad stands out more on the receipt\n• Shoppers are more likely to notice a larger coupon\n• Better ROI per dollar spent\n\nThe upgrade is very affordable and the results speak for themselves. Want me to put together a quick comparison for you?\n\n${rep}`;
    } else if (templateType === 'expand') {
      const nearby = findNearbyStores(proof.store);
      let storeList = '';
      if (nearby.length > 0) {
        storeList = '\n\nHere are some stores near you that would be a great fit:\n' + nearby.map(s => `• ${s.GroceryChain} — ${s.Address}, ${s.City}, ${s.State} (${s.StoreName})`).join('\n');
      }
      subject = `Expand Your Reach — More Stores Near ${biz}`;
      body = `Hi ${contact},\n\nYour ad for ${biz} at ${store} looks fantastic! I wanted to reach out because we have several other stores nearby that could help you reach even more customers.\n\nMany of our most successful advertisers run their ads across multiple locations — it's the fastest way to build local brand recognition and drive new customers from different neighborhoods.${storeList}\n\nThe more locations you're in, the more people see your name — and the better your results. Want me to put together pricing for any of these?\n\n${rep}`;
    } else if (templateType === 'approve') {
      subject = `Your Ad Looks Great! — ${biz}`;
      body = `Hi ${contact},\n\nJust wanted to check in — your ad proof for ${biz} looks great!\n\nJust a friendly reminder to reply with your approval so we can get it into production. It's scheduled to be installed at ${store} in ${installMonth}.\n\nIf you have any last-minute tweaks, now's the time. Otherwise, we're good to go!\n\n${rep}`;
    }
    
    draftPreview = { subject, body, email: proof.client_email || '', proofId: proof.message_id };
  }

  function copyDraft() {
    if (!draftPreview) return;
    const text = `Subject: ${draftPreview.subject}\n\n${draftPreview.body}`;
    navigator.clipboard.writeText(text).then(() => {
      alert('✅ Email draft copied to clipboard!');
    }).catch(() => {
      // Fallback
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      alert('✅ Email draft copied to clipboard!');
    });
  }

  function openInEmailApp() {
    if (!draftPreview) return;
    window.open(`mailto:${draftPreview.email}?subject=${encodeURIComponent(draftPreview.subject)}&body=${encodeURIComponent(draftPreview.body)}`);
  }

  // Submit contract state
  let contractFile = null;
  let contractParsing = false;
  let contractParsed = null;
  let contractError = '';

  onMount(async () => {
    try {
      const [contractsRes, storesRes, renewalsRes, proofsRes] = await Promise.all([
        fetch(import.meta.env.BASE_URL + 'data/contracts.json'),
        fetch(import.meta.env.BASE_URL + 'data/stores.json'),
        fetch(import.meta.env.BASE_URL + 'data/pending_renewals.json').catch(() => ({ json: () => [] })),
        fetch(import.meta.env.BASE_URL + 'data/ad_proofs.json').catch(() => ({ json: () => [] }))
      ]);
      const data = await contractsRes.json();
      contracts = data.contracts || [];
      allStores = await storesRes.json().catch(() => []);
      pendingRenewals = await renewalsRes.json().catch(() => []);
      adProofs = await proofsRes.json().catch(() => []);
    } catch (err) {
      console.error('Failed to load data:', err);
    }
    loading = false;
  });

  // Get renewals scoped to rep (managers see all, reps see only their own)
  $: myRenewals = isManager
    ? pendingRenewals
    : pendingRenewals.filter(r => {
        const rn = (repName || '').toLowerCase();
        const repLower = (r.rep || '').toLowerCase();
        // Match first name or full name
        return repLower.includes(rn.split(' ')[0]) && (rn.split(' ').length < 2 || repLower.includes(rn.split(' ')[1] || ''));
      });

  $: renewalReps = [...new Set(myRenewals.map(r => r.rep))].sort();
  $: renewalCycles = [...new Set(myRenewals.map(r => r.cycle))].sort();
  $: renewalZones = [...new Set(myRenewals.map(r => r.zone).filter(Boolean))].sort();

  // Zone install day lookup from RTUI Zone Chart
  const ZONE_DAYS = {'01':1,'02':8,'03':26,'04':28,'05':25,'06':1,'07':7,'08':5,'09':14,'10':30,'11':25,'12':16,'13':20,'14':10,'15':18,'16':7,'17':20,'18':20,'19':8,'20':10,'21':16,'22':1,'23':12,'24':14,'25':23,'26':20,'27':25,'28':6,'29':6};

  function getRenewalDeadline(renewal) {
    // Deadline = (install_day + 3) in the month before the end date
    // Zone 7 example: B2 ends 5/1/2026, install day 7, deadline = April 10 (7+3)
    const storeId = renewal.store || '';
    const zoneMatch = storeId.match(/(\d{2})[A-Z]?-/) || (renewal.zone || '').match(/(\d{2})/);
    const zoneNum = zoneMatch ? zoneMatch[1] : '07';
    const installDay = ZONE_DAYS[zoneNum] || 7;
    const deadlineDay = installDay + 3;

    // Parse end date
    const endStr = renewal.endDate || '';
    const endParts = endStr.split('/');
    if (endParts.length < 3) return null;
    const endMonth = parseInt(endParts[0]) - 1; // 0-indexed
    const endYear = parseInt(endParts[2].length === 2 ? '20' + endParts[2] : endParts[2]);
    
    // Deadline is in the month BEFORE the end date
    let dlMonth = endMonth - 1;
    let dlYear = endYear;
    if (dlMonth < 0) { dlMonth = 11; dlYear--; }
    
    return new Date(dlYear, dlMonth, deadlineDay);
  }

  function formatDeadline(renewal) {
    const dl = getRenewalDeadline(renewal);
    if (!dl) return '';
    return dl.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function getDeadlineUrgency(renewal) {
    const dl = getRenewalDeadline(renewal);
    if (!dl) return '';
    const now = new Date();
    const daysLeft = Math.ceil((dl - now) / 86400000);
    if (daysLeft < 0) return 'overdue';
    if (daysLeft <= 7) return 'urgent';
    if (daysLeft <= 14) return 'soon';
    return 'ok';
  }
  
  $: filteredRenewals = myRenewals.filter(r => {
    if (renewalCycleFilter !== 'all' && r.cycle !== renewalCycleFilter) return false;
    if (renewalRepFilter !== 'all' && r.rep !== renewalRepFilter) return false;
    if (renewalZoneFilter !== 'all' && r.zone !== renewalZoneFilter) return false;
    if (renewalSearch) {
      const q = renewalSearch.toLowerCase();
      return (r.business || '').toLowerCase().includes(q) ||
        (r.contactName || '').toLowerCase().includes(q) ||
        (r.store || '').toLowerCase().includes(q) ||
        (r.rep || '').toLowerCase().includes(q) ||
        (r.category || '').toLowerCase().includes(q);
    }
    return true;
  });

  $: repName = $user?.name || $user?.first_name || '';

  // Format price: handles both number (4175.0) and string ("$4,175.00") formats
  function fmtPrice(v) {
    if (v == null || v === '' || v === 0 || v === '$ -' || v === '$-') return '$0';
    if (typeof v === 'number') return '$' + v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return String(v);
  }
  $: isManager = repName?.toLowerCase().includes('tyler') || repName?.toLowerCase().includes('rick leibowitz') || repName?.toLowerCase().includes('richard leibowitz');

  // Ad proofs scoped to rep (managers see all, reps see only their own)
  $: myAdProofs = isManager
    ? adProofs
    : adProofs.filter(p => {
        const repLower = (repName || '').toLowerCase();
        return p.recipients?.some(email => {
          const mapped = (p.reps || []).find(r => r.email === email);
          if (mapped) return mapped.name.toLowerCase().includes(repLower.split(' ')[0]);
          return false;
        });
      });

  $: proofZones = [...new Set(myAdProofs.map(p => p.zone).filter(Boolean))].sort();
  $: proofReps = [...new Set(myAdProofs.flatMap(p => (p.reps || []).map(r => r.name)).filter(Boolean))].sort();
  $: proofStores = [...new Set(myAdProofs.map(p => p.store?.replace(/^[>\s]+/, '')).filter(Boolean))].sort();
  
  $: filteredProofs = myAdProofs.filter(p => {
    if (proofZoneFilter !== 'all' && p.zone !== proofZoneFilter) return false;
    if (proofRepFilter !== 'all' && !(p.reps || []).some(r => r.name === proofRepFilter)) return false;
    if (proofStoreFilter !== 'all' && !p.store?.includes(proofStoreFilter)) return false;
    if (proofSearch) {
      const q = proofSearch.toLowerCase();
      return (p.client_name || '').toLowerCase().includes(q) ||
        (p.contract_number || '').toLowerCase().includes(q) ||
        (p.store || '').toLowerCase().includes(q) ||
        (p.location || '').toLowerCase().includes(q);
    }
    return true;
  });

  let sortBy = 'date-desc'; // date-desc, date-asc, rep, amount-desc, amount-asc, name

  // My Customers = closed deals for this rep (or all for manager)
  $: myCustomers = isManager
    ? contracts
    : contracts.filter(c => {
        const rep = (c.sales_rep || '').toLowerCase();
        return rep.includes((repName || '').toLowerCase().split(' ')[0]);
      });

  // My Sales = same data but focused on amounts
  $: mySales = myCustomers;

  $: totalRevenue = mySales.reduce((sum, c) => sum + (c.total_amount || 0), 0);

  $: filteredCustomers = (() => {
    let list = searchQuery
      ? myCustomers.filter(c =>
          (c.business_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
          (c.contact_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
          (c.store_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
          (c.sales_rep || '').toLowerCase().includes(searchQuery.toLowerCase())
        )
      : [...myCustomers];
    
    // Sort
    if (sortBy === 'date-desc') {
      list.sort((a, b) => (b.date || '').localeCompare(a.date || ''));
    } else if (sortBy === 'date-asc') {
      list.sort((a, b) => (a.date || '').localeCompare(b.date || ''));
    } else if (sortBy === 'rep') {
      list.sort((a, b) => (a.sales_rep || '').localeCompare(b.sales_rep || ''));
    } else if (sortBy === 'amount-desc') {
      list.sort((a, b) => (b.total_amount || 0) - (a.total_amount || 0));
    } else if (sortBy === 'amount-asc') {
      list.sort((a, b) => (a.total_amount || 0) - (b.total_amount || 0));
    } else if (sortBy === 'name') {
      list.sort((a, b) => (a.business_name || '').localeCompare(b.business_name || ''));
    }
    return list;
  })();

  // Calculate upcoming events for a client based on contract data
  function getClientEvents(contract) {
    const events = [];
    const today = new Date();
    const contractDate = contract.date ? new Date(contract.date) : null;
    
    if (!contractDate) return events;

    // Install date: snap to zone-specific install day of month
    // Zone install day lookup from RTUI Zone Chart
    const ZONE_DAYS = {'01':1,'02':8,'03':26,'04':28,'05':25,'06':1,'07':7,'08':5,'09':14,'10':30,'11':25,'12':16,'13':20,'14':10,'15':18,'16':7,'17':20,'18':20,'19':8,'20':10,'21':16,'22':1,'23':12,'24':14,'25':23,'26':20,'27':25,'28':6,'29':6};
    const storeId = contract.storeId || contract.store || '';
    const zoneMatch = storeId.match(/(\d{2})[A-Z]?-/);
    const zoneDay = zoneMatch ? (ZONE_DAYS[zoneMatch[1]] || 7) : 7;
    
    const installDate = new Date(contractDate);
    installDate.setDate(installDate.getDate() + 30);
    // Snap to zone-specific install day
    const installMonth = installDate.getDate() > zoneDay ? installDate.getMonth() + 1 : installDate.getMonth();
    const installLaunch = new Date(installDate.getFullYear(), installMonth, zoneDay);
    if (installLaunch >= today) {
      events.push({ type: '📦', label: 'Install', date: installLaunch });
    }

    // Audit window: 45 days after install
    const auditDate = new Date(installLaunch);
    auditDate.setDate(auditDate.getDate() + 45);
    if (auditDate >= today) {
      events.push({ type: '🔍', label: 'Audit Due', date: auditDate });
    }

    // Renewal conversation: 10 months after contract
    const renewalDate = new Date(contractDate);
    renewalDate.setMonth(renewalDate.getMonth() + 10);
    if (renewalDate >= today) {
      events.push({ type: '🔄', label: 'Renewal Conversation', date: renewalDate });
    }

    // Contract end: 12 months after contract
    const endDate = new Date(contractDate);
    endDate.setMonth(endDate.getMonth() + 12);
    if (endDate >= today) {
      events.push({ type: '📋', label: 'Contract Ends', date: endDate });
    }

    return events.sort((a, b) => a.date - b.date);
  }

  function formatDate(d) {
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function daysFromNow(d) {
    const diff = Math.ceil((d - new Date()) / (1000 * 60 * 60 * 24));
    if (diff === 0) return 'Today';
    if (diff === 1) return 'Tomorrow';
    if (diff < 0) return `${Math.abs(diff)}d overdue`;
    if (diff <= 7) return `In ${diff} days`;
    if (diff <= 30) return `In ${Math.ceil(diff / 7)} weeks`;
    return `In ${Math.ceil(diff / 30)} months`;
  }

  function getNearbyStores(contract) {
    const storeNum = contract.store_number || '';
    // Find the customer's store
    const currentStore = allStores.find(s => s.StoreName === storeNum || (storeNum && s.StoreName?.includes(storeNum)));
    if (!currentStore) return [];

    // Find other stores in the same city
    return allStores.filter(s => 
      s.StoreName !== currentStore.StoreName &&
      s.City === currentStore.City &&
      s.State === currentStore.State
    ).slice(0, 8);
  }

  function toggleExpand(idx) {
    expandedCustomer = expandedCustomer === idx ? null : idx;
    emailDraft = null;
  }

  function showEmailDraft(contract, templateType) {
    const biz = contract.business_name || 'your business';
    const owner = contract.contact_name || '';
    const rep = repName || 'Your IndoorMedia Rep';
    const store = contract.store_name || '';

    const templates = {
      kickoff: {
        subject: `What's Next — ${biz} & IndoorMedia`,
        body: `Hi ${owner},\n\nWelcome to IndoorMedia! I wanted to reach out and let you know what happens next with your advertising at ${store}.\n\nYour ad will be printed and installed during the next cycle. Once it's live, I'll check in to make sure everything looks great.\n\nIn the meantime, if you have any questions or want to make changes to your ad, just let me know.\n\nLooking forward to a great partnership!\n\nBest,\n${rep}\nIndoorMedia`
      },
      checkin: {
        subject: `Checking in — ${biz} & IndoorMedia`,
        body: `Hi ${owner},\n\nI wanted to check in and see how things are going with your register tape ad at ${store}.\n\nHave you noticed any new customers mentioning the ad? Many of our advertisers see results within the first few weeks — I'd love to hear your experience.\n\nIf you'd like to make any changes for the next cycle, now's a great time to let me know.\n\nBest,\n${rep}\nIndoorMedia`
      },
      upsell: {
        subject: `Expansion Opportunity — ${biz}`,
        body: `Hi ${owner},\n\nYour ad at ${store} has been running great, and I wanted to share some ways to expand your reach:\n\n• Add nearby stores — reach even more shoppers in your area\n• DigitalBoost — geofenced digital ads near the store (360K total impressions/pin)\n• Double Ad — upgrade to a larger ad for more visibility\n• Cartvertising — ads on shopping carts for maximum exposure\n\nWould you be open to a quick chat about growing your presence?\n\nBest,\n${rep}\nIndoorMedia`
      },
      renewal: {
        subject: `Time to Renew — ${biz} & IndoorMedia`,
        body: `Hi ${owner},\n\nYour advertising contract at ${store} is coming up for renewal. I wanted to touch base early so we can ensure there's no gap in your coverage.\n\nRenewing now locks in your current rate and keeps your ad running without interruption. Many of our advertisers also use renewal time to:\n\n• Add additional stores\n• Upgrade to a Double Ad\n• Bundle with digital products for better results\n\nCan we set up a quick call this week to discuss?\n\nBest,\n${rep}\nIndoorMedia`
      },
      proofReview: {
        subject: `Ad Proof Review & Campaign Optimization — ${biz}`,
        body: `Hi ${owner},\n\nSydney, our graphic design coordinator, recently sent over your current ad proof and I wanted to check whether you'd like any updates or changes before the next production cycle.\n\nThis is a good time to consider testing a more aggressive offer. Stronger coupons consistently increase response rates, bring in more first-time customers, and help accelerate repeat visits. Even small adjustments—like a higher-value incentive or bundle-style offer—can materially improve results.\n\nThere are a few additional ways we can expand your reach right now:\n\n1. Add nearby stores\nPlacing your message in additional locations increases frequency and exposure within the local area.\n\n2. Extend your campaign with Digital Boost (or add another pin drop to get more impressions)\nAdditional geotargeted impressions reinforce your in-store print visibility and keeps your business top-of-mind after customers leave the grocery store.\n\n3. Activate Loyalty Boost (new)\nOur Loyalty Boost program helps convert first-time visitors into repeat customers and strengthens long-term retention.\n\nHere's a quick overview:\nhttps://www.indoormedia.com/loyalty-and-rewards-program/\n\nIf you're open to testing any improvements—or just want a second set of eyes on your offer strategy—I'm always available to review options with you and help make sure your campaign is performing at the highest level.\n\nIf you haven't already, please let Sydney know what changes (if any) you'd like to make.\n\nAll the best,\n${rep}`
      }
    };

    emailDraft = templates[templateType] || templates.kickoff;
  }

  function copyEmail() {
    if (!emailDraft) return;
    const text = `Subject: ${emailDraft.subject}\n\n${emailDraft.body}`;
    navigator.clipboard.writeText(text).then(() => {
      emailDraft = { ...emailDraft, copied: true };
      setTimeout(() => { emailDraft = { ...emailDraft, copied: false }; }, 2000);
    });
  }

  async function handleContractUpload(event) {
    const file = event.target.files[0];
    if (!file || file.type !== 'application/pdf') {
      contractError = 'Please select a PDF file';
      return;
    }
    
    contractFile = file;
    contractParsing = true;
    contractError = '';
    contractParsed = null;

    try {
      const arrayBuffer = await file.arrayBuffer();
      const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
      let fullText = '';
      
      for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const content = await page.getTextContent();
        fullText += content.items.map(item => item.str).join(' ') + '\n';
      }
      
      // Parse contract fields
      const parsed = {};
      
      // Contract number
      let m = fullText.match(/Contract\s*#:\s*(\S+)/);
      parsed.contract_number = m ? m[1] : '';
      
      // Date
      m = fullText.match(/Contract\s*#:.*?(\d{1,2}\/\d{1,2}\/\d{4})/);
      if (m) {
        const parts = m[1].split('/');
        parsed.date = `${parts[2]}-${parts[0].padStart(2,'0')}-${parts[1].padStart(2,'0')} 00:00`;
        parsed.payment_date = m[1];
      }
      
      // Sales rep
      m = fullText.match(/Sales Representative:\s*([^|]+)/);
      parsed.sales_rep = m ? m[1].trim() : '';
      
      // Business name from Advertiser's Business Name
      m = fullText.match(/Advertiser's Business Name:\s*([^\n]+?)(?:Advertiser|$)/);
      parsed.business_name = m ? m[1].trim() : '';
      
      // Contact name
      m = fullText.match(/Advertiser's Printed Name:\s*([^\n]+?)(?:Advertiser|$)/);
      parsed.contact_name = m ? m[1].trim() : '';
      
      // Email (first non-indoormedia email)
      const emails = fullText.match(/[\w.+-]+@[\w.-]+\.\w+/g) || [];
      parsed.contact_email = emails.find(e => !e.includes('indoormedia')) || '';
      
      // Phone
      m = fullText.match(/\(?(\d{3})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})/);
      parsed.contact_phone = m ? `(${m[1]}) ${m[2]}-${m[3]}` : '';
      
      // Contract total
      m = fullText.match(/Contract Total\s*\$?([\d,]+\.?\d*)/);
      parsed.total_amount = m ? parseFloat(m[1].replace(',', '')) : 0;
      if (!parsed.total_amount) {
        m = fullText.match(/Net Price\s*\$?([\d,]+\.?\d*)/);
        parsed.total_amount = m ? parseFloat(m[1].replace(',', '')) : 0;
      }
      
      // Store info
      m = fullText.match(/Register Tape\s*([\w\s]+-\d+)/);
      if (m) {
        const storeParts = m[1].trim().split('-');
        parsed.store_name = storeParts[0].trim();
        parsed.store_number = storeParts[storeParts.length - 1];
      } else {
        parsed.store_name = '';
        parsed.store_number = '';
      }
      
      // Product type
      m = fullText.match(/(Single|Double)\s+Ad/);
      parsed.product_description = m ? `${m[1]} Ad` : '';
      
      // Address
      m = fullText.match(/(\d+\s+[^,]+,\s*[^,]+,?\s*\w{2}\s+\d{5})/);
      parsed.address = m ? m[1].trim() : '';
      
      parsed.extracted_at = new Date().toISOString();
      contractParsed = parsed;
      
    } catch (err) {
      console.error('PDF parse error:', err);
      contractError = 'Failed to read PDF. Make sure it\'s an IndoorMedia contract.';
    } finally {
      contractParsing = false;
    }
  }

  function submitContract() {
    if (!contractParsed) return;
    
    // Save to localStorage
    const submitted = JSON.parse(localStorage.getItem('submitted_contracts') || '[]');
    submitted.push({
      ...contractParsed,
      submittedBy: $user?.name || 'Unknown',
      submittedAt: new Date().toISOString()
    });
    localStorage.setItem('submitted_contracts', JSON.stringify(submitted));
    
    // Also add to contracts list so it shows immediately
    contracts = [contractParsed, ...contracts];
    
    // Reset
    contractParsed = null;
    contractFile = null;
    contractError = '';
    view = 'main';
  }

  function goBack() {
    view = 'main';
    searchQuery = '';
    expandedCustomer = null;
    emailDraft = null;
    contractParsed = null;
    contractFile = null;
    contractError = '';
  }
</script>

<div class="clients-container">
  {#if view === 'main'}
    <h2>Clients</h2>
    <p class="subtitle">Manage customers & sales</p>

    <div class="button-grid">
      <button class="main-btn" on:click={() => view = 'customers'}>
        <div class="btn-icon">👥</div>
        <div class="btn-text">My Customers</div>
        <div class="btn-desc">{myCustomers.length} closed deals</div>
      </button>

      <button class="main-btn" on:click={() => view = 'sales'}>
        <div class="btn-icon">💳</div>
        <div class="btn-text">My Sales</div>
        <div class="btn-desc">${totalRevenue.toLocaleString()} total</div>
      </button>

      <button class="main-btn" on:click={() => view = 'submit-contract'}>
        <div class="btn-icon">📄</div>
        <div class="btn-text">Submit Contract</div>
        <div class="btn-desc">Upload signed agreement</div>
      </button>

      <button class="main-btn" on:click={() => view = 'renewals'}>
        <div class="btn-icon">🔄</div>
        <div class="btn-text">Pending Renewals</div>
        <div class="btn-desc">{myRenewals.length} accounts</div>
      </button>

      <button class="main-btn" on:click={() => view = 'ad-proofs'}>
        <div class="btn-icon">🎨</div>
        <div class="btn-text">Ad Proofs</div>
        <div class="btn-desc">{myAdProofs.length} proofs</div>
      </button>
    </div>

  {/if}

  <!-- My Customers -->
  {#if view === 'customers'}
    <button class="back-btn" on:click={goBack}>&larr; Back</button>
    <h2>My Customers</h2>
    <p class="subtitle">{myCustomers.length} closed deals</p>

    <div class="search-box">
      <input type="text" placeholder="Search customers..." bind:value={searchQuery} />
    </div>

    <div class="sort-bar">
      <span class="sort-label">Sort:</span>
      <button class="sort-btn" class:active={sortBy === 'date-desc'} on:click={() => sortBy = 'date-desc'}>Newest</button>
      <button class="sort-btn" class:active={sortBy === 'date-asc'} on:click={() => sortBy = 'date-asc'}>Oldest</button>
      <button class="sort-btn" class:active={sortBy === 'rep'} on:click={() => sortBy = 'rep'}>Rep</button>
      <button class="sort-btn" class:active={sortBy === 'amount-desc'} on:click={() => sortBy = 'amount-desc'}>$$$ ↓</button>
      <button class="sort-btn" class:active={sortBy === 'amount-asc'} on:click={() => sortBy = 'amount-asc'}>$$$ ↑</button>
      <button class="sort-btn" class:active={sortBy === 'name'} on:click={() => sortBy = 'name'}>A-Z</button>
    </div>

    {#if loading}
      <p>Loading...</p>
    {:else if filteredCustomers.length === 0}
      <p class="empty">No customers found. Sales sync from Gmail contracts nightly.</p>
    {:else}
      <div class="customer-list">
        {#each filteredCustomers as c, i}
          {@const clientEvents = getClientEvents(c)}
          {@const nearbyStores = getNearbyStores(c)}
          <div class="customer-card">
            <div class="card-header">
              <h4>{c.business_name || 'Unknown'}</h4>
              <span class="amount">${(c.total_amount || 0).toLocaleString()}</span>
            </div>
            <p class="contact">{c.contact_name || ''}</p>
            {#if c.contact_phone}
              <p class="phone">📞 {c.contact_phone}</p>
            {/if}
            {#if c.contact_email}
              <p class="email">📧 {c.contact_email}</p>
            {/if}
            <div class="card-meta">
              <span>🏪 {c.store_name || ''} #{c.store_number || ''}</span>
              <span>📋 {c.product_description || ''}</span>
              <span>📅 {c.date ? c.date.split(' ')[0] : ''}</span>
            </div>
            {#if c.address}
              <p class="address">📍 {c.address}</p>
            {/if}
            {#if isManager && c.sales_rep}
              <p class="rep-tag">Rep: {c.sales_rep}</p>
            {/if}
            {#if clientEvents.length > 0}
              <div class="client-events">
                <p class="events-label">Upcoming</p>
                {#each clientEvents as evt}
                  <div class="client-event" class:soon={daysFromNow(evt.date).startsWith('In') && parseInt(daysFromNow(evt.date).match(/\d+/)) <= 7 || daysFromNow(evt.date) === 'Today' || daysFromNow(evt.date) === 'Tomorrow'} class:overdue={daysFromNow(evt.date).includes('overdue')}>
                    <span class="evt-icon">{evt.type}</span>
                    <span class="evt-label">{evt.label}</span>
                    <span class="evt-date">{formatDate(evt.date)} · {daysFromNow(evt.date)}</span>
                  </div>
                {/each}
              </div>
            {/if}
            <div class="card-actions">
              {#if c.contact_phone}
                <a href="tel:{c.contact_phone}" class="action-btn call">📞 Call</a>
              {/if}
              {#if c.contact_email}
                <a href="mailto:{c.contact_email}" class="action-btn">📧 Email</a>
              {/if}
              <button class="action-btn expand-btn" on:click={() => toggleExpand(i)}>
                {expandedCustomer === i ? '▲ Less' : '🚀 More'}
              </button>
            </div>

            {#if expandedCustomer === i}
              <div class="expanded-section">
                <!-- Email Templates -->
                <div class="section-header">✉️ Draft Email</div>
                <div class="email-btns">
                  <button class="email-tmpl-btn" on:click={() => showEmailDraft(c, 'kickoff')}>🚀 Kickoff</button>
                  <button class="email-tmpl-btn" on:click={() => showEmailDraft(c, 'checkin')}>✅ Check-in</button>
                  <button class="email-tmpl-btn" on:click={() => showEmailDraft(c, 'proofReview')}>🎨 Proof Review</button>
                  <button class="email-tmpl-btn" on:click={() => showEmailDraft(c, 'upsell')}>⬆️ Upsell</button>
                  <button class="email-tmpl-btn" on:click={() => showEmailDraft(c, 'renewal')}>🔄 Renewal</button>
                </div>

                {#if emailDraft}
                  <div class="draft-box">
                    <p class="draft-subject"><strong>Subject:</strong> {emailDraft.subject}</p>
                    <pre class="draft-body">{emailDraft.body}</pre>
                    <button class="copy-btn" on:click={copyEmail}>
                      {emailDraft.copied ? '✅ Copied!' : '📋 Copy Email'}
                    </button>
                    {#if c.contact_email}
                      <a href="mailto:{c.contact_email}?subject={encodeURIComponent(emailDraft.subject)}&body={encodeURIComponent(emailDraft.body)}" class="send-btn">📤 Open in Mail</a>
                    {/if}
                  </div>
                {/if}

                <!-- Expansion Opportunities -->
                <div class="section-header">🚀 Expansion Opportunities</div>
                
                {#if nearbyStores.length > 0}
                  <p class="expand-label">🏪 Nearby Stores in {nearbyStores[0]?.City}</p>
                  <div class="nearby-list">
                    {#each nearbyStores as ns}
                      <div class="nearby-store">
                        <span class="ns-name">{ns.GroceryChain}</span>
                        <span class="ns-num">{ns.StoreName}</span>
                      </div>
                    {/each}
                  </div>
                {:else}
                  <p class="expand-note">No other stores found in this city</p>
                {/if}

                <p class="expand-label">📦 Product Upsells</p>
                <div class="upsell-list">
                  <div class="upsell-item">🚀 <strong>DigitalBoost</strong> — Geofence ads (360K total impressions/pin)</div>
                  <div class="upsell-item">📍 <strong>FindLocal</strong> — SEO & listings ($695)</div>
                  <div class="upsell-item">⭐ <strong>ReviewBoost</strong> — Automated reviews ($695)</div>
                  <div class="upsell-item">💎 <strong>LoyaltyBoost</strong> — Loyalty program ($3,600/yr)</div>
                  <div class="upsell-item">🛒 <strong>Cartvertising</strong> — Cart ads ($2,995+)</div>
                  <div class="upsell-item">📰 <strong>Double Ad</strong> — Upgrade ad size</div>
                </div>
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  {/if}

  <!-- Pending Renewals -->
  <!-- Pending Renewals -->
  {#if view === 'renewals'}
    <button class="back-btn" on:click={goBack}>&larr; Back</button>
    <h2>🔄 Pending Renewals</h2>
    <p class="subtitle">{filteredRenewals.length} of {pendingRenewals.length} accounts — ${pendingRenewals.reduce((sum, r) => sum + (typeof r.contractPrice === 'number' ? r.contractPrice : parseFloat(String(r.contractPrice || '0').replace(/[$,]/g, '')) || 0), 0).toLocaleString()} total value</p>

    <input type="text" class="search-input" placeholder="Search by business, rep, store, category..." bind:value={renewalSearch} />

    <div class="renewal-filters">
      <select bind:value={renewalZoneFilter}>
        <option value="all">All Zones</option>
        {#each renewalZones as zone}
          <option value={zone}>{zone} ({myRenewals.filter(r => r.zone === zone).length})</option>
        {/each}
      </select>

      <select bind:value={renewalRepFilter}>
        <option value="all">All Reps ({pendingRenewals.length})</option>
        {#each renewalReps as rep}
          <option value={rep}>{rep} ({myRenewals.filter(r => r.rep === rep).length})</option>
        {/each}
      </select>

      <select bind:value={renewalCycleFilter}>
        <option value="all">All Cycles</option>
        {#each renewalCycles as cycle}
          <option value={cycle}>{cycle} ({myRenewals.filter(r => r.cycle === cycle).length})</option>
        {/each}
      </select>
    </div>

    <div class="select-bar">
      <button class="select-toggle" class:active={selectMode} on:click={() => { selectMode = !selectMode; if (!selectMode) selectedRenewals = new Set(); }}>
        {selectMode ? '✕ Cancel' : '☑️ Select'}
      </button>
      {#if selectMode}
        <button class="select-all-btn" on:click={selectAll}>
          {selectedRenewals.size === filteredRenewals.length ? 'Deselect All' : 'Select All'} ({selectedRenewals.size})
        </button>
        <button class="export-btn" on:click={exportSelectedPdf} disabled={selectedRenewals.size === 0}>
          📄 Export PDF ({selectedRenewals.size})
        </button>
      {/if}
    </div>

    {#if filteredRenewals.length === 0}
      <p class="empty">No renewals match your filters.</p>
    {:else}
      <div class="renewal-list">
        {#each filteredRenewals as renewal}
          <div class="renewal-card" class:selected={selectedRenewals.has(renewal.accountNumber)} on:click={() => { if (selectMode) { toggleSelect(renewal.accountNumber); } else { expandedRenewal = expandedRenewal === renewal.accountNumber ? null : renewal.accountNumber; } }}>
            {#if selectMode}
              <div class="select-check">{selectedRenewals.has(renewal.accountNumber) ? '☑️' : '⬜'}</div>
            {/if}
            <div style="flex:1; min-width:0;">
            <div class="renewal-header">
              <div class="renewal-biz">
                <h4>{renewal.business}</h4>
                <span class="renewal-cat">{renewal.category || 'N/A'}</span>
              </div>
              <div class="renewal-meta">
                <span class="renewal-cycle">{renewal.cycle}</span>
                <span class="renewal-price">{fmtPrice(renewal.contractPrice)}</span>
              </div>
            </div>
            <div class="renewal-sub">
              <span>🏪 {renewal.store}</span>
              <span>👤 {renewal.rep}</span>
              <span>📅 Ends: {renewal.endDate || '—'}</span>
            </div>
            {#if formatDeadline(renewal)}
              <div class="renewal-deadline" class:overdue={getDeadlineUrgency(renewal) === 'overdue'} class:urgent={getDeadlineUrgency(renewal) === 'urgent'} class:soon={getDeadlineUrgency(renewal) === 'soon'}>
                ⏰ Renewal due: <strong>{formatDeadline(renewal)}</strong>
                {#if getDeadlineUrgency(renewal) === 'overdue'} — OVERDUE
                {:else if getDeadlineUrgency(renewal) === 'urgent'} — Due this week!
                {:else if getDeadlineUrgency(renewal) === 'soon'} — Due soon
                {/if}
              </div>
            {/if}

            {#if expandedRenewal === renewal.accountNumber}
              <div class="renewal-details">
                <div class="detail-grid">
                  <div class="detail-item">
                    <span class="detail-label">Contact</span>
                    <span class="detail-value">{renewal.contactName || 'N/A'}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Phone</span>
                    <span class="detail-value">{renewal.phone || 'N/A'}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Email</span>
                    <span class="detail-value">{renewal.email || 'N/A'}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Ad Size</span>
                    <span class="detail-value">{renewal.adSize || 'N/A'}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Contract #</span>
                    <span class="detail-value">{renewal.contractNumber || 'N/A'}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Account #</span>
                    <span class="detail-value">{renewal.accountNumber || 'N/A'}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Cycle Revenue</span>
                    <span class="detail-value">{fmtPrice(renewal.cycleRevenue)}</span>
                  </div>
                  {#if renewal.lateBalance && renewal.lateBalance !== 0}
                  <div class="detail-item warning">
                    <span class="detail-label">⚠️ Late Balance</span>
                    <span class="detail-value">{fmtPrice(renewal.lateBalance)}</span>
                  </div>
                  {/if}
                  <div class="detail-item">
                    <span class="detail-label">Run Length</span>
                    <span class="detail-value">{renewal.runLength ? renewal.runLength + ' quarters' : 'N/A'}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Address</span>
                    <span class="detail-value">{renewal.address || ''}{renewal.city ? ', ' + renewal.city : ''}{renewal.state ? ', ' + renewal.state : ''} {renewal.zip || ''}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Rep Status</span>
                    <span class="detail-value" class:status-active={renewal.repStatus === 'Active'} class:status-inactive={renewal.repStatus === 'Inactive'}>{renewal.repStatus || 'N/A'}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Start Date</span>
                    <span class="detail-value">{renewal.startDate || 'N/A'}</span>
                  </div>
                </div>

                <div class="renewal-actions">
                  {#if renewal.phone}
                    <a href="tel:{renewal.phone}" class="action-btn call-btn">📞 Call</a>
                  {/if}
                  {#if renewal.email}
                    <a href="mailto:{renewal.email}?subject=Renewal%20—%20{encodeURIComponent(renewal.business)}" class="action-btn email-btn">✉️ Email</a>
                  {/if}
                </div>
              </div>
            {/if}
            </div>
          </div>
        {/each}
      </div>
    {/if}
  {/if}

  {#if view === 'submit-contract'}
    <button class="back-btn" on:click={goBack}>&larr; Back</button>
    <h2>📄 Submit Contract</h2>
    <p class="subtitle">Upload a signed IndoorMedia agreement</p>

    <div class="upload-area">
      <input type="file" accept=".pdf" on:change={handleContractUpload} id="contract-upload" />
      <label for="contract-upload" class="upload-label">
        {#if contractParsing}
          ⏳ Reading PDF...
        {:else if contractFile}
          📄 {contractFile.name}
        {:else}
          📎 Tap to select PDF
        {/if}
      </label>
    </div>

    {#if contractError}
      <p class="error-text">{contractError}</p>
    {/if}

    {#if contractParsed}
      <div class="parsed-card">
        <h3>✅ Contract Parsed</h3>
        
        <div class="parsed-field">
          <span class="field-label">Contract #</span>
          <span class="field-value">{contractParsed.contract_number || '—'}</span>
        </div>
        <div class="parsed-field">
          <span class="field-label">Business</span>
          <span class="field-value">{contractParsed.business_name || '—'}</span>
        </div>
        <div class="parsed-field">
          <span class="field-label">Contact</span>
          <span class="field-value">{contractParsed.contact_name || '—'}</span>
        </div>
        <div class="parsed-field">
          <span class="field-label">Email</span>
          <span class="field-value">{contractParsed.contact_email || '—'}</span>
        </div>
        <div class="parsed-field">
          <span class="field-label">Phone</span>
          <span class="field-value">{contractParsed.contact_phone || '—'}</span>
        </div>
        <div class="parsed-field">
          <span class="field-label">Sales Rep</span>
          <span class="field-value">{contractParsed.sales_rep || '—'}</span>
        </div>
        <div class="parsed-field">
          <span class="field-label">Store</span>
          <span class="field-value">{contractParsed.store_name} #{contractParsed.store_number}</span>
        </div>
        <div class="parsed-field">
          <span class="field-label">Product</span>
          <span class="field-value">{contractParsed.product_description || '—'}</span>
        </div>
        <div class="parsed-field highlight">
          <span class="field-label">Total</span>
          <span class="field-value">${(contractParsed.total_amount || 0).toLocaleString()}</span>
        </div>
        <div class="parsed-field">
          <span class="field-label">Date</span>
          <span class="field-value">{contractParsed.payment_date || '—'}</span>
        </div>

        <button class="submit-btn" on:click={submitContract}>
          ✅ Confirm & Submit
        </button>
        <button class="cancel-btn" on:click={() => { contractParsed = null; contractFile = null; }}>
          ✏️ Try Different PDF
        </button>
      </div>
    {/if}
  {/if}

  <!-- My Sales -->
  {#if view === 'sales'}
    <button class="back-btn" on:click={goBack}>&larr; Back</button>
    <h2>My Sales</h2>
    <p class="subtitle">{mySales.length} deals &bull; ${totalRevenue.toLocaleString()} total</p>

    {#if loading}
      <p>Loading...</p>
    {:else if mySales.length === 0}
      <p class="empty">No sales found. Sales data syncs from Gmail contracts nightly at 8 PM.</p>
    {:else}
      <div class="sales-summary">
        <div class="stat">
          <span class="stat-value">{mySales.length}</span>
          <span class="stat-label">Deals</span>
        </div>
        <div class="stat">
          <span class="stat-value">${totalRevenue.toLocaleString()}</span>
          <span class="stat-label">Revenue</span>
        </div>
        <div class="stat">
          <span class="stat-value">${mySales.length ? Math.round(totalRevenue / mySales.length).toLocaleString() : 0}</span>
          <span class="stat-label">Avg Deal</span>
        </div>
      </div>

      <div class="sales-list">
        {#each mySales.sort((a, b) => (b.date || '').localeCompare(a.date || '')) as sale}
          <div class="sale-row">
            <div class="sale-info">
              <span class="sale-name">{sale.business_name || 'Unknown'}</span>
              <span class="sale-meta">{sale.store_name || ''} &bull; {sale.product_description || ''} &bull; {sale.date ? sale.date.split(' ')[0] : ''}</span>
            </div>
            <span class="sale-amount">${(sale.total_amount || 0).toLocaleString()}</span>
          </div>
        {/each}
      </div>
    {/if}
  {/if}

  <!-- Ad Proofs -->
  {#if view === 'ad-proofs'}
    <button class="back-btn" on:click={goBack}>&larr; Back</button>
    <h2>🎨 Ad Proofs</h2>
    <p class="subtitle">{filteredProofs.length} proof{filteredProofs.length !== 1 ? 's' : ''}</p>

    <div class="filter-bar">
      <input type="text" placeholder="Search client, contract #, store..." bind:value={proofSearch} class="search-input" />
    </div>
    <div class="filter-row">
      <select bind:value={proofZoneFilter} class="filter-select">
        <option value="all">All Zones</option>
        {#each proofZones as zone}
          <option value={zone}>{zone}</option>
        {/each}
      </select>
      <select bind:value={proofRepFilter} class="filter-select">
        <option value="all">All Reps</option>
        {#each proofReps as rep}
          <option value={rep}>{rep}</option>
        {/each}
      </select>
      <select bind:value={proofStoreFilter} class="filter-select">
        <option value="all">All Stores</option>
        {#each proofStores as store}
          <option value={store}>{store.length > 40 ? store.substring(0, 40) + '...' : store}</option>
        {/each}
      </select>
    </div>

    <div class="proofs-list">
      {#each filteredProofs as proof}
        <div class="proof-card" class:expanded={expandedProof === proof.message_id}>
          <button class="proof-header" on:click={() => expandedProof = expandedProof === proof.message_id ? null : proof.message_id}>
            <div class="proof-info">
              <h4>{proof.client_name || 'Unknown'}</h4>
              <p class="proof-meta">
                {proof.contract_number || ''} · {proof.zone} {proof.cycle} · {proof.ad_size || ''} Ad
              </p>
              <p class="proof-store">{proof.store || ''}</p>
              <p class="proof-date">{proof.date || ''}</p>
            </div>
            <span class="expand-arrow">{expandedProof === proof.message_id ? '▼' : '▶'}</span>
          </button>
          
          {#if expandedProof === proof.message_id}
            <div class="proof-detail">
              <div class="proof-fields">
                <div class="field-row">
                  <span class="field-label">Contract</span>
                  <span class="field-value">{proof.contract_number}</span>
                </div>
                <div class="field-row">
                  <span class="field-label">Ad Size</span>
                  <span class="field-value">{proof.ad_size || 'N/A'}</span>
                </div>
                <div class="field-row">
                  <span class="field-label">Store</span>
                  <span class="field-value">{proof.store || 'N/A'}</span>
                </div>
                <div class="field-row">
                  <span class="field-label">Install</span>
                  <span class="field-value">{proof.install_month || 'N/A'}</span>
                </div>
                <div class="field-row">
                  <span class="field-label">Runs</span>
                  <span class="field-value">{proof.run_months || 'N/A'}</span>
                </div>
                {#if proof.review_deadline}
                  <div class="field-row">
                    <span class="field-label">Deadline</span>
                    <span class="field-value" style="color: #cc0000; font-weight: 700;">{proof.review_deadline}</span>
                  </div>
                {/if}
                <div class="field-row">
                  <span class="field-label">Zone</span>
                  <span class="field-value">{proof.zone} · {proof.cycle}</span>
                </div>
                {#if proof.reps?.length > 0}
                  <div class="field-row">
                    <span class="field-label">Rep(s)</span>
                    <span class="field-value">{proof.reps.map(r => r.name).join(', ')}</span>
                  </div>
                {/if}
              </div>

              {#if proof.image_url}
                <div class="proof-image-container">
                  <h4>Ad Proof Image</h4>
                  <img src={proof.image_url} alt="Ad proof for {proof.client_name}" class="proof-image" loading="lazy" referrerpolicy="no-referrer" on:error={(e) => { e.target.style.display='none'; }} />
                  <a href={proof.image_url} target="_blank" class="proof-image-fallback">📷 Tap to view ad proof image</a>
                  <a href={proof.image_url} target="_blank" class="view-full-btn">View Full Size ↗</a>
                </div>
              {/if}

              <!-- Contact Actions -->
              {#if proof.client_email || proof.contact_name}
                <div class="proof-contact-actions">
                  <h4>📬 Contact Customer</h4>
                  {#if proof.client_email}
                    <p class="client-email-display">✉️ {proof.client_email}</p>
                  {/if}

                  <div class="template-section">
                    <h5>Quick Templates</h5>
                    <div class="template-list">
                      <button class="template-btn" on:click={() => showDraft(proof, 'ready')}>
                        🎨 Your Ad Design is Ready!
                        <span class="template-desc">Review proof, verify address/phone</span>
                      </button>
                      <button class="template-btn" on:click={() => showDraft(proof, 'stronger')}>
                        🔥 Suggest a Stronger Offer
                        <span class="template-desc">Recommend more aggressive promotion</span>
                      </button>
                      <button class="template-btn" on:click={() => showDraft(proof, 'upsell')}>
                        📏 Upsell: Upgrade Ad Size
                        <span class="template-desc">{proof.ad_size === 'Double' ? 'Suggest premium placement' : 'Single → Double upgrade'}</span>
                      </button>
                      <button class="template-btn" on:click={() => showDraft(proof, 'expand')}>
                        🏪 Expand to Nearby Stores
                        <span class="template-desc">Suggests actual nearby store locations</span>
                      </button>
                      <button class="template-btn" on:click={() => showDraft(proof, 'approve')}>
                        ✅ Looks Great — Nudge Approval
                        <span class="template-desc">Friendly reminder to approve</span>
                      </button>
                    </div>
                  </div>
                </div>
              {/if}
            </div>
          {/if}
        </div>
      {/each}

      {#if filteredProofs.length === 0}
        <p class="empty-state">No ad proofs found{proofSearch ? ' matching your search' : ''}.</p>
      {/if}
    </div>
  {/if}

  <!-- Draft Preview Modal -->
  {#if draftPreview}
    <div class="draft-overlay" on:click|self={() => draftPreview = null}>
      <div class="draft-modal">
        <div class="draft-header">
          <h3>📧 Email Draft Preview</h3>
          <button class="draft-close" on:click={() => draftPreview = null}>✕</button>
        </div>
        
        <div class="draft-to">
          <span class="draft-label">To:</span>
          <span class="draft-value">{draftPreview.email || 'No email'}</span>
        </div>
        <div class="draft-subject">
          <span class="draft-label">Subject:</span>
          <span class="draft-value">{draftPreview.subject}</span>
        </div>
        
        <div class="draft-body-container">
          <pre class="draft-body-text">{draftPreview.body}</pre>
        </div>

        <div class="draft-actions">
          <button class="draft-action-btn copy-btn" on:click={copyDraft}>
            📋 Copy to Clipboard
          </button>
          <button class="draft-action-btn send-btn" on:click={openInEmailApp}>
            ✉️ Open in Email App
          </button>
          <button class="draft-action-btn close-btn" on:click={() => draftPreview = null}>
            Close
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .clients-container { padding: 20px; max-width: 100%; margin: 0 auto; }
  h2 { margin: 0 0 6px; font-size: 24px; color: var(--text-primary); font-weight: 700; }
  .subtitle { margin: 0 0 16px; color: var(--text-secondary); font-size: 14px; }
  .back-btn { background: none; border: none; color: #CC0000; font-size: 14px; font-weight: 600; cursor: pointer; padding: 10px 0; margin-bottom: 16px; }

  .button-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem; width: 100%; }
  @media (min-width: 768px) { .button-grid { grid-template-columns: repeat(2, 1fr); gap: 2rem; } }
  @media (min-width: 1200px) { .button-grid { grid-template-columns: repeat(4, 1fr); gap: 2rem; } }
  .main-btn { background: var(--card-bg); border: 2px solid var(--border-color); border-radius: 16px; padding: 2rem 1.5rem; cursor: pointer; transition: all 0.2s; text-align: center; color: var(--text-primary); min-height: 180px; display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; }
  .main-btn:hover { border-color: #cc0000; box-shadow: 0 4px 12px rgba(204, 0, 0, 0.1); transform: translateY(-2px); }
  .btn-icon { font-size: 2rem; margin-bottom: 0.5rem; }
  .btn-text { font-weight: 600; color: var(--text-primary, #eee); margin-bottom: 0.25rem; }
  .btn-desc { font-size: 0.85rem; color: var(--text-tertiary, #999); }

  .search-box { margin: 15px 0; }
  .search-box input { width: 100%; padding: 12px 16px; border: 1px solid #e0e0e0; border-radius: 8px; font-size: 14px; box-sizing: border-box; height: 44px; }

  .customer-list { display: flex; flex-direction: column; gap: 12px; }
  .customer-card { background: white; border: 1px solid #e0e0e0; border-radius: 12px; padding: 16px; }
  .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
  .card-header h4 { margin: 0; font-size: 16px; color: #333; font-weight: 700; flex: 1; }
  .amount { font-weight: 700; color: #CC0000; font-size: 16px; white-space: nowrap; margin-left: 8px; }
  .contact { margin: 0 0 4px; font-size: 13px; color: #555; font-weight: 600; }
  .phone, .email { margin: 2px 0; font-size: 13px; color: #555; }
  .card-meta { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0; font-size: 11px; color: #888; }
  .address { margin: 4px 0; font-size: 12px; color: #888; }
  .rep-tag { margin: 4px 0 0; font-size: 11px; color: #CC0000; font-weight: 600; }
  .card-actions { display: flex; gap: 8px; margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee; }
  .action-btn { flex: 1; padding: 8px; border: 1px solid #ddd; border-radius: 8px; text-align: center; text-decoration: none; font-size: 13px; font-weight: 600; color: #333; background: #f9f9f9; }
  .action-btn.call { background: #2e7d32; color: white; border-color: #2e7d32; }

  .empty { color: #999; font-style: italic; text-align: center; margin: 40px 0; }

  .info-card { background: #f9f9f9; border-radius: 12px; padding: 16px; margin-top: 15px; }
  .info-card p { margin: 0 0 10px; color: #555; font-size: 13px; }
  .info-card ul { margin: 0; padding-left: 20px; font-size: 13px; color: #555; }
  .info-card li { margin: 4px 0; }
  .note { color: #999; font-style: italic; font-size: 12px !important; }

  .sales-summary { display: flex; gap: 12px; margin-bottom: 20px; }
  .stat { flex: 1; background: white; border: 1px solid #eee; border-radius: 10px; padding: 14px; text-align: center; }
  .stat-value { display: block; font-size: 20px; font-weight: 700; color: #CC0000; }
  .stat-label { display: block; font-size: 11px; color: #888; margin-top: 4px; text-transform: uppercase; }

  .sales-list { display: flex; flex-direction: column; gap: 8px; }
  .sale-row { display: flex; justify-content: space-between; align-items: center; padding: 12px; background: white; border: 1px solid #eee; border-radius: 8px; }
  .sale-info { display: flex; flex-direction: column; flex: 1; }
  .sale-name { font-weight: 600; font-size: 14px; color: #333; }
  .sale-meta { font-size: 11px; color: #888; margin-top: 4px; }
  .sale-amount { font-weight: 700; font-size: 16px; color: #CC0000; margin-left: 12px; }

  /* Client Events */
  .client-events { margin: 10px 0; padding: 10px; background: var(--bg-secondary, #f9f9f9); border-radius: 8px; }
  .events-label { margin: 0 0 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--text-tertiary, #999); letter-spacing: 0.5px; }
  .client-event { display: flex; align-items: center; gap: 6px; padding: 4px 0; font-size: 12px; }
  .evt-icon { font-size: 14px; }
  .evt-label { font-weight: 600; color: var(--text-primary); min-width: 120px; }
  .evt-date { color: var(--text-secondary); }
  .client-event.soon .evt-date { color: #CC0000; font-weight: 600; }
  .client-event.overdue .evt-date { color: #c33; font-weight: 700; }
  .client-event.overdue .evt-label { color: #c33; }

  /* Sort Bar */
  .sort-bar { display: flex; align-items: center; gap: 6px; margin-bottom: 14px; overflow-x: auto; white-space: nowrap; padding-bottom: 4px; }
  .sort-label { font-size: 12px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; }
  .sort-btn { padding: 6px 10px; border: 1px solid var(--border-color, #ddd); border-radius: 16px; background: var(--card-bg, white); font-size: 11px; font-weight: 600; cursor: pointer; color: var(--text-secondary); transition: all 0.2s; flex-shrink: 0; }
  .sort-btn.active { background: #CC0000; color: white; border-color: #CC0000; }
  .sort-btn:hover:not(.active) { border-color: #CC0000; color: #CC0000; }

  /* Submit Contract */
  .upload-area { margin: 16px 0; }
  .upload-area input[type="file"] { display: none; }
  .upload-label { display: block; padding: 24px; text-align: center; border: 2px dashed #ddd; border-radius: 10px; font-size: 16px; font-weight: 600; color: var(--text-secondary); cursor: pointer; transition: all 0.2s; }
  .upload-label:hover { border-color: #CC0000; background: #fff5f5; }

  .error-text { color: #c33; font-size: 13px; margin: 8px 0; }

  .parsed-card { background: var(--card-bg, white); border: 1px solid var(--border-color, #eee); border-radius: 10px; padding: 16px; margin-top: 16px; }
  .parsed-card h3 { margin: 0 0 12px; font-size: 16px; color: #2e7d32; }
  .parsed-field { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f0f0f0; font-size: 13px; }
  .parsed-field:last-of-type { border-bottom: none; }
  .parsed-field.highlight { background: #fff5f5; margin: 4px -8px; padding: 8px; border-radius: 6px; }
  .field-label { color: var(--text-secondary); font-weight: 600; }
  .field-value { color: var(--text-primary); text-align: right; max-width: 60%; }
  .parsed-field.highlight .field-value { color: #CC0000; font-weight: 700; font-size: 16px; }

  .submit-btn { width: 100%; padding: 14px; background: #CC0000; color: white; border: none; border-radius: 8px; font-size: 15px; font-weight: 700; cursor: pointer; margin-top: 16px; }
  .cancel-btn { width: 100%; padding: 10px; background: none; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; color: var(--text-secondary); cursor: pointer; margin-top: 8px; }

  /* Expanded Section */
  .expand-btn { background: #fff5f5 !important; color: #CC0000 !important; border-color: #CC0000 !important; font-weight: 600; }
  .expanded-section { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border-color, #eee); }
  .section-header { font-size: 13px; font-weight: 700; color: var(--text-primary); margin: 12px 0 8px; text-transform: uppercase; letter-spacing: 0.5px; }
  .section-header:first-child { margin-top: 0; }

  /* Email Templates */
  .email-btns { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
  .email-tmpl-btn { padding: 8px 12px; background: var(--card-bg, white); border: 1px solid var(--border-color, #ddd); border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.2s; color: var(--text-primary); }
  .email-tmpl-btn:hover { border-color: #CC0000; background: #fff5f5; }

  .draft-box { background: var(--bg-secondary, #f5f5f5); border-radius: 8px; padding: 12px; margin-bottom: 12px; }
  .draft-subject { margin: 0 0 8px; font-size: 13px; color: var(--text-primary); }
  .draft-body { margin: 0; font-size: 12px; color: var(--text-secondary); white-space: pre-wrap; font-family: inherit; line-height: 1.5; max-height: 200px; overflow-y: auto; }
  .copy-btn { padding: 8px 16px; background: #CC0000; color: white; border: none; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; margin-top: 8px; margin-right: 8px; }
  .send-btn { display: inline-block; padding: 8px 16px; background: #1565c0; color: white; border: none; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; margin-top: 8px; text-decoration: none; }

  /* Expansion */
  .expand-label { margin: 8px 0 6px; font-size: 12px; font-weight: 700; color: var(--text-secondary); }
  .expand-note { font-size: 12px; color: var(--text-tertiary, #999); font-style: italic; }
  .nearby-list { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; }
  .nearby-store { display: flex; justify-content: space-between; padding: 6px 10px; background: var(--card-bg, white); border: 1px solid var(--border-color, #eee); border-radius: 6px; font-size: 12px; }
  .ns-name { font-weight: 600; color: var(--text-primary); }
  .ns-num { color: #CC0000; font-weight: 600; font-size: 11px; }

  .upsell-list { display: flex; flex-direction: column; gap: 4px; }
  .upsell-item { font-size: 12px; color: var(--text-secondary); padding: 4px 0; }
  .upsell-item strong { color: var(--text-primary); }
  /* Pending Renewals */
  .renewal-btn { border: 2px solid #CC0000 !important; }
  .search-input { width: 100%; padding: 10px 14px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; margin-bottom: 12px; box-sizing: border-box; }
  .search-input:focus { outline: none; border-color: #CC0000; }
  .renewal-filters { display: flex; gap: 8px; margin-bottom: 16px; }
  .renewal-filters select { flex: 1; padding: 8px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; background: white; }
  .renewal-list { display: flex; flex-direction: column; gap: 10px; }
  .select-bar { display:flex; gap:8px; align-items:center; margin-bottom:12px; flex-wrap:wrap; }
  .select-toggle { padding:8px 14px; border:2px solid var(--border-color, #ddd); border-radius:8px; background:var(--card-bg, white); font-size:13px; font-weight:700; cursor:pointer; color:var(--text-primary, #333); }
  .select-toggle.active { border-color:#CC0000; color:#CC0000; }
  .select-all-btn { padding:8px 12px; border:1px solid var(--border-color, #ddd); border-radius:8px; background:var(--card-bg, white); font-size:12px; font-weight:600; cursor:pointer; color:var(--text-secondary); }
  .export-btn { padding:8px 16px; border:none; border-radius:8px; background:#CC0000; color:white; font-size:13px; font-weight:700; cursor:pointer; }
  .export-btn:disabled { background:#999; cursor:not-allowed; }
  .export-btn:hover:not(:disabled) { background:#a00; }
  .select-check { font-size:20px; margin-right:8px; flex-shrink:0; }
  .renewal-card { background: white; border: 1px solid #e0e0e0; border-radius: 10px; padding: 14px; cursor: pointer; transition: all 0.2s; display:flex; align-items:flex-start; }
  .renewal-deadline { font-size:12px; padding:4px 8px; margin-top:6px; border-radius:4px; background:rgba(46,125,50,0.08); color:#2E7D32; }
  .renewal-deadline.soon { background:rgba(255,152,0,0.1); color:#E65100; }
  .renewal-deadline.urgent { background:rgba(204,0,0,0.1); color:#CC0000; font-weight:700; }
  .renewal-deadline.overdue { background:rgba(204,0,0,0.15); color:#CC0000; font-weight:800; }
  .renewal-card.selected { border-color: #CC0000; background: rgba(204,0,0,0.03); }
  .renewal-card:hover { border-color: #CC0000; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
  .renewal-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
  .renewal-biz h4 { margin: 0; font-size: 15px; color: #333; }
  .renewal-cat { font-size: 12px; color: #888; }
  .renewal-meta { text-align: right; }
  .renewal-cycle { display: inline-block; background: #CC0000; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
  .renewal-price { display: block; font-size: 14px; font-weight: 700; color: #2e7d32; margin-top: 4px; }
  .renewal-sub { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 8px; font-size: 12px; color: #666; }
  .renewal-details { margin-top: 14px; padding-top: 14px; border-top: 1px solid #eee; }
  .detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .detail-item { display: flex; flex-direction: column; }
  .detail-label { font-size: 11px; color: #888; font-weight: 600; text-transform: uppercase; }
  .detail-value { font-size: 14px; color: #333; }
  .status-active { color: #2e7d32; font-weight: 600; }
  .status-inactive { color: #c33; font-weight: 600; }
  .renewal-actions { display: flex; gap: 8px; margin-top: 12px; }
  .renewal-actions .action-btn { flex: 1; text-align: center; padding: 10px; border-radius: 8px; font-size: 14px; font-weight: 600; text-decoration: none; }
  .renewal-actions .call-btn { background: #2e7d32; color: white; }
  .renewal-actions .email-btn { background: #CC0000; color: white; }
  /* Pending Renewals */
  .renewal-btn { border: 2px solid #CC0000 !important; }
  .renewal-filters { margin-bottom: 16px; }
  .renewal-search { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; margin-bottom: 8px; box-sizing: border-box; }
  .filter-row { display: flex; gap: 8px; }
  .filter-row select { flex: 1; padding: 8px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; background: white; }
  .renewal-list { display: flex; flex-direction: column; gap: 8px; }
  .renewal-card { background: white; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden; }
  .renewal-card.expanded { border-color: #CC0000; }
  .renewal-header { display: flex; justify-content: space-between; align-items: center; padding: 12px; width: 100%; background: none; border: none; cursor: pointer; text-align: left; }
  .renewal-main h4 { margin: 0; font-size: 15px; color: #333; }
  .renewal-meta { margin: 2px 0 0; font-size: 12px; color: #888; }
  .renewal-rep { margin: 2px 0 0; font-size: 12px; color: #666; }
  .renewal-cycle { background: #CC0000; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-left: 6px; }
  .renewal-right { text-align: right; flex-shrink: 0; }
  .renewal-price { font-weight: 700; color: #2e7d32; font-size: 14px; display: block; }
  .renewal-arrow { font-size: 12px; color: #999; }
  .renewal-details { padding: 0 12px 12px; border-top: 1px solid #eee; }
  .detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 12px; }
  .detail-item { background: #f9f9f9; padding: 8px; border-radius: 6px; }
  .detail-item.warning { background: #fff3e0; border: 1px solid #ff9800; }
  .detail-label { display: block; font-size: 11px; color: #888; font-weight: 600; text-transform: uppercase; }
  .detail-value { font-size: 14px; color: #333; word-break: break-all; }
  .detail-value.inactive { color: #c33; font-weight: 600; }
  .renewal-actions { display: flex; gap: 8px; margin-top: 12px; }
  .renewal-actions .action-btn { flex: 1; text-align: center; padding: 10px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px; }
  .renewal-actions .call-btn { background: #2e7d32; color: white; }
  .renewal-actions .email-btn { background: #1976d2; color: white; }
  /* Ad Proofs */
  .proofs-list { display: flex; flex-direction: column; gap: 12px; margin-top: 16px; }
  .proof-card { background: var(--card-bg); border: 2px solid var(--border-color); border-radius: 12px; overflow: hidden; transition: all 0.2s; }
  .proof-card.expanded { border-color: #cc0000; }
  .proof-header { display: flex; justify-content: space-between; align-items: center; width: 100%; padding: 16px; background: none; border: none; cursor: pointer; text-align: left; color: var(--text-primary); }
  .proof-info h4 { margin: 0 0 4px; font-size: 16px; font-weight: 700; }
  .proof-meta { margin: 0 0 2px; font-size: 13px; color: var(--text-secondary); font-weight: 600; }
  .proof-store { margin: 0 0 2px; font-size: 12px; color: var(--text-tertiary); }
  .proof-date { margin: 0; font-size: 11px; color: var(--text-tertiary); }
  .expand-arrow { font-size: 14px; color: var(--text-tertiary); flex-shrink: 0; }
  .proof-detail { padding: 0 16px 16px; border-top: 1px solid var(--border-color); }
  .proof-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 12px; }
  @media (min-width: 768px) { .proof-fields { grid-template-columns: 1fr 1fr 1fr; } }
  .proof-image-container { margin-top: 16px; text-align: center; }
  .proof-image-container h4 { margin: 0 0 12px; font-size: 14px; color: var(--text-secondary); }
  .proof-image { max-width: 100%; border-radius: 8px; border: 1px solid var(--border-color); }
  .view-full-btn { display: inline-block; margin-top: 8px; padding: 8px 16px; background: #cc0000; color: white; border-radius: 8px; text-decoration: none; font-size: 13px; font-weight: 600; }
  .view-full-btn:hover { background: #aa0000; }
  .filter-bar { margin-top: 12px; }
  .search-input { width: 100%; padding: 10px 14px; border: 2px solid var(--border-color); border-radius: 10px; font-size: 14px; background: var(--input-bg); color: var(--text-primary); box-sizing: border-box; }
  .filter-row { display: flex; gap: 8px; margin-top: 8px; flex-wrap: wrap; }
  .filter-select { flex: 1; min-width: 100px; padding: 8px 10px; border: 2px solid var(--border-color); border-radius: 8px; font-size: 13px; background: var(--input-bg); color: var(--text-primary); }
  .empty-state { text-align: center; padding: 40px 20px; color: var(--text-tertiary); font-size: 15px; }

  /* Ad Proof Contact Actions */
  .proof-contact-actions { margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--border-color); }
  .proof-contact-actions h4 { margin: 0 0 12px; font-size: 15px; color: var(--text-primary); }
  .contact-btns { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
  .contact-btn { display: inline-flex; align-items: center; gap: 6px; padding: 10px 20px; border-radius: 10px; font-size: 14px; font-weight: 600; text-decoration: none; transition: all 0.2s; }
  .email-btn { background: #cc0000; color: white; }
  .email-btn:hover { background: #aa0000; }
  .template-section { margin-top: 8px; }
  .template-section h5 { margin: 0 0 10px; font-size: 13px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
  .template-list { display: flex; flex-direction: column; gap: 8px; }
  .template-btn { display: flex; flex-direction: column; align-items: flex-start; gap: 4px; width: 100%; padding: 14px 16px; background: var(--card-bg); border: 2px solid var(--border-color); border-radius: 10px; cursor: pointer; text-align: left; font-size: 14px; font-weight: 600; color: var(--text-primary); transition: all 0.2s; }
  .template-btn:hover { border-color: #cc0000; background: rgba(204,0,0,0.05); }
  .template-desc { font-size: 12px; font-weight: 400; color: var(--text-tertiary); }
  .proof-image-fallback { display: inline-block; margin-top: 8px; padding: 8px 16px; background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; text-decoration: none; font-size: 13px; color: var(--text-primary); }
  .client-email-display { margin: 0 0 12px; font-size: 14px; color: var(--text-secondary); }

  /* Draft Preview Modal */
  .draft-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.6); z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 20px; }
  .draft-modal { background: var(--bg-secondary, white); border-radius: 16px; max-width: 600px; width: 100%; max-height: 85vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
  .draft-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 20px 12px; border-bottom: 1px solid var(--border-color); }
  .draft-header h3 { margin: 0; font-size: 18px; color: var(--text-primary); }
  .draft-close { background: none; border: none; font-size: 20px; cursor: pointer; color: var(--text-tertiary); padding: 4px 8px; }
  .draft-to, .draft-subject { padding: 10px 20px; border-bottom: 1px solid var(--border-color); display: flex; gap: 8px; align-items: baseline; }
  .draft-label { font-size: 12px; font-weight: 700; color: var(--text-tertiary); text-transform: uppercase; min-width: 55px; }
  .draft-value { font-size: 14px; color: var(--text-primary); font-weight: 600; }
  .draft-body-container { padding: 20px; }
  .draft-body-text { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; line-height: 1.6; color: var(--text-primary); white-space: pre-wrap; word-wrap: break-word; margin: 0; background: none; border: none; }
  .draft-actions { display: flex; gap: 10px; padding: 16px 20px; border-top: 1px solid var(--border-color); flex-wrap: wrap; }
  .draft-action-btn { flex: 1; min-width: 140px; padding: 12px 16px; border: none; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s; text-align: center; }
  .copy-btn { background: var(--card-bg); border: 2px solid var(--border-color); color: var(--text-primary); }
  .copy-btn:hover { border-color: #cc0000; }
  .send-btn { background: #cc0000; color: white; }
  .send-btn:hover { background: #aa0000; }
  .close-btn { background: var(--card-bg); border: 2px solid var(--border-color); color: var(--text-tertiary); }
</style>
