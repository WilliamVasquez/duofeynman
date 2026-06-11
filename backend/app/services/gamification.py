"""Lógica de gamificación: racha y logros."""
from __future__ import annotations
import logging
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user import User
from app.models.attempt import Attempt
from app.models.progress import Achievement, UserAchievement


log = logging.getLogger(__name__)


def update_streak(db: Session, user: User) -> int:
    """Recalcula la racha de días consecutivos practicados.

    Llamar después de completar un intento (el intento de hoy ya tiene
    completed_at, así que hoy siempre cuenta). La racha se recalcula
    completa desde el historial: es idempotente, no depende del valor
    anterior de streak_days.
    """
    # Fechas distintas con práctica, más recientes primero.
    # 400 días alcanza para cualquier racha humanamente posible.
    rows = (
        db.query(func.date(Attempt.completed_at))
        .filter(Attempt.user_id == user.id, Attempt.completed_at.isnot(None))
        .distinct()
        .order_by(func.date(Attempt.completed_at).desc())
        .limit(400)
        .all()
    )
    dates = []
    for (d,) in rows:
        if d is None:
            continue
        if isinstance(d, str):
            d = datetime.strptime(d, "%Y-%m-%d").date()
        dates.append(d)
    dates = sorted(set(dates), reverse=True)

    today = date.today()
    if not dates:
        user.streak_days = 1
        return user.streak_days

    # Contar días consecutivos hacia atrás. La racha sigue viva si la
    # última práctica fue hoy o ayer (ayer = todavía no la perdió).
    expected = today if dates[0] == today else today - timedelta(days=1)
    streak = 0
    for d in dates:
        if d == expected:
            streak += 1
            expected -= timedelta(days=1)
        elif d < expected:
            break

    user.streak_days = max(streak, 1)
    return user.streak_days


# Cada chequeo recibe (db, user, attempt) y devuelve True si desbloquea.
ACHIEVEMENT_CHECKS = {
    "first_steps":    lambda db, u, a: a.completed_at is not None,
    "first_mastered": lambda db, u, a: bool(a.mastered),
    "no_spanish":     lambda db, u, a: bool(a.mastered) and a.code_switch_rate == 0,
    "streak_7":       lambda db, u, a: u.streak_days >= 7,
    "fluent_minute":  lambda db, u, a: a.fluency_score >= 0.6 and a.duration_seconds >= 60,
}


def award_achievements(db: Session, user: User, attempt: Attempt) -> list[dict]:
    """Otorga todos los logros que el usuario acaba de cumplir.

    Devuelve la lista de logros recién desbloqueados (para mostrar en el front).
    """
    unlocked: list[dict] = []
    for code, check in ACHIEVEMENT_CHECKS.items():
        try:
            if not check(db, user, attempt):
                continue
        except Exception:
            log.exception("Error chequeando logro %s", code)
            continue

        ach = db.query(Achievement).filter_by(code=code).first()
        if not ach:
            continue
        already = (
            db.query(UserAchievement)
            .filter_by(user_id=user.id, achievement_id=ach.id)
            .first()
        )
        if already:
            continue

        db.add(UserAchievement(user_id=user.id, achievement_id=ach.id))
        user.total_xp += ach.xp_reward
        unlocked.append({
            "code": ach.code,
            "title_es": ach.title_es,
            "description_es": ach.description_es,
            "icon": ach.icon,
            "xp": ach.xp_reward,
        })
        log.info("Usuario %s desbloqueó logro %s (+%d XP)", user.username, code, ach.xp_reward)
    return unlocked
