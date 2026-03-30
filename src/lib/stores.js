import { writable } from 'svelte/store';

// Current logged-in user
export const currentUser = writable(null);
export const user = writable(null); // Alias for currentUser

// Theme (light/dark)
const savedTheme = typeof localStorage !== 'undefined' ? localStorage.getItem('theme') : 'light';
export const theme = writable(savedTheme || 'light');

// Current tab/view state
export const currentTab = writable('search'); // 'search', 'prospects', 'testimonials', 'cart'

// Cart items
export const cart = writable([]);

// Search results
export const searchResults = writable([]);

// Loading state
export const loading = writable(false);

// Error messages
export const error = writable(null);

// Store functions
export function setUser(userObj) {
  currentUser.set(userObj);
  user.set(userObj); // Keep both in sync
  if (userObj) {
    localStorage.setItem('user', JSON.stringify(userObj));
  } else {
    localStorage.removeItem('user');
    cart.set([]);
  }
}

export function setTab(tab) {
  currentTab.set(tab);
  error.set(null); // Clear errors when switching tabs
}

export function addToCart(item) {
  cart.update(items => {
    const existing = items.find(i => i.id === item.id && i.type === item.type);
    if (existing) {
      existing.quantity = (existing.quantity || 1) + 1;
      return items;
    }
    return [...items, { ...item, quantity: 1 }];
  });
}

export function removeFromCart(id, type) {
  cart.update(items => items.filter(i => !(i.id === id && i.type === type)));
}

export function clearCart() {
  cart.set([]);
}

export function setError(message) {
  error.set(message);
  setTimeout(() => error.set(null), 5000);
}

export function setLoading(isLoading) {
  loading.set(isLoading);
}
