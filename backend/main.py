from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import sentry_sdk
from dotenv import load_dotenv

_dotenv_path = Path(__file__).resolve().parent.parent / ".env"
if _dotenv_path.exists():
    load_dotenv(_dotenv_path)

import traceback

import jwt
from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from supabase import Client

from config.database import get_db
from dependencies import (
    JWT_ALGORITHM, JWT_SECRET, SKIP_AUTH_PATHS,
    decode_jwt, get_db as dep_get_db, is_financial_locked_path,
    validate_csrf,
)
from managers import ws_manager
from routers.auth import router as auth_router
from routers.students import router as students_router
from routers.grades import router as grades_router
from routers.notices import router as notices_router
from routers.subjects import router as subjects_router
from routers.exams import router as exams_router
from routers.admin import router as admin_router
from routers.ai_agent import router as ai_router
from routers.teachers import router as teachers_router
from routers.password_reset import router as password_reset_router
from routers.google_oauth import router as google_oauth_router

logging.basicConfig(
    level=logging.WARNING if os.getenv("ENV") == "production" else logging.DEBUG,
    format="[%(asctime)s] %(levelname)s %(name)s | %(message)s",
)
logger = logging.getLogger("siee.core")

SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=os.getenv("ENV", "development"),
        traces_sample_rate=0.05,
        profiles_sample_rate=0.0,
        enable_tracing=False,
    )
    logger.info("sentry initialized (env=%s)", os.getenv("ENV", "development"))

FINANCIAL_LOCKED_PATHS: tuple[str, ...] = (
    "/api/grades/download-pdf",
    "/api/grades/report-card",
    "/api/grades/bulletin",
    "/api/students/report",
    "/api/reports/",
)

# ── General Rate Limiter (in-memory, per-worker) ──
# NOTE: in-memory only — if scaling to multiple workers/instances,
# migrate to Redis-backed limiter (e.g. Upstash Redis, slowapi + redis).
# See Others.md §8 for discussion.
_api_calls: dict[str, list[float]] = defaultdict(list)
_api_calls_lock = threading.Lock()
API_RATE_LIMIT: int = int(os.getenv("API_RATE_LIMIT", "120"))  # requests per window
API_RATE_WINDOW: int = 60  # 1 minute window


def _check_api_rate_limit(ip: str) -> bool:
    now = time.time()
    window = API_RATE_WINDOW
    # Lock guards the compound read-modify-write against threadpool races.
    with _api_calls_lock:
        _api_calls[ip] = [t for t in _api_calls[ip] if now - t < window]
        if len(_api_calls[ip]) >= API_RATE_LIMIT:
            return False
        _api_calls[ip].append(now)
        return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("siee core booting (Supabase)")
    try:
        db: Client = next(dep_get_db())
        db.table("profiles").select("id").limit(1).execute()
        logger.info("supabase connection verified")
    except Exception:
        logger.info("supabase ping — run seed.sql in Supabase Dashboard first if you see 403s")
    yield
    logger.info("vyntra core stopped")


app = FastAPI(title="Vyntra Core — Academic Platform", version="5.0.0", lifespan=lifespan)


def _get_cors_origin(request: Request) -> str:
    origin = request.headers.get("Origin", "")
    if origin in ALLOWED_ORIGINS:
        return origin
    import re
    if re.match(r"^https?://localhost(:\d+)?$", origin):
        return origin
    return "https://colegiociudaddelsol.edu.co"


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    origin = _get_cors_origin(request)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        },
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s\n%s", exc, traceback.format_exc())
    status = getattr(exc, "status_code", 500)
    detail = getattr(exc, "detail", "Error interno del servidor")
    origin = _get_cors_origin(request)
    return JSONResponse(
        status_code=status,
        content={"detail": detail},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        },
    )


ALLOWED_ORIGINS: list[str] = [
    "https://vyntraacademic.netlify.app",
    "http://localhost:4321",
    "http://localhost:8000",
]
_env_origins = os.getenv("ALLOWED_ORIGINS", "")
if _env_origins:
    ALLOWED_ORIGINS.extend([o.strip() for o in _env_origins.split(",") if o.strip()])
# Remove wildcard to avoid CORS + credentials conflicts
ALLOWED_ORIGINS = [o for o in ALLOWED_ORIGINS if o != "*"]


MAX_BODY_SIZE = int(os.getenv("MAX_BODY_SIZE", "10485760"))  # 10 MB default

@app.middleware("http")
async def body_size_limit_middleware(request: Request, call_next: Any) -> Response:
    if request.method in ("POST", "PUT", "PATCH"):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY_SIZE:
            origin = _get_cors_origin(request)
            return JSONResponse(status_code=413, content={"detail": "Payload demasiado grande. Máximo 10 MB."},
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Credentials": "true",
                },
            )
    return await call_next(request)


@app.middleware("http")
async def csrf_middleware(request: Request, call_next: Any) -> Response:
    try:
        validate_csrf(request)
    except HTTPException as e:
        origin = _get_cors_origin(request)
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail},
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
            },
        )
    return await call_next(request)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next: Any) -> Response:
    if not request.url.path.startswith("/api"):
        return await call_next(request)
    client_ip = request.client.host if request.client else "unknown"
    if not _check_api_rate_limit(client_ip):
        origin = _get_cors_origin(request)
        return JSONResponse(
            status_code=429,
            content={"detail": "Demasiadas solicitudes. Intenta de nuevo en un minuto."},
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
                "Retry-After": "60",
            },
        )
    return await call_next(request)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next: Any) -> Response:
    if request.method == "OPTIONS":
        origin = request.headers.get("Origin", "")
        if origin in ALLOWED_ORIGINS:
            return Response(
                status_code=204,
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-CSRF-Token, Cache-Control",
                    "Access-Control-Max-Age": "600",
                },
            )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "0"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    origin = request.headers.get("Origin", "")
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


@app.middleware("http")
async def auth_middleware(request: Request, call_next: Any) -> Response:
    path = request.url.path
    if request.method == "OPTIONS" or path in SKIP_AUTH_PATHS or (request.method == "GET" and path.startswith("/api/notices")):
        return await call_next(request)
    origin = _get_cors_origin(request)
    # Support both Authorization header and httpOnly cookie
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        token = request.cookies.get("access_token", "")
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Authorization required"}, headers={"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true"})
    try:
        claims = decode_jwt(token)
    except jwt.ExpiredSignatureError:
        return JSONResponse(status_code=401, content={"detail": "Token expired"}, headers={"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true"})
    except jwt.PyJWTError:
        return JSONResponse(status_code=401, content={"detail": "Invalid token"}, headers={"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true"})
    request.state.user_id = claims["sub"]
    request.state.user_role = claims.get("role", "student")
    return await call_next(request)


@app.middleware("http")
async def financial_guard_middleware(request: Request, call_next: Any) -> Response:
    if not is_financial_locked_path(request.url.path):
        return await call_next(request)
    # All FINANCIAL_LOCKED_PATHS are GET endpoints (download-pdf, report).
    # student_id comes from query params only — no body reading required.
    student_id = request.query_params.get("student_id")
    origin = _get_cors_origin(request)
    if not student_id:
        return JSONResponse(status_code=422, content={"detail": "Query param student_id required"}, headers={"Access-Control-Allow-Origin": origin})
    try:
        db: Client = next(dep_get_db())
        result = db.table("student_metadata").select("*").eq("profile_id", student_id).execute()
        rows = result.data
        if not rows:
            return JSONResponse(status_code=404, content={"detail": "Student not found"}, headers={"Access-Control-Allow-Origin": origin})
        meta = rows[0]
        if meta.get("months_in_arrears", 0) >= 2 and not meta.get("financial_override", False):
            logger.warning("financial-block student=%s path=%s", student_id, request.url.path)
            return JSONResponse(
                status_code=403,
                content={"detail": "Estatus financiero irregular — Descarga restringida por mora"},
                headers={"Access-Control-Allow-Origin": origin},
            )
    except Exception as e:
        logger.error("financial guard error: %s", e)
        # Fail-closed: never let a download proceed when the security check
        # itself fails. A transient DB error must not become a bypass vector.
        return JSONResponse(
            status_code=503,
            content={"detail": "No se pudo verificar el estatus financiero. Intenta de nuevo."},
            headers={"Access-Control-Allow-Origin": origin},
        )
    return await call_next(request)


app.include_router(auth_router)
app.include_router(students_router)
app.include_router(grades_router)
app.include_router(notices_router)
app.include_router(subjects_router)
app.include_router(exams_router)
app.include_router(admin_router)
app.include_router(ai_router)
app.include_router(teachers_router)
app.include_router(password_reset_router)
app.include_router(google_oauth_router)


@app.get("/")
async def root() -> dict[str, Any]:
    return {"status": "online", "message": "Vyntra Core — Academic Platform v5", "colegio": "Ciudad del Sol"}


# ── Pre-warmed cache ──
_warmup_done = False


@app.get("/api/warmup")
async def warmup() -> dict[str, Any]:
    global _warmup_done
    db: Client = next(dep_get_db())
    try:
        db.table("profiles").select("count").limit(1).execute()
        _warmup_done = True
        return {"status": "warm", "database": "connected"}
    except Exception as e:
        return {"status": "cold", "error": str(e)}


@app.api_route("/api/health", methods=["GET", "HEAD"])
async def health() -> Response:
    return JSONResponse(
        {"status": "alive", "ws_connected": ws_manager.count, "database": "supabase", "warm": _warmup_done},
    )


# ── Response compression ──
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, token: str = Query(..., min_length=1)) -> None:
    try:
        claims = decode_jwt(token)
    except jwt.PyJWTError:
        await websocket.close(code=4001, reason="invalid_token")
        return
    user_id = claims["sub"]
    await websocket.accept()
    await ws_manager.register(user_id, websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "invalid_json"})
                continue
            logger.debug("ws-in %s -> %s", user_id, msg.get("type"))
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        await ws_manager.unregister(user_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
