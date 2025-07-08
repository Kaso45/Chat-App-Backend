import os
from fastapi_mail import ConnectionConfig

from app.config.config import settings

dirname = os.path.dirname(__file__)
templates_folder = os.path.join(dirname, "../templates")

mail_conf = ConnectionConfig(
    MAIL_USERNAME=settings.SENDER_MAIL,
    MAIL_PASSWORD=settings.SENDER_MAIL_PASSWORD,
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
