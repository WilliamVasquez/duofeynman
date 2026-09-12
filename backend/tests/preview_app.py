"""Servidor E2E sólo local: SQLite en memoria, usuario ficticio, voz/gramática simuladas.

Desde backend/: python -m uvicorn tests.preview_app:app --host 127.0.0.1 --port 8766
No usar en producción. No toca MySQL, el seed ni archivos de audio del usuario.
"""
import io
import json
import wave
from pathlib import Path
from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app import main
from app.database import get_db
from app.models import User, Module, Lesson, Topic, Dialogue, DialogueTurn
from app.routers.deps import get_current_user
from app.services import tts, analyzer, error_drills

main.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
Factory = sessionmaker(bind=main.engine, autoflush=False)
app = main.app


def db_session():
    with Factory() as db:
        yield db


def fake_user(db=Depends(get_db)):
    return db.get(User, 1)


app.dependency_overrides[get_db] = db_session
app.dependency_overrides[get_current_user] = fake_user


async def fake_audio(*args, **kwargs):
    output = io.BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(16000)
        wav.writeframes(b'\0' * 16000)
    return output.getvalue(), 'audio/wav'


async def local_grammar(text):
    return analyzer.apply_custom_rules(text)


tts.synthesize = fake_audio
analyzer.check_grammar = local_grammar


@app.on_event('startup')
def fixtures():
    root = Path(__file__).parents[1] / 'app/data/curriculum'
    with Factory() as db:
        db.add(User(id=1, email='preview@example.com', username='Preview', password_hash='unused'))
        for m in json.loads((root/'a1_curriculum.json').read_text(encoding='utf-8'))['modules']:
            module = Module(**{k:v for k,v in m.items() if k!='lessons'})
            db.add(module); db.flush()
            for l in m['lessons']:
                lesson = Lesson(module_id=module.id, **{k:v for k,v in l.items() if k!='topics'})
                db.add(lesson); db.flush()
                for t in l['topics']:
                    db.add(Topic(lesson_id=lesson.id, **t))
        for d in json.loads((root/'dialogues.json').read_text(encoding='utf-8'))['dialogues']:
            dialogue = Dialogue(**{k:v for k,v in d.items() if k!='turns'})
            db.add(dialogue); db.flush()
            for i, t in enumerate(d['turns']):
                db.add(DialogueTurn(dialogue_id=dialogue.id, order_index=i, **{k:v for k,v in t.items() if k!='order_index'}))
        db.flush()
        error_drills.capture(db, 1, analyzer.apply_custom_rules('I tired.'))
        db.commit()
