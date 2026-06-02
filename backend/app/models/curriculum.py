"""Estructura del curriculum: Módulos → Lecciones → Temas (Topics).

Un Topic es la unidad mínima de práctica Feynman: un concepto que el usuario
debe poder explicar en inglés en voz alta.
"""
from sqlalchemy import String, Integer, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title_es: Mapped[str] = mapped_column(String(200))
    title_en: Mapped[str] = mapped_column(String(200))
    description_es: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(10), default="A1")  # A1, A2, B1, B2
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan", order_by="Lesson.order_index")


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"), index=True)
    slug: Mapped[str] = mapped_column(String(80), index=True)
    title_es: Mapped[str] = mapped_column(String(200))
    title_en: Mapped[str] = mapped_column(String(200))
    objective_es: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    module = relationship("Module", back_populates="lessons")
    topics = relationship("Topic", back_populates="lesson", cascade="all, delete-orphan", order_by="Topic.order_index")


class Topic(Base):
    """Tema concreto que el usuario debe poder explicar (núcleo Feynman)."""
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), index=True)
    slug: Mapped[str] = mapped_column(String(80))
    prompt_es: Mapped[str] = mapped_column(Text)         # "Explicá tu rutina diaria"
    prompt_en: Mapped[str] = mapped_column(Text)         # "Explain your daily routine"
    example_en: Mapped[str] = mapped_column(Text)        # respuesta modelo nativa
    # vocabulario clave: [{"en":"wake up","es":"despertarse","ipa":"weɪk ʌp"}]
    key_vocabulary: Mapped[list] = mapped_column(JSON, default=list)
    # frases conectoras sugeridas: ["first","then","after that","because"]
    connectors: Mapped[list] = mapped_column(JSON, default=list)
    # preguntas socráticas que la IA puede usar como guía
    socratic_hints: Mapped[list] = mapped_column(JSON, default=list)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)  # 1-5
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    lesson = relationship("Lesson", back_populates="topics")

    __table_args__ = (
        Index("ix_topics_lesson_slug", "lesson_id", "slug", unique=True),
    )
