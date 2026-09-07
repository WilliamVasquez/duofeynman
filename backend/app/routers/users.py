from fastapi import APIRouter, Depends
from app.models.user import User
from app.schemas.user import UserOut
from app.routers.deps import get_current_user
from app.database import get_db
from sqlalchemy.orm import Session
from app.services.gamification import calculate_streak

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("", response_model=UserOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = UserOut.model_validate(user)
    result.streak_days = calculate_streak(db, user)
    return result
