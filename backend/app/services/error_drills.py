"""Mini ejercicios de corrección derivados sólo de errores con sugerencia explícita."""
import hashlib
from app.timeutils import learning_day
from datetime import date
from app.models import SrsCard
from app.services.text_utils import normalize


def capture(db, user_id, errors, topic_id=None):
    existing = {(c.payload or {}).get("key"): c for c in db.query(SrsCard).filter_by(user_id=user_id, card_type="ERROR_DRILL").all()}
    for error in errors[:20]:
        wrong, right = str(error.get("span_text") or "").strip(), str(error.get("suggestion") or "").strip()
        if not wrong or not right or normalize(wrong) == normalize(right) or len(right) > 500:
            continue
        key = hashlib.sha256((str(error.get("rule_id")) + "|" + normalize(wrong) + "|" + normalize(right)).encode()).hexdigest()
        card = existing.get(key)
        if card:
            card.due_date = min(card.due_date or learning_day(), learning_day())
            card.payload = {**card.payload, "occurrences": card.payload.get("occurrences", 1) + 1}
        else:
            card = SrsCard(user_id=user_id, topic_id=topic_id, card_type="ERROR_DRILL", front=wrong, back=right,
                payload={"key": key, "explanation_es": error.get("explanation_es", ""), "occurrences": 1})
            db.add(card)
            existing[key] = card
