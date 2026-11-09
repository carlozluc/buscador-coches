"""Filtros de precio/km/anio/combustible aplicados antes de puntuar (Paso 1 + Paso 3)."""
from __future__ import annotations

from sites.base import Listing

COMBUSTIBLES_EXCLUIDOS = {"diesel", "electrico", "hibrido_enchufable"}  # el usuario pidio gasolina o hibrido no enchufable

# Webs donde la ubicacion del anuncio no se filtra por texto: ftomeocasion/canalcar/autofesa
# son concesionarios fisicos en Madrid (todo su stock esta ahi), y clicars es un vendedor
# online que entrega a domicilio en toda España (no muestra ubicacion fisica por anuncio).
WEBS_SIEMPRE_DENTRO_DE_UBICACION = {"ftomeocasion", "canalcar", "autofesa", "clicars"}


def pasa_filtros(listing: Listing, parametros_modelo: dict, parametros_generales: dict) -> tuple[bool, str]:
    if listing.precio is None:
        return False, "sin precio"
    precio_min = parametros_modelo.get("precio_min", parametros_generales["precio_min"])
    precio_max = parametros_modelo.get("precio_max", parametros_generales["precio_max"])
    if not (precio_min <= listing.precio <= precio_max):
        return False, f"precio fuera de rango ({listing.precio})"

    ubicacion_objetivo = (parametros_generales.get("ubicacion") or "").strip().lower()
    if ubicacion_objetivo and listing.web_id not in WEBS_SIEMPRE_DENTRO_DE_UBICACION:
        if not listing.ubicacion or ubicacion_objetivo not in listing.ubicacion.lower():
            return False, f"fuera de {parametros_generales.get('ubicacion')} (ubicacion anuncio: {listing.ubicacion})"

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
