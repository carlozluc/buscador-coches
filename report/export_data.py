"""Genera webapp/data.json: los mismos datos del informe HTML, en JSON, para que la
PWA los pinte con JS real (sin las limitaciones de los clientes de correo)."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from db import storage
from financing import simular as simular_financiacion
from report.generate_report import _es_hoy, _filas_parametros_aplicados, _pros_contras
from scoring import construir_explicacion

BASE_DIR = Path(__file__).parent.parent
WEBAPP_DIR = BASE_DIR / "webapp"
WEBAPP_DIR.mkdir(exist_ok=True)


def _anuncio_a_dict(row) -> dict:
    pros, contras = _pros_contras(row)
    nuevo = _es_hoy(row["primer_visto"])
    bajada = (
        row["primer_precio"] is not None
        and row["precio"] is not None
        and row["precio"] < row["primer_precio"]
    )
    return {
        "url": row["url"],
        "web_id": row["web_id"],
        "modelo_id": row["modelo_id"],
        "titulo": row["titulo"],
        "marca": row["marca"],
        "modelo": row["modelo"],
        "version": row["version"],
        "anio": row["anio"],
        "km": row["km"],
        "precio": row["precio"],
        "combustible": row["combustible"],
        "cambio": row["cambio"],
        "etiqueta": row["etiqueta"],
        "foto_url": row["foto_url"],
        "vendedor_tipo": row["vendedor_tipo"],
        "garantia_meses": row["garantia_meses"],
        "ubicacion": row["ubicacion"],
        "puntuacion": row["puntuacion"],
        "pros": pros,
        "contras": contras,
        "explicacion": construir_explicacion(row["puntuacion"], pros, contras),
        "financiacion": simular_financiacion(row["precio"], row["cuota_financiacion_vendedor"]),
        "nuevo_hoy": nuevo,
        "bajada_precio": bajada,
        "precio_anterior": row["primer_precio"] if bajada else None,
        "primer_visto": row["primer_visto"],
    }


def _modelo_a_dict(conn, modelo: dict, generales: dict) -> dict:
    fotos = storage.fotos_modelo(conn, modelo["id"], limit=8)
    foto_generica = modelo.get("foto_generica")
    atribucion = None
    if not fotos and foto_generica:
        fotos = [foto_generica]
        atribucion = modelo.get("foto_generica_atribucion")

    tabla = list(modelo.get("tabla_detalle", [])) + _filas_parametros_aplicados(modelo, generales)

    return {
        "id": modelo["id"],
        "nombre": modelo["nombre"],
        "marca": modelo["marca"],
        "fiabilidad_puntuacion": modelo.get("fiabilidad_puntuacion"),
        "fiabilidad_descripcion": modelo.get("fiabilidad_descripcion"),
        "resumen_problemas": modelo.get("resumen_problemas"),
        "resumen_parametros": modelo.get("resumen_parametros"),
        "revision_obligada": modelo.get("revision_obligada", []),
        "tabla_detalle": tabla,
        "fotos": fotos,
        "foto_atribucion": atribucion,
    }


def generar_datos_app(parametros_modelos: list[dict], parametros_generales: dict) -> Path:
    conn = storage.conectar()

    modelos = [_modelo_a_dict(conn, m, parametros_generales) for m in parametros_modelos]
    anuncios = [_anuncio_a_dict(f) for f in storage.todos_los_anuncios_activos(conn)]

    conn.close()

    datos = {
        "generado": datetime.now(timezone.utc).isoformat(),
        "fecha": date.today().isoformat(),
        "modelos": modelos,
        "anuncios": anuncios,
    }

    ruta = WEBAPP_DIR / "data.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=0), encoding="utf-8")
    return ruta
