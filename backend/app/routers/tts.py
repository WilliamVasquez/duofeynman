"""Endpoint TTS: genera audio neural con fallback automático."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from app.models.user import User
from app.routers.deps import get_current_user
from app.services import tts as tts_service
from app.services.rate_limit import limiter


router = APIRouter(prefix="/api/tts", tags=["tts"])


@router.get("")
@limiter.limit("60/minute")
async def synthesize(
    request: Request,
    text: str = Query(..., min_length=1, max_length=600),
    voice: str | None = Query(None),
    _user: User = Depends(get_current_user),
):
    try:
        audio, mime = await tts_service.synthesize(text, voice)
    except tts_service.TTSError as e:
        raise HTTPException(503, str(e))
    return Response(
        content=audio,
        media_type=mime,
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/status")
def status(_user: User = Depends(get_current_user)):
    return tts_service.status()
