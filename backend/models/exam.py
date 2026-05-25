from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class ExamQuestion(BaseModel):
    text: str = Field(..., min_length=3, max_length=800)
    options: list[str] = Field(..., min_length=2, max_length=6)
    correct: int = Field(..., ge=0)

    model_config = {"extra": "forbid"}


class ExamCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    grade: str = Field(..., min_length=1, max_length=10)
    subject: str = Field(..., min_length=2, max_length=80)
    questions: list[ExamQuestion] = Field(..., min_length=1, max_length=50)
    duration: int = Field(default=60, ge=10, le=300)
    due_date: Optional[datetime] = None
    teacher_id: str = ""

    model_config = {"extra": "forbid"}


class ExamDB(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    title: str
    grade: str
    subject: str
    questions: list[ExamQuestion]
    duration: int = 60
    due_date: Optional[datetime] = None
    is_active: bool = True
    teacher_id: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}


class ExamSubmit(BaseModel):
    student_id: str = Field(..., min_length=1)
    exam_id: str = Field(..., min_length=1)
    answers: list[int] = Field(..., min_length=1)

    model_config = {"extra": "forbid"}


class ExamResultDB(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    student_id: str
    exam_id: str
    exam_title: str = ""
    subject: str = ""
    grade: str = ""
    score: float = Field(default=0.0, ge=0.0, le=5.0)
    total_questions: int = 0
    correct_answers: int = 0
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}


class ExamIncidentDB(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    student_id: str
    exam_id: str
    incident_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_seconds: Optional[int] = None
    strikes_before: int = 0

    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}


class IncidentReport(BaseModel):
    student_id: str = Field(..., min_length=1)
    exam_id: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1, max_length=2000)
    severity: str = Field(default="medium", pattern=r"^(low|medium|high|critical)$")

    model_config = {"extra": "forbid"}
