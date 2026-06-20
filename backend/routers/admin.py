import logging
import secrets
import string
from datetime import datetime, timezone
from typing import Any, Optional

import bcrypt
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from supabase import Client

from config.database import get_admin_db
from config.email import send_email
from dependencies import admin_dependency, audit, auth_dependency
from models import FinancialToggleSchema, UserCreate, VoteRequest

logger = logging.getLogger("siee.admin")
router = APIRouter(prefix="/api/admin", tags=["admin"])


class AbpProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    linked_subject_ids: list[str] = Field(default_factory=list)
    project_trigger_keyword: str = Field(default="abp", max_length=50)
    model_config = {"extra": "forbid"}


class AbpProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    linked_subject_ids: Optional[list[str]] = None
    is_active: Optional[bool] = None
    project_trigger_keyword: Optional[str] = Field(None, max_length=50)
    model_config = {"extra": "forbid"}


@router.get("/stats")
async def admin_stats() -> JSONResponse:
    db: Client = next(get_admin_db())
    total_students = db.table("profiles").select("*", count="exact").eq("role", "student").execute().count
    total_teachers = db.table("profiles").select("*", count="exact").eq("role", "teacher").execute().count
    total_admins = db.table("profiles").select("*", count="exact").eq("role", "admin").execute().count

    # mora count via DB filter (was Python-side aggregation across all rows)
    mora_count = db.table("student_metadata").select("*", count="exact").gte("months_in_arrears", 2).execute().count

    total_notices = db.table("notices").select("*", count="exact").execute().count
    total_exams = db.table("exams").select("*", count="exact").execute().count
    total_grades = db.table("grades").select("*", count="exact").execute().count

    # Sampled average for performance — exact value would require a Postgres RPC.
    # Acceptable since this stat is informational, not critical.
    grades_sample = db.table("grades").select("score").limit(2000).execute()
    scores = [float(g.get("score", 0)) for g in (grades_sample.data or [])]
    promedio = round(sum(scores) / len(scores), 1) if scores else 0.0

    return JSONResponse(content={
        "total_students": total_students or 0,
        "mora": mora_count or 0,
        "total_teachers": total_teachers or 0,
        "total_admins": total_admins or 0,
        "total_notices": total_notices or 0,
        "total_exams": total_exams or 0,
        "total_grades": total_grades or 0,
        "promedio_general": promedio,
    })


@router.get("/mora-students")
async def mora_students() -> JSONResponse:
    db: Client = next(get_admin_db())
    meta_result = db.table("student_metadata").select("profile_id, months_in_arrears, total_balance, current_status").gte("months_in_arrears", 2).execute()
    if not meta_result.data:
        return JSONResponse(content=[])
    profile_ids = [m["profile_id"] for m in meta_result.data if m.get("profile_id")]
    profile_map = {}
    if profile_ids:
        profiles = db.table("profiles").select("id, login_credential, fullname").in_("id", profile_ids).execute()
        profile_map = {p["id"]: p for p in (profiles.data or [])}
    return JSONResponse(content=[{
        "profile_id": m["profile_id"],
        "login_credential": profile_map.get(m["profile_id"], {}).get("login_credential", ""),
        "fullname": profile_map.get(m["profile_id"], {}).get("fullname", ""),
        "months_in_arrears": m.get("months_in_arrears", 0),
        "total_balance": float(m.get("total_balance", 0)),
        "current_status": m.get("current_status", ""),
    } for m in meta_result.data])


@router.post("/candidates", status_code=201)
async def add_candidate(
    name: str = Form(...),
    position: str = Form(...),
    file: UploadFile = File(...),
    user_id: str = Depends(admin_dependency),
) -> JSONResponse:
    try:
        import cloudinary
        import cloudinary.uploader
        result = cloudinary.uploader.upload(file.file, folder="elecciones")
        url = result.get("secure_url")
    except Exception as exc:
        logger.error("cloudinary upload failed: %s", exc)
        raise HTTPException(status_code=500, detail="Error al subir la imagen del candidato")

    db: Client = next(get_admin_db())
    db.table("candidates").insert({
        "name": name,
        "position": position,
        "photo_url": url,
        "votes": 0,
    }).execute()
    return JSONResponse(content={"message": "Candidato registrado"}, status_code=201)


@router.get("/candidates")
async def list_candidates() -> JSONResponse:
    db: Client = next(get_admin_db())
    result = db.table("candidates").select("*").order("name").execute()
    return JSONResponse(content=result.data)


@router.delete("/candidates/{candidate_id}")
async def delete_candidate(candidate_id: str, user_id: str = Depends(admin_dependency)) -> JSONResponse:
    db: Client = next(get_admin_db())
    db.table("candidates").delete().eq("id", candidate_id).execute()
    return JSONResponse(content={"message": "Candidato eliminado"})


@router.get("/election-results")
async def election_results() -> JSONResponse:
    db: Client = next(get_admin_db())
    result = db.table("candidates").select("name, votes, position").order("name").execute()
    return JSONResponse(content=result.data)


@router.post("/election-reset")
async def reset_election(user_id: str = Depends(admin_dependency)) -> JSONResponse:
    db: Client = next(get_admin_db())
    db.table("votes").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    db.table("candidates").update({"votes": 0}).neq("id", "00000000-0000-0000-0000-000000000000").execute()
    audit.log("election_reset", user_id, detail="All votes and candidate tallies reset")
    return JSONResponse(content={"message": "Elección reiniciada — todos los votos eliminados"})


@router.post("/students")
async def enroll_student(data: UserCreate, user_id: str = Depends(admin_dependency)) -> JSONResponse:
    db: Client = next(get_admin_db())
    existing = db.table("profiles").select("id").eq("login_credential", data.login_credential).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="El documento ID ya está registrado")
    hashed = bcrypt.hashpw(data.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    profile_doc = {
        "login_credential": data.login_credential,
        "fullname": data.fullname,
        "role": "student",
        "password_hash": hashed,
        "is_active": True,
    }
    result = db.table("profiles").insert(profile_doc).execute()
    profile_id = result.data[0]["id"]
    audit.log("student_enrolled", user_id, profile_id, f"credential={data.login_credential}")
    grade = getattr(data, "grade", "")
    if grade:
        db.table("student_metadata").insert({
            "profile_id": profile_id,
            "current_status": "AL_DIA",
            "months_in_arrears": 0,
            "total_balance": 0.0,
            "financial_override": False,
        }).execute()
        course = db.table("courses").select("id").eq("grade", grade).execute()
        if course.data:
            db.table("student_metadata").update({"course_id": course.data[0]["id"]}).eq("profile_id", profile_id).execute()
    return JSONResponse(content={"message": "Estudiante matriculado", "profile_id": profile_id}, status_code=201)


class TeacherRegisterRequest(BaseModel):
    document_id: str = Field(..., min_length=1)
    teacher_name: str = Field(..., min_length=3, max_length=120)
    password: str = Field(default="123456", min_length=4, max_length=128)
    model_config = {"extra": "forbid"}


@router.post("/assign-teacher", status_code=201)
async def register_teacher(data: TeacherRegisterRequest, user_id: str = Depends(admin_dependency)) -> JSONResponse:
    db: Client = next(get_admin_db())
    existing = db.table("profiles").select("id").eq("login_credential", data.document_id).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="El docente ya existe")
    hashed = bcrypt.hashpw(data.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    profile_doc = {
        "login_credential": data.document_id,
        "fullname": data.teacher_name,
        "role": "teacher",
        "password_hash": hashed,
        "is_active": True,
    }
    result = db.table("profiles").insert(profile_doc).execute()
    profile_id = result.data[0]["id"]
    audit.log("teacher_registered", user_id, profile_id, f"credential={data.document_id}")
    return JSONResponse(content={"message": "Docente registrado", "profile_id": profile_id}, status_code=201)


# ── Admin Account Creation ──

class AdminCreateRequest(BaseModel):
    login_credential: str = Field(..., min_length=1)
    fullname: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=4, max_length=128)
    email: str = Field(default="", max_length=255)
    model_config = {"extra": "forbid"}


@router.post("/admins", status_code=201)
async def create_admin(data: AdminCreateRequest, user_id: str = Depends(admin_dependency)) -> JSONResponse:
    db: Client = next(get_admin_db())
    existing = db.table("profiles").select("id").eq("login_credential", data.login_credential).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="El usuario ya existe")
    hashed = bcrypt.hashpw(data.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    profile_doc = {
        "login_credential": data.login_credential,
        "fullname": data.fullname,
        "role": "admin",
        "password_hash": hashed,
        "is_active": True,
        "email": data.email,
    }
    result = db.table("profiles").insert(profile_doc).execute()
    logger.info("admin created profile=%s by admin=%s", result.data[0]["id"], user_id)
    return JSONResponse(content={"message": "Administrador creado", "profile_id": result.data[0]["id"]}, status_code=201)


@router.get("/teachers")
async def list_teachers_with_subjects(user_id: str = Depends(admin_dependency)) -> JSONResponse:
    db: Client = next(get_admin_db())
    teachers_profiles = db.table("profiles").select("id, login_credential, fullname").eq("role", "teacher").execute()
    assignments = db.table("teacher_assignments").select("teacher_id, subject_id, grade, subjects!inner(name)").execute()
    assign_map: dict[str, list[dict]] = {}
    for a in assignments.data:
        tid = a.get("teacher_id", "")
        if tid not in assign_map:
            assign_map[tid] = []
        assign_map[tid].append({"name": a.get("subjects", {}).get("name", ""), "subject_id": a.get("subject_id", "")})

    meta_map: dict[str, dict] = {}
    meta_result = db.table("teacher_metadata").select("*").execute()
    for m in meta_result.data:
        meta_map[m["profile_id"]] = m

    teachers = []
    for p in teachers_profiles.data:
        pid = p["id"]
        subjects = assign_map.get(pid, [])
        meta = meta_map.get(pid, {})
        teachers.append({
            "id": pid,
            "document_id": p.get("login_credential", ""),
            "fullname": p.get("fullname", ""),
            "subjects": subjects,
            "is_director": bool(meta.get("director_grade", "")),
            "director_grade": meta.get("director_grade", ""),
        })
    return JSONResponse(content=teachers)


class SubjectAssignRequest(BaseModel):
    subject_id: str = Field(..., min_length=1)
    model_config = {"extra": "forbid"}


@router.put("/teachers/{doc_id}/subjects")
async def assign_teacher_subject(doc_id: str, data: SubjectAssignRequest, user_id: str = Depends(admin_dependency)) -> JSONResponse:
    db: Client = next(get_admin_db())
    teacher = db.table("profiles").select("id").eq("login_credential", doc_id).execute()
    if not teacher.data:
        raise HTTPException(status_code=404, detail="Docente no encontrado")
    teacher_id = teacher.data[0]["id"]
    existing = db.table("teacher_assignments").select("id").eq("teacher_id", teacher_id).eq("subject_id", data.subject_id).execute()
    if existing.data:
        return JSONResponse(content={"message": "La materia ya está asignada a este docente"})
    db.table("teacher_assignments").insert({"teacher_id": teacher_id, "subject_id": data.subject_id}).execute()
    return JSONResponse(content={"message": "Materia asignada al docente"})


class DirectorAssignRequest(BaseModel):
    grade: str = Field(..., min_length=1, max_length=10)
    model_config = {"extra": "forbid"}


@router.patch("/teachers/{doc_id}/director")
async def set_teacher_director(doc_id: str, data: DirectorAssignRequest, user_id: str = Depends(admin_dependency)) -> JSONResponse:
    db: Client = next(get_admin_db())
    teacher = db.table("profiles").select("id").eq("login_credential", doc_id).execute()
    if not teacher.data:
        raise HTTPException(status_code=404, detail="Docente no encontrado")
    teacher_id = teacher.data[0]["id"]
    existing = db.table("teacher_metadata").select("*").eq("profile_id", teacher_id).execute()
    if existing.data:
        db.table("teacher_metadata").update({"director_grade": data.grade}).eq("profile_id", teacher_id).execute()
    else:
        db.table("teacher_metadata").insert({"profile_id": teacher_id, "director_grade": data.grade}).execute()
    course = db.table("courses").select("id").eq("grade", data.grade).execute()
    if course.data:
        db.table("courses").update({"director_id": teacher_id}).eq("id", course.data[0]["id"]).execute()
    return JSONResponse(content={"message": f"Docente marcado como director de {data.grade}"})


@router.delete("/teachers/{doc_id}")
async def delete_teacher_profile(doc_id: str, user_id: str = Depends(admin_dependency)) -> JSONResponse:
    db: Client = next(get_admin_db())
    teacher = db.table("profiles").select("id").eq("login_credential", doc_id).execute()
    if not teacher.data:
        raise HTTPException(status_code=404, detail="Docente no encontrado")
    teacher_id = teacher.data[0]["id"]
    db.table("teacher_assignments").delete().eq("teacher_id", teacher_id).execute()
    db.table("teacher_metadata").delete().eq("profile_id", teacher_id).execute()
    db.table("profiles").delete().eq("id", teacher_id).execute()
    return JSONResponse(content={"message": "Docente eliminado"})


@router.post("/student/cast-vote")
async def cast_vote(data: VoteRequest, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_admin_db())
    if user_id != data.student_id:
        raise HTTPException(status_code=403, detail="No puedes votar por otro estudiante")
    existing = db.table("votes").select("*").eq("student_id", data.student_id).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Ya has votado")

    db.table("votes").insert({
        "student_id": data.student_id,
        "candidate_id": data.candidate_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    if data.candidate_id != "blank":
        candidate = db.table("candidates").select("votes").eq("id", data.candidate_id).execute()
        if candidate.data:
            current_votes = candidate.data[0].get("votes", 0)
            db.table("candidates").update({"votes": current_votes + 1}).eq("id", data.candidate_id).execute()

    return JSONResponse(content={"message": "Voto registrado"})


@router.get("/students")
async def admin_list_students(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    user_id: str = Depends(admin_dependency),
) -> JSONResponse:
    db: Client = next(get_admin_db())
    count_result = db.table("profiles").select("id", count="exact").eq("role", "student").execute()
    total = getattr(count_result, 'count', None) or 0
    offset = (page - 1) * per_page
    profiles = db.table("profiles").select("id, login_credential, fullname").eq("role", "student").range(offset, offset + per_page - 1).execute()
    profile_ids = [p["id"] for p in (profiles.data or [])]
    meta_map = {}
    course_map = {}
    if profile_ids:
        metas = db.table("student_metadata").select("profile_id, months_in_arrears, financial_override, current_status, course_id").in_("profile_id", profile_ids).execute()
        for m in (metas.data or []):
            meta_map[m["profile_id"]] = m
        course_ids = [m.get("course_id") for m in (metas.data or []) if m.get("course_id")]
        if course_ids:
            courses = db.table("courses").select("id, name").in_("id", course_ids).execute()
            course_map = {c["id"]: c.get("name", "") for c in (courses.data or [])}
    return JSONResponse(content={
        "data": [{
            "_id": p["id"],
            "document_id": p.get("login_credential", ""),
            "fullname": p["fullname"],
            "nombre": p["fullname"],
            "grado": course_map.get(meta_map.get(p["id"], {}).get("course_id", ""), ""),
            "grade": course_map.get(meta_map.get(p["id"], {}).get("course_id", ""), ""),
            "is_paid": (meta_map.get(p["id"], {}).get("months_in_arrears", 0) < 2 or meta_map.get(p["id"], {}).get("financial_override", False)),
        } for p in (profiles.data or [])],
        "page": page,
        "per_page": per_page,
        "total": total,
    })


@router.patch("/students/{profile_id}/financial")
async def admin_toggle_financial(profile_id: str, body: FinancialToggleSchema, user_id: str = Depends(admin_dependency)) -> JSONResponse:
    db: Client = next(get_admin_db())
    is_paid = body.is_paid
    update = {
        "months_in_arrears": 0 if is_paid else 2,
        "current_status": "AL_DIA" if is_paid else "EN_MORA",
    }
    db.table("student_metadata").update(update).eq("profile_id", profile_id).execute()
    audit.log("financial_toggle", user_id, profile_id, f"is_paid={is_paid}")
    return JSONResponse(content={"message": "Estado actualizado"})


@router.get("/at-risk-students")
async def risk_students() -> JSONResponse:
    db: Client = next(get_admin_db())
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
    return JSONResponse(content=[{
        "profile_id": rid,
        "login_credential": profile_map.get(rid, {}).get("login_credential"),
        "fullname": profile_map.get(rid, {}).get("fullname"),
        "avg_score": round(sum(score_map[rid]) / len(score_map[rid]), 1),
    } for rid in risk_ids if rid in profile_map])


# ── Financial Summary ──────────────────────────────────────────────

@router.get("/financial-summary")
async def financial_summary() -> JSONResponse:
    db: Client = next(get_admin_db())

    profiles = db.table("profiles").select("id").eq("role", "student").execute()
    total_students = len(profiles.data)

    meta = db.table("student_metadata").select("profile_id, months_in_arrears, total_balance, financial_override").execute()
    total_arrears = 0.0
    arrears_count = 0
    override_count = 0
    paid_count = 0

    for m in meta.data:
        bal = float(m.get("total_balance", 0))
        months = m.get("months_in_arrears", 0)
        override = m.get("financial_override", False)

        total_arrears += bal
        if months >= 2 and not override:
            arrears_count += 1
        else:
            paid_count += 1
        if override:
            override_count += 1

    return JSONResponse(content={
        "total_students": total_students,
        "total_collected": round(total_arrears, 2),
        "total_in_arrears": arrears_count,
        "total_paid": paid_count,
        "active_overrides": override_count,
        "collection_rate": round((paid_count / total_students * 100) if total_students else 0, 1),
    })


# ── Incident Monitor ───────────────────────────────────────────────

@router.get("/incidents")
async def list_incidents(limit: int = Query(50, ge=1, le=200)) -> JSONResponse:
    db: Client = next(get_admin_db())
    result = db.table("incident_reports").select("id, student_id, exam_id, incident_type, severity, description, created_at").order("created_at", desc=True).limit(limit).execute()
    if not result.data:
        return JSONResponse(content=[])
    student_ids = list({inc.get("student_id") for inc in result.data if inc.get("student_id")})
    exam_ids = list({inc.get("exam_id") for inc in result.data if inc.get("exam_id")})
    profile_map = {}
    if student_ids:
        profiles = db.table("profiles").select("id, fullname").in_("id", student_ids).execute()
        profile_map = {p["id"]: p.get("fullname", "") for p in (profiles.data or [])}
    exam_map = {}
    if exam_ids:
        exams = db.table("exams").select("id, title").in_("id", exam_ids).execute()
        exam_map = {e["id"]: e.get("title", "") for e in (exams.data or [])}
    status_map = {
        "network_loss": "Interrumpido por Red — Progreso a Salvo",
        "power_loss": "Interrumpido por Fluido Eléctrico — Progreso a Salvo",
        "suspicious": "Comportamiento Anómalo Detectado",
        "tab_switch": "Cambio de Ventana Registrado",
    }
    return JSONResponse(content=[{
        "id": inc.get("id"),
        "student_id": inc.get("student_id"),
        "student_name": profile_map.get(inc.get("student_id"), ""),
        "exam_id": inc.get("exam_id"),
        "exam_title": exam_map.get(inc.get("exam_id"), ""),
        "incident_type": inc.get("incident_type", "unknown"),
        "status": status_map.get(inc.get("incident_type"), f"Incidente: {inc.get('incident_type', 'unknown')}"),
        "severity": inc.get("severity", "low"),
        "description": inc.get("description", ""),
        "created_at": str(inc.get("created_at", "")),
    } for inc in result.data])


# ── ABP Project Linker ─────────────────────────────────────────────

@router.get("/abp-projects")
async def list_abp_projects() -> JSONResponse:
    db: Client = next(get_admin_db())
    try:
        result = db.table("abp_projects").select("id, name, description, linked_subject_ids, is_active, project_trigger_keyword, created_at").order("created_at", desc=True).execute()
    except Exception as exc:
        logger.warning("abp_projects table not accessible: %s", exc)
        return JSONResponse(content=[])
    if not result.data:
        return JSONResponse(content=[])
    all_subject_ids = list({sid for p in result.data for sid in (p.get("linked_subject_ids") or [])})
    subject_map = {}
    if all_subject_ids:
        subs = db.table("subjects").select("id, name").in_("id", all_subject_ids).execute()
        subject_map = {s["id"]: s.get("name", "") for s in (subs.data or [])}
    return JSONResponse(content=[{
        "id": p.get("id"),
        "name": p.get("name"),
        "description": p.get("description", ""),
        "linked_subject_ids": p.get("linked_subject_ids") or [],
        "linked_subject_names": [subject_map.get(sid, sid) for sid in (p.get("linked_subject_ids") or [])],
        "is_active": p.get("is_active", True),
        "project_trigger_keyword": p.get("project_trigger_keyword", "abp"),
        "created_at": str(p.get("created_at", "")),
    } for p in result.data])


@router.post("/abp-projects", status_code=201)
async def create_abp_project(data: AbpProjectCreate, user_id: str = Depends(admin_dependency)) -> JSONResponse:
    db: Client = next(get_admin_db())
    try:
        db.table("abp_projects").select("id").limit(1).execute()
    except Exception as exc:
        logger.error("abp_projects table missing: %s", exc)
        raise HTTPException(status_code=503, detail="La tabla abp_projects no existe. Ejecuta la migración DDL.")
    doc = data.model_dump()
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    doc["updated_at"] = doc["created_at"]
    result = db.table("abp_projects").insert(doc).execute()
    return JSONResponse(content={"message": "Proyecto ABP creado", "id": result.data[0]["id"]}, status_code=201)


@router.put("/abp-projects/{project_id}")
async def update_abp_project(project_id: str, data: AbpProjectUpdate, user_id: str = Depends(admin_dependency)) -> JSONResponse:
    db: Client = next(get_admin_db())
    update_data = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = db.table("abp_projects").update(update_data).eq("id", project_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Proyecto ABP no encontrado")
    return JSONResponse(content={"message": "Proyecto ABP actualizado"})


@router.delete("/abp-projects/{project_id}")
async def delete_abp_project(project_id: str, user_id: str = Depends(admin_dependency)) -> JSONResponse:
    db: Client = next(get_admin_db())
    result = db.table("abp_projects").delete().eq("id", project_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Proyecto ABP no encontrado")
    return JSONResponse(content={"message": "Proyecto ABP eliminado"})


# ── Digital Materials Processed ──────────────────────────────────

@router.get("/materials-count")
async def materials_count() -> JSONResponse:
    db: Client = next(get_admin_db())
    try:
        result = db.table("class_materials").select("*", count="exact").execute()
        total = result.count or 0
        by_type = {}
        for r in (result.data or []):
            ft = r.get("file_type", "unknown")
            by_type[ft] = by_type.get(ft, 0) + 1
    except Exception as e:
        logger.warning("class_materials_stats error: %s", e)
        total = 0
        by_type = {}
    return JSONResponse(content={"total": total, "by_type": by_type})


# ── Global Skill Thermometer ────────────────────────────────────

@router.get("/skill-thermometer")
async def skill_thermometer() -> JSONResponse:
    db: Client = next(get_admin_db())
    try:
        results = db.table("exam_results").select("score").execute()
        scores = [float(r.get("score", 0)) for r in results.data] if results.data else []
    except Exception as e:
        logger.warning("skill_thermometer error: %s", e)
        scores = []
    total = len(scores)
    oro = sum(1 for s in scores if s >= 4.0)
    plata = sum(1 for s in scores if 3.0 <= s < 4.0)
    bronce = sum(1 for s in scores if s < 3.0)
    avg_score = round(sum(scores) / total, 2) if total else 0.0
    return JSONResponse(content={
        "total_quizzes": total,
        "oro": oro,
        "plata": plata,
        "bronce": bronce,
        "average_score": avg_score,
        "oro_pct": round(oro / total * 100, 1) if total else 0,
        "plata_pct": round(plata / total * 100, 1) if total else 0,
        "bronce_pct": round(bronce / total * 100, 1) if total else 0,
    })


# ── Consola de Identidades ──────────────────────────────────────

class ResetPasswordRequest(BaseModel):
    profile_id: str = Field(..., min_length=1)

def _generate_temp_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

@router.get("/identity-directory")
async def identity_directory(search: str = Query("", max_length=100)) -> JSONResponse:
    db: Client = next(get_admin_db())
    profiles = db.table("profiles").select("id, fullname, login_credential, role, is_active").execute()
    items = profiles.data or []
    if search:
        q = search.lower()
        items = [p for p in items if q in (p.get("fullname") or "").lower() or q in (p.get("login_credential") or "").lower()]
    profile_ids = [p["id"] for p in items if p.get("role") == "student"]
    meta_map = {}
    if profile_ids:
        metas = db.table("student_metadata").select("profile_id, current_status").in_("profile_id", profile_ids).execute()
        meta_map = {m["profile_id"]: m.get("current_status", "") for m in (metas.data or [])}
    for p in items:
        p["grade"] = meta_map.get(p["id"], "")
    return JSONResponse(content=items)


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, user_id: str = Depends(admin_dependency)) -> JSONResponse:
    db: Client = next(get_admin_db())
    profile = db.table("profiles").select("id, fullname, login_credential, email").eq("id", data.profile_id).execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    prof = profile.data[0]
    temp_pass = _generate_temp_password()
    hashed = bcrypt.hashpw(temp_pass.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    db.table("profiles").update({"password_hash": hashed}).eq("id", data.profile_id).execute()

    email = prof.get("email")
    if email:
        try:
            send_email(email, "VYNTRA — Contraseña temporal", f"Hola {prof.get('fullname', 'Usuario')},\n\nTu contraseña temporal es: {temp_pass}\n\n— Equipo VYNTRA")
        except Exception:
            logger.warning("temp password not delivered by email for profile=%s", data.profile_id)
    else:
        logger.warning("temp password not delivered: profile has no email for profile=%s", data.profile_id)

    logger.info("password reset profile=%s by admin=%s", data.profile_id, user_id)
    return JSONResponse(content={
        "status": "reset",
        "profile_id": data.profile_id,
        "fullname": prof.get("fullname", ""),
        "login_credential": prof.get("login_credential", ""),
    })
