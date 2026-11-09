// Service worker: app shell en cache (cache-first) y datos con red primero,
// cayendo a la copia en cache cuando no hay conexión (para poder abrir la app
// en el movil sin wifi/datos y ver el ultimo informe descargado).
var CACHE_VERSION = "v2";
var SHELL_CACHE = "coches-shell-" + CACHE_VERSION;
var DATA_CACHE = "coches-data-" + CACHE_VERSION;

var SHELL_FILES = [
  "./",
  "./index.html",
  "./app.js",
  "./styles.css",
  "./manifest.json",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(SHELL_CACHE).then(function (cache) { return cache.addAll(SHELL_FILES); })
  );
  self.skipWaiting();
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys
          .filter(function (k) { return k !== SHELL_CACHE && k !== DATA_CACHE; })
          .map(function (k) { return caches.delete(k); })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", function (event) {
  var url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== location.origin) return;

  if (url.pathname.endsWith("data.json")) {
    event.respondWith(
      fetch(event.request)
        .then(function (resp) {
          var copia = resp.clone();
          caches.open(DATA_CACHE).then(function (cache) { cache.put(event.request, copia); });
          return resp;
        })
        .catch(function () { return caches.match(event.request); })
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then(function (cached) {
      return cached || fetch(event.request);
    })
  );
});
