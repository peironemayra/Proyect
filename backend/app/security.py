from __future__ import annotations

import secrets
from passlib.context import CryptContext

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return _pwd.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return _pwd.verify(password, password_hash)

def new_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
