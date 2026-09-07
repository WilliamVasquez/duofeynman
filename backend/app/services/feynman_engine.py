"""Motor del Método Feynman aplicado a aprender inglés hablado y escrito.

Versión 100% rule-based (sin IA generativa, sin APIs pagas).

Ciclo Feynman por Topic:
  1. EXPOSE       → mostrar tema + vocabulario + audio modelo (frontend)
  2. EXPLAIN      → usuario explica (voz o texto) en inglés
  3. DETECT       → análisis: fluidez + gramática (LanguageTool) + code-switch
                    + cobertura de vocabulario y connectors del topic
  4. REFINE       → preguntas socráticas fijas del topic (topic.socratic_hints)
  5. CONSOLIDATE  → crear card SRS y registrar dominio

Filosofía:
  - Sin IA generativa significa: las preguntas son fijas por tema, los mensajes
    motivacionales se eligen de un pool, las correcciones vienen de reglas
    duras (LanguageTool + heurísticas).
  - Para A1-A2 es suficiente y muchas veces MÁS pedagógico (consistente,
    explicable, no inventa).
"""
from __future__ import annotations
import logging
import random
import re
import json
from pathlib import Path
from typing import Any

from app.models.curriculum import Topic
from app.services import analyzer
from app.services.text_utils import normalize as _tnorm, matches_term


log = logging.getLogger(__name__)

# Criterios editoriales de contenido: alternativas OR dentro de cada grupo.
# No evalúan semántica libre; el feedback explica qué evidencia falta.
ASSESSMENT = json.loads((Path(__file__).parents[1] / "data/curriculum/assessment.json").read_text(encoding="utf-8"))


def check_objective(topic: Topic, text: str) -> tuple[bool, list[list[str]]]:
    normalized = " " + _tnorm(text) + " "
    groups = ASSESSMENT.get(topic.slug)
    if groups is None:
        groups = [_vocab_strings(topic)] if _vocab_strings(topic) else []
    def matches(term):
        if term == "i am <number>":
            return bool(re.search(r"\bi am (?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)\b", normalized))
        return matches_term(text, term)
    missing = [group for group in groups if not any(matches(term) for term in group)]
    return not missing, missing


# Pool de mensajes motivacionales en español, según rango de score.
ENCOURAGEMENT_POOL = {
    "high": [
        "¡Excelente! Sonó natural y fluido. 🎉",
        "Buenísimo, lo explicaste con claridad. ¡Seguí así!",
        "Muy bien, tu inglés se está soltando. 💪",
        "¡Eso es! Esa es la idea del método Feynman: simple y claro.",
    ],
    "mid": [
        "Vas por buen camino. Probá conectar mejor tus ideas con 'because', 'so', 'then'.",
        "Bien, pero podés ser más simple. Como si se lo explicaras a un niño.",
        "Buen intento. Mirá las correcciones y volvé a intentar.",
        "Casi. Una vuelta más y lo dominás.",
    ],
    "low": [
        "Tranquilo, hablar es lo más difícil. Probá de nuevo, más despacio.",
        "No pasa nada, leé el ejemplo, escuchalo, y reintentá.",
        "Recordá: en inglés, no traduzcas en tu cabeza. Pensá en imágenes.",
        "Vas a poder. Probá usando solo 3-4 palabras clave del tema.",
    ],
    "code_switch": [
        "Te trabaste y dijiste algunas palabras en español. Está OK — la próxima intentá decirlas en inglés aunque sea mal pronunciado.",
        "Mezclaste un poco de español. Mirá el vocabulario clave arriba y reintentá.",
    ],
    "too_short": [
        "Muy cortito. Intentá decir al menos 2-3 oraciones.",
        "Necesito escucharte más. Probá con la rutina completa, paso por paso.",
    ],
}


def _coverage(text: str, items: list[str]) -> tuple[float, list[str]]:
    """Cuántos items aparecen en text. Devuelve (ratio, faltantes).

    Usa normalización compartida: apóstrofes curvos y contracciones
    (don't ↔ do not) matchean entre sí.
    """
    if not items:
        return 1.0, []
    found = [it for it in items if matches_term(text, it)]
    missing = [it for it in items if not matches_term(text, it)]
    return len(found) / len(items), missing


def _vocab_strings(topic: Topic) -> list[str]:
    out = []
    for v in topic.key_vocabulary or []:
        en = v.get("en") if isinstance(v, dict) else None
        if en:
            out.append(en)
    return out


def compute_subscores(
    metrics: dict, vocab_cov: float, connector_cov: float, difficulty: int = 3,
    reference: dict | None = None,
) -> dict:
    """Calcula 4 sub-scores (0-1) que se le muestran al usuario.

    - vocabulary: cobertura de vocab del topic + diversidad léxica
    - structure:  conectores + tiempos verbales + cantidad de oraciones
    - naturalness: sin code-switching + pocos errores gramaticales
    - fluency:    velocidad/longitud adecuada

    `difficulty` (1-5) del topic: en niveles bajos (≤2) no exigimos
    3 oraciones ni 3 tiempos verbales — una respuesta A1 corta y correcta
    debe poder aprobar.
    """
    # Vocabulario
    lex_div_norm = min(metrics.get("lexical_diversity", 0) / 0.7, 1.0)
    vocabulary = (vocab_cov * 0.6 + lex_div_norm * 0.4)

    # Estructura: objetivos escalados por dificultad
    reference = reference or {}
    tense_target = min(3, reference.get("tense_diversity", 1))
    sentence_target = max(1, min(3, reference.get("sentence_count", 2)))
    tenses = metrics.get("tense_diversity", 0)
    tense_score = min(tenses / tense_target, 1.0) if tense_target else 1.0
    sentences = metrics.get("sentence_count", 1)
    sentence_score = min(sentences / sentence_target, 1.0)
    structure = (connector_cov * 0.4 + tense_score * 0.3 + sentence_score * 0.3)

    # Naturalidad
    cs_rate = metrics.get("code_switch_rate", 0)
    cs_score = max(0.0, 1 - cs_rate * 2)  # penalización fuerte
    grammar_errors = metrics.get("grammar_errors_count", 0)
    word_count = max(metrics.get("word_count", 1), 1)
    err_density = grammar_errors / word_count
    # *4 (antes *10): con *10 un error cada 10 palabras dejaba gramática en 0.
    # LanguageTool marca bastante ruido (mayúsculas, comas) — no castigar tanto.
    grammar_score = max(0.0, 1 - err_density * 4)
    naturalness = (cs_score * 0.6 + grammar_score * 0.4)

    # Fluidez (longitud + velocidad)
    length_target = max(5, min(20, reference.get("word_count", 20)))
    length_score = min(word_count / length_target, 1.0)
    fluency_raw = metrics.get("fluency_score", 0)
    fluency_combined = (length_score * 0.5 + fluency_raw * 0.5)

    return {
        "vocabulary": round(max(0.0, min(1.0, vocabulary)), 2),
        "structure": round(max(0.0, min(1.0, structure)), 2),
        "naturalness": round(max(0.0, min(1.0, naturalness)), 2),
        "fluency": round(max(0.0, min(1.0, fluency_combined)), 2),
    }


def compute_overall_score(subscores: dict) -> float:
    """Score combinado a partir de los 4 sub-scores.

    Pesos: vocabulario 25 · estructura 25 · naturalidad 30 · fluidez 20.
    Naturalidad pesa más porque sin code-switching y con gramática mínima
    es la mejor señal de aprendizaje real para A1-A2.
    """
    score = (
        subscores["vocabulary"] * 0.25
        + subscores["structure"] * 0.25
        + subscores["naturalness"] * 0.30
        + subscores["fluency"] * 0.20
    )
    return round(max(0.0, min(1.0, score)), 2)


def mastery_threshold(difficulty: int) -> float:
    """Umbral de MASTERED según dificultad del topic (1-5).

    En A1 (dificultad 1-2) el usuario recién arranca: exigir 0.78 con
    sub-scores que castigan fuerte hacía imposible aprobar respuestas
    cortas correctas.
    """
    if difficulty <= 2:
        return 0.68
    if difficulty == 3:
        return 0.72
    return 0.78


def decide_next_action(score: float, word_count: int, difficulty: int = 3) -> str:
    if word_count < 5:
        return "CONTINUE"
    if score >= mastery_threshold(difficulty):
        return "MASTERED"
    if score >= 0.55:
        return "REFINE"
    return "CONTINUE"


def pick_encouragement(score: float, metrics: dict, threshold: float = 0.78) -> str:
    if metrics["word_count"] < 8:
        return random.choice(ENCOURAGEMENT_POOL["too_short"])
    if metrics["code_switch_rate"] >= 0.15:
        return random.choice(ENCOURAGEMENT_POOL["code_switch"])
    if score >= threshold:
        return random.choice(ENCOURAGEMENT_POOL["high"])
    if score >= 0.55:
        return random.choice(ENCOURAGEMENT_POOL["mid"])
    return random.choice(ENCOURAGEMENT_POOL["low"])


def build_socratic_questions(
    topic: Topic, score: float, missing_vocab: list[str], missing_connectors: list[str],
    threshold: float = 0.78,
) -> list[str]:
    """Selecciona preguntas socráticas del topic + sugerencias dinámicas simples."""
    questions: list[str] = []

    # 1-2 preguntas fijas del curriculum
    hints = list(topic.socratic_hints or [])
    random.shuffle(hints)
    questions.extend(hints[:2])

    # Sugerencias generadas con plantillas (no es IA, son templates)
    if score < threshold and missing_connectors:
        c = missing_connectors[0]
        questions.append(f"Try saying it again using '{c}' to connect your ideas.")

    if score < 0.6 and missing_vocab:
        v = missing_vocab[0]
        questions.append(f"Can you use the word '{v}' in your answer?")

    return questions[:3]


def build_corrections(
    grammar_errors: list[dict],
    code_switch_errors: list[dict],
) -> list[dict]:
    """Normaliza errores para guardar y devolver al frontend."""
    out: list[dict] = []
    for g in grammar_errors[:8]:
        out.append({
            "category": "GRAMMAR",
            "rule_id": g.get("rule_id"),
            "span_text": g["span_text"][:500],
            "suggestion": g["suggestion"][:500],
            "explanation_es": g.get("explanation_en", "")[:1000],
            "severity": g.get("severity", 1),
        })
    for cs in code_switch_errors[:5]:
        out.append(cs)
    return out


async def evaluate_round(
    topic: Topic,
    transcript: str,
    duration_seconds: int,
    *,
    mode: str = "speak",
) -> dict[str, Any]:
    """Evalúa una ronda. `mode` = 'speak' | 'write'.

    En modo 'write' la fluidez no se mide por wpm (penalizaría injustamente).
    """
    local_metrics = analyzer.analyze_transcript(transcript, duration_seconds)
    reference = analyzer.analyze_transcript(topic.example_en or "", 0)
    grammar_errors = await analyzer.check_grammar(transcript)

    # En modo escrito ignoramos fluidez por tiempo y la basamos en longitud
    if mode == "write":
        wc = local_metrics["word_count"]
        local_metrics["fluency_score"] = min(wc / max(5, min(30, reference["word_count"])), 1.0)

    local_metrics["grammar_errors_count"] = len(grammar_errors)

    vocab_list = _vocab_strings(topic)
    connectors = list(topic.connectors or [])
    vocab_cov, missing_vocab = _coverage(transcript, vocab_list)
    connector_cov, missing_connectors = _coverage(transcript, connectors)

    difficulty = int(topic.difficulty or 3)
    threshold = mastery_threshold(difficulty)
    # Los conectores son sugerencias. No exigir más de los que usa el modelo.
    reference_connectors, _ = _coverage(topic.example_en or "", connectors)
    connector_score = min(1.0, connector_cov / reference_connectors) if reference_connectors else 1.0
    subscores = compute_subscores(local_metrics, vocab_cov, connector_score, difficulty, reference)
    score = compute_overall_score(subscores)
    objective_met, missing_objective = check_objective(topic, transcript)
    if not objective_met:
        score = min(score, round(threshold - 0.01, 2))
    action = decide_next_action(score, local_metrics["word_count"], difficulty)
    encouragement = pick_encouragement(score, local_metrics, threshold)
    socratic = build_socratic_questions(
        topic, score, missing_vocab, missing_connectors, threshold
    )
    if not objective_met:
        suggestions = "; ".join(" / ".join(g[:3]) for g in missing_objective)
        socratic = [f"Answer this task: {topic.prompt_en}", f"Try using: {suggestions}."]

    errors = build_corrections(
        grammar_errors,
        local_metrics.get("code_switch_errors", []),
    )

    error_density = (len(errors) / max(local_metrics["word_count"], 1)) * 100

    # Mostrar respuesta modelo solo si no dominó (para que pueda copiar / escuchar)
    model_answer = topic.example_en if action != "MASTERED" else None

    return {
        "overall_score": score,
        "objective_met": objective_met,
        "fluency_score": local_metrics["fluency_score"],
        "code_switch_rate": local_metrics["code_switch_rate"],
        "self_correction_rate": local_metrics.get("self_correction_rate", 0.0),
        "error_density": error_density,
        "word_count": local_metrics["word_count"],
        "vocab_coverage": round(vocab_cov, 2),
        "connector_coverage": round(connector_cov, 2),
        "subscores": subscores,
        "lexical_diversity": local_metrics.get("lexical_diversity", 0),
        "sentence_count": local_metrics.get("sentence_count", 0),
        "tenses_used": local_metrics.get("tenses_used", []),
        "errors": errors,
        "socratic_questions": socratic,
        "encouragement_es": encouragement,
        "next_action": action,
        "model_answer_en": model_answer,
    }
