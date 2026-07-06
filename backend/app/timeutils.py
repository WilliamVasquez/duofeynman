"""Utilidades de tiempo.

datetime.utcnow() está deprecado desde Python 3.12. Las columnas de MySQL son
DATETIME naive, así que devolvemos UTC naive para mantener la misma semántica
que utcnow() sin el warning (y sin romper comparaciones naive vs aware).
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """UTC actual como datetime naive (equivalente moderno de datetime.utcnow())."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
