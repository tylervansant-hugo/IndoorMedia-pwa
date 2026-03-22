import { writable } from 'svelte/store';

const browser = typeof window !== 'undefined';

// Initialize theme from localStorage or system preference
function getInitialTheme() {
  if (!browser) return 'light';
  
  const stored = localStorage.getItem('theme');
  if (stored) return stored;
  
  // Check system preference
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }
  
  return 'light';
}

export const theme = writable(getInitialTheme());

// Subscribe to theme changes and update localStorage + document
if (browser) {
  theme.subscribe(value => {
    localStorage.setItem('theme', value);
    document.documentElement.setAttribute('data-theme', value);
  });
  
  // Set initial theme on document
  document.documentElement.setAttribute('data-theme', getInitialTheme());
}

export function toggleTheme() {
  theme.update(current => current === 'light' ? 'dark' : 'light');
}
