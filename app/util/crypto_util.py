"""Module providing encryption and decryption functions"""

from cryptography.fernet import Fernet
from app.config import settings

key = settings.FERNET_SECRET_KEY
cipher = Fernet(key)

def encrypt_data(data: str):
    """Function for data encryption"""
    try:
        return cipher.encrypt(data.encode())
    except Exception as e:
        raise RuntimeError("Encryption failed") from e
    
def decrypt_data(encrypted_data: str):
    """Function for data decryption"""
    try:
        return cipher.decrypt(encrypted_data)
    except Exception as e:
        raise RuntimeError("Description failed") from e