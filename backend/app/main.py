"""DuoFeynman — backend principal."""
import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.database import Base, engine
from app import models  # noqa: F401
from app.routers import auth, users, curriculum, attempts, progress, tts, srs, dictation, dialogues, profile as profile_router
from app.services.rate_limit import limiter


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


app = FastAPI(
    title="DuoFeynman API",
    description="Aprendé inglés hablado con el método Feynman.",
    version="0.1.0",
    # Ocultar docs en producción para no exponer la superficie de ataque
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

# === Rate limiting ===
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Demasiadas peticiones. Esperá un momento y volvé a intentar."},
    )


# Manejador global para no leakear stack traces en producción
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log = logging.getLogger("duofeynman.error")
    log.exception("Error no manejado en %s %s", request.method, request.url.path)
    if settings.is_production:
        return JSONResponse(
            status_code=500,
            content={"detail": "Error interno del servidor."},
        )
    # En dev, dejamos pasar el detalle para debug
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {exc}"},
    )


# === CORS ===
# En producción: solo los orígenes explícitos del .env.
# En dev: además localhost en cualquier puerto, pero NO wildcard.
_cors_origins = list(settings.cors_list)
if not settings.is_production:
    _cors_origins += [
        "http://localhost:8000", "http://127.0.0.1:8000",
        "http://localhost:5500", "http://127.0.0.1:5500",
        "http://localhost:3000", "http://127.0.0.1:3000",
    ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)


# === Security headers ===
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(self), camera=()"
    if settings.is_production:
        # HSTS solo cuando hay HTTPS — si activás esto sin HTTPS, te cierra el sitio
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # CSP estricto. Si servís frontend desde otro dominio, ajustá.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "media-src 'self' blob: data:; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'none';"
        )
    return response


@app.on_event("startup")
def on_startup():
    # Crear tablas si no existen (en dev). En prod usar Alembic.
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    from app.services import vosk_stt
    return {
        "status": "ok",
        "env": settings.APP_ENV,
        "vosk_stt_available": vosk_stt.available(),
    }


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(curriculum.router)
app.include_router(attempts.router)
app.include_router(progress.router)
app.include_router(tts.router)
app.include_router(srs.router)
app.include_router(dictation.router)
app.include_router(dialogues.router)
app.include_router(profile_router.router)


# Servir frontend estático (mismo dominio = sin lío de CORS)
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def root():
        index = FRONTEND_DIR / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return {"message": "DuoFeynman API. Frontend no encontrado."}
