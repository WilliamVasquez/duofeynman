"""Conversión y limpieza de audio con ffmpeg, compartida por los motores STT."""
from __future__ import annotations
import logging
import shutil
import subprocess


log = logging.getLogger(__name__)


class AudioError(Exception):
    pass


# Limpieza antes del STT: recorta el retumbe de baja frecuencia, hace de
# anti-alias antes del resample a 16 kHz, y nivela el volumen para micrófonos
# flojos o grabaciones lejanas.
AUDIO_FILTER = "highpass=f=80,lowpass=f=8000,dynaudnorm=f=200:g=15"


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _run_ffmpeg(audio_bytes: bytes, audio_filter: str | None) -> subprocess.CompletedProcess:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0"]
    if audio_filter:
        cmd += ["-af", audio_filter]
    cmd += ["-ac", "1", "-ar", "16000", "-f", "wav", "pipe:1"]
    return subprocess.run(cmd, input=audio_bytes, capture_output=True, check=False)


def to_wav_16k_mono(audio_bytes: bytes) -> bytes:
    """Convierte cualquier formato a WAV PCM 16 kHz mono, ya filtrado."""
    if not has_ffmpeg():
        raise AudioError(
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
        raise AudioError("No se pudo convertir el audio. ¿Formato inválido?")
    return proc.stdout
