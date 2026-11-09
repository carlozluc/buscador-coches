"""
Scraper de ocasionplus.com (compraventa propia de coches de ocasion, no concesionario
tercero). robots.txt no restringe las paginas de marca/modelo con ruta limpia
(`/coches-segunda-mano/{marca}/{modelo}`); solo bloquea parametros de filtro en query
string (marca=, modelo=, sort=, etc.) y rutas internas como /*/search, que no usamos.

Mecanismo: la pagina es una SPA Next.js pero viene completamente renderizada en el HTML
(SSR), asi que requests+BeautifulSoup basta, sin Playwright. No se observo paginacion
real en estas paginas de modelo (tope ~20 resultados); suficiente para modelos nicho.
"""
from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

from .base import (
    HEADERS,
    Listing,
    inferir_combustible,
    normaliza_cambio,
    normaliza_combustible,
    parse_anio,
    parse_km,
    parse_precio,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://www.ocasionplus.com"
WEB_ID = "ocasionplus"

SLUG_MARCA_ESPECIALES = {
    "mercedes": "mercedes-benz",
    "mercedes-benz": "mercedes-benz",
}


def _slug(texto: str) -> str:
    return texto.lower().strip().replace(" ", "-")


def _slug_marca(marca: str) -> str:
    base = _slug(marca)
    return SLUG_MARCA_ESPECIALES.get(base, base)


def _parse_card(card) -> Listing | None:
    link = card if card.name == "a" else card.select_one("a[href^='/coches-segunda-mano/']")
    if not link:
        return None
    href = link.get("href", "")
    url = BASE_URL + href if href.startswith("/") else href

    marca_modelo_el = card.select_one('[data-test="span-brand-model"]')
    if not marca_modelo_el:
        return None  # no es una tarjeta de vehiculo (enlace de navegacion/footer)
    version_el = card.select_one('[data-test="span-version"]')
    marca_modelo = marca_modelo_el.get_text(strip=True) if marca_modelo_el else ""
    version = version_el.get_text(strip=True) if version_el else ""
    partes = marca_modelo.split(" ", 1)
    marca = partes[0] if partes else ""
    modelo = partes[1] if len(partes) > 1 else ""
    titulo = f"{marca_modelo} {version}".strip()

    precio_el = card.select_one('[data-test="span-price"]')
    precio = parse_precio(precio_el.get_text()) if precio_el else None

    cuota_el = card.select_one('[data-test="span-finace-quote"]')
    cuota = parse_precio(cuota_el.get_text()) if cuota_el else None

    anio_el = card.select_one('[data-test="span-registration-date"]')
    anio = parse_anio(anio_el.get_text()) if anio_el else None

    km_el = card.select_one('[data-test="span-km"]')
    km = parse_km(km_el.get_text()) if km_el else None

    combustible_el = card.select_one('[data-test="span-fuel-type"]')
    combustible = normaliza_combustible(combustible_el.get_text(strip=True)) if combustible_el else None
    if not combustible:
        combustible = inferir_combustible(titulo)

    cambio_el = card.select_one('[data-test="span-engine-transmission"]')
    cambio = normaliza_cambio(cambio_el.get_text(strip=True)) if cambio_el else None

    etiqueta_el = card.select_one('img[alt="distintivo-ambiental"]')
    etiqueta = None
    if etiqueta_el:
        m = re.search(r"/icons/([A-Z0-9]+)\.svg", etiqueta_el.get("src", ""))
        etiqueta = m.group(1) if m else None

    ubicacion_el = card.select_one('[data-test="div-dealer"]')
    ubicacion = ubicacion_el.get_text(strip=True) if ubicacion_el else None

    garantia_el = card.select_one('[data-test="span-warranty"]')
    libro_el = card.select_one('[data-test="span-maintenance-book"]')
    extras = " ".join(e.get_text(strip=True) for e in (garantia_el, libro_el) if e)
    garantia_meses = 12 if garantia_el else None

    img_el = card.select_one(".cardVehicle-module-scss-module__w3hfpa__image img[alt]:not([alt='water-mark-car'])")
    foto_url = img_el.get("src") if img_el else None

    return Listing(
        web_id=WEB_ID,
        modelo_id="",
        titulo=titulo,
        marca=marca,
        modelo=modelo,
        version=version,
        anio=anio,
        km=km,
        precio=precio,
        combustible=combustible,
        cambio=cambio,
        etiqueta=etiqueta,
        url=url,
        foto_url=foto_url,
        vendedor_tipo="profesional",
        garantia_meses=garantia_meses,
        cuota_financiacion_vendedor=cuota,
        texto_anuncio=(titulo + " " + extras).strip(),
        ubicacion=ubicacion,
    )


def buscar(marca: str, modelos_busqueda: list[str], modelo_id: str) -> list[Listing]:
    marca_slug = _slug_marca(marca)
    resultados: list[Listing] = []
    for termino in modelos_busqueda:
        modelo_slug = _slug(termino)
        url = f"{BASE_URL}/coches-segunda-mano/{marca_slug}/{modelo_slug}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning("ocasionplus: fallo buscando %s %s (%s)", marca, termino, e)
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        for card in soup.select("a[href^='/coches-segunda-mano/']"):
            listing = _parse_card(card)
            if listing:
                listing.modelo_id = modelo_id
                resultados.append(listing)

    return resultados
