// Client-side Counter Sign PDF generator.
// Replaces the dead backend (Cloudflare tunnel + Flask). Overlays content onto
// per-chain fillable PDF templates using pdf-lib. Layout mirrors
// scripts/counter_sign_generator.py exactly (letter 612x792, origin bottom-left).

import { PDFDocument, rgb } from 'pdf-lib';
import QRCode from 'qrcode';

// ===== Constants (from the Python source) =====
const LETTER_WIDTH = 612.0;
const LETTER_HEIGHT = 792.0;

// QR code (classic)
const QR_CODE_X_MIN = 484.4;
const QR_CODE_Y_MIN = 22.7;
const QR_CODE_SIZE = 109.9;

// White background box behind QR (classic)
const QR_BG_X_MIN = 470.0;
const QR_BG_Y_MIN = 10.0;
const QR_BG_SIZE = 140.0;

// Business card bottom-left (classic)
const BC_X_BOTTOM = 9.2;
const BC_Y_BOTTOM = 10.0;
const BC_WIDTH = 126.72;
const BC_HEIGHT = 126.72;

// Ad grid zone
const AD_X_MARGIN = 36.0;
const AD_WIDTH = LETTER_WIDTH - 2 * AD_X_MARGIN; // 540
const GRID_Y_BOTTOM = 150.0;
const GRID_Y_TOP = 430.0;
const GRID_HEIGHT = GRID_Y_TOP - GRID_Y_BOTTOM; // 280
const GRID_GAP = 10.0;

// Clean footer
const CLEAN_FOOTER_HEIGHT = 155.0;
const CLEAN_FOOTER_Y = 0.0;
const CLEAN_FOOTER_COLOR = rgb(0.6, 0.0, 0.0);

const BASE_URL = import.meta.env.BASE_URL;

// ---- helpers ----

function baseName(url) {
  return url;
}

async function fetchBytes(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load ${url} (${res.status})`);
  return new Uint8Array(await res.arrayBuffer());
}

async function fileToBytes(file) {
  return new Uint8Array(await file.arrayBuffer());
}

// Embed an image (File or {bytes,type}) into the doc; detect png/jpg.
async function embedImage(doc, file) {
  const bytes = file instanceof Uint8Array ? file : await fileToBytes(file);
  const type = (file && file.type) || '';
  const name = (file && file.name) || '';
  const isPng = /png/i.test(type) || /\.png$/i.test(name);
  if (isPng) {
    try { return await doc.embedPng(bytes); } catch { return await doc.embedJpg(bytes); }
  }
  try { return await doc.embedJpg(bytes); } catch { return await doc.embedPng(bytes); }
}

// Load PNG data URL bytes into doc
async function embedDataUrlPng(doc, dataUrl) {
  const b64 = dataUrl.split(',')[1];
  const bin = atob(b64);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return await doc.embedPng(arr);
}

// Grid positions (classic): mirrors calculate_grid_positions.
function calculateGridPositions(numImages) {
  if (numImages === 1) {
    const w = AD_WIDTH * 0.85;
    const h = GRID_HEIGHT * 0.85;
    const x = AD_X_MARGIN + (AD_WIDTH - w) / 2;
    const y = GRID_Y_BOTTOM + (GRID_HEIGHT - h) / 2;
    return [[x, y, w, h]];
  }
  let cols, rows;
  if (numImages <= 4) {
    cols = 2;
    rows = Math.ceil(numImages / 2);
  } else {
    cols = 3;
    rows = 2;
  }
  const usableWidth = AD_WIDTH - GRID_GAP * (cols - 1);
  const usableHeight = GRID_HEIGHT - GRID_GAP * (rows - 1);
  const cellW = usableWidth / cols;
  const cellH = usableHeight / rows;
  const positions = [];
  for (let idx = 0; idx < numImages; idx++) {
    const col = idx % cols;
    const row = Math.floor(idx / cols);
    const x = AD_X_MARGIN + col * (cellW + GRID_GAP);
    const y = GRID_Y_TOP - (row + 1) * cellH - row * GRID_GAP;
    positions.push([x, y, cellW, cellH]);
  }
  return positions;
}

// Fit an embedded image to a box preserving aspect ratio.
function fitToBox(imgW, imgH, maxW, maxH) {
  const ratio = imgW / imgH;
  const available = maxW / maxH;
  let w, h;
  if (ratio > available) {
    w = maxW;
    h = maxW / ratio;
  } else {
    h = maxH;
    w = maxH * ratio;
  }
  return [w, h];
}

async function drawAdGrid(doc, page, adImages, gridTop, gridBottom) {
  if (!adImages || adImages.length === 0) return;
  const n = Math.min(adImages.length, 6);
  const imgs = adImages.slice(0, n);

  let positions;
  const gridHeight = gridTop - gridBottom;
  if (n === 1) {
    const w = AD_WIDTH * 0.85;
    const h = gridHeight * 0.85;
    const x = AD_X_MARGIN + (AD_WIDTH - w) / 2;
    const y = gridBottom + (gridHeight - h) / 2;
    positions = [[x, y, w, h]];
  } else {
    let cols, rows;
    if (n <= 4) { cols = 2; rows = Math.ceil(n / 2); }
    else { cols = 3; rows = 2; }
    const usableW = AD_WIDTH - GRID_GAP * (cols - 1);
    const usableH = gridHeight - GRID_GAP * (rows - 1);
    const cellW = usableW / cols;
    const cellH = usableH / rows;
    positions = [];
    for (let idx = 0; idx < n; idx++) {
      const col = idx % cols;
      const row = Math.floor(idx / cols);
      const x = AD_X_MARGIN + col * (cellW + GRID_GAP);
      const y = gridTop - (row + 1) * cellH - row * GRID_GAP;
      positions.push([x, y, cellW, cellH]);
    }
  }

  for (let idx = 0; idx < imgs.length; idx++) {
    const [cellX, cellY, cellW, cellH] = positions[idx];
    const img = await embedImage(doc, imgs[idx]);
    const [fw, fh] = fitToBox(img.width, img.height, cellW * 0.95, cellH * 0.95);
    const adX = cellX + (cellW - fw) / 2;
    const adY = cellY + (cellH - fh) / 2;
    page.drawImage(img, { x: adX, y: adY, width: fw, height: fh });
  }
}

// ===== Classic overlay =====
async function overlayClassic(doc, page, { adImages, businessCard, qrDataUrl }) {
  // 1. White QR background box (drawn first)
  page.drawRectangle({
    x: QR_BG_X_MIN, y: QR_BG_Y_MIN, width: QR_BG_SIZE, height: QR_BG_SIZE,
    color: rgb(1, 1, 1),
  });

  // 2. Ad images grid
  await drawAdGrid(doc, page, adImages, GRID_Y_TOP, GRID_Y_BOTTOM);

  // 3. Business card bottom-left
  if (businessCard) {
    const bc = await embedImage(doc, businessCard);
    const ratio = bc.width / bc.height;
    let fw, fh;
    if (ratio > 1) { fw = BC_WIDTH; fh = BC_WIDTH / ratio; }
    else { fh = BC_HEIGHT; fw = BC_HEIGHT * ratio; }
    const bcX = BC_X_BOTTOM + (BC_WIDTH - fw) / 2;
    const bcY = BC_Y_BOTTOM + (BC_HEIGHT - fh) / 2;
    page.drawImage(bc, { x: bcX, y: bcY, width: fw, height: fh });
  }

  // 4. QR code
  if (qrDataUrl) {
    const qr = await embedDataUrlPng(doc, qrDataUrl);
    page.drawImage(qr, {
      x: QR_CODE_X_MIN, y: QR_CODE_Y_MIN, width: QR_CODE_SIZE, height: QR_CODE_SIZE,
    });
  }
}

// ===== Clean overlay =====
async function overlayClean(doc, page, { adImages, businessCard, qrDataUrl, logoBytes }) {
  const pageWidth = LETTER_WIDTH;

  // 1. Dark maroon footer bar full width
  page.drawRectangle({
    x: 0, y: CLEAN_FOOTER_Y, width: pageWidth, height: CLEAN_FOOTER_HEIGHT,
    color: CLEAN_FOOTER_COLOR,
  });

  // 2. IndoorMedia logo (left)
  if (logoBytes) {
    try {
      const logo = await doc.embedPng(logoBytes);
      const logoRatio = logo.width / logo.height;
      const logoH = CLEAN_FOOTER_HEIGHT * 0.75; // 116.25
      const logoW = logoH * logoRatio;
      const logoX = 15;
      const logoY = CLEAN_FOOTER_Y + (CLEAN_FOOTER_HEIGHT - logoH) / 2;
      page.drawImage(logo, { x: logoX, y: logoY, width: logoW, height: logoH });
    } catch (e) { /* logo optional */ }
  }

  // 3. Business card (center)
  if (businessCard) {
    const bc = await embedImage(doc, businessCard);
    const bcRatio = bc.width / bc.height;
    const bcMaxW = pageWidth * 0.42; // 257.04
    const bcMaxH = CLEAN_FOOTER_HEIGHT * 0.80; // 124
    let bcW, bcH;
    if (bcRatio > bcMaxW / bcMaxH) { bcW = bcMaxW; bcH = bcW / bcRatio; }
    else { bcH = bcMaxH; bcW = bcH * bcRatio; }
    const bcX = (pageWidth - bcW) / 2;
    const bcY = CLEAN_FOOTER_Y + (CLEAN_FOOTER_HEIGHT - bcH) / 2;
    page.drawImage(bc, { x: bcX, y: bcY, width: bcW, height: bcH });
  }

  // 4. QR code (right) — maroon cover rect first, then QR
  if (qrDataUrl) {
    // cover original template QR area with footer-colored rect
    page.drawRectangle({
      x: QR_BG_X_MIN - 5, y: 0,
      width: pageWidth - QR_BG_X_MIN + 10, height: CLEAN_FOOTER_HEIGHT,
      color: CLEAN_FOOTER_COLOR,
    });
    const qrSize = CLEAN_FOOTER_HEIGHT * 0.85; // 131.75
    const qrX = pageWidth - qrSize - 5;
    const qrY = CLEAN_FOOTER_Y + (CLEAN_FOOTER_HEIGHT - qrSize) / 2;
    const qr = await embedDataUrlPng(doc, qrDataUrl);
    page.drawImage(qr, { x: qrX, y: qrY, width: qrSize, height: qrSize });
  }

  // 5. Ad images — grid zone shifted above the taller footer.
  // Python clean: clean_grid_bottom = CLEAN_FOOTER_HEIGHT + 5 (=160), clean_grid_top = 430.
  const cleanGridBottom = CLEAN_FOOTER_HEIGHT + 5;
  const cleanGridTop = 430.0;
  await drawAdGrid(doc, page, adImages, cleanGridTop, cleanGridBottom);
}

/**
 * Generate a Counter Sign PDF fully client-side.
 * @returns {Promise<Blob>} application/pdf
 */
export async function generateCounterSignPdf({
  chainCode,
  adImageFiles,
  businessCardFile,
  landingPageUrl,
  style,
  repCell,
}) {
  if (!chainCode) throw new Error('No chain selected');
  const adImages = adImageFiles || [];
  if (adImages.length === 0) throw new Error('At least one ad proof image is required');

  // 1. Resolve template via manifest
  const manifest = await (await fetch(BASE_URL + 'data/store_templates/manifest.json')).json();
  // case-insensitive lookup, matching Python glob resolution order
  let filename = manifest[chainCode] || manifest[chainCode.toUpperCase()];
  if (!filename) {
    const key = Object.keys(manifest).find(
      (k) => k.toLowerCase() === String(chainCode).toLowerCase()
    );
    if (key) filename = manifest[key];
  }
  if (!filename) throw new Error(`No template found for ${chainCode}`);

  const templateBytes = await fetchBytes(
    BASE_URL + 'data/store_templates/' + filename
  );

  // 2. Load template
  const doc = await PDFDocument.load(templateBytes);
  const page = doc.getPages()[0];

  // 3. QR content
  let qrDataUrl = null;
  if (landingPageUrl && String(landingPageUrl).toLowerCase() !== 'none' && landingPageUrl.trim()) {
    qrDataUrl = await QRCode.toDataURL(landingPageUrl, { margin: 2 });
  } else if (repCell) {
    const digits = String(repCell).replace(/[^0-9]/g, '');
    if (digits) qrDataUrl = await QRCode.toDataURL(`tel:${digits}`, { margin: 2 });
  }

  // 4. Overlay
  if (style === 'clean') {
    let logoBytes = null;
    try {
      logoBytes = await fetchBytes(BASE_URL + 'data/indoormedia_logo_clean.png');
    } catch (e) { /* optional */ }
    await overlayClean(doc, page, {
      adImages,
      businessCard: businessCardFile,
      qrDataUrl,
      logoBytes,
    });
  } else {
    await overlayClassic(doc, page, {
      adImages,
      businessCard: businessCardFile,
      qrDataUrl,
    });
  }

  // 5. Serialize
  const outBytes = await doc.save();
  return new Blob([outBytes], { type: 'application/pdf' });
}
