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

from config.database import get_db
from dependencies import admin_dependency, auth_dependency
from models import FinancialToggleSchema, VoteRequest

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
    db: Client = next(get_db())
    total_students = db.table("profiles").select("*", count="exact").eq("role", "student").execute().count
    total_teachers = db.table("profiles").select("*", count="exact").eq("role", "teacher").execute().count
    total_admins = db.table("profiles").select("*", count="exact").eq("role", "admin").execute().count

    mora_count = 0
    meta_result = db.table("student_metadata").select("months_in_arrears").execute()
    for m in meta_result.data:
        if m.get("months_in_arrears", 0) >= 2:
            mora_count += 1

    total_notices = db.table("notices").select("*", count="exact").execute().count
    total_exams = db.table("exams").select("*", count="exact").execute().count
    total_grades = db.table("grades").select("*", count="exact").execute().count

    grades_data = db.table("grades").select("score").execute()
    scores = [float(g.get("score", 0)) for g in grades_data.data]
    promedio = round(sum(scores) / len(scores), 1) if scores else 0.0

    return JSONResponse(content={
        "total_students": total_students or 0,
        "mora": mora_count,
        "total_teachers": (total_teachers or 0) + (total_admins or 0),
        "total_notices": total_notices or 0,
        "total_exams": total_exams or 0,
        "total_grades": total_grades or 0,
        "promedio_general": promedio,
    })


@router.get("/mora-students")
async def mora_students() -> JSONResponse:
    db: Client = next(get_db())
    meta_result = db.table("student_metadata").select("profile_id, months_in_arrears, total_balance, current_status").gte("months_in_arrears", 2).execute()
    students = []
    for m in meta_result.data:
        p = db.table("profiles").select("login_credential, fullname").eq("id", m["profile_id"]).execute()
        profile = p.data[0] if p.data else {}
        students.append({
            "profile_id": m["profile_id"],
            "login_credential": profile.get("login_credential", ""),
            "fullname": profile.get("fullname", ""),
            "months_in_arrears": m.get("months_in_arrears", 0),
            "total_balance": float(m.get("total_balance", 0)),
            "current_status": m.get("current_status", ""),
        })
    return JSONResponse(content=students)


@router.post("/candidates", status_code=201)
async def add_candidate(
    name: str = Form(...),
    position: str = Form(...),
    file: UploadFile = File(...),
    user_id: str = Depends(auth_dependency),
) -> JSONResponse:
    try:
        import cloudinary
        import cloudinary.uploader
        result = cloudinary.uploader.upload(file.file, folder="elecciones")
        url = result.get("secure_url")
    except Exception as exc:
        logger.error("cloudinary upload failed: %s", exc)
        raise HTTPException(status_code=500, detail="Error al subir la imagen del candidato")

    db: Client = next(get_db())
    db.table("candidates").insert({
        "name": name,
        "position": position,
        "photo_url": url,
        "votes": 0,
    }).execute()
    return JSONResponse(content={"message": "Candidato registrado"}, status_code=201)


@router.get("/candidates")
async def list_candidates() -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("candidates").select("*").order("name").execute()
    return JSONResponse(content=result.data)


@router.delete("/candidates/{candidate_id}")
async def delete_candidate(candidate_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    db.table("candidates").delete().eq("id", candidate_id).execute()
    return JSONResponse(content={"message": "Candidato eliminado"})


@router.get("/election-results")
async def election_results() -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("candidates").select("name, votes, position").order("name").execute()
    return JSONResponse(content=result.data)


@router.post("/student/cast-vote")
async def cast_vote(data: VoteRequest, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
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
async def admin_list_students(user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    profiles = db.table("profiles").select("*").eq("role", "student").execute()
    students: list[dict[str, Any]] = []
    for p in profiles.data:
        meta = db.table("student_metadata").select("*").eq("profile_id", p["id"]).execute()
        m = meta.data[0] if meta.data else {}
        months = m.get("months_in_arrears", 0)
        is_paid = months < 2 or m.get("financial_override", False)
        students.append({
            "_id": p["id"],
            "nombre": p["fullname"],
            "grado": m.get("current_status", ""),
            "is_paid": is_paid,
        })
    return JSONResponse(content=students)


@router.patch("/students/{profile_id}/financial")
async def admin_toggle_financial(profile_id: str, body: FinancialToggleSchema, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    is_paid = body.is_paid
    update = {
        "months_in_arrears": 0 if is_paid else 2,
        "current_status": "AL_DIA" if is_paid else "EN_MORA",
    }
    db.table("student_metadata").update(update).eq("profile_id", profile_id).execute()
    return JSONResponse(content={"message": "Estado actualizado"})


@router.get("/at-risk-students")
async def risk_students() -> JSONResponse:
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
        p = db.table("profiles").select("login_credential, fullname").eq("id", rid).execute()
        if p.data:
            students.append({
                "profile_id": rid,
                "login_credential": p.data[0].get("login_credential"),
                "fullname": p.data[0].get("fullname"),
                "avg_score": round(risk_map[rid] / count_map[rid], 1),
            })
    return JSONResponse(content=students)


# ── Financial Summary ──────────────────────────────────────────────

@router.get("/financial-summary")
async def financial_summary() -> JSONResponse:
    db: Client = next(get_db())

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
    db: Client = next(get_db())
    result = db.table("incident_reports").select("*").order("created_at", desc=True).limit(limit).execute()
    incidents = []
    for inc in result.data:
        student_name = ""
        if inc.get("student_id"):
            p = db.table("profiles").select("fullname").eq("id", inc["student_id"]).execute()
            if p.data:
                student_name = p.data[0].get("fullname", "")
        exam_title = ""
        if inc.get("exam_id"):
            e = db.table("exams").select("title").eq("id", inc["exam_id"]).execute()
            if e.data:
                exam_title = e.data[0].get("title", "")

        incident_type = inc.get("incident_type", "unknown")
        status_map = {
            "network_loss": "Interrumpido por Red — Progreso a Salvo",
            "power_loss": "Interrumpido por Fluido Eléctrico — Progreso a Salvo",
            "suspicious": "Comportamiento Anómalo Detectado",
            "tab_switch": "Cambio de Ventana Registrado",
        }
        status = status_map.get(incident_type, f"Incidente: {incident_type}")

        incidents.append({
            "id": inc.get("id"),
            "student_id": inc.get("student_id"),
            "student_name": student_name,
            "exam_id": inc.get("exam_id"),
            "exam_title": exam_title,
            "incident_type": incident_type,
            "status": status,
            "severity": inc.get("severity", "low"),
            "description": inc.get("description", ""),
            "created_at": str(inc.get("created_at", "")),
        })
    return JSONResponse(content=incidents)


# ── ABP Project Linker ─────────────────────────────────────────────

@router.get("/abp-projects")
async def list_abp_projects() -> JSONResponse:
    db: Client = next(get_db())
    try:
        result = db.table("abp_projects").select("*").order("created_at", desc=True).execute()
    except Exception as exc:
        logger.warning("abp_projects table not accessible: %s", exc)
        return JSONResponse(content=[])
    projects = []
    for p in result.data:
        subjects_raw = p.get("linked_subject_ids") or []
        subject_names = []
        for sid in subjects_raw:
            s = db.table("subjects").select("name").eq("id", sid).execute()
            if s.data:
                subject_names.append(s.data[0].get("name", sid))
        projects.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "description": p.get("description", ""),
            "linked_subject_ids": subjects_raw,
            "linked_subject_names": subject_names,
            "is_active": p.get("is_active", True),
            "project_trigger_keyword": p.get("project_trigger_keyword", "abp"),
            "created_at": str(p.get("created_at", "")),
        })
    return JSONResponse(content=projects)


@router.post("/abp-projects", status_code=201)
async def create_abp_project(data: AbpProjectCreate, user_id: str = Depends(admin_dependency)) -> JSONResponse:
    db: Client = next(get_db())
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
    db: Client = next(get_db())
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
    db: Client = next(get_db())
    result = db.table("abp_projects").delete().eq("id", project_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Proyecto ABP no encontrado")
    return JSONResponse(content={"message": "Proyecto ABP eliminado"})


# ── Digital Materials Processed ──────────────────────────────────

@router.get("/materials-count")
async def materials_count() -> JSONResponse:
    db: Client = next(get_db())
    try:
        result = db.table("class_materials").select("*", count="exact").execute()
        total = result.count or 0
        by_type = {}
        for r in (result.data or []):
            ft = r.get("file_type", "unknown")
            by_type[ft] = by_type.get(ft, 0) + 1
    except Exception:
        total = 0
        by_type = {}
    return JSONResponse(content={"total": total, "by_type": by_type})


# ── Global Skill Thermometer ────────────────────────────────────

@router.get("/skill-thermometer")
async def skill_thermometer() -> JSONResponse:
    db: Client = next(get_db())
    try:
        results = db.table("exam_results").select("score").execute()
        scores = [float(r.get("score", 0)) for r in results.data] if results.data else []
    except Exception:
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
    db: Client = next(get_db())
    profiles = db.table("profiles").select("id, fullname, login_credential, role, is_active").execute()
    items = profiles.data or []
    if search:
        q = search.lower()
        items = [
            p for p in items
            if q in (p.get("fullname") or "").lower()
            or q in (p.get("login_credential") or "").lower()
        ]
    for p in items:
        meta = db.table("student_metadata").select("current_status").eq("profile_id", p["id"]).execute()
        p["grade"] = (meta.data[0] or {}).get("current_status", "") if meta.data else ""
    return JSONResponse(content=items)


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, user_id: str = Depends(admin_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    profile = db.table("profiles").select("id, fullname, login_credential").eq("id", data.profile_id).execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    temp_pass = _generate_temp_password()
    hashed = bcrypt.hashpw(temp_pass.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    db.table("profiles").update({"password_hash": hashed}).eq("id", data.profile_id).execute()

    logger.info("password reset profile=%s by admin=%s", data.profile_id, user_id)
    return JSONResponse(content={
        "status": "reset",
        "temporary_password": temp_pass,
        "profile_id": data.profile_id,
        "fullname": profile.data[0].get("fullname", ""),
        "login_credential": profile.data[0].get("login_credential", ""),
    })
