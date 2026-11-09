"""Genera el informe HTML diario (Paso 8 del plan) a partir de lo que hay en SQLite."""
from __future__ import annotations

import html
import json
from datetime import date, datetime
from pathlib import Path

from db import storage
from financing import simular as simular_financiacion
from scoring import construir_explicacion

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

PLACEHOLDER_SVG = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 240'>"
    "<rect width='400' height='240' fill='%23e4e1da'/>"
    "<path d='M60 150l20-45a18 18 0 0 1 16-11h88a18 18 0 0 1 16 11l20 45' "
    "fill='none' stroke='%23a39b8a' stroke-width='6' stroke-linejoin='round'/>"
    "<rect x='55' y='150' width='290' height='34' rx='10' fill='%23a39b8a'/>"
    "<circle cx='105' cy='186' r='16' fill='%23e4e1da' stroke='%23a39b8a' stroke-width='6'/>"
    "<circle cx='295' cy='186' r='16' fill='%23e4e1da' stroke='%23a39b8a' stroke-width='6'/>"
    "</svg>"
)


def _fmt_eur(valor) -> str:
    if valor is None:
        return "-"
    return f"{valor:,.0f} €".replace(",", ".")


def _fmt_km(valor) -> str:
    if valor is None:
        return "-"
    return f"{valor:,.0f} km".replace(",", ".")


def _es_hoy(iso_fecha: str) -> bool:
    try:
        return datetime.fromisoformat(iso_fecha).date() == date.today()
    except (ValueError, TypeError):
        return False


def _pros_contras(row) -> tuple[list[str], list[str]]:
    try:
        datos = json.loads(row["motivos"]) if row["motivos"] else {}
    except (TypeError, json.JSONDecodeError):
        return [], []
    return datos.get("pros", []), datos.get("contras", [])


def _financiacion_filas(row) -> str:
    financiacion = simular_financiacion(row["precio"], row["cuota_financiacion_vendedor"])
    filas = ""
    for clave, etiqueta in [
        ("oferta_vendedor", "Oferta del vendedor"),
        ("mercado_medio", "Mercado medio"),
        ("prestamo_familiar", "Préstamo familiar (3%, sin entrada)"),
    ]:
        datos = financiacion.get(clave)
        cuota = datos.get("cuota_mensual") if datos else None
        cuota_txt = _fmt_eur(cuota) + "/mes" if cuota else "No especificada"
        filas += f"<tr><td>{etiqueta}</td><td>{cuota_txt}</td></tr>"
    return filas


def _tarjeta_html(row, nombre_modelo: str) -> str:
    nuevo = _es_hoy(row["primer_visto"])
    bajada = row["primer_precio"] is not None and row["precio"] is not None and row["precio"] < row["primer_precio"]

    badges = ""
    if nuevo:
        badges += '<span class="badge badge-nuevo">Nuevo hoy</span>'
    if bajada:
        badges += f'<span class="badge badge-bajada">Bajada: {_fmt_eur(row["primer_precio"])} → {_fmt_eur(row["precio"])}</span>'

    foto = row["foto_url"] or PLACEHOLDER_SVG
    foto_clase = "foto" if row["foto_url"] else "foto foto-generica"

    puntuacion = row["puntuacion"] or 0
    estrellas = "★" * round(puntuacion) + "☆" * (5 - round(puntuacion))

    pros, contras = _pros_contras(row)
    explicacion = construir_explicacion(puntuacion, pros, contras)

    return f"""
    <article class="tarjeta" data-modelo="{html.escape(row["modelo_id"])}" data-puntuacion="{puntuacion}"
         data-precio="{row["precio"] or 0}" data-km="{row["km"] or 0}" data-web="{html.escape(row["web_id"])}">
      <img class="{foto_clase}" src="{html.escape(foto)}" loading="lazy" alt="">
      <div class="contenido">
        <div class="eyebrow">{html.escape(nombre_modelo)}</div>
        <div class="cabecera">
          <h3>{html.escape(row["titulo"] or "")}</h3>
          <div class="puntuacion" title="{puntuacion}/5">{estrellas}</div>
        </div>
        <div class="badges">{badges}</div>
        <div class="specs">
          <span>{row["anio"] or "-"}</span>
          <span class="num">{_fmt_km(row["km"])}</span>
          <span>{html.escape(row["combustible"] or "-")}</span>
          <span>{html.escape(row["cambio"] or "-")}</span>
          <span>{html.escape(row["etiqueta"] or "-")}</span>
          <span>{html.escape(row["ubicacion"] or "-")}</span>
        </div>
        <div class="precio num">{_fmt_eur(row["precio"])}
          <span class="garantia">{f'Garantía {row["garantia_meses"]} meses' if row["garantia_meses"] else ''}</span>
        </div>
        <p class="explicacion-puntuacion">{html.escape(explicacion)}</p>
        <table class="financiacion">{_financiacion_filas(row)}</table>
        <div class="pie">
          <span class="web">{html.escape(row["web_id"])}</span>
          <a class="enlace" href="{html.escape(row["url"])}" target="_blank" rel="noopener">Ver anuncio</a>
        </div>
      </div>
    </article>
    """


def _top10_html(filas_todas: list, nombres_modelo: dict) -> str:
    top = sorted(filas_todas, key=lambda r: r["puntuacion"] or 0, reverse=True)[:10]
    if not top:
        return '<p class="sin-resultados">Todavía no hay anuncios suficientes para armar un Top 10.</p>'

    tarjetas = ""
    for i, row in enumerate(top, start=1):
        pros, contras = _pros_contras(row)
        explicacion = construir_explicacion(row["puntuacion"], pros, contras)
        foto = row["foto_url"] or PLACEHOLDER_SVG
        tarjetas += f"""
        <article class="top10-item">
          <div class="top10-rank">{i}</div>
          <img src="{html.escape(foto)}" loading="lazy" alt="">
          <div class="top10-cuerpo">
            <div class="eyebrow">{html.escape(nombres_modelo.get(row["modelo_id"], ""))}</div>
            <h3>{html.escape(row["titulo"] or "")}</h3>
            <p class="top10-motivo">{html.escape(explicacion)}</p>
            <div class="top10-datos">
              <span class="precio num">{_fmt_eur(row["precio"])}</span>
              <span class="num">{_fmt_km(row["km"])}</span>
              <span>{row["anio"] or "-"}</span>
              <span class="puntuacion">{row["puntuacion"]:.1f}/5</span>
            </div>
            <a class="enlace" href="{html.escape(row["url"])}" target="_blank" rel="noopener">Ver anuncio</a>
          </div>
        </article>
        """
    return f'<div class="top10-grid">{tarjetas}</div>'


def _fmt_num(valor) -> str:
    return f"{valor:,.0f}".replace(",", ".") if valor is not None else "-"


def _filas_parametros_aplicados(modelo: dict, generales: dict) -> list[dict]:
    """Genera, a partir de los campos que realmente usan filtros.py/scoring.py, una fila
    por cada parametro aplicado a este modelo. Distingue "Filtro aplicado" (excluye
    anuncios directamente) de "Preferencia de puntuación" (no excluye, solo puntua mas o
    menos alto) — asi se ve con claridad cuando el filtro es mas amplio que la preferencia
    real (p.ej. filtro desde un año, pero la puntuación premia unos años más tarde)."""
    filas: list[dict] = []
    fuente_research = "Research de fiabilidad del modelo"

    precio_min_modelo = modelo.get("precio_min")
    precio_max_modelo = modelo.get("precio_max")
    if precio_min_modelo is not None or precio_max_modelo is not None:
        precio_min_efectivo = precio_min_modelo if precio_min_modelo is not None else generales.get("precio_min")
        precio_max_efectivo = precio_max_modelo if precio_max_modelo is not None else generales.get("precio_max")
        filas.append({
            "tipo": "Filtro aplicado",
            "tema": "Precio (presupuesto propio de este modelo)",
            "descripcion": f"Solo se consideran anuncios entre {_fmt_num(precio_min_efectivo)} € y {_fmt_num(precio_max_efectivo)} €. "
                            f"Este modelo tiene un presupuesto distinto al general porque su precio de mercado real no encaja en el rango de 12.000-23.000 € del resto de finalistas."
                            + (f" {modelo['justificacion_precio']}" if modelo.get("justificacion_precio") else ""),
            "fuente": "Research de precios de mercado" if modelo.get("justificacion_precio") else "Presupuesto definido por el usuario",
        })
    else:
        filas.append({
            "tipo": "Filtro aplicado",
            "tema": "Precio",
            "descripcion": f"Solo se consideran anuncios entre {_fmt_num(generales.get('precio_min'))} € y {_fmt_num(generales.get('precio_max'))} €. Es el rango de presupuesto general, igual para todos los modelos.",
            "fuente": "Presupuesto definido por el usuario",
        })
    filas.append({
        "tipo": "Filtro aplicado",
        "tema": "Combustible",
        "descripcion": "Se excluyen directamente los anuncios de diésel o eléctrico puro. Solo entran gasolina e híbridos no enchufables (el combustible se infiere del texto del anuncio cuando la web no lo da en un campo propio).",
        "fuente": "Criterio definido por el usuario",
    })

    anio_min = modelo.get("anio_min")
    anio_pref = modelo.get("anio_preferente_desde")
    if anio_min is not None:
        filas.append({
            "tipo": "Filtro aplicado",
            "tema": "Año mínimo",
            "descripcion": f"Se excluyen directamente los anuncios anteriores a {anio_min}.",
            "fuente": fuente_research,
        })
    anios_evitar = modelo.get("anios_evitar") or []
    if anios_evitar:
        filas.append({
            "tipo": "Filtro aplicado",
            "tema": "Años a evitar",
            "descripcion": f"Se excluyen específicamente los años {', '.join(str(a) for a in anios_evitar)}, aunque estén dentro del rango general permitido, por los problemas documentados precisamente en esos años.",
            "fuente": fuente_research,
        })
    if anio_pref is not None and anio_min is not None:
        if anio_pref > anio_min:
            filas.append({
                "tipo": "Preferencia de puntuación",
                "tema": "Año preferente",
                "descripcion": f"El filtro deja pasar anuncios desde {anio_min} (no se excluyen los anteriores a {anio_pref}), pero en la puntuación se premian especialmente los años {anio_pref} en adelante. Es decir: el filtrado es más amplio ({anio_min}+) que la preferencia real a la hora de puntuar ({anio_pref}+).",
                "fuente": fuente_research,
            })
        else:
            filas.append({
                "tipo": "Preferencia de puntuación",
                "tema": "Año preferente",
                "descripcion": f"El año preferente coincide con el filtro mínimo ({anio_min}): no hay un rango más amplio aparte, cualquier año que pase el filtro puntúa igual de bien en este criterio.",
                "fuente": fuente_research,
            })

    km_max = modelo.get("km_max")
    if km_max is not None:
        filas.append({
            "tipo": "Filtro aplicado",
            "tema": "Kilometraje máximo",
            "descripcion": f"Se excluyen directamente los anuncios con más de {_fmt_num(km_max)} km.",
            "fuente": fuente_research,
        })

    cambio_pref = modelo.get("cambio_preferente") or []
    if cambio_pref:
        filas.append({
            "tipo": "Preferencia de puntuación",
            "tema": "Cambio preferente",
            "descripcion": f"No se excluyen otros tipos de cambio, pero puntúan más alto los anuncios con: {', '.join(cambio_pref)}.",
            "fuente": fuente_research,
        })

    motor_evitar = modelo.get("motor_evitar") or []
    if motor_evitar:
        filas.append({
            "tipo": "Preferencia de puntuación",
            "tema": "Motor/variante a evitar",
            "descripcion": f"No se excluyen directamente, pero restan puntos si el anuncio menciona: {', '.join(motor_evitar)}.",
            "fuente": fuente_research,
        })

    return filas


def _tabla_detalle_html(modelo: dict, generales: dict) -> str:
    filas = list(modelo.get("tabla_detalle", [])) + _filas_parametros_aplicados(modelo, generales)
    if not filas:
        return "<p>Sin detalle estructurado todavía.</p>"
    clases_tipo = {
        "Problema": "tipo-problema",
        "Filtro aplicado": "tipo-filtro",
        "Preferencia de puntuación": "tipo-preferencia",
    }
    filas_html = ""
    for f in filas:
        tipo = f.get("tipo", "")
        clase_tipo = clases_tipo.get(tipo, "tipo-parametro")
        filas_html += f"""
        <tr>
          <td><span class="tipo-pill {clase_tipo}">{html.escape(tipo)}</span></td>
          <td><strong>{html.escape(f.get("tema", ""))}</strong></td>
          <td>{html.escape(f.get("descripcion", ""))}</td>
          <td class="fuente">{html.escape(f.get("fuente", ""))}</td>
        </tr>
        """
    return f"""
    <table class="tabla-detalle">
      <thead><tr><th>Tipo</th><th>Tema</th><th>Descripción detallada / por qué</th><th>Fuente</th></tr></thead>
      <tbody>{filas_html}</tbody>
    </table>
    """


def _fichas_modelo_html(conn, parametros_modelos: list[dict], generales: dict) -> tuple[str, str]:
    """Devuelve (tarjetas_resumen, modales) para el panel de fiabilidad."""
    tarjetas = ""
    modales = ""
    for modelo in parametros_modelos:
        mid = modelo["id"]
        fotos = storage.fotos_modelo(conn, mid, limit=8)
        foto_generica = modelo.get("foto_generica")
        atribucion_html = ""
        if not fotos and foto_generica:
            fotos = [foto_generica]
            atribucion = modelo.get("foto_generica_atribucion", "")
            if atribucion:
                atribucion_html = f'<p class="foto-atribucion">{html.escape(atribucion)}</p>'
        foto_principal = fotos[0] if fotos else PLACEHOLDER_SVG

        tarjetas += f"""
        <a href="#modal-{html.escape(mid)}" class="ficha-modelo">
          <img src="{html.escape(foto_principal)}" loading="lazy" alt="">
          <div class="ficha-cuerpo">
            <h3>{html.escape(modelo["nombre"])}</h3>
            <div class="ficha-bloque">
              <span class="ficha-etiqueta">Principales problemas</span>
              <p>{html.escape(modelo.get("resumen_problemas", "Sin resumen todavía."))}</p>
            </div>
            <div class="ficha-bloque">
              <span class="ficha-etiqueta">Parámetros de búsqueda definidos</span>
              <p>{html.escape(modelo.get("resumen_parametros", "Sin resumen todavía."))}</p>
            </div>
            <span class="ver-mas">Ver ficha completa →</span>
          </div>
        </a>
        """

        galeria = "".join(f'<img src="{html.escape(f)}" loading="lazy" alt="">' for f in fotos) or (
            f'<img src="{PLACEHOLDER_SVG}" alt="">'
        )

        # Modal solo-CSS (ancla + :target): funciona sin JavaScript, necesario porque
        # Gmail y otros clientes de correo bloquean <script> y onclick al abrir el adjunto.
        modales += f"""
        <div id="modal-{html.escape(mid)}" class="modal-overlay">
          <a href="#" class="modal-overlay-fondo" aria-label="Cerrar"></a>
          <div class="modal-modelo">
            <a href="#" class="modal-cerrar" aria-label="Cerrar">✕</a>
            <h2>{html.escape(modelo["nombre"])}</h2>
            <div class="modal-galeria">{galeria}</div>
            {atribucion_html}
            <h3>Fiabilidad del modelo</h3>
            <div class="fiabilidad-bloque">
              <div class="fiabilidad-estrellas" title="{modelo.get('fiabilidad_puntuacion', 0)}/5">{'★' * int(modelo.get('fiabilidad_puntuacion', 0) + 0.5) + '☆' * (5 - int(modelo.get('fiabilidad_puntuacion', 0) + 0.5))} <span class="num">{modelo.get('fiabilidad_puntuacion', '-')}/5</span></div>
              <p>{html.escape(modelo.get("fiabilidad_descripcion", "Sin valoración todavía."))}</p>
            </div>
            <h3>Problemas conocidos y parámetros de búsqueda</h3>
            {_tabla_detalle_html(modelo, generales)}
            <h3>Qué revisar al comprar una unidad de segunda mano</h3>
            <ul class="modal-revision">{"".join(f"<li>{html.escape(r)}</li>" for r in modelo.get("revision_obligada", []))}</ul>
          </div>
        </div>
        """
    return tarjetas, modales


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Source+Sans+3:wght@400;600;700&family=JetBrains+Mono:wght@500;700&display=swap');

:root {
  --bg: #f4f1ea;
  --surface: #ffffff;
  --border: #e3ddcf;
  --fg: #211d17;
  --fg-muted: #6b6354;
  --accent: #b5471b;
  --accent-fg: #ffffff;
  --good-bg: #dcefdd;
  --good-fg: #1d6b2c;
  --warn-bg: #fbe6cf;
  --warn-fg: #9a5a0a;
  --bad-bg: #f7dede;
  --bad-fg: #a3271c;
  --chip-bg: #ece7da;
  --font-display: 'Fraunces', Georgia, serif;
  --font-body: 'Source Sans 3', -apple-system, Segoe UI, sans-serif;
  --font-mono: 'JetBrains Mono', 'Courier New', monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #1b1915; --surface: #242019; --border: #3a342a; --fg: #efe9dc; --fg-muted: #aba391;
    --accent: #e07a4a; --accent-fg: #1b1915;
    --good-bg: #1d3524; --good-fg: #7fd99a; --warn-bg: #3a2a12; --warn-fg: #f0b26b;
    --bad-bg: #3a1d1a; --bad-fg: #f29088; --chip-bg: #2d281f;
    color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg: #1b1915; --surface: #242019; --border: #3a342a; --fg: #efe9dc; --fg-muted: #aba391;
  --accent: #e07a4a; --accent-fg: #1b1915;
  --good-bg: #1d3524; --good-fg: #7fd99a; --warn-bg: #3a2a12; --warn-fg: #f0b26b;
  --bad-bg: #3a1d1a; --bad-fg: #f29088; --chip-bg: #2d281f;
  color-scheme: dark;
}

* { box-sizing: border-box; }
body { font-family: var(--font-body); background: var(--bg); color: var(--fg); margin: 0; }
.wrap { max-width: 1180px; margin: 0 auto; padding: 0 max(16px, env(safe-area-inset-left, 0px)) 48px max(16px, env(safe-area-inset-right, 0px)); }

header.hero { background: var(--accent); color: var(--accent-fg); padding: 28px max(16px, env(safe-area-inset-left, 0px)) 24px; }
header.hero .wrap { padding-left: 0; padding-right: 0; }
header.hero h1 { font-family: var(--font-display); font-weight: 700; font-size: clamp(1.5rem, 1.1rem + 2vw, 2.3rem); margin: 0 0 6px; text-wrap: balance; }
header.hero p { margin: 0; opacity: .92; font-size: .95rem; }
header.hero .resumen-chips { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px; }
header.hero .chip { background: rgba(255,255,255,.18); padding: 5px 12px; border-radius: 999px; font-size: .8rem; font-weight: 600; }

/* --- Pestañas (solo CSS, sin JS: funcionan dentro de clientes de correo que bloquean
   <script>, como el visor de adjuntos de Gmail en movil) --- */
.tab-input { position: absolute; opacity: 0; width: 1px; height: 1px; pointer-events: none; }
.tabs-nav { display: flex; gap: 4px; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 4px; margin: -22px 0 28px; position: relative; z-index: 2; flex-wrap: wrap; }
.tabs-nav label { flex: 1; min-width: 140px; text-align: center; font: inherit; font-weight: 700; font-size: .88rem; padding: 10px 12px; border-radius: 9px; background: transparent; color: var(--fg-muted); cursor: pointer; }
.tab-panel { display: none; }
#tab-top10:checked ~ .tabs-nav label[for="tab-top10"],
#tab-fiabilidad:checked ~ .tabs-nav label[for="tab-fiabilidad"],
#tab-anuncios:checked ~ .tabs-nav label[for="tab-anuncios"] { background: var(--accent); color: var(--accent-fg); }
#tab-top10:checked ~ #panel-top10,
#tab-fiabilidad:checked ~ #panel-fiabilidad,
#tab-anuncios:checked ~ #panel-anuncios { display: block; }

h2.titulo-seccion { font-family: var(--font-display); font-size: 1.4rem; font-weight: 700; margin: 8px 0 6px; }
p.subtitulo-seccion { color: var(--fg-muted); margin: 0 0 18px; max-width: 65ch; }

/* --- Top 10 --- */
.top10-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.top10-item { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 14px; display: grid; grid-template-columns: 30px 120px 1fr; gap: 12px; align-items: start; }
.top10-rank { font-family: var(--font-display); font-size: 1.5rem; font-weight: 700; color: var(--accent); }
.top10-item img { width: 120px; height: 92px; object-fit: cover; border-radius: 8px; background: var(--chip-bg); }
.top10-cuerpo h3 { margin: 2px 0 4px; font-size: .98rem; }
.top10-motivo { font-size: .82rem; color: var(--fg-muted); margin: 0 0 8px; min-width: 0; }
.top10-datos { display: flex; gap: 10px; flex-wrap: wrap; font-size: .8rem; margin-bottom: 8px; }
.top10-datos .precio { font-weight: 700; color: var(--accent); }
.top10-datos .puntuacion { font-weight: 700; }

/* --- Fichas por modelo --- */
.fichas-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
.ficha-modelo { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; display: flex; flex-direction: column; cursor: pointer; transition: transform .15s ease; text-decoration: none; color: inherit; }
.ficha-modelo:hover { transform: translateY(-2px); }
.ficha-modelo img { width: 100%; height: 200px; object-fit: cover; background: var(--chip-bg); }
.ficha-cuerpo { padding: 14px; display: flex; flex-direction: column; gap: 10px; }
.ficha-cuerpo h3 { margin: 0; font-size: 1.05rem; }
.ficha-etiqueta { font-size: .7rem; text-transform: uppercase; letter-spacing: .04em; color: var(--accent); font-weight: 700; }
.ficha-bloque p { margin: 3px 0 0; font-size: .85rem; }
.ver-mas { font-size: .8rem; font-weight: 700; color: var(--accent); margin-top: 4px; }

/* --- Modal de ficha de modelo (ancla + :target, sin JS) --- */
.modal-overlay { display: none; position: fixed; inset: 0; z-index: 50; align-items: center; justify-content: center; padding: 20px; background: rgba(20,16,10,.55); }
.modal-overlay:target { display: flex; }
.modal-overlay-fondo { position: absolute; inset: 0; }
.modal-modelo { position: relative; z-index: 1; width: min(760px, 92vw); max-height: 86vh; overflow-y: auto; border-radius: 16px; padding: 22px; background: var(--surface); color: var(--fg); }
.modal-modelo h2 { font-family: var(--font-display); margin: 4px 0 14px; padding-right: 30px; }
.modal-modelo h3 { font-size: 1rem; margin: 20px 0 8px; }
.modal-cerrar { position: absolute; top: 16px; right: 16px; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 50%; border: 1px solid var(--border); background: var(--bg); color: var(--fg); font-size: 1rem; text-decoration: none; cursor: pointer; }
.modal-galeria { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 6px; }
.modal-galeria img { height: 200px; width: auto; max-width: 90%; object-fit: cover; border-radius: 10px; flex: 0 0 auto; }
.tabla-detalle { width: 100%; border-collapse: collapse; font-size: .82rem; margin-top: 4px; }
.tabla-detalle th { text-align: left; font-size: .72rem; text-transform: uppercase; color: var(--fg-muted); border-bottom: 2px solid var(--border); padding: 6px 8px; }
.tabla-detalle td { padding: 8px; border-bottom: 1px solid var(--border); vertical-align: top; }
.tabla-detalle td.fuente { color: var(--fg-muted); font-size: .76rem; }
.tipo-pill { font-size: .68rem; font-weight: 700; padding: 2px 8px; border-radius: 999px; white-space: nowrap; }
.tipo-problema { background: var(--bad-bg); color: var(--bad-fg); }
.tipo-filtro { background: var(--chip-bg); color: var(--fg); }
.tipo-preferencia { background: var(--good-bg); color: var(--good-fg); }
.tipo-parametro { background: var(--warn-bg); color: var(--warn-fg); }
.foto-atribucion { font-size: .7rem; color: var(--fg-muted); margin: 4px 0 0; }
.fiabilidad-bloque { background: var(--chip-bg); border-radius: 10px; padding: 12px 14px; }
.fiabilidad-estrellas { color: #e0a800; font-size: 1.05rem; margin-bottom: 6px; }
.fiabilidad-estrellas .num { color: var(--fg); font-size: .85rem; margin-left: 4px; }
.fiabilidad-bloque p { margin: 0; font-size: .85rem; }
.modal-revision { font-size: .82rem; padding-left: 18px; display: flex; flex-direction: column; gap: 5px; }

/* --- Filtros --- */
.barra-filtros { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 12px; margin-bottom: 18px; position: sticky; top: env(safe-area-inset-top, 0px); z-index: 5; }
.barra-filtros label { font-size: .78rem; color: var(--fg-muted); display: flex; flex-direction: column; gap: 3px; }
.barra-filtros select { font: inherit; padding: 6px 8px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg); color: var(--fg); }
.barra-filtros .contador { margin-left: auto; font-size: .8rem; color: var(--fg-muted); }

/* --- Listado principal --- */
.tarjetas { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
.tarjeta { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; display: flex; flex-direction: column; }
.tarjeta[hidden] { display: none; }
.foto { width: 100%; height: 230px; object-fit: cover; background: var(--chip-bg); display: block; }
.foto-generica { object-fit: contain; padding: 30px; }
.contenido { padding: 12px; display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.eyebrow { font-size: .68rem; text-transform: uppercase; letter-spacing: .05em; color: var(--accent); font-weight: 700; }
.cabecera { display: flex; justify-content: space-between; align-items: start; gap: 8px; }
.cabecera h3 { margin: 0; font-size: 1rem; min-width: 0; }
.puntuacion { color: #e0a800; white-space: nowrap; font-size: .95rem; }
.badges { display: flex; gap: 6px; flex-wrap: wrap; }
.badge { font-size: .72rem; padding: 2px 8px; border-radius: 999px; font-weight: 700; }
.badge-nuevo { background: var(--good-bg); color: var(--good-fg); }
.badge-bajada { background: var(--warn-bg); color: var(--warn-fg); }
.specs { display: flex; flex-wrap: wrap; gap: 6px; font-size: .78rem; color: var(--fg-muted); }
.specs span { background: var(--chip-bg); padding: 2px 7px; border-radius: 6px; }
.precio { font-size: 1.2rem; font-weight: 700; display: flex; justify-content: space-between; align-items: baseline; color: var(--accent); }
.garantia { font-size: .72rem; color: var(--good-fg); font-weight: 600; }
.explicacion-puntuacion { font-size: .8rem; color: var(--fg-muted); margin: 2px 0 0; line-height: 1.4; }
.financiacion { width: 100%; font-size: .78rem; border-collapse: collapse; margin-top: 2px; }
.financiacion td { padding: 3px 0; border-top: 1px solid var(--border); }
.financiacion td:last-child { text-align: right; font-weight: 600; font-family: var(--font-mono); }
.pie { display: flex; justify-content: space-between; align-items: center; margin-top: 4px; }
.web { font-size: .72rem; color: var(--fg-muted); text-transform: uppercase; }
.enlace { background: var(--accent); color: var(--accent-fg); text-decoration: none; padding: 6px 14px; border-radius: 999px; font-size: .85rem; font-weight: 600; }
.num { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
.sin-resultados { color: var(--fg-muted); font-style: italic; padding: 8px 0; }

@media (max-width: 560px) {
  .pros-contras-grid { grid-template-columns: 1fr; }
  .top10-item { grid-template-columns: 24px 90px 1fr; }
  .top10-item img { width: 90px; height: 70px; }
}
"""

JS = """
(function () {
  // Las pestañas se manejan solo con CSS (inputs radio + :checked), ver más abajo
  // en el HTML: así funcionan también donde el correo bloquea JavaScript.

  // --- Filtros del listado ---
  var selModelo = document.getElementById('filtro-modelo');
  var selOrden = document.getElementById('filtro-orden');
  var contador = document.getElementById('contador-resultados');
  var tarjetas = Array.prototype.slice.call(document.querySelectorAll('#listado .tarjeta'));
  var contenedor = document.getElementById('listado');

  function aplicar() {
    var modelo = selModelo.value;
    var visibles = 0;
    tarjetas.forEach(function (t) {
      var ok = modelo === 'todos' || t.dataset.modelo === modelo;
      t.hidden = !ok;
      if (ok) visibles++;
    });
    if (contador) contador.textContent = visibles + ' anuncio' + (visibles === 1 ? '' : 's');

    var orden = selOrden.value;
    var ordenadas = tarjetas.slice().sort(function (a, b) {
      if (orden === 'puntuacion') return parseFloat(b.dataset.puntuacion) - parseFloat(a.dataset.puntuacion);
      if (orden === 'precio_asc') return parseFloat(a.dataset.precio) - parseFloat(b.dataset.precio);
      if (orden === 'precio_desc') return parseFloat(b.dataset.precio) - parseFloat(a.dataset.precio);
      if (orden === 'km_asc') return parseFloat(a.dataset.km) - parseFloat(b.dataset.km);
      return 0;
    });
    ordenadas.forEach(function (t) { contenedor.appendChild(t); });
  }

  selModelo.addEventListener('change', aplicar);
  selOrden.addEventListener('change', aplicar);
  aplicar();
})();
"""


def generar_informe(parametros_modelos: list[dict], parametros_generales: dict) -> Path:
    conn = storage.conectar()

    nombres_modelo = {m["id"]: m["nombre"] for m in parametros_modelos}
    todas_las_filas = storage.todos_los_anuncios_activos(conn)

    opciones_modelo = "".join(
        f'<option value="{html.escape(m["id"])}">{html.escape(m["nombre"])}</option>' for m in parametros_modelos
    )

    tarjetas_html = "".join(_tarjeta_html(f, nombres_modelo.get(f["modelo_id"], f["modelo_id"])) for f in todas_las_filas)
    if not tarjetas_html:
        tarjetas_html = '<p class="sin-resultados">Sin anuncios activos que cumplan los filtros ahora mismo.</p>'

    top10 = _top10_html(todas_las_filas, nombres_modelo)
    fichas_resumen, modales = _fichas_modelo_html(conn, parametros_modelos, parametros_generales)

    conn.close()

    hoy = date.today().isoformat()
    documento = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="claude:viewport-fit-sides" content="cover">
<title>Informe de coches de ocasión</title>
<style>{CSS}</style>
</head>
<body>
<header class="hero">
  <div class="wrap">
    <h1>Informe diario de coches de ocasión</h1>
    <p>{hoy} · Madrid · ftomeocasion · canalcar · clicars · coches.com · autofesa · ocasionplus</p>
    <div class="resumen-chips">
      <span class="chip">{len(todas_las_filas)} anuncios activos</span>
      <span class="chip">{len(parametros_modelos)} modelos</span>
    </div>
  </div>
</header>

<div class="wrap">

  <input type="radio" name="tabs" id="tab-top10" class="tab-input" checked>
  <input type="radio" name="tabs" id="tab-fiabilidad" class="tab-input">
  <input type="radio" name="tabs" id="tab-anuncios" class="tab-input">

  <nav class="tabs-nav" role="tablist">
    <label for="tab-top10" role="tab">Top 10 de hoy</label>
    <label for="tab-fiabilidad" role="tab">Fichas técnicas</label>
    <label for="tab-anuncios" role="tab">Todos los anuncios</label>
  </nav>

  <section id="panel-top10" class="tab-panel">
    <h2 class="titulo-seccion">Top 10 de hoy</h2>
    <p class="subtitulo-seccion">Los anuncios con mejor puntuación combinando precio frente al mercado, kilometraje, año, motor/cambio recomendado, garantía e historial de mantenimiento.</p>
    {top10}
  </section>

  <section id="panel-fiabilidad" class="tab-panel">
    <h2 class="titulo-seccion">Fichas técnicas por modelo</h2>
    <p class="subtitulo-seccion">Resumen del research de fiabilidad y de los filtros aplicados a cada modelo antes de puntuar los anuncios. Haz click en una ficha para ver el detalle completo con fotos y fuentes.</p>
    <div class="fichas-grid">{fichas_resumen}</div>
  </section>

  <section id="panel-anuncios" class="tab-panel">
    <h2 class="titulo-seccion">Todos los anuncios</h2>
    <div class="barra-filtros">
      <label>Modelo
        <select id="filtro-modelo">
          <option value="todos">Todos los modelos</option>
          {opciones_modelo}
        </select>
      </label>
      <label>Ordenar por
        <select id="filtro-orden">
          <option value="puntuacion">Puntuación</option>
          <option value="precio_asc">Precio: menor a mayor</option>
          <option value="precio_desc">Precio: mayor a menor</option>
          <option value="km_asc">Kilometraje: menor a mayor</option>
        </select>
      </label>
      <span class="contador" id="contador-resultados"></span>
    </div>
    <div class="tarjetas" id="listado">{tarjetas_html}</div>
  </section>

</div>

{modales}

<script>{JS}</script>
</body>
</html>"""

    ruta_fecha = OUTPUT_DIR / f"informe_{hoy}.html"
    ruta_fecha.write_text(documento, encoding="utf-8")
    ruta_ultimo = OUTPUT_DIR / "ultimo_informe.html"
    ruta_ultimo.write_text(documento, encoding="utf-8")
    return ruta_fecha
