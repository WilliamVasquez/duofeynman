from pydantic import BaseModel
from typing import Any


class TopicOut(BaseModel):
    id: int
    slug: str
    prompt_es: str
    prompt_en: str
    example_en: str
    key_vocabulary: list[Any] = []
    connectors: list[str] = []
    socratic_hints: list[str] = []
    difficulty: int
    order_index: int

    class Config:
        from_attributes = True


class LessonOut(BaseModel):
    id: int
    slug: str
    title_es: str
    title_en: str
    objective_es: str
    order_index: int
    topics: list[TopicOut] = []

    class Config:
        from_attributes = True


class ModuleOut(BaseModel):
    id: int
    slug: str
    title_es: str
    title_en: str
    description_es: str
    level: str
    order_index: int
    lessons: list[LessonOut] = []

    class Config:
        from_attributes = True
