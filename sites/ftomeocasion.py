"""
Scraper de ftomeocasion.com (concesionario oficial Audi/Skoda/Volkswagen en Madrid,
tambien con stock de otras marcas de ocasion: BMW, Honda, Hyundai, Mazda, Mercedes,
MINI, Seat, Toyota, Volvo). robots.txt sin restricciones (Paso 0).

Mecanismo: la pagina de resultados usa query params numericos (marca=ID, modelo=ID...)
cuyos IDs se leen de los <select> renderizados en el propio HTML (no son fijos / pueden
cambiar), asi que los resolvemos en caliente contra la pagina de busqueda sin filtrar.
El precio/km/anio se filtran en nuestro propio codigo (ver aplica_filtros) en vez de usar
los desplegables de precio/km del sitio, que solo ofrecen valores preestablecidos.

LIMITACION CONOCIDA: no se encontro paginacion visible con pocos resultados; si un modelo
concreto supera una pagina de resultados en este sitio, habria que revisar si usan
"cargar mas" por AJAX y anadir soporte aqui.
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

BASE_URL = "https://www.ftomeocasion.com"
SEARCH_PATH = "/coches-de-ocasion"
WEB_ID = "ftomeocasion"


def _parse_opciones(soup: BeautifulSoup, select_name: str) -> dict[str, str]:
    """Lee <input type="hidden" name="X"> seguido de <ul><li><span data-value="ID">Nombre</span>.
    Devuelve {nombre_normalizado_minuscula: id}."""
    opciones: dict[str, str] = {}
    hidden = soup.find("input", attrs={"name": select_name})
    if not hidden:
        return opciones
    dropdown = hidden.find_parent("div", class_="dropdown")
    if not dropdown:
        return opciones
    for li in dropdown.select("ul.dropdown-menu li span[data-value]"):
        valor = li.get("data-value", "").strip()
        nombre = li.get_text(strip=True)
        if valor and valor != "-1" and nombre:
            opciones[nombre.lower()] = valor
    return opciones


def _obtener_marcas(session: requests.Session) -> dict[str, str]:
    resp = session.get(f"{BASE_URL}{SEARCH_PATH}", headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    return _parse_opciones(soup, "marca")


def _obtener_modelos(session: requests.Session, marca_id: str) -> dict[str, str]:
    resp = session.post(
        f"{BASE_URL}/frontend/ajax/ModelosByAdType/coche/{marca_id}/filtro_listado_modal/modelos_drop",
        headers=HEADERS,
        timeout=20,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    opciones: dict[str, str] = {}
    for li in soup.select("li span[data-value]"):
        valor = li.get("data-value", "").strip()
        nombre = li.get_text(strip=True)
        if valor and valor != "-1" and nombre:
            opciones[nombre.lower()] = valor
    return opciones


_RE_FOTO = re.compile(r'\["large"\]\s*(?:=>|=&gt;)\s*string\(\d+\)\s*"([^"]*)"')
_RE_FOTO_ORIG = re.compile(r'\["original"\]\s*(?:=>|=&gt;)\s*string\(\d+\)\s*"([^"]*)"')


def _extraer_foto(card) -> str | None:
    """La propia pagina incrusta un volcado de depuracion con las URLs de fotos reales
    (campo 'fotos_capas[].urls'); preferimos 'original' (maxima resolucion) y si no esta
    disponible caemos a 'large'."""
    texto = str(card)
    m = _RE_FOTO_ORIG.search(texto) or _RE_FOTO.search(texto)
    return m.group(1) if m and m.group(1) else None


def _parse_card(card, modelo_id: str) -> Listing | None:
    link = card.select_one("a[href^='/coches-de-ocasion/']")
    if not link:
        return None
    href = link.get("href", "")
    url = BASE_URL + href

    titulo_el = card.select_one(".titulo, h2, h3")
    version_el = card.select_one(".version-complemento")
    titulo = titulo_el.get_text(" ", strip=True) if titulo_el else link.get("title", "")
    version = version_el.get_text(" ", strip=True) if version_el else ""

    precio_el = card.select_one(".precio")
    precio = parse_precio(precio_el.get_text()) if precio_el else None

    cuota_el = card.select_one(".precio-cuota")
    cuota = parse_precio(cuota_el.get_text()) if cuota_el else None

    etiqueta_el = card.select_one(".distintivo img, .imagenAmbiental")
    etiqueta = etiqueta_el.get("alt") if etiqueta_el else None

    detalles = [d.get_text(strip=True) for d in card.select(".detalles .flex div:not(:has(img))")]
    # orden observado: [fecha(mm/aaaa), km, cambio, combustible]
    anio = km = cambio = combustible = None
    for d in detalles:
        if re.match(r"^\d{1,2}/\d{4}$|^\d{4}$", d):
            anio = parse_anio(d)
        elif "km" in d.lower():
            km = parse_km(d)
        elif d.lower() in ("automático", "manual") or "manual" in d.lower() or "autom" in d.lower():
            cambio = normaliza_cambio(d)
        elif d:
            combustible = normaliza_combustible(d)
    if not combustible:
        combustible = inferir_combustible(titulo + " " + version)

    # marca/modelo a partir del propio titulo (ej. "Mercedes Clase A 180 Sedan...")
    partes = titulo.split(" ", 2)
    marca = partes[0] if partes else ""
    modelo = partes[1] if len(partes) > 1 else ""

    return Listing(
        web_id=WEB_ID,
        modelo_id=modelo_id,
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
        foto_url=_extraer_foto(card),
        vendedor_tipo="profesional",
        garantia_meses=12,  # concesionario oficial, garantia minima habitual; afinar si el anuncio la especifica
        cuota_financiacion_vendedor=cuota,
        texto_anuncio=titulo + " " + version,
    )


def buscar(marca: str, modelos_busqueda: list[str], modelo_id: str) -> list[Listing]:
    """Busca anuncios de `marca` cuyo modelo coincida con alguno de `modelos_busqueda`."""
    session = requests.Session()
    try:
        marcas = _obtener_marcas(session)
    except requests.RequestException as e:
        logger.warning("ftomeocasion: no se pudo cargar la lista de marcas (%s)", e)
        return []

    marca_id = marcas.get(marca.lower())
    if not marca_id:
        logger.info("ftomeocasion: la marca '%s' no esta en su catalogo, se omite", marca)
        return []

    try:
        modelos = _obtener_modelos(session, marca_id)
    except requests.RequestException as e:
        logger.warning("ftomeocasion: no se pudo cargar modelos de %s (%s)", marca, e)
        return []

    resultados: list[Listing] = []
    for termino in modelos_busqueda:
        modelo_match_id = next(
            (mid for nombre, mid in modelos.items() if termino.lower() in nombre), None
        )
        if not modelo_match_id:
            continue
        try:
            resp = session.get(
                f"{BASE_URL}{SEARCH_PATH}",
                params={"marca": marca_id, "modelo": modelo_match_id},
                headers=HEADERS,
                timeout=20,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning("ftomeocasion: fallo buscando %s %s (%s)", marca, termino, e)
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        for card_wrapper in soup.select(".col_card"):
            card = card_wrapper.select_one("a[href^='/coches-de-ocasion/']")
            if not card:
                continue
            listing = _parse_card(card_wrapper, modelo_id)
            if listing:
                resultados.append(listing)

    return resultados
