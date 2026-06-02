"""Usuario de la app."""
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(190), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    native_language: Mapped[str] = mapped_column(String(10), default="es")
    target_level: Mapped[str] = mapped_column(String(10), default="A1")
    current_level: Mapped[str] = mapped_column(String(10), default="A1")
    daily_goal_minutes: Mapped[int] = mapped_column(Integer, default=15)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    total_xp: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    attempts = relationship("Attempt", back_populates="user", cascade="all, delete-orphan")
    srs_cards = relationship("SrsCard", back_populates="user", cascade="all, delete-orphan")
    progress = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")
    achievements = relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")
