"""Lógica de gamificación: racha y logros."""
from __future__ import annotations
import logging
from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user import User
from app.models.attempt import Attempt
from app.models.progress import Achievement, UserAchievement


log = logging.getLogger(__name__)


def update_streak(db: Session, user: User) -> int:
    """Recalcula la racha de días consecutivos practicados.

    Llamar después de completar un intento. Devuelve la nueva racha.
    """
    # Última fecha en que cerró un intento, EXCLUYENDO la sesión actual.
    rows = (
        db.query(func.date(Attempt.completed_at))
        .filter(Attempt.user_id == user.id, Attempt.completed_at.isnot(None))
        .order_by(Attempt.completed_at.desc())
        .limit(5)
        .all()
    )
    dates = sorted({r[0] for r in rows if r[0]}, reverse=True)
    today = date.today()

    if not dates:
        user.streak_days = 1
        return user.streak_days

    last = dates[0]
    if isinstance(last, str):
        from datetime import datetime as _dt
        last = _dt.strptime(last, "%Y-%m-%d").date()

    delta = (today - last).days
    if delta == 0:
        # Hoy ya practicó — la racha no cambia.
        if user.streak_days < 1:
            user.streak_days = 1
        # Pero verificar si las fechas previas son consecutivas
        # (por si es la primera vez que entra a esta función)
        if user.streak_days <= 1:
            user.streak_days = _count_consecutive_days(dates)
    elif delta == 1:
        user.streak_days += 1
    else:
        user.streak_days = 1

    return user.streak_days


def _count_consecutive_days(dates: list) -> int:
    """Cuenta días consecutivos hacia atrás desde hoy."""
    if not dates:
        return 0
    today = date.today()
    streak = 0
    expected = today
    for d in dates:
        from datetime import datetime as _dt
        if isinstance(d, str):
            d = _dt.strptime(d, "%Y-%m-%d").date()
        if d == expected:
            streak += 1
            from datetime import timedelta
            expected = expected - timedelta(days=1)
        elif d < expected:
            break
    return max(streak, 1)


# Cada chequeo recibe (db, user, attempt) y devuelve True si desbloquea.
ACHIEVEMENT_CHECKS = {
    "first_steps":    lambda db, u, a: True,
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
