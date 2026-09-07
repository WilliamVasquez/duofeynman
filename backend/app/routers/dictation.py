"""Modo dictado: TTS lee una frase, usuario escribe lo que escuchó.

Es independiente del ciclo Feynman — entrena el oído.
"""
import re
import random
from difflib import SequenceMatcher
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.curriculum import Topic
from app.models.dictation import DictationExercise
from app.routers.deps import get_current_user
from app.timeutils import utcnow
from app.services import tts
from app.services.rate_limit import limiter


router = APIRouter(prefix="/api/dictation", tags=["dictation"])


# Normalización compartida: maneja apóstrofes curvos y contracciones
from app.services.text_utils import normalize as _normalize


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


@router.post("/next")
def next_sentence(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Crea un ejercicio y entrega su ID; la respuesta permanece en el servidor."""
    topics = (
        db.query(Topic)
        .filter(Topic.difficulty <= 3)
        .all()
    )
    candidates = [(t, sentence.strip()) for t in topics
                  for sentence in re.split(r"[.!?]+", t.example_en or "")
                  if 0 < len(sentence.strip()) <= 500]
    if not candidates:
        raise HTTPException(404, "No hay frases de dictado disponibles")
    topic, sentence = random.choice(candidates)
    exercise = DictationExercise(user_id=user.id, topic_id=topic.id, target=sentence)
    db.add(exercise)
    db.commit()
    db.refresh(exercise)

    return {
        "dictation_id": exercise.id,
        "topic_id": topic.id,
        "hint_es": topic.prompt_es,
        "hint_en": topic.prompt_en,
        "length_chars": len(sentence),
        "word_count": len(sentence.split()),
    }


class DictationCheckIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dictation_id: UUID
    user_input: str = Field(min_length=1, max_length=500)


def _exercise(db: Session, user: User, exercise_id: str) -> DictationExercise:
    exercise = db.get(DictationExercise, exercise_id)
    if not exercise or exercise.user_id != user.id:
        raise HTTPException(404, "Dictation not found.")
    if exercise.created_at < utcnow() - timedelta(days=1):
        raise HTTPException(410, "This dictation has expired. Start a new one.")
    return exercise


@router.get("/{exercise_id}/audio")
@limiter.limit("60/minute")
async def audio(request: Request, exercise_id: UUID, slow: bool = False,
                db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    exercise = _exercise(db, user, str(exercise_id))
    try:
        data, mime = await tts.synthesize(exercise.target, level=user.current_level,
                                          rate="-40%" if slow else None)
    except tts.TTSError as exc:
        raise HTTPException(503, "Audio unavailable. Please try again.") from exc
    return Response(content=data, media_type=mime, headers={"Cache-Control": "private, no-store"})


@router.post("/check")
def check(
    payload: DictationCheckIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Compara lo que escribió el usuario con la frase modelo."""
    exercise = _exercise(db, user, str(payload.dictation_id))
    similarity = _similarity(exercise.target, payload.user_input)
    diff = _word_diff(exercise.target, payload.user_input)
    score = round(similarity, 2)

    if score >= 0.9:
        feedback = "¡Excelente oído! 🎧"
    elif score >= 0.75:
        feedback = "Muy bien. Faltaron detalles."
    elif score >= 0.5:
        feedback = "Vas bien. Volvé a escucharlo y ajustá."
    else:
        feedback = "Difícil. Bajá la velocidad y reintentá."

    # UPDATE condicional: incluso con dos requests simultáneos solo uno premia.
    awarded = 0
    if score >= 0.85:
        awarded = db.query(DictationExercise).filter_by(id=exercise.id, rewarded=False).update(
            {"rewarded": True}, synchronize_session=False)
        if awarded:
            db.query(User).filter_by(id=user.id).update({User.total_xp: User.total_xp + 3}, synchronize_session=False)
    db.query(DictationExercise).filter(DictationExercise.id == exercise.id,
                                     DictationExercise.best_score < score).update(
        {"best_score": score}, synchronize_session=False)
    exercise.completed_at = utcnow()
    db.commit()
    db.refresh(user)

    return {
        "score": score,
        "feedback_es": feedback,
        "target": exercise.target,
        "xp_awarded": 3 if awarded else 0,
        "you_wrote": payload.user_input,
        "word_diff": diff,
    }
