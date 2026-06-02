"""Endpoints de diálogos guionados."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.user import User
from app.models.dialogue import Dialogue, DialogueTurn
from app.routers.deps import get_current_user
from app.services import dialogue_engine


router = APIRouter(prefix="/api/dialogues", tags=["dialogues"])


@router.get("")
def list_dialogues(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    dialogues = (
        db.query(Dialogue)
        .order_by(Dialogue.order_index, Dialogue.id)
        .all()
    )
    return [
        {
            "id": d.id, "slug": d.slug,
            "title_es": d.title_es, "title_en": d.title_en,
            "description_es": d.description_es,
            "setting_es": d.setting_es, "setting_en": d.setting_en or "",
            "npc_name": d.npc_name, "npc_role_es": d.npc_role_es,
            "icon": d.icon, "difficulty": d.difficulty,
            "is_adult": d.is_adult, "level": d.level,
        }
        for d in dialogues
    ]


@router.get("/{dialogue_id}")
def get_dialogue(
    dialogue_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    d = (
        db.query(Dialogue)
        .options(selectinload(Dialogue.turns))
        .filter(Dialogue.id == dialogue_id)
        .first()
    )
    if not d:
        raise HTTPException(404, "Diálogo no encontrado")
    return {
        "id": d.id, "slug": d.slug,
        "title_es": d.title_es, "title_en": d.title_en,
        "description_es": d.description_es,
        "setting_es": d.setting_es, "setting_en": d.setting_en or "",
        "npc_name": d.npc_name, "npc_role_es": d.npc_role_es,
        "icon": d.icon, "difficulty": d.difficulty,
        "is_adult": d.is_adult,
        "key_vocabulary": d.key_vocabulary,
        "turns": [
            {
                "id": t.id,
                "order_index": t.order_index,
                "speaker": t.speaker,
                "npc_text_en": t.npc_text_en,
                "npc_text_es": t.npc_text_es,
                "user_hint_es": t.user_hint_es,
                "user_example_en": t.user_example_en,
                "helper_phrases": t.helper_phrases,
                # NO devolvemos required_keywords — para no "hacer trampa"
            }
            for t in d.turns
        ],
    }


class TurnCheckIn(BaseModel):
    turn_id: int
    user_text: str = Field(min_length=1, max_length=1000)


@router.post("/turn/check")
def check_turn(
    payload: TurnCheckIn,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    turn = db.get(DialogueTurn, payload.turn_id)
    if not turn or turn.speaker != "USER":
        raise HTTPException(404, "Turno no encontrado o no es del usuario")
    result = dialogue_engine.evaluate_turn(
        user_text=payload.user_text,
        required_keywords=turn.required_keywords or [],
        user_example_en=turn.user_example_en or "",
    )
    return {
        **result,
        "example_en": turn.user_example_en,
    }
