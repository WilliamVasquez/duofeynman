"""Utilidades de tiempo.

datetime.utcnow() está deprecado desde Python 3.12. Las columnas de MySQL son
DATETIME naive, así que devolvemos UTC naive para mantener la misma semántica
que utcnow() sin el warning (y sin romper comparaciones naive vs aware).
"""
from datetime import datetime, timezone, timedelta, time


def utcnow() -> datetime:
    """UTC actual como datetime naive (equivalente moderno de datetime.utcnow())."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def learning_day(value: datetime | None = None):
    """Día pedagógico de El Salvador (UTC-6, sin cambio estacional)."""
    return ((value if value is not None else utcnow()) - timedelta(hours=6)).date()


def learning_day_start(day=None):
    """Inicio del día pedagógico expresado como UTC naive para la BD."""
    return datetime.combine(day or learning_day(), time(6))
