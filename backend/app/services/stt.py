"""Orquestador de Speech-to-Text: faster-whisper con Vosk como respaldo.

Whisper entiende bastante mejor a hablantes no nativos, así que va primero.
Vosk queda como fallback para quien ya lo tenga instalado o para máquinas
donde Whisper sea demasiado lento.

Se fuerza uno u otro con STT_ENGINE en .env: `auto` (default), `whisper`, `vosk`.
"""
from __future__ import annotations
import logging

from app.config import settings
from app.services import audio_utils


log = logging.getLogger(__name__)


class STTUnavailable(Exception):
    pass


def _engine_pref() -> str:
    return (settings.STT_ENGINE or "auto").strip().lower()


def _whisper():
    from app.services import whisper_stt
    return whisper_stt


def _vosk():
    """Importado tarde: si el paquete vosk no está, no queremos romper el arranque."""
    from app.services import vosk_stt
    return vosk_stt


def _vosk_or_none():
    try:
        return _vosk()
    except Exception as e:  # ImportError y cualquier otra sorpresa al cargar
        log.info("Vosk no disponible: %s", e)
        return None


def _preprocess(audio_bytes: bytes) -> bytes:
    """Limpia el audio si hay ffmpeg. Si no hay, se devuelve tal cual.

    Whisper decodifica solo (PyAV), así que ffmpeg es opcional para él; el
    filtrado igual ayuda con micrófonos flojos, así que lo aprovechamos.
    """
    if not audio_utils.has_ffmpeg():
        return audio_bytes
    try:
        return audio_utils.to_wav_16k_mono(audio_bytes)
    except audio_utils.AudioError as e:
        log.warning("No pude limpiar el audio (%s). Sigo con el original.", e)
        return audio_bytes


def transcribe(audio_bytes: bytes) -> tuple[str, str]:
    """Transcribe audio a inglés. Devuelve (texto, motor_usado)."""
    pref = _engine_pref()
    errors: list[str] = []

    if pref in ("auto", "whisper"):
        w = _whisper()
        if w.available():
            clean = _preprocess(audio_bytes)
            try:
                return w.transcribe(clean), "whisper"
            except w.STTUnavailable as e:
                errors.append(f"whisper: {e}")
                if pref == "whisper":
                    raise STTUnavailable(str(e)) from e
                log.warning("Whisper falló, intento con Vosk: %s", e)
        elif pref == "whisper":
            raise STTUnavailable(
                "STT_ENGINE=whisper pero faster-whisper no está instalado. "
                "Corré: pip install faster-whisper"
            )

    if pref in ("auto", "vosk"):
        v = _vosk_or_none()
        if v is not None and v.available():
            try:
                # Vosk necesita WAV 16 kHz mono: su transcribe() ya convierte.
                return v.transcribe(audio_bytes), "vosk"
            except v.STTUnavailable as e:
                errors.append(f"vosk: {e}")
        elif pref == "vosk":
            raise STTUnavailable(
                "STT_ENGINE=vosk pero el modelo Vosk o ffmpeg no están disponibles."
            )

    detail = " | ".join(errors) if errors else (
        "No hay motor STT disponible. Instalá faster-whisper "
        "(pip install faster-whisper) o configurá el modelo de Vosk."
    )
    raise STTUnavailable(detail)


def available() -> bool:
    pref = _engine_pref()
    if pref in ("auto", "whisper") and _whisper().available():
        return True
    if pref in ("auto", "vosk"):
        v = _vosk_or_none()
        if v is not None and v.available():
            return True
    return False


def diagnose() -> dict:
    v = _vosk_or_none()
    info = {
        "available": available(),
        "engine_preference": _engine_pref(),
        "ffmpeg_in_path": audio_utils.has_ffmpeg(),
        "whisper": _whisper().diagnose(),
        "vosk": v.diagnose() if v is not None else {"vosk_available": False},
    }
    # Compatibilidad: el frontend viejo leía `vosk_available` en la raíz.
    info["vosk_available"] = bool(info["vosk"].get("vosk_available"))
    return info
