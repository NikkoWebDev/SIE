from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class GradeEntry(BaseModel):
    student_id: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=2, max_length=80)
    grade: float = Field(..., ge=0.0, le=5.0)
    observations: str = Field(default="", max_length=500)
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"extra": "forbid"}


class GradeDB(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    student_id: str
    subject_id: str
    subject_name: str = ""
    project_id: str = ""
    score: float = Field(..., ge=0.0, le=5.0)
    observations: str = ""
    teacher_id: str = ""
    period: str = "P1"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}


class GradeSubmission(BaseModel):
    student_id: str = Field(..., min_length=1, pattern=r"^\S+$")
    teacher_id: str = Field(..., min_length=1, pattern=r"^\S+$")
    course_id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    subject_id: str = Field(..., min_length=1)
    score: float = Field(..., ge=0.0, le=5.0)
    observations: str = Field(default="", max_length=500)
    period: str = Field(default="P1", max_length=4)

    model_config = {"extra": "forbid"}


class SubjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    grade: str = Field(..., min_length=1, max_length=10)
    gem_tutor_url: str = Field(default="")
    gem_planner_url: str = Field(default="")

    model_config = {"extra": "forbid"}


class SubjectDB(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    name: str
    grade: str
    gem_tutor_url: str = ""
    gem_planner_url: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}


class DeliveryDB(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    student_id: str
    grade: str
    subject: str
    filename: str
    url: str
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    teacher_id: Optional[str] = None
    reviewed: bool = False
    review_score: Optional[float] = None

    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}


class GuideDB(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    grade: str
    subject: str
    filename: str
    url: str
    teacher_id: str = ""
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resource_type: str = "guide"

    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}


class RiskEvent(BaseModel):
    type: str
    msg: str
    student_id: str = ""
    materia: str = ""
    score: float = 0.0
    nota: float = 0.0
    threshold: float = 3.5
    is_at_risk: bool = True
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def grade_color(score: float) -> str:
    if score < 3.5:
        return "#FF0000"
    return "#00FF00"


def grade_status(score: float) -> str:
    if score < 3.5:
        return "En Riesgo"
    return "Aceptable"
