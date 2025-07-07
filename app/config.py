"""Module providing class to access for environment variables"""

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

class Settings(BaseSettings):
    """Class for getting environment variables"""
    MONGO_URI: str
    ACCESS_TOKEN_SECRET: str
    RESET_PASSWORD_TOKEN_SECRET: str
    FERNET_SECRET_KEY: str

    model_config = SettingsConfigDict(
        env_file=".env"
    )

settings = Settings()
