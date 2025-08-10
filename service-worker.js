const CACHE_NAME = 'audio-master-cache-v1';
const urlsToCache = [
  '/',
  '/static/manifest.json',
  // We can't cache the result page directly as it's generated dynamically,
  // but we can cache the main page which holds most of the UI.
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - return response
        if (response) {
          return response;
        }
        return fetch(event.request);
      }
    )
  );
});
