from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jwt
from dotenv import load_dotenv
from fastapi import HTTPException, Request
from supabase import Client

from config.database import get_db

_dotenv_path = Path(__file__).resolve().parent.parent / ".env"
if _dotenv_path.exists():
    load_dotenv(_dotenv_path)

logger = logging.getLogger("siee.deps")

RISK_THRESHOLD: float = 3.5
MAX_GRADE: float = 5.0
JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")

SKIP_AUTH_PATHS: frozenset[str] = frozenset({
    "/", "/api/health", "/api/login", "/api/auth/login", "/api/auth/register",
    "/api/notices", "/api/admin/stats", "/api/admin/mora-students", "/api/admin/at-risk-students",
    "/api/subjects", "/api/admin/candidates", "/api/admin/election-results",
    "/docs", "/openapi.json", "/redoc",
})
FINANCIAL_LOCKED_PATHS: tuple[str, ...] = (
    "/api/grades/download-pdf",
    "/api/grades/report-card",
    "/api/grades/bulletin",
    "/api/students/report",
    "/api/reports/",
)

TOKEN_EXPIRY_HOURS: int = int(os.getenv("TOKEN_EXPIRY_HOURS", "8"))


def encode_jwt(payload: dict[str, Any], expires_hours: int = TOKEN_EXPIRY_HOURS) -> str:
    payload = dict(payload)
    payload.setdefault("iat", datetime.now(timezone.utc))
    payload.setdefault("exp", datetime.now(timezone.utc) + timedelta(hours=expires_hours))
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict[str, Any]:
    return jwt.decode(
        token, JWT_SECRET, algorithms=[JWT_ALGORITHM],
        options={"require": ["sub"]},
    )


def auth_dependency(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization required")
    try:
        claims = decode_jwt(auth_header[7:])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    request.state.user_role = claims.get("role", "student")
    return claims["sub"]


def teacher_dependency(request: Request) -> str:
    user_id = auth_dependency(request)
    role: str = getattr(request.state, "user_role", "")
    if role.lower() not in ("teacher", "profesor"):
        raise HTTPException(status_code=403, detail="Se requieren permisos de docente")
    return user_id


def admin_dependency(request: Request) -> str:
    user_id = auth_dependency(request)
    role: str = getattr(request.state, "user_role", "")
    if role.lower() not in ("admin", "rector"):
        raise HTTPException(status_code=403, detail="Se requieren permisos de administrador")
    return user_id


async def financial_guard(request: Request) -> None:
    student_id = request.query_params.get("student_id")
    if not student_id and request.method in ("POST", "PUT"):
        try:
            body = await request.body()
            parsed = json.loads(body)
            student_id = parsed.get("student_id")
        except Exception:
            logger.debug("could not parse student_id from POST body for path=%s", request.url.path)
    if not student_id:
        raise HTTPException(status_code=422, detail="student_id required")
    db: Client = next(get_db())
    result = db.table("student_metadata").select("*").eq("profile_id", student_id).execute()
    rows = result.data
    if not rows:
        raise HTTPException(status_code=404, detail="Student not found")
    meta = rows[0]
    if meta.get("months_in_arrears", 0) >= 2 and not meta.get("financial_override", False):
        logger.warning("financial-block student=%s path=%s", student_id, request.url.path)
        raise HTTPException(
            status_code=403,
            detail="Estatus financiero irregular — Descarga restringida",
        )


def is_financial_locked_path(path: str) -> bool:
    return any(path.startswith(p) for p in FINANCIAL_LOCKED_PATHS)
