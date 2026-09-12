"""Plan diario estable con prioridades explicables, sin un modelo generativo."""
from app.timeutils import learning_day
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.models import DailyPlan, User, UserProfile, Topic, Lesson, Module, Attempt, UserProgress, SrsCard, DialogueSession, Dialogue, ListeningAttempt
from app.routers.deps import get_current_user
from app.routers.listening import pick

router = APIRouter(prefix='/api/daily', tags=['daily'])
LEVELS = {'A1': 0, 'A2': 1, 'B1': 2}


def build_items(db, user):
    profile = db.query(UserProfile).filter_by(user_id=user.id).first()
    hidden = (profile.hidden_items or {}) if profile else {}
    excluded = set(hidden.get('topics', []))
    level = LEVELS.get(user.current_level, 0)
    rows = [(t, module_level) for t, module_level in db.query(Topic, Module.level).join(Lesson, Topic.lesson_id == Lesson.id).join(Module, Lesson.module_id == Module.id)
        .order_by(Module.order_index, Lesson.order_index, Topic.order_index).all()
        if t.slug not in excluded and module_level in LEVELS]
    mastery = {p.topic_id: p.mastery_level for p in db.query(UserProgress).filter_by(user_id=user.id).all()}
    frontier = next((LEVELS[lvl] for t, lvl in rows if mastery.get(t.id, 0) < 1), level)
    level = max(level, frontier)
    topics = [t for t, lvl in rows if LEVELS[lvl] <= level]
    available = {t.id: t for t in topics}
    items, used = [], set()

    def topic_item(topic, reason_en, reason_es, card=None):
        used.add(topic.id)
        items.append({'kind': 'topic', 'id': topic.id, 'card_id': card.id if card else None,
                      'title_en': topic.prompt_en, 'title_es': topic.prompt_es, 'reason_en': reason_en, 'reason_es': reason_es})

    due = db.query(SrsCard).filter(SrsCard.user_id == user.id, SrsCard.due_date <= learning_day()).order_by(SrsCard.due_date, SrsCard.id).all()
    due = [c for c in due if c.topic_id is None or c.topic_id in available]
    if due:
        card = due[0]
        if card.card_type == 'ERROR_DRILL':
            items.append({'kind': 'drill', 'id': card.id, 'title_en': 'Fix a recurring phrase', 'title_es': 'Corregí una frase recurrente',
                'reason_en': 'This correction is due for review.', 'reason_es': 'Esta corrección ya toca repasarla.'})
        elif card.topic_id in available:
            topic_item(available[card.topic_id], 'This topic is due for review.', 'Ya toca repasar este tema.', card)

    # Considera rondas enviadas, incluso si todavía no se dominó el tema.
    latest = {}
    for attempt in db.query(Attempt).filter(Attempt.user_id == user.id, Attempt.word_count > 0).order_by(Attempt.started_at.desc(), Attempt.id.desc()).limit(300).all():
        latest.setdefault(attempt.topic_id, attempt)
    weak = sorted((a for tid, a in latest.items() if tid in available and tid not in used and a.overall_score < .78),
                  key=lambda a: (a.overall_score, a.started_at))
    if weak:
        topic_item(available[weak[0].topic_id], 'Your recent answer needs more practice.', 'Tu respuesta reciente necesita más práctica.')
    else:
        active = db.query(DialogueSession, Dialogue).join(Dialogue, Dialogue.id == DialogueSession.dialogue_id).filter(
            DialogueSession.user_id == user.id, DialogueSession.completed_at.is_(None)).order_by(DialogueSession.updated_at.desc()).all()
        for session, dialogue in active:
            if dialogue.slug in hidden.get('dialogues', []) or LEVELS.get(dialogue.level, 99) > level or dialogue.is_adult:
                continue
            items.append({'kind': 'dialogue', 'id': dialogue.id, 'baseline_runs': session.completed_runs,
                'title_en': dialogue.title_en, 'title_es': dialogue.title_es,
                'reason_en': 'Resume your unfinished conversation.', 'reason_es': 'Retomá la conversación pendiente.'})
            break

    fresh = next((t for t in topics if t.id not in used and mastery.get(t.id, 0) < 1), None)
    if fresh:
        topic_item(fresh, 'Next topic on your learning path.', 'Próximo tema de tu camino de aprendizaje.')
    elif topics:
        review = next((t for t in topics if t.id not in used), None)
        if review:
            topic_item(review, 'Consolidate a topic you have learned.', 'Consolidá un tema que ya aprendiste.')
    listening = pick(db, user)
    items.append({'kind': 'listening', 'id': listening['slug'], 'title_en': listening['question_en'], 'title_es': listening['question_es'],
                  'reason_en': 'Practice understanding meaning from audio.', 'reason_es': 'Practicá entender el significado del audio.'})
    goal = max(5, min(45, profile.daily_goal_minutes if profile else 15))
    minutes, extra = divmod(goal, max(1, len(items)))
    for i, item in enumerate(items):
        item['minutes'] = minutes + (i < extra)
    return items


def is_done(db, user, plan, item):
    if item['kind'] == 'drill' or item.get('card_id'):
        card = db.get(SrsCard, item.get('card_id') or item['id'])
        reviewed = bool(card and card.user_id == user.id and card.last_reviewed_at and card.last_reviewed_at >= plan.created_at)
        if reviewed or item['kind'] == 'drill':
            return reviewed
    if item['kind'] == 'topic':
        attempts = db.query(Attempt).filter_by(user_id=user.id, topic_id=item['id']).filter(Attempt.word_count > 0).all()
        return any(a.started_at >= plan.created_at or any(r.get('ts', '') >= plan.created_at.isoformat() for r in (a.rounds or [])) for a in attempts)
    if item['kind'] == 'dialogue':
        session = db.query(DialogueSession).filter_by(user_id=user.id, dialogue_id=item['id']).first()
        return bool(session and session.completed_runs > item['baseline_runs'])
    return db.query(ListeningAttempt).filter(ListeningAttempt.user_id == user.id, ListeningAttempt.exercise_slug == item['id'], ListeningAttempt.completed_at >= plan.created_at).first() is not None


@router.post('/today')
def today(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plan = db.query(DailyPlan).filter_by(user_id=user.id, day=learning_day()).first()
    if not plan:
        plan = DailyPlan(user_id=user.id, day=learning_day(), items=build_items(db, user))
        db.add(plan)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            plan = db.query(DailyPlan).filter_by(user_id=user.id, day=learning_day()).one()
        db.refresh(plan)
    items = [{**item, 'done': is_done(db, user, plan, item)} for item in plan.items]
    return {'day': plan.day.isoformat(), 'items': items, 'completed': sum(i['done'] for i in items),
            'total': len(items), 'minutes': sum(i['minutes'] for i in items)}
