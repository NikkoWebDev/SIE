from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from dependencies import auth_dependency, get_db
from models import ExamCreate, ExamSubmit, IncidentReport, VoteRequest

logger = logging.getLogger("siee.exams")
router = APIRouter(prefix="/api", tags=["exams"])


@router.post("/teacher/create-exam", status_code=201)
async def create_exam(data: ExamCreate, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    doc = data.model_dump()
    doc["is_active"] = True
    doc["created_at"] = datetime.now(timezone.utc)
    result = await db["exams"].insert_one(doc)
    return JSONResponse(content={"message": "Examen creado", "exam_id": str(result.inserted_id)}, status_code=201)


@router.get("/teacher/exams")
async def list_exams(
    grade: Optional[str] = None,
    subject: Optional[str] = None,
    user_id: str = Depends(auth_dependency),
) -> JSONResponse:
    db = get_db()
    query: dict[str, Any] = {}
    if grade:
        query["grade"] = grade
    if subject:
        query["subject"] = subject
    exams: list[dict[str, Any]] = []
    async for e in db["exams"].find(query).sort("_id", -1):
        e["_id"] = str(e["_id"])
        exams.append(e)
    return JSONResponse(content=exams)


@router.get("/student/exams")
async def list_student_exams(grade: Optional[str] = None, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    query: dict[str, Any] = {"is_active": True}
    if grade:
        query["grade"] = grade
    exams: list[dict[str, Any]] = []
    async for e in db["exams"].find(query).sort("_id", -1):
        e["_id"] = str(e["_id"])
        for q in e.get("questions", []):
            if "correct" in q:
                del q["correct"]
        exams.append(e)
    return JSONResponse(content=exams)


@router.get("/student/exam/{exam_id}")
async def get_exam(exam_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    try:
        exam = await db["exams"].find_one({"_id": ObjectId(exam_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")
    if not exam:
        raise HTTPException(status_code=404, detail="Examen no encontrado")
    for q in exam.get("questions", []):
        if "correct" in q:
            del q["correct"]
    exam["_id"] = str(exam["_id"])
    return JSONResponse(content=exam)


@router.post("/student/submit-exam")
async def submit_exam(data: ExamSubmit, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    try:
        exam = await db["exams"].find_one({"_id": ObjectId(data.exam_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="ID de examen inválido")
    if not exam:
        raise HTTPException(status_code=404, detail="Examen no encontrado")

    questions = exam.get("questions", [])
    if not questions:
        raise HTTPException(status_code=400, detail="Examen sin preguntas")

    dupe = await db["exam_results"].find_one({
        "student_id": data.student_id,
        "exam_id": data.exam_id,
    })
    if dupe:
        raise HTTPException(status_code=400, detail="Ya has presentado este examen")

    correct_count = 0
    for i, ans in enumerate(data.answers):
        if i < len(questions) and ans == questions[i].get("correct"):
            correct_count += 1

    final_grade = round((correct_count / len(questions)) * 5, 1) if questions else 0.0
    now = datetime.now(timezone.utc)

    await db["exam_results"].insert_one({
        "student_id": data.student_id,
        "exam_id": data.exam_id,
        "grade": final_grade,
        "correct": correct_count,
        "total": len(questions),
        "created_at": now,
    })

    await db["grades"].update_one(
        {"student_id": data.student_id, "subject_id": exam.get("subject", "")},
        {"$set": {
            "student_id": data.student_id,
            "subject_id": exam.get("subject", ""),
            "project_id": f"exam_{data.exam_id[:8]}",
            "score": final_grade,
            "observations": f"Nota automática: {exam.get('title', 'Examen')}",
            "created_at": now,
            "teacher_id": user_id,
            "course_id": exam.get("grade", ""),
        }},
        upsert=True,
    )

    from models import grade_status
    return JSONResponse(content={
        "grade": final_grade,
        "correct": correct_count,
        "total": len(questions),
        "status": grade_status(final_grade),
    })


@router.get("/teacher/exam-results/{exam_id}")
async def get_exam_results(exam_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    results: list[dict[str, Any]] = []
    async for r in db["exam_results"].find({"exam_id": exam_id}):
        results.append({
            "student_id": r.get("student_id"),
            "grade": r.get("grade"),
            "correct": r.get("correct"),
            "total": r.get("total"),
            "created_at": str(r.get("created_at", "")),
        })
    return JSONResponse(content=results)


@router.post("/exams/report-incident")
async def report_incident(data: IncidentReport, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    doc = data.model_dump()
    doc["created_at"] = datetime.now(timezone.utc)
    await db["exam_incidents"].insert_one(doc)
    return JSONResponse(content={"status": "ok"})


@router.get("/exam-incidents")
async def list_incidents(user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    incidents: list[dict[str, Any]] = []
    async for i in db["exam_incidents"].find().sort("_id", -1).limit(100):
        i["_id"] = str(i["_id"])
        incidents.append(i)
    return JSONResponse(content=incidents)
