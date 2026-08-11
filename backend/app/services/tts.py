"""Text-to-Speech con dos backends en cascada.

1. Edge TTS — voces Microsoft Neural (online, gratis, sin API key)
   Aria, Jenny, Guy son casi indistinguibles de un humano.

2. Piper TTS — neural offline mediante el BINARIO standalone (no el paquete pip,
   que no tiene wheels para Windows). Fallback cuando no hay internet.

Si ninguno está disponible, /api/tts devuelve 503 y el frontend usa el
speechSynthesis del navegador como último recurso.
"""
from __future__ import annotations
import hashlib
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

import httpx
from starlette.concurrency import run_in_threadpool

from app.config import settings


log = logging.getLogger(__name__)


try:
    import edge_tts  # type: ignore
    HAS_EDGE = True
except ImportError:
    HAS_EDGE = False
    log.warning("edge-tts no instalado. La voz online no estará disponible.")


VOICES_EDGE = {
    "aria":    "en-US-AriaNeural",
    "jenny":   "en-US-JennyNeural",
    "guy":     "en-US-GuyNeural",
    "davis":   "en-US-DavisNeural",
    "sonia":   "en-GB-SoniaNeural",
    "ryan":    "en-GB-RyanNeural",
    "natasha": "en-AU-NatashaNeural",
}


class TTSError(Exception):
    pass


# === Velocidad de habla según nivel ===
# Entender inglés a velocidad real es una habilidad aparte de entender las
# palabras, así que se entrena de a poco: A1 lento, B1 velocidad normal.
# El signo NO es opcional: edge-tts valida ^[+-]\d+%$ y rechaza "0%".
RATE_BY_LEVEL = {
    "A1": "-25%",
    "A2": "-15%",
    "B1": "+0%",
    "B2": "+0%",
}
DEFAULT_RATE = "-10%"


def rate_for_level(level: str | None) -> str:
    if not level:
        return DEFAULT_RATE
    return RATE_BY_LEVEL.get(level.strip().upper(), DEFAULT_RATE)


def _normalize_rate(rate: str | None) -> str:
    """Deja el rate en el formato que exige edge-tts (con signo)."""
    r = (rate or "").strip()
    m = re.match(r"^([+-]?)(\d+)%$", r)
    if not m:
        return DEFAULT_RATE
    return f"{m.group(1) or '+'}{m.group(2)}%"


def _rate_percent(rate: str) -> int:
    """'-25%' -> -25. Cualquier cosa rara -> 0."""
    m = re.match(r"^([+-]?\d+)%$", (rate or "").strip())
    return int(m.group(1)) if m else 0


# === Edge TTS ===

async def synthesize_edge(text: str, voice_key: str, rate: str = DEFAULT_RATE) -> bytes:
    """Genera MP3 con Microsoft Edge TTS (online, neural).

    No hacemos pre-check de internet: si edge-tts falla, su excepción
    decide. Es más confiable que adivinar conectividad con un HEAD.
    """
    if not HAS_EDGE:
        raise TTSError("edge-tts no instalado")
    voice = VOICES_EDGE.get(voice_key, VOICES_EDGE[settings.DEFAULT_VOICE])
    chunks: list[bytes] = []
    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])
    except Exception as e:
        log.exception("edge-tts falló: %s", e)
        raise TTSError(f"edge-tts falló: {e}") from e
    if not chunks:
        raise TTSError("edge-tts no devolvió audio (¿sin internet o bloqueado?)")
    return b"".join(chunks)


# === Piper TTS (binario standalone) ===

def _resolve(rel_or_abs: str) -> Path:
    p = Path(rel_or_abs)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent.parent.parent / p
    return p


# Dónde buscar el binario si PIPER_BINARY_PATH no existe. El binario standalone
# de Windows se descomprime junto a los modelos, así que ésa es la ruta más común.
_PIPER_BIN_CANDIDATES = (
    "models/piper/piper.exe",
    "piper/piper.exe",
    "models/piper/piper",
    "piper/piper",
)

# Dónde buscar modelos .onnx si PIPER_MODEL_PATH no existe.
_PIPER_MODEL_DIRS = ("models/piper", "piper")

# Calidad del modelo por sufijo del nombre. Más alto = más natural.
_PIPER_QUALITY_RANK = {"high": 3, "medium": 2, "low": 1}


def _piper_binary_path() -> Path:
    configured = _resolve(settings.PIPER_BINARY_PATH)
    if configured.exists():
        return configured
    for cand in _PIPER_BIN_CANDIDATES:
        p = _resolve(cand)
        if p.exists():
            return p
    return configured  # devolvemos la configurada para que el error la muestre


def _model_quality(path: Path) -> int:
    """Rankea en_US-amy-medium.onnx -> 2. Desconocido -> 0."""
    stem = path.stem.lower()
    for name, rank in _PIPER_QUALITY_RANK.items():
        if stem.endswith("-" + name):
            return rank
    return 0


def _piper_model_path() -> Path:
    """Modelo configurado; si no existe, el .onnx de mayor calidad disponible."""
    configured = _resolve(settings.PIPER_MODEL_PATH)
    if configured.exists() and Path(str(configured) + ".json").exists():
        return configured

    found: list[Path] = []
    for d in _PIPER_MODEL_DIRS:
        dir_path = _resolve(d)
        if not dir_path.is_dir():
            continue
        for onnx in sorted(dir_path.glob("*.onnx")):
            # Sin el .json al lado, piper no puede usar el modelo.
            if Path(str(onnx) + ".json").exists():
                found.append(onnx)
    if found:
        # Empate en calidad => el archivo más grande, que suele ser el mejor.
        best = max(found, key=lambda p: (_model_quality(p), p.stat().st_size))
        if best != configured:
            log.info("Piper: usando modelo autodetectado %s", best.name)
        return best
    return configured


def _piper_ready() -> bool:
    bin_path = _piper_binary_path()
    model_path = _piper_model_path()
    json_path = Path(str(model_path) + ".json")
    return bin_path.exists() and model_path.exists() and json_path.exists()


def synthesize_piper(text: str, rate: str = DEFAULT_RATE) -> bytes:
    """Llama al binario piper.exe y devuelve WAV PCM."""
    if not _piper_ready():
        raise TTSError(
            "Piper no configurado. Faltan piper.exe o el modelo .onnx. "
            "Ver README sección 'Piper offline en Windows'."
        )
    bin_path = _piper_binary_path()
    model_path = _piper_model_path()
    # Piper no habla en porcentajes: usa length-scale, donde MÁS es más lento.
    # -25% de velocidad => escala 1/0.75 = 1.33.
    factor = 1.0 + _rate_percent(rate) / 100.0
    length_scale = 1.0 / factor if factor > 0.1 else 1.0
    try:
        proc = subprocess.run(
            [
                str(bin_path),
                "--model", str(model_path),
                "--length-scale", f"{length_scale:.3f}",
                "--output-raw",
            ],
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError as e:
        raise TTSError(f"No se pudo ejecutar piper: {e}") from e
    if proc.returncode != 0:
        raise TTSError(
            f"piper falló (code {proc.returncode}): "
            + proc.stderr.decode(errors="ignore")[:300]
        )
    raw_pcm = proc.stdout
    if not raw_pcm:
        raise TTSError("piper no produjo audio")
    return _pcm_to_wav(raw_pcm, sample_rate=_piper_sample_rate(model_path))


def _piper_sample_rate(model_path: Path, fallback: int = 22050) -> int:
    """Lee audio.sample_rate del .json del modelo.

    Hace falta porque autodetectamos el modelo: no todos son 22050 Hz, y
    asumir mal el sample rate deforma la voz (queda aguda o grave).
    """
    import json
    try:
        with open(str(model_path) + ".json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        rate = int(cfg.get("audio", {}).get("sample_rate", fallback))
        return rate if 8000 <= rate <= 48000 else fallback
    except Exception as e:
        log.warning("No pude leer el sample rate de %s: %s", model_path.name, e)
        return fallback


def _pcm_to_wav(pcm: bytes, sample_rate: int = 22050) -> bytes:
    """Envuelve PCM s16le mono en un contenedor WAV."""
    import io
    import wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)
    return buf.getvalue()


# === Cache en disco ===
# La misma frase se reproduce muchas veces (escuchar el ejemplo, repetir el
# diálogo, repaso SRS). Guardar el audio evita re-pedirlo a Microsoft y hace
# que la segunda reproducción funcione sin internet.

_CACHE_EXTS = {".mp3": "audio/mpeg", ".wav": "audio/wav"}
_MIME_EXT = {"audio/mpeg": ".mp3", "audio/wav": ".wav"}


def _cache_dir() -> Path:
    return _resolve(settings.TTS_CACHE_DIR)


def _cache_key(text: str, voice_key: str, rate: str) -> str:
    raw = f"{text}|{voice_key}|{rate}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _cache_get(key: str) -> tuple[bytes, str] | None:
    d = _cache_dir()
    for ext, mime in _CACHE_EXTS.items():
        p = d / f"{key}{ext}"
        if p.exists():
            try:
                data = p.read_bytes()
            except OSError as e:
                log.warning("No pude leer el cache %s: %s", p.name, e)
                return None
            if not data:
                return None
            # Tocar el archivo: la purga borra por fecha de uso (LRU).
            try:
                os.utime(p, None)
            except OSError:
                pass
            return data, mime
    return None


def _cache_put(key: str, audio: bytes, mime: str) -> None:
    ext = _MIME_EXT.get(mime)
    if not ext:
        return
    d = _cache_dir()
    try:
        d.mkdir(parents=True, exist_ok=True)
        # Escribir a temporal y renombrar: si dos requests piden la misma frase
        # a la vez, nadie lee un archivo a medio escribir.
        tmp = d / f"{key}.{os.getpid()}.tmp"
        tmp.write_bytes(audio)
        os.replace(tmp, d / f"{key}{ext}")
    except OSError as e:
        log.warning("No pude escribir el cache TTS: %s", e)
        return
    _prune_cache()


def _prune_cache() -> None:
    """Si el cache pasa el límite, borra los más viejos hasta el 80%."""
    limit = settings.TTS_CACHE_MAX_MB * 1024 * 1024
    if limit <= 0:
        return
    d = _cache_dir()
    try:
        files = [
            (p, p.stat()) for p in d.iterdir()
            if p.is_file() and p.suffix in _CACHE_EXTS
        ]
    except OSError:
        return
    total = sum(st.st_size for _, st in files)
    if total <= limit:
        return
    target = int(limit * 0.8)
    for p, st in sorted(files, key=lambda f: f[1].st_mtime):
        if total <= target:
            break
        try:
            p.unlink()
            total -= st.st_size
        except OSError:
            pass
    log.info("Cache TTS purgado a %.1f MB", total / 1024 / 1024)


def cache_stats() -> dict:
    d = _cache_dir()
    try:
        files = [p for p in d.iterdir() if p.is_file() and p.suffix in _CACHE_EXTS]
        size = sum(p.stat().st_size for p in files)
    except OSError:
        return {"entries": 0, "size_mb": 0.0, "max_mb": settings.TTS_CACHE_MAX_MB}
    return {
        "entries": len(files),
        "size_mb": round(size / 1024 / 1024, 2),
        "max_mb": settings.TTS_CACHE_MAX_MB,
    }


# === Orquestador ===

async def synthesize(
    text: str,
    voice_key: str | None = None,
    level: str | None = None,
    rate: str | None = None,
) -> tuple[bytes, str]:
    """Sintetiza texto. `rate` explícito gana; si no, se deduce del nivel."""
    text = text.strip()
    if not text:
        raise TTSError("Texto vacío")
    text = text[:600]
    voice_key = voice_key or settings.DEFAULT_VOICE
    rate = _normalize_rate(rate or rate_for_level(level))

    key = _cache_key(text, voice_key, rate)
    cached = _cache_get(key)
    if cached:
        log.debug("TTS: cache hit (%s)", key[:8])
        return cached

    edge_error: str | None = None
    if HAS_EDGE:
        try:
            audio = await synthesize_edge(text, voice_key, rate)
            log.info(
                "TTS: Edge OK (voz=%s, rate=%s, %d bytes)", voice_key, rate, len(audio)
            )
            _cache_put(key, audio, "audio/mpeg")
            return audio, "audio/mpeg"
        except TTSError as e:
            edge_error = str(e)
            log.warning("Edge TTS falló, intentando Piper: %s", edge_error)

    if _piper_ready():
        try:
            # piper.exe es un subprocess síncrono que tarda ~1 s: en threadpool,
            # sino bloquea el event loop y congela al resto de los requests.
            audio = await run_in_threadpool(synthesize_piper, text, rate)
            log.info("TTS: Piper OK (rate=%s, %d bytes)", rate, len(audio))
            _cache_put(key, audio, "audio/wav")
            return audio, "audio/wav"
        except TTSError as e:
            log.warning("Piper TTS no disponible: %s", e)

    detail = "Sin backend TTS disponible."
    if edge_error:
        detail += f" Edge: {edge_error}."
    raise TTSError(detail + " El frontend usará el TTS del navegador.")


def status() -> dict:
    model = _piper_model_path()
    return {
        "edge_available": HAS_EDGE,
        "piper_available": _piper_ready(),
        "piper_model": model.name if model.exists() else None,
        "default_voice": settings.DEFAULT_VOICE,
        "voices": list(VOICES_EDGE.keys()),
        "rates_by_level": RATE_BY_LEVEL,
        "cache": cache_stats(),
    }
