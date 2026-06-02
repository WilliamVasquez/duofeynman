"""Perfil del usuario para personalizar la experiencia.

Es opcional — el usuario puede no llenarlo y la app igual funciona.
La data acá NO se usa para autenticación, solo para personalizar prompts
y filtrar contenido en el frontend.
"""
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)

    nickname: Mapped[str] = mapped_column(String(120), default="")
    job: Mapped[str] = mapped_column(String(255), default="")
    city: Mapped[str] = mapped_column(String(120), default="")
    has_partner: Mapped[bool] = mapped_column(Boolean, default=False)
    partner_name: Mapped[str] = mapped_column(String(120), default="")
    has_kids: Mapped[bool] = mapped_column(Boolean, default=False)
    hobbies: Mapped[str] = mapped_column(String(500), default="")
    travels_often: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_goal_minutes: Mapped[int] = mapped_column(Integer, default=15)

    # JSON: áreas de interés (work, relationship, family, ...)
    interests: Mapped[dict] = mapped_column(JSON, default=dict)
    # JSON: {"dialogues": ["slug1", ...], "topics": [...]}
    hidden_items: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
