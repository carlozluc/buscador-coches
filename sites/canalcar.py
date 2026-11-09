"""
Scraper de canalcar.es (concesionario de ocasion en Las Rozas, Madrid, desde 1964).
robots.txt sin restricciones para bots genericos (Paso 0).

Mecanismo: paginas de marca con URL fija `/coches-ocasion/{marca-slug}-segunda-mano-madrid`.
Todas las unidades de esa marca aparecen en una sola pagina (sin paginacion real observada
hasta 45 resultados; si una marca supera eso convendria revisar si aparece paginacion).
Filtramos por modelo nosotros mismos sobre el texto de cada ficha.
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

BASE_URL = "https://www.canalcar.es"
WEB_ID = "canalcar"

# Canalcar usa "mercedes-benz" en vez de "mercedes" en su slug de marca.
SLUG_ESPECIALES = {
    "mercedes-benz": "mercedes-benz",
    "mercedes": "mercedes-benz",
}


def _slug_marca(marca: str) -> str:
    base = marca.lower().strip().replace(" ", "-")
    return SLUG_ESPECIALES.get(base, base)


def _parse_card(article) -> Listing | None:
    link = article.select_one(".vehicle__title a[href]") or article.select_one("a.vehicle-link[href]")
    if not link:
        return None
    href = link.get("href", "")
    url = BASE_URL + href if href.startswith("/") else href
    titulo_completo = link.get("title", "").strip()

    modelo_el = article.select_one(".vehicle__model")
    version_el = article.select_one(".vehicle__version")
    modelo_txt = modelo_el.get_text(" ", strip=True) if modelo_el else ""
    version_txt = version_el.get_text(" ", strip=True) if version_el else ""

    partes = modelo_txt.split(" ", 1)
    marca = partes[0] if partes else ""
    modelo = partes[1] if len(partes) > 1 else ""

    specs = [li.get_text(strip=True) for li in article.select(".vehicle__specs.vehicle__features li")]
    anio = km = combustible = cambio = None
    for s in specs:
        if re.match(r"^(19|20)\d{2}$", s):
            anio = parse_anio(s)
        elif "km" in s.lower():
            km = parse_km(s)
        elif s.lower() in ("manual",) or "manual" in s.lower() or "autom" in s.lower():
            cambio = normaliza_cambio(s)
        elif s:
            combustible = normaliza_combustible(s)
    if not combustible:
        combustible = inferir_combustible(titulo_completo + " " + version_txt)

    precio_el = article.select_one(".vehicle__price")
    precio = None
    if precio_el:
        data_precio = precio_el.get("data-precio")
        if data_precio:
            try:
                precio = float(data_precio)
            except ValueError:
                precio = parse_precio(data_precio)
        else:
            precio = parse_precio(precio_el.get_text())

    cuota_el = article.select_one(".vehicle__quota")
    cuota = parse_precio(cuota_el.get_text()) if cuota_el else None

    foto_el = article.select_one("img.vehicle-photo")
    foto_url = foto_el.get("src") if foto_el else None

    ubic_el = article.select_one(".vehicle__specs-location li")
    ubicacion = ubic_el.get_text(strip=True) if ubic_el else None

    return Listing(
        web_id=WEB_ID,
        modelo_id="",  # se rellena en buscar()
        titulo=titulo_completo or modelo_txt,
        marca=marca,
        modelo=modelo,
        version=version_txt,
        anio=anio,
        km=km,
        precio=precio,
        combustible=combustible,
        cambio=cambio,
        etiqueta=None,  # canalcar no muestra distintivo DGT en la tarjeta de listado
        url=url,
        foto_url=foto_url,
        vendedor_tipo="profesional",
        garantia_meses=None,
        cuota_financiacion_vendedor=cuota,
        texto_anuncio=titulo_completo + " " + version_txt,
        ubicacion=ubicacion,
    )


def buscar(marca: str, modelos_busqueda: list[str], modelo_id: str) -> list[Listing]:
    slug = _slug_marca(marca)
    url = f"{BASE_URL}/coches-ocasion/{slug}-segunda-mano-madrid"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 404:
            logger.info("canalcar: sin pagina de marca para '%s' (%s)", marca, url)
            return []
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning("canalcar: fallo cargando %s (%s)", url, e)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # Evita contar la seccion "coches similares / que pueden interesarte" del final de la pagina.
    similares = soup.find(id="coches-similares")
    if similares:
        similares.decompose()

    resultados: list[Listing] = []
    terminos = [t.lower() for t in modelos_busqueda]
    for article in soup.select("article.vehicle"):
        listing = _parse_card(article)
        if not listing:
            continue
        if any(t in listing.modelo.lower() or t in listing.titulo.lower() for t in terminos):
            listing.modelo_id = modelo_id
            resultados.append(listing)

    return resultados
