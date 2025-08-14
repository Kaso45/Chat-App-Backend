"""Configuration settings loaded from environment variables (.env)."""

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """Class for getting environment variables"""

    MONGO_URI: str
    ACCESS_TOKEN_SECRET: str
    RESET_PASSWORD_TOKEN_SECRET: str
    ACCESS_TOKEN_EXPIRE_MINUTE: int
    RESET_PASSWORD_TOKEN_EXPIRE_MINUTE: int
    FERNET_SECRET_KEY: str
    SENDER_MAIL: str
    SENDER_MAIL_PASSWORD: str
    ALGORITHM: str
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_USERNAME: str
    REDIS_PASSWORD: str

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()  # type: ignore
