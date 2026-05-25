from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdf_canvas

from dependencies import (
    MAX_GRADE, RISK_THRESHOLD,
    auth_dependency, financial_guard, get_db, is_financial_locked_path,
)
from models import GradeSubmission, RiskEvent, grade_color, grade_status

logger = logging.getLogger("siee.grades")

router = APIRouter(prefix="/api", tags=["grades"])

risk_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1024)
ws_manager: Any = None

_abp_propagated_subjects = frozenset({
    "matematicas", "ciencias", "humanidades",
    "tecnologia", "emprendimiento", "artistica",
    "educacion_fisica", "etica", "ingles",
})


def set_ws_manager(mgr: Any) -> None:
    global ws_manager
    ws_manager = mgr


def get_risk_queue() -> asyncio.Queue[dict[str, Any]]:
    return risk_queue


async def _mutate_risk(db: Any, student_id: str, at_risk: bool) -> None:
    await db["students"].update_one(
        {"document_id": student_id},
        {"$set": {
            "is_at_risk": at_risk,
            "risk_updated_at": datetime.now(timezone.utc),
        }},
    )


async def _propagate_abp_grade(db: Any, sub: GradeSubmission) -> list[str]:
    propagated: list[str] = []
    normalized = sub.project_id.strip().lower()
    if "abp" not in normalized and "proyecto" not in normalized:
        return propagated

    from motor.motor_asyncio import AsyncIOMotorCollection
    coll: AsyncIOMotorCollection = db["grades"]
    now = datetime.now(timezone.utc)
    for target in _abp_propagated_subjects:
        if target == sub.subject_id.strip().lower():
            continue
        doc = sub.model_dump()
        doc["subject_id"] = target
        doc["score"] = sub.score
        doc["observations"] = f"[ABP Propagado] Nota integrada desde proyecto: {sub.project_id}"
        doc["created_at"] = now
        doc["propagated_from"] = sub.subject_id
        await coll.update_one(
            {"student_id": sub.student_id, "subject_id": target, "project_id": sub.project_id},
            {"$set": doc},
            upsert=True,
        )
        propagated.append(target)
    return propagated


async def risk_agent_worker() -> None:
    logger.info("risk-agent started")
    while True:
        event = await risk_queue.get()
        if event is None:
            risk_queue.task_done()
            break
        try:
            student_id = str(event["student_id"])
            teacher_id = str(event["teacher_id"])
            score = float(event["score"])
            at_risk = score < RISK_THRESHOLD
            await _mutate_risk(get_db(), student_id, at_risk)
            if at_risk:
                alert = RiskEvent(
                    type="RISK_ALERT",
                    msg="Plan de Apoyo Requerido — Agenda cita académica",
                    student_id=student_id,
                    materia=str(event.get("subject_id", "")),
                    score=score,
                    nota=score,
                    is_at_risk=True,
                ).model_dump()
                if ws_manager:
                    await ws_manager.send(student_id, alert)
                    await ws_manager.send(teacher_id, alert)
            logger.info("risk-agent student=%s score=%.1f at_risk=%s q=%d", student_id, score, at_risk, risk_queue.qsize())
        except Exception:
            logger.exception("risk-agent failed event=%s", event)
        finally:
            risk_queue.task_done()
    logger.info("risk-agent stopped")


@router.post("/teacher/submit-grade", status_code=201)
async def submit_grade(submission: GradeSubmission, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    doc = submission.model_dump()
    doc["created_at"] = datetime.now(timezone.utc)
    result = await db["grades"].update_one(
        {"student_id": submission.student_id, "subject_id": submission.subject_id, "project_id": submission.project_id},
        {"$set": doc},
        upsert=True,
    )
    grade_id = str(result.upserted_id) if result.upserted_id else "updated"

    propagated = await _propagate_abp_grade(db, submission)

    await risk_queue.put({
        "student_id": submission.student_id,
        "teacher_id": submission.teacher_id,
        "course_id": submission.course_id,
        "project_id": submission.project_id,
        "subject_id": submission.subject_id,
        "score": submission.score,
        "grade_id": grade_id,
    })

    logger.info("grade=%s student=%s score=%.1f propagated=%s", grade_id, submission.student_id, submission.score, propagated)
    return JSONResponse(status_code=201, content={
        "grade_id": grade_id,
        "status": "accepted",
        "abp_propagated": propagated,
    })


@router.get("/teacher/grades")
async def list_teacher_grades(
    grade: str = Query(None),
    subject: str = Query(None),
    user_id: str = Depends(auth_dependency),
) -> JSONResponse:
    db = get_db()
    query: dict[str, Any] = {}
    if grade:
        query["course_id"] = grade
    if subject:
        query["subject_id"] = subject
    cursor = db["grades"].find(query).sort("created_at", -1)
    grades: list[dict[str, Any]] = []
    async for g in cursor:
        grades.append({
            "student_id": g.get("student_id"),
            "subject_id": g.get("subject_id"),
            "project_id": g.get("project_id"),
            "score": g.get("score"),
            "observations": g.get("observations", ""),
            "created_at": str(g.get("created_at", "")),
        })
    return JSONResponse(content=grades)


@router.get("/student/my-grades/{student_id}")
async def get_my_grades(student_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    cursor = db["grades"].find({"student_id": student_id}).sort("created_at", -1)
    grades: list[dict[str, Any]] = []
    async for g in cursor:
        grades.append({
            "subject": g.get("subject_id"),
            "grade": g.get("score"),
            "observations": g.get("observations", ""),
            "created_at": str(g.get("created_at", "")),
        })
    return JSONResponse(content=grades)


@router.get("/grades/download-pdf")
async def download_grade_pdf(
    student_id: str = Query(..., min_length=1),
    user_id: str = Depends(auth_dependency),
) -> Response:
    db = get_db()
    if is_financial_locked_path("/api/grades/download-pdf"):
        req = type("_R", (), {"query_params": {"student_id": student_id}})()
        await financial_guard(req)

    cursor = db["grades"].find({"student_id": student_id}).sort("created_at", -1)
    grades = await cursor.to_list(length=100)

    student = await db["students"].find_one({"document_id": student_id})
    name = student.get("fullname", student_id) if student else student_id

    buf = BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, h - 60, "Colegio Técnico Ciudad del Sol")
    c.setFont("Helvetica", 12)
    c.drawString(50, h - 80, "Sistema de Información Estudiantil — Boletín Académico")
    c.drawString(50, h - 100, f"Estudiante: {name}")
    c.drawString(50, h - 115, f"ID: {student_id}")
    c.drawString(50, h - 130, f"Fecha: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    c.setStrokeColorRGB(0.5, 0, 0)
    c.line(50, h - 140, w - 50, h - 140)

    y = h - 165
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Asignatura")
    c.drawString(180, y, "Proyecto ABP")
    c.drawString(330, y, "Nota")
    c.drawString(400, y, "Estado")

    c.setFont("Helvetica", 10)
    for g in grades:
        y -= 18
        if y < 60:
            c.showPage()
            y = h - 60
        score_val = g.get("score", 0)
        estado = grade_status(score_val)
        c.setFillColorRGB(*_hex_to_rgb(grade_color(score_val)))
        c.drawString(50, y, str(g.get("subject_id", "-"))[:24])
        c.drawString(180, y, str(g.get("project_id", "-"))[:22])
        c.drawString(330, y, f"{score_val:.1f}")
        c.drawString(400, y, estado)
        c.setFillColorRGB(0, 0, 0)

    c.save()
    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="boletin_{student_id}.pdf"'},
    )


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))
