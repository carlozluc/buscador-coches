"""
Scraper de coches.com. robots.txt abierto salvo /reserva, /contacto, /index.php (Paso 0).

Mecanismo: pagina `/coches-segunda-mano/{marca}-{modelo}.htm` con tarjetas renderizadas
server-side pero con clases CSS generadas (CSS modules, tipo "Box-module_box__Wgbf3")
que cambian entre despliegues de la web. En vez de depender de esas clases, extraemos
cada tarjeta por regex sobre una ventana de texto alrededor de cada enlace de ficha
("ocasion-...htm"), usando el aria-label del enlace (que da marca/modelo/version/
provincia de forma limpia) y patrones de precio/km/ano/combustible en el HTML circundante.
Es mas resistente a cambios de maquetacion que depender de nombres de clase exactos.
"""
from __future__ import annotations

import logging
import re

import requests

from .base import HEADERS, Listing, inferir_combustible, normaliza_cambio, normaliza_combustible, parse_precio

logger = logging.getLogger(__name__)

BASE_URL = "https://www.coches.com"
WEB_ID = "coches_com"

# Excepciones de slug de marca en coches.com (comprobadas contra la web real).
SLUG_MARCA_ESPECIALES = {
    "mercedes-benz": "mercedes-clase",
    "mercedes": "mercedes-clase",
}

VENTANA_CARD = 3600  # caracteres de HTML a examinar tras cada enlace de ficha


def _slug(marca: str, modelo_termino: str) -> str:
    marca_slug = marca.lower().strip().replace(" ", "-")
    marca_slug = SLUG_MARCA_ESPECIALES.get(marca_slug, marca_slug)
    modelo_slug = modelo_termino.lower().strip().replace(" ", "-")
    return f"{marca_slug}-{modelo_slug}"


FOTO_VENTANA_ATRAS = 3000


def _extraer_foto(html: str, href_idx: int) -> str | None:
    inicio = max(0, href_idx - FOTO_VENTANA_ATRAS)
    bloque = html[inicio:href_idx]
    matches = re.findall(r'src="(https://images\.coches\.com/[^"?]+)(?:\?[^"]*)?"', bloque)
    return matches[-1] if matches else None


def _parse_card(html: str, href_idx: int, href: str) -> Listing | None:
    ventana = html[href_idx : href_idx + VENTANA_CARD]
    foto_url = _extraer_foto(html, href_idx)

    aria_match = re.search(r'aria-label="([^"]+)"', html[max(0, href_idx - 200) : href_idx + 200])
    aria_label = aria_match.group(1) if aria_match else ""
    # formato observado: "SKODA-Kamiq-1.5 TSI Style-150-en-Madrid"
    partes = aria_label.split("-")
    marca = partes[0].title() if partes else ""

    km_match = re.search(r"([\d.]+)\s*km", ventana)
    anio_match = re.search(r">\s*((?:19|20)\d{2})\s*<", ventana)
    fuel_match = re.search(r">(Gasolina|Di[eé]sel|El[eé]ctrico|H[ií]brido[^<]*)<", ventana, re.I)
    provincia_match = re.search(r"en-([A-Za-z-]+)(?:\"|$)", aria_label)

    precio_match = re.search(r"Al contado.{0,400}?([\d.]+)\s*€", ventana, re.S)
    precio = parse_precio(precio_match.group(1)) if precio_match else None

    financ_match = re.search(r"Financiando.{0,400}?([\d.]+)\s*€", ventana, re.S)
    precio_financiado = parse_precio(financ_match.group(1)) if financ_match else None

    url = href if href.startswith("http") else BASE_URL + href

    if aria_label:
        titulo = aria_label.replace("-", " ").strip()
    else:
        # Sin aria-label: derivamos un titulo legible del slug de la URL en vez de mostrar la URL.
        slug = re.search(r"ocasion-([a-z0-9-]+)\.htm", href)
        titulo = slug.group(1).replace("-", " ").title() if slug else "Anuncio sin titulo"

    combustible = normaliza_combustible(fuel_match.group(1)) if fuel_match else None
    if not combustible:
        combustible = inferir_combustible(titulo)

    return Listing(
        web_id=WEB_ID,
        modelo_id="",
        titulo=titulo,
        marca=marca,
        modelo="",
        version="",
        anio=int(anio_match.group(1)) if anio_match else None,
        km=int(km_match.group(1).replace(".", "")) if km_match else None,
        precio=precio,
        combustible=combustible,
        cambio=normaliza_cambio(ventana) if re.search(r"\b(manual|autom[aá]tic[oa])\b", ventana, re.I) else None,
        etiqueta=None,
        url=url,
        foto_url=foto_url,
        vendedor_tipo=None,
        garantia_meses=None,
        cuota_financiacion_vendedor=precio_financiado,
        texto_anuncio=titulo,
        ubicacion=provincia_match.group(1).replace("-", " ") if provincia_match else None,
    )


def buscar(marca: str, modelos_busqueda: list[str], modelo_id: str) -> list[Listing]:
    resultados: list[Listing] = []
    vistos_urls: set[str] = set()

    for termino in modelos_busqueda:
        slug = _slug(marca, termino)
        url = f"{BASE_URL}/coches-segunda-mano/{slug}.htm"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=25)
            if resp.status_code == 404:
                logger.info("coches.com: sin pagina para '%s' (%s)", slug, url)
                continue
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning("coches.com: fallo cargando %s (%s)", url, e)
            continue

        html = resp.text
        for m in re.finditer(r'href="(https://www\.coches\.com/coches-segunda-mano/ocasion-[^"]+\.htm[^"]*)"', html):
            href = m.group(1)
            if href in vistos_urls:
                continue
            vistos_urls.add(href)
            listing = _parse_card(html, m.start(), href)
            if listing:
                listing.modelo_id = modelo_id
                listing.modelo = termino
                resultados.append(listing)

    return resultados
