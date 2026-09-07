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


# Números en palabras. Hace falta porque Whisper transcribe "at six" como
# "at 6", mientras el usuario escribiendo pone "six": sin esto, la misma
# respuesta cuenta como distinta según si la habló o la escribió.
_UNITS = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen",
]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
         "eighty", "ninety"]


def _number_to_words(n: int) -> str | None:
    """0-100 a palabras. Fuera de rango → None (años, cantidades: se dejan)."""
    if n < 20:
        return _UNITS[n]
    if n < 100:
        tens, unit = divmod(n, 10)
        return _TENS[tens] + ((" " + _UNITS[unit]) if unit else "")
    if n == 100:
        return "one hundred"
    return None


def _digits_to_words(s: str) -> str:
    def repl(m):
        word = _number_to_words(int(m.group(0)))
        return word if word is not None else m.group(0)
    return re.sub(r"\b\d{1,3}\b", repl, s)


def normalize(s: str) -> str:
    """lowercase + apóstrofes unificados + contracciones expandidas
    + números a palabras + sin puntuación + espacios colapsados."""
    s = s.lower()
    # Apóstrofes curvos/backtick → apóstrofe recto ANTES de limpiar puntuación
    s = s.replace("’", "'").replace("‘", "'").replace("`", "'")
    # Expandir contracciones a forma larga (don't → do not)
    s = _CONTRACTION_RE.sub(lambda m: CONTRACTIONS[m.group(1)], s)
    s = re.sub(r"[^\w\s]", " ", s)
    # Después de limpiar puntuación: "6:30" ya es "6 30" → "six thirty"
    s = _digits_to_words(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# Variantes explícitas del curriculum: evitamos stemming que confunda go/good.
TERM_VARIANTS = {
    "dollar": ["dollars"], "costs": ["cost"], "favorite": ["favourite"],
    "wake up": ["woke up", "woken up", "waking up"],
    "get up": ["got up", "getting up"],
    "give up": ["gave up", "given up", "giving up"],
    "keep going": ["kept going"],
    "work out": ["worked out", "working out", "works out"],
    "pay off": ["paid off", "paying off", "pays off"],
    "figure out": ["figured out", "figuring out"],
    "run into": ["ran into", "running into"],
    "catch up": ["caught up", "catching up"],
    "hang out": ["hung out", "hanging out"],
    "show up": ["showed up", "showing up"],
    "let down": ["let ... down"],
    "come up with": ["came up with", "coming up with"],
    "deal with": ["dealt with", "dealing with"],
    "follow up": ["followed up", "following up"],
    "look into": ["looked into", "looking into"],
    "get along with": ["get along ... with", "got along with"],
    "back up": ["back ... up", "backed ... up"],
    "take over": ["took over", "taken over", "taking over"],
    "he/she told me": ["he told me", "she told me", "boss told me"],
    "he/she said that": ["he said", "she said"],
}


def matches_term(text: str, term: str) -> bool:
    """Busca palabras/frases completas; '...' permite hasta 8 palabras intermedias."""
    normalized = normalize(text)
    for variant in [term, *TERM_VARIANTS.get(term.lower(), [])]:
        chunks = [normalize(p) for p in variant.split("...")]
        if not all(chunks):
            continue
        pattern = r"(?:\s+\w+){0,8}\s+".join(re.escape(p) for p in chunks)
        if re.search(r"(?<!\w)" + pattern + r"(?!\w)", normalized):
            return True
    return False
