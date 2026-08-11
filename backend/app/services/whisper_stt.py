"""Speech-to-Text offline con faster-whisper.

Reemplaza a Vosk como motor principal: entiende mucho mejor a hablantes no
nativos. Vosk confundía cosas como "yes that's right" → "yes that's why".

Gratis y offline (licencia MIT, sin API key). El modelo se baja una sola vez
de HuggingFace la primera vez que se usa, y queda en caché en disco:

    base.en   ~150 MB  — rápido, suficiente para A1-B1
    small.en  ~500 MB  — más preciso, ~2-3× más lento en CPU

Se elige con WHISPER_MODEL en .env. Con `int8` corre en CPU sin GPU.

Ojo: Whisper alucina con silencio o ruido (devuelve frases tipo "Thank you."
que nadie dijo). Por eso va con VAD activado y un filtro de alucinaciones
conocidas — ver _HALLUCINATIONS.
"""
from __future__ import annotations
import logging
import re
import threading
from io import BytesIO
from pathlib import Path

from app.config import settings


log = logging.getLogger(__name__)


try:
    from faster_whisper import WhisperModel  # type: ignore
    HAS_WHISPER = True
except ImportError:  # pragma: no cover - depende del entorno
    HAS_WHISPER = False
    log.info("faster-whisper no instalado; el STT usará Vosk si está disponible.")


class STTUnavailable(Exception):
    pass


# Frases que Whisper inventa cuando el audio es silencio o ruido. Vienen de los
# subtítulos de YouTube con los que se entrenó.
_HALLUCINATIONS = {
    "thank you", "thanks for watching", "thank you for watching",
    "please subscribe", "subscribe to my channel", "bye", "bye bye",
    "you", "okay", "oh", "hmm", "mm", "mm-hmm", "so",
    "thanks for watching and don't forget to subscribe",
}

_model: WhisperModel | None = None
# Cargar el modelo tarda segundos y no es thread-safe: dos requests simultáneos
# no deben construirlo dos veces.
_model_lock = threading.Lock()


def _download_root() -> str | None:
    """Carpeta donde cachear el modelo. None = el default de HuggingFace."""
    raw = (settings.WHISPER_MODEL_DIR or "").strip()
    if not raw:
        return None
    p = Path(raw)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent.parent.parent / p
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


def get_model() -> WhisperModel:
    global _model
    if not HAS_WHISPER:
        raise STTUnavailable(
            "faster-whisper no está instalado. Corré: pip install faster-whisper"
        )
    if _model is None:
        with _model_lock:
            if _model is None:  # otro thread pudo haberlo cargado mientras esperábamos
                name = settings.WHISPER_MODEL
                log.info(
                    "Cargando modelo Whisper '%s' (compute=%s). "
                    "La primera vez lo descarga (~150 MB para base.en).",
                    name, settings.WHISPER_COMPUTE_TYPE,
                )
                try:
                    _model = WhisperModel(
                        name,
                        device="cpu",
                        compute_type=settings.WHISPER_COMPUTE_TYPE,
                        download_root=_download_root(),
                    )
                except Exception as e:
                    raise STTUnavailable(
                        f"No se pudo cargar el modelo Whisper '{name}': {e}. "
                        "La primera vez necesita internet para descargarlo."
                    ) from e
                log.info("Modelo Whisper listo.")
    return _model


def _clean(text: str) -> str:
    """Recorta espacios y descarta alucinaciones de silencio."""
    text = text.strip()
    if not text:
        return ""
    bare = re.sub(r"[^a-z\s']", "", text.lower()).strip()
    if bare in _HALLUCINATIONS:
        log.info("Whisper alucinó sobre silencio (%r), lo descarto.", text)
        return ""
    return text


# Techos para las pistas de vocabulario. Whisper igual trunca solo a la mitad
# de su ventana, pero recortamos antes para que entren los términos que importan
# y para no confiar en un input que viene del cliente.
MAX_HINTS = 32
MAX_HINTS_CHARS = 300


def build_hotwords(hints: list[str] | None) -> str | None:
    """Convierte la lista de términos esperados en el string que espera Whisper.

    Es un sesgo BLANDO: sube la probabilidad de esas palabras, pero el modelo
    puede transcribir cualquier otra cosa. Si el usuario dice algo distinto,
    se transcribe lo que dijo.
    """
    if not hints:
        return None
    seen: set[str] = set()
    terms: list[str] = []
    for h in hints:
        if not isinstance(h, str):
            continue
        t = " ".join(h.split())          # colapsa espacios y saltos de línea
        if not t or len(t) > 40:
            continue
        low = t.lower()
        if low in seen:
            continue
        seen.add(low)
        terms.append(t)
        if len(terms) >= MAX_HINTS:
            break
    if not terms:
        return None
    out = " ".join(terms)[:MAX_HINTS_CHARS].strip()
    return out or None


def transcribe(audio_bytes: bytes, hints: list[str] | None = None) -> str:
    """Transcribe audio (webm/opus/wav/ogg) a texto inglés.

    Whisper decodifica el audio por su cuenta con PyAV, así que no hace falta
    ffmpeg. Igual aceptamos WAV ya convertido: da lo mismo.

    `hints` sesga el reconocimiento hacia el vocabulario esperado del ejercicio
    (equivalente server-side de lo que hace Web Speech con sus alternativas).
    """
    model = get_model()
    hotwords = build_hotwords(hints)
    try:
        segments, info = model.transcribe(
            BytesIO(audio_bytes),
            language="en",              # fijo: la app es de inglés, evita que detecte español
            beam_size=5,
            vad_filter=True,            # descarta silencio => menos alucinaciones
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=False,  # sin esto se engancha repitiendo frases
            no_speech_threshold=0.6,
            temperature=0.0,            # determinístico
            hotwords=hotwords,
        )
        parts = [seg.text for seg in segments]
    except STTUnavailable:
        raise
    except Exception as e:
        log.exception("Whisper falló al transcribir: %s", e)
        raise STTUnavailable(f"No se pudo transcribir el audio: {e}") from e

    text = _clean(" ".join(p.strip() for p in parts if p and p.strip()))
    if text:
        log.info(
            "Whisper: %d segmento(s), prob. de habla en inglés=%.2f, hints=%s",
            len(parts), getattr(info, "language_probability", 0.0) or 0.0,
            "sí" if hotwords else "no",
        )
    return text


def model_is_downloaded() -> bool:
    """True si el modelo ya está en caché (es decir, funciona sin internet)."""
    if not HAS_WHISPER:
        return False
    name = settings.WHISPER_MODEL
    root = _download_root()
    roots = [Path(root)] if root else [Path.home() / ".cache" / "huggingface" / "hub"]
    # faster-whisper guarda los oficiales como models--Systran--faster-whisper-<name>
    slug = f"faster-whisper-{name}".replace("/", "--")
    for r in roots:
        if not r.exists():
            continue
        for d in r.glob("**/*"):
            if d.is_dir() and slug in d.name:
                return True
        # Un modelo local (ruta propia) también cuenta.
        if (r / name).is_dir():
            return True
    return False


def available() -> bool:
    """Instalado y listo para usar. El modelo se baja solo la primera vez."""
    return HAS_WHISPER


def diagnose() -> dict:
    return {
        "installed": HAS_WHISPER,
        "model": settings.WHISPER_MODEL,
        "compute_type": settings.WHISPER_COMPUTE_TYPE,
        "model_downloaded": model_is_downloaded(),
        "loaded": _model is not None,
    }
