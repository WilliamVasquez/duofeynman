from datetime import date, timedelta, datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import get_db
from app.models.user import User
from app.models.attempt import Attempt, AttemptError
from app.models.curriculum import Topic
from app.models.progress import UserProgress, Achievement, UserAchievement
from app.models.srs import SrsCard
from app.routers.deps import get_current_user


router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("/summary")
def summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    total_attempts = db.query(func.count(Attempt.id)).filter_by(user_id=user.id).scalar() or 0
    mastered = (
        db.query(func.count(UserProgress.id))
        .filter(UserProgress.user_id == user.id, UserProgress.mastery_level >= 3)
        .scalar() or 0
    )
    avg_score = (
        db.query(func.avg(Attempt.overall_score))
        .filter(Attempt.user_id == user.id, Attempt.completed_at.isnot(None))
        .scalar()
    )
    due_cards = (
        db.query(func.count(SrsCard.id))
        .filter(SrsCard.user_id == user.id, SrsCard.due_date <= date.today())
        .scalar() or 0
    )
    return {
        "username": user.username,
        "current_level": user.current_level,
        "target_level": user.target_level,
        "streak_days": user.streak_days,
        "total_xp": user.total_xp,
        "total_attempts": total_attempts,
        "mastered_topics": mastered,
        "average_score": round(float(avg_score or 0), 2),
        "due_srs_cards": due_cards,
    }


@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Datos para el dashboard del usuario.

    Incluye: resumen, gráfico de últimos 7 días, logros desbloqueados/pendientes.
    """
    summary_data = summary(db, user)

    # Últimos 7 días: agrupar por fecha
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    daily_rows = (
        db.query(
            func.date(Attempt.completed_at).label("d"),
            func.avg(Attempt.fluency_score).label("fluency"),
            func.avg(Attempt.overall_score).label("score"),
            func.count(Attempt.id).label("count"),
        )
        .filter(
            Attempt.user_id == user.id,
            Attempt.completed_at.isnot(None),
            Attempt.completed_at >= seven_days_ago,
        )
        .group_by(func.date(Attempt.completed_at))
        .all()
    )
    daily_map = {}
    for r in daily_rows:
        d = r.d
        if hasattr(d, "isoformat"):
            d = d.isoformat()
        daily_map[str(d)] = {
            "fluency": round(float(r.fluency or 0), 2),
            "score": round(float(r.score or 0), 2),
            "count": int(r.count or 0),
        }

    # Generar 7 días continuos (incluso si no hay datos)
    last_7_days = []
    for i in range(6, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        info = daily_map.get(d, {"fluency": 0, "score": 0, "count": 0})
        last_7_days.append({"date": d, **info})

    # Logros desbloqueados y pendientes
    unlocked_q = (
        db.query(Achievement, UserAchievement.unlocked_at)
        .join(UserAchievement, UserAchievement.achievement_id == Achievement.id)
        .filter(UserAchievement.user_id == user.id)
        .all()
    )
    unlocked_codes = {a.code for a, _ in unlocked_q}
    unlocked_list = [
        {
            "code": a.code,
            "title_es": a.title_es,
            "description_es": a.description_es,
            "icon": a.icon,
            "xp": a.xp_reward,
            "unlocked_at": ts.isoformat() if ts else None,
        }
        for a, ts in unlocked_q
    ]
    pending = (
        db.query(Achievement)
        .filter(~Achievement.code.in_(unlocked_codes) if unlocked_codes else True)
        .all()
    )
    pending_list = [
        {
            "code": a.code,
            "title_es": a.title_es,
            "description_es": a.description_es,
            "icon": a.icon,
            "xp": a.xp_reward,
        }
        for a in pending
    ]

    return {
        "summary": summary_data,
        "last_7_days": last_7_days,
        "achievements_unlocked": unlocked_list,
        "achievements_pending": pending_list,
    }


@router.get("/insights")
def insights(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Insights pedagógicos: qué te cuesta más, qué dominás, qué practicar.

    Útil para el dashboard: el usuario ve patrones reales de su aprendizaje.
    """
    # 1. Errores más frecuentes por categoría
    error_categories = (
        db.query(AttemptError.category, func.count(AttemptError.id).label("count"))
        .join(Attempt, Attempt.id == AttemptError.attempt_id)
        .filter(Attempt.user_id == user.id)
        .group_by(AttemptError.category)
        .order_by(desc("count"))
        .all()
    )
    by_category = [{"category": c, "count": int(n)} for c, n in error_categories]

    # 2. Palabras más frecuentes en code-switching (las que más decís en español)
    cs_words = (
        db.query(AttemptError.span_text, func.count(AttemptError.id).label("count"))
        .join(Attempt, Attempt.id == AttemptError.attempt_id)
        .filter(
            Attempt.user_id == user.id,
            AttemptError.category == "CODE_SWITCH",
        )
        .group_by(AttemptError.span_text)
        .order_by(desc("count"))
        .limit(10)
        .all()
    )
    spanish_leaks = [{"word": w, "count": int(n)} for w, n in cs_words]

    # 3. Errores gramaticales recurrentes (mismo span_text)
    grammar_recurring = (
        db.query(AttemptError.span_text, AttemptError.suggestion, func.count(AttemptError.id).label("count"))
        .join(Attempt, Attempt.id == AttemptError.attempt_id)
        .filter(
            Attempt.user_id == user.id,
            AttemptError.category.in_(["GRAMMAR", "AI_CORRECTION"]),
        )
        .group_by(AttemptError.span_text, AttemptError.suggestion)
        .order_by(desc("count"))
        .limit(10)
        .all()
    )
    grammar_drills = [
        {"wrong": w, "fix": s, "count": int(n)}
        for w, s, n in grammar_recurring if int(n) >= 2
    ]

    # 4. Temas con menor score promedio (zonas débiles)
    weak_topics = (
        db.query(
            Topic.id, Topic.prompt_es, Topic.slug,
            func.avg(Attempt.overall_score).label("avg_score"),
            func.count(Attempt.id).label("attempts"),
        )
        .join(Attempt, Attempt.topic_id == Topic.id)
        .filter(Attempt.user_id == user.id, Attempt.completed_at.isnot(None))
        .group_by(Topic.id, Topic.prompt_es, Topic.slug)
        .having(func.count(Attempt.id) >= 1)
        .order_by("avg_score")
        .limit(5)
        .all()
    )
    weak_list = [
        {
            "topic_id": int(tid), "slug": s, "prompt_es": p,
            "avg_score": round(float(a or 0), 2),
            "attempts": int(c),
        }
        for tid, p, s, a, c in weak_topics
    ]

    # 5. Temas dominados rápido (1-2 intentos)
    fast_mastered = (
        db.query(Topic.prompt_es, UserProgress.attempts_count, UserProgress.best_score)
        .join(UserProgress, UserProgress.topic_id == Topic.id)
        .filter(
            UserProgress.user_id == user.id,
            UserProgress.mastery_level >= 3,
            UserProgress.attempts_count <= 2,
        )
        .order_by(desc(UserProgress.best_score))
        .limit(5)
        .all()
    )
    fast_list = [
        {"prompt_es": p, "attempts": int(a), "best_score": round(float(s or 0), 2)}
        for p, a, s in fast_mastered
    ]

    # 6. Promedios globales: fluidez, code-switch, vocab coverage (últimos 20)
    recent_avg = (
        db.query(
            func.avg(Attempt.fluency_score).label("fluency"),
            func.avg(Attempt.code_switch_rate).label("cs"),
            func.avg(Attempt.overall_score).label("score"),
            func.avg(Attempt.word_count).label("words"),
        )
        .filter(Attempt.user_id == user.id, Attempt.completed_at.isnot(None))
        .first()
    )
    averages = {
        "fluency": round(float(recent_avg.fluency or 0), 2),
        "code_switch_rate": round(float(recent_avg.cs or 0), 2),
        "score": round(float(recent_avg.score or 0), 2),
        "avg_words_per_attempt": round(float(recent_avg.words or 0), 1),
    }

    return {
        "averages": averages,
        "errors_by_category": by_category,
        "spanish_leaks": spanish_leaks,
        "grammar_drills": grammar_drills,
        "weak_topics": weak_list,
        "fast_mastered": fast_list,
    }
