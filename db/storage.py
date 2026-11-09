"""Acceso a la base de datos SQLite local: historico de anuncios y registro de ejecuciones."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "coches.sqlite3"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def conectar() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
    return conn


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def guardar_anuncio(conn: sqlite3.Connection, listing, puntuacion_resultado: dict) -> dict:
    """Inserta o actualiza un anuncio. Devuelve metadatos: es_nuevo, bajada_precio, precio_anterior.

    `puntuacion_resultado` es el dict que devuelve scoring.puntuar(): {"nota", "desglose", "motivos"}.
    """
    ahora = _ahora()
    fila = conn.execute("SELECT * FROM anuncios WHERE url = ?", (listing.url,)).fetchone()
    puntuacion = puntuacion_resultado["nota"]
    motivos_json = json.dumps(
        {"pros": puntuacion_resultado["pros"], "contras": puntuacion_resultado["contras"]}, ensure_ascii=False
    )

    if fila is None:
        conn.execute(
            """
            INSERT INTO anuncios (
                url, web_id, modelo_id, titulo, marca, modelo, version, anio, km, precio,
                combustible, cambio, etiqueta, foto_url, vendedor_tipo, garantia_meses,
                cuota_financiacion_vendedor, ubicacion, puntuacion, motivos, texto_anuncio,
                primer_visto, ultima_vez_visto, primer_precio, activo
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)
            """,
            (
                listing.url, listing.web_id, listing.modelo_id, listing.titulo, listing.marca,
                listing.modelo, listing.version, listing.anio, listing.km, listing.precio,
                listing.combustible, listing.cambio, listing.etiqueta, listing.foto_url,
                listing.vendedor_tipo, listing.garantia_meses, listing.cuota_financiacion_vendedor,
                listing.ubicacion, puntuacion, motivos_json, listing.texto_anuncio,
                ahora, ahora, listing.precio,
            ),
        )
        conn.commit()
        return {"es_nuevo": True, "bajada_precio": False, "precio_anterior": None}

    bajada_precio = (
        listing.precio is not None and fila["precio"] is not None and listing.precio < fila["precio"]
    )
    conn.execute(
        """
        UPDATE anuncios SET
            titulo=?, km=?, precio=?, puntuacion=?, motivos=?, foto_url=?, ultima_vez_visto=?, activo=1
        WHERE url=?
        """,
        (listing.titulo, listing.km, listing.precio, puntuacion, motivos_json, listing.foto_url, ahora, listing.url),
    )
    conn.commit()
    return {
        "es_nuevo": False,
        "bajada_precio": bajada_precio,
        "precio_anterior": fila["precio"] if bajada_precio else None,
    }


def marcar_inactivos_no_vistos(conn: sqlite3.Connection, urls_vistas_hoy: set[str], modelo_id: str) -> None:
    """Los anuncios de ese modelo que no aparecieron en esta ejecucion se marcan inactivos (probablemente vendidos/retirados)."""
    filas = conn.execute(
        "SELECT url FROM anuncios WHERE modelo_id = ? AND activo = 1", (modelo_id,)
    ).fetchall()
    for fila in filas:
        if fila["url"] not in urls_vistas_hoy:
            conn.execute("UPDATE anuncios SET activo = 0 WHERE url = ?", (fila["url"],))
    conn.commit()


def registrar_ejecucion(
    conn: sqlite3.Connection, web_id: str, modelo_id: str, estado: str, num_anuncios: int, detalle: str = ""
) -> None:
    conn.execute(
        "INSERT INTO ejecuciones (fecha, web_id, modelo_id, estado, num_anuncios, detalle) VALUES (?,?,?,?,?,?)",
        (_ahora(), web_id, modelo_id, estado, num_anuncios, detalle),
    )
    conn.commit()


def anuncios_activos_por_modelo(conn: sqlite3.Connection, modelo_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM anuncios WHERE modelo_id = ? AND activo = 1 ORDER BY puntuacion DESC", (modelo_id,)
    ).fetchall()


def todos_los_anuncios_activos(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM anuncios WHERE activo = 1 ORDER BY puntuacion DESC").fetchall()


def foto_representativa_modelo(conn: sqlite3.Connection, modelo_id: str) -> str | None:
    fotos = fotos_modelo(conn, modelo_id, limit=1)
    return fotos[0] if fotos else None


def fotos_modelo(conn: sqlite3.Connection, modelo_id: str, limit: int = 8) -> list[str]:
    """Varias fotos distintas (de distintos anuncios) de ese modelo, para la galeria de la ficha."""
    filas = conn.execute(
        "SELECT DISTINCT foto_url FROM anuncios WHERE modelo_id = ? AND activo = 1 AND foto_url IS NOT NULL "
        "ORDER BY puntuacion DESC LIMIT ?",
        (modelo_id, limit),
    ).fetchall()
    return [f["foto_url"] for f in filas]
