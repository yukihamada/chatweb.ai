// chatweb.ai Service Worker — PWA support (v2: network-first for HTML)
const CACHE = 'chatweb-v3';

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(['/', '/static/favicon.svg', '/manifest.json']))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  // Delete all old caches
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

  // Network-first for HTML pages (always get latest)
  if (e.request.headers.get('accept')?.includes('text/html') ||
      url.pathname === '/' || url.pathname.endsWith('.html')) {
    e.respondWith(
      fetch(e.request).then(resp => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return resp;
      }).catch(() => caches.match(e.request))  // offline fallback
    );
    return;
  }

  // Cache-first for static assets (images, fonts, JS libs)
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request).then(resp => {
      if (resp.ok) {
        const clone = resp.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
      }
      return resp;
    }))
  );
});
