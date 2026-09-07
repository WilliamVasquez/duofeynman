"""Ejercicios de dictado: respuesta y recompensa controladas por el servidor."""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, ForeignKey, Text, DateTime, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.timeutils import utcnow


class DictationExercise(Base):
    __tablename__ = "dictation_exercises"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"))
    target: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    best_score: Mapped[float] = mapped_column(Float, default=0.0)
    rewarded: Mapped[bool] = mapped_column(Boolean, default=False)
