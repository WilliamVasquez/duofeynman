"""Carga inicial del curriculum desde JSON.

Uso:
    python -m app.seed
"""
import json
import logging
from pathlib import Path

from app.database import SessionLocal, engine, Base
from app.models.curriculum import Module, Lesson, Topic
from app.models.progress import Achievement
from app.models.dialogue import Dialogue, DialogueTurn
from app import models  # noqa: F401  (asegura registro de todos los modelos)


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("seed")


CURRICULUM_PATH = Path(__file__).parent / "data" / "curriculum" / "a1_curriculum.json"
DIALOGUES_PATH = Path(__file__).parent / "data" / "curriculum" / "dialogues.json"


ACHIEVEMENTS = [
    {"code": "first_steps", "title_es": "Primeros pasos", "description_es": "Completaste tu primer intento.", "icon": "footprints", "xp_reward": 10},
    {"code": "first_mastered", "title_es": "Primer dominio", "description_es": "Dominaste tu primer tema.", "icon": "star", "xp_reward": 25},
    {"code": "streak_7", "title_es": "Una semana", "description_es": "Practicaste 7 días seguidos.", "icon": "flame", "xp_reward": 50},
    {"code": "no_spanish", "title_es": "Sin code-switching", "description_es": "Completaste un tema sin meter palabras en español.", "icon": "shield-check", "xp_reward": 30},
    {"code": "fluent_minute", "title_es": "Un minuto fluido", "description_es": "Hablaste 60 segundos sin pausa larga.", "icon": "zap", "xp_reward": 40},
]


def seed():
    log.info("Creando tablas...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if not CURRICULUM_PATH.exists():
            log.error("No existe %s", CURRICULUM_PATH)
            return

        data = json.loads(CURRICULUM_PATH.read_text(encoding="utf-8"))

        for m_data in data["modules"]:
            module = db.query(Module).filter_by(slug=m_data["slug"]).first()
            if not module:
                module = Module(
                    slug=m_data["slug"],
                    title_es=m_data["title_es"],
                    title_en=m_data["title_en"],
                    description_es=m_data["description_es"],
                    level=m_data["level"],
                    order_index=m_data["order_index"],
                )
                db.add(module)
                db.flush()
                log.info("  + Módulo: %s", module.slug)

            for l_data in m_data.get("lessons", []):
                lesson = (
                    db.query(Lesson)
                    .filter_by(module_id=module.id, slug=l_data["slug"])
                    .first()
                )
                if not lesson:
                    lesson = Lesson(
                        module_id=module.id,
                        slug=l_data["slug"],
                        title_es=l_data["title_es"],
                        title_en=l_data["title_en"],
                        objective_es=l_data["objective_es"],
                        order_index=l_data["order_index"],
                    )
                    db.add(lesson)
                    db.flush()
                    log.info("    + Lección: %s", lesson.slug)

                for t_data in l_data.get("topics", []):
                    topic = (
                        db.query(Topic)
                        .filter_by(lesson_id=lesson.id, slug=t_data["slug"])
                        .first()
                    )
                    if not topic:
                        db.add(Topic(
                            lesson_id=lesson.id,
                            slug=t_data["slug"],
                            prompt_es=t_data["prompt_es"],
                            prompt_en=t_data["prompt_en"],
                            example_en=t_data["example_en"],
                            key_vocabulary=t_data.get("key_vocabulary", []),
                            connectors=t_data.get("connectors", []),
                            socratic_hints=t_data.get("socratic_hints", []),
                            difficulty=t_data.get("difficulty", 1),
                            order_index=t_data.get("order_index", 0),
                        ))
                        log.info("      + Topic: %s", t_data["slug"])

        # Logros
        for a in ACHIEVEMENTS:
            if not db.query(Achievement).filter_by(code=a["code"]).first():
                db.add(Achievement(**a))
                log.info("  + Logro: %s", a["code"])

        # Diálogos
        if DIALOGUES_PATH.exists():
            dlg_data = json.loads(DIALOGUES_PATH.read_text(encoding="utf-8"))
            for d_data in dlg_data.get("dialogues", []):
                existing = db.query(Dialogue).filter_by(slug=d_data["slug"]).first()
                if existing:
                    # Re-sembrar turnos: borrar y recrear (curriculum vivo)
                    db.query(DialogueTurn).filter_by(dialogue_id=existing.id).delete()
                    existing.title_es = d_data["title_es"]
                    existing.title_en = d_data["title_en"]
                    existing.description_es = d_data["description_es"]
                    existing.setting_es = d_data["setting_es"]
                    existing.setting_en = d_data.get("setting_en", "")
                    existing.npc_name = d_data["npc_name"]
                    existing.npc_role_es = d_data["npc_role_es"]
                    existing.icon = d_data["icon"]
                    existing.difficulty = d_data["difficulty"]
                    existing.is_adult = d_data.get("is_adult", False)
                    existing.level = d_data["level"]
                    existing.order_index = d_data["order_index"]
                    existing.key_vocabulary = d_data.get("key_vocabulary", [])
                    dialogue = existing
                    log.info("  ~ Diálogo actualizado: %s", dialogue.slug)
                else:
                    dialogue = Dialogue(
                        slug=d_data["slug"],
                        title_es=d_data["title_es"],
                        title_en=d_data["title_en"],
                        description_es=d_data["description_es"],
                        setting_es=d_data["setting_es"],
                        setting_en=d_data.get("setting_en", ""),
                        npc_name=d_data["npc_name"],
                        npc_role_es=d_data["npc_role_es"],
                        icon=d_data["icon"],
                        difficulty=d_data["difficulty"],
                        is_adult=d_data.get("is_adult", False),
                        level=d_data["level"],
                        order_index=d_data["order_index"],
                        key_vocabulary=d_data.get("key_vocabulary", []),
                    )
                    db.add(dialogue)
                    db.flush()
                    log.info("  + Diálogo: %s", dialogue.slug)

                for i, t in enumerate(d_data.get("turns", [])):
                    db.add(DialogueTurn(
                        dialogue_id=dialogue.id,
                        order_index=i,
                        speaker=t["speaker"],
                        npc_text_en=t.get("npc_text_en", ""),
                        npc_text_es=t.get("npc_text_es", ""),
                        user_hint_es=t.get("user_hint_es", ""),
                        user_example_en=t.get("user_example_en", ""),
                        required_keywords=t.get("required_keywords", []),
                        helper_phrases=t.get("helper_phrases", []),
                    ))

        db.commit()
        log.info("Seed completado.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
