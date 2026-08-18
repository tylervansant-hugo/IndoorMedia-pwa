/**
 * Per-rep cart helpers with cross-device sync.
 *
 * Why this exists:
 *  - The cart used to live in a single device-global localStorage key
 *    ('indoormedia_cart'), so (a) two reps sharing a device saw each other's
 *    cart, and (b) a cart started on a phone didn't appear on an iPad.
 *  - Now the cart is scoped to the logged-in rep AND mirrored to Firestore
 *    (one doc per rep), so the same rep picks up the same cart on any device.
 *
 * Storage:
 *  - localStorage key: `indoormedia_cart__<repId>` (instant, offline-friendly)
 *  - Firestore: rep_cart_<repId> via saveRepCart/getRepCart (cross-device)
 *
 * Back-compat: the legacy global 'indoormedia_cart' key is migrated into the
 * current rep's cart once, then ignored.
 */
import { get } from 'svelte/store';
import { user } from './stores.js';
import { whenFirebaseReady, saveRepCart, getRepCart } from './firebase.js';

const LEGACY_KEY = 'indoormedia_cart';

export function currentRepId() {
  try {
    const u = get(user);
    if (u && (u.id != null)) return String(u.id);
  } catch {}
  // Fallback so the app still works before login resolves.
  try {
    const raw = localStorage.getItem('user') || localStorage.getItem('impro_user');
    if (raw) { const u = JSON.parse(raw); if (u && u.id != null) return String(u.id); }
  } catch {}
  return null;
}

export function cartKey(repId = currentRepId()) {
  return repId ? `${LEGACY_KEY}__${repId}` : LEGACY_KEY;
}

/** Read the current rep's cart from localStorage (with one-time legacy migration). */
export function readCart(repId = currentRepId()) {
  const key = cartKey(repId);
  try {
    let raw = localStorage.getItem(key);
    if (raw == null && repId) {
      // Migrate a pre-existing global cart into this rep's scoped key once.
      const legacy = localStorage.getItem(LEGACY_KEY);
      if (legacy != null) {
        localStorage.setItem(key, legacy);
        raw = legacy;
        // Clear the global key so it can't leak to another rep on this device.
        try { localStorage.removeItem(LEGACY_KEY); } catch {}
      }
    }
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

/** Write the current rep's cart to localStorage + Firestore, notify listeners. */
export function writeCart(cartItems, repId = currentRepId()) {
  const items = Array.isArray(cartItems) ? cartItems : [];
  try { localStorage.setItem(cartKey(repId), JSON.stringify(items)); } catch {}
  // Cross-device: fire-and-forget cloud write.
  if (repId) {
    try { whenFirebaseReady(4000).then((ready) => { if (ready) saveRepCart(repId, items); }); } catch {}
  }
  try { window.dispatchEvent(new Event('cart-updated')); } catch {}
  return items;
}

/**
 * Pull the rep's cloud cart and reconcile with local. Cloud is treated as the
 * source of truth for cross-device continuity: if the cloud copy is newer than
 * the last local write (or local is empty), adopt it. Returns the effective cart.
 * Call this on login / app resume / Cart view mount.
 */
export async function syncCartFromCloud(repId = currentRepId()) {
  if (!repId) return readCart(repId);
  const ready = await whenFirebaseReady(6000);
  if (!ready) return readCart(repId);
  let remote = null;
  try { remote = await getRepCart(repId); } catch { return readCart(repId); }
  const local = readCart(repId);
  if (!remote) {
    // Nothing in cloud yet — push local up so other devices can get it.
    if (local.length) { try { saveRepCart(repId, local); } catch {} }
    return local;
  }
  // Adopt cloud when local is empty, or when cloud was updated more recently
  // than our local marker. (We store a lightweight local timestamp per rep.)
  const localTsKey = `${cartKey(repId)}__ts`;
  let localTs = 0;
  try { localTs = parseInt(localStorage.getItem(localTsKey) || '0', 10) || 0; } catch {}
  const remoteTs = Date.parse(remote.updatedAt || 0) || 0;
  if (local.length === 0 || remoteTs > localTs) {
    try {
      localStorage.setItem(cartKey(repId), JSON.stringify(remote.cart));
      localStorage.setItem(localTsKey, String(remoteTs || Date.now()));
    } catch {}
    try { window.dispatchEvent(new Event('cart-updated')); } catch {}
    return remote.cart;
  }
  // Local is newer/equal — make sure cloud reflects it.
  try { saveRepCart(repId, local); } catch {}
  return local;
}

/** Stamp the local write time (called by writeCart callers that want ts tracking). */
export function markCartWritten(repId = currentRepId()) {
  try { localStorage.setItem(`${cartKey(repId)}__ts`, String(Date.now())); } catch {}
}
