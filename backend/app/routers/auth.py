"""Registro y login."""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserOut, Token
from app.services.security import hash_password, verify_password, create_access_token
from app.services.rate_limit import limiter


router = APIRouter(prefix="/api/auth", tags=["auth"])
audit_log = logging.getLogger("duofeynman.audit")


@router.post("/register", response_model=Token, status_code=201)
@limiter.limit("3/hour")
def register(request: Request, payload: UserCreate, db: Session = Depends(get_db)):
    exists = db.query(User).filter(
        or_(User.email == payload.email, User.username == payload.username)
    ).first()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email o usuario ya registrado")

    user = User(
        email=payload.email,
        username=payload.username,
        password_hash=hash_password(payload.password),
        target_level=payload.target_level,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, payload: UserLogin, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "?"
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        audit_log.warning("login_fail email=%s ip=%s", payload.email, client_ip)
        # Mensaje genérico para no leakear si el email existe o no
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")

    user.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    audit_log.info("login_ok user_id=%s ip=%s", user.id, client_ip)

    token = create_access_token(user.id)
    return Token(access_token=token, user=UserOut.model_validate(user))
