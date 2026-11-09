"""
Scraper de autofesa.com (concesionario de ocasion en Madrid). robots.txt solo
restringe /admin/, /feed/ y /goal/ para bots genericos: sin restriccion sobre
listados o fichas de vehiculo.

Mecanismo: paginas de marca+modelo con URL fija `/coches-segunda-mano/{marca-slug}/{modelo-slug}`,
servidas ya renderizadas en el HTML (sin JS). Paginacion por `?page=N` (30 resultados/pagina).
Si el modelo no tiene stock actualmente el sitio devuelve 404 (no una pagina vacia).
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

BASE_URL = "https://www.autofesa.com"
WEB_ID = "autofesa"
MAX_PAGINAS = 5

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
    link = card.select_one("a[href*='/coches-de-ocasion/']")
    if not link:
        return None
    url = link.get("href", "")

    make_el = card.select_one(".vehicle-card__title .make")
    model_el = card.select_one(".vehicle-card__title .model")
    version_el = card.select_one(".vehicle-card__title .version")
    marca = make_el.get_text(strip=True) if make_el else ""
    modelo = model_el.get_text(strip=True) if model_el else ""
    version = version_el.get_text(strip=True) if version_el else ""
    if modelo and version.lower().startswith(modelo.lower()):
        version = version[len(modelo):].strip()
    titulo = f"{marca} {modelo} {version}".strip()

    items = [li.get_text(" ", strip=True) for li in card.select(".vehicle-card__features .list .item")]
    anio = km = cambio = combustible = None
    for it in items:
        if re.match(r"^(19|20)\d{2}$", it):
            anio = parse_anio(it)
        elif "km" in it.lower():
            km = parse_km(it)
        elif "manual" in it.lower() or "autom" in it.lower():
            cambio = normaliza_cambio(it)
        elif it.lower() in ("gasolina", "diesel", "diésel", "hibrido", "híbrido", "eléctrico", "electrico"):
            combustible = normaliza_combustible(it)
    combustible_titulo = inferir_combustible(titulo)
    if not combustible:
        combustible = combustible_titulo
    elif combustible == "hibrido_no_enchufable" and combustible_titulo == "hibrido_enchufable":
        # La etiqueta "Hibrido" generica de autofesa no distingue enchufable/no enchufable;
        # si el titulo lo deja claro (p.ej. "TFSIe"), ese dato es mas fiable.
        combustible = combustible_titulo

    precio_el = card.select_one(".vehicle-card__price .current span")
    precio = parse_precio(precio_el.get_text()) if precio_el else None

    cuota_el = card.select_one(".vehicle-card__footer .quota")
    cuota = parse_precio(cuota_el.get_text()) if cuota_el else None

    etiqueta_el = card.select_one("img.eco-label")
    etiqueta = etiqueta_el.get("alt", "").replace("Etiqueta ", "") if etiqueta_el else None

    tiene_libro = card.select_one(".vehicle-card-tags__tag--service-book") is not None
    if tiene_libro:
        titulo_extra = "libro de revisiones"
    else:
        titulo_extra = ""

    foto_el = card.select_one(".vehicle-card__slider img")
    foto_url = foto_el.get("src") if foto_el else None

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
        garantia_meses=12,
        cuota_financiacion_vendedor=cuota,
        texto_anuncio=(titulo + " " + titulo_extra).strip(),
    )


def _buscar_termino(marca: str, marca_slug: str, termino: str, modelo_id: str) -> list[Listing]:
    modelo_slug = _slug(termino)
    resultados: list[Listing] = []
    for pagina in range(1, MAX_PAGINAS + 1):
        url = f"{BASE_URL}/coches-segunda-mano/{marca_slug}/{modelo_slug}"
        if pagina > 1:
            url += f"?page={pagina}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 404:
                break
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning("autofesa: fallo buscando %s %s pagina %d (%s)", marca, termino, pagina, e)
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.vehicle-card")
        if not cards:
            break
        for card in cards:
            listing = _parse_card(card)
            if listing:
                listing.modelo_id = modelo_id
                resultados.append(listing)
        if len(cards) < 30:
            break

    return resultados


def buscar(marca: str, modelos_busqueda: list[str], modelo_id: str) -> list[Listing]:
    marca_slug = _slug_marca(marca)
    resultados: list[Listing] = []
    for termino in modelos_busqueda:
        resultados.extend(_buscar_termino(marca, marca_slug, termino, modelo_id))
    return resultados
