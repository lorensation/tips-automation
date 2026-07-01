from email.message import EmailMessage
from pathlib import Path
import smtplib

from app.config import Settings


def send_outputs_email(settings: Settings, subject: str, body: str, attachment_paths: list[Path]) -> None:
    if not settings.smtp_host or not settings.smtp_from or not settings.email_recipient_list:
        raise RuntimeError("SMTP is not configured")
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from
    message["To"] = ", ".join(settings.email_recipient_list)
    message.set_content(body)
    for path in attachment_paths:
        data = path.read_bytes()
        message.add_attachment(data, maintype="application", subtype="octet-stream", filename=path.name)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)
