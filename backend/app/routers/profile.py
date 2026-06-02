"""Endpoints del perfil del usuario."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.profile import UserProfile
from app.routers.deps import get_current_user


router = APIRouter(prefix="/api/me/profile", tags=["profile"])


DEFAULT_INTERESTS = {
    "work": True, "relationship": True, "family": True,
    "health": True, "travel": True, "social": True,
    "shopping": True, "adult": False,
}


class ProfileIn(BaseModel):
    nickname: str = ""
    job: str = ""
    city: str = ""
    has_partner: bool = False
    partner_name: str = ""
    has_kids: bool = False
    hobbies: str = ""
    travels_often: bool = False
    daily_goal_minutes: int = Field(default=15, ge=5, le=120)
    interests: dict = Field(default_factory=dict)
    hidden_items: dict = Field(default_factory=dict)


class ProfileOut(ProfileIn):
    user_id: int
    updated_at: str | None = None

    class Config:
        from_attributes = True


def _to_dict(p: UserProfile) -> dict:
    return {
        "user_id": p.user_id,
        "nickname": p.nickname or "",
        "job": p.job or "",
        "city": p.city or "",
        "has_partner": bool(p.has_partner),
        "partner_name": p.partner_name or "",
        "has_kids": bool(p.has_kids),
        "hobbies": p.hobbies or "",
        "travels_often": bool(p.travels_often),
        "daily_goal_minutes": int(p.daily_goal_minutes or 15),
        "interests": p.interests or DEFAULT_INTERESTS,
        "hidden_items": p.hidden_items or {"dialogues": [], "topics": []},
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@router.get("")
def get_profile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    p = db.query(UserProfile).filter_by(user_id=user.id).first()
    if not p:
        # Devolver default vacío sin crearlo aún
        return {
            "user_id": user.id,
            "nickname": "", "job": "", "city": "",
            "has_partner": False, "partner_name": "",
            "has_kids": False, "hobbies": "",
            "travels_often": False, "daily_goal_minutes": 15,
            "interests": DEFAULT_INTERESTS,
            "hidden_items": {"dialogues": [], "topics": []},
            "updated_at": None,
        }
    return _to_dict(p)


@router.put("")
def put_profile(
    payload: ProfileIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upsert del perfil."""
    p = db.query(UserProfile).filter_by(user_id=user.id).first()
    if not p:
        p = UserProfile(user_id=user.id)
        db.add(p)

    p.nickname = payload.nickname.strip()[:120]
    p.job = payload.job.strip()[:255]
    p.city = payload.city.strip()[:120]
    p.has_partner = bool(payload.has_partner)
    p.partner_name = payload.partner_name.strip()[:120]
    p.has_kids = bool(payload.has_kids)
    p.hobbies = payload.hobbies.strip()[:500]
    p.travels_often = bool(payload.travels_often)
    p.daily_goal_minutes = max(5, min(120, int(payload.daily_goal_minutes)))
    # Mergear con defaults para no perder keys nuevas
    p.interests = {**DEFAULT_INTERESTS, **(payload.interests or {})}
    p.hidden_items = payload.hidden_items or {"dialogues": [], "topics": []}

    db.commit()
    db.refresh(p)
    return _to_dict(p)
