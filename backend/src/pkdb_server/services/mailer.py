"""Synchronous injected SMTP transport; credentials are never logged."""

import smtplib
from email.message import EmailMessage

from pkdb_server.config import Settings
from pkdb_server.services.accounts import MailDeliveryFailed


class SMTPMailer:
    def __init__(self, settings: Settings):
        self.settings = settings

    def send(self, recipient: str, subject: str, body: str) -> None:
        settings = self.settings
        if not settings.smtp_host or not settings.smtp_sender:
            raise MailDeliveryFailed("Email delivery is not configured")
        message = EmailMessage()
        message["From"] = settings.smtp_sender
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_starttls:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(
                    settings.smtp_username, settings.smtp_password.get_secret_value()
                )
            smtp.send_message(message)
