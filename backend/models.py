from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field, model_validator

MAX_GRADE: float = 5.0
RISK_THRESHOLD: float = 3.5


class LoginRequest(BaseModel):
    tipo: str = Field(default="estudiante", pattern=r"^(estudiante|docente|rector)$")
    documento: str = Field(..., min_length=4, max_length=32)
    contraseña: Optional[str] = None


class StudentCreate(BaseModel):
    document_id: str = Field(..., min_length=4)
    fullname: str = Field(..., min_length=1)
    grade: str = Field(..., min_length=1)
    is_paid: bool = True
    role: str = "ESTUDIANTE"

    @model_validator(mode="after")
    def _sanitize(self) -> "StudentCreate":
        self.document_id = self.document_id.strip()
        self.fullname = self.fullname.strip()
        self.grade = self.grade.strip()
        return self


class StudentUpdate(BaseModel):
    fullname: Optional[str] = None
    grade: Optional[str] = None
    is_paid: Optional[bool] = None


class PaymentToggle(BaseModel):
    is_paid: bool


class TeacherAssignment(BaseModel):
    document_id: str
    fullname: str
    password: str = Field(..., min_length=4)
    subject: str
    grade: str

    @model_validator(mode="after")
    def _sanitize(self) -> "TeacherAssignment":
        self.document_id = self.document_id.strip()
        self.fullname = self.fullname.strip()
        self.subject = self.subject.strip()
        self.grade = self.grade.strip()
        return self


class SubjectCreate(BaseModel):
    name: str = Field(..., min_length=1)
    grade: str = Field(..., min_length=1)
    gem_tutor_url: str = ""
    gem_planner_url: str = ""

    @model_validator(mode="after")
    def _sanitize(self) -> "SubjectCreate":
        self.name = self.name.strip()
        self.grade = self.grade.strip()
        return self


class NoticeCreate(BaseModel):
    titulo: str = Field(..., min_length=1)
    contenido: str = Field(..., min_length=1)
    categoria: str = "General"
    archivo_url: Optional[str] = None


class GradeSubmission(BaseModel):
    student_id: str = Field(..., min_length=1, pattern=r"^\S+$")
    teacher_id: str = Field(..., min_length=1, pattern=r"^\S+$")
    course_id: str = Field(default="default", min_length=1)
    project_id: str = Field(..., min_length=1, pattern=r"^\S+$")
    subject_id: str = Field(..., min_length=1, pattern=r"^\S+$")
    score: float = Field(..., ge=0.0, le=MAX_GRADE)
    observations: str = ""

    @model_validator(mode="after")
    def _sanitize(self) -> "GradeSubmission":
        self.student_id = self.student_id.strip()
        self.teacher_id = self.teacher_id.strip()
        self.project_id = self.project_id.strip()
        self.subject_id = self.subject_id.strip()
        return self


class Question(BaseModel):
    text: str
    options: list[str]
    correct: int = Field(..., ge=0)


class ExamCreate(BaseModel):
    title: str = Field(..., min_length=1)
    grade: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=1)
    questions: list[Question] = Field(..., min_length=1)
    duration: int = Field(..., ge=1)
    due_date: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def _validate_questions(self) -> "ExamCreate":
        for i, q in enumerate(self.questions):
            if q.correct >= len(q.options):
                raise ValueError(f"Question {i}: correct index out of range")
        return self


class ExamSubmit(BaseModel):
    student_id: str = Field(..., min_length=1)
    exam_id: str = Field(..., min_length=1)
    answers: list[int] = Field(default_factory=list)


class VoteRequest(BaseModel):
    student_id: str = Field(..., min_length=1)
    candidate_id: str = Field(default="blank")


class CandidateCreate(BaseModel):
    name: str = Field(..., min_length=1)
    position: str = Field(..., min_length=1)


class IncidentReport(BaseModel):
    student_id: str
    exam_id: str
    type: str = "suspicious"
    detail: str = ""

    @model_validator(mode="after")
    def _sanitize(self) -> "IncidentReport":
        self.student_id = self.student_id.strip()
        self.exam_id = self.exam_id.strip()
        return self


class RiskEvent(BaseModel):
    type: str
    msg: str
    student_id: str = ""
    score: float = 0.0
    threshold: float = RISK_THRESHOLD
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def grade_status(score: float) -> str:
    if score >= 4.0:
        return "Sobresaliente"
    if score >= RISK_THRESHOLD:
        return "Aceptable"
    return "En Riesgo"


def grade_badge_class(score: float) -> str:
    if score >= 4.0:
        return "brand-green"
    if score >= RISK_THRESHOLD:
        return "brand-gold"
    return "brand-danger"


def grade_color(score: float) -> str:
    if score >= 4.0:
        return "#4caf50"
    if score >= RISK_THRESHOLD:
        return "#fdc003"
    return "#ba1a1a"
