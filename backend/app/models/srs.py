"""Spaced Repetition System (algoritmo SM-2 simplificado)."""
from datetime import datetime, date
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, Float, Date, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SrsCard(Base):
    """Una tarjeta SRS = algo que el usuario debe recordar/practicar.

    Puede ser:
    - Un Topic ya explicado (revisión completa)
    - Un error específico que cometió (mini-drill)
    - Una pieza de vocabulario / connector
    """
    __tablename__ = "srs_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id"), nullable=True, index=True)

    card_type: Mapped[str] = mapped_column(String(30), default="TOPIC")
    # TOPIC | VOCAB | CONNECTOR | ERROR_DRILL

    front: Mapped[str] = mapped_column(Text)           # prompt mostrado
    back: Mapped[str] = mapped_column(Text)            # respuesta esperada / explicación
    payload: Mapped[dict] = mapped_column(JSON, default=dict)  # extras (audio_url, ipa, etc.)

    # SM-2
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    interval_days: Mapped[int] = mapped_column(Integer, default=0)
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    due_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user = relationship("User", back_populates="srs_cards")
