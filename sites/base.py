"""Tipos y utilidades comunes para todos los scrapers de sitios."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9",
}

# Pausa entre peticiones al mismo sitio, en segundos. Scraping respetuoso: 1 ejecucion/dia con pausas.
PAUSA_ENTRE_PETICIONES = 2.0


@dataclass
class Listing:
    """Un anuncio normalizado, independientemente de la web de origen."""

    web_id: str
    modelo_id: str
    titulo: str
    marca: str
    modelo: str
    version: str
    anio: Optional[int]
    km: Optional[int]
    precio: Optional[float]
    combustible: Optional[str]
    cambio: Optional[str]
    etiqueta: Optional[str]
    url: str
    foto_url: Optional[str]
    vendedor_tipo: Optional[str] = None  # "profesional" | "particular" | None
    garantia_meses: Optional[int] = None
    cuota_financiacion_vendedor: Optional[float] = None
    texto_anuncio: str = ""
    ubicacion: Optional[str] = None
    extra: dict = field(default_factory=dict)


def parse_precio(texto: str) -> Optional[float]:
    """'25.550€' / '25.550 €' / '25550' -> 25550.0"""
    if not texto:
        return None
    limpio = re.sub(r"[^\d,.]", "", texto)
    limpio = limpio.replace(".", "").replace(",", ".")
    try:
        return float(limpio)
    except ValueError:
        return None


def parse_km(texto: str) -> Optional[int]:
    """'83.331km' / '83.331 km' -> 83331"""
    if not texto:
        return None
    limpio = re.sub(r"[^\d]", "", texto)
    try:
        return int(limpio) if limpio else None
    except ValueError:
        return None


def parse_anio(texto: str) -> Optional[int]:
    """'4/2022' / '2022' -> 2022"""
    if not texto:
        return None
    m = re.search(r"(19|20)\d{2}", texto)
    return int(m.group(0)) if m else None


def normaliza_combustible(texto: str) -> Optional[str]:
    if not texto:
        return None
    t = texto.lower()
    if "hibrido" in t or "híbrido" in t:
        if "enchuf" in t or "phev" in t:
            return "hibrido_enchufable"
        return "hibrido_no_enchufable"
    if "gasolina" in t:
        return "gasolina"
    if "diesel" in t or "diésel" in t:
        return "diesel"
    if "electrico" in t or "eléctrico" in t:
        return "electrico"
    return texto


def normaliza_cambio(texto: str) -> Optional[str]:
    if not texto:
        return None
    t = texto.lower()
    if "manual" in t:
        return "manual"
    if "autom" in t:
        return "automatico"
    return texto


def inferir_combustible(texto: str) -> Optional[str]:
    """Deduce el combustible a partir del texto del anuncio (version/titulo) cuando el
    scraper del sitio no lo ha podido extraer de un campo propio."""
    if not texto:
        return None
    t = texto.lower()
    if re.search(r"\b(tdi|hdi|cdi|dci|crdi|bluehdi|multijet)\b", t):
        return "diesel"
    if re.search(r"\b(phev|e-?hybrid|ehybrid)\b", t) and "mild" not in t:
        return "hibrido_enchufable"
    if re.search(r"\b(hev|hybrid|h[ií]brido|e-?boxer|boosterjet|mild.?hybrid)\b", t):
        return "hibrido_no_enchufable"
    if re.search(r"\b(tsi|tfsi|mpi|vti|gasolina|turbojet|puretech)\b", t):
        return "gasolina"
    return None


def contiene_palabras_clave(texto: str, palabras_clave: list[str]) -> list[str]:
    """Devuelve las palabras clave de historial de mantenimiento presentes en el texto del anuncio."""
    if not texto:
        return []
    t = texto.lower()
    return [p for p in palabras_clave if p.lower() in t]
