# Buscador de coches de ocasión

Scraper diario + app web (PWA) que busca coches de ocasión en varias webs, los puntúa
por fiabilidad/precio/km, simula 3 financiaciones por anuncio, y lo publica cada día:
- por email (adjunto HTML), y
- en una app instalable en el móvil (con fotos y filtros reales, sin las limitaciones
  del cliente de correo).

Todo corre automáticamente en GitHub Actions: no depende de que tu PC esté encendido.

## Puesta en marcha (una sola vez)

### 1. Crear la cuenta y el repositorio en GitHub

1. Entra en https://github.com/join y crea una cuenta gratuita (si no tienes).
2. Entra en https://github.com/new, ponle de nombre p. ej. `buscador-coches`, márcalo
   **Public** (necesario para que GitHub Pages sea gratis), y crea el repositorio
   **vacío** (sin README, sin .gitignore — ya los trae esta carpeta).
3. Copia la URL que te da GitHub (algo como `https://github.com/tu-usuario/buscador-coches.git`)
   y pásamela para que haga el primer `git push`.

### 2. Secrets (credenciales, nunca en el código)

En el repo ya creado: **Settings → Secrets and variables → Actions → New repository secret**.
Añade estos tres (son los mismos datos que ya tienes en `config/email_config.json`, que
se queda solo en tu PC y nunca se sube):

| Nombre | Valor |
|---|---|
| `EMAIL_REMITENTE` | tu Gmail |
| `EMAIL_DESTINATARIO` | tu Gmail (o a quien quieras avisar) |
| `EMAIL_APP_PASSWORD` | la contraseña de aplicación de 16 caracteres de Gmail |

Importante: como esa contraseña ya estuvo en un archivo local, te recomiendo
**revocarla y generar una nueva** en https://myaccount.google.com/apppasswords antes
de guardarla en el Secret, solo por higiene.

### 3. Activar GitHub Pages

**Settings → Pages → Build and deployment → Source** → elige **"GitHub Actions"**
(no "Deploy from a branch"). No hace falta nada más, el workflow ya sube la app ahí.

### 4. (Opcional) Variable con la URL de la app

Una vez que el primer deploy termine, GitHub te da la URL de Pages (algo como
`https://tu-usuario.github.io/buscador-coches/`). En **Settings → Secrets and
variables → Actions → Variables → New repository variable**, añade:

| Nombre | Valor |
|---|---|
| `APP_URL` | la URL de Pages de arriba |

Así el email diario incluye también el enlace a la app.

### 5. Primera ejecución

En la pestaña **Actions** del repo, entra en el workflow "Informe diario de coches" y
pulsa **Run workflow** para lanzarlo a mano la primera vez (si no, espera a la hora
programada). Tarda unos minutos; al terminar, la app está publicada y el email enviado.

## Instalar la app en el móvil

Abre la URL de Pages en Chrome (Android) o Safari (iPhone) y usa "Añadir a pantalla
de inicio" / "Instalar app". Queda como un icono normal; al abrirla carga los
datos del último informe, con fotos y los filtros funcionando de verdad (a
diferencia del adjunto de email, aquí no hay restricciones de JavaScript).

## Automatización

`.github/workflows/daily.yml` corre cada día a las 06:30 UTC (~7:30-8:30 hora de
Madrid según el horario). Puedes cambiar la hora editando el `cron` de ese archivo.
Cada ejecución: scrapea, puntúa, guarda histórico en `db/coches.sqlite3` (se commitea
de vuelta al repo para no perder el histórico entre ejecuciones), genera
`webapp/data.json`, envía el email, y publica la app en Pages.

La tarea programada de Windows (Task Scheduler) en tu PC de casa deja de ser
necesaria; puedes desactivarla cuando quieras.

## Desarrollo local

```bash
pip install -r requirements.txt
playwright install chromium
cp config/email_config.example.json config/email_config.json  # y edítalo con tus datos
python run_daily.py
```

Para ver la app en local:

```bash
cd webapp
python -m http.server 8000
```

y abre `http://localhost:8000`.
