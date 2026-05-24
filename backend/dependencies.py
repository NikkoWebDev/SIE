from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import jwt
from dotenv import load_dotenv
from fastapi import HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from motor.motor_asyncio import AsyncIOMotorClient

_dotenv_path = Path(__file__).resolve().parent.parent / ".env"
if _dotenv_path.exists():
    load_dotenv(_dotenv_path)

logger = logging.getLogger("siee.deps")

COLLECTIONS: tuple[str, ...] = (
    "students", "admins", "grades", "notices", "subjects", "guides",
    "deliveries", "assignments", "exams", "exam_results", "exam_incidents",
    "candidates", "votes",
)

RISK_THRESHOLD: float = 3.5
MAX_GRADE: float = 5.0
JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
MONGO_URI: str = os.getenv("MONGO_URL") or os.getenv(
    "MONGODB_URI",
    "mongodb+srv://admin:password@cluster0.example.mongodb.net/?retryWrites=true&w=majority",
)
MONGO_DB: str = os.getenv("MONGO_DB", "sie_core")

SKIP_AUTH_PATHS: frozenset[str] = frozenset({
    "/", "/api/health", "/api/login", "/docs", "/openapi.json", "/redoc",
})
FINANCIAL_LOCKED_PATHS: tuple[str, ...] = (
    "/api/grades/download-pdf",
    "/api/grades/report-card",
    "/api/grades/bulletin",
    "/api/students/report",
    "/api/reports/",
)

_mongo_client: AsyncIOMotorClient | None = None
_db: Any = None


def get_db() -> Any:
    if _db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    return _db


async def init_db() -> None:
    global _mongo_client, _db
    _mongo_client = AsyncIOMotorClient(
        MONGO_URI,
        maxPoolSize=20,
        minPoolSize=2,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )
    _db = _mongo_client[MONGO_DB]
    await _mongo_client.admin.command("ping")
    logger.info("mongodb connected | db=%s", MONGO_DB)


async def close_db() -> None:
    if _mongo_client:
        _mongo_client.close()
        logger.info("mongodb disconnected")


def encode_jwt(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict[str, Any]:
    return jwt.decode(
        token, JWT_SECRET, algorithms=[JWT_ALGORITHM],
        options={"require": ["sub"]},
    )


async def auth_dependency(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization required")
    try:
        claims = decode_jwt(auth_header[7:])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return claims["sub"]


async def financial_guard(request: Request) -> None:
    student_id = request.query_params.get("student_id")
    if not student_id and request.method in ("POST", "PUT"):
        try:
            body = await request.json()
            student_id = body.get("student_id")
        except Exception:
            pass
    if not student_id:
        raise HTTPException(status_code=422, detail="student_id required")
    db = get_db()
    student = await db["students"].find_one({"_id": student_id})
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.get("is_paid") is False:
        logger.warning("financial-block student=%s path=%s", student_id, request.url.path)
        raise HTTPException(
            status_code=403,
            detail="Estatus financiero irregular — Descarga restringida",
        )


def is_financial_locked_path(path: str) -> bool:
    return any(path.startswith(p) for p in FINANCIAL_LOCKED_PATHS)
