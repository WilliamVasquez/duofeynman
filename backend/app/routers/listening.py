"""Comprensión auditiva editorial: ninguna respuesta correcta llega antes de corregir."""
import json
from pathlib import Path
from uuid import UUID
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ListeningAttempt, User
from app.routers.deps import get_current_user
from app.services import tts
from app.services.rate_limit import limiter
from app.timeutils import utcnow

EXERCISES = json.loads((Path(__file__).parents[1] / 'data/curriculum/listening.json').read_text(encoding='utf-8'))
BY_SLUG = {e['slug']: e for e in EXERCISES}
router = APIRouter(prefix='/api/listening', tags=['listening'])


class StartIn(BaseModel):
    slug: str | None = Field(default=None, max_length=100)


def pick(db, user):
    attempts = db.query(ListeningAttempt).filter_by(user_id=user.id).order_by(ListeningAttempt.created_at.desc()).all()
    latest, completed = {}, {}
    for a in attempts:
        if a.exercise_slug not in latest:
            latest[a.exercise_slug] = a
        if a.completed_at and a.exercise_slug not in completed:
            completed[a.exercise_slug] = a
    levels = ['A1', 'A2', 'B1']
    level = levels.index(user.current_level) if user.current_level in levels else 0
    # Tres audios distintos correctos sin texto permiten subir un nivel.
    while level < 2:
        mastered = sum(a.score == 1 and not a.revealed and a.completed_at is not None
            for slug, a in completed.items() if BY_SLUG[slug]['level'] == levels[level])
        if mastered < 3:
            break
        level += 1
    eligible = [e for e in EXERCISES if e['level'] == levels[level]]
    # Primero no vistos, luego respuestas incorrectas/con ayuda y después las más antiguas.
    return min(eligible, key=lambda e: (e['slug'] in latest,
        latest[e['slug']].score if e['slug'] in latest and not latest[e['slug']].revealed else 0,
        latest[e['slug']].created_at if e['slug'] in latest else utcnow()))


def owned(db, user, attempt_id):
    a = db.query(ListeningAttempt).filter_by(id=str(attempt_id), user_id=user.id).with_for_update().first()
    if not a:
        raise HTTPException(404, 'Listening exercise not found.')
    if a.created_at < utcnow() - timedelta(days=1):
        raise HTTPException(410, 'This exercise has expired. Start a new one.')
    return a, BY_SLUG[a.exercise_slug]


@router.post('/next')
def next_exercise(payload: StartIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    exercise = BY_SLUG.get(payload.slug) if payload.slug else pick(db, user)
    if not exercise:
        raise HTTPException(404, 'Listening exercise not found.')
    a = ListeningAttempt(user_id=user.id, exercise_slug=exercise['slug'])
    db.add(a); db.commit(); db.refresh(a)
    return {'id': a.id, **{k: exercise[k] for k in ('slug', 'level', 'question_en', 'question_es', 'options')}}


@router.get('/{attempt_id}/audio')
@limiter.limit('60/minute')
async def audio(request: Request, attempt_id: UUID, slow: bool = False, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    a, e = owned(db, user, attempt_id)
    try:
        data, mime = await tts.synthesize(e['audio_en'], level=e['level'], rate='-40%' if slow else None)
    except tts.TTSError as exc:
        raise HTTPException(503, 'Audio unavailable. Try again or reveal the text for guided practice.') from exc
    a.heard = True
    db.commit()
    return Response(data, media_type=mime, headers={'Cache-Control': 'private, no-store'})


@router.post('/{attempt_id}/reveal')
def reveal(attempt_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    a, e = owned(db, user, attempt_id)
    if not a.completed_at:
        a.revealed = True
        db.commit()
    return {k: e[k] for k in ('audio_en', 'audio_es')}


class AnswerIn(BaseModel):
    choice: int = Field(ge=0, le=2)


@router.post('/{attempt_id}/check')
def check(attempt_id: UUID, payload: AnswerIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    a, e = owned(db, user, attempt_id)
    if not a.heard and not a.revealed:
        raise HTTPException(409, 'Listen first, or reveal the text for guided practice.')
    if not a.completed_at:
        a.choice = payload.choice
        a.score = float(payload.choice == e['correct'])
        a.completed_at = utcnow()
        db.commit()
    return {'score': a.score, 'choice': a.choice, 'assisted': a.revealed,
        **{k: e[k] for k in ('correct', 'audio_en', 'audio_es', 'explanation_en', 'explanation_es')}}
