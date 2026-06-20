from datetime import datetime, timezone
from typing import Any, Optional

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from supabase import Client

from config.database import get_db
from dependencies import admin_dependency, audit, auth_dependency, financial_guard, is_financial_locked_path
from models import StudentUpdate, StudentMetadataSchema, grade_status, OutageReport

logger = logging.getLogger("siee.students")
router = APIRouter(prefix="/api", tags=["students"])


@router.get("/students")
async def list_students(
    request: Request,
    grade: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    user_id: str = Depends(auth_dependency),
) -> JSONResponse:
    db: Client = next(get_db())
    query = db.table("profiles").select("id, login_credential, fullname, role, is_active", count="exact")
    query = query.eq("role", "student")
    if grade:
        courses = db.table("courses").select("id").eq("name", grade).execute()
        if courses.data:
            course_ids = [c["id"] for c in courses.data]
            meta_ids = db.table("student_metadata").select("profile_id").in_("course_id", course_ids).execute()
            profile_ids = [m["profile_id"] for m in (meta_ids.data or [])]
            if profile_ids:
                query = query.in_("id", profile_ids)
            else:
                query = query.eq("id", "nonexistent")
    offset = (page - 1) * per_page
    result = query.range(offset, offset + per_page - 1).execute()
    students = [
        {
            "profile_id": s["id"],
            "login_credential": s["login_credential"],
            "fullname": s["fullname"],
            "role": s["role"],
            "is_active": s.get("is_active", True),
        }
        for s in (result.data or [])
    ]
    total = getattr(result, 'count', None) or len(students)
    return JSONResponse(content={
        "data": students,
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": (total + per_page - 1) // per_page,
    })


@router.get("/students/risk")
async def get_risk_students(user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("grades").select("student_id, score").execute()
    if not result.data:
        return JSONResponse(content=[])
    score_map: dict[str, list[float]] = {}
    for g in result.data:
        sid = g.get("student_id")
        if sid:
            score_map.setdefault(sid, []).append(float(g.get("score", 0)))
    risk_ids = [sid for sid, scores in score_map.items() if (sum(scores) / len(scores)) < 3.5]
    if not risk_ids:
        return JSONResponse(content=[])
    profiles = db.table("profiles").select("id, login_credential, fullname").in_("id", risk_ids).execute()
    profile_map = {p["id"]: p for p in (profiles.data or [])}
    students = [
        {
            "profile_id": rid,
            "login_credential": profile_map.get(rid, {}).get("login_credential", ""),
            "fullname": profile_map.get(rid, {}).get("fullname", ""),
            "avg_score": round(sum(score_map[rid]) / len(score_map[rid]), 1),
            "status": "En Riesgo",
        }
        for rid in risk_ids if rid in profile_map
    ]
    return JSONResponse(content=students)


@router.get("/students/{profile_id}")
async def get_student(profile_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    profile = db.table("profiles").select("id, login_credential, fullname, role, is_active").eq("id", profile_id).execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    p = profile.data[0]
    meta = db.table("student_metadata").select("months_in_arrears, financial_override, total_balance, current_status, guardian_info").eq("profile_id", profile_id).execute()
    metadata = meta.data[0] if meta.data else {}
    return JSONResponse(content={
        "profile_id": p["id"],
        "login_credential": p["login_credential"],
        "fullname": p["fullname"],
        "role": p["role"],
        "is_active": p.get("is_active", True),
        "metadata": {
            "months_in_arrears": metadata.get("months_in_arrears", 0),
            "financial_override": metadata.get("financial_override", False),
            "total_balance": float(metadata.get("total_balance", 0)),
            "current_status": metadata.get("current_status", "AL_DIA"),
            "guardian_info": metadata.get("guardian_info", ""),
        },
    })


@router.get("/students/{student_id}/grades")
async def get_student_grades(
    student_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    user_id: str = Depends(auth_dependency),
) -> JSONResponse:
    db: Client = next(get_db())
    role: str = getattr(request.state, "user_role", "")
    if role == "student" and user_id != student_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver las notas de otro estudiante")
    result = db.table("grades").select("subject_id, project_id, score, observations, created_at", count="exact").eq("student_id", student_id).order("created_at", desc=True).execute()
    total = getattr(result, 'count', None) or len(result.data or [])
    grades = [
        {
            "subject_id": g.get("subject_id"),
            "project_id": g.get("project_id"),
            "score": float(g.get("score", 0)),
            "observations": g.get("observations", ""),
            "created_at": str(g.get("created_at", "")),
        }
        for g in (result.data or [])
    ]
    return JSONResponse(content={"data": grades, "total": total})


@router.get("/students/{student_id}/report")
async def get_student_report(student_id: str, request: Request, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    role: str = getattr(request.state, "user_role", "")
    if role == "student" and user_id != student_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver el reporte de otro estudiante")
    if is_financial_locked_path("/api/students/report"):
        class _MockRequest:
            query_params = {"student_id": student_id}
            method = "GET"
            class url:
                path = "/api/students/report"
            @staticmethod
            async def body():
                return b""
        req = _MockRequest()
        await financial_guard(req)
    profile = db.table("profiles").select("fullname").eq("id", student_id).execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    meta = db.table("student_metadata").select("current_status, months_in_arrears, financial_override, course_id").eq("profile_id", student_id).execute()
    metadata = meta.data[0] if meta.data else {}
    grade_name = ""
    course_id = metadata.get("course_id")
    if course_id:
        course = db.table("courses").select("name").eq("id", course_id).execute()
        if course.data:
            grade_name = course.data[0].get("name", "")
    grades_result = db.table("grades").select("subject_id, project_id, score, observations, created_at").eq("student_id", student_id).order("created_at", desc=True).execute()
    grades = [
        {
            "subject_id": g.get("subject_id"),
            "project_id": g.get("project_id"),
            "score": float(g.get("score", 0)),
            "observations": g.get("observations", ""),
            "created_at": str(g.get("created_at", "")),
        }
        for g in (grades_result.data or [])
    ]
    avg_score = sum(g["score"] for g in grades) / len(grades) if grades else 0.0
    return JSONResponse(content={
        "student": profile.data[0].get("fullname"),
        "grade": grade_name,
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
async def toggle_payment(profile_id: str, data: StudentMetadataSchema, user_id: str = Depends(admin_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    meta_result = db.table("student_metadata").select("id").eq("profile_id", profile_id).execute()
    if not meta_result.data:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    new_status = "AL_DIA" if data.months_in_arrears < 2 else "EN_MORA"
    db.table("student_metadata").update({
        "months_in_arrears": data.months_in_arrears,
        "financial_override": data.financial_override,
        "current_status": new_status,
    }).eq("profile_id", profile_id).execute()
    audit.log("payment_toggle", user_id, profile_id, f"months={data.months_in_arrears}, override={data.financial_override}")
    return JSONResponse(content={"message": "Estado financiero actualizado"})


@router.get("/students/{profile_id}/financial-status")
async def check_financial_status(profile_id: str, request: Request, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    role: str = getattr(request.state, "user_role", "")
    if role == "student" and user_id != profile_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver el estado financiero de otro estudiante")
    meta = db.table("student_metadata").select("months_in_arrears, financial_override, current_status").eq("profile_id", profile_id).execute()
    if not meta.data:
        return JSONResponse(content={"is_blocked": False, "reason": "No metadata found"})
    m = meta.data[0]
    months = m.get("months_in_arrears", 0)
    override = m.get("financial_override", False)
    return JSONResponse(content={
        "is_blocked": months >= 2 and not override,
        "months_in_arrears": months,
        "financial_override": override,
        "current_status": m.get("current_status", "AL_DIA"),
    })


@router.post("/students/{profile_id}/bypass-override")
async def toggle_financial_override(profile_id: str, user_id: str = Depends(admin_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    meta = db.table("student_metadata").select("financial_override").eq("profile_id", profile_id).execute()
    if not meta.data:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    current = meta.data[0].get("financial_override", False)
    db.table("student_metadata").update({
        "financial_override": not current,
        "financial_override_by": user_id,
        "financial_override_at": datetime.now(timezone.utc).isoformat(),
    }).eq("profile_id", profile_id).execute()
    audit.log("financial_override_toggle", user_id, profile_id, f"new_value={not current}")
    return JSONResponse(content={"message": "Override toggled", "financial_override": not current})


@router.delete("/admin/students/{profile_id}")
async def delete_student(profile_id: str, user_id: str = Depends(admin_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    db.table("student_metadata").delete().eq("profile_id", profile_id).execute()
    db.table("profiles").delete().eq("id", profile_id).execute()
    audit.log("student_deleted", user_id, profile_id)
    return JSONResponse(content={"message": "Estudiante eliminado"})


@router.post("/students/report-outage")
async def report_outage(data: OutageReport, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    now = datetime.now(timezone.utc).isoformat()
    progress = db.table("exam_progress").select("id, current_responses, answers, time_elapsed_seconds").eq("student_id", data.student_id).eq("exam_id", data.exam_id).execute()
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
        result = db.table("behavior_logs").select("id, student_id, log_type, description, recorded_by, created_at").eq("student_id", student_id).order("created_at", desc=True).limit(50).execute()
        return JSONResponse(content=[{
            "id": r.get("id"),
            "student_id": r.get("student_id"),
            "log_type": r.get("log_type", "positive"),
            "description": r.get("description", ""),
            "recorded_by": r.get("recorded_by", ""),
            "created_at": str(r.get("created_at", "")),
        } for r in (result.data or [])])
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
        mats = db.table("class_materials").select("id, subject_id, grade_id, file_url, file_type, uploaded_by, created_at").eq("grade_id", grade_id).order("created_at", desc=True).execute()
        subject_ids = {m["subject_id"] for m in (mats.data or []) if m.get("subject_id")}
        subjects_map = {}
        if subject_ids:
            subs = db.table("subjects").select("id, name").in_("id", list(subject_ids)).execute()
            subjects_map = {s["id"]: s.get("name", "") for s in (subs.data or [])}
        return JSONResponse(content=[{
            "id": m.get("id"),
            "subject_id": m.get("subject_id", ""),
            "subject_name": subjects_map.get(m.get("subject_id", ""), ""),
            "grade_id": m.get("grade_id", ""),
            "file_url": m.get("file_url", ""),
            "file_type": m.get("file_type", "md"),
            "uploaded_by": m.get("uploaded_by", ""),
            "created_at": str(m.get("created_at", "")),
        } for m in (mats.data or [])])
    except Exception as e:
        logger.warning("student materials fetch error: %s", e)
        return JSONResponse(content=[])


@router.get("/schedule")
async def get_student_schedule(
    student_id: str = Query(..., min_length=1),
    user_id: str = Depends(auth_dependency),
) -> JSONResponse:
    db: Client = next(get_db())
    profile = db.table("profiles").select("id").eq("login_credential", student_id).execute()
    if not profile.data:
        return JSONResponse(content={"days": {}, "hours": []})
    pid = profile.data[0]["id"]
    meta = db.table("student_metadata").select("course_id").eq("profile_id", pid).execute()
    if not meta.data or not meta.data[0].get("course_id"):
        return JSONResponse(content={"days": {}, "hours": []})
    course_id = meta.data[0]["course_id"]
    rows = db.table("class_schedules").select("*, subjects(name)").eq("course_id", course_id).execute()
    if not rows.data:
        return JSONResponse(content={"days": {}, "hours": []})

    def _fmt(t):
        s = str(t)
        return s[:5] if ":" in s else s
    pairs = sorted(set((_fmt(r["start_time"]), _fmt(r["end_time"])) for r in rows.data), key=lambda x: x[0])
    hours = [{"time": f"{st} - {et}"} for st, et in pairs]
    idx_map = {pair: i for i, pair in enumerate(pairs)}
    day_names = {1: "lunes", 2: "martes", 3: "miercoles", 4: "jueves", 5: "viernes"}
    days = {n: [None] * len(hours) for n in day_names.values()}

    for r in rows.data:
        dow = r.get("day_of_week")
        subj = (r.get("subjects") or {}).get("name", "")
        key = (_fmt(r["start_time"]), _fmt(r["end_time"]))
        if dow in day_names and subj and key in idx_map:
            days[day_names[dow]][idx_map[key]] = {"subject": subj}

    return JSONResponse(content={"days": days, "hours": hours})
