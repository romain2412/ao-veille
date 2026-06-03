"""
Envoi d'emails via SMTP — avec dégradation gracieuse.

La configuration est lue depuis l'environnement :
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SMTP_TLS

Si SMTP_HOST n'est pas défini, l'envoi est simplement ignoré (no-op) et
`send_email` renvoie False, sans lever d'erreur : l'application continue de
fonctionner (ex. l'admin transmet le lien d'invitation manuellement).
"""
from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def smtp_configured() -> bool:
    """Vrai si un serveur SMTP est configuré (au minimum SMTP_HOST)."""
    return bool(os.getenv("SMTP_HOST"))


def send_email(to: str, subject: str, body_text: str, body_html: str | None = None) -> bool:
    """Envoie un email. Renvoie True si envoyé, False sinon (non configuré ou échec).

    N'élève jamais d'exception : un échec d'envoi ne doit pas casser l'appelant.
    """
    if not smtp_configured():
        logger.info("[mailer] SMTP non configuré — email non envoyé (à %s).", to)
        return False

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER") or None
    password = os.getenv("SMTP_PASSWORD") or None
    sender = os.getenv("SMTP_FROM") or user or "no-reply@fbvrd-tools.fr"
    use_tls = os.getenv("SMTP_TLS", "true").lower() in ("1", "true", "yes")

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    try:
        if port == 465:
            # SMTPS (TLS implicite)
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=context, timeout=20) as server:
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20) as server:
                if use_tls:
                    server.starttls(context=ssl.create_default_context())
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        logger.info("[mailer] Email envoyé à %s (sujet: %s).", to, subject)
        return True
    except Exception as exc:
        logger.warning("[mailer] Échec d'envoi à %s : %s", to, exc)
        return False
