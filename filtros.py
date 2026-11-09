"""Filtros de precio/km/anio/combustible aplicados antes de puntuar (Paso 1 + Paso 3)."""
from __future__ import annotations

from sites.base import Listing

COMBUSTIBLES_EXCLUIDOS = {"diesel", "electrico"}  # el usuario pidio gasolina o hibrido no enchufable


def pasa_filtros(listing: Listing, parametros_modelo: dict, parametros_generales: dict) -> tuple[bool, str]:
    if listing.precio is None:
        return False, "sin precio"
    if not (parametros_generales["precio_min"] <= listing.precio <= parametros_generales["precio_max"]):
        return False, f"precio fuera de rango ({listing.precio})"

    if listing.combustible in COMBUSTIBLES_EXCLUIDOS:
        return False, f"combustible excluido ({listing.combustible})"

    km_max = parametros_modelo.get("km_max", parametros_generales.get("km_max_generico", 120000))
    if listing.km is not None and listing.km > km_max:
        return False, f"km por encima del maximo del modelo ({listing.km} > {km_max})"

    anio_min = parametros_modelo.get("anio_min")
    if anio_min and listing.anio is not None and listing.anio < anio_min:
        return False, f"anio por debajo del minimo del modelo ({listing.anio} < {anio_min})"

    anios_evitar = parametros_modelo.get("anios_evitar", [])
    if listing.anio in anios_evitar:
        return False, f"anio en lista de evitar ({listing.anio})"

    return True, "ok"
