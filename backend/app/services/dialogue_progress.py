"""Reanudación y retiro gradual de ayudas, sin confundir omitir con dominar."""
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from app.models import DialogueSession, DialogueResponse
from app.timeutils import utcnow
import re

MODES = ("choose", "order", "type")


def personalize(text, profile):
    if not profile:
        return text
    for original, value in (("William", profile.nickname), ("Sofia", profile.partner_name)):
        if value and value.strip():
            name = value.strip()
            text = re.sub(r'\b' + original + r'\b', lambda _: name, text)
            text = re.sub(r'\b' + original.lower() + r'\b', lambda _: name.lower(), text)
    return text


def owned(db, user, session_id):
    session = db.query(DialogueSession).filter_by(id=str(session_id), user_id=user.id).with_for_update().first()
    if not session:
        raise HTTPException(404, "Conversation session not found.")
    return session


def state(db, session):
    responses = db.query(DialogueResponse).filter_by(session_id=session.id, run_number=session.run_number).order_by(DialogueResponse.created_at, DialogueResponse.id).all()
    return {
        "id": session.id, "run_number": session.run_number, "cursor": session.cursor,
        "completed": session.completed_at is not None, "completed_runs": session.completed_runs,
        "recommended_mode": MODES[session.support_stage], "stage_successes": session.stage_successes,
        "responses": [{"id": r.id, "turn_index": r.turn_index, "text": r.user_text,
                       "mode": r.mode, "used_help": r.used_help, "continued": r.continued,
                       "score": r.result["score"], "passed": r.result["passed"], "result": r.result} for r in responses],
    }


def start(db, user, dialogue, snapshot):
    session = db.query(DialogueSession).filter_by(user_id=user.id, dialogue_id=dialogue.id).with_for_update().first()
    if session is None:
        session = DialogueSession(user_id=user.id, dialogue_id=dialogue.id, snapshot=snapshot)
        db.add(session)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            session = db.query(DialogueSession).filter_by(user_id=user.id, dialogue_id=dialogue.id).with_for_update().one()
    elif session.completed_at:
        session.snapshot = snapshot
        session.cursor = 0
        session.run_number += 1
        session.completed_at = None
    # Cursor apunta al próximo USER; el cliente reconstruye los NPC previos.
    turns = session.snapshot["turns"]
    while session.cursor < len(turns) and turns[session.cursor]["speaker"] != "USER":
        session.cursor += 1
    db.commit()
    return session


def advance(db, session):
    session.cursor += 1
    turns = session.snapshot["turns"]
    while session.cursor < len(turns) and turns[session.cursor]["speaker"] != "USER":
        session.cursor += 1
    if session.cursor < len(turns):
        return
    session.completed_at = utcnow()
    session.completed_runs += 1
    db.flush()
    responses = db.query(DialogueResponse).filter_by(session_id=session.id, run_number=session.run_number).all()
    expected = sum(t["speaker"] == "USER" for t in turns)
    ranks = {"choose": 0, "order": 1, "type": 2, "speak": 2}
    # Dos recorridos limpios habilitan la próxima ayuda sugerida. Todos los
    # modos siguen disponibles; errores/omisiones nunca bloquean la salida.
    clean = len(responses) == expected and expected > 0 and all(
        r.result["passed"] and not r.continued and not r.used_help
        and ranks[r.mode] >= session.support_stage for r in responses)
    session.stage_successes = session.stage_successes + 1 if clean else 0
    if session.stage_successes >= 2 and session.support_stage < 2:
        session.support_stage += 1
        session.stage_successes = 0


def public_dialogue(session):
    return {**session.snapshot, "turns": [{k: v for k, v in t.items() if k != "required_keywords"} for t in session.snapshot["turns"]]}
