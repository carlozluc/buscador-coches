// Service worker: red primero, cayendo a la copia en cache cuando no hay conexion
// (para poder abrir la app en el movil sin wifi/datos y ver el ultimo informe
// descargado). Red-primero para TODO, incluido el propio codigo de la app, asi
// un despliegue nuevo se ve en la siguiente visita con conexion sin tener que
// acordarse de subir un numero de version aqui.
var CACHE = "coches-v1";

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
    caches.open(CACHE).then(function (cache) { return cache.addAll(SHELL_FILES); })
  );
  self.skipWaiting();
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", function (event) {
  var url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== location.origin) return;

  event.respondWith(
    fetch(event.request)
      .then(function (resp) {
        var copia = resp.clone();
        caches.open(CACHE).then(function (cache) { cache.put(event.request, copia); });
        return resp;
      })
      .catch(function () { return caches.match(event.request); })
  );
});
