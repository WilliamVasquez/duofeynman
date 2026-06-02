"""Modelos ORM. Importar todos acá para que Alembic los detecte."""
from app.models.user import User
from app.models.curriculum import Module, Lesson, Topic
from app.models.attempt import Attempt, AttemptError
from app.models.srs import SrsCard
from app.models.progress import UserProgress, Achievement, UserAchievement
from app.models.dialogue import Dialogue, DialogueTurn
from app.models.profile import UserProfile

__all__ = [
    "User",
    "Module",
    "Lesson",
    "Topic",
    "Attempt",
    "AttemptError",
    "SrsCard",
    "UserProgress",
    "Achievement",
    "UserAchievement",
    "Dialogue",
    "DialogueTurn",
    "UserProfile",
]
