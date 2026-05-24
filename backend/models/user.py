from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class UserRole(StrEnum):
    STUDENT = "ESTUDIANTE"
    TEACHER = "PROFESOR"
    ADMIN = "RECTOR"


class StudentCreate(BaseModel):
    document_id: str = Field(..., min_length=5, pattern=r"^\d+$")
    fullname: str = Field(..., min_length=3, max_length=120)
    grade: str = Field(..., min_length=1, max_length=10)
    is_paid: bool = Field(default=True)
    role: UserRole = Field(default=UserRole.STUDENT)

    model_config = {"extra": "forbid"}


class StudentDB(StudentCreate):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_at_risk: bool = False
    risk_updated_at: Optional[datetime] = None
    enrollment_year: int = Field(default=2026)

    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}


class StudentResponse(BaseModel):
    document_id: str
    fullname: str
    grade: str
    is_paid: bool
    role: str
    is_at_risk: bool = False
    enrollment_year: int = 2026

    model_config = {"extra": "ignore"}


class TeacherCreate(BaseModel):
    document_id: str = Field(..., min_length=5, pattern=r"^\d+$")
    teacher_name: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=4, max_length=128)
    subject: str = Field(..., min_length=2, max_length=80)
    grade: str = Field(..., min_length=1, max_length=10)
    is_homeroom_teacher: bool = False

    model_config = {"extra": "forbid"}


class TeacherDB(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    document_id: str
    teacher_name: str
    password: str
    role: UserRole = UserRole.TEACHER
    subjects: list[str] = Field(default_factory=list)
    grades: list[str] = Field(default_factory=list)
    is_homeroom_teacher: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}


class TeacherResponse(BaseModel):
    document_id: str
    teacher_name: str
    subjects: list[str]
    grades: list[str]
    is_homeroom_teacher: bool

    model_config = {"extra": "ignore"}


class AdminCreate(BaseModel):
    document_id: str = Field(..., min_length=5, pattern=r"^\d+$")
    fullname: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=4, max_length=128)
    role: UserRole = Field(default=UserRole.ADMIN)

    model_config = {"extra": "forbid"}


class AdminDB(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    document_id: str
    fullname: str
    password: str
    role: UserRole = UserRole.ADMIN
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}


class AdminResponse(BaseModel):
    document_id: str
    fullname: str
    role: str

    model_config = {"extra": "ignore"}


class LoginRequest(BaseModel):
    document_id: str = Field(..., min_length=5, alias="documento")
    password: Optional[str] = Field(default=None, alias="contraseña")

    model_config = {"populate_by_name": True, "extra": "forbid"}


class LoginResponse(BaseModel):
    document_id: str
    fullname: str
    role: str
    grade: Optional[str] = None
    token: str
