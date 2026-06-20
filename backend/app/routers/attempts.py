"""Núcleo del producto: ciclo Feynman (modo hablar o escribir)."""
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.curriculum import Topic
from app.models.attempt import Attempt, AttemptError
from app.models.progress import UserProgress
from app.models.srs import SrsCard
from app.schemas.attempt import (
    AttemptStartIn, AttemptRoundIn, AttemptOut, FeedbackOut, ErrorOut
)
from app.routers.deps import get_current_user
from app.services import feynman_engine
from app.services import vosk_stt
from app.services import srs as srs_service
from app.services import gamification
from app.services.rate_limit import limiter
from fastapi import Request


router = APIRouter(prefix="/api/attempts", tags=["attempts"])


@router.post("/start", response_model=AttemptOut)
def start_attempt(
    payload: AttemptStartIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    topic = db.get(Topic, payload.topic_id)
    if not topic:
        raise HTTPException(404, "Topic no encontrado")

    # Cerrar intentos huérfanos previos del mismo topic (si los hay)
    db.query(Attempt).filter(
        Attempt.user_id == user.id,
        Attempt.topic_id == topic.id,
        Attempt.completed_at.is_(None),
    ).update({"completed_at": datetime.utcnow(), "stage": "ABANDONED"})

    attempt = Attempt(user_id=user.id, topic_id=topic.id, stage="EXPLAIN")
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return AttemptOut.model_validate(attempt)


@router.post("/round", response_model=FeedbackOut)
async def submit_round(
    payload: AttemptRoundIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    attempt = db.get(Attempt, payload.attempt_id)
    if not attempt or attempt.user_id != user.id:
        raise HTTPException(404, "Intento no encontrado")
    if attempt.completed_at:
        raise HTTPException(400, "Intento ya cerrado")

    topic = db.get(Topic, attempt.topic_id)

    result = await feynman_engine.evaluate_round(
        topic, payload.transcript, payload.duration_seconds, mode=payload.mode
    )

    rounds = list(attempt.rounds or [])
    rounds.append({
        "mode": payload.mode,
        "transcript": payload.transcript,
        "duration_seconds": payload.duration_seconds,
        "score": result["overall_score"],
        "feedback_es": result["encouragement_es"],
        "next_action": result["next_action"],
        "ts": datetime.utcnow().isoformat(),
    })
    attempt.rounds = rounds
    attempt.overall_score = result["overall_score"]
    attempt.fluency_score = result["fluency_score"]
    attempt.code_switch_rate = result["code_switch_rate"]
    attempt.self_correction_rate = result.get("self_correction_rate", 0.0)
    attempt.error_density = result["error_density"]
    attempt.word_count = result["word_count"]
    attempt.duration_seconds = (attempt.duration_seconds or 0) + payload.duration_seconds

    db.query(AttemptError).filter(AttemptError.attempt_id == attempt.id).delete()
    for e in result["errors"][:30]:
        db.add(AttemptError(
            attempt_id=attempt.id,
            category=e["category"],
            rule_id=e.get("rule_id"),
            span_text=e["span_text"],
            suggestion=e["suggestion"],
            explanation_es=e["explanation_es"],
            severity=e.get("severity", 1),
        ))

    unlocked: list[dict] = []
    if result["next_action"] == "MASTERED":
        attempt.stage = "DONE"
        attempt.mastered = True
        attempt.completed_at = datetime.utcnow()

        progress = (
            db.query(UserProgress)
            .filter_by(user_id=user.id, topic_id=topic.id)
            .first()
        )
        if not progress:
            progress = UserProgress(user_id=user.id, topic_id=topic.id)
            db.add(progress)
        progress.attempts_count += 1
        progress.last_score = result["overall_score"]
        progress.best_score = max(progress.best_score, result["overall_score"])
        progress.mastery_level = min(5, progress.mastery_level + 1)
        progress.last_practiced_at = datetime.utcnow()

        user.total_xp += 10

        # SRS: actualizar card existente o crear nueva
        existing = (
            db.query(SrsCard)
            .filter_by(user_id=user.id, topic_id=topic.id, card_type="TOPIC")
            .first()
        )
        if existing:
            quality = srs_service.score_to_quality(result["overall_score"])
            srs_service.review_card(existing, quality)
            existing.last_reviewed_at = datetime.utcnow()
            existing.payload = {**(existing.payload or {}), "last_transcript": payload.transcript, "mode": payload.mode}
        else:
            db.add(SrsCard(
                user_id=user.id,
                topic_id=topic.id,
                card_type="TOPIC",
                front=topic.prompt_en,
                back=topic.example_en,
                payload={"last_transcript": payload.transcript, "mode": payload.mode},
                due_date=date.today(),
            ))

        # Actualizar racha y otorgar logros
        gamification.update_streak(db, user)
        unlocked = gamification.award_achievements(db, user, attempt)
    else:
        attempt.stage = "REFINE" if result["next_action"] == "REFINE" else "EXPLAIN"

    db.commit()
    db.refresh(attempt)

    return FeedbackOut(
        overall_score=result["overall_score"],
        fluency_score=result["fluency_score"],
        code_switch_rate=result["code_switch_rate"],
        self_correction_rate=result.get("self_correction_rate", 0.0),
        error_density=result["error_density"],
        word_count=result["word_count"],
        vocab_coverage=result["vocab_coverage"],
        connector_coverage=result["connector_coverage"],
        subscores=result.get("subscores", {}),
        lexical_diversity=result.get("lexical_diversity", 0.0),
        sentence_count=result.get("sentence_count", 0),
        tenses_used=result.get("tenses_used", []),
        errors=[ErrorOut.model_validate(e) for e in attempt.errors],
        socratic_questions=result["socratic_questions"],
        encouragement_es=result["encouragement_es"],
        next_action=result["next_action"],
        model_answer_en=result.get("model_answer_en"),
        unlocked_achievements=unlocked,
    )


@router.post("/transcribe")
@limiter.limit("20/minute")
async def transcribe_audio(
    request: Request,
    file: UploadFile = File(...),
    _user: User = Depends(get_current_user),
):
    audio = await file.read()
    if len(audio) > 10 * 1024 * 1024:
        raise HTTPException(413, "Audio demasiado grande (máx 10MB)")
    try:
        # Vosk es síncrono y puede tardar segundos: correrlo en threadpool
        # para no bloquear el event loop del resto de los requests.
        text = await run_in_threadpool(vosk_stt.transcribe, audio)
    except vosk_stt.STTUnavailable as e:
        raise HTTPException(503, str(e))
    return {"transcript": text}


@router.get("/stt-status")
def stt_status(_user: User = Depends(get_current_user)):
    return vosk_stt.diagnose()
