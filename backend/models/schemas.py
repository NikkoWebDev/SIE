from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator

RISK_THRESHOLD: float = 3.5
MAX_GRADE: float = 5.0


class GradeSubmission(BaseModel):
    student_id: str = Field(..., min_length=1)
    teacher_id: str = Field(..., min_length=1)
    course_id: str = Field(default="default")
    project_id: str = Field(..., min_length=1)
    subject_id: str = Field(..., min_length=1)
    score: float = Field(..., ge=0.0, le=MAX_GRADE)
    observations: str = Field(default="", max_length=500)
    period: str = Field(default="P1", max_length=4)
    model_config = {"extra": "forbid"}


class GradeEntry(BaseModel):
    student_id: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=2, max_length=80)
    grade: float = Field(..., ge=0.0, le=5.0)
    observations: str = Field(default="", max_length=500)
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_config = {"extra": "forbid"}


class PaymentToggle(BaseModel):
    student_id: str = Field(..., min_length=1)
    is_paid: bool
    model_config = {"extra": "forbid"}


class PaymentToggleRequest(BaseModel):
    login_credential: str = Field(..., min_length=1)
    is_paid: bool
    model_config = {"extra": "forbid"}


class StudentMetadataSchema(BaseModel):
    profile_id: str = Field(..., min_length=1)
    months_in_arrears: int = Field(default=0, ge=0)
    financial_override: bool = Field(default=False)
    current_status: str = Field(default="AL_DIA")
    total_balance: float = Field(default=0.0, ge=0.0)
    guardian_info: str = Field(default="")
    model_config = {"extra": "ignore"}


class FinancialStatusResponse(BaseModel):
    profile_id: str
    is_paid: bool
    current_status: str
    months_in_arrears: int
    total_balance: float
    financial_override_active: bool = False
    model_config = {"extra": "ignore"}


class Question(BaseModel):
    text: str = Field(..., min_length=3, max_length=800)
    options: list[str] = Field(..., min_length=2, max_length=6)
    correct: int = Field(..., ge=0)
    model_config = {"extra": "forbid"}


class ExamCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    grade: str = Field(default="")
    subject: str = Field(default="")
    questions: list[Question] = Field(..., min_length=1, max_length=50)
    duration: int = Field(default=60, ge=10, le=300)
    due_date: Optional[str] = None
    teacher_id: str = ""

    @model_validator(mode="after")
    def _validate_questions(self) -> ExamCreate:
        for i, q in enumerate(self.questions):
            if q.correct >= len(q.options):
                raise ValueError(f"Question {i}: correct index out of range")
        return self
    model_config = {"extra": "forbid"}


class ExamSubmit(BaseModel):
    student_id: str = Field(..., min_length=1)
    exam_id: str = Field(..., min_length=1)
    answers: list[int] = Field(..., min_length=1)
    model_config = {"extra": "forbid"}


class ExamProgressSchema(BaseModel):
    student_id: str = Field(..., min_length=1)
    exam_id: str = Field(..., min_length=1)
    answers: dict[str, Any] = Field(default_factory=dict)
    current_question_index: int = Field(default=0, ge=0)
    time_elapsed_seconds: int = Field(default=0, ge=0)
    interrupted: bool = Field(default=False)
    resumed_at: Optional[str] = None
    last_saved_at: Optional[str] = None
    model_config = {"extra": "ignore"}


class ExamResultResponse(BaseModel):
    student_id: str
    exam_id: str
    exam_title: str = ""
    subject: str = ""
    score: float = Field(default=0.0, ge=0.0, le=5.0)
    total_questions: int = 0
    correct_answers: int = 0
    status: str = ""
    model_config = {"extra": "ignore"}


class IncidentReport(BaseModel):
    student_id: str = Field(..., min_length=1)
    exam_id: str = Field(..., min_length=1)
    incident_type: str = Field(default="suspicious")
    description: str = Field(default="", max_length=2000)
    severity: str = Field(default="medium")
    duration_seconds: Optional[int] = None
    strikes_before: int = Field(default=0, ge=0)
    model_config = {"extra": "forbid"}


class VoteRequest(BaseModel):
    student_id: str = Field(..., min_length=1)
    candidate_id: str = Field(..., min_length=1)
    model_config = {"extra": "forbid"}


class CandidateCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=120)
    position: str = Field(..., min_length=2, max_length=80)
    photo_url: str = Field(default="")
    model_config = {"extra": "forbid"}


class NoticeCreate(BaseModel):
    titulo: str = Field(..., min_length=1)
    contenido: str = Field(..., min_length=1)
    categoria: str = Field(default="General", max_length=40)
    archivo_url: Optional[str] = None
    author: str = Field(default="Rectoría")
    model_config = {"extra": "forbid"}


class NoticeResponse(BaseModel):
    id: str = ""
    titulo: str
    contenido: str
    categoria: str
    archivo_url: Optional[str] = None
    fecha: str = ""
    author: str = "Rectoría"
    is_pinned: bool = False
    model_config = {"extra": "ignore"}


class SubjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    grade: str = Field(default="", max_length=10)
    is_abp: bool = Field(default=False)
    tutor_ai: str = Field(default="", max_length=500)
    planner_ai: str = Field(default="", max_length=500)
    model_config = {"extra": "forbid"}


class TeacherAssignment(BaseModel):
    document_id: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=1)
    grade: str = Field(default="")
    model_config = {"extra": "forbid"}


class FinancialToggleSchema(BaseModel):
    is_paid: bool
    model_config = {"extra": "forbid"}


class OutageReport(BaseModel):
    student_id: str = Field(..., min_length=1)
    exam_id: str = Field(..., min_length=1)
    incident_type: str = Field(default="network_loss")
    description: str = Field(default="", max_length=1000)
    model_config = {"extra": "forbid"}


class BehaviorLogEntry(BaseModel):
    id: str = ""
    student_id: str = ""
    log_type: str = ""  # 'positive', 'disciplinary', 'merit'
    description: str = ""
    recorded_by: str = ""
    created_at: str = ""
    model_config = {"extra": "ignore"}


class ClassMaterialSchema(BaseModel):
    id: str
    subject_id: str
    subject_name: str = ""
    grade_id: str
    file_url: str
    file_type: str = "md"
    markdown_content: str = ""
    cloudinary_url: str = ""
    uploaded_by: str = ""
    created_at: str = ""
    model_config = {"extra": "ignore"}


def grade_status(score: float) -> str:
    if score >= 4.0:
        return "Sobresaliente"
    if score >= RISK_THRESHOLD:
        return "Aceptable"
    return "En Riesgo"


def grade_color(score: float) -> str:
    if score >= 4.0:
        return "#00FF66"
    if score >= RISK_THRESHOLD:
        return "#FFE600"
    return "#FF0055"


def grade_badge_class(score: float) -> str:
    if score >= 4.0:
        return "text-success"
    if score >= RISK_THRESHOLD:
        return "text-brand-gold"
    return "text-brand-danger"
