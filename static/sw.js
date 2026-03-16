// Synapse Service Worker — PWA support
const CACHE = 'synapse-v1';
const PRECACHE = ['/', '/static/index.html'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  // Network-first for API calls, cache-first for static
  const url = new URL(e.request.url);
  if (url.pathname.startsWith('/chat') || url.pathname.startsWith('/a2a') ||
      url.pathname.startsWith('/upload') || url.pathname.startsWith('/export')) {
    return; // let network handle
  }
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request).then(resp => {
      if (resp.ok && e.request.method === 'GET') {
        const clone = resp.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
      }
      return resp;
    }))
  );
});
