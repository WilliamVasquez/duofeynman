from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.curriculum import Module, Lesson, Topic
from app.schemas.curriculum import ModuleOut, LessonOut, TopicOut
from app.routers.deps import get_current_user
from app.models.user import User


router = APIRouter(prefix="/api/curriculum", tags=["curriculum"])


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
