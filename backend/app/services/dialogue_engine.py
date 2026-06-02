"""Motor de validación de respuestas en diálogos guionados.

Rule-based, sin IA. Por turno verifica:
- Cobertura de keywords requeridos (al menos uno de cada grupo)
- Similitud con la respuesta modelo (orientativa)
- Sin code-switching pesado al español
- Longitud mínima

Devuelve score 0-1, feedback en español, y si "aprobó" para avanzar.
"""
from __future__ import annotations
import re
from difflib import SequenceMatcher

from app.services.analyzer import detect_code_switching


def _normalize(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s']", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _keyword_coverage(text_norm: str, groups: list) -> tuple[float, list[list[str]]]:
    """Devuelve (cobertura, grupos_no_cubiertos).

    `groups` es una lista de listas. Cada sublista es un grupo OR:
    al menos UNO de los términos debe aparecer en el texto.
    """
    if not groups:
        return 1.0, []
    covered = 0
    missing: list[list[str]] = []
    for grp in groups:
        if not grp:
            covered += 1
            continue
        if any(_normalize(k) in text_norm for k in grp):
            covered += 1
        else:
            missing.append(grp)
    return covered / len(groups), missing


def evaluate_turn(
    user_text: str,
    required_keywords: list,
    user_example_en: str,
) -> dict:
    """Evalúa una respuesta de usuario en un diálogo.

    Devuelve dict con: score, passed, feedback_es, missing_groups,
    code_switch_words, similarity.
    """
    text = user_text.strip()
    norm = _normalize(text)

    if not norm:
        return {
            "score": 0.0, "passed": False, "similarity": 0.0,
            "feedback_es": "No dijiste nada. Probá de nuevo.",
            "missing_groups": required_keywords, "code_switch_words": [],
        }

    # Keywords
    kw_coverage, missing = _keyword_coverage(norm, required_keywords or [])
    # Similitud
    similarity = SequenceMatcher(None, norm, _normalize(user_example_en)).ratio() if user_example_en else 0.5
    # Code-switch
    cs_rate, cs_words = detect_code_switching(text)
    # Longitud
    word_count = len(norm.split())
    length_ok = word_count >= 2

    # Score combinado
    score = (
        kw_coverage * 0.5
        + min(similarity, 1.0) * 0.25
        + (1 - min(cs_rate, 1)) * 0.15
        + (1.0 if length_ok else 0.3) * 0.10
    )
    score = round(max(0.0, min(1.0, score)), 2)

    # Decisión: avanza si el score es bueno, aunque falte 1 grupo no crítico.
    # Reglas (cualquiera califica):
    #   - score >= 0.75 (claramente bien, dejá pasar)
    #   - score >= 0.55 y no falta nada
    #   - score >= 0.6 y falta solo 1 grupo (cubriste lo importante)
    total_groups = max(1, len(required_keywords or []))
    missing_count = len(missing)
    passed = (
        score >= 0.75
        or (score >= 0.55 and missing_count == 0)
        or (score >= 0.6 and missing_count <= 1 and total_groups >= 2)
    )

    # Feedback en español: si pasó, mensaje positivo; si no, decir qué falta.
    if passed:
        if cs_words:
            feedback = f"Pasa, pero ojo: dijiste «{', '.join(cs_words[:3])}» en español."
        elif missing:
            hints = " · ".join(grp[0] for grp in missing[:2])
            feedback = f"¡Bien! Sumá esto para sonar aún más natural: {hints}."
        elif score >= 0.9:
            feedback = "¡Perfecto! Sonó muy natural. 🎉"
        elif score >= 0.75:
            feedback = "Muy bien, podemos avanzar."
        else:
            feedback = "Aceptable, sigamos."
    else:
        if cs_words:
            feedback = f"Te trabaste con español: «{', '.join(cs_words[:3])}». Probá en inglés."
        elif missing:
            hints = " · ".join(grp[0] for grp in missing[:3])
            feedback = f"Faltó algo importante. Usá: {hints}"
        elif word_count < 3:
            feedback = "Muy cortito. Probá con una oración un poco más larga."
        else:
            feedback = "Probá de nuevo. Mirá las pistas y la respuesta modelo."

    return {
        "score": score,
        "passed": passed,
        "similarity": round(similarity, 2),
        "feedback_es": feedback,
        "missing_groups": missing,
        "code_switch_words": cs_words,
        "word_count": word_count,
    }
