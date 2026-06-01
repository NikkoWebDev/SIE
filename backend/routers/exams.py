from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from supabase import Client

from config.database import get_db
from dependencies import auth_dependency, financial_guard, is_financial_locked_path
from managers import ws_manager
from models import ExamCreate, ExamProgressSchema, ExamSubmit, IncidentReport, grade_status

logger = logging.getLogger("siee.exams")
router = APIRouter(prefix="/api", tags=["exams"])


@router.post("/teacher/create-exam", status_code=201)
async def create_exam(data: ExamCreate, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    doc = data.model_dump()
    doc["questions"] = [q.model_dump() for q in doc["questions"]]
    doc["is_active"] = True
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    result = db.table("exams").insert(doc).execute()
    exam_id = result.data[0]["id"]
    return JSONResponse(content={"message": "Examen creado", "exam_id": exam_id}, status_code=201)


@router.get("/teacher/exams")
async def list_exams(
    grade: Optional[str] = None,
    subject: Optional[str] = None,
    user_id: str = Depends(auth_dependency),
) -> JSONResponse:
    db: Client = next(get_db())
    query = db.table("exams").select("*")
    if grade:
        query = query.eq("grade", grade)
    if subject:
        query = query.eq("subject", subject)
    result = query.order("created_at", desc=True).execute()
    return JSONResponse(content=result.data)


@router.get("/student/exams")
async def list_student_exams(grade: Optional[str] = None, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    query = db.table("exams").select("*").eq("is_active", True)
    if grade:
        query = query.eq("grade", grade)
    result = query.order("created_at", desc=True).execute()
    for exam in result.data:
        questions = exam.get("questions", [])
        for q in questions:
            if "correct" in q:
                del q["correct"]
    return JSONResponse(content=result.data)


@router.get("/student/exam/{exam_id}")
async def get_exam(exam_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("exams").select("*").eq("id", exam_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Examen no encontrado")
    exam = result.data[0]
    for q in exam.get("questions", []):
        if "correct" in q:
            del q["correct"]
    return JSONResponse(content=exam)


@router.post("/student/submit-exam")
async def submit_exam(data: ExamSubmit, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())

    exam_result = db.table("exams").select("*").eq("id", data.exam_id).execute()
    if not exam_result.data:
        raise HTTPException(status_code=404, detail="Examen no encontrado")
    exam = exam_result.data[0]

    questions = exam.get("questions", [])
    if not questions:
        raise HTTPException(status_code=400, detail="Examen sin preguntas")

    dupe = db.table("exam_results").select("*").eq("student_id", data.student_id).eq("exam_id", data.exam_id).execute()
    if dupe.data:
        raise HTTPException(status_code=400, detail="Ya has presentado este examen")

    correct_count = 0
    for i, ans in enumerate(data.answers):
        if i < len(questions) and ans == questions[i].get("correct"):
            correct_count += 1

    final_grade = round((correct_count / len(questions)) * 5, 1) if questions else 0.0
    now = datetime.now(timezone.utc).isoformat()

    db.table("exam_results").insert({
        "student_id": data.student_id,
        "exam_id": data.exam_id,
        "score": final_grade,
        "correct": correct_count,
        "total": len(questions),
        "created_at": now,
    }).execute()

    subject_name = exam.get("subject", "")
    subject_lookup = db.table("subjects").select("id").eq("name", subject_name).execute()
    resolved_subject_id = subject_lookup.data[0]["id"] if subject_lookup.data else ""

    db.table("grades").upsert({
        "student_id": data.student_id,
        "subject_id": resolved_subject_id,
        "project_id": f"exam_{data.exam_id[:8]}",
        "score": final_grade,
        "observations": f"Nota automática: {exam.get('title', 'Examen')}",
        "created_at": now,
        "teacher_id": user_id,
        "course_id": exam.get("grade", ""),
    }, on_conflict="student_id, subject_id, project_id").execute()

    if final_grade < 3.5:
        profile = db.table("profiles").select("fullname").eq("id", data.student_id).execute()
        student_name = profile.data[0].get("fullname", "") if profile.data else ""
        risk_doc = {
            "student_id": data.student_id,
            "alert_type": "exam_risk",
            "severity": "high" if final_grade < 2.5 else "medium",
            "avg_score": final_grade,
            "reason": f"Examen reprobado ({final_grade}) en {exam.get('title', '')}",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        db.table("risk_alerts").insert(risk_doc).execute()
        await ws_manager.broadcast({
            "type": "RISK_ALERT",
            "student_id": data.student_id,
            "student_name": student_name,
            "avg_score": final_grade,
            "subject": exam.get("title", ""),
            "severity": risk_doc["severity"],
        })

    return JSONResponse(content={
        "grade": final_grade,
        "correct": correct_count,
        "total": len(questions),
        "status": grade_status(final_grade),
    })


@router.post("/exam/save-progress")
async def save_exam_progress(data: ExamProgressSchema, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    now = datetime.now(timezone.utc).isoformat()
    doc = data.model_dump()
    doc["last_saved_at"] = now

    existing = db.table("exam_progress").select("*").eq("student_id", data.student_id).eq("exam_id", data.exam_id).execute()
    if existing.data:
        db.table("exam_progress").update(doc).eq("id", existing.data[0]["id"]).execute()
    else:
        db.table("exam_progress").insert(doc).execute()

    return JSONResponse(content={"status": "saved", "at": now})


@router.get("/exam/progress/{student_id}/{exam_id}")
async def get_exam_progress(student_id: str, exam_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("exam_progress").select("*").eq("student_id", student_id).eq("exam_id", exam_id).execute()
    if not result.data:
        return JSONResponse(content={})
    return JSONResponse(content=result.data[0])


@router.get("/teacher/exam-results/{exam_id}")
async def get_exam_results(exam_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("exam_results").select("*").eq("exam_id", exam_id).execute()
    formatted = []
    for r in result.data:
        formatted.append({
            "student_id": r.get("student_id"),
            "grade": float(r.get("score", 0)),
            "correct": r.get("correct"),
            "total": r.get("total"),
            "created_at": str(r.get("created_at", "")),
        })
    return JSONResponse(content=formatted)


@router.post("/exams/report-incident")
async def report_incident(data: IncidentReport, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    doc = data.model_dump()
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    db.table("incident_reports").insert(doc).execute()
    await ws_manager.broadcast({
        "type": "exam_interrupted",
        "student_id": doc.get("student_id"),
        "exam_id": doc.get("exam_id"),
        "incident_type": doc.get("incident_type"),
        "created_at": doc["created_at"],
    })
    return JSONResponse(content={"status": "ok"})


@router.get("/exam-incidents")
async def list_incidents(user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("incident_reports").select("*").order("created_at", desc=True).limit(100).execute()
    return JSONResponse(content=result.data)


@router.post("/exam/handle-disconnect")
async def handle_disconnect(data: IncidentReport, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    doc = data.model_dump()
    doc["incident_type"] = "network_loss"
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    db.table("incident_reports").insert(doc).execute()

    progress = db.table("exam_progress").select("*").eq("student_id", data.student_id).eq("exam_id", data.exam_id).execute()
    if progress.data:
        db.table("exam_progress").update({"interrupted": True, "last_saved_at": doc["created_at"]}).eq("id", progress.data[0]["id"]).execute()

    await ws_manager.broadcast({
        "type": "exam_interrupted",
        "student_id": doc.get("student_id"),
        "exam_id": doc.get("exam_id"),
        "incident_type": "network_loss",
        "created_at": doc["created_at"],
    })
    return JSONResponse(content={"status": "disconnect_logged", "can_resume": True})


@router.get("/risk-alerts")
async def list_risk_alerts(
    student_id: str = Query("", description="Filter by student"),
    days: int = Query(30, description="Look back days"),
    user_id: str = Depends(auth_dependency),
) -> JSONResponse:
    db: Client = next(get_db())
    query = db.table("risk_alerts").select("*").order("created_at", desc=True).limit(100)
    if student_id:
        query = query.eq("student_id", student_id)
    result = query.execute()
    return JSONResponse(content=result.data)
