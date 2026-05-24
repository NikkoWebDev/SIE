from __future__ import annotations

import asyncio
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

import jwt
from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from dependencies import (
    JWT_ALGORITHM, JWT_SECRET, MONGO_DB, MONGO_URI, SKIP_AUTH_PATHS,
    decode_jwt, get_db, init_db, is_financial_locked_path,
)
from routers.grades import get_risk_queue, risk_agent_worker, set_ws_manager
from routers.auth import router as auth_router, _hydrate_fallback
from routers.students import router as students_router
from routers.grades import router as grades_router
from routers.notices import router as notices_router
from routers.subjects import router as subjects_router
from routers.exams import router as exams_router
from routers.admin import router as admin_router

logging.basicConfig(
    level=logging.WARNING if os.getenv("ENV") == "production" else logging.DEBUG,
    format="[%(asctime)s] %(levelname)s %(name)s | %(message)s",
)
logger = logging.getLogger("siee.core")

COLLECTIONS: tuple[str, ...] = (
    "students", "admins", "grades", "notices", "subjects", "guides",
    "deliveries", "assignments", "exams", "exam_results", "exam_incidents",
    "candidates", "votes",
)

FINANCIAL_LOCKED_PATHS: tuple[str, ...] = (
    "/api/grades/download-pdf",
    "/api/grades/report-card",
    "/api/grades/bulletin",
    "/api/students/report",
    "/api/reports/",
)

_worker_task: asyncio.Task[None] | None = None


# ---------------------------------------------------------------------------
# EcosystemSocketManager (WebSocket live alerts)
# ---------------------------------------------------------------------------
class EcosystemSocketManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def register(self, user_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self.active_connections[user_id] = ws
        logger.debug("ws+ %s (total=%d)", user_id, len(self.active_connections))

    async def unregister(self, user_id: str) -> None:
        async with self._lock:
            ws = self.active_connections.pop(user_id, None)
        if ws:
            try:
                await ws.close()
            except Exception:
                pass
        logger.debug("ws- %s (total=%d)", user_id, len(self.active_connections))

    async def send(self, user_id: str, payload: dict[str, Any]) -> bool:
        async with self._lock:
            ws = self.active_connections.get(user_id)
        if ws is None:
            return False
        try:
            await ws.send_json(payload)
            return True
        except Exception:
            await self.unregister(user_id)
            return False

    async def broadcast(self, payload: dict[str, Any]) -> int:
        async with self._lock:
            snapshot = list(self.active_connections.items())
        sent = 0
        for uid, ws in snapshot:
            try:
                await ws.send_json(payload)
                sent += 1
            except Exception:
                await self.unregister(uid)
        return sent

    @property
    def count(self) -> int:
        return len(self.active_connections)


ws_manager = EcosystemSocketManager()


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _worker_task
    logger.info("siee core booting")
    await init_db()
    db = get_db()
    await _hydrate_fallback(db)
    try:
        for coll in COLLECTIONS:
            await db.create_collection(coll)
    except Exception:
        pass
    try:
        await db["grades"].create_index(
            [("student_id", 1), ("subject_id", 1), ("created_at", -1)],
            name="idx_grade_student_subject", background=True,
        )
        await db["students"].create_index(
            [("is_at_risk", 1), ("is_paid", 1)], name="idx_student_flags", background=True,
        )
        await db["students"].create_index("document_id", unique=True, background=True, name="idx_student_doc")
    except Exception:
        pass
    set_ws_manager(ws_manager)
    _worker_task = asyncio.create_task(risk_agent_worker())
    yield
    logger.info("siee core shutting down")
    await get_risk_queue().put(None)
    if _worker_task:
        try:
            await asyncio.wait_for(_worker_task, timeout=10.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            _worker_task.cancel()
    from dependencies import close_db
    await close_db()
    logger.info("siee core stopped")


app = FastAPI(title="SIEE Core — Solara Academic", version="4.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def auth_middleware(request: Request, call_next: Any) -> Response:
    path = request.url.path
    if request.method == "OPTIONS" or path.startswith("/ws") or path in SKIP_AUTH_PATHS:
        return await call_next(request)
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Authorization required"})
    try:
        claims = decode_jwt(auth_header[7:])
    except jwt.ExpiredSignatureError:
        return JSONResponse(status_code=401, content={"detail": "Token expired"})
    except jwt.PyJWTError:
        return JSONResponse(status_code=401, content={"detail": "Invalid token"})
    request.state.user_id = claims["sub"]
    request.state.user_role = claims.get("role", "ESTUDIANTE")
    return await call_next(request)


# ---------------------------------------------------------------------------
# Financial guard middleware
# ---------------------------------------------------------------------------
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
        return JSONResponse(status_code=422, content={"detail": "Query param student_id required"})
    db = get_db()
    student = await db["students"].find_one({"document_id": student_id})
    if student is None:
        return JSONResponse(status_code=404, content={"detail": "Student not found"})
    if student.get("is_paid") is False:
        logger.warning("financial-block student=%s path=%s", student_id, request.url.path)
        return JSONResponse(status_code=403, content={"detail": "⚠️ Estatus financiero irregular — Descarga restringida por mora"})
    return await call_next(request)


# ---------------------------------------------------------------------------
# Router mounts
# ---------------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(students_router)
app.include_router(grades_router)
app.include_router(notices_router)
app.include_router(subjects_router)
app.include_router(exams_router)
app.include_router(admin_router)


@app.get("/")
async def root() -> dict[str, Any]:
    return {"status": "online", "message": "SIEE Core — Solara Academic Backend v4.0.0", "colegio": "Ciudad del Sol"}


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "status": "alive",
        "queue_depth": get_risk_queue().qsize(),
        "ws_connected": ws_manager.count,
    }


# ---------------------------------------------------------------------------
# WebSocket (live risk alerts + ABP notifications)
# ---------------------------------------------------------------------------
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
