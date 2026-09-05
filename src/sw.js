const VERSION = '__BUILD_VERSION__';
const ROOT = new URL('./', self.location.href);
// Preserve the cache lineage across the Manuale rename.
const PREFIX = `preces-shell:${ROOT.pathname}:`;
const SHELL = `${PREFIX}${VERSION}`;
const ASSETS = __PRECACHE_ASSETS__;

self.addEventListener('install', event => {
  event.waitUntil(caches.open(SHELL).then(cache => cache.addAll(ASSETS.map(path => new URL(path, ROOT).href))).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith(PREFIX) && key !== SHELL).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== ROOT.origin || !url.pathname.startsWith(ROOT.pathname)) return;
  // Day packs are verified and saved by the app; never cache a failed request.
  if (url.pathname.includes('/data/days/')) return;
  const relative = url.pathname.slice(ROOT.pathname.length);
  if (relative === 'data/index.json') {
    event.respondWith(caches.open(SHELL).then(async cache => {
      try {
        const fresh = await fetch(event.request);
        if (fresh.ok) { await cache.put(url.href, fresh.clone()); return fresh; }
        return (await cache.match(url.href)) || fresh;
      } catch (error) {
        const saved = await cache.match(url.href);
        if (saved) return saved;
        throw error;
      }
    }));
    return;
  }
  if (event.request.mode === 'navigate') {
    // Serve the page from the same versioned cache as its modules. Fetching the
    // page from the network while modules came from cache mixes a new document
    // with an old script, which fails in ways neither version would alone. The
    // calendar is handled above, so freshness where it matters is unaffected.
    const target = relative === '' || relative === 'index.html' ? new URL('index.html', ROOT).href : url.href;
    event.respondWith(caches.open(SHELL).then(async cache => (await cache.match(target)) || fetch(event.request)));
  } else if (ASSETS.includes(relative)) {
    event.respondWith(caches.open(SHELL).then(async cache => (await cache.match(url.href)) || fetch(event.request)));
  }
});
