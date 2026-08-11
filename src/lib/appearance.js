// Centralized "Appearance" preferences applier — THEME-BASED.
//
// The appearance system is now built around curated THEMES instead of a pile of
// à-la-carte color pickers. Each theme defines a coordinated palette that has
// BOTH a light and a dark variant baked in, so it stays legible whether the
// user is in day or night mode. Legibility is guaranteed programmatically:
// text and card colors are chosen (and contrast-checked) per mode, so there is
// no way to pick an illegible combo.
//
// Keys used:
//   appearance_theme  -> theme id (see THEMES); default 'classic'
//   appearance_mode   -> 'auto' | 'light' | 'dark'  (day/night base)
//   appearance_font   -> font family id (see FONT_OPTIONS)
//
// Back-compat: older keys (appearance_accent, appearance_wallpaper, card/text
// color, opacity, border, custom image) are IGNORED going forward and cleared
// on reset. getAppearance() still returns an `accent`/`icons` field so existing
// callers keep working.

export const FONT_OPTIONS = [
  { id: 'system', label: 'System', stack: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif` },
  { id: 'rounded', label: 'Rounded', stack: `'SF Pro Rounded', 'Nunito', 'Quicksand', system-ui, sans-serif` },
  { id: 'serif', label: 'Serif', stack: `'Georgia', 'Iowan Old Style', 'Times New Roman', serif` },
  { id: 'mono', label: 'Mono', stack: `'SF Mono', 'JetBrains Mono', 'Menlo', 'Consolas', monospace` },
  { id: 'condensed', label: 'Condensed', stack: `'Roboto Condensed', 'Arial Narrow', 'Helvetica Neue', sans-serif` },
  { id: 'humanist', label: 'Humanist', stack: `'Optima', 'Segoe UI', 'Gill Sans', 'Trebuchet MS', sans-serif` },
];

export const DEFAULT_ACCENT = '#CC0000';

// ── Curated themes ────────────────────────────────────────────
// Each theme provides an accent + a soft background wash for BOTH modes. The
// wash is intentionally subtle (a gentle gradient behind cards) so text stays
// readable without any dimming hacks. `light`/`dark` hold the per-mode
// background gradient + the page base color used to build cards.
//
//   accent : brand/action color (used app-wide via --accent)
//   light  : { bg, wash }  -> bg = page base, wash = gradient painted behind cards
//   dark   : { bg, wash }
//
// Cards, text, borders are DERIVED from the mode base so contrast is guaranteed.
export const THEMES = [
  {
    id: 'classic', name: 'Classic', emoji: '🔴',
    accent: '#CC0000',
    light: { bg: '#ededf0', wash: '' },
    dark:  { bg: '#1a1a1a', wash: '' },
  },
  {
    id: 'midnight', name: 'Midnight', emoji: '🌙',
    accent: '#3b82f6',
    light: { bg: '#eef2fb', wash: 'linear-gradient(160deg,#e8eefc 0%,#dfe7f7 100%)' },
    dark:  { bg: '#0f172a', wash: 'linear-gradient(160deg,#0f172a 0%,#1e293b 100%)' },
  },
  {
    id: 'forest', name: 'Forest', emoji: '🌲',
    accent: '#0a7a4a',
    light: { bg: '#eaf3ec', wash: 'linear-gradient(160deg,#e6f2ea 0%,#dbeee0 100%)' },
    dark:  { bg: '#0e1c16', wash: 'linear-gradient(160deg,#0e1c16 0%,#12281d 100%)' },
  },
  {
    id: 'sunset', name: 'Sunset', emoji: '🌇',
    accent: '#e0533d',
    light: { bg: '#fdeee7', wash: 'linear-gradient(160deg,#fdeadf 0%,#fbe0d3 100%)' },
    dark:  { bg: '#1c1210', wash: 'linear-gradient(160deg,#1c1210 0%,#2a1a15 100%)' },
  },
  {
    id: 'grape', name: 'Grape', emoji: '🍇',
    accent: '#7c3aed',
    light: { bg: '#f2ecfb', wash: 'linear-gradient(160deg,#efe7fb 0%,#e7dbf7 100%)' },
    dark:  { bg: '#150f24', wash: 'linear-gradient(160deg,#150f24 0%,#221635 100%)' },
  },
  {
    id: 'ocean', name: 'Ocean', emoji: '🌊',
    accent: '#0e8ea4',
    light: { bg: '#e7f4f7', wash: 'linear-gradient(160deg,#e2f2f6 0%,#d5ebf1 100%)' },
    dark:  { bg: '#0a1a1f', wash: 'linear-gradient(160deg,#0a1a1f 0%,#0f2a31 100%)' },
  },
  {
    id: 'slate', name: 'Slate', emoji: '🪨',
    accent: '#475569',
    light: { bg: '#eef0f3', wash: 'linear-gradient(160deg,#eceff3 0%,#e2e6ec 100%)' },
    dark:  { bg: '#161a20', wash: 'linear-gradient(160deg,#161a20 0%,#1f252e 100%)' },
  },
  {
    id: 'mono', name: 'Mono', emoji: '⚪',
    accent: '#111827',
    light: { bg: '#f4f4f5', wash: '' },
    dark:  { bg: '#101012', wash: '' },
  },
];

export const MODE_OPTIONS = [
  { id: 'auto', label: 'Auto', emoji: '🌗' },
  { id: 'light', label: 'Day', emoji: '☀️' },
  { id: 'dark', label: 'Night', emoji: '🌙' },
];

export const DEFAULT_THEME = 'classic';

function themeById(id) { return THEMES.find(t => t.id === id) || THEMES[0]; }
function fontStack(id) { return (FONT_OPTIONS.find(f => f.id === id) || FONT_OPTIONS[0]).stack; }

// ── Color math (contrast + legibility) ────────────────────────
function hexToRgb(hex) {
  if (!hex) return null;
  let h = String(hex).trim().replace('#', '');
  if (h.length === 3) h = h.split('').map(c => c + c).join('');
  if (h.length !== 6 || /[^0-9a-fA-F]/.test(h)) return null;
  return { r: parseInt(h.slice(0, 2), 16), g: parseInt(h.slice(2, 4), 16), b: parseInt(h.slice(4, 6), 16) };
}
function rgbToHex(r, g, b) {
  const c = (n) => Math.max(0, Math.min(255, Math.round(n))).toString(16).padStart(2, '0');
  return `#${c(r)}${c(g)}${c(b)}`;
}
function relLuminance({ r, g, b }) {
  const ch = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b);
}
// WCAG contrast ratio between two rgb colors (1..21).
function contrast(a, b) {
  const la = relLuminance(a), lb = relLuminance(b);
  const hi = Math.max(la, lb), lo = Math.min(la, lb);
  return (hi + 0.05) / (lo + 0.05);
}
function mix(a, b, t) {
  return { r: a.r + (b.r - a.r) * t, g: a.g + (b.g - a.g) * t, b: a.b + (b.b - a.b) * t };
}
const WHITE = { r: 255, g: 255, b: 255 };
const BLACK = { r: 17, g: 17, b: 17 };

// Given a card background, return a primary + secondary text color that ALWAYS
// meets a strong contrast target (>= 7:1 primary, >= 4.5:1 secondary). This is
// the legibility safeguard: no matter the theme/mode, text is readable.
function legibleText(cardRgb) {
  const onWhite = contrast(cardRgb, BLACK); // dark text contrast
  const onBlack = contrast(cardRgb, WHITE); // light text contrast
  const base = onWhite >= onBlack ? BLACK : WHITE;
  const other = base === BLACK ? WHITE : BLACK;
  // Primary: pure base (max contrast). Secondary: blend toward the card until it
  // dips just below AA-large but stays >= 4.5:1 so it's muted yet legible.
  let secondary = base;
  for (let t = 0; t <= 0.6; t += 0.05) {
    const cand = mix(base, cardRgb, t);
    if (contrast(cand, cardRgb) >= 4.6) secondary = cand; else break;
  }
  return {
    primary: rgbToHex(base.r, base.g, base.b),
    secondary: rgbToHex(secondary.r, secondary.g, secondary.b),
    onDark: base === WHITE,
  };
}

// Build a card background from the page base: nudge slightly toward white (light
// mode) or lighten (dark mode) so cards separate from the page.
function cardFromBase(baseRgb, isDark) {
  return isDark ? mix(baseRgb, WHITE, 0.10) : WHITE;
}
function borderFromBase(baseRgb, isDark) {
  return isDark ? mix(baseRgb, WHITE, 0.22) : mix(baseRgb, BLACK, 0.10);
}

// Ensure the accent itself is legible as a button background (white or near-black
// label). If the accent is too light for white text, we darken it a touch.
function safeAccent(accentHex) {
  const rgb = hexToRgb(accentHex) || hexToRgb(DEFAULT_ACCENT);
  let c = rgb;
  // We always put WHITE text on accent buttons; ensure >= 3:1 (large/bold).
  let guard = 0;
  while (contrast(c, WHITE) < 3.2 && guard < 12) { c = mix(c, BLACK, 0.12); guard++; }
  return rgbToHex(c.r, c.g, c.b);
}

// ── Resolve the effective light/dark mode ─────────────────────
export function resolveMode(mode) {
  if (mode === 'light' || mode === 'dark') return mode;
  // auto → follow system
  try {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark';
  } catch {}
  return 'light';
}

export function getAppearance() {
  const themeId = localStorage.getItem('appearance_theme') || DEFAULT_THEME;
  const mode = localStorage.getItem('appearance_mode') || 'auto';
  const font = localStorage.getItem('appearance_font') || 'system';
  const t = themeById(themeId);
  return {
    theme: themeId,
    mode,
    font,
    // Legacy fields some callers still read:
    accent: t.accent,
    icons: 'emoji',
  };
}

// Apply the given (or stored) appearance prefs to the document root.
export function applyAppearance(prefs) {
  if (typeof document === 'undefined') return;
  const p = prefs || getAppearance();
  const root = document.documentElement;
  const t = themeById(p.theme);
  const effMode = resolveMode(p.mode);
  const isDark = effMode === 'dark';

  // Drive the app's existing light/dark theme system.
  root.setAttribute('data-theme', isDark ? 'dark' : 'light');
  try {
    if (document.body) document.body.setAttribute('data-theme', isDark ? 'dark' : 'light');
    document.querySelectorAll('.main[data-theme]').forEach(el => el.setAttribute('data-theme', isDark ? 'dark' : 'light'));
  } catch {}

  // Font.
  root.style.setProperty('--app-font', fontStack(p.font));

  // Accent (legibility-guarded for white button text).
  const accent = safeAccent(t.accent);
  root.style.setProperty('--accent', accent);
  root.style.setProperty('--accent-color', accent);

  // Per-mode palette.
  const modeDef = isDark ? t.dark : t.light;
  const baseRgb = hexToRgb(modeDef.bg) || (isDark ? { r: 26, g: 26, b: 26 } : { r: 237, g: 237, b: 240 });
  const cardRgb = cardFromBase(baseRgb, isDark);
  const borderRgb = borderFromBase(baseRgb, isDark);
  const text = legibleText(cardRgb);

  // Background wash (subtle gradient) — painted behind cards, NEVER dimmed.
  const wash = modeDef.wash || '';
  root.style.setProperty('--app-wallpaper', wash || 'none');
  root.setAttribute('data-wallpaper', wash ? `theme-${t.id}` : 'none');
  // No veil: themes are pre-tuned for contrast, so show the wash at full strength.
  root.style.setProperty('--wallpaper-veil-alpha', '0');

  // Card + border + text overrides (these win over the per-theme .main blocks).
  root.style.setProperty('--card-bg-override', rgbToHex(cardRgb.r, cardRgb.g, cardRgb.b));
  root.setAttribute('data-custom-card', '1');
  root.style.setProperty('--border-override', rgbToHex(borderRgb.r, borderRgb.g, borderRgb.b));
  root.setAttribute('data-custom-border', '1');
  root.style.setProperty('--text-primary-override', text.primary);
  root.style.setProperty('--text-secondary-override', text.secondary);
  root.setAttribute('data-custom-text', '1');

  // Page base color (so areas behind the wash match the theme).
  root.style.setProperty('--bg-primary-override', rgbToHex(baseRgb.r, baseRgb.g, baseRgb.b));
  root.setAttribute('data-custom-bg', '1');

  root.setAttribute('data-icons', 'emoji');
  root.setAttribute('data-appearance-theme', t.id);
}

export function setAppearance(patch) {
  const cur = getAppearance();
  const next = { ...cur, ...patch };
  if (patch.theme !== undefined) localStorage.setItem('appearance_theme', next.theme);
  if (patch.mode !== undefined) localStorage.setItem('appearance_mode', next.mode);
  if (patch.font !== undefined) localStorage.setItem('appearance_font', next.font);
  // Keep the legacy `theme` store (light/dark) in sync so other code paths that
  // read localStorage 'theme' stay correct.
  if (patch.theme !== undefined || patch.mode !== undefined) {
    try { localStorage.setItem('theme', resolveMode(next.mode)); } catch {}
  }
  applyAppearance(next);
  try { window.dispatchEvent(new CustomEvent('appearance-changed', { detail: next })); } catch {}
  return getAppearance();
}

// Convenience for the header day/night toggle: cycle Auto→Day→Night→Auto or
// simply flip when called with an explicit mode.
export function setMode(mode) { return setAppearance({ mode }); }

export function resetAppearance() {
  // Clear new keys.
  ['appearance_theme', 'appearance_mode', 'appearance_font'].forEach(k => localStorage.removeItem(k));
  // Clear all legacy à-la-carte keys so nothing stale lingers.
  [
    'appearance_accent', 'appearance_wallpaper', 'appearance_bg_color', 'appearance_bg_image',
    'appearance_border', 'appearance_icons', 'appearance_text_color', 'appearance_card_color',
    'appearance_card_opacity', 'appearance_wp_opacity',
  ].forEach(k => localStorage.removeItem(k));
  applyAppearance();
  try { window.dispatchEvent(new CustomEvent('appearance-changed', { detail: getAppearance() })); } catch {}
}

// Re-apply when the system light/dark preference changes AND mode is 'auto'.
if (typeof window !== 'undefined' && window.matchMedia) {
  try {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      const mode = localStorage.getItem('appearance_mode') || 'auto';
      if (mode === 'auto') applyAppearance();
    });
  } catch {}
}
