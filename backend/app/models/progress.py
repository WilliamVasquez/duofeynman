"""Progreso del usuario y gamificación."""
from datetime import datetime, date
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, Date, Float, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserProgress(Base):
    """Progreso por Topic. Se actualiza con cada Attempt."""
    __tablename__ = "user_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), index=True)

    attempts_count: Mapped[int] = mapped_column(Integer, default=0)
    best_score: Mapped[float] = mapped_column(Float, default=0.0)
    last_score: Mapped[float] = mapped_column(Float, default=0.0)
    mastery_level: Mapped[int] = mapped_column(Integer, default=0)  # 0=nuevo, 5=dominado
    last_practiced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user = relationship("User", back_populates="progress")

    __table_args__ = (
        Index("ix_progress_user_topic", "user_id", "topic_id", unique=True),
    )


class Achievement(Base):
    """Logros desbloqueables (gamificación)."""
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    title_es: Mapped[str] = mapped_column(String(200))
    description_es: Mapped[str] = mapped_column(Text)
    icon: Mapped[str] = mapped_column(String(40), default="trophy")
    xp_reward: Mapped[int] = mapped_column(Integer, default=10)


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    achievement_id: Mapped[int] = mapped_column(ForeignKey("achievements.id"), index=True)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="achievements")

    __table_args__ = (
        Index("ix_user_achievement_unique", "user_id", "achievement_id", unique=True),
    )
