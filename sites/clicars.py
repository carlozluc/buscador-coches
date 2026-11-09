"""
Scraper de clicars.com (cadena de superventas de ocasion). robots.txt abierto salvo
/completado, /test y /blog/wp-admin (Paso 0).

Es una SPA: el HTML servido sin JS no contiene los anuncios (confirmado en el Paso 5).
Se renderiza con Playwright/Chromium headless y se parsea el HTML ya hidratado.

Mecanismo de busqueda: paginas `/coches-segunda-mano-ocasion/{marca-slug}/{modelo-slug}`.
Cada tarjeta trae datos ricos en atributos data-* del bloque de precio (incluye oferta
web, cuota de financiacion y precio financiado: utiles tambien para el Paso 7).
"""
from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from .base import HEADERS, Listing, inferir_combustible, normaliza_cambio, parse_km, parse_precio

logger = logging.getLogger(__name__)

BASE_URL = "https://www.clicars.com"
WEB_ID = "clicars"

SLUG_MARCA_ESPECIALES = {
    "mercedes-benz": "mercedes-benz",
    "mercedes": "mercedes-benz",
}


def _slug(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")


def _render_html(url: str) -> str | None:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(user_agent=HEADERS["User-Agent"])
            page.goto(url, wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(2000)
            html = page.content()
            browser.close()
            return html
    except Exception as e:  # noqa: BLE001 - fallos de red/renderizado no deben tumbar el resto del scraper
        logger.warning("clicars: fallo renderizando %s (%s)", url, e)
        return None


def _parse_card(h2) -> Listing | None:
    """`h2` es ya el elemento <h2 class="maker"> (soup.select("h2.maker") lo devuelve directamente)."""
    strong = h2.select_one("strong")
    modelo_txt = strong.get_text(strip=True) if strong else ""
    version_el = h2.select_one(".version")
    info_el = h2.select_one(".info")
    version = version_el.get_text(strip=True) if version_el else ""
    info = info_el.get_text(" ", strip=True) if info_el else ""

    anio = km = cv = cambio = None
    piezas = [p.strip() for p in info.split("|")]
    for pieza in piezas:
        if re.match(r"^(19|20)\d{2}$", pieza):
            anio = int(pieza)
        elif "km" in pieza.lower():
            km = parse_km(pieza)
        elif "cv" in pieza.lower():
            cv = pieza
        elif pieza:
            cambio = normaliza_cambio(pieza) or cambio

    link = h2.find_parent("a", href=True) or h2.select_one("a[href]")
    url = None
    contenedor = h2
    for _ in range(4):
        contenedor = contenedor.parent
        if contenedor is None:
            break
        enlace = contenedor.find("a", href=re.compile(r"/coches-segunda-mano-ocasion/comprar-"))
        if enlace:
            url = enlace.get("href")
            break
    if not url and link:
        url = link.get("href")

    precio_div = None
    buscar_en = h2
    for _ in range(5):
        buscar_en = buscar_en.parent
        if buscar_en is None:
            break
        precio_div = buscar_en.select_one(".trigger-modal-price, [data-price-web-offer], [data-price-web]")
        if precio_div:
            break

    precio_web = precio_oferta = precio_financiado = cuota = None
    if precio_div:
        precio_web = parse_precio(precio_div.get("data-price-web"))
        precio_oferta = parse_precio(precio_div.get("data-price-web-offer")) or precio_web
        precio_financiado = parse_precio(precio_div.get("data-price-financing"))
        cuota = parse_precio(precio_div.get("data-price-quota"))

    partes = modelo_txt.split(" ", 1)
    marca = partes[0] if partes else ""
    modelo = partes[1] if len(partes) > 1 else ""
    titulo = f"{modelo_txt} {version}".strip()

    return Listing(
        web_id=WEB_ID,
        modelo_id="",
        titulo=titulo,
        marca=marca,
        modelo=modelo,
        version=version,
        anio=anio,
        km=km,
        precio=precio_oferta,
        combustible=inferir_combustible(titulo),  # no viene en un campo propio; se deduce del texto
        cambio=cambio,
        etiqueta=None,
        url=(BASE_URL + url) if url and url.startswith("/") else url,
        foto_url=None,
        vendedor_tipo="profesional",
        garantia_meses=None,
        cuota_financiacion_vendedor=cuota,
        texto_anuncio=f"{modelo_txt} {version} {cv or ''}",
        extra={"precio_web": precio_web, "precio_financiado_total": precio_financiado},
    )


def buscar(marca: str, modelos_busqueda: list[str], modelo_id: str) -> list[Listing]:
    marca_slug = SLUG_MARCA_ESPECIALES.get(_slug(marca), _slug(marca))
    resultados: list[Listing] = []

    for termino in modelos_busqueda:
        modelo_slug = _slug(termino)
        url = f"{BASE_URL}/coches-segunda-mano-ocasion/{marca_slug}/{modelo_slug}"
        html = _render_html(url)
        if not html:
            continue
        soup = BeautifulSoup(html, "lxml")
        tarjetas = soup.select("h2.maker")
        if not tarjetas:
            logger.info("clicars: 0 tarjetas para %s (%s)", url, "puede que la marca/modelo no este en catalogo")
            continue

        # Si la marca/modelo no existe en su catalogo, clicars.com puede redirigir a una
        # pagina generica con coches de otras marcas en vez de dar 404. Nos protegemos
        # comprobando que la marca del anuncio coincida con la buscada antes de aceptarlo.
        for h2 in tarjetas:
            listing = _parse_card(h2)
            if not listing:
                continue
            marca_obtenida = SLUG_MARCA_ESPECIALES.get(_slug(listing.marca), _slug(listing.marca))
            if marca_obtenida != marca_slug:
                continue
            listing.modelo_id = modelo_id
            resultados.append(listing)

        if tarjetas and not resultados:
            logger.info(
                "clicars: %s tarjetas encontradas en %s pero ninguna de la marca '%s' "
                "(probable redireccion a pagina generica, se descartan)",
                len(tarjetas), url, marca,
            )

    return resultados
