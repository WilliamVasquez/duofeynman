"""Rate limiting global con slowapi.

Política:
- /api/auth/login → 5 intentos por minuto por IP (anti-brute-force)
- /api/auth/register → 3 cuentas por hora por IP (anti-spam)
- /api/attempts/transcribe → 20 por minuto por usuario (anti-DoS de audio)
- /api/tts → 60 por minuto por usuario (anti-abuso de TTS)
- Default global → 120 req/min por IP
"""
from slowapi import Limiter
from slowapi.util import get_remote_address


# Limiter global. Las rutas usan @limiter.limit(...) para reglas específicas.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["120/minute"],
    storage_uri="memory://",  # en memoria; para multi-proceso usar redis://
)
