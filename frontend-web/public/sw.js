// Task Scheduling Agent V2 - Service Worker
// Provides offline support and caching for PWA

importScripts('https://www.gstatic.com/firebasejs/11.0.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/11.0.0/firebase-messaging-compat.js');

let _firebaseInitialized = false;
let _firebaseMessaging = null;

const _CACHE_NAME = 'taskagent-v1';
const STATIC_CACHE = 'taskagent-static-v1';
const DYNAMIC_CACHE = 'taskagent-dynamic-v1';

// Static assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icon-192x192.png',
  '/icon-512x512.png'
];

// API routes that should NOT be cached
const API_ROUTES = ['/api/'];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name !== STATIC_CACHE && name !== DYNAMIC_CACHE)
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip API requests - always go to network
  if (url.origin === self.location.origin && API_ROUTES.some(route => url.pathname.startsWith(route))) {
    event.respondWith(
      fetch(request)
        .catch(() => {
          // Return offline response for API failures
          return new Response(
            JSON.stringify({ error: 'You are offline. Please check your connection.' }),
            {
              status: 503,
              headers: { 'Content-Type': 'application/json' }
            }
          );
        })
    );
    return;
  }

  // For navigation requests (HTML pages) - network first, fallback to cache
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Clone and cache the response
          const responseClone = response.clone();
          caches.open(DYNAMIC_CACHE)
            .then((cache) => cache.put(request, responseClone));
          return response;
        })
        .catch(() => {
          return caches.match(request)
            .then((response) => response || caches.match('/index.html'));
        })
    );
    return;
  }

  // For static assets - cache first, fallback to network
  event.respondWith(
    caches.match(request)
      .then((cachedResponse) => {
        if (cachedResponse) {
          // Return cached response and update cache in background
          fetch(request)
            .then((response) => {
              caches.open(DYNAMIC_CACHE)
                .then((cache) => cache.put(request, response));
            })
            .catch(() => {}); // Ignore network errors for background update
          return cachedResponse;
        }

        // Not in cache - fetch from network and cache
        return fetch(request)
          .then((response) => {
            // Don't cache non-successful responses
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }

            const responseClone = response.clone();
            caches.open(DYNAMIC_CACHE)
              .then((cache) => cache.put(request, responseClone));
            return response;
          });
      })
  );
});

// Handle messages from the app
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data && event.data.type === 'CLEAR_CACHE') {
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((name) => caches.delete(name))
        );
      })
      .then(() => {
        event.ports[0].postMessage({ success: true });
      });
  }

  if (event.data && event.data.type === 'INIT_FIREBASE' && event.data.firebaseConfig && !_firebaseInitialized) {
    try {
      firebase.initializeApp(event.data.firebaseConfig);
      _firebaseMessaging = firebase.messaging();
      _firebaseMessaging.onBackgroundMessage((payload) => {
        const title = payload?.notification?.title || 'Notification';
        const body = payload?.notification?.body || '';
        const url = payload?.data?.url || '/';
        return self.registration.showNotification(title, {
          body,
          icon: '/icon-192x192.png',
          badge: '/icon-192x192.png',
          data: { url },
        });
      });
      _firebaseInitialized = true;
    } catch {}
  }
});

// Background sync for offline submissions (future feature)
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-submissions') {
    console.log('[SW] Syncing offline submissions...');
    // TODO: Implement offline submission sync
  }
});

// Handle notification click
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const raw = event.notification?.data?.url || '/';
  const url = new URL(raw, self.location.origin).toString();
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url === url && 'focus' in client) return client.focus();
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});
