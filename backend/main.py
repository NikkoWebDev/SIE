import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

_dotenv_path = Path(__file__).resolve().parent.parent / ".env"
if _dotenv_path.exists():
    load_dotenv(_dotenv_path)

import jwt
from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, model_validator
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdf_canvas

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MONGO_URI: str = os.getenv("MONGO_URL") or os.getenv(
    "MONGODB_URI",
    "mongodb+srv://admin:password@cluster0.example.mongodb.net/?retryWrites=true&w=majority",
)
MONGO_DB: str = os.getenv("MONGO_DB", "sie_core")
GRADES_COLL: str = "grades"
STUDENTS_COLL: str = "students"
RISK_THRESHOLD: float = 3.5
MAX_GRADE: float = 5.0
QUEUE_SIZE: int = int(os.getenv("QUEUE_SIZE", "1024"))
JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")

logging.basicConfig(
    level=logging.WARNING if os.getenv("ENV") == "production" else logging.DEBUG,
    format="[%(asctime)s] %(levelname)s %(name)s | %(message)s",
)
logger = logging.getLogger("siee.core")

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class GradeSubmission(BaseModel):
    student_id: str = Field(..., min_length=1, pattern=r"^\S+$")
    teacher_id: str = Field(..., min_length=1, pattern=r"^\S+$")
    course_id: str = Field(..., min_length=1, pattern=r"^\S+$")
    project_id: str = Field(..., min_length=1, pattern=r"^\S+$")
    subject_id: str = Field(..., min_length=1, pattern=r"^\S+$")
    score: float = Field(..., ge=0.0, le=MAX_GRADE)

    @model_validator(mode="after")
    def _sanitize_ids(self) -> "GradeSubmission":
        self.student_id = self.student_id.strip()
        self.teacher_id = self.teacher_id.strip()
        self.course_id = self.course_id.strip()
        self.project_id = self.project_id.strip()
        self.subject_id = self.subject_id.strip()
        return self


class RiskEvent(BaseModel):
    type: str
    msg: str
    student_id: str = ""
    score: float = 0.0
    threshold: float = RISK_THRESHOLD
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

# ---------------------------------------------------------------------------
# EcosystemSocketManager
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
        if ws is not None:
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

# ---------------------------------------------------------------------------
# Module-level state (populated during lifespan)
# ---------------------------------------------------------------------------
ws_manager: EcosystemSocketManager = EcosystemSocketManager()
mongo_db: Any = None
risk_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=QUEUE_SIZE)
_worker_task: asyncio.Task[None] | None = None

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
async def _persist_grade(db: Any, sub: GradeSubmission) -> str:
    doc = sub.model_dump()
    doc["created_at"] = datetime.now(timezone.utc)
    result = await db[GRADES_COLL].insert_one(doc)
    return str(result.inserted_id)


async def _mutate_risk(db: Any, student_id: str, at_risk: bool) -> None:
    await db[STUDENTS_COLL].update_one(
        {"_id": student_id},
        {"$set": {
            "is_at_risk": at_risk,
            "risk_updated_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )


async def _fetch_student(db: Any, student_id: str) -> dict[str, Any] | None:
    return await db[STUDENTS_COLL].find_one({"_id": student_id})

# ---------------------------------------------------------------------------
# Background risk worker
# ---------------------------------------------------------------------------
async def siee_risk_agent_worker() -> None:
    logger.info("risk-agent started")
    while True:
        event: dict[str, Any] | None = await risk_queue.get()
        if event is None:
            risk_queue.task_done()
            break
        try:
            student_id: str = event["student_id"]
            teacher_id: str = event["teacher_id"]
            score: float = event["score"]

            at_risk = score < RISK_THRESHOLD
            await _mutate_risk(mongo_db, student_id, at_risk)

            if at_risk:
                alert = RiskEvent(
                    type="RISK_ALERT",
                    msg="Plan de Apoyo Requerido: Agenda cita académica",
                    student_id=student_id,
                    score=score,
                ).model_dump()
                await ws_manager.send(student_id, alert)
                await ws_manager.send(teacher_id, alert)

            logger.info(
                "risk-agent student=%s score=%.1f at_risk=%s q=%d",
                student_id, score, at_risk, risk_queue.qsize(),
            )
        except Exception:
            logger.exception("risk-agent failed event=%s", event)
        finally:
            risk_queue.task_done()
    logger.info("risk-agent stopped")

# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global mongo_db, ws_manager, _worker_task

    logger.info("siee core booting")
    mongo_client = AsyncIOMotorClient(
        MONGO_URI,
        maxPoolSize=20,
        minPoolSize=2,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )
    mongo_db = mongo_client[MONGO_DB]
    try:
        await mongo_client.admin.command("ping")
        logger.info("mongodb connected")
    except Exception as exc:
        logger.error("mongodb unreachable: %s", exc)
        raise

    _worker_task = asyncio.create_task(siee_risk_agent_worker())

    try:
        await mongo_db[STUDENTS_COLL].create_index(
            [("is_at_risk", 1), ("risk_updated_at", -1)],
            name="idx_student_risk",
            background=True,
        )
        await mongo_db[GRADES_COLL].create_index(
            [("student_id", 1), ("subject_id", 1), ("created_at", -1)],
            name="idx_grade_student_subject",
            background=True,
        )
    except Exception:
        pass

    yield

    logger.info("siee core shutting down")
    await risk_queue.put(None)
    if _worker_task is not None:
        try:
            await asyncio.wait_for(_worker_task, timeout=10.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            _worker_task.cancel()
    if mongo_client:
        mongo_client.close()
    logger.info("siee core stopped")


app = FastAPI(title="SIEE Core", version="4.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------
SKIP_AUTH: frozenset[str] = frozenset({"/api/health", "/docs", "/openapi.json"})

def _decode_jwt(token: str) -> dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"require": ["sub"]})

# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def auth_middleware(request: Request, call_next: Any) -> Response:
    path = request.url.path
    if request.method == "OPTIONS" or path.startswith("/ws") or path in SKIP_AUTH:
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Authorization required"})

    try:
        claims = _decode_jwt(auth_header[7:])
    except jwt.ExpiredSignatureError:
        return JSONResponse(status_code=401, content={"detail": "Token expired"})
    except jwt.PyJWTError:
        return JSONResponse(status_code=401, content={"detail": "Invalid token"})

    request.state.user_id = claims["sub"]
    return await call_next(request)

# ---------------------------------------------------------------------------
# Financial guard middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def financial_guard_middleware(request: Request, call_next: Any) -> Response:
    if not request.url.path.startswith("/api/grades/download-pdf"):
        return await call_next(request)

    student_id = request.query_params.get("student_id")
    if not student_id:
        return JSONResponse(status_code=422, content={"detail": "Query param student_id required"})

    student = await _fetch_student(mongo_db, student_id)
    if student is None:
        return JSONResponse(status_code=404, content={"detail": "Student not found"})

    if student.get("is_paid") is False:
        logger.warning("financial-block student=%s", student_id)
        return JSONResponse(status_code=403, content={"detail": "Estatus financiero irregular - Descarga restringida"})

    return await call_next(request)

# ---------------------------------------------------------------------------
# HTTP endpoints
# ---------------------------------------------------------------------------
@app.post("/api/teacher/submit-grade", status_code=201)
async def submit_grade(submission: GradeSubmission) -> JSONResponse:
    if mongo_db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    grade_id = await _persist_grade(mongo_db, submission)

    await risk_queue.put({
        "student_id": submission.student_id,
        "teacher_id": submission.teacher_id,
        "course_id": submission.course_id,
        "project_id": submission.project_id,
        "subject_id": submission.subject_id,
        "score": submission.score,
        "grade_id": grade_id,
    })

    logger.info("grade=%s student=%s score=%.1f", grade_id, submission.student_id, submission.score)
    return JSONResponse(status_code=201, content={"grade_id": grade_id, "status": "accepted"})


@app.get("/api/grades/download-pdf")
async def download_grade_pdf(student_id: str = Query(..., min_length=1)) -> Response:
    if mongo_db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    grades_cursor = mongo_db[GRADES_COLL].find({"student_id": student_id}).sort("created_at", -1)
    grades = await grades_cursor.to_list(length=100)

    student = await _fetch_student(mongo_db, student_id)
    name = student.get("nombre", student_id) if student else student_id

    buf = _build_pdf(student_id, name, grades)
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="boletin_{student_id}.pdf"'},
    )


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "status": "alive",
        "queue_depth": risk_queue.qsize(),
        "ws_connected": ws_manager.count,
    }

# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------
@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, token: str = Query(..., min_length=1)) -> None:
    try:
        claims = _decode_jwt(token)
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

# ---------------------------------------------------------------------------
# PDF builder
# ---------------------------------------------------------------------------
def _build_pdf(student_id: str, student_name: str, grades: list[dict[str, Any]]) -> Any:
    from io import BytesIO
    buf = BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, h - 60, "Colegio Técnico Ciudad del Sol")
    c.setFont("Helvetica", 12)
    c.drawString(50, h - 80, "Sistema de Información Estudiantil — Boletín Académico")
    c.drawString(50, h - 100, f"Estudiante: {student_name}  |  ID: {student_id}")
    c.drawString(50, h - 115, f"Fecha: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    c.setStrokeColorRGB(0.5, 0, 0)
    c.line(50, h - 125, w - 50, h - 125)

    y = h - 150
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Asignatura")
    c.drawString(200, y, "Proyecto ABP")
    c.drawString(350, y, "Nota")
    c.drawString(430, y, "Estado")

    c.setFont("Helvetica", 10)
    for g in grades:
        y -= 18
        if y < 60:
            c.showPage()
            y = h - 60
        score = g.get("score", 0)
        if score < 3.5:
            estado = "En Riesgo"
        elif score >= 4.0:
            estado = "Sobresaliente"
        else:
            estado = "Aceptable"
        c.drawString(50, y, str(g.get("subject_id", "-"))[:28])
        c.drawString(200, y, str(g.get("project_id", "-"))[:22])
        c.drawString(350, y, f"{score:.1f}")
        c.drawString(430, y, estado)

    c.save()
    buf.seek(0)
    return buf

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
