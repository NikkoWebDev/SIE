from __future__ import annotations

import json
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jwt
from dotenv import load_dotenv
from fastapi import HTTPException, Request, Response
from supabase import Client

from config.database import get_db

_dotenv_path = Path(__file__).resolve().parent.parent / ".env"
if _dotenv_path.exists():
    load_dotenv(_dotenv_path)

logger = logging.getLogger("siee.deps")

RISK_THRESHOLD: float = 3.5
MAX_GRADE: float = 5.0
JWT_SECRET: str = os.getenv("JWT_SECRET", "")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET no configurada. El servidor no arrancará sin una clave JWT segura.")
JWT_ALGORITHM: str = "HS256"  # fixed algorithm — cannot be overridden via env

SKIP_AUTH_PATHS: frozenset[str] = frozenset({
    "/", "/api/health", "/api/login", "/api/auth/login", "/api/auth/register",
    "/api/auth/forgot-password", "/api/auth/reset-password", "/api/auth/google",
    "/api/auth/logout",
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
    payload.setdefault("jti", secrets.token_hex(16))  # unique token ID for revocation
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict[str, Any]:
    return jwt.decode(
        token, JWT_SECRET, algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "exp", "jti"]},
    )


def _is_cross_origin(request: Request | None) -> bool:
    if request is None:
        return os.getenv("ENV", "development") == "production"
    origin = request.headers.get("Origin", "")
    if not origin:
        return os.getenv("ENV", "development") == "production"
    server_origin = f"{request.url.scheme}://{request.url.hostname}"
    if request.url.port:
        server_origin += f":{request.url.port}"
    return origin != server_origin


def _cookie_samesite(request: Request | None = None) -> str:
    return "none" if _is_cross_origin(request) else "lax"


def _cookie_secure(request: Request | None = None) -> bool:
    return _is_cross_origin(request)


def set_jwt_cookie(response: Response, token: str, token_type: str = "bearer", request: Request | None = None) -> None:
    """Set JWT as httpOnly cookie. Cross-origin safe (SameSite=None + Secure in prod)."""
    max_age = TOKEN_EXPIRY_HOURS * 3600
    response.set_cookie(
        key="access_token",
        value=token,
        max_age=max_age,
        httponly=True,
        secure=_cookie_secure(request),
        samesite=_cookie_samesite(request),
        path="/",
    )
    response.set_cookie(
        key="token_type",
        value=token_type,
        max_age=max_age,
        httponly=True,
        secure=_cookie_secure(request),
        samesite=_cookie_samesite(request),
        path="/",
    )


def clear_jwt_cookie(response: Response, request: Request | None = None) -> None:
    """Clear JWT cookies (logout)."""
    response.delete_cookie(key="access_token", path="/", httponly=True, secure=_cookie_secure(request), samesite=_cookie_samesite(request))
    response.delete_cookie(key="token_type", path="/", httponly=True, secure=_cookie_secure(request), samesite=_cookie_samesite(request))


def auth_dependency(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        token = request.cookies.get("access_token", "")
    if not token:
        raise HTTPException(status_code=401, detail="Authorization required")
    try:
        claims = decode_jwt(token)
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


# ── CSRF Protection ──────────────────────────────────────────────

CSRF_SKIP_PATHS: frozenset[str] = frozenset({
    "/api/auth/login", "/api/auth/register", "/api/auth/forgot-password",
    "/api/auth/reset-password", "/api/auth/google", "/api/auth/logout",
    "/api/health", "/api/ai",
})


def set_csrf_cookie(response: Response, request: Request | None = None) -> str:
    """Set a CSRF token cookie (non-httpOnly so JS can read it for header)."""
    token = secrets.token_hex(32)
    response.set_cookie(
        key="csrf_token",
        value=token,
        max_age=TOKEN_EXPIRY_HOURS * 3600,
        httponly=False,
        secure=_cookie_secure(request),
        samesite=_cookie_samesite(request),
        path="/",
    )
    return token


def clear_csrf_cookie(response: Response, request: Request | None = None) -> None:
    response.delete_cookie(
        key="csrf_token", path="/", httponly=False,
        secure=_cookie_secure(request), samesite=_cookie_samesite(request),
    )


def validate_csrf(request: Request) -> None:
    """Validate CSRF token for mutating requests using cookie auth.

    Uses Double Submit Cookie pattern: cookie value must match X-CSRF-Token header.
    Skips validation if Authorization header is present (Bearer token, not vulnerable to CSRF).
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    path = request.url.path
    if any(path.startswith(p) for p in CSRF_SKIP_PATHS):
        return
    # If request uses Authorization header, no CSRF check needed
    if request.headers.get("Authorization", "").startswith("Bearer "):
        return
    cookie_token = request.cookies.get("csrf_token", "")
    header_token = request.headers.get("X-CSRF-Token", "")
    if not cookie_token or not header_token or cookie_token != header_token:
        raise HTTPException(
            status_code=403,
            detail="CSRF validation failed. Recarga la página e intenta de nuevo.",
        )


def is_financial_locked_path(path: str) -> bool:
    return any(path.startswith(p) for p in FINANCIAL_LOCKED_PATHS)


# ── Audit Logging ────────────────────────────────────────────────

AUDIT_LOG_LEVEL = os.getenv("AUDIT_LOG_LEVEL", "INFO").upper()


class AuditLogger:
    """Structured audit log for sensitive operations."""

    @staticmethod
    def log(action: str, actor_id: str, target_id: str = "", detail: str = "", success: bool = True) -> None:
        entry = {
            "action": action,
            "actor_id": actor_id,
            "target_id": target_id,
            "detail": detail,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if AUDIT_LOG_LEVEL == "DEBUG":
            logger.debug("AUDIT: %s", json.dumps(entry, ensure_ascii=False))
        else:
            logger.info("AUDIT: %s", json.dumps(entry, ensure_ascii=False))

    @staticmethod
    def log_failure(action: str, actor_id: str, target_id: str = "", detail: str = "") -> None:
        AuditLogger.log(action, actor_id, target_id, detail, success=False)


audit = AuditLogger()
