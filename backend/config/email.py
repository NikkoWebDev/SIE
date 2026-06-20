"""Email delivery via SMTP (stdlib only).

Configuration is read from environment variables. When SMTP is not
configured the sender raises EmailNotConfigured so callers can decide how
to degrade. No third-party dependencies are used.

Required env vars to enable delivery:
    SMTP_HOST           e.g. smtp.gmail.com
    SMTP_PORT           e.g. 587 (STARTTLS) or 465 (SSL)
    SMTP_USERNAME       SMTP auth user
    SMTP_PASSWORD       SMTP auth password / app password
    SMTP_FROM           From address (defaults to SMTP_USERNAME)
    SMTP_USE_SSL        "true" to use implicit SSL (port 465); else STARTTLS
"""
from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

logger = logging.getLogger("siee.email")


class EmailNotConfigured(RuntimeError):
    """Raised when SMTP credentials are not present in the environment."""


def _smtp_config() -> dict[str, str]:
    host = os.getenv("SMTP_HOST", "").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    if not host or not username or not password:
        raise EmailNotConfigured(
            "SMTP no configurado (SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD ausentes)"
        )
    return {
        "host": host,
        "port": os.getenv("SMTP_PORT", "587").strip(),
        "username": username,
        "password": password,
        "from_addr": os.getenv("SMTP_FROM", username).strip(),
        "use_ssl": os.getenv("SMTP_USE_SSL", "false").strip().lower() == "true",
    }


def is_configured() -> bool:
    try:
        _smtp_config()
        return True
    except EmailNotConfigured:
        return False


def send_email(to_addr: str, subject: str, body: str) -> None:
    """Send a plaintext email. Raises EmailNotConfigured or smtplib errors."""
    cfg = _smtp_config()
    msg = EmailMessage()
    msg["From"] = cfg["from_addr"]
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)

    port = int(cfg["port"])
    context = ssl.create_default_context()

    if cfg["use_ssl"]:
        with smtplib.SMTP_SSL(cfg["host"], port, context=context, timeout=15) as server:
            server.login(cfg["username"], cfg["password"])
            server.send_message(msg)
    else:
        with smtplib.SMTP(cfg["host"], port, timeout=15) as server:
            server.starttls(context=context)
            server.login(cfg["username"], cfg["password"])
            server.send_message(msg)
