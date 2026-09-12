"""Práctica persistente. Tablas nuevas: no alteran el historial existente."""
from datetime import datetime, date
from uuid import uuid4
from sqlalchemy import String, ForeignKey, Integer, Float, Boolean, JSON, DateTime, Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.timeutils import utcnow


class DialogueSession(Base):
    __tablename__ = "dialogue_sessions"
    __table_args__ = (UniqueConstraint("user_id", "dialogue_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    dialogue_id: Mapped[int] = mapped_column(ForeignKey("dialogues.id"), index=True)
    snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cursor: Mapped[int] = mapped_column(Integer, default=0)
    run_number: Mapped[int] = mapped_column(Integer, default=1)
    completed_runs: Mapped[int] = mapped_column(Integer, default=0)
    support_stage: Mapped[int] = mapped_column(Integer, default=0)
    stage_successes: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class DialogueResponse(Base):
    __tablename__ = "dialogue_responses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("dialogue_sessions.id"), index=True)
    run_number: Mapped[int] = mapped_column(Integer)
    turn_index: Mapped[int] = mapped_column(Integer)
    user_text: Mapped[str] = mapped_column(String(1000))
    mode: Mapped[str] = mapped_column(String(12))
    used_help: Mapped[bool] = mapped_column(Boolean, default=False)
    continued: Mapped[bool] = mapped_column(Boolean, default=False)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ListeningAttempt(Base):
    __tablename__ = "listening_attempts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    exercise_slug: Mapped[str] = mapped_column(String(100))
    heard: Mapped[bool] = mapped_column(Boolean, default=False)
    revealed: Mapped[bool] = mapped_column(Boolean, default=False)
    choice: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DailyPlan(Base):
    __tablename__ = "daily_plans"
    __table_args__ = (UniqueConstraint("user_id", "day"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[date] = mapped_column(Date)
    items: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
