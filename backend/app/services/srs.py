"""Algoritmo de repetición espaciada (SM-2 simplificado).

Calidad de respuesta (q):
  0 = totalmente fallado     → reset
  3 = correcto pero costoso  → mantener intervalo
  4 = correcto fluido         → avanzar
  5 = perfecto                → avanzar más rápido
"""
from datetime import date, timedelta

from app.models.srs import SrsCard


def review_card(card: SrsCard, quality: int) -> SrsCard:
    quality = max(0, min(5, quality))

    if quality < 3:
        card.repetitions = 0
        card.interval_days = 1
    else:
        if card.repetitions == 0:
            card.interval_days = 1
        elif card.repetitions == 1:
            card.interval_days = 3
        else:
            card.interval_days = round(card.interval_days * card.ease_factor)
        card.repetitions += 1

    card.ease_factor = max(
        1.3,
        card.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
    )
    card.due_date = date.today() + timedelta(days=card.interval_days)
    return card


def score_to_quality(overall_score: float) -> int:
    """Mapea score 0-1 a calidad SM-2 0-5."""
    if overall_score >= 0.9:
        return 5
    if overall_score >= 0.75:
        return 4
    if overall_score >= 0.6:
        return 3
    if overall_score >= 0.4:
        return 2
    return 1
