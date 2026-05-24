import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

_dotenv_path = Path(__file__).resolve().parent.parent / ".env"
if _dotenv_path.exists():
    load_dotenv(_dotenv_path)

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MONGO_URI: str = os.getenv("MONGO_URL") or os.getenv(
    "MONGODB_URI",
    "mongodb+srv://admin:password@cluster0.example.mongodb.net/?retryWrites=true&w=majority",
)
MONGO_DB: str = os.getenv("MONGO_DB", "sie_core")
GRADE_COLLECTION: str = "grades"
STUDENT_COLLECTION: str = "students"
RISK_THRESHOLD: float = 3.5
MAX_GRADE: float = 5.0
QUEUE_BACKLOG: int = int(os.getenv("QUEUE_BACKLOG", "1024"))

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


class RiskStatus(StrEnum):
    SAFE = "safe"
    WARNING = "warning"
    AT_RISK = "at_risk"


class WebSocketPayload(BaseModel):
    kind: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data: dict[str, Any]


# ---------------------------------------------------------------------------
# Internal event
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class InternalEvent:
    event_type: str
    payload: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

# ---------------------------------------------------------------------------
# EcosystemSocketManager
# ---------------------------------------------------------------------------
class EcosystemSocketManager:
    """Maps active WebSocket connections by (role, doc_id)."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def register(self, role: str, user_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self._store.setdefault(role, {})[user_id] = ws
        logger.debug("ws+ %s:%s (total=%d)", role, user_id, await self._total())

    async def unregister(self, role: str, user_id: str) -> None:
        async with self._lock:
            bucket = self._store.get(role)
            if bucket is None:
                return
            bucket.pop(user_id, None)
            if not bucket:
                del self._store[role]
        logger.debug("ws- %s:%s (total=%d)", role, user_id, await self._total())

    async def send(self, role: str, user_id: str, payload: dict[str, Any]) -> bool:
        ws: WebSocket | None
        async with self._lock:
            ws = self._store.get(role, {}).get(user_id)
        if ws is None:
            return False
        try:
            await ws.send_json(payload)
            return True
        except Exception:
            await self.unregister(role, user_id)
            return False

    async def broadcast(self, role: str, payload: dict[str, Any]) -> int:
        async with self._lock:
            snapshot = list(self._store.get(role, {}).items())
        count = 0
        for uid, ws in snapshot:
            try:
                await ws.send_json(payload)
                count += 1
            except Exception:
                await self.unregister(role, uid)
        return count

    async def broadcast_all(self, payload: dict[str, Any]) -> int:
        """Send to every connected socket regardless of role."""
        async with self._lock:
            snapshot: list[tuple[str, str, WebSocket]] = [
                (role, uid, ws)
                for role, bucket in self._store.items()
                for uid, ws in bucket.items()
            ]
        count = 0
        for role, uid, ws in snapshot:
            try:
                await ws.send_json(payload)
                count += 1
            except Exception:
                await self.unregister(role, uid)
        return count

    async def _total(self) -> int:
        return sum(len(b) for b in self._store.values())

    @property
    def stats(self) -> dict[str, int]:
        return {r: len(b) for r, b in self._store.items()}

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def _resolve_risk(score: float) -> RiskStatus:
    if score >= 4.0:
        return RiskStatus.SAFE
    if score >= RISK_THRESHOLD:
        return RiskStatus.WARNING
    return RiskStatus.AT_RISK


async def _persist_grade(db: Any, sub: GradeSubmission) -> str:
    doc = sub.model_dump()
    doc["created_at"] = datetime.now(timezone.utc)
    doc["risk_status"] = _resolve_risk(sub.score)
    result = await db[GRADE_COLLECTION].insert_one(doc)
    return str(result.inserted_id)


async def _flag_student_risk(db: Any, student_id: str, at_risk: bool) -> None:
    await db[STUDENT_COLLECTION].update_one(
        {"_id": student_id},
        {"$set": {
            "is_at_risk": at_risk,
            "risk_updated_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )

# ---------------------------------------------------------------------------
# SIEERiskAgent
# ---------------------------------------------------------------------------
class SIEERiskAgent:
    """Background worker that consumes grade events and enforces the 3.5 rule."""

    def __init__(
        self,
        db: Any,
        queue: asyncio.Queue[InternalEvent],
        ws_manager: EcosystemSocketManager,
    ) -> None:
        self._db = db
        self._queue = queue
        self._ws = ws_manager
        self._task: asyncio.Task[None] | None = None

    async def _process(self, event: InternalEvent) -> None:
        payload = event.payload
        student_id = payload["student_id"]
        teacher_id = payload["teacher_id"]
        score = payload["score"]
        grade_id = payload["grade_id"]

        at_risk = score < RISK_THRESHOLD
        await _flag_student_risk(self._db, student_id, at_risk)

        if at_risk:
            student_alert: dict[str, Any] = {
                "kind": "academic_alert",
                "message": "Plan de Apoyo Requerido",
                "student_id": student_id,
                "course_id": payload["course_id"],
                "subject_id": payload["subject_id"],
                "score": score,
                "threshold": RISK_THRESHOLD,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await self._ws.send("student", student_id, student_alert)

            log_entry: dict[str, Any] = {
                "kind": "risk_event_log",
                "teacher_id": teacher_id,
                "student_id": student_id,
                "grade_id": grade_id,
                "score": score,
                "threshold": RISK_THRESHOLD,
                "message": "Estudiante marcado en riesgo — Plan de Apoyo Requerido",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await self._ws.broadcast(f"teacher_dashboard_{teacher_id}", log_entry)
            await self._ws.send("teacher", teacher_id, log_entry)

        logger.info(
            "risk-agent processed grade=%s student=%s score=%.1f at_risk=%s",
            grade_id, student_id, score, at_risk,
        )

    async def _consume(self) -> None:
        logger.info("risk-agent started")
        while True:
            event = await self._queue.get()
            if event is None:
                self._queue.task_done()
                break
            try:
                await self._process(event)
            except Exception:
                logger.exception("risk-agent failed event=%s", event.event_type)
            finally:
                self._queue.task_done()
        logger.info("risk-agent stopped")

    async def start(self) -> None:
        self._task = asyncio.create_task(self._consume())

    async def stop(self) -> None:
        if self._task is None:
            return
        await self._queue.put(None)  # type: ignore[arg-type]
        try:
            await asyncio.wait_for(self._task, timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("risk-agent stop timed out — cancelling")
            self._task.cancel()

# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------
mongo_client: AsyncIOMotorClient | None = None
db: Any = None
event_queue: asyncio.Queue[InternalEvent] = asyncio.Queue(maxsize=QUEUE_BACKLOG)
ws_manager = EcosystemSocketManager()
risk_agent = SIEERiskAgent(db=None, queue=event_queue, ws_manager=ws_manager)  # type: ignore[arg-type]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global mongo_client, db, risk_agent
    logger.info("siee core booting")

    mongo_client = AsyncIOMotorClient(
        MONGO_URI,
        maxPoolSize=20,
        minPoolSize=2,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )
    db = mongo_client[MONGO_DB]
    try:
        await mongo_client.admin.command("ping")
        logger.info("mongodb connected — %s", MONGO_DB)
    except Exception as exc:
        logger.error("mongodb unreachable: %s", exc)
        raise

    risk_agent._db = db
    await risk_agent.start()

    # ensure compound index for student risk lookups
    await db[STUDENT_COLLECTION].create_index(
        [("is_at_risk", 1), ("risk_updated_at", -1)],
        name="idx_student_risk",
        background=True,
    )
    await db[GRADE_COLLECTION].create_index(
        [("student_id", 1), ("subject_id", 1), ("created_at", -1)],
        name="idx_grade_student_subject",
        background=True,
    )

    yield

    logger.info("siee core shutting down")
    await risk_agent.stop()
    if mongo_client:
        mongo_client.close()
    logger.info("siee core stopped")


app = FastAPI(title="SIEE Core", version="4.0.0", lifespan=lifespan)

# ---------------------------------------------------------------------------
# HTTP endpoints
# ---------------------------------------------------------------------------
@app.post("/api/teacher/submit-grade", status_code=201)
async def submit_grade(submission: GradeSubmission) -> JSONResponse:
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    grade_id = await _persist_grade(db, submission)

    event = InternalEvent(
        event_type="grade_submitted",
        payload={
            "student_id": submission.student_id,
            "teacher_id": submission.teacher_id,
            "course_id": submission.course_id,
            "project_id": submission.project_id,
            "subject_id": submission.subject_id,
            "score": submission.score,
            "grade_id": grade_id,
        },
    )
    await event_queue.put(event)

    logger.info(
        "grade persisted id=%s student=%s score=%.1f",
        grade_id, submission.student_id, submission.score,
    )
    return JSONResponse(
        status_code=201,
        content={"grade_id": grade_id, "status": "accepted", "queued": True},
    )


@app.get("/api/health")
async def health() -> dict[str, str | int | float | dict[str, int]]:
    return {
        "status": "alive",
        "worker_queue_depth": event_queue.qsize(),
        "ws_connections": ws_manager.stats,
    }

# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------
@app.websocket("/ws/{role}/{user_id}")
async def ws_endpoint(websocket: WebSocket, role: str, user_id: str) -> None:
    await websocket.accept()
    await ws_manager.register(role, user_id, websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "invalid_json"})
                continue
            logger.debug("ws in %s:%s -> %s", role, user_id, msg.get("kind"))
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        await ws_manager.unregister(role, user_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
