from __future__ import annotations

import logging
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdf_canvas
from supabase import Client

from config.database import get_db
from dependencies import (
    MAX_GRADE, RISK_THRESHOLD,
    auth_dependency, financial_guard, is_financial_locked_path,
)
from models import grade_color, grade_status

logger = logging.getLogger("siee.grades")
router = APIRouter(prefix="/api", tags=["grades"])


@router.get("/grades")
async def get_grades(
    student_id: Optional[str] = Query(None),
    teacher_id: Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    limit: int = Query(100),
    user_id: str = Depends(auth_dependency),
) -> JSONResponse:
    db: Client = next(get_db())
    query = db.table("grades").select("*")
    if student_id:
        query = query.eq("student_id", student_id)
    if teacher_id:
        query = query.eq("teacher_id", teacher_id)
    if subject:
        query = query.eq("subject_id", subject)
    result = query.order("created_at", desc=True).limit(limit).execute()

    subjects_map: dict[str, str] = {}
    try:
        all_subjects = db.table("subjects").select("id, name").execute()
        for s in all_subjects.data:
            subjects_map[s["id"]] = s.get("name", s["id"])
    except Exception:
        pass

    grades = []
    for g in result.data:
        sid = g.get("subject_id", "")
        grades.append({
            "id": g.get("id"),
            "student_id": g.get("student_id"),
            "subject_id": sid,
            "subject_name": subjects_map.get(sid, sid),
            "project_id": g.get("project_id"),
            "score": float(g.get("score", 0)),
            "observations": g.get("observations", ""),
            "created_at": str(g.get("created_at", "")),
            "teacher_id": g.get("teacher_id"),
            "course_id": g.get("course_id"),
        })
    return JSONResponse(content=grades)


@router.get("/teacher/grades")
async def list_teacher_grades(
    grade: str = Query(None),
    subject: str = Query(None),
    user_id: str = Depends(auth_dependency),
) -> JSONResponse:
    db: Client = next(get_db())
    query = db.table("grades").select("*")
    if grade:
        query = query.eq("course_id", grade)
    if subject:
        query = query.eq("subject_id", subject)
    result = query.order("created_at", desc=True).execute()
    grades = []
    for g in result.data:
        grades.append({
            "student_id": g.get("student_id"),
            "subject_id": g.get("subject_id"),
            "project_id": g.get("project_id"),
            "score": float(g.get("score", 0)),
            "observations": g.get("observations", ""),
            "created_at": str(g.get("created_at", "")),
        })
    return JSONResponse(content=grades)


@router.get("/student/my-grades/{student_id}")
async def get_my_grades(student_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("grades").select("*").eq("student_id", student_id).order("created_at", desc=True).execute()
    grades = []
    for g in result.data:
        grades.append({
            "subject": g.get("subject_id"),
            "grade": float(g.get("score", 0)),
            "observations": g.get("observations", ""),
            "created_at": str(g.get("created_at", "")),
        })
    return JSONResponse(content=grades)


@router.get("/grades/download-pdf")
async def download_grade_pdf(
    student_id: str = Query(..., min_length=1),
    user_id: str = Depends(auth_dependency),
) -> Response:
    db: Client = next(get_db())
    if is_financial_locked_path("/api/grades/download-pdf"):
        req = type("_R", (), {"query_params": {"student_id": student_id}})()
        await financial_guard(req)

    result = db.table("grades").select("*").eq("student_id", student_id).order("created_at", desc=True).execute()
    grades = result.data

    profile_result = db.table("profiles").select("fullname").eq("id", student_id).execute()
    name = profile_result.data[0]["fullname"] if profile_result.data else student_id

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
        score_val = float(g.get("score", 0))
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
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
