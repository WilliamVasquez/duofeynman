"""Text-to-Speech con dos backends en cascada.

1. Edge TTS — voces Microsoft Neural (online, gratis, sin API key)
   Aria, Jenny, Guy son casi indistinguibles de un humano.

2. Piper TTS — neural offline mediante el BINARIO standalone (no el paquete pip,
   que no tiene wheels para Windows). Fallback cuando no hay internet.

Si ninguno está disponible, /api/tts devuelve 503 y el frontend usa el
speechSynthesis del navegador como último recurso.
"""
from __future__ import annotations
import logging
import shutil
import subprocess
from pathlib import Path

import httpx

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


# === Edge TTS ===

async def synthesize_edge(text: str, voice_key: str) -> bytes:
    """Genera MP3 con Microsoft Edge TTS (online, neural).

    No hacemos pre-check de internet: si edge-tts falla, su excepción
    decide. Es más confiable que adivinar conectividad con un HEAD.
    """
    if not HAS_EDGE:
        raise TTSError("edge-tts no instalado")
    voice = VOICES_EDGE.get(voice_key, VOICES_EDGE[settings.DEFAULT_VOICE])
    chunks: list[bytes] = []
    try:
        communicate = edge_tts.Communicate(text, voice, rate="-10%")
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


def _piper_binary_path() -> Path:
    return _resolve(settings.PIPER_BINARY_PATH)


def _piper_model_path() -> Path:
    return _resolve(settings.PIPER_MODEL_PATH)


def _piper_ready() -> bool:
    bin_path = _piper_binary_path()
    model_path = _piper_model_path()
    json_path = Path(str(model_path) + ".json")
    return bin_path.exists() and model_path.exists() and json_path.exists()


def synthesize_piper(text: str) -> bytes:
    """Llama al binario piper.exe y devuelve WAV PCM."""
    if not _piper_ready():
        raise TTSError(
            "Piper no configurado. Faltan piper.exe o el modelo .onnx. "
            "Ver README sección 'Piper offline en Windows'."
        )
    bin_path = _piper_binary_path()
    model_path = _piper_model_path()
    try:
        proc = subprocess.run(
            [
                str(bin_path),
                "--model", str(model_path),
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
    return _pcm_to_wav(raw_pcm, sample_rate=22050)


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


# === Orquestador ===

async def synthesize(text: str, voice_key: str | None = None) -> tuple[bytes, str]:
    text = text.strip()
    if not text:
        raise TTSError("Texto vacío")
    text = text[:600]
    voice_key = voice_key or settings.DEFAULT_VOICE

    edge_error: str | None = None
    if HAS_EDGE:
        try:
            audio = await synthesize_edge(text, voice_key)
            log.info("TTS: Edge OK (voz=%s, %d bytes)", voice_key, len(audio))
            return audio, "audio/mpeg"
        except TTSError as e:
            edge_error = str(e)
            log.warning("Edge TTS falló, intentando Piper: %s", edge_error)

    if _piper_ready():
        try:
            audio = synthesize_piper(text)
            log.info("TTS: Piper OK (%d bytes)", len(audio))
            return audio, "audio/wav"
        except TTSError as e:
            log.warning("Piper TTS no disponible: %s", e)

    detail = "Sin backend TTS disponible."
    if edge_error:
        detail += f" Edge: {edge_error}."
    raise TTSError(detail + " El frontend usará el TTS del navegador.")


def status() -> dict:
    return {
        "edge_available": HAS_EDGE,
        "piper_available": _piper_ready(),
        "default_voice": settings.DEFAULT_VOICE,
        "voices": list(VOICES_EDGE.keys()),
    }
