<script>
  import { createEventDispatcher } from 'svelte';
  import { PDFDocument, rgb } from 'pdf-lib';
  import { user } from '../lib/stores.js';
  import { normalizeCycle, cycleStartMonths, cycleSummary } from '../lib/cycleSchedule.js';

  // Cycle → start-month info for this store (A/B/C rotates every quarter).
  $: storeCycle = normalizeCycle(store?.Cycle);
  $: cycleInfo = storeCycle ? cycleSummary(storeCycle) : null;

  // The store to audit is passed in from the Stores tab.
  export let store = null;

  const dispatch = createEventDispatcher();

  // ── Zone install schedule (from RTUI Zone Chart) ──────────────
  // NOTE: This const MUST be declared before the audit-state `let`s below,
  // because those initializers call getLastInstallDate()/getNextInstallDate()
  // which read ZONE_INSTALL_DAYS. Declaring it after would put it in the
  // temporal-dead-zone at init time → ReferenceError → the modal never renders.
  const ZONE_INSTALL_DAYS = {'01':1,'02':8,'03':26,'04':28,'05':25,'06':1,'07':7,'08':5,'09':14,'10':30,'11':25,'12':16,'13':20,'14':10,'15':18,'16':7,'17':20,'18':20,'19':8,'20':10,'21':16,'22':1,'23':12,'24':14,'25':23,'26':20,'27':25,'28':6,'29':6};

  // ── Audit state ───────────────────────────────────────────────
  let auditStep = 2; // 2: shipment dates, 3: enter inventory, 4: report (step 1 store-select removed — store comes in as a prop)
  let auditStoreNum = store?.StoreName || '';
  let auditCases = '';
  let auditRolls = '';
  let auditDate = getLastInstallDate(auditStoreNum);
  let auditPerformedDate = new Date().toISOString().split('T')[0];
  let auditStartingCases = '';
  let auditNextShipmentDate = getNextInstallDate(auditStoreNum);
  let auditReport = null;
  let auditOldCasesDiscarded = '';
  let auditBlankTapeUsage = '';
  let auditNotes = '';

  function getStoreInstallDay(storeId) {
    const m = (storeId || '').match(/(\d{2})[A-Z]?-/);
    return m ? (ZONE_INSTALL_DAYS[m[1]] || 7) : 7;
  }

  function ordinal(d) {
    if (d == 1 || d == 21 || d == 31) return 'st';
    if (d == 2 || d == 22) return 'nd';
    if (d == 3 || d == 23) return 'rd';
    return 'th';
  }

  function getLastInstallDate(storeId) {
    const day = getStoreInstallDay(storeId);
    const now = new Date();
    let d = new Date(now.getFullYear(), now.getMonth(), day);
    if (d > now) d.setMonth(d.getMonth() - 1);
    return d.toISOString().split('T')[0];
  }

  function getNextInstallDate(storeId) {
    const day = getStoreInstallDay(storeId);
    const now = new Date();
    let d = new Date(now.getFullYear(), now.getMonth(), day);
    if (d <= now) d.setMonth(d.getMonth() + 1);
    return d.toISOString().split('T')[0];
  }

  function getAuditDueDate(storeId) {
    // Audit is 45 days after the last install
    const lastInstall = new Date(getLastInstallDate(storeId) + 'T12:00:00');
    lastInstall.setDate(lastInstall.getDate() + 45);
    return lastInstall.toISOString().split('T')[0];
  }

  function downloadBlob(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();
  }

  function generateAuditReport() {
    const cases = parseInt(auditCases) || 0;
    const rolls = parseInt(auditRolls) || 0;
    const starting = parseInt(auditStartingCases) || 20;
    const totalRolls = (cases * 50) + rolls;
    const startingRolls = starting * 50;

    const delDate = new Date(auditDate);
    const performedDate = new Date(auditPerformedDate + 'T12:00:00');
    const daysSinceDelivery = Math.max(1, Math.floor((performedDate - delDate) / (1000 * 60 * 60 * 24)));
    const rollsUsed = startingRolls - totalRolls;
    const usagePerDay = Math.round((rollsUsed / daysSinceDelivery) * 10) / 10;
    const daysUntilRunout = usagePerDay > 0 ? Math.round((totalRolls / usagePerDay) * 10) / 10 : 999;

    const runoutDate = new Date(performedDate);
    runoutDate.setDate(runoutDate.getDate() + Math.floor(daysUntilRunout));

    const nextDelivery = new Date(auditNextShipmentDate);
    const daysUntilDelivery = Math.ceil((nextDelivery - performedDate) / (1000 * 60 * 60 * 24));
    const insufficient = daysUntilRunout < daysUntilDelivery;

    const nextDeliveryMonth = nextDelivery.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    auditReport = {
      storeNum: auditStoreNum,
      chain: store?.GroceryChain || '',
      city: store?.City || '',
      state: store?.State || '',
      deliveryDate: delDate.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }),
      startingCases: starting,
      startingRolls: startingRolls,
      currentCases: cases,
      currentRolls: rolls,
      totalRolls: totalRolls,
      rollsUsed: rollsUsed,
      daysSinceDelivery: daysSinceDelivery,
      usagePerDay: usagePerDay,
      daysUntilRunout: daysUntilRunout,
      runoutDate: runoutDate.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }),
      nextDelivery: nextDelivery.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }),
      nextDeliveryMonth: nextDeliveryMonth,
      daysUntilDelivery: daysUntilDelivery,
      insufficient: insufficient,
      oldCasesDiscarded: parseInt(auditOldCasesDiscarded) || 0,
      blankTapeUsage: parseInt(auditBlankTapeUsage) || 0,
      notes: auditNotes.trim()
    };
    auditStep = 4;
  }

  async function downloadAuditPdf() {
    try {
      const r = auditReport;
      const repName = $user?.name || $user?.first_name || 'Rep';

      const pdfDoc = await PDFDocument.create();
      const page = pdfDoc.addPage([612, 792]);
      const bold = await pdfDoc.embedFont('Helvetica-Bold');
      const reg = await pdfDoc.embedFont('Helvetica');

      page.drawRectangle({ x: 0, y: 700, width: 612, height: 92, color: rgb(0.8, 0, 0) });
      page.drawText('STORE AUDIT REPORT', { x: 30, y: 740, size: 22, font: bold, color: rgb(1, 1, 1) });
      page.drawText(r.storeNum, { x: 30, y: 715, size: 14, font: reg, color: rgb(1, 1, 1) });

      let y = 670;
      const section = (title) => {
        y -= 10;
        page.drawText(title, { x: 40, y, size: 13, font: bold, color: rgb(0.1, 0.1, 0.1) });
        y -= 22;
      };
      const line = (label, value) => {
        page.drawText(label, { x: 50, y, size: 11, font: reg, color: rgb(0.3, 0.3, 0.3) });
        page.drawText(String(value), { x: 220, y, size: 11, font: reg, color: rgb(0.1, 0.1, 0.1) });
        y -= 20;
      };

      line('Store:', `${r.chain} - ${r.city}, ${r.state}`);
      line('Rep:', repName);
      line('Audit Date:', new Date(auditPerformedDate + 'T12:00:00').toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }));

      section('DELIVERY');
      line('Delivery Date:', r.deliveryDate);
      line('Starting:', `${r.startingCases} cases (${r.startingRolls.toLocaleString()} rolls)`);

      section('CURRENT INVENTORY');
      line('Full Cases:', String(r.currentCases));
      line('Loose Rolls:', String(r.currentRolls));
      line('Total Rolls:', String(r.totalRolls));

      section('PROJECTION');
      line('Rolls Used:', `${r.rollsUsed} in ${r.daysSinceDelivery} days`);
      line('Usage Rate:', `${r.usagePerDay} rolls/day`);
      line('Days Until Runout:', String(r.daysUntilRunout));
      line('Est. Runout Date:', r.runoutDate);
      line('Next Delivery:', `${r.nextDelivery} (${r.daysUntilDelivery} days)`);

      if (r.oldCasesDiscarded > 0 || r.blankTapeUsage > 0) {
        section('ADDITIONAL');
        if (r.oldCasesDiscarded > 0) line('Old Cases Discarded:', String(r.oldCasesDiscarded));
        if (r.blankTapeUsage > 0) line('Blank Tape Usage:', `${r.blankTapeUsage} rolls`);
      }

      if (r.notes) {
        section('NOTES');
        const words = r.notes.split(' ');
        let noteLine = '';
        for (const word of words) {
          if ((noteLine + ' ' + word).length > 80) {
            page.drawText(noteLine.trim(), { x: 50, y, size: 10, font: reg, color: rgb(0.2, 0.2, 0.2) });
            y -= 14;
            noteLine = word;
          } else {
            noteLine += ' ' + word;
          }
        }
        if (noteLine.trim()) {
          page.drawText(noteLine.trim(), { x: 50, y, size: 10, font: reg, color: rgb(0.2, 0.2, 0.2) });
          y -= 14;
        }
      }

      y -= 15;
      const statusText = r.insufficient
        ? 'INSUFFICIENT: Inventory will run out BEFORE next delivery! Action needed.'
        : 'SUFFICIENT: Inventory will last until next delivery.';
      const statusColor = r.insufficient ? rgb(0.8, 0, 0) : rgb(0, 0.5, 0);
      page.drawText(statusText, { x: 40, y, size: 12, font: bold, color: statusColor });

      page.drawText(`Generated ${new Date().toLocaleString()} - IndoorMedia Audit Tool`, {
        x: 150, y: 20, size: 8, font: reg, color: rgb(0.6, 0.6, 0.6)
      });

      const pdfBytes = await pdfDoc.save();
      downloadBlob(new Blob([pdfBytes], { type: 'application/pdf' }), `Audit_${r.storeNum}.pdf`);
    } catch (err) {
      alert('Error: ' + err.message);
      console.error(err);
    }
  }

  function close() {
    dispatch('close');
  }
</script>

<div class="audit-overlay" on:click|self={close}>
  <div class="audit-modal">
    <button class="audit-close" on:click={close} aria-label="Close">✕</button>

    {#if auditStep === 2}
      <h2>📋 Audit: {auditStoreNum}</h2>
      <p class="subtitle">{store?.GroceryChain} - {store?.City}</p>

      <div class="form-card">
        <p class="form-label">📅 Dates</p>
        <p class="hint" style="margin-bottom:10px;">📍 Zone install day: <strong>{getStoreInstallDay(auditStoreNum)}{ordinal(getStoreInstallDay(auditStoreNum))} of each month</strong> | Audit due: <strong>{new Date(getAuditDueDate(auditStoreNum) + 'T12:00:00').toLocaleDateString('en-US', {month:'short', day:'numeric'})}</strong> (45 days post-install)</p>
        {#if cycleInfo}
          <p class="hint" style="margin-bottom:10px;">🔄 Cycle <strong>{cycleInfo.cycle}</strong> — new ad cycle starts <strong>{cycleInfo.startMonths}</strong>{#if cycleInfo.currentStart} | current: <strong>{cycleInfo.currentStart.toLocaleDateString('en-US',{month:'short',year:'numeric'})}</strong>, next: <strong>{cycleInfo.nextStart.toLocaleDateString('en-US',{month:'short',year:'numeric'})}</strong>{/if}</p>
        {/if}

        <div class="form-group">
          <label>Date Audit Performed *</label>
          <input type="date" bind:value={auditPerformedDate} required />
        </div>

        <div class="form-group">
          <label>Last Delivery/Install Date *</label>
          <input type="date" bind:value={auditDate} required />
          <p class="hint">Auto-set from zone schedule — adjust if different</p>
        </div>

        <div class="form-group">
          <label>Next Shipment/Install Date *</label>
          <input type="date" bind:value={auditNextShipmentDate} required />
          <p class="hint">Auto-set from zone schedule — next {getStoreInstallDay(auditStoreNum)}{ordinal(getStoreInstallDay(auditStoreNum))}</p>
        </div>

        <button class="action-btn" on:click={() => auditStep = 3} disabled={!auditDate || !auditNextShipmentDate}>
          Continue to Inventory
        </button>
      </div>

    {:else if auditStep === 3}
      <h2>📋 Audit: {auditStoreNum}</h2>
      <p class="subtitle">{store?.GroceryChain} - {store?.City}</p>

      <div class="form-card">
        <p class="form-label">📦 Current Inventory</p>

        <div class="form-group">
          <label>Starting Cases (at delivery)</label>
          <input type="number" bind:value={auditStartingCases} min="0" max="50" placeholder="e.g., 20" />
        </div>

        <div class="form-group">
          <label>Full Cases Currently</label>
          <input type="number" bind:value={auditCases} min="0" max="50" placeholder="0-50" />
        </div>

        <div class="form-group">
          <label>Loose Rolls Currently</label>
          <input type="number" bind:value={auditRolls} min="0" max="49" placeholder="0-49" />
        </div>

        <div class="form-group">
          <label>🗑️ Old Cases Discarded</label>
          <input type="number" bind:value={auditOldCasesDiscarded} min="0" max="50" placeholder="0" />
        </div>

        <div class="form-group">
          <label>📋 Blank Tape Usage</label>
          <input type="number" bind:value={auditBlankTapeUsage} min="0" max="50" placeholder="Rolls used for blank tape" />
        </div>

        <div class="form-group">
          <label>📝 Notes</label>
          <textarea bind:value={auditNotes} rows="3" placeholder="Any observations, issues, or comments..."></textarea>
        </div>

        <button class="action-btn" on:click={generateAuditReport} disabled={!auditCases && auditCases !== 0}>
          Generate Audit Report
        </button>

        <button class="back-btn" on:click={() => auditStep = 2}>← Back to Dates</button>
      </div>

    {:else if auditStep === 4 && auditReport}
      <h2>📋 Audit Report</h2>

      <div class="report-card">
        <div class="report-header">{auditReport.storeNum}</div>
        <p class="report-chain">{auditReport.chain} - {auditReport.city}</p>

        <div class="report-section">
          <h4>Delivery</h4>
          <p>Date: {auditReport.deliveryDate}</p>
          <p>Starting: {auditReport.startingCases} cases ({auditReport.startingRolls} rolls)</p>
        </div>

        <div class="report-section">
          <h4>Current Inventory</h4>
          <p>{auditReport.currentCases} cases + {auditReport.currentRolls} rolls = {auditReport.totalRolls} total rolls</p>
        </div>

        <div class="report-section">
          <h4>Projection</h4>
          <p>Rolls used: {auditReport.rollsUsed} in {auditReport.daysSinceDelivery} days</p>
          <p>Usage rate: {auditReport.usagePerDay} rolls/day</p>
          <p>Days until runout: {auditReport.daysUntilRunout}</p>
          <p>Est. runout date: {auditReport.runoutDate}</p>
          <p class="next-delivery-highlight">📅 Next delivery: <strong>{auditReport.nextDeliveryMonth}</strong></p>
          <p class="next-delivery-detail">({auditReport.nextDelivery}, {auditReport.daysUntilDelivery} days away)</p>
        </div>

        {#if auditReport.oldCasesDiscarded > 0 || auditReport.blankTapeUsage > 0}
          <div class="report-section">
            <h4>Additional</h4>
            {#if auditReport.oldCasesDiscarded > 0}<p>🗑️ Old cases discarded: {auditReport.oldCasesDiscarded}</p>{/if}
            {#if auditReport.blankTapeUsage > 0}<p>📋 Blank tape usage: {auditReport.blankTapeUsage} rolls</p>{/if}
          </div>
        {/if}

        {#if auditReport.notes}
          <div class="report-section">
            <h4>📝 Notes</h4>
            <p style="white-space: pre-wrap;">{auditReport.notes}</p>
          </div>
        {/if}

        <div class="report-status" class:status-ok={!auditReport.insufficient} class:status-warn={auditReport.insufficient}>
          {auditReport.insufficient ? 'INSUFFICIENT: Inventory may run out before next delivery!' : 'SUFFICIENT: Inventory should last until next delivery.'}
        </div>

        <button class="action-btn" on:click={downloadAuditPdf}>Download Audit PDF</button>
        <button class="edit-btn" on:click={() => auditStep = 2}>Edit</button>
      </div>
    {/if}
  </div>
</div>

<style>
  .audit-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
    display: flex;
    align-items: flex-start;
    justify-content: center;
    z-index: 1000;
    padding: 20px 12px;
    overflow-y: auto;
  }
  .audit-modal {
    position: relative;
    background: var(--card-bg, #fff);
    color: var(--text-primary, #111);
    border-radius: 16px;
    width: 100%;
    max-width: 520px;
    padding: 22px 20px 26px;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
    margin: auto 0;
  }
  .audit-close {
    position: absolute;
    top: 12px;
    right: 12px;
    width: 34px;
    height: 34px;
    border: none;
    border-radius: 50%;
    background: var(--border-color, #eee);
    color: var(--text-primary, #333);
    font-size: 16px;
    cursor: pointer;
    line-height: 1;
  }
  h2 { margin: 0 8px 4px 0; font-size: 20px; }
  .subtitle { margin: 0 0 16px; color: var(--text-secondary, #777); font-size: 14px; }
  .form-card { background: var(--bg-secondary, #f7f7f8); border-radius: 12px; padding: 16px; }
  .form-label { font-weight: 700; margin: 0 0 10px; }
  .form-group { margin-bottom: 14px; }
  .form-group label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 5px; }
  .form-group input, .form-group textarea {
    width: 100%; padding: 10px; border-radius: 8px;
    border: 1px solid var(--border-color, #ddd);
    background: var(--card-bg, #fff); color: var(--text-primary, #111);
    font-family: inherit; font-size: 14px; box-sizing: border-box; resize: vertical;
  }
  .hint { font-size: 12px; color: var(--text-secondary, #888); margin: 4px 0 0; }
  .action-btn {
    width: 100%; padding: 13px; border: none; border-radius: 10px;
    background: #cc0000; color: #fff; font-weight: 700; font-size: 15px;
    cursor: pointer; margin-top: 6px;
  }
  .action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .back-btn, .edit-btn {
    width: 100%; padding: 11px; border: 1px solid var(--border-color, #ddd);
    border-radius: 10px; background: transparent; color: var(--text-primary, #333);
    font-weight: 600; font-size: 14px; cursor: pointer; margin-top: 8px;
  }
  .report-card { background: var(--bg-secondary, #f7f7f8); border-radius: 12px; padding: 16px; }
  .report-header { font-size: 20px; font-weight: 800; }
  .report-chain { margin: 2px 0 14px; color: var(--text-secondary, #777); }
  .report-section { border-top: 1px solid var(--border-color, #e5e5e5); padding-top: 10px; margin-top: 10px; }
  .report-section h4 { margin: 0 0 6px; font-size: 14px; }
  .report-section p { margin: 3px 0; font-size: 14px; }
  .next-delivery-highlight { color: #cc0000; }
  .next-delivery-detail { font-size: 12px; color: var(--text-secondary, #888); }
  .report-status { margin-top: 14px; padding: 12px; border-radius: 10px; font-weight: 700; text-align: center; }
  .status-ok { background: rgba(0, 150, 0, 0.12); color: #0a7a0a; }
  .status-warn { background: rgba(204, 0, 0, 0.12); color: #cc0000; }
</style>
