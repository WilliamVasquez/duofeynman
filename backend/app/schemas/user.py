import re
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator


# Passwords muy comunes — bloquearlas reduce el éxito de credential stuffing.
_COMMON_PASSWORDS = {
    "password", "123456789", "12345678", "qwerty12", "qwerty123",
    "password1", "abc12345", "1q2w3e4r", "letmein1", "iloveyou1",
    "welcome1", "admin123", "duofeynman", "william123",
}


def _validate_password_strength(p: str) -> str:
    if len(p) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    if not re.search(r"[A-Za-z]", p) or not re.search(r"\d", p):
        raise ValueError("La contraseña debe mezclar letras y al menos un número.")
    if p.lower() in _COMMON_PASSWORDS:
        raise ValueError("Esa contraseña es demasiado común. Elegí otra.")
    return p


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=60, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    target_level: str = Field(default="A1", pattern=r"^(A1|A2|B1|B2)$")

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: str
    current_level: str
    target_level: str
    streak_days: int
    total_xp: int
    daily_goal_minutes: int
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
