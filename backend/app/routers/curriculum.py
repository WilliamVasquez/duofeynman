from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.curriculum import Module, Lesson, Topic
from app.models.progress import UserProgress
from app.schemas.curriculum import ModuleOut, LessonOut, TopicOut
from app.routers.deps import get_current_user
from app.models.user import User


router = APIRouter(prefix="/api/curriculum", tags=["curriculum"])


@router.get("/path")
def learning_path(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Camino de aprendizaje guiado: curriculum + progreso del usuario.

    Cada topic lleva `status`:
      - "mastered": mastery_level >= 1 (lo dominó al menos una vez)
      - "current":  el próximo topic a practicar (primero sin dominar,
                    en orden módulo → lección → topic)
      - "new":      todavía no llegó (accesible igual — desbloqueo suave)

    Además devuelve `next_topic` (puntero global) para el botón "Continue".
    """
    modules = (
        db.query(Module)
        .options(selectinload(Module.lessons).selectinload(Lesson.topics))
        .order_by(Module.order_index)
        .all()
    )

    # Progreso del usuario: topic_id -> mastery_level
    rows = (
        db.query(UserProgress.topic_id, UserProgress.mastery_level)
        .filter(UserProgress.user_id == user.id)
        .all()
    )
    mastery = {tid: lvl for tid, lvl in rows}

    next_topic: dict | None = None
    out_modules = []
    for m in modules:
        out_lessons = []
        for lesson in sorted(m.lessons, key=lambda x: x.order_index):
            out_topics = []
            done_count = 0
            for t in sorted(lesson.topics, key=lambda x: x.order_index):
                lvl = mastery.get(t.id, 0)
                if lvl >= 1:
                    status = "mastered"
                    done_count += 1
                elif next_topic is None:
                    status = "current"
                    next_topic = {
                        "topic_id": t.id,
                        "lesson_id": lesson.id,
                        "module_id": m.id,
                        "prompt_es": t.prompt_es,
                        "prompt_en": t.prompt_en,
                        "lesson_title_en": lesson.title_en,
                        "lesson_title_es": lesson.title_es,
                        "module_title_en": m.title_en,
                        "level": m.level,
                    }
                else:
                    status = "new"
                out_topics.append({
                    "id": t.id,
                    "slug": t.slug,
                    "prompt_es": t.prompt_es,
                    "prompt_en": t.prompt_en,
                    "difficulty": t.difficulty,
                    "order_index": t.order_index,
                    "mastery_level": lvl,
                    "status": status,
                })
            total = len(out_topics)
            out_lessons.append({
                "id": lesson.id,
                "slug": lesson.slug,
                "title_es": lesson.title_es,
                "title_en": lesson.title_en,
                "objective_es": lesson.objective_es,
                "order_index": lesson.order_index,
                "topics": out_topics,
                "done_count": done_count,
                "total_count": total,
                "completed": total > 0 and done_count == total,
            })
        out_modules.append({
            "id": m.id,
            "slug": m.slug,
            "title_es": m.title_es,
            "title_en": m.title_en,
            "level": m.level,
            "order_index": m.order_index,
            "lessons": out_lessons,
        })

    return {"modules": out_modules, "next_topic": next_topic}


@router.get("/modules", response_model=list[ModuleOut])
def list_modules(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    modules = (
        db.query(Module)
        .options(selectinload(Module.lessons).selectinload(Lesson.topics))
        .order_by(Module.order_index)
        .all()
    )
    return [ModuleOut.model_validate(m) for m in modules]


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
def get_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    lesson = (
        db.query(Lesson)
        .options(selectinload(Lesson.topics))
        .filter(Lesson.id == lesson_id)
        .first()
    )
    if not lesson:
        raise HTTPException(404, "Lección no encontrada")
    return LessonOut.model_validate(lesson)


@router.get("/topics/{topic_id}", response_model=TopicOut)
def get_topic(
    topic_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(404, "Topic no encontrado")
    return TopicOut.model_validate(topic)
