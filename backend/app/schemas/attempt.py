from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Literal


class AttemptStartIn(BaseModel):
    topic_id: int
    mode: Literal["speak", "write"] = "speak"


class AttemptRoundIn(BaseModel):
    attempt_id: int
    transcript: str = Field(min_length=1, max_length=5000)
    duration_seconds: int = Field(ge=0, le=600)
    mode: Literal["speak", "write"] = "speak"


class ErrorOut(BaseModel):
    category: str
    rule_id: str | None = None
    span_text: str
    suggestion: str
    explanation_es: str
    severity: int

    class Config:
        from_attributes = True


class FeedbackOut(BaseModel):
    overall_score: float
    fluency_score: float
    code_switch_rate: float
    self_correction_rate: float = 0.0
    error_density: float
    word_count: int
    vocab_coverage: float = 0.0
    connector_coverage: float = 0.0
    subscores: dict = {}
    lexical_diversity: float = 0.0
    sentence_count: int = 0
    tenses_used: list[str] = []
    errors: list[ErrorOut] = []
    socratic_questions: list[str] = []
    encouragement_es: str
    next_action: str
    model_answer_en: str | None = None
    unlocked_achievements: list[dict] = []


class AttemptOut(BaseModel):
    id: int
    user_id: int
    topic_id: int
    stage: str
    rounds: list[Any] = []
    overall_score: float
    mastered: bool
    word_count: int
    started_at: datetime
    completed_at: datetime | None = None

    class Config:
        from_attributes = True
