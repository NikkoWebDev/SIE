from datetime import datetime, timezone
from typing import Any

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from supabase import Client

from config.database import get_db
from dependencies import auth_dependency, financial_guard, is_financial_locked_path
from models import StudentUpdate, StudentMetadataSchema, grade_status, OutageReport

logger = logging.getLogger("siee.students")
router = APIRouter(prefix="/api", tags=["students"])


@router.get("/students")
async def list_students(request: Request, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    grade = request.query_params.get("grade")
    meta_col = request.query_params.get("column", "grade")
    query = db.table("profiles").select("id, login_credential, fullname, role, is_active")
    if grade:
        query = query.eq("role", "student")
    result = query.execute()
    students: list[dict[str, Any]] = []
    for s in result.data:
        students.append({
            "profile_id": s["id"],
            "login_credential": s["login_credential"],
            "fullname": s["fullname"],
            "role": s["role"],
            "is_active": s.get("is_active", True),
        })
    return JSONResponse(content=students)


@router.get("/students/risk")
async def get_risk_students(user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("grades").select("student_id, score").execute()
    risk_map: dict[str, float] = {}
    count_map: dict[str, int] = {}
    for g in result.data:
        sid = g.get("student_id")
        if sid:
            risk_map[sid] = risk_map.get(sid, 0) + float(g.get("score", 0))
            count_map[sid] = count_map.get(sid, 0) + 1
    risk_ids = {sid for sid in risk_map if (risk_map[sid] / count_map[sid]) < 3.5}
    students = []
    for rid in risk_ids:
        p = db.table("profiles").select("*").eq("id", rid).execute()
        if p.data:
            profile = p.data[0]
            students.append({
                "profile_id": rid,
                "login_credential": profile.get("login_credential"),
                "fullname": profile.get("fullname"),
                "avg_score": round(risk_map[rid] / count_map[rid], 1),
                "status": "En Riesgo",
            })
    return JSONResponse(content=students)


@router.get("/students/{profile_id}")
async def get_student(profile_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("profiles").select("*").eq("id", profile_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    profile = result.data[0]

    meta_result = db.table("student_metadata").select("*").eq("profile_id", profile_id).execute()
    metadata = meta_result.data[0] if meta_result.data else {}

    return JSONResponse(content={
        "profile_id": profile["id"],
        "login_credential": profile["login_credential"],
        "fullname": profile["fullname"],
        "role": profile["role"],
        "is_active": profile.get("is_active", True),
        "metadata": {
            "months_in_arrears": metadata.get("months_in_arrears", 0),
            "financial_override": metadata.get("financial_override", False),
            "total_balance": float(metadata.get("total_balance", 0)),
            "current_status": metadata.get("current_status", "AL_DIA"),
            "guardian_info": metadata.get("guardian_info", ""),
        },
    })


@router.get("/students/{student_id}/grades")
async def get_student_grades(student_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("grades").select("*").eq("student_id", student_id).order("created_at", desc=True).execute()
    grades: list[dict[str, Any]] = []
    for g in result.data:
        grades.append({
            "subject_id": g.get("subject_id"),
            "project_id": g.get("project_id"),
            "score": float(g.get("score", 0)),
            "observations": g.get("observations", ""),
            "created_at": str(g.get("created_at", "")),
        })
    return JSONResponse(content=grades)


@router.get("/students/{student_id}/report")
async def get_student_report(student_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    if is_financial_locked_path("/api/students/report"):
        req = type("_R", (), {"query_params": {"student_id": student_id}})()
        await financial_guard(req)

    profile_result = db.table("profiles").select("*").eq("id", student_id).execute()
    if not profile_result.data:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    profile = profile_result.data[0]

    meta_result = db.table("student_metadata").select("*").eq("profile_id", student_id).execute()
    metadata = meta_result.data[0] if meta_result.data else {}

    grades_result = db.table("grades").select("*").eq("student_id", student_id).order("created_at", desc=True).execute()
    grades: list[dict[str, Any]] = []
    for g in grades_result.data:
        grades.append({
            "subject_id": g.get("subject_id"),
            "project_id": g.get("project_id"),
            "score": float(g.get("score", 0)),
            "observations": g.get("observations", ""),
            "created_at": str(g.get("created_at", "")),
        })

    avg_score = sum(g["score"] for g in grades) / len(grades) if grades else 0.0
    return JSONResponse(content={
        "student": profile.get("fullname"),
        "grade": metadata.get("current_status", ""),
        "is_on_time": metadata.get("months_in_arrears", 0) < 2 or metadata.get("financial_override", False),
        "promedio": round(avg_score, 1),
        "estado": grade_status(avg_score),
        "grades": grades,
    })


@router.put("/students/{profile_id}")
async def update_student(profile_id: str, data: StudentUpdate, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = db.table("profiles").update(update_data).eq("id", profile_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return JSONResponse(content={"message": "Estudiante actualizado"})


@router.post("/admin/students/{profile_id}/toggle-payment")
async def toggle_payment(profile_id: str, data: StudentMetadataSchema, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    meta_result = db.table("student_metadata").select("*").eq("profile_id", profile_id).execute()
    if not meta_result.data:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    meta = meta_result.data[0]
    new_status = "AL_DIA" if data.months_in_arrears < 2 else "EN_MORA"
    db.table("student_metadata").update({
        "months_in_arrears": data.months_in_arrears,
        "financial_override": data.financial_override,
        "current_status": new_status,
    }).eq("profile_id", profile_id).execute()

    return JSONResponse(content={"message": "Estado financiero actualizado"})


@router.get("/students/{profile_id}/financial-status")
async def check_financial_status(profile_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    meta_result = db.table("student_metadata").select("*").eq("profile_id", profile_id).execute()
    if not meta_result.data:
        return JSONResponse(content={"is_blocked": False, "reason": "No metadata found"})
    meta = meta_result.data[0]
    months = meta.get("months_in_arrears", 0)
    override = meta.get("financial_override", False)
    is_blocked = months >= 2 and not override
    return JSONResponse(content={
        "is_blocked": is_blocked,
        "months_in_arrears": months,
        "financial_override": override,
        "current_status": meta.get("current_status", "AL_DIA"),
    })


@router.post("/students/{profile_id}/bypass-override")
async def toggle_financial_override(profile_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    admin = db.table("profiles").select("role").eq("id", user_id).execute()
    if not admin.data or admin.data[0].get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo rector puede modificar override")

    meta_result = db.table("student_metadata").select("*").eq("profile_id", profile_id).execute()
    if not meta_result.data:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    current = meta_result.data[0].get("financial_override", False)
    from datetime import datetime, timezone
    db.table("student_metadata").update({
        "financial_override": not current,
        "financial_override_by": user_id,
        "financial_override_at": datetime.now(timezone.utc).isoformat(),
    }).eq("profile_id", profile_id).execute()

    return JSONResponse(content={
        "message": "Override toggled",
        "financial_override": not current,
    })


@router.delete("/admin/students/{profile_id}")
async def delete_student(profile_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    db.table("student_metadata").delete().eq("profile_id", profile_id).execute()
    db.table("profiles").delete().eq("id", profile_id).execute()
    return JSONResponse(content={"message": "Estudiante eliminado"})


@router.post("/students/report-outage")
async def report_outage(data: OutageReport, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    now = datetime.now(timezone.utc).isoformat()

    progress = db.table("exam_progress").select("*").eq("student_id", data.student_id).eq("exam_id", data.exam_id).execute()
    if progress.data:
        existing = progress.data[0]
        current_answers = existing.get("current_responses", existing.get("answers", {}))
        db.table("exam_progress").update({
            "status": "interrupted",
            "current_responses": current_answers,
            "last_saved_at": now,
            "time_elapsed_seconds": existing.get("time_elapsed_seconds", 0),
        }).eq("id", existing["id"]).execute()

    doc = data.model_dump()
    doc["incident_type"] = "power_outage"
    doc["severity"] = "high"
    doc["description"] = data.description or "Posible fallo técnico (Corte de fluido/red)"
    doc["created_at"] = now
    db.table("incident_reports").insert(doc).execute()

    return JSONResponse(content={
        "status": "outage_logged",
        "message": "Progreso guardado. Tus respuestas están a salvo.",
        "can_resume": True,
        "at": now,
    })


@router.get("/students/{student_id}/behavior-logs")
async def get_behavior_logs(student_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    try:
        result = db.table("behavior_logs").select("*").eq("student_id", student_id).order("created_at", desc=True).limit(50).execute()
        logs = []
        for r in result.data:
            logs.append({
                "id": r.get("id"),
                "student_id": r.get("student_id"),
                "log_type": r.get("log_type", "positive"),
                "description": r.get("description", ""),
                "recorded_by": r.get("recorded_by", ""),
                "created_at": str(r.get("created_at", "")),
            })
        return JSONResponse(content=logs)
    except Exception as e:
        logger.warning("behavior logs fetch error: %s", e)
        return JSONResponse(content=[])


@router.get("/students/{student_id}/materials")
async def get_student_materials(student_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    try:
        meta = db.table("student_metadata").select("course_id").eq("profile_id", student_id).execute()
        if not meta.data or not meta.data[0].get("course_id"):
            return JSONResponse(content=[])
        course_id = meta.data[0]["course_id"]
        course = db.table("courses").select("name").eq("id", course_id).execute()
        if not course.data:
            return JSONResponse(content=[])
        grade_id = course.data[0]["name"]

        mats = db.table("class_materials").select("*").eq("grade_id", grade_id).order("created_at", desc=True).execute()
        subject_ids = {m["subject_id"] for m in mats.data if m.get("subject_id")}
        subjects_map = {}
        if subject_ids:
            subs = db.table("subjects").select("id, name").in_("id", list(subject_ids)).execute()
            for s in subs.data:
                subjects_map[s["id"]] = s.get("name", "")

        materials = []
        for m in mats.data:
            materials.append({
                "id": m.get("id"),
                "subject_id": m.get("subject_id", ""),
                "subject_name": subjects_map.get(m.get("subject_id", ""), ""),
                "grade_id": m.get("grade_id", ""),
                "file_url": m.get("file_url", ""),
                "file_type": m.get("file_type", "md"),
                "uploaded_by": m.get("uploaded_by", ""),
                "created_at": str(m.get("created_at", "")),
            })
        return JSONResponse(content=materials)
    except Exception as e:
        logger.warning("student materials fetch error: %s", e)
        return JSONResponse(content=[])
