"""Endpoints de Spaced Repetition System."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.services.text_utils import normalize
from app.services.srs import review_card
from app.timeutils import utcnow, learning_day
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.database import get_db
from app.models.user import User
from app.models.srs import SrsCard
from app.models.curriculum import Topic
from app.routers.deps import get_current_user


router = APIRouter(prefix="/api/srs", tags=["srs"])


@router.get("/due")
def due_cards(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Tarjetas SRS que vencen hoy o antes."""
    cards = (
        db.query(SrsCard)
        .filter(
            SrsCard.user_id == user.id,
            SrsCard.due_date <= learning_day(),
        )
        .order_by(SrsCard.due_date.asc())
        .limit(50)
        .all()
    )
    topic_ids = [c.topic_id for c in cards if c.topic_id]
    topics_map = {}
    if topic_ids:
        for t in db.query(Topic).filter(Topic.id.in_(topic_ids)).all():
            topics_map[t.id] = t

    out = []
    for c in cards:
        t = topics_map.get(c.topic_id)
        out.append({
            "id": c.id,
            "card_type": c.card_type,
            "front": c.front,
            "back": c.back if c.card_type != "ERROR_DRILL" else None,
            "due_date": c.due_date.isoformat(),
            "interval_days": c.interval_days,
            "repetitions": c.repetitions,
            "topic": {
                "id": t.id,
                "slug": t.slug,
                "prompt_es": t.prompt_es,
                "prompt_en": t.prompt_en,
                "example_en": t.example_en,
                "key_vocabulary": t.key_vocabulary,
                "connectors": t.connectors,
                "socratic_hints": t.socratic_hints,
                "difficulty": t.difficulty,
                "order_index": t.order_index,
            } if t else None,
        })
    return out


@router.get("/stats")
def stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    total = db.query(func.count(SrsCard.id)).filter_by(user_id=user.id).scalar() or 0
    due = (
        db.query(func.count(SrsCard.id))
        .filter(SrsCard.user_id == user.id, SrsCard.due_date <= learning_day())
        .scalar() or 0
    )
    mature = (
        db.query(func.count(SrsCard.id))
        .filter(SrsCard.user_id == user.id, SrsCard.interval_days >= 21)
        .scalar() or 0
    )
    return {"total": total, "due_today": due, "mature": mature}


def _drill(db, user, card_id):
    card = db.query(SrsCard).filter_by(id=card_id, user_id=user.id, card_type="ERROR_DRILL").with_for_update().first()
    if not card:
        raise HTTPException(404, "Practice card not found.")
    return card


@router.get('/drills/{card_id}')
def get_drill(card_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    card = _drill(db, user, card_id)
    return {"id": card.id, "front": card.front, "occurrences": (card.payload or {}).get('occurrences', 1)}


class DrillAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=500)


@router.post('/drills/{card_id}/check')
def check_drill(card_id: int, payload: DrillAnswer, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    card = _drill(db, user, card_id)
    correct = normalize(payload.answer) == normalize(card.back)
    # Una reprogramación por día. Reintentar tras ver la corrección sigue
    # permitido, pero no multiplica intervalos ni genera XP.
    scheduled = card.last_reviewed_at is None or learning_day(card.last_reviewed_at) < learning_day()
    if scheduled:
        review_card(card, 4 if correct else 1)
        card.last_reviewed_at = utcnow()
        card.payload = {**(card.payload or {}), "last_correct": correct}
        db.commit()
    return {"correct": correct, "answer": card.back, "explanation_es": (card.payload or {}).get('explanation_es', ''),
            "due_date": card.due_date.isoformat(), "scheduled": scheduled}
