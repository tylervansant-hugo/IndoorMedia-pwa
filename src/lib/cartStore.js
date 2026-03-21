import { writable } from 'svelte/store';

// Initialize cart from localStorage
function createCartStore() {
  let initialCart = [];
  
  if (typeof window !== 'undefined') {
    try {
      const saved = localStorage.getItem('indoormedia_cart');
      if (saved) {
        initialCart = JSON.parse(saved);
      }
    } catch (e) {
      console.warn('Failed to load cart from localStorage:', e);
    }
  }

  const { subscribe, set, update } = writable(initialCart);

  return {
    subscribe,
    
    addItem: (item) => update(cart => {
      const updatedCart = [...cart, item];
      persistCart(updatedCart);
      return updatedCart;
    }),
    
    removeItem: (itemId) => update(cart => {
      const updatedCart = cart.filter(item => item.id !== itemId);
      persistCart(updatedCart);
      return updatedCart;
    }),
    
    updateQuantity: (itemId, quantity) => update(cart => {
      const item = cart.find(i => i.id === itemId);
      if (item) {
        item.quantity = Math.max(1, quantity);
      }
      persistCart(cart);
      return cart;
    }),
    
    clearCart: () => {
      set([]);
      if (typeof window !== 'undefined') {
        localStorage.removeItem('indoormedia_cart');
      }
    },
    
    getTotal: () => {
      let total = 0;
      const unsubscribe = subscribe(cart => {
        total = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
      });
      unsubscribe();
      return total;
    },
  };
}

function persistCart(cart) {
  if (typeof window !== 'undefined') {
    try {
      localStorage.setItem('indoormedia_cart', JSON.stringify(cart));
    } catch (e) {
      console.warn('Failed to persist cart:', e);
    }
  }
}

export const cart = createCartStore();
