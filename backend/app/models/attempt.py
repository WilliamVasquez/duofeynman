"""Intentos del usuario explicando un Topic (ciclo Feynman)."""
from datetime import datetime
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, Float, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Attempt(Base):
    """Un intento = una sesión de explicación de un Topic.

    El ciclo Feynman puede tener varias rondas (refine), cada una guardada en
    `rounds` como JSON: [{"transcript":"...", "feedback":"...", "score":0.7}]
    """
    __tablename__ = "attempts"
    # Índice compuesto: racha (update_streak) e insights filtran por
    # user_id + completed_at en cada intento masterizado.
    __table_args__ = (Index("ix_attempts_user_completed", "user_id", "completed_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), index=True)

    stage: Mapped[str] = mapped_column(String(20), default="EXPLAIN")
    # EXPOSE | EXPLAIN | DETECT | REFINE | CONSOLIDATE | DONE

    rounds: Mapped[list] = mapped_column(JSON, default=list)

    # Métricas de dominio (calculadas al cerrar el intento)
    fluency_score: Mapped[float] = mapped_column(Float, default=0.0)        # 0-1
    code_switch_rate: Mapped[float] = mapped_column(Float, default=0.0)     # 0-1
    error_density: Mapped[float] = mapped_column(Float, default=0.0)        # err/100w
    self_correction_rate: Mapped[float] = mapped_column(Float, default=0.0)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)        # 0-1
    mastered: Mapped[bool] = mapped_column(default=False)

    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    word_count: Mapped[int] = mapped_column(Integer, default=0)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user = relationship("User", back_populates="attempts")
    errors = relationship("AttemptError", back_populates="attempt", cascade="all, delete-orphan")


class AttemptError(Base):
    """Errores específicos detectados (para análisis y SRS targeted)."""
    __tablename__ = "attempt_errors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.id"), index=True)
    category: Mapped[str] = mapped_column(String(60))
    # GRAMMAR | PRONUNCIATION | VOCABULARY | CODE_SWITCH | FILLER | INCOMPLETE
    rule_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    span_text: Mapped[str] = mapped_column(String(500))
    suggestion: Mapped[str] = mapped_column(String(500), default="")
    explanation_es: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[int] = mapped_column(Integer, default=1)  # 1-3

    attempt = relationship("Attempt", back_populates="errors")
