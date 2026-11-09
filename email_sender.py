"""
Envio del informe diario por email (Paso 3 del pedido de mejoras).

Usa SMTP sobre la cuenta de Gmail del usuario con una "contrasena de aplicacion"
(App Password) que el propio usuario genera y guarda en config/email_config.json.
Ese archivo es local, nunca se ha compartido con Claude, y si "activo" esta en false
o falta la contrasena, el envio simplemente se omite (con un aviso en el log) sin
romper el resto de la ejecucion diaria.
"""
from __future__ import annotations

import json
import logging
import os
import smtplib
from datetime import date
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "config" / "email_config.json"


def _cargar_config() -> dict | None:
    """Config de email: variables de entorno (GitHub Actions Secrets) si existen,
    si no el archivo local config/email_config.json (uso en el PC de casa)."""
    if os.environ.get("EMAIL_APP_PASSWORD"):
        return {
            "activo": os.environ.get("EMAIL_ACTIVO", "true").lower() != "false",
            "remitente": os.environ.get("EMAIL_REMITENTE", ""),
            "destinatario": os.environ.get("EMAIL_DESTINATARIO", ""),
            "app_password": os.environ.get("EMAIL_APP_PASSWORD", ""),
            "smtp_host": os.environ.get("EMAIL_SMTP_HOST", "smtp.gmail.com"),
            "smtp_port": int(os.environ.get("EMAIL_SMTP_PORT", "587")),
        }
    if not CONFIG_PATH.exists():
        return None
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def enviar_informe(ruta_html: Path, resumen_texto: str = "") -> bool:
    """Envia el informe HTML como adjunto. Devuelve True si se envio, False si se omitio/fallo."""
    config = _cargar_config()
    if not config:
        logger.info("email: config/email_config.json no existe, se omite el envio")
        return False
    if not config.get("activo"):
        logger.info("email: envio desactivado (activo=false en email_config.json)")
        return False
    if not config.get("app_password"):
        logger.warning("email: falta app_password en email_config.json, se omite el envio")
        return False

    hoy = date.today().isoformat()
    msg = MIMEMultipart()
    msg["Subject"] = f"Informe de coches de ocasion - {hoy}"
    msg["From"] = config["remitente"]
    msg["To"] = config["destinatario"]

    app_url = os.environ.get("APP_URL", "")
    aviso_app = f"\n\nApp (fotos y filtros en el movil): {app_url}" if app_url else ""
    cuerpo = resumen_texto or (
        "Informe diario de coches de ocasion adjunto.\n\n"
        "Abrelo en el navegador del movil o del ordenador para usar los filtros "
        "y la ordenacion (no funcionan dentro del cuerpo del correo)."
        + aviso_app
    )
    msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

    with open(ruta_html, "rb") as f:
        adjunto = MIMEApplication(f.read(), _subtype="html")
    adjunto.add_header("Content-Disposition", "attachment", filename=ruta_html.name)
    msg.attach(adjunto)

    try:
        with smtplib.SMTP(config["smtp_host"], config["smtp_port"], timeout=30) as server:
            server.starttls()
            server.login(config["remitente"], config["app_password"])
            server.send_message(msg)
        logger.info("email: informe enviado a %s", config["destinatario"])
        return True
    except Exception as e:  # noqa: BLE001 - un fallo de email no debe tumbar el resto de la ejecucion
        logger.warning("email: fallo al enviar (%s)", e)
        return False
