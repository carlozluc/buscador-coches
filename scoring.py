"""
Motor de puntuacion 1-5 (Paso 6 del plan).

Pesos (sobre 100 puntos, luego normalizados a 1-5):
- Precio vs mercado del modelo              30
- Kilometraje dentro del rango bueno         20
- Anio dentro del rango bueno                20
- Motor/cambio recomendado                   10
- Garantia ofrecida                          10
- Historial de mantenimiento (palabras clave) 7
- Tipo de vendedor + antiguedad del anuncio   3

Un anuncio sin dato en un criterio no se penaliza por ese criterio (no suma, no resta),
salvo el precio: sin precio, el anuncio no puede puntuarse de forma fiable y se penaliza.

`puntuar()` devuelve la nota final, el desglose, y una clasificacion de cada criterio en
"pro" o "contra" (segun si obtuvo >=60% o <=30% de su maximo) para poder explicar de forma
legible por que un anuncio puntua como puntua (Top 10 y tarjetas individuales).
"""
from __future__ import annotations

from statistics import median
from typing import Any

from sites.base import contiene_palabras_clave

# (criterio, puntos_maximos) — se usa para decidir si un resultado es "pro" o "contra".
MAXIMOS = {
    "precio": 30.0,
    "km": 20.0,
    "anio": 20.0,
    "motor_cambio": 10.0,
    "garantia": 10.0,
    "historial": 7.0,
    "vendedor": 3.0,
}


def _puntua_precio(listing: Any, precios_comparables: list[float]) -> tuple[float, str]:
    if listing.precio is None:
        return 0.0, "sin precio, no se pudo valorar"
    if len(precios_comparables) < 3:
        return 15.0, "sin suficientes anuncios comparables hoy para valorar el precio"
    precio_medio = median(precios_comparables)
    if precio_medio <= 0:
        return 15.0, ""
    diferencia = (precio_medio - listing.precio) / precio_medio
    diferencia_clamp = max(-0.5, min(0.5, diferencia))
    puntos = 15.0 + diferencia_clamp * 30.0
    if diferencia >= 0.08:
        motivo = f"precio un {diferencia*100:.0f}% por debajo de la mediana del mercado ({precio_medio:,.0f} €)".replace(",", ".")
    elif diferencia <= -0.08:
        motivo = f"precio un {abs(diferencia)*100:.0f}% por encima de la mediana del mercado ({precio_medio:,.0f} €)".replace(",", ".")
    else:
        motivo = "precio en línea con la mediana del mercado"
    return puntos, motivo


def _puntua_km(listing: Any, km_max_modelo: int) -> tuple[float, str]:
    if listing.km is None:
        return 0.0, "sin dato de kilometraje"
    if listing.km <= km_max_modelo * 0.5:
        return 20.0, "kilometraje muy bajo para el modelo"
    if listing.km <= km_max_modelo:
        proporcion = (km_max_modelo - listing.km) / (km_max_modelo * 0.5)
        return max(5.0, 20.0 * proporcion), "kilometraje dentro del rango recomendado"
    return 0.0, f"kilometraje por encima del tope recomendado para el modelo ({km_max_modelo:,} km)".replace(",", ".")


def _puntua_anio(listing: Any, anio_min: int, anio_preferente_desde: int, anios_evitar: list[int]) -> tuple[float, str]:
    if listing.anio is None:
        return 0.0, "sin dato de año"
    if listing.anio in (anios_evitar or []):
        return 0.0, f"año {listing.anio}, está en la lista de años a evitar para este modelo"
    if listing.anio >= anio_preferente_desde:
        return 20.0, f"año {listing.anio}, dentro del rango preferente ({anio_preferente_desde}+)"
    if listing.anio >= anio_min:
        return 10.0, f"año {listing.anio}, aceptable pero anterior al rango preferente"
    return 3.0, f"año {listing.anio}, por debajo del mínimo recomendado para el modelo"


def _puntua_motor_cambio(listing: Any, cambio_preferente: list[str], motor_evitar: list[str]) -> tuple[float, str]:
    puntos = 5.0
    motivo = "sin dato de cambio para valorar"
    if listing.cambio and cambio_preferente:
        if any(pref.replace("_", "") in (listing.cambio or "").replace("_", "") for pref in cambio_preferente):
            puntos += 5.0
            motivo = f"cambio {listing.cambio}, el recomendado para este modelo"
        else:
            motivo = f"cambio {listing.cambio}, no es el preferente para este modelo"
    texto = (listing.texto_anuncio or "").lower()
    if motor_evitar and any(m.lower() in texto for m in motor_evitar):
        puntos = max(0.0, puntos - 5.0)
        motivo = "motor/variante señalado para evitar en el research de fiabilidad"
    return min(10.0, puntos), motivo


def _puntua_garantia(listing: Any) -> tuple[float, str]:
    if not listing.garantia_meses:
        return 0.0, "sin garantía especificada en el anuncio"
    if listing.garantia_meses >= 24:
        return 10.0, f"garantía de {listing.garantia_meses} meses"
    if listing.garantia_meses >= 12:
        return 7.0, f"garantía de {listing.garantia_meses} meses"
    return 4.0, f"garantía corta, de {listing.garantia_meses} meses"


def _puntua_historial(listing: Any, palabras_clave: list[str]) -> tuple[float, str]:
    encontradas = contiene_palabras_clave(listing.texto_anuncio, palabras_clave)
    if not encontradas:
        return 0.0, ""  # no se penaliza visiblemente: casi ningun anuncio trae este texto, no es informativo
    return min(7.0, 2.5 * len(encontradas)), "el anuncio menciona " + ", ".join(encontradas[:2])


def _puntua_vendedor(listing: Any) -> tuple[float, str]:
    if listing.vendedor_tipo == "profesional":
        return 3.0, "vendedor profesional"
    if listing.vendedor_tipo == "particular":
        return 1.0, "vendedor particular"
    return 0.0, ""


def puntuar(
    listing: Any,
    parametros_modelo: dict,
    parametros_generales: dict,
    precios_comparables: list[float],
) -> dict:
    """Devuelve {"nota", "desglose", "pros": [str,...], "contras": [str,...]}."""
    precio_pts, precio_motivo = _puntua_precio(listing, precios_comparables)
    km_pts, km_motivo = _puntua_km(
        listing, parametros_modelo.get("km_max", parametros_generales.get("km_max_generico", 120000))
    )
    anio_pts, anio_motivo = _puntua_anio(
        listing,
        parametros_modelo.get("anio_min", 2000),
        parametros_modelo.get("anio_preferente_desde", parametros_modelo.get("anio_min", 2000)),
        parametros_modelo.get("anios_evitar", []),
    )
    motor_pts, motor_motivo = _puntua_motor_cambio(
        listing, parametros_modelo.get("cambio_preferente", []), parametros_modelo.get("motor_evitar", [])
    )
    garantia_pts, garantia_motivo = _puntua_garantia(listing)
    historial_pts, historial_motivo = _puntua_historial(
        listing, parametros_generales.get("palabras_clave_historial_positivas", [])
    )
    vendedor_pts, vendedor_motivo = _puntua_vendedor(listing)

    desglose = {
        "precio": round(precio_pts, 1),
        "km": round(km_pts, 1),
        "anio": round(anio_pts, 1),
        "motor_cambio": round(motor_pts, 1),
        "garantia": round(garantia_pts, 1),
        "historial": round(historial_pts, 1),
        "vendedor": round(vendedor_pts, 1),
    }
    motivos = {
        "precio": precio_motivo,
        "km": km_motivo,
        "anio": anio_motivo,
        "motor_cambio": motor_motivo,
        "garantia": garantia_motivo,
        "historial": historial_motivo,
        "vendedor": vendedor_motivo,
    }

    total = sum(desglose.values())
    nota = round(1.0 + (max(0.0, min(100.0, total)) / 100.0) * 4.0, 2)

    pros: list[str] = []
    contras: list[str] = []
    for criterio, puntos in desglose.items():
        maximo = MAXIMOS[criterio]
        motivo = motivos[criterio]
        if not motivo:
            continue
        if puntos >= maximo * 0.6:
            pros.append(motivo)
        elif puntos <= maximo * 0.3:
            contras.append(motivo)

    return {"nota": nota, "desglose": desglose, "pros": pros, "contras": contras}


def calcular_puntuacion(listing: Any, parametros_modelo: dict, parametros_generales: dict, precios_comparables: list[float]) -> float:
    """Compatibilidad: devuelve solo la nota final."""
    return puntuar(listing, parametros_modelo, parametros_generales, precios_comparables)["nota"]
