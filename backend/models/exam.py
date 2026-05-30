from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class ExamQuestion(BaseModel):
    text: str = Field(..., min_length=3, max_length=800)
    options: list[str] = Field(..., min_length=2, max_length=6)
    correct: int = Field(..., ge=0)
    model_config = {"extra": "forbid"}


class ExamDB(BaseModel):
    id: str
    title: str
    grade: str
    subject: str
    questions: list[dict]
    duration: int = 60
    due_date: Optional[str] = None
    is_active: bool = True
    teacher_id: str = ""
    created_at: str = ""
    model_config = {"extra": "ignore"}


class ExamResultDB(BaseModel):
    id: str
    student_id: str
    exam_id: str
    score: float = 0.0
    correct: int = 0
    total: int = 0
    created_at: str = ""
    model_config = {"extra": "ignore"}
