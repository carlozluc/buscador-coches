"""
Orquestador diario (Paso 5 / Paso 9 del plan).

Flujo: scrapea las 5 (de momento 4) webs configuradas para cada uno de los modelos
finalistas -> filtra -> puntua -> guarda en SQLite (historico/dedupe) -> genera el
informe HTML del dia.

Uso:
    py -3 run_daily.py
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from db import storage
from filtros import pasa_filtros
from scoring import puntuar
from sites import SCRAPERS

BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR / "config"
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "run_daily.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("run_daily")


def cargar_json(nombre: str) -> dict:
    with open(CONFIG_DIR / nombre, encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parametros_generales = cargar_json("parametros_generales.json")
    parametros_modelos = cargar_json("parametros_modelos.json")["modelos"]

    conn = storage.conectar()
    resumen_ejecucion = []

    for modelo in parametros_modelos:
        modelo_id = modelo["id"]
        marca = modelo["marca"]
        modelos_busqueda = modelo["modelos_busqueda"]

        logger.info("=== %s (%s) ===", modelo["nombre"], modelo_id)

        listings_brutos = []
        for web_id, buscar_fn in SCRAPERS.items():
            try:
                encontrados = buscar_fn(marca, modelos_busqueda, modelo_id)
                storage.registrar_ejecucion(
                    conn, web_id, modelo_id,
                    "ok" if encontrados else "sin_resultados",
                    len(encontrados),
                )
                logger.info("  %s: %d anuncios brutos", web_id, len(encontrados))
                listings_brutos.extend(encontrados)
            except Exception as e:  # noqa: BLE001 - un fallo en una web no debe tumbar el resto
                logger.exception("  %s: error buscando %s", web_id, modelo_id)
                storage.registrar_ejecucion(conn, web_id, modelo_id, "error", 0, str(e))

        # Filtra antes de puntuar
        listings_validos = []
        for listing in listings_brutos:
            ok, motivo = pasa_filtros(listing, modelo, parametros_generales)
            if ok:
                listings_validos.append(listing)
            else:
                logger.debug("  descartado (%s): %s", motivo, listing.url)

        precios_comparables = [l.precio for l in listings_validos if l.precio is not None]

        urls_vistas_hoy = set()
        for listing in listings_validos:
            resultado = puntuar(listing, modelo, parametros_generales, precios_comparables)
            storage.guardar_anuncio(conn, listing, resultado)
            urls_vistas_hoy.add(listing.url)

        storage.marcar_inactivos_no_vistos(conn, urls_vistas_hoy, modelo_id)

        logger.info("  -> %d anuncios validos tras filtros", len(listings_validos))
        resumen_ejecucion.append(
            {"modelo_id": modelo_id, "nombre": modelo["nombre"], "brutos": len(listings_brutos), "validos": len(listings_validos)}
        )

    conn.close()

    logger.info("Resumen: %s", json.dumps(resumen_ejecucion, ensure_ascii=False))

    from report.generate_report import generar_informe

    ruta_informe = generar_informe(parametros_modelos, parametros_generales)
    logger.info("Informe generado: %s", ruta_informe)

    from report.export_data import generar_datos_app

    ruta_datos_app = generar_datos_app(parametros_modelos, parametros_generales)
    logger.info("Datos de la app generados: %s", ruta_datos_app)

    from email_sender import enviar_informe

    enviar_informe(ruta_informe)


if __name__ == "__main__":
    main()
