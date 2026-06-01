from __future__ import annotations

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field


class UserRole(StrEnum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class LoginRequest(BaseModel):
    document_id: str = Field(..., min_length=1, alias="documento")
    password: Optional[str] = Field(default=None, alias="contraseña")
    model_config = {"populate_by_name": True, "extra": "forbid"}


class LoginResponse(BaseModel):
    profile_id: str
    login_credential: str
    fullname: str
    role: str
    token: str
    model_config = {"extra": "ignore"}


class UserLogin(BaseModel):
    login_credential: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    model_config = {"extra": "forbid"}


class UserCreate(BaseModel):
    login_credential: str = Field(..., min_length=1)
    fullname: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=4, max_length=128)
    role: UserRole = Field(default=UserRole.STUDENT)
    grade: str = Field(default="", max_length=10)
    model_config = {"extra": "forbid"}


class UserResponse(BaseModel):
    profile_id: str
    login_credential: str
    fullname: str
    role: str
    is_active: bool = True
    model_config = {"extra": "ignore"}


class TokenSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_hours: int = 8
    usuario: dict = {}
    model_config = {"extra": "ignore"}


class StudentCreate(BaseModel):
    login_credential: str = Field(..., min_length=1)
    fullname: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=4, max_length=128)
    grade: str = Field(default="")
    model_config = {"extra": "forbid"}


class StudentUpdate(BaseModel):
    fullname: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None
    model_config = {"extra": "forbid"}


class StudentDB(BaseModel):
    id: str
    login_credential: str
    fullname: str
    role: str
    is_active: bool = True
    created_at: str = ""
    model_config = {"extra": "ignore"}
