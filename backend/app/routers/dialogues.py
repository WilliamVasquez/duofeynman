"""Endpoints de diálogos guionados."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from uuid import UUID
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.user import User
from app.models.dialogue import Dialogue, DialogueTurn
from app.routers.deps import get_current_user
from app.services import dialogue_engine
from app.services import dialogue_progress
from app.models import DialogueSession, DialogueResponse, UserProfile


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
    progress = {s.dialogue_id: s for s in db.query(DialogueSession).filter_by(user_id=_user.id).all()}
    return [
        {
            "id": d.id, "slug": d.slug,
            "title_es": d.title_es, "title_en": d.title_en,
            "description_es": d.description_es,
            "setting_es": d.setting_es, "setting_en": d.setting_en or "",
            "npc_name": d.npc_name, "npc_role_es": d.npc_role_es,
            "icon": d.icon, "difficulty": d.difficulty,
            "is_adult": d.is_adult, "level": d.level,
            "progress": ({"completed_runs": progress[d.id].completed_runs,
                          "resumable": progress[d.id].completed_at is None,
                          "recommended_mode": dialogue_progress.MODES[progress[d.id].support_stage]}
                         if d.id in progress else None),
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
                "answer_options": t.answer_options or [],
                # NO devolvemos required_keywords — para no "hacer trampa"
            }
            for t in d.turns
        ],
    }


class TurnCheckIn(BaseModel):
    turn_id: int
    user_text: str = Field(min_length=1, max_length=1000)
    session_id: UUID | None = None
    response_id: UUID | None = None
    run_number: int = Field(default=1, ge=1)
    mode: Literal["choose", "order", "type", "speak"] = "type"
    used_help: bool = False


@router.post("/{dialogue_id}/session")
def start_session(dialogue_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    snapshot = get_dialogue(dialogue_id, db, user)
    dialogue = db.get(Dialogue, dialogue_id)
    for item, turn in zip(snapshot["turns"], dialogue.turns):
        item["required_keywords"] = turn.required_keywords or []
    session = dialogue_progress.start(db, user, dialogue, snapshot)
    return {"dialogue": dialogue_progress.public_dialogue(session), "session": dialogue_progress.state(db, session)}


class ContinueIn(BaseModel):
    response_id: UUID


@router.post("/session/{session_id}/continue")
def continue_session(session_id: UUID, payload: ContinueIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = dialogue_progress.owned(db, user, session_id)
    response = db.get(DialogueResponse, str(payload.response_id))
    if not response or response.session_id != session.id or response.run_number != session.run_number:
        raise HTTPException(404, "Response not found.")
    if not response.continued:
        if response.turn_index != session.cursor or not response.result["can_continue"] or response.result["passed"]:
            raise HTTPException(409, "This turn has already moved on. Reopen the conversation.")
        response.continued = True
        dialogue_progress.advance(db, session)
        db.commit()
    return dialogue_progress.state(db, session)


@router.post("/turn/check")
def check_turn(
    payload: TurnCheckIn,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    session = None
    if payload.session_id:
        session = dialogue_progress.owned(db, _user, payload.session_id)
        if not payload.response_id:
            raise HTTPException(422, "A response ID is required.")
        previous = db.get(DialogueResponse, str(payload.response_id))
        if previous:
            if previous.session_id != session.id or previous.run_number != payload.run_number:
                raise HTTPException(409, "Response ID already used.")
            return {**previous.result, "session": dialogue_progress.state(db, session), "response_id": previous.id}
        if session.completed_at or payload.run_number != session.run_number:
            raise HTTPException(409, "This conversation has moved on. Reopen it.")
        from types import SimpleNamespace
        turn = SimpleNamespace(**session.snapshot["turns"][session.cursor])
        if turn.id != payload.turn_id:
            raise HTTPException(409, "Answer the current turn first.")
    else:
        # Compatibilidad con clientes antiguos: sólo evalúa, no inventa progreso.
        turn = db.get(DialogueTurn, payload.turn_id)
        if not turn or turn.speaker != "USER":
            raise HTTPException(404, "Turno no encontrado o no es del usuario")
    # Todo lo que la app le ofreció al usuario cuenta como respuesta válida:
    # las opciones del modo Choose y las helper_phrases. Sin esto la app
    # rechaza sus propias sugerencias (ver dialogue_engine).
    accepted = [
        *(o.get("en", "") for o in (turn.answer_options or []) if isinstance(o, dict)),
        *(turn.helper_phrases or []),
    ]
    profile = db.query(UserProfile).filter_by(user_id=_user.id).first()
    accepted += [dialogue_progress.personalize(text, profile) for text in [turn.user_example_en or '', *accepted]]
    result = dialogue_engine.evaluate_turn(
        user_text=payload.user_text,
        required_keywords=turn.required_keywords or [],
        user_example_en=turn.user_example_en or "",
        accepted_answers=accepted,
    )
    result = {
        **result,
        "example_en": turn.user_example_en,
    }
    if result["code_switch_words"]:
        result["feedback_en"] = "Try using English for: " + ", ".join(result["code_switch_words"][:3]) + "."
    elif result["passed"]:
        result["feedback_en"] = "Good! You can move on." if result["score"] < .9 else "Great! That is a natural answer."
    else:
        result["feedback_en"] = "Try a fuller answer for this situation. You can use a suggestion or continue anyway."
    if session:
        from app.services import analyzer, error_drills
        errors = analyzer.apply_custom_rules(payload.user_text) if payload.mode in ("type", "speak") else []
        result["errors"] = errors
        error_drills.capture(db, _user.id, errors)
        response = DialogueResponse(id=str(payload.response_id), session_id=session.id,
            run_number=session.run_number, turn_index=session.cursor, user_text=payload.user_text,
            mode=payload.mode, used_help=payload.used_help, continued=False, result=result)
        db.add(response)
        if result["passed"]:
            dialogue_progress.advance(db, session)
        db.commit()
        return {**result, "session": dialogue_progress.state(db, session), "response_id": response.id}
    return result
