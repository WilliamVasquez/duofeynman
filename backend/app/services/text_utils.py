"""Normalización de texto compartida para matching de respuestas.

Resuelve falsos negativos conocidos:
- Apóstrofes curvos (’ ‘ `) del teclado móvil rompían contracciones.
- "don't" vs "do not": ambas formas son válidas — se expanden a la forma
  larga para que matcheen entre sí.
"""
from __future__ import annotations
import re


# Contracciones comunes A1-B1 → forma larga canónica.
# Nota: 's y 'd son ambiguos (is/has, would/had); expandimos a la forma
# más frecuente en A1 (is / would). Suficiente para matching.
CONTRACTIONS = {
    "don't": "do not", "doesn't": "does not", "didn't": "did not",
    "can't": "can not", "cannot": "can not", "won't": "will not",
    "isn't": "is not", "aren't": "are not", "wasn't": "was not",
    "weren't": "were not", "haven't": "have not", "hasn't": "has not",
    "hadn't": "had not", "wouldn't": "would not", "couldn't": "could not",
    "shouldn't": "should not", "mustn't": "must not",
    "i'm": "i am", "you're": "you are", "we're": "we are",
    "they're": "they are", "he's": "he is", "she's": "she is",
    "it's": "it is", "that's": "that is", "there's": "there is",
    "what's": "what is", "who's": "who is", "where's": "where is",
    "how's": "how is", "here's": "here is",
    "i've": "i have", "you've": "you have", "we've": "we have",
    "they've": "they have",
    "i'll": "i will", "you'll": "you will", "he'll": "he will",
    "she'll": "she will", "we'll": "we will", "they'll": "they will",
    "it'll": "it will",
    "i'd": "i would", "you'd": "you would", "he'd": "he would",
    "she'd": "she would", "we'd": "we would", "they'd": "they would",
    "let's": "let us",
}

_CONTRACTION_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in CONTRACTIONS) + r")\b"
)


def normalize(s: str) -> str:
    """lowercase + apóstrofes unificados + contracciones expandidas
    + sin puntuación + espacios colapsados."""
    s = s.lower()
    # Apóstrofes curvos/backtick → apóstrofe recto ANTES de limpiar puntuación
    s = s.replace("’", "'").replace("‘", "'").replace("`", "'")
    # Expandir contracciones a forma larga (don't → do not)
    s = _CONTRACTION_RE.sub(lambda m: CONTRACTIONS[m.group(1)], s)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s
