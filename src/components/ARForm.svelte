<script>
  // A/R Adjustment Request Form — easy fill-out (like the audit tool), saved to
  // localStorage and exportable as a filled PDF matching the paper form.
  import { onMount } from 'svelte';
  import { user } from '../lib/stores.js';
  import StoreSearchInput from '../lib/StoreSearchInput.svelte';

  let allStores = [];
  let contracts = [];
  let saved = false;
  let exporting = false;

  // ── Form model (mirrors the paper A/R Adjustment Request Form) ──
  const blank = {
    // Customer info
    accountNumber: '', customer: '', address: '', cityStateZip: '', phone: '',
    // Request meta
    name: '', date: new Date().toISOString().split('T')[0], repId: '', collectorId: '',
    // Product detail
    rateCard: '', newIo: '', auditInstallInfo: '', cartStartDate: '', duration: '',
    // Order/processing
    skynetBy: '', skynetDate: '', processedByAccounting: '', newPaymentPlan: '',
    // Approvals / signatures
    customerSignature: '', corporateApproval: '', zoneMgrApproval: '',
    // Reason
    reason: '',
    // Skip / move
    changeFromStore: '', fromCycle: '', fromCaseCount: '',
    toStore: '', toCycle: '', toCaseCount: '',
    addressChange: '',
    // Money
    creditAmount: '', refundAmount: '', refundVia: '',
    // Bottom identifiers
    bottomDate: '', store: '', contractNumber: '', zone: '',
  };
  let f = { ...blank };

  // Adjustment type quick-select (drives which sections to emphasize).
  const REQUEST_TYPES = [
    { id: 'credit', label: '💳 Credit account' },
    { id: 'refund', label: '💵 Issue refund' },
    { id: 'skipmove', label: '🔀 Skip / move store' },
    { id: 'paymentplan', label: '🗓️ Change payment plan' },
    { id: 'address', label: '📍 Address change' },
    { id: 'other', label: '📝 Other adjustment' },
  ];
  let requestTypes = new Set();
  function toggleType(id) {
    if (requestTypes.has(id)) requestTypes.delete(id);
    else requestTypes.add(id);
    requestTypes = requestTypes;
  }

  const RATE_CARDS = ['Register Tape', 'Cartvertising', 'Nose of Cart', 'Header Ad', 'DigitalBoost', 'FindLocal', 'ReviewBoost', 'LoyaltyBoost', 'Other'];
  const REFUND_METHODS = ['Check', 'Credit Card', 'ACH / Bank Transfer', 'Account Credit', 'Other'];

  onMount(async () => {
    try {
      const res = await fetch(import.meta.env.BASE_URL + 'data/stores.json?t=' + Date.now());
      allStores = await res.json();
    } catch (e) { console.warn('[ARForm] stores load failed', e); }
    try {
      const cRes = await fetch(import.meta.env.BASE_URL + 'data/contracts.json?t=' + Date.now());
      const cData = await cRes.json();
      contracts = cData.contracts || cData || [];
    } catch (e) { contracts = []; }
    // Prefill rep from the signed-in user.
    f.name = $user?.name || $user?.first_name || '';
    f.repId = $user?.id ? String($user.id) : '';
    // Restore an in-progress draft.
    try {
      const draft = JSON.parse(localStorage.getItem('ar_form_draft') || 'null');
      if (draft) { f = { ...blank, ...draft }; }
    } catch {}
  });

  // ── Prefill from an existing client (contract) ──
  let clientSearch = '';
  let clientResults = [];
  let showClientPicker = false;
  function searchClients() {
    const q = clientSearch.trim().toLowerCase();
    if (q.length < 2) { clientResults = []; return; }
    clientResults = contracts.filter(c =>
      (c.business_name || '').toLowerCase().includes(q) ||
      (c.contact_name || '').toLowerCase().includes(q) ||
      (c.contract_number || '').toLowerCase().includes(q) ||
      (c.contact_phone || '').toLowerCase().includes(q)
    ).slice(0, 12);
  }
  function pickClient(c) {
    f.customer = c.business_name || f.customer;
    f.address = c.address || f.address;
    f.phone = c.contact_phone || f.phone;
    f.contractNumber = c.contract_number || f.contractNumber;
    f.store = c.store_name ? (c.store_name + (c.store_number ? ' #' + c.store_number : '')) : f.store;
    f.zone = c.zone || f.zone;
    f.rateCard = c.product_description && RATE_CARDS.includes(c.product_description) ? c.product_description : f.rateCard;
    if (c.contact_name) f.customerContact = c.contact_name;
    showClientPicker = false;
    clientSearch = '';
    clientResults = [];
    f = f;
  }

  // Store pickers for the skip/move section.
  function pickFromStore(store) {
    f.changeFromStore = `${store.GroceryChain} - ${store.City} (${store.StoreName})`;
    f.fromCycle = store.Cycle || f.fromCycle;
    f.fromCaseCount = store['Case Count'] != null ? String(store['Case Count']) : f.fromCaseCount;
    f = f;
  }
  function pickToStore(store) {
    f.toStore = `${store.GroceryChain} - ${store.City} (${store.StoreName})`;
    f.toCycle = store.Cycle || f.toCycle;
    f.toCaseCount = store['Case Count'] != null ? String(store['Case Count']) : f.toCaseCount;
    f = f;
  }

  function saveDraft() {
    localStorage.setItem('ar_form_draft', JSON.stringify(f));
    saved = true;
    setTimeout(() => saved = false, 2500);
  }
  function clearForm() {
    if (!confirm('Clear the whole form?')) return;
    f = { ...blank };
    f.name = $user?.name || $user?.first_name || '';
    f.repId = $user?.id ? String($user.id) : '';
    requestTypes = new Set();
    localStorage.removeItem('ar_form_draft');
  }

  // ── Export a filled PDF that mirrors the paper form ──
  async function exportPdf() {
    exporting = true;
    try {
      const { PDFDocument, rgb, StandardFonts } = await import('pdf-lib');
      const pdf = await PDFDocument.create();
      const font = await pdf.embedFont(StandardFonts.Helvetica);
      const bold = await pdf.embedFont(StandardFonts.HelveticaBold);
      const red = rgb(0.8, 0, 0), black = rgb(0.1, 0.1, 0.1), gray = rgb(0.4, 0.4, 0.4);
      const W = 612, H = 792, M = 44;

      // Standard PDF fonts (WinAnsi) can't encode many unicode chars a rep might
      // type (arrows, smart quotes, em dashes, emoji). Normalize to safe ASCII
      // so the export never crashes.
      function san(v) {
        return String(v == null ? '' : v)
          .replace(/[\u2018\u2019\u201A\u201B]/g, "'")
          .replace(/[\u201C\u201D\u201E]/g, '"')
          .replace(/[\u2013\u2014\u2015]/g, '-')
          .replace(/[\u2192\u27A1]/g, '->')
          .replace(/\u2190/g, '<-')
          .replace(/[\u2022\u25CF]/g, '*')
          .replace(/\u2026/g, '...')
          .replace(/[^\x20-\x7E]/g, ''); // drop anything else non-Latin1
      }
      let page = pdf.addPage([W, H]);
      let y = H - M;

      function ensure(need) {
        if (y - need < 50) { page = pdf.addPage([W, H]); y = H - M; }
      }
      // A labeled "field" line: bold label + value on a ruled line.
      function field(label, value, opts = {}) {
        const lw = opts.labelWidth || 150;
        const size = 10;
        ensure(20);
        page.drawText(san(label), { x: M, y, font: bold, size, color: black });
        const vx = M + lw;
        const lineW = (opts.width || (W - M - vx));
        page.drawText(san(value), { x: vx, y, font, size, color: black });
        page.drawLine({ start: { x: vx, y: y - 2 }, end: { x: vx + lineW, y: y - 2 }, thickness: 0.5, color: rgb(0.75,0.75,0.75) });
        y -= 20;
      }
      // Two fields side by side.
      function field2(l1, v1, l2, v2) {
        const size = 10; ensure(20);
        const half = (W - M*2) / 2;
        const pad = 6;
        // Position each value just past its actual label width so long labels
        // ("From Case Count", "Zone Mgr Approval") never collide with the value.
        const s1 = san(l1), s2 = san(l2);
        page.drawText(s1, { x: M, y, font: bold, size, color: black });
        const vx1 = M + bold.widthOfTextAtSize(s1, size) + pad;
        page.drawText(san(v1), { x: vx1, y, font, size, color: black });
        page.drawLine({ start: { x: vx1, y: y - 2 }, end: { x: M + half - 10, y: y - 2 }, thickness: 0.5, color: rgb(0.75,0.75,0.75) });
        page.drawText(s2, { x: M + half, y, font: bold, size, color: black });
        const vx2 = M + half + bold.widthOfTextAtSize(s2, size) + pad;
        page.drawText(san(v2), { x: vx2, y, font, size, color: black });
        page.drawLine({ start: { x: vx2, y: y - 2 }, end: { x: W - M, y: y - 2 }, thickness: 0.5, color: rgb(0.75,0.75,0.75) });
        y -= 20;
      }
      function section(title) {
        ensure(26); y -= 4;
        page.drawText(san(title), { x: M, y, font: bold, size: 11, color: red });
        y -= 6;
        page.drawLine({ start: { x: M, y: y }, end: { x: W - M, y: y }, thickness: 1, color: red });
        y -= 16;
      }
      function multi(label, value, lines = 2) {
        ensure(16 + lines * 16);
        page.drawText(san(label), { x: M, y, font: bold, size: 10, color: black });
        y -= 16;
        // wrap value
        const words = san(value).split(' ');
        const maxW = W - M*2; let line = ''; let drawn = 0;
        for (const w of words) {
          const test = line ? line + ' ' + w : w;
          if (font.widthOfTextAtSize(test, 10) > maxW && line) {
            page.drawText(line, { x: M, y, font, size: 10, color: black });
            page.drawLine({ start: { x: M, y: y - 2 }, end: { x: W - M, y: y - 2 }, thickness: 0.5, color: rgb(0.8,0.8,0.8) });
            y -= 18; line = w; drawn++;
          } else line = test;
        }
        if (line) { page.drawText(line, { x: M, y, font, size: 10, color: black }); page.drawLine({ start: { x: M, y: y - 2 }, end: { x: W - M, y: y - 2 }, thickness: 0.5, color: rgb(0.8,0.8,0.8) }); y -= 18; drawn++; }
        // pad remaining blank ruled lines
        for (; drawn < lines; drawn++) { page.drawLine({ start: { x: M, y: y - 2 }, end: { x: W - M, y: y - 2 }, thickness: 0.5, color: rgb(0.8,0.8,0.8) }); y -= 18; }
        y -= 2;
      }

      // Header
      page.drawRectangle({ x: 0, y: y - 34, width: W, height: 46, color: red });
      page.drawText('A/R ADJUSTMENT REQUEST FORM', { x: M, y: y - 8, font: bold, size: 16, color: rgb(1,1,1) });
      page.drawText('IndoorMedia', { x: W - M - font.widthOfTextAtSize('IndoorMedia', 10), y: y - 8, font, size: 10, color: rgb(1,1,1) });
      y -= 52;

      section('Customer Info');
      field('Account #:', f.accountNumber);
      field('Customer:', f.customer);
      if (f.customerContact) field('Contact Name:', f.customerContact);
      field('Address:', f.address);
      field('City, State, ZIP:', f.cityStateZip);
      field('Phone #:', f.phone);
      field2('Name:', f.name, 'Date:', f.date);
      field2('Rep ID:', f.repId, 'Collector ID:', f.collectorId);

      section('Product Detail');
      field('Rate Card:', f.rateCard);
      field('New IO:', f.newIo);
      field('Audit/Install Info:', f.auditInstallInfo);
      field2('Cart Start Date:', f.cartStartDate, 'Duration:', f.duration);

      section('Adjustment Requested');
      if (requestTypes.size) {
        const labels = REQUEST_TYPES.filter(t => requestTypes.has(t.id)).map(t => t.label.replace(/^[^ ]+ /, ''));
        field('Type(s):', labels.join(', '), { labelWidth: 90 });
      }
      multi('Reason:', f.reason, 2);
      if (f.creditAmount) field('Please credit account, amount:', '$' + f.creditAmount, { labelWidth: 210 });
      if (f.refundAmount) field2('Refund amount:', '$' + f.refundAmount, 'Via:', f.refundVia);
      if (f.newPaymentPlan) field('Change to new payment plan:', f.newPaymentPlan, { labelWidth: 210 });

      // Skip / move
      section('Skip / Move');
      if (f.changeFromStore) field('Change FROM store:', f.changeFromStore, { labelWidth: 130 });
      field2('From Cycle:', f.fromCycle, 'From Case Count:', f.fromCaseCount);
      if (f.toStore) field('Move TO store:', f.toStore, { labelWidth: 130 });
      field2('To Cycle:', f.toCycle, 'To Case Count:', f.toCaseCount);
      multi('Will the business address change? (correct address if applicable):', f.addressChange, 1);

      section('Order / Processing (office use)');
      field('Order created in Skynet by:', f.skynetBy, { labelWidth: 165 });
      field('Skynet date:', f.skynetDate, { labelWidth: 165 });
      field('Processed by Accounting:', f.processedByAccounting, { labelWidth: 170 });

      section('Approvals & Signatures');
      field('Customer Signature:', f.customerSignature, { labelWidth: 150 });
      field2('Corporate Approval:', f.corporateApproval, 'Zone Mgr Approval:', f.zoneMgrApproval);

      section('Reference');
      field2('Date:', f.bottomDate, 'Store:', f.store);
      field2('Contract #:', f.contractNumber, 'Zone:', f.zone);

      // Footer
      page.drawText('IndoorMedia  |  A/R Adjustment Request  |  Generated ' + new Date().toLocaleDateString(), { x: M, y: 30, font, size: 8, color: gray });

      const bytes = await pdf.save();
      const fname = 'AR_Adjustment_' + (f.customer || 'form').replace(/[^a-z0-9]+/gi, '_') + '_' + f.date + '.pdf';
      if (navigator.share && /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)) {
        try { await navigator.share({ files: [new File([bytes], fname, { type: 'application/pdf' })], title: fname }); saveDraft(); return; } catch {}
      }
      const blob = new Blob([bytes], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
      saveDraft();
    } catch (e) {
      alert('Could not generate the PDF: ' + (e?.message || e));
    } finally {
      exporting = false;
    }
  }
</script>

<div class="ar-container">
  <h2>🧾 A/R Adjustment Request</h2>
  <p class="subtitle">Fill it out here, then export a completed PDF to submit.</p>

  <!-- Prefill from an existing client -->
  <div class="ar-prefill">
    {#if !showClientPicker}
      <button class="prefill-btn" on:click={() => { showClientPicker = true; }}>⚡ Prefill from an existing client</button>
    {:else}
      <div class="prefill-box">
        <div class="prefill-head">
          <strong>Search clients</strong>
          <button class="x" on:click={() => { showClientPicker = false; clientSearch=''; clientResults=[]; }}>✕</button>
        </div>
        <input type="text" placeholder="Business, contact, phone, or contract #…" bind:value={clientSearch} on:input={searchClients} />
        {#if clientResults.length}
          <div class="prefill-results">
            {#each clientResults as c}
              <button class="prefill-result" on:click={() => pickClient(c)}>
                <span class="pr-biz">{c.business_name || 'Client'}</span>
                <span class="pr-sub">{[c.contact_name, c.store_name, c.contract_number].filter(Boolean).join(' · ')}</span>
              </button>
            {/each}
          </div>
        {/if}
      </div>
    {/if}
  </div>

  <!-- Adjustment type quick-select -->
  <div class="ar-section">
    <label class="sec-label">What are you requesting?</label>
    <div class="type-grid">
      {#each REQUEST_TYPES as t}
        <button class="type-chip" class:on={requestTypes.has(t.id)} on:click={() => toggleType(t.id)}>{t.label}</button>
      {/each}
    </div>
  </div>

  <!-- Customer Info -->
  <fieldset class="ar-fieldset">
    <legend>Customer Info</legend>
    <div class="grid2">
      <label>Account #<input bind:value={f.accountNumber} /></label>
      <label>Contract #<input bind:value={f.contractNumber} /></label>
      <label class="full">Customer<input bind:value={f.customer} /></label>
      <label class="full">Contact Name<input bind:value={f.customerContact} /></label>
      <label class="full">Address<input bind:value={f.address} /></label>
      <label>City, State, ZIP<input bind:value={f.cityStateZip} /></label>
      <label>Phone #<input bind:value={f.phone} /></label>
      <label>Store<input bind:value={f.store} /></label>
      <label>Zone<input bind:value={f.zone} /></label>
    </div>
  </fieldset>

  <!-- Request meta -->
  <fieldset class="ar-fieldset">
    <legend>Request Info</legend>
    <div class="grid2">
      <label>Name<input bind:value={f.name} /></label>
      <label>Date<input type="date" bind:value={f.date} /></label>
      <label>Rep ID<input bind:value={f.repId} /></label>
      <label>Collector ID<input bind:value={f.collectorId} /></label>
    </div>
  </fieldset>

  <!-- Product Detail -->
  <fieldset class="ar-fieldset">
    <legend>Product Detail</legend>
    <div class="grid2">
      <label>Rate Card
        <select bind:value={f.rateCard}>
          <option value="">— select —</option>
          {#each RATE_CARDS as r}<option value={r}>{r}</option>{/each}
        </select>
      </label>
      <label>New IO<input bind:value={f.newIo} /></label>
      <label class="full">Audit / Install Info<input bind:value={f.auditInstallInfo} /></label>
      <label>Cart Start Date<input type="date" bind:value={f.cartStartDate} /></label>
      <label>Duration<input placeholder="e.g., 12 months" bind:value={f.duration} /></label>
    </div>
  </fieldset>

  <!-- Reason + money -->
  <fieldset class="ar-fieldset">
    <legend>Adjustment Details</legend>
    <label class="full">Reason<textarea rows="3" bind:value={f.reason} placeholder="Explain the adjustment request…"></textarea></label>
    <div class="grid2">
      <label>Credit account amount ($)<input inputmode="decimal" bind:value={f.creditAmount} /></label>
      <label>Refund amount ($)<input inputmode="decimal" bind:value={f.refundAmount} /></label>
      <label>Refund via
        <select bind:value={f.refundVia}>
          <option value="">— select —</option>
          {#each REFUND_METHODS as m}<option value={m}>{m}</option>{/each}
        </select>
      </label>
      <label class="full">Change to new payment plan<input bind:value={f.newPaymentPlan} /></label>
    </div>
  </fieldset>

  <!-- Skip / Move -->
  <fieldset class="ar-fieldset">
    <legend>Skip / Move (optional)</legend>
    <label class="full">Change FROM store
      <StoreSearchInput stores={allStores} placeholder="Search current store…" maxResults={8} on:select={e => pickFromStore(e.detail)} />
    </label>
    {#if f.changeFromStore}<p class="picked">📍 {f.changeFromStore}</p>{/if}
    <div class="grid2">
      <label>From Cycle<input bind:value={f.fromCycle} /></label>
      <label>From Case Count<input inputmode="numeric" bind:value={f.fromCaseCount} /></label>
    </div>
    <label class="full">Move TO store
      <StoreSearchInput stores={allStores} placeholder="Search destination store…" maxResults={8} on:select={e => pickToStore(e.detail)} />
    </label>
    {#if f.toStore}<p class="picked">📍 {f.toStore}</p>{/if}
    <div class="grid2">
      <label>To Cycle<input bind:value={f.toCycle} /></label>
      <label>To Case Count<input inputmode="numeric" bind:value={f.toCaseCount} /></label>
    </div>
    <label class="full">Will the business address change? (correct address if applicable)<input bind:value={f.addressChange} /></label>
  </fieldset>

  <!-- Approvals -->
  <fieldset class="ar-fieldset">
    <legend>Approvals & Signatures</legend>
    <div class="grid2">
      <label class="full">Customer Signature (name)<input bind:value={f.customerSignature} /></label>
      <label>Corporate Approval<input bind:value={f.corporateApproval} /></label>
      <label>Zone Mgr Approval<input bind:value={f.zoneMgrApproval} /></label>
    </div>
    <p class="office-note">Office use: Order created in Skynet by / Processed by Accounting are left blank on the exported PDF for the office to complete (fill below if known).</p>
    <div class="grid2">
      <label>Skynet created by<input bind:value={f.skynetBy} /></label>
      <label>Skynet date<input type="date" bind:value={f.skynetDate} /></label>
      <label class="full">Processed by Accounting<input bind:value={f.processedByAccounting} /></label>
    </div>
  </fieldset>

  <div class="ar-actions">
    <button class="ar-btn primary" on:click={exportPdf} disabled={exporting}>{exporting ? '⏳ Generating…' : '📄 Export Filled PDF'}</button>
    <button class="ar-btn" on:click={saveDraft}>{saved ? '✅ Saved' : '💾 Save Draft'}</button>
    <button class="ar-btn ghost" on:click={clearForm}>🗑️ Clear</button>
  </div>
</div>

<style>
  .ar-container { max-width: 640px; margin: 0 auto; padding-bottom: 40px; }
  h2 { margin: 0; font-size: 20px; color: var(--text-primary, #222); }
  .subtitle { color: var(--text-secondary, #666); font-size: 14px; margin: 4px 0 16px; }

  .ar-prefill { margin-bottom: 14px; }
  .prefill-btn { width: 100%; padding: 11px; background: #fff; color: #1565c0; border: 1.5px dashed #1565c0; border-radius: 8px; font-weight: 700; font-size: 14px; cursor: pointer; }
  .prefill-box { background: var(--card-bg,#fff); border: 1px solid var(--border-color,#e0e0e0); border-radius: 10px; padding: 10px; }
  .prefill-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 13px; }
  .prefill-head .x { background: none; border: none; cursor: pointer; color: #999; font-size: 14px; }
  .prefill-box input { width: 100%; padding: 9px 11px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; box-sizing: border-box; }
  .prefill-results { margin-top: 6px; display: flex; flex-direction: column; gap: 6px; max-height: 240px; overflow-y: auto; }
  .prefill-result { text-align: left; background: #fff; border: 1px solid #eee; border-radius: 6px; padding: 8px; cursor: pointer; display: flex; flex-direction: column; gap: 2px; }
  .prefill-result:active { background: #f0f6ff; }
  .pr-biz { font-weight: 700; font-size: 13px; color: #1565c0; }
  .pr-sub { font-size: 12px; color: #888; }

  .ar-section { margin-bottom: 14px; }
  .sec-label { display:block; font-size: 13px; font-weight: 700; color: var(--text-primary,#333); margin-bottom: 8px; }
  .type-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
  .type-chip { padding: 10px; border-radius: 8px; border: 1.5px solid var(--border-color,#ddd); background: var(--card-bg,#fff); color: var(--text-primary,#333); font-size: 13px; font-weight: 600; cursor: pointer; text-align: left; }
  .type-chip.on { border-color: #CC0000; background: #fff5f5; color: #CC0000; }

  .ar-fieldset { border: 1px solid var(--border-color,#e2e2e2); border-radius: 10px; padding: 12px 12px 4px; margin: 0 0 14px; }
  .ar-fieldset legend { font-size: 13px; font-weight: 800; color: #CC0000; padding: 0 6px; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 12px; }
  .ar-fieldset label { display: flex; flex-direction: column; font-size: 12px; font-weight: 600; color: var(--text-secondary,#555); gap: 4px; margin-bottom: 10px; }
  .ar-fieldset label.full { grid-column: 1 / -1; }
  .ar-fieldset input, .ar-fieldset select, .ar-fieldset textarea {
    padding: 10px 11px; border: 1.5px solid var(--border-color,#ddd); border-radius: 7px;
    font-size: 15px; font-family: inherit; background: var(--card-bg,#fff); color: var(--text-primary,#222); width: 100%; box-sizing: border-box;
  }
  .ar-fieldset input:focus, .ar-fieldset select:focus, .ar-fieldset textarea:focus { outline: none; border-color: #CC0000; }
  .picked { font-size: 12px; color: #2e7d32; margin: -4px 0 8px; }
  .office-note { font-size: 11px; color: var(--text-secondary,#999); background: var(--bg-secondary,#f7f7f7); border-radius: 6px; padding: 8px; margin: 2px 0 10px; }

  .ar-actions { display: flex; flex-direction: column; gap: 10px; margin-top: 8px; }
  .ar-btn { padding: 14px; border-radius: 8px; font-size: 15px; font-weight: 700; cursor: pointer; border: 1.5px solid var(--border-color,#ddd); background: var(--card-bg,#fff); color: var(--text-primary,#333); }
  .ar-btn.primary { background: #CC0000; color: #fff; border-color: #CC0000; }
  .ar-btn.primary:disabled { background: #ccc; border-color: #ccc; cursor: not-allowed; }
  .ar-btn.ghost { color: #CC0000; }
</style>
