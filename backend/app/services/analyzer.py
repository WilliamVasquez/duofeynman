"""Analizador lingüístico: detecta errores, mide fluidez y code-switching.

Combina:
- Reglas locales rápidas (sin red): code-switching, fluidez, fillers, errores A1
- LanguageTool API pública (gratis): gramática general
"""
from __future__ import annotations
import re
import logging
import httpx

from app.config import settings


log = logging.getLogger(__name__)


# Palabras españolas comunes (detección de code-switching)
COMMON_SPANISH = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o", "pero", "porque",
    "que", "como", "cuando", "donde", "muy", "mas", "más", "yo", "tu",
    "tú", "él", "ella", "nosotros", "ellos", "ellas", "es", "son", "está",
    "esta", "estoy", "tengo", "tiene", "hace", "hacer", "voy", "vamos",
    "trabajo", "casa", "comida", "agua", "tiempo", "día", "dia", "noche",
    "bueno", "buena", "malo", "mala", "siempre", "nunca", "también", "tambien",
    "entonces", "después", "despues", "antes", "ahora", "aquí", "aqui",
    "allá", "alla", "hola", "adiós", "adios", "gracias", "por", "favor",
    "sí", "ser", "estar", "del",
    "con", "sin", "para",
}

# Lugares y nombres propios comunes que NO deben marcarse como español
# aunque contengan palabras españolas (ej "El Salvador").
PROPER_NOUNS_WHITELIST = {
    "el salvador", "los angeles", "las vegas", "san salvador", "la paz",
    "san francisco", "san diego", "san jose", "santa fe", "santa monica",
    "san antonio", "santa cruz", "puerto rico", "costa rica",
    "buenos aires", "rio de janeiro", "el paso",
}

FILLERS_EN = {"um", "uh", "er", "hmm"}

# Marcadores de autocorrección: el hablante nota un error y reformula.
# Es señal POSITIVA (monitoreo lingüístico, clave en la Output Hypothesis):
# no penaliza, pero lo medimos para mostrarle al usuario que se está corrigiendo.
SELF_CORRECTION_MARKERS = [
    r"\bi mean\b",
    r"\bno,?\s+wait\b",
    r"\bwait,?\s+no\b",
    r"\bsorry,?\s+i mean\b",
    r"\bactually,?\s+no\b",
    r"\bor rather\b",
]

# Reglas custom para errores típicos A1 que LanguageTool a veces no atrapa.
# Cada regla: (regex, sugerencia, explicación_es, severity)
CUSTOM_RULES = [
    # Text-speak / abreviaciones
    (r"\b[Uu]\b(?!\.)", "you", "Escribiste 'U'. En inglés correcto se dice 'you'.", 2),
    (r"\b[Rr]\b(?!\.)", "are", "Escribiste 'R'. En inglés correcto es 'are'.", 2),
    (r"\b[Uu]r\b", "your", "'ur' es text-speak. Lo correcto es 'your'.", 2),
    (r"\bthx\b", "thanks", "'thx' es informal. Mejor 'thanks'.", 1),
    # I + verbo sin 'm / 'am
    (r"\bI from\b", "I'm from", "Falta el verbo 'to be': 'I'm from' (= I am from).", 3),
    (r"\bI in\b", "I'm in", "Falta el verbo: 'I'm in'.", 3),
    (r"\bI a (?=[a-z])", "I'm a ", "Falta el verbo: 'I'm a' (= I am a).", 3),
    (r"\bI very\b", "I'm very", "Falta el verbo 'to be': 'I'm very'.", 3),
    (r"\bI [Hh]appy\b", "I'm happy", "Con adjetivos hace falta 'to be': 'I am happy'.", 3),
    (r"\bI [Ss]ad\b", "I'm sad", "Con adjetivos hace falta 'to be': 'I am sad'.", 3),
    (r"\bI [Tt]ired\b", "I'm tired", "Con adjetivos hace falta 'to be': 'I am tired'.", 3),
    # i minúscula como pronombre
    (r"(^|[\s.!?])i(\s)", r"\1I\2", "El pronombre 'I' siempre va en mayúscula.", 1),
    # gonna / wanna en contexto formal (advertencia leve)
    (r"\bgonna\b", "going to", "'gonna' es informal hablado. En escrito mejor 'going to'.", 1),
    (r"\bwanna\b", "want to", "'wanna' es informal hablado. En escrito mejor 'want to'.", 1),
    # Doble negación típica de hispanohablantes
    (r"\bI don't have no\b", "I don't have any", "En inglés no se usa doble negación: 'I don't have any'.", 3),
    (r"\bI no\s+(have|like|want|go|see)\b", r"I don't \1", "Negación correcta: 'I don't + verbo'.", 3),
    # "have X years" en vez de "be X years old"
    (r"\bI have (\d+) years?\b", r"I am \1 years old", "En inglés la edad usa 'to be': 'I am X years old', no 'I have X years'.", 3),
    # Punto final faltante
    # (skip — no es realmente un error pedagógico fuerte para A1)
]


def detect_code_switching(text: str) -> tuple[float, list[str]]:
    """Devuelve (rate, lista_de_palabras_es).

    Reglas para evitar falsos positivos:
    - Si la palabra aparece en mayúsculas iniciales en el original (probable
      nombre propio), no la marcamos.
    - Si la palabra es parte de un nombre propio conocido de la whitelist
      (ej. "El Salvador"), no la marcamos.
    """
    text_lower = text.lower()

    # 1. Marcar offsets cubiertos por nombres propios whitelisteados
    masked_ranges: list[tuple[int, int]] = []
    for proper in PROPER_NOUNS_WHITELIST:
        for m in re.finditer(re.escape(proper), text_lower):
            masked_ranges.append((m.start(), m.end()))

    def is_masked(start: int, end: int) -> bool:
        return any(s <= start and end <= e for (s, e) in masked_ranges)

    # 2. Recorrer palabras con su offset y case original
    flagged: list[str] = []
    total = 0
    for m in re.finditer(r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü]+", text):
        word = m.group(0)
        total += 1
        if is_masked(m.start(), m.end()):
            continue
        lw = word.lower()
        if len(lw) <= 1:
            continue
        if lw not in COMMON_SPANISH:
            continue
        # Si la palabra está capitalizada (primera letra mayúscula) y no es
        # comienzo de oración, probablemente sea nombre propio.
        if word[0].isupper():
            # Verificar si es inicio de oración
            prev = text[:m.start()].rstrip()
            is_sentence_start = (not prev) or prev[-1] in ".!?¡¿\n"
            if not is_sentence_start:
                continue
        flagged.append(lw)

    if total == 0:
        return 0.0, []
    rate = len(flagged) / total
    return rate, sorted(set(flagged))


def count_fillers(text: str) -> int:
    lowered = " " + text.lower() + " "
    return sum(lowered.count(f" {f} ") for f in FILLERS_EN)


def detect_self_corrections(text: str) -> tuple[int, float]:
    """Cuenta autocorrecciones: el usuario nota un error y reformula sobre la marcha.

    Detecta marcadores ("I mean", "no wait"...), falsos arranques con guión
    ("go— I went") y repeticiones inmediatas de palabra ("I I went").
    Devuelve (count, rate) con rate = correcciones / oraciones (cap 1.0).
    """
    low = text.lower()
    count = sum(len(re.findall(pat, low)) for pat in SELF_CORRECTION_MARKERS)
    # Falsos arranques marcados con guión de interrupción
    count += len(re.findall(r"\w+\s*[—–-]{1,2}\s+\w+", text))
    # Tartamudeo/reinicio: misma palabra repetida ("the the", "I I")
    count += len(re.findall(r"\b(\w+)\s+\1\b", low))
    sentences = max(1, len([p for p in re.split(r"[.!?]+", text) if p.strip()]))
    rate = min(1.0, count / sentences)
    return count, round(rate, 3)


def compute_fluency(word_count: int, duration_seconds: int) -> float:
    if duration_seconds <= 0:
        return 0.0
    wpm = (word_count / duration_seconds) * 60
    return max(0.0, min(1.0, wpm / 100.0))


def apply_custom_rules(text: str) -> list[dict]:
    """Aplica reglas regex locales. Complementan a LanguageTool."""
    errors: list[dict] = []
    for pattern, suggestion, explanation, severity in CUSTOM_RULES:
        for m in re.finditer(pattern, text):
            span = m.group(0)
            # La suggestion puede contener referencias \1, \2 -> reemplazar
            try:
                fix = re.sub(pattern, suggestion, span)
            except re.error:
                fix = suggestion
            errors.append({
                "category": "GRAMMAR",
                "rule_id": f"custom:{pattern[:30]}",
                "span_text": span,
                "suggestion": fix,
                "explanation_en": explanation,  # ya está en español
                "severity": severity,
            })
    return errors


async def check_grammar(text: str) -> list[dict]:
    """Llama a LanguageTool API pública + suma reglas custom locales."""
    custom = apply_custom_rules(text)

    lt_errors: list[dict] = []
    url = f"{settings.LANGUAGETOOL_URL}/check"
    try:
        async with httpx.AsyncClient(timeout=25) as cli:
            r = await cli.post(
                url,
                data={
                    "text": text,
                    "language": "en-US",
                    "level": "default",
                    "enabledOnly": "false",
                },
            )
            r.raise_for_status()
            data = r.json()
        for m in data.get("matches", []):
            offset = m.get("offset", 0)
            length = m.get("length", 0)
            span = text[offset: offset + length]
            replacements = [r["value"] for r in m.get("replacements", [])[:3]]
            lt_errors.append({
                "category": "GRAMMAR",
                "rule_id": m.get("rule", {}).get("id"),
                "span_text": span,
                "suggestion": replacements[0] if replacements else "",
                "explanation_en": m.get("message", ""),
                "severity": 2 if m.get("rule", {}).get("issueType") == "grammar" else 1,
            })
        log.info("LanguageTool devolvió %d errores", len(lt_errors))
    except (httpx.HTTPError, ValueError) as e:
        log.warning("LanguageTool no disponible (%s). Solo se usan reglas custom.", e)

    # Deduplicar: si una regla custom y LT marcan el mismo span, preferimos custom
    # (explicación en español).
    seen_spans = {e["span_text"].lower() for e in custom}
    deduped = custom + [e for e in lt_errors if e["span_text"].lower() not in seen_spans]
    return deduped


def lexical_diversity(text: str) -> float:
    """Type-Token Ratio (TTR): variedad de vocabulario.

    1.0 = todas las palabras distintas (muy variado).
    0.3 = repetís mucho las mismas palabras.
    Para A1-A2, TTR esperado ronda 0.45-0.65 en respuestas cortas.
    """
    words = re.findall(r"[a-z]+", text.lower())
    if not words:
        return 0.0
    # Filtrar stopwords muy frecuentes para que no distorsione
    types = set(words)
    return round(len(types) / len(words), 3)


def count_sentences(text: str) -> int:
    """Cuenta oraciones aproximadas (separadas por . ! ?)."""
    if not text.strip():
        return 0
    parts = [p for p in re.split(r"[.!?]+", text) if p.strip() and len(p.split()) >= 2]
    return max(1, len(parts))


# Tiempos verbales — patrones muy simples (no perfectos, pero útiles para A1-A2)
TENSE_PATTERNS = {
    "present_simple": re.compile(r"\b(?:i|we|you|they) (?:am|is|are|do|don't|have|has|like|want|need|go|work|live)\b", re.I),
    "present_continuous": re.compile(r"\b(?:am|is|are) \w+ing\b", re.I),
    "past_simple": re.compile(r"\b(?:was|were|did|didn't|had|went|got|made|said|told|saw|came|took)\b", re.I),
    "future": re.compile(r"\b(?:will|won't|going to|gonna|i'll|we'll|they'll|you'll)\b", re.I),
    "modal": re.compile(r"\b(?:can|could|should|would|might|may|must|have to|need to)\b", re.I),
    "conditional": re.compile(r"\b(?:if|unless|would|could)\b", re.I),
}


def tense_diversity(text: str) -> dict:
    """Devuelve qué tiempos verbales aparecen y cuántos distintos."""
    found = {name: bool(p.search(text)) for name, p in TENSE_PATTERNS.items()}
    found["distinct_count"] = sum(1 for v in found.values() if v)
    return found


def has_question(text: str) -> bool:
    """¿La respuesta incluye al menos una pregunta?"""
    if "?" in text:
        return True
    q_starters = ("who", "what", "where", "when", "why", "how", "do you", "are you", "can you", "is there", "have you")
    lowered = text.lower().strip()
    return any(lowered.startswith(s) for s in q_starters)


def analyze_transcript(text: str, duration_seconds: int) -> dict:
    """Análisis local enriquecido."""
    words = re.findall(r"\S+", text)
    word_count = len(words)
    cs_rate, cs_words = detect_code_switching(text)
    fluency = compute_fluency(word_count, duration_seconds)
    fillers = count_fillers(text)
    sc_count, sc_rate = detect_self_corrections(text)
    lex_div = lexical_diversity(text)
    sentence_count = count_sentences(text)
    tenses = tense_diversity(text)
    question = has_question(text)

    code_switch_errors = [
        {
            "category": "CODE_SWITCH",
            "rule_id": None,
            "span_text": w,
            "suggestion": "",
            "explanation_es": f"Dijiste «{w}» en español. Intentá decirlo en inglés.",
            "severity": 2,
        }
        for w in cs_words
    ]

    return {
        "word_count": word_count,
        "fluency_score": fluency,
        "code_switch_rate": cs_rate,
        "self_correction_count": sc_count,
        "self_correction_rate": sc_rate,
        "fillers": fillers,
        "lexical_diversity": lex_div,
        "sentence_count": sentence_count,
        "tense_diversity": tenses["distinct_count"],
        "tenses_used": [k for k, v in tenses.items() if v is True],
        "has_question": question,
        "code_switch_errors": code_switch_errors,
    }
