import asyncio
import logging
import smtplib
from email.mime.text import MIMEText

from app.core.config import get_settings

logger = logging.getLogger("app.email")


def _send_sync(*, host: str, to: str, subject: str, body: str) -> None:
    settings = get_settings()
    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = settings.smtp_from_email
    message["To"] = to

    with smtplib.SMTP(host, settings.smtp_port, timeout=10) as client:
        if settings.smtp_use_tls:
            client.starttls()
        if settings.smtp_username and settings.smtp_password:
            client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(message)


async def send_email(*, to: str, subject: str, body: str) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        logger.info(
            "SMTP not configured; logging email instead.\nTo: %s\nSubject: %s\n%s",
            to,
            subject,
            body,
        )
        return

    try:
        await asyncio.to_thread(
            _send_sync, host=settings.smtp_host, to=to, subject=subject, body=body
        )
    except OSError:
        logger.exception("Failed to send email to %s", to)
