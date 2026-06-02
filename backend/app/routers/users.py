from fastapi import APIRouter, Depends
from app.models.user import User
from app.schemas.user import UserOut
from app.routers.deps import get_current_user

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)
