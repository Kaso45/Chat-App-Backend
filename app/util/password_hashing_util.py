"""Module providing hashing and verifying password functions"""

import bcrypt

def hash_password(password: str) -> str:
    """Function for hashing password"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """function for verifying plain password and hashed password"""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))