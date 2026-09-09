// promos.js — seasonal promo/contest feature flags.
// ARCHIVE SWITCH: flip a flag to `true` to bring the promo back next season.
// All promo code (Summer Promo pricing mode + Summer Sales Contest leaderboard)
// stays intact in the codebase; these flags just show/hide it.

export const PROMOS = {
  // Summer Sales Contest (May 27 – Sep 1). Ended 2026-09-09 — archived.
  // Controls: StoreSearch "Summer Promo 🔥" pricing mode + Main homepage
  // "Summer Sales Contest" leaderboard/detail.
  summer: false,
};

export const summerPromoActive = () => PROMOS.summer === true;
