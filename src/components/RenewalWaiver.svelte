<script>
  // Renewal Waiver form — fills RTUI's official fillable PDF
  // (data/forms/Renewal_Waiver_Fillable.pdf) via its AcroForm fields, with
  // client prefill from contracts (auto-fills Sales Representative from the
  // contract's sales_rep, same source as the counter-sign tool). Saves a draft
  // and exports the filled PDF, preserving the official RTUI layout.
  import { onMount } from 'svelte';
  import { user } from '../lib/stores.js';

  let contracts = [];
  let saved = false;
  let exporting = false;
  let exportMsg = '';

  const TEMPLATE_URL = import.meta.env.BASE_URL + 'data/forms/Renewal_Waiver_Fillable.pdf';

  // Mirrors the fillable fields in the official PDF.
  const blank = {
    date: new Date().toISOString().split('T')[0],
    businessName: '',
    businessAddress: '',
    authorizingPerson: '',
    storeLocation: '',
    customerName: '',       // "I, ____ representing the above named business"
    businessCategory: '',   // "contact other ____ on the above noted store"
    salesRep: '',
    printName: '',          // customer print name
    printName2: '',         // rep print name
    reason: '',
  };
  let f = { ...blank };

  // Common non-renewal reasons for quick-select.
  const REASONS = [
    'Going out of business',
    'Budget / cost',
    'Changing marketing strategy',
    'Not enough ROI / results',
    'Sold / under new ownership',
    'Switching to a competitor',
    'Other',
  ];
  function pickReason(r) { f.reason = r === 'Other' ? '' : r; f = f; }

  onMount(async () => {
    try {
      const cRes = await fetch(import.meta.env.BASE_URL + 'data/contracts.json?t=' + Date.now());
      const cData = await cRes.json();
      contracts = cData.contracts || cData || [];
    } catch (e) { contracts = []; }
    // Prefill rep print name from signed-in user.
    f.printName2 = $user?.name || $user?.display_name || '';
    f.salesRep = $user?.name || $user?.display_name || '';
    // Restore a draft.
    try {
      const draft = JSON.parse(localStorage.getItem('renewal_waiver_draft') || 'null');
      if (draft) f = { ...blank, ...draft };
    } catch {}
  });

  // ── Client prefill from contracts ──
  let clientSearch = '';
  let clientResults = [];
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
    f.businessName = c.business_name || f.businessName;
    f.businessAddress = c.address || f.businessAddress;
    f.authorizingPerson = c.contact_name || f.authorizingPerson;
    f.customerName = c.contact_name || f.customerName;
    f.printName = c.contact_name || f.printName;
    f.storeLocation = c.store_name
      ? (c.store_name + (c.store_number ? ' #' + c.store_number : '') + (c.zone ? ' / ' + c.zone : ''))
      : f.storeLocation;
    // Auto-fill Sales Representative from the contract (the circled line).
    if (c.sales_rep && c.sales_rep.trim()) {
      f.salesRep = c.sales_rep.trim();
      f.printName2 = c.sales_rep.trim();
    }
    clientSearch = '';
    clientResults = [];
    f = f;
  }

  function saveDraft() {
    localStorage.setItem('renewal_waiver_draft', JSON.stringify(f));
    saved = true;
    setTimeout(() => saved = false, 2500);
  }
  function clearForm() {
    if (!confirm('Clear the whole form?')) return;
    f = { ...blank };
    f.printName2 = $user?.name || $user?.display_name || '';
    f.salesRep = $user?.name || $user?.display_name || '';
    localStorage.removeItem('renewal_waiver_draft');
  }

  // Human date for the "Date" field.
  function prettyDate(iso) {
    if (!iso) return '';
    try {
      const d = new Date(iso + 'T00:00:00');
      return d.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    } catch { return iso; }
  }

  // Fill the official AcroForm template and download.
  async function exportPdf() {
    exporting = true;
    exportMsg = '';
    try {
      const { PDFDocument } = await import('pdf-lib');
      const res = await fetch(TEMPLATE_URL + '?t=' + Date.now());
      if (!res.ok) throw new Error('Template not found (' + res.status + ')');
      const bytes = new Uint8Array(await res.arrayBuffer());
      const doc = await PDFDocument.load(bytes);
      const form = doc.getForm();

      // Map our model to the exact field names in the PDF.
      const setText = (name, val) => {
        try { form.getTextField(name).setText(val || ''); } catch (e) { /* field may differ */ }
      };
      setText('Date', prettyDate(f.date));
      setText('Business Name', f.businessName);
      setText('Business Address', f.businessAddress);
      setText('Authorizing Person  s Name', f.authorizingPerson);
      setText('Store   Location', f.storeLocation);
      setText('Customer Name', f.customerName);
      setText('Business Category', f.businessCategory);
      setText('Sales Representative', f.salesRep);
      setText('Print Name', f.printName);
      setText('Print Name_2', f.printName2);
      setText('What is the main reason for non renewalRow1', f.reason);

      // Keep fields editable in the output (don't flatten) so signatures can be
      // added; comment the next line out to flatten instead.
      // form.flatten();

      const out = await doc.save();
      const blob = new Blob([out], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      const safe = (f.businessName || 'Renewal_Waiver').replace(/[^a-z0-9]+/gi, '_');
      a.href = url; a.download = safe + '_Renewal_Waiver.pdf';
      document.body.appendChild(a); a.click();
      window.URL.revokeObjectURL(url); a.remove();
      exportMsg = '✅ Filled waiver downloaded';
    } catch (err) {
      exportMsg = '❌ ' + err.message;
    } finally {
      exporting = false;
    }
  }

  // Download the blank official form.
  async function downloadBlank() {
    try {
      const res = await fetch(TEMPLATE_URL + '?t=' + Date.now());
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'Renewal_Waiver_Fillable.pdf';
      document.body.appendChild(a); a.click();
      window.URL.revokeObjectURL(url); a.remove();
    } catch {}
  }
</script>

<div class="rw-container">
  <h2>📝 Renewal Waiver</h2>
  <p class="subtitle">Document a customer's decision not to renew — fills RTUI's official form.</p>

  <!-- Client prefill -->
  <div class="rw-card">
    <label class="rw-label">Prefill from a client</label>
    <input class="rw-input" type="text" placeholder="Search business, contact, contract #…"
      bind:value={clientSearch} on:input={searchClients} />
    {#if clientResults.length}
      <div class="rw-results">
        {#each clientResults as c}
          <button class="rw-result" on:click={() => pickClient(c)}>
            <strong>{c.business_name || 'Unknown'}</strong>
            <span>{c.contract_number || ''} · {c.store_name || ''}{c.store_number ? ' #' + c.store_number : ''} · {c.sales_rep || 'No rep'}</span>
          </button>
        {/each}
      </div>
    {/if}
  </div>

  <div class="rw-card">
    <div class="rw-field">
      <label class="rw-label">Date</label>
      <input class="rw-input" type="date" bind:value={f.date} />
    </div>
    <div class="rw-field">
      <label class="rw-label">Business Name</label>
      <input class="rw-input" type="text" bind:value={f.businessName} />
    </div>
    <div class="rw-field">
      <label class="rw-label">Business Address</label>
      <input class="rw-input" type="text" bind:value={f.businessAddress} />
    </div>
    <div class="rw-field">
      <label class="rw-label">Authorizing Person's Name</label>
      <input class="rw-input" type="text" bind:value={f.authorizingPerson} />
    </div>
    <div class="rw-field">
      <label class="rw-label">Store # / Location</label>
      <input class="rw-input" type="text" bind:value={f.storeLocation} />
    </div>
    <div class="rw-field">
      <label class="rw-label">Customer Name <span class="rw-hint">(the person releasing rights)</span></label>
      <input class="rw-input" type="text" bind:value={f.customerName} />
    </div>
    <div class="rw-field">
      <label class="rw-label">Business Category <span class="rw-hint">(RTUI may contact other ___ at this store)</span></label>
      <input class="rw-input" type="text" bind:value={f.businessCategory} placeholder="e.g. Mexican restaurants" />
    </div>
    <div class="rw-field">
      <label class="rw-label">Sales Representative <span class="rw-hint">(auto-filled from contract)</span></label>
      <input class="rw-input" type="text" bind:value={f.salesRep} />
    </div>
    <div class="rw-row">
      <div class="rw-field">
        <label class="rw-label">Print Name (Customer)</label>
        <input class="rw-input" type="text" bind:value={f.printName} />
      </div>
      <div class="rw-field">
        <label class="rw-label">Print Name (Rep)</label>
        <input class="rw-input" type="text" bind:value={f.printName2} />
      </div>
    </div>
    <div class="rw-field">
      <label class="rw-label">Main reason for non-renewal</label>
      <div class="rw-reasons">
        {#each REASONS as r}
          <button class="rw-reason" class:active={f.reason === r || (r === 'Other' && f.reason && !REASONS.includes(f.reason))} on:click={() => pickReason(r)}>{r}</button>
        {/each}
      </div>
      <input class="rw-input" type="text" bind:value={f.reason} placeholder="Reason…" />
    </div>
    <p class="rw-note">✍️ Signature is left blank for the customer to sign after printing (or in a PDF signer).</p>
  </div>

  <div class="rw-actions">
    <button class="rw-btn primary" on:click={exportPdf} disabled={exporting}>{exporting ? '⏳ Generating…' : '📄 Export Filled PDF'}</button>
    <button class="rw-btn" on:click={saveDraft}>{saved ? '✅ Saved' : '💾 Save Draft'}</button>
    <button class="rw-btn" on:click={downloadBlank}>⬇️ Blank Form</button>
    <button class="rw-btn danger" on:click={clearForm}>🗑️ Clear</button>
  </div>
  {#if exportMsg}<p class="rw-status" class:warn={exportMsg.startsWith('❌')}>{exportMsg}</p>{/if}
</div>

<style>
  .rw-container { max-width: 640px; margin: 0 auto; }
  h2 { margin: 0 0 6px; font-size: 20px; }
  .subtitle { margin: 0 0 16px; font-size: 13px; color: var(--text-secondary, #888); }
  .rw-card { background: var(--card-bg, #fff); border: 1px solid var(--border-color, #e0e0e0); border-radius: 12px; padding: 16px; margin-bottom: 14px; }
  .rw-field { margin-bottom: 12px; }
  .rw-row { display: flex; gap: 12px; flex-wrap: wrap; }
  .rw-row .rw-field { flex: 1 1 200px; min-width: 0; }
  .rw-label { display: block; font-size: 13px; font-weight: 700; color: var(--text-primary, #333); margin-bottom: 5px; }
  .rw-hint { font-weight: 400; color: #999; font-size: 11px; }
  .rw-input { width: 100%; padding: 10px 12px; border: 1px solid var(--border-color, #ccc); border-radius: 8px; font-size: 14px; font-family: inherit; box-sizing: border-box; background: var(--input-bg, #fff); color: var(--text-primary, #222); }
  .rw-input:focus { outline: none; border-color: #0b8043; }
  .rw-results { margin-top: 8px; display: flex; flex-direction: column; gap: 6px; max-height: 260px; overflow-y: auto; }
  .rw-result { text-align: left; padding: 10px; border: 1px solid var(--border-color, #e0e0e0); border-radius: 8px; background: var(--card-bg, #fafafa); cursor: pointer; display: flex; flex-direction: column; gap: 2px; }
  .rw-result:hover { border-color: #0b8043; background: #e9f7ef; }
  .rw-result strong { font-size: 14px; }
  .rw-result span { font-size: 12px; color: #777; }
  .rw-reasons { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
  .rw-reason { padding: 7px 10px; border: 1px solid var(--border-color, #ccc); border-radius: 16px; background: var(--card-bg, #fff); font-size: 12px; cursor: pointer; white-space: nowrap; }
  .rw-reason.active { background: #0b8043; color: #fff; border-color: #0b8043; }
  .rw-note { font-size: 12px; color: #888; margin: 6px 0 0; line-height: 1.4; }
  .rw-actions { display: flex; gap: 8px; flex-wrap: wrap; }
  .rw-btn { flex: 1 1 auto; padding: 12px; border-radius: 8px; border: 1px solid var(--border-color, #ccc); background: var(--card-bg, #fff); color: var(--text-primary, #333); font-size: 13px; font-weight: 700; cursor: pointer; white-space: nowrap; }
  .rw-btn.primary { background: #0b8043; color: #fff; border-color: #0b8043; }
  .rw-btn.danger { color: #cc0000; border-color: #e5b4b4; }
  .rw-btn:disabled { opacity: 0.55; cursor: default; }
  .rw-status { margin: 10px 0 0; font-size: 13px; font-weight: 600; color: #0b8043; }
  .rw-status.warn { color: #cc0000; }
</style>
