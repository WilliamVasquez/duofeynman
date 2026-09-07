"""Motor de validación de respuestas en diálogos guionados.

Rule-based, sin IA. Filosofía (post-rediseño):

El motor NO es un examen: es un guía. Nunca puede rechazar algo que la app
misma sugirió, y nunca puede dejar al usuario trabado sin saber qué decir.
Por eso:

1. `accepted_answers` (respuesta modelo + answer_options + helper_phrases)
   son SIEMPRE válidas. Si el usuario dice cualquiera de ellas → pasa.
2. La similitud se mide contra la MEJOR de todas las respuestas aceptadas,
   no solo contra `user_example_en`. Así una respuesta válida distinta a la
   modelo no muere.
3. `required_keywords` es un BONUS (peso 0.30), no una compuerta. Antes
   pesaba 0.50 y bloqueaba: 316 de 599 helper_phrases del propio curriculum
   se rechazaban a sí mismas.
4. Si igual no pasa, `can_continue` = True: el frontend ofrece avanzar.
   Nadie se queda encerrado en un turno.
"""
from __future__ import annotations
from difflib import SequenceMatcher

from app.services.analyzer import detect_code_switching
from app.services.text_utils import normalize as _normalize, matches_term


# Umbral para considerar que el usuario "dijo" una de las respuestas aceptadas.
# 0.90 tolera typos y puntuación pero no acepta una frase distinta.
_MATCH_THRESHOLD = 0.90


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
        if any(matches_term(text_norm, k) for k in grp):
            covered += 1
        else:
            missing.append(grp)
    return covered / len(groups), missing


def _best_similarity(norm: str, candidates: list[str]) -> tuple[float, str]:
    """Similitud contra la mejor respuesta aceptada. Devuelve (ratio, cual)."""
    best, best_text = 0.0, ""
    for cand in candidates:
        cand_norm = _normalize(cand or "")
        if not cand_norm:
            continue
        ratio = SequenceMatcher(None, norm, cand_norm).ratio()
        if ratio > best:
            best, best_text = ratio, cand
    return best, best_text


def evaluate_turn(
    user_text: str,
    required_keywords: list,
    user_example_en: str,
    accepted_answers: list[str] | None = None,
) -> dict:
    """Evalúa una respuesta de usuario en un diálogo.

    `accepted_answers`: todas las respuestas que la app considera válidas para
    este turno (respuesta modelo + opciones + helper_phrases). Si el usuario
    dice cualquiera de ellas, pasa sí o sí.

    Devuelve dict con: score, passed, can_continue, feedback_es,
    missing_groups, code_switch_words, similarity.
    """
    text = user_text.strip()
    norm = _normalize(text)

    # Candidatos de similitud: siempre incluye la respuesta modelo.
    candidates = [c for c in [user_example_en, *(accepted_answers or [])] if c and c.strip()]

    if not norm:
        return {
            "score": 0.0, "passed": False, "can_continue": False, "similarity": 0.0,
            "feedback_es": "No dijiste nada. Probá de nuevo.",
            "missing_groups": required_keywords, "code_switch_words": [],
            "word_count": 0, "matched_answer": "",
        }

    kw_coverage, missing = _keyword_coverage(norm, required_keywords or [])
    similarity, matched = _best_similarity(norm, candidates) if candidates else (0.5, "")
    cs_rate, cs_words = detect_code_switching(text)
    word_count = len(norm.split())
    length_ok = word_count >= 2

    # Atajo: dijo (casi) exactamente una respuesta aceptada → pasa siempre.
    # Esto es lo que impide que la app rechace sus propias sugerencias.
    if similarity >= _MATCH_THRESHOLD and not cs_words:
        return {
            "score": 1.0, "passed": True, "can_continue": True,
            "similarity": round(similarity, 2),
            "feedback_es": "¡Perfecto! Justo así se dice. 🎉",
            "missing_groups": [], "code_switch_words": [],
            "word_count": word_count, "matched_answer": matched,
        }

    # Score combinado. Keywords bajaron de 0.50 a 0.30: son bonus, no compuerta.
    score = (
        kw_coverage * 0.30
        + min(similarity, 1.0) * 0.40
        + (1 - min(cs_rate, 1)) * 0.15
        + (1.0 if length_ok else 0.3) * 0.15
    )
    score = round(max(0.0, min(1.0, score)), 2)

    # Decisión: generosa a propósito. Bloquear sin explicar es peor que
    # dejar pasar una respuesta imperfecta con feedback.
    # Code-switch pesado corta el paso: si media respuesta es español, no
    # sirve como práctica de inglés por más keywords que matcheen
    # ("no sé qué decir" cubría el grupo ["yes","no","please"] con el "no").
    heavy_code_switch = cs_rate >= 0.20
    passed = (not heavy_code_switch) and (
        score >= 0.60                        # razonablemente bien
        or similarity >= 0.70                # se parece bastante a algo válido
        or (kw_coverage >= 0.99 and word_count >= 3 and not cs_words)  # dijo todo lo pedido
    )

    # Aunque no pase: el usuario puede seguir. No hay callejón sin salida.
    can_continue = word_count >= 2

    if passed:
        if cs_words:
            feedback = f"Pasa, pero ojo: dijiste «{', '.join(cs_words[:3])}» en español."
        elif missing:
            hints = " · ".join(grp[0] for grp in missing[:2])
            feedback = f"¡Bien! Sumá esto para sonar aún más natural: {hints}."
        elif score >= 0.85:
            feedback = "¡Muy natural! 🎉"
        else:
            feedback = "Bien, podemos avanzar."
    else:
        if cs_words:
            feedback = f"Te trabaste con español: «{', '.join(cs_words[:3])}». Probá en inglés."
        elif word_count < 3:
            feedback = "Muy cortito. Probá con una oración un poco más larga."
        elif missing:
            hints = " · ".join(grp[0] for grp in missing[:3])
            feedback = f"Se entiende, pero para este turno se espera algo con: {hints}"
        else:
            feedback = "No es lo que espera el personaje. Mirá las opciones de abajo."

    return {
        "score": score,
        "passed": passed,
        "can_continue": can_continue,
        "similarity": round(similarity, 2),
        "feedback_es": feedback,
        "missing_groups": missing,
        "code_switch_words": cs_words,
        "word_count": word_count,
        "matched_answer": matched if similarity >= _MATCH_THRESHOLD else "",
    }
