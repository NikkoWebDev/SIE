from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

_dotenv_path = Path(__file__).resolve().parent.parent / ".env"
if _dotenv_path.exists():
    load_dotenv(_dotenv_path)

import traceback

import jwt
from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from supabase import Client

from config.database import get_db
from dependencies import (
    JWT_ALGORITHM, JWT_SECRET, SKIP_AUTH_PATHS,
    decode_jwt, get_db as dep_get_db, is_financial_locked_path,
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

logging.basicConfig(
    level=logging.WARNING if os.getenv("ENV") == "production" else logging.DEBUG,
    format="[%(asctime)s] %(levelname)s %(name)s | %(message)s",
)
logger = logging.getLogger("siee.core")

FINANCIAL_LOCKED_PATHS: tuple[str, ...] = (
    "/api/grades/download-pdf",
    "/api/grades/report-card",
    "/api/grades/bulletin",
    "/api/students/report",
    "/api/reports/",
)


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
    logger.info("siee core stopped")


app = FastAPI(title="SIEE Core — Solara Academic (Supabase)", version="5.0.0", lifespan=lifespan)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s\n%s", exc, traceback.format_exc())
    status = exc.status_code if isinstance(exc, StarletteHTTPException) else 500
    detail = exc.detail if isinstance(exc, StarletteHTTPException) else "Error interno del servidor"
    return JSONResponse(
        status_code=status,
        content={"detail": detail},
        headers={"Access-Control-Allow-Origin": "*"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def auth_middleware(request: Request, call_next: Any) -> Response:
    path = request.url.path
    if request.method == "OPTIONS" or path.startswith("/ws") or path in SKIP_AUTH_PATHS:
        return await call_next(request)
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Authorization required"}, headers={"Access-Control-Allow-Origin": "*"})
    try:
        claims = decode_jwt(auth_header[7:])
    except jwt.ExpiredSignatureError:
        return JSONResponse(status_code=401, content={"detail": "Token expired"}, headers={"Access-Control-Allow-Origin": "*"})
    except jwt.PyJWTError:
        return JSONResponse(status_code=401, content={"detail": "Invalid token"}, headers={"Access-Control-Allow-Origin": "*"})
    request.state.user_id = claims["sub"]
    request.state.user_role = claims.get("role", "student")
    return await call_next(request)


@app.middleware("http")
async def financial_guard_middleware(request: Request, call_next: Any) -> Response:
    if not is_financial_locked_path(request.url.path):
        return await call_next(request)
    student_id = request.query_params.get("student_id")
    if not student_id and request.method == "POST":
        try:
            body = await request.body()
            parsed = json.loads(body)
            student_id = parsed.get("student_id")
        except Exception:
            pass
    if not student_id:
        return JSONResponse(status_code=422, content={"detail": "Query param student_id required"}, headers={"Access-Control-Allow-Origin": "*"})
    try:
        db: Client = next(dep_get_db())
        result = db.table("student_metadata").select("*").eq("profile_id", student_id).execute()
        rows = result.data
        if not rows:
            return JSONResponse(status_code=404, content={"detail": "Student not found"}, headers={"Access-Control-Allow-Origin": "*"})
        meta = rows[0]
        if meta.get("months_in_arrears", 0) >= 2 and not meta.get("financial_override", False):
            logger.warning("financial-block student=%s path=%s", student_id, request.url.path)
            return JSONResponse(
                status_code=403,
                content={"detail": "Estatus financiero irregular — Descarga restringida por mora"},
                headers={"Access-Control-Allow-Origin": "*"},
            )
    except Exception as e:
        logger.error("financial guard error: %s", e)
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


@app.get("/")
async def root() -> dict[str, Any]:
    return {"status": "online", "message": "SIEE Core — Solara Academic (Supabase v5)", "colegio": "Ciudad del Sol"}


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "status": "alive",
        "ws_connected": ws_manager.count,
        "database": "supabase",
    }


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
