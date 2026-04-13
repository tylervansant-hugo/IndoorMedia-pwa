/**
 * Service Worker for IndoorMedia PWA
 * Handles offline caching, push notifications, and background sync
 */

const CACHE_VERSION = 'v1';
const CACHE_NAME = `indoormedia-${CACHE_VERSION}`;

// Assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/service-worker.js',
];

// API endpoints that should be cached
const API_CACHE = {
  'GET': [
    /^\/api\/stores/,
    /^\/api\/rep-registry/,
    /^\/api\/testimonials/,
    /^\/api\/pricing/,
  ],
};

/**
 * Install event - cache static assets
 */
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');

  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('[SW] Service worker installed');
        return self.skipWaiting();
      })
      .catch((err) => console.error('[SW] Install error:', err))
  );
});

/**
 * Activate event - clean up old caches
 */
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');

  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => !name.includes(CACHE_VERSION))
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => self.clients.claim())
  );
});

/**
 * Fetch event - serve from cache, fallback to network
 */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const { method, url } = request;

  // Skip non-GET requests
  if (method !== 'GET') {
    return event.respondWith(fetch(request));
  }

  // Skip cross-origin requests
  if (!url.startsWith(self.location.origin)) {
    return;
  }

  // API requests - network first, cache fallback
  if (url.includes('/api/')) {
    return event.respondWith(
      fetch(request)
        .then((response) => {
          // Cache successful API responses
          if (response.ok) {
            const cache = caches.open(CACHE_NAME);
            cache.then((c) => c.put(request, response.clone()));
          }
          return response;
        })
        .catch(() => {
          // Fallback to cached response
          return caches.match(request).then((cached) => {
            if (cached) {
              console.log('[SW] Serving from cache:', url);
              return cached;
            }
            // Return offline fallback
            return new Response(
              JSON.stringify({
                error: 'offline',
                message: 'You are offline. Some data may be unavailable.',
              }),
              {
                status: 503,
                statusText: 'Service Unavailable',
                headers: { 'Content-Type': 'application/json' },
              }
            );
          });
        })
    );
  }

  // Static assets - cache first, network fallback
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) {
        // Update cache in background
        fetch(request).then((response) => {
          if (response.ok) {
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, response.clone());
            });
          }
        });
        return cached;
      }
      return fetch(request).then((response) => {
        if (response.ok) {
          const cache = caches.open(CACHE_NAME);
          cache.then((c) => c.put(request, response.clone()));
        }
        return response;
      });
    })
  );
});

/**
 * Message handler for client communication
 */
self.addEventListener('message', (event) => {
  console.log('[SW] Message received:', event.data);

  if (event.data.type === 'CLEAR_CACHE') {
    caches.delete(CACHE_NAME).then(() => {
      event.ports[0].postMessage({ status: 'cache cleared' });
    });
  }

  if (event.data.type === 'CACHE_URLS') {
    const urls = event.data.urls || [];
    caches.open(CACHE_NAME).then((cache) => {
      cache.addAll(urls).then(() => {
        event.ports[0].postMessage({ status: 'urls cached', count: urls.length });
      });
    });
  }
});

/**
 * Periodic sync for background updates (requires permission)
 */
self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'update-data') {
    console.log('[SW] Periodic sync: updating data');
    event.waitUntil(
      Promise.all([
        fetch('/api/stores').then((r) => r.json()),
        fetch('/api/testimonials').then((r) => r.json()),
      ]).catch((err) => console.error('[SW] Periodic sync error:', err))
    );
  }
});

console.log('[SW] Service Worker loaded');
