CREATE TABLE IF NOT EXISTS anuncios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    web_id TEXT NOT NULL,
    modelo_id TEXT NOT NULL,
    titulo TEXT,
    marca TEXT,
    modelo TEXT,
    version TEXT,
    anio INTEGER,
    km INTEGER,
    precio REAL,
    combustible TEXT,
    cambio TEXT,
    etiqueta TEXT,
    foto_url TEXT,
    vendedor_tipo TEXT,
    garantia_meses INTEGER,
    cuota_financiacion_vendedor REAL,
    ubicacion TEXT,
    puntuacion REAL,
    motivos TEXT,
    texto_anuncio TEXT,
    primer_visto TEXT NOT NULL,
    ultima_vez_visto TEXT NOT NULL,
    primer_precio REAL,
    activo INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_anuncios_modelo ON anuncios(modelo_id);
CREATE INDEX IF NOT EXISTS idx_anuncios_web ON anuncios(web_id);

CREATE TABLE IF NOT EXISTS ejecuciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    web_id TEXT NOT NULL,
    modelo_id TEXT NOT NULL,
    estado TEXT NOT NULL,          -- 'ok' | 'error' | 'bloqueado' | 'sin_resultados'
    num_anuncios INTEGER DEFAULT 0,
    detalle TEXT
);
