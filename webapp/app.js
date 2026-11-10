(function () {
  "use strict";

  var PLACEHOLDER_SVG =
    "data:image/svg+xml;utf8," +
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 240'>" +
    "<rect width='400' height='240' fill='%23e4e1da'/>" +
    "<path d='M60 150l20-45a18 18 0 0 1 16-11h88a18 18 0 0 1 16 11l20 45' " +
    "fill='none' stroke='%23a39b8a' stroke-width='6' stroke-linejoin='round'/>" +
    "<rect x='55' y='150' width='290' height='34' rx='10' fill='%23a39b8a'/>" +
    "<circle cx='105' cy='186' r='16' fill='%23e4e1da' stroke='%23a39b8a' stroke-width='6'/>" +
    "<circle cx='295' cy='186' r='16' fill='%23e4e1da' stroke='%23a39b8a' stroke-width='6'/>" +
    "</svg>";

  function esc(v) {
    if (v === null || v === undefined) return "";
    return String(v)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fmtEur(v) {
    if (v === null || v === undefined) return "-";
    return Math.round(v).toLocaleString("es-ES") + " €";
  }

  function fmtKm(v) {
    if (v === null || v === undefined) return "-";
    return Math.round(v).toLocaleString("es-ES") + " km";
  }

  function estrellas(puntuacion) {
    var n = Math.round(puntuacion || 0);
    return "★".repeat(Math.max(0, n)) + "☆".repeat(Math.max(0, 5 - n));
  }

  function filaFinanciacion(etiqueta, datos) {
    var cuota = datos && datos.cuota_mensual;
    var txt = cuota ? fmtEur(cuota) + "/mes" : "No especificada";
    return "<tr><td>" + esc(etiqueta) + "</td><td>" + txt + "</td></tr>";
  }

  function tablaFinanciacion(fin) {
    if (!fin) return "";
    return (
      "<table class=\"financiacion\">" +
      filaFinanciacion("Oferta del vendedor", fin.oferta_vendedor) +
      filaFinanciacion("Mercado medio", fin.mercado_medio) +
      filaFinanciacion("Préstamo familiar (3%, sin entrada)", fin.prestamo_familiar) +
      "</table>"
    );
  }

  function tarjetaAnuncioHtml(a, nombreModelo) {
    var badges = "";
    if (a.nuevo_hoy) badges += '<span class="badge badge-nuevo">Nuevo hoy</span>';
    if (a.bajada_precio)
      badges +=
        '<span class="badge badge-bajada">Bajada: ' +
        fmtEur(a.precio_anterior) +
        " → " +
        fmtEur(a.precio) +
        "</span>";

    var foto = a.foto_url || PLACEHOLDER_SVG;
    var fotoClase = a.foto_url ? "foto" : "foto foto-generica";
    var puntuacion = a.puntuacion || 0;

    var art = document.createElement("article");
    art.className = "tarjeta";
    art.dataset.modelo = a.modelo_id || "";
    art.dataset.puntuacion = puntuacion;
    art.dataset.precio = a.precio || 0;
    art.dataset.km = a.km || 0;
    art.dataset.nuevo = a.primer_visto || "";
    art.dataset.texto = (a.titulo || "").toLowerCase() + " " + (a.combustible || "").toLowerCase() + " " + (a.cambio || "").toLowerCase();

    art.innerHTML =
      '<img class="' + fotoClase + '" src="' + esc(foto) + '" loading="lazy" alt="">' +
      '<div class="contenido">' +
      '<div class="eyebrow">' + esc(nombreModelo) + "</div>" +
      '<div class="cabecera"><h3>' + esc(a.titulo) + '</h3><div class="puntuacion" title="' + puntuacion + '/5">' + estrellas(puntuacion) + "</div></div>" +
      '<div class="badges">' + badges + "</div>" +
      '<div class="specs">' +
      "<span>" + esc(a.anio || "-") + "</span>" +
      '<span class="num">' + fmtKm(a.km) + "</span>" +
      "<span>" + esc(a.combustible || "-") + "</span>" +
      "<span>" + esc(a.cambio || "-") + "</span>" +
      "<span>" + esc(a.etiqueta || "-") + "</span>" +
      "<span>" + esc(a.ubicacion || "-") + "</span>" +
      "</div>" +
      '<div class="precio num">' + fmtEur(a.precio) + '<span class="garantia">' + (a.garantia_meses ? "Garantía " + a.garantia_meses + " meses" : "") + "</span></div>" +
      '<p class="explicacion-puntuacion">' + esc(a.explicacion || "") + "</p>" +
      tablaFinanciacion(a.financiacion) +
      '<div class="pie"><span class="web">' + esc(a.web_id) + '</span><a class="enlace" href="' + esc(a.url) + '" target="_blank" rel="noopener">Ver anuncio</a></div>' +
      "</div>";
    return art;
  }

  function renderHero(data) {
    var fecha = new Date(data.generado);
    document.getElementById("subtitulo-hero").textContent = data.fecha + " · Madrid · ftomeocasion · canalcar · clicars · coches.com · autofesa · ocasionplus";
    document.getElementById("chip-anuncios").textContent = data.anuncios.length + " anuncios activos";
    document.getElementById("chip-modelos").textContent = data.modelos.length + " modelos";
    document.getElementById("chip-actualizado").textContent =
      "Actualizado " + fecha.toLocaleString("es-ES", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  }

  function renderTop10(anuncios, nombresModelo) {
    var cont = document.getElementById("top10-contenedor");
    var top = anuncios.slice().sort(function (a, b) { return (b.puntuacion || 0) - (a.puntuacion || 0); }).slice(0, 10);
    if (!top.length) {
      cont.innerHTML = '<p class="sin-resultados">Todavía no hay anuncios suficientes para armar un Top 10.</p>';
      return;
    }
    var grid = document.createElement("div");
    grid.className = "top10-grid";
    top.forEach(function (a, i) {
      var el = document.createElement("a");
      el.className = "top10-item";
      el.href = a.url;
      el.target = "_blank";
      el.rel = "noopener";
      el.innerHTML =
        '<div class="top10-rank">' + (i + 1) + "</div>" +
        '<img src="' + esc(a.foto_url || PLACEHOLDER_SVG) + '" loading="lazy" alt="">' +
        '<div class="top10-cuerpo">' +
        '<div class="eyebrow">' + esc(nombresModelo[a.modelo_id] || "") + "</div>" +
        "<h3>" + esc(a.titulo) + "</h3>" +
        '<p class="top10-motivo">' + esc(a.explicacion || "") + "</p>" +
        '<div class="top10-datos">' +
        '<span class="precio num">' + fmtEur(a.precio) + "</span>" +
        '<span class="num">' + fmtKm(a.km) + "</span>" +
        "<span>" + esc(a.anio || "-") + "</span>" +
        '<span class="puntuacion">' + (a.puntuacion || 0).toFixed(1) + "/5</span>" +
        "</div></div>";
      grid.appendChild(el);
    });
    cont.innerHTML = "";
    cont.appendChild(grid);
  }

  function modalFichaHtml(m) {
    var fotos = (m.fotos && m.fotos.length ? m.fotos : [PLACEHOLDER_SVG])
      .map(function (f) { return '<img src="' + esc(f) + '" loading="lazy" alt="">'; })
      .join("");
    var atribucion = m.foto_atribucion ? '<p class="foto-atribucion">' + esc(m.foto_atribucion) + "</p>" : "";
    var puntuacion = m.fiabilidad_puntuacion || 0;
    var nEstrellas = Math.floor(puntuacion + 0.5);
    var tabla = (m.tabla_detalle || []).map(function (f) {
      var clases = { Problema: "tipo-problema", "Filtro aplicado": "tipo-filtro", "Preferencia de puntuación": "tipo-preferencia" };
      var clase = clases[f.tipo] || "tipo-parametro";
      return (
        "<tr><td><span class=\"tipo-pill " + clase + "\">" + esc(f.tipo) + "</span></td>" +
        "<td><strong>" + esc(f.tema) + "</strong></td>" +
        "<td>" + esc(f.descripcion) + "</td>" +
        '<td class="fuente">' + esc(f.fuente) + "</td></tr>"
      );
    }).join("");
    var revision = (m.revision_obligada || []).map(function (r) { return "<li>" + esc(r) + "</li>"; }).join("");

    return (
      "<h2>" + esc(m.nombre) + '</h2><div class="modal-galeria">' + fotos + "</div>" + atribucion +
      "<h3>Fiabilidad del modelo</h3>" +
      '<div class="fiabilidad-bloque"><div class="fiabilidad-estrellas" title="' + puntuacion + '/5">' +
      "★".repeat(nEstrellas) + "☆".repeat(5 - nEstrellas) + ' <span class="num">' + puntuacion + "/5</span></div>" +
      "<p>" + esc(m.fiabilidad_descripcion || "Sin valoración todavía.") + "</p></div>" +
      "<h3>Problemas conocidos y parámetros de búsqueda</h3>" +
      '<table class="tabla-detalle"><thead><tr><th>Tipo</th><th>Tema</th><th>Descripción detallada / por qué</th><th>Fuente</th></tr></thead><tbody>' + tabla + "</tbody></table>" +
      "<h3>Qué revisar al comprar una unidad de segunda mano</h3>" +
      '<ul class="modal-revision">' + revision + "</ul>"
    );
  }

  function renderFichas(modelos) {
    var cont = document.getElementById("fichas-contenedor");
    cont.innerHTML = "";
    var dialogo = document.getElementById("modal-ficha");
    modelos.filter(function (m) { return m.categoria !== "comparacion"; }).forEach(function (m) {
      var foto = (m.fotos && m.fotos[0]) || PLACEHOLDER_SVG;
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "ficha-modelo";
      btn.innerHTML =
        '<img src="' + esc(foto) + '" loading="lazy" alt="">' +
        '<div class="ficha-cuerpo"><h3>' + esc(m.nombre) + "</h3>" +
        '<div class="ficha-bloque"><span class="ficha-etiqueta">Principales problemas</span><p>' + esc(m.resumen_problemas || "Sin resumen todavía.") + "</p></div>" +
        '<div class="ficha-bloque"><span class="ficha-etiqueta">Parámetros de búsqueda definidos</span><p>' + esc(m.resumen_parametros || "Sin resumen todavía.") + "</p></div>" +
        '<span class="ver-mas">Ver ficha completa →</span></div>';
      btn.addEventListener("click", function () {
        document.getElementById("modal-contenido").innerHTML = modalFichaHtml(m);
        dialogo.showModal();
      });
      cont.appendChild(btn);
    });
  }

  function aplicarFiltros(anuncios) {
    var modelo = document.getElementById("filtro-modelo").value;
    var orden = document.getElementById("filtro-orden").value;
    var precioMax = parseFloat(document.getElementById("filtro-precio-max").value);
    var kmMax = parseFloat(document.getElementById("filtro-km-max").value);
    var texto = document.getElementById("filtro-texto").value.trim().toLowerCase();

    var tarjetas = Array.prototype.slice.call(document.querySelectorAll("#listado .tarjeta"));
    var visibles = 0;
    tarjetas.forEach(function (t) {
      var ok = modelo === "todos" || t.dataset.modelo === modelo;
      if (ok && !isNaN(precioMax) && parseFloat(t.dataset.precio) > precioMax) ok = false;
      if (ok && !isNaN(kmMax) && parseFloat(t.dataset.km) > kmMax) ok = false;
      if (ok && texto && t.dataset.texto.indexOf(texto) === -1) ok = false;
      t.hidden = !ok;
      if (ok) visibles++;
    });

    document.getElementById("contador-resultados").textContent = visibles + " anuncio" + (visibles === 1 ? "" : "s");

    var contenedor = document.getElementById("listado");
    tarjetas
      .slice()
      .sort(function (a, b) {
        if (orden === "puntuacion") return parseFloat(b.dataset.puntuacion) - parseFloat(a.dataset.puntuacion);
        if (orden === "precio_asc") return parseFloat(a.dataset.precio) - parseFloat(b.dataset.precio);
        if (orden === "precio_desc") return parseFloat(b.dataset.precio) - parseFloat(a.dataset.precio);
        if (orden === "km_asc") return parseFloat(a.dataset.km) - parseFloat(b.dataset.km);
        if (orden === "nuevo") return (b.dataset.nuevo || "").localeCompare(a.dataset.nuevo || "");
        return 0;
      })
      .forEach(function (t) { contenedor.appendChild(t); });
  }

  function renderAnuncios(data) {
    var nombresModelo = {};
    data.modelos.forEach(function (m) { nombresModelo[m.id] = m.nombre; });

    var selModelo = document.getElementById("filtro-modelo");
    data.modelos.forEach(function (m) {
      var opt = document.createElement("option");
      opt.value = m.id;
      opt.textContent = m.nombre;
      selModelo.appendChild(opt);
    });

    var listado = document.getElementById("listado");
    listado.innerHTML = "";
    if (!data.anuncios.length) {
      listado.innerHTML = '<p class="sin-resultados">Sin anuncios activos que cumplan los filtros ahora mismo.</p>';
    } else {
      data.anuncios.forEach(function (a) {
        listado.appendChild(tarjetaAnuncioHtml(a, nombresModelo[a.modelo_id] || a.modelo_id));
      });
    }

    ["filtro-modelo", "filtro-orden", "filtro-precio-max", "filtro-km-max", "filtro-texto"].forEach(function (id) {
      document.getElementById(id).addEventListener("input", function () { aplicarFiltros(data.anuncios); });
    });
    aplicarFiltros(data.anuncios);

    return nombresModelo;
  }

  function tarjetasAnunciosHtml(modeloId, nombresModelo, sinResultadosTexto) {
    var anuncios = window.__datosApp.anuncios.filter(function (a) { return a.modelo_id === modeloId; });
    if (!anuncios.length) {
      return '<p class="sin-resultados">' + esc(sinResultadosTexto) + "</p>";
    }
    var contTarjetas = document.createElement("div");
    contTarjetas.className = "tarjetas";
    anuncios
      .slice()
      .sort(function (a, b) { return (b.puntuacion || 0) - (a.puntuacion || 0); })
      .forEach(function (a) { contTarjetas.appendChild(tarjetaAnuncioHtml(a, nombresModelo[a.modelo_id] || a.modelo_id)); });
    return contTarjetas.outerHTML;
  }

  function renderComparativas(modelos, nombresModelo) {
    var cont = document.getElementById("comparativas-contenedor");
    cont.innerHTML = "";
    var comparativas = modelos.filter(function (m) { return m.categoria === "comparacion" && !m.es_alternativa_de; });
    if (!comparativas.length) {
      cont.innerHTML = '<p class="sin-resultados">No hay ninguna comparativa activa ahora mismo.</p>';
      return;
    }
    var alternativasPorPadre = {};
    modelos.filter(function (m) { return m.categoria === "comparacion" && m.es_alternativa_de; }).forEach(function (m) {
      (alternativasPorPadre[m.es_alternativa_de] = alternativasPorPadre[m.es_alternativa_de] || []).push(m);
    });

    comparativas.forEach(function (m) {
      var bloque = document.createElement("article");
      bloque.className = "comparativa-bloque";

      var alternativasHtml = (alternativasPorPadre[m.id] || []).map(function (alt) {
        return (
          "<h4>" + esc(alt.nombre) + "</h4>" +
          tarjetasAnunciosHtml(alt.id, nombresModelo, "Todavía no hemos encontrado anuncios de esta alternativa en el mercado.")
        );
      }).join("");

      bloque.innerHTML =
        "<h3>" + esc(m.comparacion_titulo || m.nombre) + "</h3>" +
        '<div class="comparativa-veredicto"><span class="ficha-etiqueta">Valoración</span><p>' + esc(m.comparacion_resumen || "") + "</p></div>" +
        '<div class="comparativa-veredicto"><span class="ficha-etiqueta">Alternativas que consideramos mejores</span><p>' + esc(m.alternativas_texto || "") + "</p></div>" +
        "<h4>Anuncios similares encontrados hoy</h4>" +
        tarjetasAnunciosHtml(m.id, nombresModelo, "Todavía no hemos encontrado anuncios similares activos en el mercado.") +
        alternativasHtml;
      cont.appendChild(bloque);
    });
  }

  function initTabs() {
    var botones = Array.prototype.slice.call(document.querySelectorAll(".tabs-nav button"));
    botones.forEach(function (btn) {
      btn.addEventListener("click", function () {
        botones.forEach(function (b) { b.classList.remove("activa"); });
        btn.classList.add("activa");
        ["top10", "fiabilidad", "anuncios", "comparativas"].forEach(function (tab) {
          document.getElementById("panel-" + tab).hidden = tab !== btn.dataset.tab;
        });
      });
    });
  }

  function initModal() {
    var dialogo = document.getElementById("modal-ficha");
    document.getElementById("modal-cerrar").addEventListener("click", function () { dialogo.close(); });
    dialogo.addEventListener("click", function (e) {
      if (e.target === dialogo) dialogo.close();
    });
  }

  function mostrarAvisoOffline(visible) {
    document.getElementById("aviso-offline").hidden = !visible;
  }

  function cargarDatos() {
    return fetch("data.json", { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        mostrarAvisoOffline(false);
        return r.json();
      })
      .catch(function () {
        mostrarAvisoOffline(true);
        return fetch("data.json").then(function (r) { return r.json(); });
      });
  }

  function init() {
    initTabs();
    initModal();
    cargarDatos().then(function (data) {
      window.__datosApp = data;
      renderHero(data);

      var nombresModeloTodos = {};
      var idsComparacion = {};
      data.modelos.forEach(function (m) {
        nombresModeloTodos[m.id] = m.nombre;
        if (m.categoria === "comparacion") idsComparacion[m.id] = true;
      });

      var dataFinalistas = {
        modelos: data.modelos.filter(function (m) { return !idsComparacion[m.id]; }),
        anuncios: data.anuncios.filter(function (a) { return !idsComparacion[a.modelo_id]; }),
      };

      var nombresModelo = renderAnuncios(dataFinalistas);
      renderTop10(dataFinalistas.anuncios, nombresModelo);
      renderFichas(data.modelos);
      renderComparativas(data.modelos, nombresModeloTodos);
    }).catch(function (err) {
      document.getElementById("subtitulo-hero").textContent = "No se pudieron cargar los datos. Revisa la conexión y recarga.";
      console.error(err);
    });

    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("sw.js").catch(function (err) { console.warn("sw:", err); });
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
