"""Mail configuration using FastMail and project templates."""

from pathlib import Path
from fastapi_mail import ConnectionConfig
from pydantic import SecretStr
from app.config.config import settings

templates_folder = (Path(__file__).parent.parent / "templates").resolve()

mail_conf = ConnectionConfig(
    MAIL_USERNAME=settings.SENDER_MAIL,
    MAIL_PASSWORD=SecretStr(settings.SENDER_MAIL_PASSWORD),
    MAIL_FROM=settings.SENDER_MAIL,
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_FROM_NAME="Chat app",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=False,
    TEMPLATE_FOLDER=templates_folder,
)
