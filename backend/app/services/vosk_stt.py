"""Speech-to-Text offline con Vosk.

Descargá el modelo `vosk-model-small-en-us-0.15` (~40 MB) desde
https://alphacephei.com/vosk/models y descomprimilo en `backend/models/vosk-en-small/`.

Vosk espera audio WAV mono PCM 16-bit a 16 kHz. El frontend graba en webm/opus,
así que lo convertimos con ffmpeg en memoria.
"""
from __future__ import annotations
import json
import logging
import shutil
import subprocess
import wave
from io import BytesIO
from pathlib import Path

from vosk import Model, KaldiRecognizer, SetLogLevel

from app.config import settings


log = logging.getLogger(__name__)
SetLogLevel(-1)  # silenciar logs de Vosk


class STTUnavailable(Exception):
    pass


_model: Model | None = None


def _model_dir() -> Path:
    p = Path(settings.VOSK_MODEL_PATH)
    if not p.is_absolute():
        # relativo al directorio backend/
        p = Path(__file__).resolve().parent.parent.parent / p
    return p


def get_model() -> Model:
    global _model
    if _model is None:
        path = _model_dir()
        if not path.exists():
            raise STTUnavailable(
                f"Modelo Vosk no encontrado en {path}. "
                "Descargá vosk-model-small-en-us-0.15 desde "
                "https://alphacephei.com/vosk/models"
            )
        log.info("Cargando modelo Vosk desde %s ...", path)
        _model = Model(str(path))
        log.info("Modelo Vosk listo.")
    return _model


def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


# Limpieza de audio antes del STT: recorta el retumbe de baja frecuencia,
# hace de anti-alias antes del resample a 16 kHz, y nivela el volumen para
# micrófonos flojos o grabaciones lejanas.
AUDIO_FILTER = "highpass=f=80,lowpass=f=8000,dynaudnorm=f=200:g=15"


def _run_ffmpeg(audio_bytes: bytes, audio_filter: str | None) -> subprocess.CompletedProcess:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0"]
    if audio_filter:
        cmd += ["-af", audio_filter]
    cmd += ["-ac", "1", "-ar", "16000", "-f", "wav", "pipe:1"]
    return subprocess.run(cmd, input=audio_bytes, capture_output=True, check=False)


def _to_wav_16k_mono(audio_bytes: bytes) -> bytes:
    """Convierte cualquier formato a WAV PCM 16 kHz mono usando ffmpeg."""
    if not _has_ffmpeg():
        raise STTUnavailable(
            "ffmpeg no está instalado o no está en PATH. "
            "Descargalo de https://ffmpeg.org/download.html y agregalo al PATH."
        )
    proc = _run_ffmpeg(audio_bytes, AUDIO_FILTER)
    if proc.returncode != 0:
        # Un ffmpeg viejo puede no tener dynaudnorm. Antes de dar error,
        # reintentar sin filtros: mejor transcribir crudo que no transcribir.
        log.warning(
            "ffmpeg falló con filtros (%s). Reintentando sin filtros.",
            proc.stderr.decode(errors="ignore")[:200],
        )
        proc = _run_ffmpeg(audio_bytes, None)
    if proc.returncode != 0:
        log.warning("ffmpeg falló: %s", proc.stderr.decode(errors="ignore"))
        raise STTUnavailable("No se pudo convertir el audio. ¿Formato inválido?")
    return proc.stdout


def transcribe(audio_bytes: bytes) -> str:
    """Transcribe audio (webm/opus/wav/ogg) a texto inglés."""
    wav = _to_wav_16k_mono(audio_bytes)
    model = get_model()

    with wave.open(BytesIO(wav), "rb") as wf:
        rec = KaldiRecognizer(model, wf.getframerate())
        rec.SetWords(False)
        results: list[str] = []
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                part = json.loads(rec.Result()).get("text", "")
                if part:
                    results.append(part)
        final = json.loads(rec.FinalResult()).get("text", "")
        if final:
            results.append(final)

    return " ".join(results).strip()


def available() -> bool:
    try:
        return _model_dir().exists() and _has_ffmpeg()
    except Exception:
        return False


def diagnose() -> dict:
    """Diagnóstico detallado para debug. Útil para ver qué falta."""
    info = {
        "vosk_available": False,
        "model_path_expected": None,
        "model_path_exists": False,
        "ffmpeg_in_path": _has_ffmpeg(),
    }
    try:
        p = _model_dir()
        info["model_path_expected"] = str(p)
        info["model_path_exists"] = p.exists()
        info["vosk_available"] = info["model_path_exists"] and info["ffmpeg_in_path"]
    except Exception as e:
        info["error"] = str(e)
    return info
