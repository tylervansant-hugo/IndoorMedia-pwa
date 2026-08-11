// IndoorMedia contract PDF generator.
// Recreates the layout of existing IndoorMedia contracts (main agreement page +
// payment schedule) and appends the real Terms & Conditions pages copied from a
// bundled template PDF (public/data/terms_template.pdf) so the legal text is
// byte-identical to current contracts.
//
// New contracts follow the current naming structure but end in the letters
// IMPRO:  <PREFIX><6 digits>IMPRO   e.g.  J435231IMPRO
//
// Usage:
//   import { generateContractPdf, nextContractNumber } from '../lib/contractGenerator.js';
//   const { blob, filename, contractNumber } = await generateContractPdf(data);

import { PDFDocument, rgb, StandardFonts } from 'pdf-lib';

const RED = rgb(0.8, 0, 0);
const NAVY = rgb(0.11, 0.15, 0.36);
const BLACK = rgb(0.1, 0.1, 0.1);
const GRAY = rgb(0.42, 0.42, 0.42);
const LIGHTGRAY = rgb(0.9, 0.9, 0.92);
const HEADERGRAY = rgb(0.86, 0.86, 0.88);
const WHITE = rgb(1, 1, 1);

const PAGE_W = 612;
const PAGE_H = 792;
const M = 40; // page margin

// Strip characters the WinAnsi StandardFonts can't encode (smart quotes, arrows,
// emoji, etc.) so drawText never throws. Maps common smart punctuation to ASCII.
function san(s) {
  if (s == null) return '';
  return String(s)
    .replace(/[\u2018\u2019\u201A\u201B]/g, "'")
    .replace(/[\u201C\u201D\u201E\u201F]/g, '"')
    .replace(/[\u2013\u2014]/g, '-')
    .replace(/\u2026/g, '...')
    .replace(/[^\x20-\x7E]/g, '');
}

// ── Contract numbering ────────────────────────────────────────
// Given the list of existing contract numbers, produce the next one with the
// IMPRO suffix. Keeps the alpha prefix of the highest existing number and
// increments the 6-digit core; falls back to a timestamp-based core if none.
export function nextContractNumber(existingNumbers, prefix) {
  let maxCore = 0;
  let bestPrefix = prefix || 'J';
  for (const n of existingNumbers || []) {
    const m = String(n).match(/^([A-Z]+)(\d{4,7})/);
    if (m) {
      const core = parseInt(m[2], 10);
      if (core > maxCore) { maxCore = core; if (!prefix) bestPrefix = m[1]; }
    }
  }
  const core = maxCore > 0 ? maxCore + 1 : (400000 + Math.floor((Date.now() / 1000) % 99999));
  return `${bestPrefix}${String(core).padStart(6, '0')}IMPRO`;
}

function money(n) {
  const v = Number(n) || 0;
  return '$' + v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Word-wrap a string to a max pixel width for a given font/size.
function wrap(text, font, size, maxW) {
  const words = san(text).split(/\s+/);
  const lines = [];
  let line = '';
  for (const w of words) {
    const test = line ? line + ' ' + w : w;
    if (font.widthOfTextAtSize(test, size) > maxW && line) { lines.push(line); line = w; }
    else line = test;
  }
  if (line) lines.push(line);
  return lines;
}

// Build a payment schedule (monthly) from total + deposit + first date.
function buildSchedule(total, months, depositAmt, firstDateStr) {
  const rows = [];
  const t = Number(total) || 0;
  const n = Math.max(1, Number(months) || 12);
  const start = firstDateStr ? new Date(firstDateStr + 'T12:00:00') : new Date();
  const deposit = Number(depositAmt) || +(t / n).toFixed(2);
  const remaining = t - deposit;
  const per = +(remaining / (n - 1 || 1)).toFixed(2);
  let running = 0;
  for (let i = 0; i < n; i++) {
    const d = new Date(start);
    d.setMonth(d.getMonth() + i);
    let amt = i === 0 ? deposit : per;
    running += amt;
    // Fix rounding on the final payment.
    if (i === n - 1) { amt = +(t - (running - amt)).toFixed(2); }
    rows.push({
      date: d.toISOString().slice(0, 10),
      amount: amt,
      tax: 0,
      total: amt,
    });
  }
  return rows;
}

// ── Main generator ────────────────────────────────────────────
// data fields:
//   contractNumber, businessName, contactName, contactEmail, contactPhone,
//   billingAddress, city, state, zip,
//   repName, repEmail, repPhone,
//   isNewCustomer (bool), digitalIntegration (bool),
//   billingType, paymentFrequency,
//   items: [{ product, storeName, storeNumber, zone, address, startInfo, adType, quarters, price }]
//   depositAmount, firstPaymentDate, termMonths, salesTax,
//   companyAddress (default Houston HQ)
export async function generateContractPdf(data) {
  const d = data || {};
  const pdf = await PDFDocument.create();
  const bold = await pdf.embedFont(StandardFonts.HelveticaBold);
  const reg = await pdf.embedFont(StandardFonts.Helvetica);

  // Wrap every page's drawText through the sanitizer.
  const guard = (pg) => {
    const orig = pg.drawText.bind(pg);
    pg.drawText = (txt, opts) => orig(san(txt), opts);
    return pg;
  };

  const contractNumber = d.contractNumber || 'PENDINGIMPRO';
  const items = Array.isArray(d.items) && d.items.length ? d.items : [{ product: 'Register Tape', price: 0 }];
  const net = items.reduce((s, it) => s + (Number(it.price) || 0), 0);
  const tax = Number(d.salesTax) || 0;
  const total = net + tax;
  const companyAddr = d.companyAddress || '1445 Langham Creek Dr, Houston, TX 77084';

  // Try to embed the logo (public/logo.png). Non-fatal if it fails.
  let logoImg = null;
  try {
    const res = await fetch(import.meta.env.BASE_URL + 'logo.png');
    if (res.ok) { logoImg = await pdf.embedPng(await res.arrayBuffer()); }
  } catch { /* logo optional */ }

  // ════ PAGE 1 — Main agreement ════
  const page = guard(pdf.addPage([PAGE_W, PAGE_H]));
  let y = PAGE_H - M;

  // Header: logo tile (top-left) + contract number (top-right)
  if (logoImg) {
    const lw = 54, lh = 54;
    page.drawImage(logoImg, { x: M, y: y - lh, width: lw, height: lh });
    page.drawText('IndoorMedia', { x: M, y: y - lh - 14, size: 11, font: bold, color: NAVY });
  } else {
    page.drawText('IndoorMedia', { x: M, y: y - 18, size: 18, font: bold, color: NAVY });
  }
  page.drawText('Contract #:', { x: PAGE_W - M - 220, y: y - 12, size: 11, font: bold, color: BLACK });
  page.drawText(contractNumber, { x: PAGE_W - M - 140, y: y - 14, size: 15, font: bold, color: GRAY });

  page.drawText(companyAddr, { x: M, y: y - 82, size: 9, font: bold, color: BLACK });
  page.drawText('Sales Representative:', { x: M, y: y - 98, size: 9, font: bold, color: BLACK });
  const repLine = [d.repName, d.repEmail, d.repPhone].filter(Boolean).join('  |  ');
  page.drawText(repLine, { x: M, y: y - 111, size: 9, font: reg, color: GRAY });

  // Divider
  y = y - 122;
  page.drawLine({ start: { x: M, y }, end: { x: PAGE_W - M, y }, thickness: 1, color: LIGHTGRAY });

  // Info region: left = Customer, right = Billing
  y -= 22;
  const colR = PAGE_W / 2 + 20;
  page.drawText('Customer Information', { x: M, y, size: 12, font: bold, color: GRAY });
  page.drawText('Billing Information', { x: colR, y, size: 12, font: bold, color: GRAY });
  y -= 18;

  const custLines = [
    d.businessName, d.contactName, d.contactEmail, d.contactPhone,
    d.billingAddress,
    [d.city, d.state].filter(Boolean).join(', ') + (d.zip ? ' ' + d.zip : ''),
  ].filter(Boolean);
  let cy = y;
  for (const line of custLines) {
    page.drawText(line, { x: M, y: cy, size: 10, font: reg, color: BLACK });
    cy -= 15;
  }
  // checkboxes under customer
  cy -= 4;
  page.drawText('New Customer: ' + (d.isNewCustomer ? '[X]' : '[ ]'), { x: M, y: cy, size: 10, font: reg, color: BLACK });
  cy -= 15;
  page.drawText('Digital Integration: ' + (d.digitalIntegration ? '[X]' : '[ ]'), { x: M, y: cy, size: 10, font: reg, color: BLACK });

  // billing column
  let by = y;
  page.drawText('Billing Type: ' + (d.billingType || 'Credit Card'), { x: colR, y: by, size: 10, font: reg, color: BLACK });
  by -= 15;
  page.drawText('Payment Frequency: ' + (d.paymentFrequency || 'monthly'), { x: colR, y: by, size: 10, font: reg, color: BLACK });
  by -= 18;
  const deposit = Number(d.depositAmount) || +(total / (Number(d.termMonths) || 12)).toFixed(2);
  const firstDate = d.firstPaymentDate || new Date().toISOString().slice(0, 10);
  const remaining = +(total - deposit).toFixed(2);
  const nExtra = (Number(d.termMonths) || 12) - 1;
  const billPara = `A deposit in the amount of ${money(deposit)} is to be paid on ${firstDate}. The remaining balance of ${money(remaining)} will be paid in ${nExtra} additional payments. See detailed payment schedule on the final page.`;
  for (const l of wrap(billPara, reg, 9, PAGE_W - M - colR)) {
    page.drawText(l, { x: colR, y: by, size: 9, font: reg, color: BLACK });
    by -= 12;
  }

  // Product/pricing table
  y = Math.min(cy, by) - 26;
  const tX = M, tW = PAGE_W - 2 * M;
  const cProd = tX + 6, cDesc = tX + 120, cPrice = tX + tW - 6;
  page.drawRectangle({ x: tX, y: y - 4, width: tW, height: 20, color: HEADERGRAY });
  page.drawText('Product', { x: cProd, y, size: 10, font: bold, color: BLACK });
  page.drawText('Description', { x: cDesc, y, size: 10, font: bold, color: BLACK });
  page.drawText('Price', { x: cPrice - bold.widthOfTextAtSize('Price', 10), y, size: 10, font: bold, color: BLACK });
  y -= 24;

  for (const it of items) {
    const descLines = [];
    if (it.storeName || it.storeNumber || it.zone) {
      descLines.push([it.storeName, it.storeNumber ? '#' + it.storeNumber : '', it.zone ? '(' + it.zone + ')' : ''].filter(Boolean).join(' '));
    }
    if (it.address) descLines.push(it.address);
    if (it.startInfo) descLines.push('Est. Start: ' + it.startInfo);
    const adBits = [it.adType, it.quarters ? it.quarters + ' quarter' + (it.quarters > 1 ? 's' : '') : ''].filter(Boolean).join(', ');
    if (adBits) descLines.push(adBits);

    const rowH = Math.max(16, descLines.length * 12 + 4);
    page.drawText(it.product || 'Register Tape', { x: cProd, y, size: 10, font: bold, color: BLACK });
    let dy = y;
    for (const dl of descLines) {
      for (const wl of wrap(dl, reg, 9, cPrice - cDesc - 60)) {
        page.drawText(wl, { x: cDesc, y: dy, size: 9, font: reg, color: GRAY });
        dy -= 12;
      }
    }
    const priceStr = money(it.price);
    page.drawText(priceStr, { x: cPrice - bold.widthOfTextAtSize(priceStr, 10), y, size: 10, font: bold, color: BLACK });
    y = Math.min(y - rowH, dy - 4);
    page.drawLine({ start: { x: tX, y: y + 6 }, end: { x: tX + tW, y: y + 6 }, thickness: 0.5, color: LIGHTGRAY });
  }

  // Summary rows
  y -= 6;
  const sumRow = (label, val, emphasize) => {
    const f = emphasize ? bold : reg;
    const sz = emphasize ? 12 : 10;
    page.drawText(label, { x: cPrice - 200, y, size: sz, font: bold, color: BLACK });
    const vs = money(val);
    page.drawText(vs, { x: cPrice - f.widthOfTextAtSize(vs, sz), y, size: sz, font: f, color: emphasize ? RED : BLACK });
    y -= emphasize ? 20 : 16;
  };
  sumRow('Net Price', net, false);
  sumRow('Sales Tax', tax, false);
  sumRow('Contract Total', total, true);

  // Terms acknowledgment
  y -= 8;
  const ackText = 'All terms are listed on the following pages of this contract. I have read all terms of the contract and understand that this is: 1) not a consumer contract, 2) there is no right of rescission, 3) the contract is non-cancellable and there is no early termination or voiding of this contract.  Advertiser initials: ' + (d.initials || 'E-SIGNATURE');
  for (const l of wrap(ackText, reg, 8.5, tW)) {
    page.drawText(l, { x: M, y, size: 8.5, font: reg, color: BLACK });
    y -= 11;
  }

  // Signature block
  y -= 14;
  const sigRow = (label, value) => {
    page.drawText(label, { x: M, y, size: 10, font: bold, color: BLACK });
    const lineX = M + 190;
    page.drawLine({ start: { x: lineX, y: y - 2 }, end: { x: PAGE_W - M, y: y - 2 }, thickness: 0.7, color: GRAY });
    if (value) page.drawText(value, { x: lineX + 8, y, size: 10, font: reg, color: BLACK });
    y -= 26;
  };
  sigRow("Advertiser's Business Name:", d.businessName || '');
  sigRow("Advertiser's Printed Name:", d.signerName || d.contactName || '');

  // Signature: prefer a drawn e-signature image; fall back to typed text.
  page.drawText("Advertiser's Signature:", { x: M, y, size: 10, font: bold, color: BLACK });
  const sigLineX = M + 190;
  page.drawLine({ start: { x: sigLineX, y: y - 2 }, end: { x: PAGE_W - M, y: y - 2 }, thickness: 0.7, color: GRAY });
  if (d.signatureImage && /^data:image\//.test(d.signatureImage)) {
    try {
      const sigPng = await pdf.embedPng(await (await fetch(d.signatureImage)).arrayBuffer());
      const maxW = PAGE_W - M - sigLineX - 10;
      const maxH = 34;
      const scale = Math.min(maxW / sigPng.width, maxH / sigPng.height);
      const w = sigPng.width * scale, h = sigPng.height * scale;
      page.drawImage(sigPng, { x: sigLineX + 8, y: y - 4, width: w, height: h });
    } catch { if (d.signature) page.drawText(d.signature, { x: sigLineX + 8, y, size: 10, font: reg, color: BLACK }); }
  } else if (d.signature) {
    page.drawText(d.signature, { x: sigLineX + 8, y, size: 10, font: reg, color: BLACK });
  }
  y -= 26;
  if (d.signedDate) {
    page.drawText('Date Signed: ' + d.signedDate, { x: M, y, size: 9, font: reg, color: GRAY });
    y -= 18;
  }

  // Footer
  page.drawText('IndoorMedia  |  indoormedia.com', {
    x: PAGE_W / 2 - reg.widthOfTextAtSize('IndoorMedia  |  indoormedia.com', 9) / 2,
    y: 28, size: 9, font: reg, color: GRAY,
  });

  // ════ T&C pages — copied from the bundled template, restamped ════
  try {
    const res = await fetch(import.meta.env.BASE_URL + 'data/terms_template.pdf');
    if (res.ok) {
      const tmpl = await PDFDocument.load(await res.arrayBuffer());
      const copied = await pdf.copyPages(tmpl, tmpl.getPageIndices());
      for (const p of copied) {
        pdf.addPage(p);
        const gp = guard(p);
        // Use the copied page's OWN dimensions (the template T&C pages are A4,
        // not US Letter) so the corner cover/stamp lands correctly.
        const pw = p.getWidth();
        const ph = p.getHeight();
        // Cover the old contract-number corner label and stamp the new one.
        gp.drawRectangle({ x: pw - M - 160, y: ph - 34, width: 160, height: 22, color: WHITE });
        gp.drawText(contractNumber, { x: pw - M - bold.widthOfTextAtSize(contractNumber, 10), y: ph - 28, size: 10, font: bold, color: BLACK });
      }
    }
  } catch { /* T&C optional but expected */ }

  // ════ Payment Details page (card/bank + voided check) ════
  const pmt = d.paymentDetails;
  if (pmt && (pmt.method === 'card' || pmt.method === 'bank' || pmt.voidedCheck)) {
    const pp = guard(pdf.addPage([PAGE_W, PAGE_H]));
    pp.drawText(contractNumber, { x: PAGE_W - M - bold.widthOfTextAtSize(contractNumber, 10), y: PAGE_H - 28, size: 10, font: bold, color: BLACK });
    const ptitle = 'Payment Details';
    pp.drawText(ptitle, { x: PAGE_W / 2 - bold.widthOfTextAtSize(ptitle, 20) / 2, y: PAGE_H - 90, size: 20, font: bold, color: GRAY });
    let py = PAGE_H - 132;
    const mask = (s) => { s = String(s || '').replace(/\s/g, ''); return s.length > 4 ? '•••• •••• •••• ' + s.slice(-4) : s; };
    const drow = (lbl, val) => {
      pp.drawText(lbl, { x: M, y: py, size: 11, font: bold, color: BLACK });
      pp.drawText(String(val || '—'), { x: M + 170, y: py, size: 11, font: reg, color: BLACK });
      py -= 22;
    };
    if (pmt.method === 'card') {
      pp.drawText('Credit / Debit Card', { x: M, y: py, size: 13, font: bold, color: NAVY }); py -= 24;
      drow('Cardholder Name', pmt.card?.name);
      drow('Card Number', mask(pmt.card?.number));
      drow('Expiration', pmt.card?.exp);
      drow('CVV', pmt.card?.cvv ? '•••' : '—');
      drow('Billing Zip', pmt.card?.zip);
    } else if (pmt.method === 'bank') {
      pp.drawText('Bank / ACH', { x: M, y: py, size: 13, font: bold, color: NAVY }); py -= 24;
      drow('Name on Account', pmt.bank?.name);
      drow('Account Type', pmt.bank?.accountType);
      drow('Routing Number', pmt.bank?.routing);
      const acct = String(pmt.bank?.account || '');
      drow('Account Number', acct.length > 4 ? '••••••' + acct.slice(-4) : acct);
    }
    if (pmt.voidedCheck && /^data:image\//.test(pmt.voidedCheck)) {
      py -= 10;
      pp.drawText('Voided Check', { x: M, y: py, size: 13, font: bold, color: NAVY }); py -= 14;
      try {
        const isPng = /^data:image\/png/.test(pmt.voidedCheck);
        const buf = await (await fetch(pmt.voidedCheck)).arrayBuffer();
        const chkImg = isPng ? await pdf.embedPng(buf) : await pdf.embedJpg(buf);
        const maxW = PAGE_W - 2 * M, maxH = 260;
        const scale = Math.min(maxW / chkImg.width, maxH / chkImg.height);
        const w = chkImg.width * scale, h = chkImg.height * scale;
        pp.drawImage(chkImg, { x: M, y: py - h, width: w, height: h });
      } catch { /* image optional */ }
    }
  }

  // ════ Payment Schedule page ════
  const sched = buildSchedule(total, Number(d.termMonths) || 12, deposit, firstDate);
  const sp = guard(pdf.addPage([PAGE_W, PAGE_H]));
  sp.drawText(contractNumber, { x: PAGE_W - M - bold.widthOfTextAtSize(contractNumber, 10), y: PAGE_H - 28, size: 10, font: bold, color: BLACK });
  const title = 'Payment Schedule';
  sp.drawText(title, { x: PAGE_W / 2 - bold.widthOfTextAtSize(title, 20) / 2, y: PAGE_H - 90, size: 20, font: bold, color: GRAY });

  let sy = PAGE_H - 130;
  const scX = M + 60, scW = PAGE_W - 2 * (M + 60);
  const colDate = scX + 10, colAmt = scX + scW * 0.42, colTax = scX + scW * 0.66, colTot = scX + scW - 10;
  sp.drawRectangle({ x: scX, y: sy - 4, width: scW, height: 22, color: HEADERGRAY });
  sp.drawText('Payment Date', { x: colDate, y: sy, size: 10, font: bold, color: BLACK });
  sp.drawText('Amount', { x: colAmt, y: sy, size: 10, font: bold, color: BLACK });
  sp.drawText('Sales Tax', { x: colTax, y: sy, size: 10, font: bold, color: BLACK });
  sp.drawText('Total', { x: colTot - bold.widthOfTextAtSize('Total', 10), y: sy, size: 10, font: bold, color: BLACK });
  sy -= 24;
  let shade = false;
  for (const r of sched) {
    if (shade) sp.drawRectangle({ x: scX, y: sy - 4, width: scW, height: 18, color: rgb(0.96, 0.96, 0.97) });
    shade = !shade;
    sp.drawText(r.date, { x: colDate, y: sy, size: 10, font: reg, color: BLACK });
    sp.drawText(money(r.amount), { x: colAmt, y: sy, size: 10, font: reg, color: BLACK });
    sp.drawText(money(r.tax), { x: colTax, y: sy, size: 10, font: reg, color: BLACK });
    const ts = money(r.total);
    sp.drawText(ts, { x: colTot - reg.widthOfTextAtSize(ts, 10), y: sy, size: 10, font: reg, color: BLACK });
    sy -= 18;
  }

  const bytes = await pdf.save();
  const blob = new Blob([bytes], { type: 'application/pdf' });
  return { blob, bytes, filename: `${contractNumber}.pdf`, contractNumber };
}
