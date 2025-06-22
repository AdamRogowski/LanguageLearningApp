const CACHE_NAME = "djangopwa-v2";
const urlsToCache = [
  "/",
  "/static/images/logo.png",
  "/static/images/favicon.ico",
  "/static/styles/main.css",
  "/lessons-repository/",

  // Add more static assets as needed
];

// Install event: cache files
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(urlsToCache))
  );
  self.skipWaiting();
});

// Activate event: clean up old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE_NAME)
            .map((key) => caches.delete(key))
        )
      )
  );
  self.clients.claim();
});

// Fetch event: serve cached, then network
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(
    caches
      .match(event.request)
      .then(
        (response) =>
          response || fetch(event.request).catch(() => caches.match("/"))
      )
  );
});