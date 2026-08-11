// Home Screen shortcuts + dashboard-widget order.
// Everything is stored per-device in localStorage and broadcast via custom
// events so the dashboard updates live.
//
//   home_shortcuts   -> JSON array of { id, label, icon, tab, action? }
//   home_widget_order-> JSON array of widget ids in display order
//   home_widget_hidden-> JSON array of hidden widget ids

const SHORTCUTS_KEY = 'home_shortcuts';
const ORDER_KEY = 'home_widget_order';
const HIDDEN_KEY = 'home_widget_hidden';

function read(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch { return fallback; }
}
function write(key, val) {
  try { localStorage.setItem(key, JSON.stringify(val)); } catch {}
}
function emit() {
  try { window.dispatchEvent(new CustomEvent('home-shortcuts-changed')); } catch {}
}

export function getShortcuts() {
  const list = read(SHORTCUTS_KEY, []);
  return Array.isArray(list) ? list : [];
}

export function addShortcut({ label, icon, tab, action, storesView, matchText }) {
  const list = getShortcuts();
  // De-dupe on label+tab+action+matchText so the same button isn't added twice.
  const key = `${label}|${tab}|${action || ''}|${matchText || ''}`;
  if (list.some(s => `${s.label}|${s.tab}|${s.action || ''}|${s.matchText || ''}` === key)) return { added: false, list };
  const id = 'sc_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  const next = [...list, {
    id,
    label,
    icon: icon || '⭐',
    tab: tab || 'dashboard',
    action: action || '',
    storesView: storesView || '',
    // matchText lets the shortcut re-find and click the ACTUAL button (not just
    // land on the page). Falls back to the visible label when omitted.
    matchText: matchText || label || '',
  }];
  write(SHORTCUTS_KEY, next);
  emit();
  return { added: true, list: next };
}

export function removeShortcut(id) {
  const next = getShortcuts().filter(s => s.id !== id);
  write(SHORTCUTS_KEY, next);
  emit();
  return next;
}

export function reorderShortcuts(fromIdx, toIdx) {
  const list = getShortcuts();
  if (fromIdx < 0 || fromIdx >= list.length || toIdx < 0 || toIdx >= list.length) return list;
  const next = [...list];
  const [moved] = next.splice(fromIdx, 1);
  next.splice(toIdx, 0, moved);
  write(SHORTCUTS_KEY, next);
  emit();
  return next;
}

// ── Dashboard widget order ────────────────────────────────────
export function getWidgetOrder(defaultOrder) {
  const saved = read(ORDER_KEY, null);
  if (!Array.isArray(saved) || !saved.length) return [...defaultOrder];
  // Keep the user's saved order for widgets they've already arranged, but
  // INSERT any brand-new default widgets at their default position (relative to
  // the widgets around them) instead of dumping them at the bottom. This way a
  // user upgrading from the old 4-card layout gets the new top blocks (search,
  // quick actions, shortcuts, etc.) in sensible places, not below their cards.
  const merged = saved.filter(id => defaultOrder.includes(id));
  for (let i = 0; i < defaultOrder.length; i++) {
    const id = defaultOrder[i];
    if (merged.includes(id)) continue;
    // Find the nearest preceding default widget that IS already placed, and
    // insert right after it; if none, insert at the front.
    let insertAt = 0;
    for (let j = i - 1; j >= 0; j--) {
      const prevIdx = merged.indexOf(defaultOrder[j]);
      if (prevIdx !== -1) { insertAt = prevIdx + 1; break; }
    }
    merged.splice(insertAt, 0, id);
  }
  return merged;
}
export function setWidgetOrder(order) {
  write(ORDER_KEY, order);
  emit();
}
export function reorderWidgets(order, fromIdx, toIdx) {
  if (fromIdx < 0 || fromIdx >= order.length || toIdx < 0 || toIdx >= order.length) return order;
  const next = [...order];
  const [moved] = next.splice(fromIdx, 1);
  next.splice(toIdx, 0, moved);
  setWidgetOrder(next);
  return next;
}

export function getHiddenWidgets() {
  const list = read(HIDDEN_KEY, []);
  return Array.isArray(list) ? list : [];
}
export function toggleWidgetHidden(id) {
  const hidden = getHiddenWidgets();
  const next = hidden.includes(id) ? hidden.filter(x => x !== id) : [...hidden, id];
  write(HIDDEN_KEY, next);
  emit();
  return next;
}

// ── Long-press "Add to Home Screen" action ────────────────────
// Svelte action: use:addToHome={{ label, icon, tab, action }}
// Long-press (600ms) shows a confirm chip; on confirm, saves the shortcut.
export function addToHome(node, params) {
  let timer = null;
  let startX = 0, startY = 0;
  let fired = false;
  // Mark so the global delegated handler skips this node (avoids double chips).
  try { node.setAttribute('data-has-addtohome', '1'); } catch {}

  function begin(x, y) {
    startX = x; startY = y; fired = false;
    timer = setTimeout(() => {
      fired = true;
      showPrompt();
    }, 600);
  }
  function move(x, y) {
    if (timer && (Math.abs(x - startX) > 10 || Math.abs(y - startY) > 10)) {
      clearTimeout(timer); timer = null;
    }
  }
  function end() {
    if (timer) { clearTimeout(timer); timer = null; }
  }

  function showPrompt() {
    const p = params || {};
    const label = p.label || node.textContent.trim().slice(0, 40) || 'Shortcut';
    // Lightweight in-DOM confirm chip anchored to the button.
    const existing = document.getElementById('add-to-home-chip');
    if (existing) existing.remove();
    const chip = document.createElement('div');
    chip.id = 'add-to-home-chip';
    chip.textContent = '➕ Add to Home Screen';
    Object.assign(chip.style, {
      position: 'fixed', zIndex: '3000', background: '#111', color: '#fff',
      padding: '10px 16px', borderRadius: '22px', fontSize: '14px', fontWeight: '700',
      boxShadow: '0 6px 24px rgba(0,0,0,0.4)', cursor: 'pointer', maxWidth: '80vw',
      left: '50%', bottom: 'calc(90px + env(safe-area-inset-bottom,0px))', transform: 'translateX(-50%)',
    });
    const remove = () => { chip.remove(); document.removeEventListener('click', outside, true); };
    const outside = (e) => { if (e.target !== chip) remove(); };
    chip.addEventListener('click', (e) => {
      e.stopPropagation();
      const res = addShortcut({ label: p.label || label, icon: p.icon, tab: p.tab, action: p.action });
      chip.textContent = res.added ? '✅ Added to Home Screen' : 'ℹ️ Already on Home Screen';
      chip.style.background = res.added ? '#0a7a0a' : '#555';
      setTimeout(remove, 1100);
      setTimeout(() => document.removeEventListener('click', outside, true), 1100);
    });
    document.body.appendChild(chip);
    setTimeout(() => document.addEventListener('click', outside, true), 50);
    // Auto-dismiss after a few seconds if untouched.
    setTimeout(() => { if (document.body.contains(chip)) remove(); }, 4000);
    if (navigator.vibrate) { try { navigator.vibrate(15); } catch {} }
  }

  const onTouchStart = (e) => { const t = e.touches[0]; begin(t.clientX, t.clientY); };
  const onTouchMove = (e) => { const t = e.touches[0]; move(t.clientX, t.clientY); };
  const onTouchEnd = () => end();
  const onMouseDown = (e) => begin(e.clientX, e.clientY);
  const onMouseMove = (e) => move(e.clientX, e.clientY);
  const onMouseUp = () => end();
  // Suppress the click that follows a long-press so navigation doesn't fire.
  const onClick = (e) => { if (fired) { e.stopPropagation(); e.preventDefault(); fired = false; } };

  node.addEventListener('touchstart', onTouchStart, { passive: true });
  node.addEventListener('touchmove', onTouchMove, { passive: true });
  node.addEventListener('touchend', onTouchEnd);
  node.addEventListener('mousedown', onMouseDown);
  node.addEventListener('mousemove', onMouseMove);
  node.addEventListener('mouseup', onMouseUp);
  node.addEventListener('click', onClick, true);

  return {
    update(newParams) { params = newParams; },
    destroy() {
      end();
      node.removeEventListener('touchstart', onTouchStart);
      node.removeEventListener('touchmove', onTouchMove);
      node.removeEventListener('touchend', onTouchEnd);
      node.removeEventListener('mousedown', onMouseDown);
      node.removeEventListener('mousemove', onMouseMove);
      node.removeEventListener('mouseup', onMouseUp);
      node.removeEventListener('click', onClick, true);
    }
  };
}

// ── Replay a pinned shortcut by clicking its REAL button ─────────
// A shortcut stores the tab it lived on + the button's visible label
// (matchText). To "open the actual shortcut" we switch to that tab, wait for
// the view to render, then find the matching pinnable button and click it —
// which fires the button's own handler (open store, add product, audit, etc.).
// Returns true if a button was found + clicked.
function norm(s) {
  return (s || '').replace(/\s+/g, ' ').trim().toLowerCase();
}

// Pull the human label out of a candidate button the same way we do when
// pinning, so matching is symmetric.
function buttonLabel(btn) {
  const textEl = btn.querySelector('.btn-text, .qa-label, .today-title, .callin-home-title');
  if (textEl && textEl.textContent.trim()) return textEl.textContent.trim();
  const raw = (btn.getAttribute('aria-label') || btn.textContent || '').replace(/\s+/g, ' ').trim();
  // Strip a leading emoji so "🏪 Stores" matches "Stores".
  return raw.replace(/\p{Extended_Pictographic}/gu, '').trim() || raw;
}

// Find the best matching pinnable button currently in the DOM for a label.
function findPinnableByLabel(matchText) {
  const want = norm(matchText);
  if (!want) return null;
  const nodes = document.querySelectorAll(PINNABLE_SELECTOR);
  let exact = null, contains = null;
  for (const btn of nodes) {
    if (btn.closest('.hs-widget')) continue;          // skip the shortcuts widget itself
    if (btn.closest(PIN_EXCLUDE_SELECTOR)) continue;
    const lbl = norm(buttonLabel(btn));
    if (!lbl) continue;
    if (lbl === want) { exact = btn; break; }
    if (!contains && (lbl.includes(want) || want.includes(lbl))) contains = btn;
  }
  return exact || contains;
}

// Attempt to click the real button for a shortcut. `sc` is the stored shortcut.
// Retries briefly because the target tab/view may still be mounting after nav.
export function replayShortcut(sc, { retries = 12, interval = 60 } = {}) {
  return new Promise((resolve) => {
    const matchText = sc.matchText || sc.label || '';
    let tries = 0;
    const attempt = () => {
      const btn = findPinnableByLabel(matchText);
      if (btn) {
        btn.scrollIntoView({ block: 'center', behavior: 'auto' });
        btn.click();
        resolve(true);
        return;
      }
      if (++tries >= retries) { resolve(false); return; }
      setTimeout(attempt, interval);
    };
    attempt();
  });
}

// ── Global delegated long-press → "Add to Home Screen" ─────────
// Instead of annotating every button in every tab, one document-level handler
// watches for a long-press on any "pinnable" button and captures its icon +
// label + the tab it lives on automatically. Call installGlobalAddToHome()
// once at app start.

// Selector for buttons that can be pinned. Primary menu/action buttons across
// the tabs; excludes tiny utility buttons (back, remove, edit, tab bar, etc.).
const PINNABLE_SELECTOR = [
  '.main-btn', '.action-btn', '.template-btn', '.tmpl-btn',
  '.prospect-store-btn', '.navigate-store-btn', '.audit-store-btn',
  '.addtape-store-btn', '.cartvert-store-btn', '.roi-btn', '.callin-home-card',
  '.today-card-full',
].join(',');

// Buttons we never want to offer pinning on (navigation/utility, or buttons
// that already carry an explicit use:addToHome with richer action metadata
// like the dashboard quick-actions).
const PIN_EXCLUDE_SELECTOR = [
  '.back-btn', '.hs-item', '.hs-edit', '.hs-remove', '.tab-bar-item',
  '.header-icon-btn', '.font-slider-reset', '.font-slider-done',
  '.cancel-btn', '.mini-clear', '.reset-btn', '.qa-btn',
  '[data-has-addtohome]',
].join(',');

// Map the active bottom-tab label to our internal tab id.
const TAB_LABEL_TO_ID = {
  'Stores': 'stores', 'Present': 'present', 'Home': 'dashboard',
  'Clients': 'clients', 'Tools': 'tools',
};

function currentTabId() {
  const active = document.querySelector('.tab-bar-item.active .tab-bar-label');
  const label = active ? active.textContent.trim() : '';
  return TAB_LABEL_TO_ID[label] || 'dashboard';
}

// Pull a clean icon (emoji) + label out of a button's DOM.
function extractIconLabel(btn) {
  let icon = '⭐';
  let label = '';
  // Common structured buttons: .btn-icon/.btn-text (main-btn) or .qa-icon/.qa-label.
  const iconEl = btn.querySelector('.btn-icon, .qa-icon, .today-icon, .callin-home-icon');
  const textEl = btn.querySelector('.btn-text, .qa-label, .today-title, .callin-home-title');
  if (iconEl) icon = iconEl.textContent.trim().slice(0, 4) || icon;
  if (textEl) label = textEl.textContent.trim();
  if (!label) {
    // Fallback: first emoji in the text becomes the icon, the rest the label.
    const raw = (btn.getAttribute('aria-label') || btn.textContent || '').replace(/\s+/g, ' ').trim();
    const emojiMatch = raw.match(/\p{Extended_Pictographic}/u);
    if (emojiMatch) icon = emojiMatch[0];
    label = raw.replace(/\p{Extended_Pictographic}/gu, '').trim();
  }
  label = label.slice(0, 40);
  return { icon, label: label || 'Shortcut' };
}

let globalInstalled = false;
export function installGlobalAddToHome() {
  if (globalInstalled || typeof document === 'undefined') return;
  globalInstalled = true;

  let timer = null, startX = 0, startY = 0, target = null, fired = false;

  const clear = () => { if (timer) { clearTimeout(timer); timer = null; } };

  function candidateFrom(el) {
    if (!el || !el.closest) return null;
    if (el.closest(PIN_EXCLUDE_SELECTOR)) return null;
    const btn = el.closest(PINNABLE_SELECTOR);
    if (!btn) return null;
    // Don't offer pinning for the Home Shortcuts widget's own tiles.
    if (btn.closest('.hs-widget')) return null;
    return btn;
  }

  function begin(x, y, el) {
    const btn = candidateFrom(el);
    if (!btn) return;
    target = btn; startX = x; startY = y; fired = false;
    timer = setTimeout(() => { fired = true; showChip(btn); }, 600);
  }
  function move(x, y) {
    if (timer && (Math.abs(x - startX) > 10 || Math.abs(y - startY) > 10)) clear();
  }

  function showChip(btn) {
    const { icon, label } = extractIconLabel(btn);
    const tab = currentTabId();
    const existing = document.getElementById('add-to-home-chip');
    if (existing) existing.remove();
    const chip = document.createElement('div');
    chip.id = 'add-to-home-chip';
    chip.textContent = `➕ Add “${label}” to Home`;
    Object.assign(chip.style, {
      position: 'fixed', zIndex: '3000', background: '#111', color: '#fff',
      padding: '11px 18px', borderRadius: '24px', fontSize: '14px', fontWeight: '700',
      boxShadow: '0 6px 24px rgba(0,0,0,0.4)', cursor: 'pointer', maxWidth: '86vw',
      left: '50%', bottom: 'calc(92px + env(safe-area-inset-bottom,0px))',
      transform: 'translateX(-50%)', textAlign: 'center', whiteSpace: 'nowrap',
      overflow: 'hidden', textOverflow: 'ellipsis',
    });
    const remove = () => { if (chip.parentNode) chip.remove(); document.removeEventListener('click', outside, true); };
    const outside = (e) => { if (e.target !== chip) remove(); };
    chip.addEventListener('click', (e) => {
      e.stopPropagation();
      // matchText = the button's own visible label, used later to re-find and
      // click the ACTUAL button so the shortcut runs its real action.
      const res = addShortcut({ label, icon, tab, matchText: label });
      chip.textContent = res.added ? '✅ Added to Home Screen' : 'ℹ️ Already on Home Screen';
      chip.style.background = res.added ? '#0a7a0a' : '#555';
      setTimeout(remove, 1100);
    });
    document.body.appendChild(chip);
    setTimeout(() => document.addEventListener('click', outside, true), 60);
    setTimeout(() => { if (document.body.contains(chip)) remove(); }, 4500);
    if (navigator.vibrate) { try { navigator.vibrate(15); } catch {} }
  }

  document.addEventListener('touchstart', (e) => { const t = e.touches[0]; begin(t.clientX, t.clientY, e.target); }, { passive: true, capture: true });
  document.addEventListener('touchmove', (e) => { const t = e.touches[0]; move(t.clientX, t.clientY); }, { passive: true, capture: true });
  document.addEventListener('touchend', clear, { capture: true });
  document.addEventListener('mousedown', (e) => begin(e.clientX, e.clientY, e.target), true);
  document.addEventListener('mousemove', (e) => move(e.clientX, e.clientY), true);
  document.addEventListener('mouseup', clear, true);
  // Suppress the click that immediately follows a completed long-press so the
  // underlying button's navigation doesn't also fire.
  document.addEventListener('click', (e) => {
    if (fired && target && (e.target === target || (target.contains && target.contains(e.target)))) {
      e.stopPropagation(); e.preventDefault(); fired = false; target = null;
    }
  }, true);
}
