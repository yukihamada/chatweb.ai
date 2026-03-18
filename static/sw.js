// chatweb.ai Service Worker — v4: network-first for all assets
const CACHE = 'chatweb-v4';

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(['/', '/static/favicon.svg', '/manifest.json']))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  // Delete ALL old caches (forces re-download of everything)
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // Skip non-GET and API calls
  if (e.request.method !== 'GET') return;
  if (url.pathname.startsWith('/chat') || url.pathname.startsWith('/a2a') ||
      url.pathname.startsWith('/upload') || url.pathname.startsWith('/export') ||
      url.pathname.startsWith('/billing') || url.pathname.startsWith('/auth') ||
      url.pathname.startsWith('/admin') || url.pathname.startsWith('/feedback')) {
    return;
  }

  // Network-first for EVERYTHING (HTML, CSS, JS, images)
  // Cache is only used as offline fallback
  e.respondWith(
    fetch(e.request).then(resp => {
      if (resp.ok) {
        const clone = resp.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
      }
      return resp;
    }).catch(() => caches.match(e.request))
  );
});
