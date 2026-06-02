"""Hash de contraseñas (bcrypt directo) y JWT.

Usamos `bcrypt` directamente en vez de `passlib` porque passlib está
abandonado y rompe con bcrypt >= 4.x.
"""
from datetime import datetime, timedelta

import bcrypt
from jose import jwt, JWTError

from app.config import settings


# bcrypt tiene un límite de 72 bytes en la contraseña. Truncamos en bytes
# (no en chars) para soportar passwords con tildes/emojis correctamente.
def _to_bytes(plain: str) -> bytes:
    return plain.encode("utf-8")[:72]


def hash_password(plain: str) -> str:
    hashed = bcrypt.hashpw(_to_bytes(plain), bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bytes(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str | int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(subject), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
