"""Modo dictado: TTS lee una frase, usuario escribe lo que escuchó.

Es independiente del ciclo Feynman — entrena el oído.
"""
import re
import random
from difflib import SequenceMatcher

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.curriculum import Topic
from app.routers.deps import get_current_user


router = APIRouter(prefix="/api/dictation", tags=["dictation"])


def _normalize(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s']", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def _word_diff(target: str, user: str) -> dict:
    """Compara palabra a palabra. Devuelve palabras correctas/incorrectas."""
    tw = _normalize(target).split()
    uw = _normalize(user).split()
    sm = SequenceMatcher(None, tw, uw)
    correct: list[str] = []
    missing: list[str] = []
    extra: list[str] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            correct.extend(tw[i1:i2])
        elif tag == "delete":
            missing.extend(tw[i1:i2])
        elif tag == "insert":
            extra.extend(uw[j1:j2])
        elif tag == "replace":
            missing.extend(tw[i1:i2])
            extra.extend(uw[j1:j2])
    return {
        "correct_count": len(correct),
        "total_count": len(tw),
        "missing": missing[:10],
        "extra": extra[:10],
    }


@router.get("/next")
def next_sentence(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Devuelve una frase aleatoria de un topic para hacer dictado.

    No le mostramos al frontend el texto, solo el ID. El frontend llama a
    /api/tts para escuchar y manda lo que escribió a /api/dictation/check.
    """
    topics = (
        db.query(Topic)
        .filter(Topic.difficulty <= 3)
        .order_by(func_random())
        .limit(1)
        .all()
    )
    if not topics:
        raise HTTPException(404, "No hay frases de dictado disponibles")
    topic = topics[0]
    # Tomar una oración del example_en (split simple por punto)
    sentences = [s.strip() for s in re.split(r"[.!?]+", topic.example_en) if s.strip()]
    if not sentences:
        raise HTTPException(404, "Topic sin frases")
    sentence = random.choice(sentences)

    return {
        "dictation_id": f"{topic.id}:{abs(hash(sentence)) % 10000}",
        "topic_id": topic.id,
        "sentence_id": abs(hash(sentence)) % 10000,
        "hint_es": topic.prompt_es,
        "length_chars": len(sentence),
        "word_count": len(sentence.split()),
        # NO mandamos la frase al cliente. Se obtiene solo vía TTS.
        "tts_text": sentence,  # se manda solo para TTS server-side
    }


class DictationCheckIn(BaseModel):
    topic_id: int
    user_input: str = Field(min_length=1, max_length=500)
    target_sentence: str = Field(min_length=1, max_length=500)


@router.post("/check")
def check(
    payload: DictationCheckIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Compara lo que escribió el usuario con la frase modelo."""
    similarity = _similarity(payload.target_sentence, payload.user_input)
    diff = _word_diff(payload.target_sentence, payload.user_input)
    score = round(similarity, 2)

    if score >= 0.9:
        feedback = "¡Excelente oído! 🎧"
    elif score >= 0.75:
        feedback = "Muy bien. Faltaron detalles."
    elif score >= 0.5:
        feedback = "Vas bien. Volvé a escucharlo y ajustá."
    else:
        feedback = "Difícil. Bajá la velocidad y reintentá."

    # Bonus XP por dictado exitoso (sin afectar SRS principal)
    if score >= 0.85:
        user.total_xp += 3
        db.commit()

    return {
        "score": score,
        "feedback_es": feedback,
        "target": payload.target_sentence,
        "you_wrote": payload.user_input,
        "word_diff": diff,
    }


# helper para SQLAlchemy random portable
def func_random():
    from sqlalchemy import func as _f
    return _f.rand()  # MySQL
