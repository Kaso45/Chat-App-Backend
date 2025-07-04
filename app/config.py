"""Module providing class to access for environment variables"""

import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Class for getting environment variables"""
    MONGO_URI: str = os.getenv("MONGO_URI")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")
    FERNET_SECRET_KEY: str = os.getenv("FERNET_SECRET_KEY")

settings = Settings()