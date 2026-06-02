"""Diálogos guionados estilo "role-play" para practicar inglés conversacional.

Cada Dialogue es una escena (ej. "Pedir comida en un restaurante").
Tiene varios DialogueTurn alternados: NPC habla → usuario responde → NPC habla...

El usuario produce inglés en cada turno; un motor rule-based valida si su
respuesta cumple con el patrón esperado (keywords + similitud + sin code-switch).
"""
from sqlalchemy import String, Integer, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Dialogue(Base):
    __tablename__ = "dialogues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title_es: Mapped[str] = mapped_column(String(200))
    title_en: Mapped[str] = mapped_column(String(200))
    description_es: Mapped[str] = mapped_column(Text)
    setting_es: Mapped[str] = mapped_column(Text)              # contexto: dónde y con quién
    setting_en: Mapped[str] = mapped_column(Text, nullable=True)  # mismo contexto en inglés (puede ser NULL en DBs antiguas)
    npc_name: Mapped[str] = mapped_column(String(60), default="Person")
    npc_role_es: Mapped[str] = mapped_column(String(100), default="otra persona")
    icon: Mapped[str] = mapped_column(String(10), default="💬")
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    is_adult: Mapped[bool] = mapped_column(default=False)
    level: Mapped[str] = mapped_column(String(10), default="A1")
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    key_vocabulary: Mapped[list] = mapped_column(JSON, default=list)

    turns = relationship(
        "DialogueTurn",
        back_populates="dialogue",
        cascade="all, delete-orphan",
        order_by="DialogueTurn.order_index",
    )


class DialogueTurn(Base):
    __tablename__ = "dialogue_turns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dialogue_id: Mapped[int] = mapped_column(ForeignKey("dialogues.id"), index=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    speaker: Mapped[str] = mapped_column(String(10), default="NPC")   # NPC | USER

    # Para turnos NPC: lo que dice (texto que se lee por TTS)
    npc_text_en: Mapped[str] = mapped_column(Text, default="")
    npc_text_es: Mapped[str] = mapped_column(Text, default="")  # traducción para entender

    # Para turnos USER: cómo evaluar la respuesta
    user_hint_es: Mapped[str] = mapped_column(Text, default="")       # qué se espera que responda
    user_example_en: Mapped[str] = mapped_column(Text, default="")    # respuesta modelo
    # Lista de listas: cada sublista es un grupo de keywords, al menos uno de cada grupo
    # debe aparecer en la respuesta. Ej: [["hi","hello","hey"], ["my name","i am","i'm"]]
    required_keywords: Mapped[list] = mapped_column(JSON, default=list)
    # Pistas que el frontend muestra ANTES de responder
    helper_phrases: Mapped[list] = mapped_column(JSON, default=list)

    dialogue = relationship("Dialogue", back_populates="turns")
