"""
Simulacion de financiacion a 6 anios (72 meses) por anuncio (Paso 7 del plan).

Tres escenarios:
1. oferta_vendedor: cuota que el propio anuncio indica (si la trae), sin mas calculo.
2. mercado_medio: TAE ~8.5%, entrada 20%, sistema de amortizacion frances a 72 meses.
3. prestamo_familiar: interes 3% anual, sin entrada, sistema de amortizacion frances a
   72 meses (la cuota SI cubre capital + intereses cada mes; al acabar el plazo el
   prestamo queda liquidado, no queda capital pendiente).

Los supuestos de "mercado medio" son una referencia documentada aqui, no una oferta real;
se pueden ajustar cambiando las constantes de abajo.
"""
from __future__ import annotations

MESES = 72
TAE_MERCADO_MEDIO = 0.085
ENTRADA_MERCADO_MEDIO_PCT = 0.20
INTERES_PRESTAMO_FAMILIAR = 0.03


def _cuota_frances(principal: float, tae_anual: float, meses: int) -> float:
    i = tae_anual / 12
    if i == 0:
        return principal / meses
    return principal * (i * (1 + i) ** meses) / ((1 + i) ** meses - 1)


def simular(precio: float | None, cuota_vendedor: float | None) -> dict:
    if precio is None:
        return {
            "oferta_vendedor": None,
            "mercado_medio": None,
            "prestamo_familiar": None,
        }

    entrada = precio * ENTRADA_MERCADO_MEDIO_PCT
    principal_mercado = precio - entrada
    cuota_mercado = round(_cuota_frances(principal_mercado, TAE_MERCADO_MEDIO, MESES), 2)

    cuota_familiar = round(_cuota_frances(precio, INTERES_PRESTAMO_FAMILIAR, MESES), 2)

    return {
        "oferta_vendedor": {
            "cuota_mensual": cuota_vendedor,
            "meses": MESES,
            "nota": "Tal como la indica el anuncio" if cuota_vendedor else "No especificada en el anuncio",
        },
        "mercado_medio": {
            "cuota_mensual": cuota_mercado,
            "entrada": round(entrada, 2),
            "meses": MESES,
            "tae": TAE_MERCADO_MEDIO,
            "nota": f"Supuesto: TAE {TAE_MERCADO_MEDIO*100:.1f}%, entrada {ENTRADA_MERCADO_MEDIO_PCT*100:.0f}%",
        },
        "prestamo_familiar": {
            "cuota_mensual": cuota_familiar,
            "entrada": 0,
            "meses": MESES,
            "interes_anual": INTERES_PRESTAMO_FAMILIAR,
            "capital_pendiente_al_final": 0,
            "nota": f"Supuesto: interés {INTERES_PRESTAMO_FAMILIAR*100:.0f}% anual, sin entrada, cuota fija que amortiza capital e intereses a 72 meses (queda liquidado)",
        },
    }
