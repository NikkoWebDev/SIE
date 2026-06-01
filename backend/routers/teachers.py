from __future__ import annotations

import io
import json
import logging
import os
import secrets
import string
import traceback
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from supabase import Client

from config.database import get_db
from config.settings import ABP_PROPAGATED_SUBJECTS
from dependencies import auth_dependency, teacher_dependency
from managers import ws_manager
from models import GradeSubmission

logger = logging.getLogger("siee.teachers")
router = APIRouter(prefix="/api/teacher", tags=["teachers"])

# ── Upload progress tracker (FASE 6.2) ──
_upload_tasks: dict[str, dict[str, Any]] = {}
_UPLOAD_CLEANUP_SECONDS = 300


def _set_upload_progress(task_id: str, stage: str, pct: int, detail: str = "", extra: dict | None = None) -> None:
    _upload_tasks[task_id] = {
        "stage": stage,
        "progress_pct": pct,
        "detail": detail,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        _upload_tasks[task_id].update(extra)


def _resolve_student_uuid(db: Client, credential: str) -> str:
    result = db.table("profiles").select("id").eq("login_credential", credential).execute()
    if result.data:
        return result.data[0]["id"]
    p = db.table("profiles").select("id").eq("id", credential).execute()
    if p.data:
        return p.data[0]["id"]
    raise HTTPException(status_code=404, detail="Estudiante no encontrado")


def _resolve_subject_uuid(db: Client, name_or_id: str) -> str:
    result = db.table("subjects").select("id").eq("name", name_or_id).execute()
    if result.data:
        return result.data[0]["id"]
    s = db.table("subjects").select("id").eq("id", name_or_id).execute()
    if s.data:
        return s.data[0]["id"]
    raise HTTPException(status_code=404, detail="Asignatura no encontrada")


def _propagate_abp_grade(
    db: Client,
    student_uuid: str,
    original_subject_name: str,
    project_id: str,
    score: float,
    teacher_id: str,
    course_id: str,
) -> list[str]:
    propagated: list[str] = []
    normalized = project_id.strip().lower()
    if "abp" not in normalized and "proyecto" not in normalized:
        return propagated

    now = datetime.now(timezone.utc).isoformat()
    for target_name in ABP_PROPAGATED_SUBJECTS:
        if target_name == original_subject_name.strip():
            continue
        target = db.table("subjects").select("id").eq("name", target_name).execute()
        if not target.data:
            continue
        target_id = target.data[0]["id"]
        doc = {
            "student_id": student_uuid,
            "subject_id": target_id,
            "project_id": project_id,
            "score": score,
            "observations": f"[ABP Propagado] Nota integrada desde proyecto: {project_id}",
            "created_at": now,
            "teacher_id": teacher_id,
            "course_id": course_id,
        }
        existing = db.table("grades").select("*").eq("student_id", student_uuid).eq("subject_id", target_id).eq("project_id", project_id).execute()
        if existing.data:
            db.table("grades").update(doc).eq("id", existing.data[0]["id"]).execute()
        else:
            db.table("grades").insert(doc).execute()
        propagated.append(target_name)
    return propagated


@router.post("/submit-grade", status_code=201)
async def submit_grade(submission: GradeSubmission, user_id: str = Depends(teacher_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    now = datetime.now(timezone.utc).isoformat()

    try:
        student_uuid = _resolve_student_uuid(db, submission.student_id)
        subject_uuid = _resolve_subject_uuid(db, submission.subject_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("resolve error student=%s subject=%s: %s", submission.student_id, submission.subject_id, e)
        raise HTTPException(status_code=400, detail="Estudiante o asignatura no válidos")

    original_subject_name = submission.subject_id

    doc = {
        "student_id": student_uuid,
        "teacher_id": submission.teacher_id,
        "course_id": submission.course_id,
        "project_id": submission.project_id,
        "subject_id": subject_uuid,
        "score": submission.score,
        "observations": submission.observations,
        "created_at": now,
    }

    existing = db.table("grades").select("*").eq("student_id", student_uuid).eq("subject_id", subject_uuid).eq("project_id", submission.project_id).execute()
    if existing.data:
        db.table("grades").update(doc).eq("id", existing.data[0]["id"]).execute()
        grade_id = existing.data[0]["id"]
    else:
        result = db.table("grades").insert(doc).execute()
        grade_id = result.data[0]["id"]

    propagated = _propagate_abp_grade(
        db, student_uuid, original_subject_name,
        submission.project_id, submission.score,
        submission.teacher_id, submission.course_id,
    )
    logger.info("grade=%s student=%s score=%.1f propagated=%s", grade_id, student_uuid, submission.score, propagated)

    is_abp_subject = submission.subject_id.strip().lower()
    propagation_note = ""
    if any(k in is_abp_subject for k in ("abp", "proyecto", "investigación", "matemáticas", "ciencias", "lenguaje", "inglés", "sociales", "tecnología", "arte", "música")):
        propagation_note = f"Nota propagada automáticamente a las {len(propagated) + 1} materias vinculadas"
        if propagated:
            subject_ids = []
            for name in propagated:
                sid = db.table("subjects").select("id").eq("name", name).execute()
                if sid.data:
                    subject_ids.append(sid.data[0]["id"])
            db.table("propagation_log").insert({
                "grade_id": grade_id,
                "original_subject_id": subject_uuid,
                "student_id": student_uuid,
                "teacher_id": submission.teacher_id,
                "score": submission.score,
                "propagated_subjects": subject_ids,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }).execute()

    if submission.score < 3.5:
        profile = db.table("profiles").select("fullname").eq("id", student_uuid).execute()
        student_name = profile.data[0].get("fullname", "") if profile.data else ""
        risk_doc = {
            "student_id": student_uuid,
            "alert_type": "academic_risk",
            "severity": "high" if submission.score < 2.5 else "medium",
            "avg_score": submission.score,
            "reason": f"Nota baja ({submission.score}) en {original_subject_name}",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        db.table("risk_alerts").insert(risk_doc).execute()
        await ws_manager.broadcast({
            "type": "RISK_ALERT",
            "student_id": student_uuid,
            "student_name": student_name,
            "avg_score": submission.score,
            "subject": original_subject_name,
            "severity": risk_doc["severity"],
        })

    return JSONResponse(status_code=201, content={
        "grade_id": grade_id,
        "status": "accepted",
        "abp_propagated": propagated,
        "propagation_count": len(propagated),
        "propagation_note": propagation_note,
    })


# ── AI Behavior Helper ───────────────────────────────────────────

class BehaviorHelperRequest(BaseModel):
    notes: str = Field(..., min_length=1, max_length=2000)
    student_name: str = Field(default="", max_length=200)


SYSTEM_PROMPT_BEHAVIOR = (
    "Eres el Asistente de Redacción Docente de VYNTRA para el Colegio Ciudad del Sol de Sogamoso. "
    "Ayudas al profesor a redactar reportes de comportamiento u observaciones académicas "
    "para el Observador del Estudiante. Transforma notas rápidas del profesor en textos "
    "formales, pedagógicos, constructivos y libres de jerga técnica. "
    "Debes devolver únicamente el texto de la observación redactada, sin prefijos, "
    "sin explicaciones adicionales, sin comillas. Máximo 500 caracteres."
)


@router.post("/ai-behavior-helper")
async def ai_behavior_helper(data: BehaviorHelperRequest, user_id: str = Depends(teacher_dependency)) -> JSONResponse:
    api_key = os.getenv("OPENROUTER_TEACHER_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_TEACHER_KEY no configurada")

    model = os.getenv("OPENROUTER_MODEL", "openrouter/free")

    user_message = f"Notas del profesor sobre {data.student_name or 'el estudiante'}: {data.notes}" if data.student_name else f"Notas del profesor: {data.notes}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT_BEHAVIOR},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": 600,
        "temperature": 0.4,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://colegiociudaddelsol.edu.co",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=payload,
                headers=headers,
            )
        if resp.status_code != 200:
            error_text = resp.text[:300]
            logger.error("OpenRouter behavior helper error: status=%s body=%s", resp.status_code, error_text)
            raise HTTPException(status_code=502, detail="Error del asistente de redacción")

        body = resp.json()
        choices = body.get("choices", [])
        if not choices:
            raise HTTPException(status_code=502, detail="No se recibió respuesta del asistente")

        optimized_text = choices[0].get("message", {}).get("content", "").strip()
        if not optimized_text:
            raise HTTPException(status_code=502, detail="Respuesta vacía del asistente")

        return JSONResponse(content={
            "optimized": optimized_text,
            "original": data.notes,
        })
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="El asistente de redacción no respondió a tiempo")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("behavior helper unexpected error: %s", e)
        raise HTTPException(status_code=500, detail="Error interno del asistente")


# ── Exam Reactivation ────────────────────────────────────────────

class ReactivateExamRequest(BaseModel):
    student_id: str = Field(..., min_length=1)
    exam_id: str = Field(..., min_length=1)


@router.post("/reactivate-exam")
async def reactivate_exam(data: ReactivateExamRequest, user_id: str = Depends(teacher_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    now = datetime.now(timezone.utc).isoformat()

    existing = db.table("exam_progress").select("*").eq("student_id", data.student_id).eq("exam_id", data.exam_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Progreso de examen no encontrado")

    db.table("exam_progress").update({
        "interrupted": False,
        "resumed_at": now,
        "last_saved_at": now,
    }).eq("id", existing.data[0]["id"]).execute()

    logger.info("exam reactivated student=%s exam=%s by teacher=%s", data.student_id, data.exam_id, user_id)
    return JSONResponse(content={
        "status": "reactivated",
        "message": "Examen reactivado — el estudiante puede continuar desde donde quedó",
        "resumed_at": now,
    })


# ── File Ingestion & Cloudinary MD Pipeline ─────────────────────

CLOUDINARY_MD_FOLDER = "class_materials"

SYSTEM_PROMPT_MD_COMPRESS = (
    "Eres un asistente que transforma contenido educativo extenso "
    "(extraído de PDF o Word) en un resumen Markdown estructurado, "
    "conciso y pedagógico. Debes mantener los conceptos clave, "
    "definiciones, fórmulas y fechas importantes. "
    "Usa títulos (##), listas (-), negritas (**) y tablas si aplica. "
    "Máximo 2000 caracteres. Devuelve solo el Markdown, sin explicaciones adicionales."
)


def _extract_text_from_bytes(content: bytes, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "pdf":
        try:
            import fitz
            doc = fitz.open(stream=content, filetype="pdf")
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            return text
        except Exception as exc:
            logger.error("pdf extraction error: %s\n%s", exc, traceback.format_exc())
            raise HTTPException(status_code=400, detail="No se pudo extraer texto del PDF")
    elif ext in ("docx", "doc"):
        try:
            import docx
            buf = io.BytesIO(content)
            doc = docx.Document(buf)
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as exc:
            logger.error("docx extraction error: %s\n%s", exc, traceback.format_exc())
            raise HTTPException(status_code=400, detail="No se pudo extraer texto del documento Word")
    else:
        return content.decode("utf-8", errors="replace")


@router.post("/upload-material", status_code=202)
async def upload_material(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    subject_id: Optional[str] = Form(None),
    grade_id: Optional[str] = Form(None),
    user_id: str = Depends(teacher_dependency),
) -> JSONResponse:
    print(f"[INPUT TRACE] Filename: {file.filename}, Content-Type: {file.content_type}")
    print(f"[INPUT TRACE] subject_id: {subject_id}, grade_id: {grade_id}")
    if not subject_id or not grade_id:
        raise HTTPException(status_code=400, detail="Faltan parámetros críticos: subject_id o grade_id vacíos.")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    task_id = secrets.token_hex(12)
    filename = file.filename or "document.pdf"
    _set_upload_progress(task_id, "queued", 0, "En cola...")
    background_tasks.add_task(_process_material_upload, task_id, raw, filename, subject_id, grade_id, user_id)
    return JSONResponse(status_code=202, content={"task_id": task_id, "status": "processing"})


@router.get("/upload-material-status/{task_id}")
async def get_upload_material_status(task_id: str, user_id: str = Depends(teacher_dependency)) -> JSONResponse:
    status = _upload_tasks.get(task_id)
    if not status:
        return JSONResponse(content={"status": "not_found"})
    return JSONResponse(content=status)


async def _process_material_upload(task_id: str, raw: bytes, filename: str, subject_id: str, grade_id: str, user_id: str) -> None:
    try:
        _set_upload_progress(task_id, "extracting", 15, "Extrayendo texto del archivo...")
        raw_text = _extract_text_from_bytes(raw, filename)
        if not raw_text.strip():
            _set_upload_progress(task_id, "error", 0, "No se pudo extraer texto del archivo")
            return

        api_key = os.getenv("OPENROUTER_TEACHER_KEY")
        if not api_key:
            _set_upload_progress(task_id, "error", 0, "OPENROUTER_TEACHER_KEY no configurada")
            return

        md_payload = {
            "model": "google/gemini-2.5-flash",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_MD_COMPRESS},
                {"role": "user", "content": f"Texto extraído:\n\n{raw_text[:15000]}"},
            ],
            "max_tokens": 2000,
            "temperature": 0.3,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://colegiociudaddelsol.edu.co",
        }

        _set_upload_progress(task_id, "compressing", 40, "Comprimiendo con IA...")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=md_payload,
                    headers=headers,
                )
            if resp.status_code != 200:
                _set_upload_progress(task_id, "error", 0, f"Error del asistente: {resp.status_code}")
                logger.error("OpenRouter MD compress error: status=%s", resp.status_code)
                return
            body = resp.json()
            choices = body.get("choices", [])
            if not choices:
                _set_upload_progress(task_id, "error", 0, "Respuesta vacía del asistente")
                return
            md_text = choices[0].get("message", {}).get("content", "").strip()
            if not md_text:
                _set_upload_progress(task_id, "error", 0, "Markdown vacío del asistente")
                return
        except httpx.TimeoutException:
            _set_upload_progress(task_id, "error", 0, "El asistente no respondió a tiempo")
            return

        _set_upload_progress(task_id, "uploading", 70, "Subiendo a Cloudinary...")
        try:
            import cloudinary
            import cloudinary.uploader
            cname = os.getenv("CLOUDINARY_CLOUD_NAME", "")
            ckey = os.getenv("CLOUDINARY_API_KEY", "")
            csec = os.getenv("CLOUDINARY_API_SECRET", "")
            if not cname or not ckey or not csec:
                _set_upload_progress(task_id, "error", 0, "Cloudinary no configurado (faltan credenciales)")
                return
            cloudinary.config(cloud_name=cname, api_key=ckey, api_secret=csec)
            safe_name = filename.rsplit(".", 1)[0][:40]
            upload_result = cloudinary.uploader.upload(
                md_text.encode("utf-8"),
                folder=CLOUDINARY_MD_FOLDER,
                public_id=f"{safe_name}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                resource_type="raw",
            )
            file_url = upload_result.get("secure_url", "")
            if not file_url:
                _set_upload_progress(task_id, "error", 0, "Error al obtener URL de Cloudinary")
                return
        except Exception as exc:
            logger.error("cloudinary md upload error: %s", exc)
            _set_upload_progress(task_id, "error", 0, "Error al subir el material a la nube")
            return

        _set_upload_progress(task_id, "saving", 90, "Guardando registro...")
        db: Client = next(get_db())
        doc = {
            "subject_id": subject_id,
            "grade_id": grade_id,
            "file_url": file_url,
            "file_type": "md",
            "uploaded_by": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = db.table("class_materials").insert(doc).execute()
        record_id = result.data[0]["id"]
        logger.info("material uploaded id=%s subject=%s grade=%s url=%s", record_id, subject_id, grade_id, file_url)
        _set_upload_progress(task_id, "complete", 100, "Material procesado exitosamente", extra={"file_url": file_url, "material_id": record_id})
    except Exception as exc:
        logger.error("upload task error: %s", exc)
        _set_upload_progress(task_id, "error", 0, f"Error interno: {exc}")


# ── Skill Badges (heat map for teacher dashboard) ───────────────

@router.get("/skill-badges")
async def get_skill_badges(user_id: str = Depends(teacher_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    results = db.table("exam_results").select("student_id, score, created_at, subject_id").execute()
    if not results.data:
        return JSONResponse(content=[])

    badges: dict[str, dict[str, Any]] = {}
    for r in results.data:
        sid = r.get("student_id")
        if not sid:
            continue
        score = float(r.get("score", 0))
        if score >= 4.0:
            badge = "Oro"
        elif score >= 3.0:
            badge = "Plata"
        else:
            badge = "Bronce"
        if sid not in badges:
            p = db.table("profiles").select("fullname, login_credential").eq("id", sid).execute()
            name = p.data[0]["fullname"] if p.data else sid
            badges[sid] = {"student_id": sid, "fullname": name, "badges": []}
        badges[sid]["badges"].append({
            "subject_id": r.get("subject_id", ""),
            "score": score,
            "badge": badge,
            "date": str(r.get("created_at", "")),
        })

    return JSONResponse(content=list(badges.values()))


# ── Planilla: batch grades for a subject+cours ────────────────

@router.get("/teacher/planilla-grades")
async def get_planilla_grades(
    subject: str = Query(...),
    course: str = Query(...),
    user_id: str = Depends(auth_dependency),
) -> JSONResponse:
    db: Client = next(get_db())
    subject_obj = db.table("subjects").select("id").eq("name", subject).execute()
    if not subject_obj.data:
        return JSONResponse(content=[])
    subject_id = subject_obj.data[0]["id"]
    grades = db.table("grades").select("*").eq("subject_id", subject_id).eq("course_id", course).execute()
    result: dict[str, dict[str, Any]] = {}
    for g in grades.data:
        sid = g.get("student_id", "")
        if sid not in result:
            result[sid] = {"student_id": sid, "periods": {}}
        period = g.get("period", "P1")
        result[sid]["periods"][period] = {
            "score": float(g.get("score", 0)),
            "observations": g.get("observations", ""),
            "grade_id": g.get("id"),
        }
    return JSONResponse(content=list(result.values()))


# ── Teacher's Subjects (legacy compatible) ──────────────────────

@router.get("/teacher/my-subjects/{teacher_id}")
async def get_teacher_subjects(teacher_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    teacher = db.table("profiles").select("id").eq("login_credential", teacher_id).execute()
    if not teacher.data:
        return JSONResponse(content=[])
    tid = teacher.data[0]["id"]
    assignments = db.table("teacher_assignments").select("*, subjects(id, name, grade, is_abp)").eq("teacher_id", tid).execute()
    subjects = []
    for a in assignments.data:
        s = a.get("subjects", {})
        subjects.append({
            "_id": s.get("id", ""),
            "name": s.get("name", ""),
            "grade": s.get("grade", a.get("grade", "")),
            "subject_name": s.get("name", ""),
            "grado": s.get("grade", a.get("grade", "")),
            "is_abp": s.get("is_abp", False),
        })
    return JSONResponse(content=subjects)


# ── Teacher Guide Upload (legacy compatible) ───────────────────

@router.post("/teacher/guides", status_code=201)
async def upload_guide_v2(
    title: str = Form(...),
    subject_name: str = Form(...),
    grade: str = Form(...),
    teacher_id: str = Form(...),
    file: UploadFile = File(...),
    user_id: str = Depends(auth_dependency),
) -> JSONResponse:
    try:
        import cloudinary
        import cloudinary.uploader
        result = cloudinary.uploader.upload(file.file, folder="guias", resource_type="auto")
        url = result.get("secure_url")
    except Exception as exc:
        logger.error("cloudinary guide upload failed: %s", exc)
        raise HTTPException(status_code=500, detail="Error al subir el archivo")

    db: Client = next(get_db())
    db.table("guides").insert({
        "title": title,
        "subject": subject_name,
        "grade": grade,
        "teacher_id": teacher_id,
        "filename": file.filename or "guide.pdf",
        "url": url,
    }).execute()
    return JSONResponse(content={"message": "Guía publicada"}, status_code=201)


@router.get("/teacher/guides/{teacher_id}")
async def list_teacher_guides(teacher_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("guides").select("*").eq("teacher_id", teacher_id).order("created_at", desc=True).execute()
    guides = []
    for g in result.data:
        guides.append({
            "_id": g.get("id"),
            "title": g.get("title", g.get("filename", "Guía")),
            "subject": g.get("subject", ""),
            "subject_name": g.get("subject", ""),
            "grade": g.get("grade", ""),
            "url": g.get("url", ""),
            "created_at": str(g.get("created_at", "")),
        })
    return JSONResponse(content=guides)


# ── Teacher's Exams (legacy compatible) ────────────────────────

@router.get("/teacher/my-exams/{teacher_id}")
async def get_teacher_exams(teacher_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("exams").select("*").eq("teacher_id", teacher_id).order("created_at", desc=True).execute()
    exams = []
    for e in result.data:
        exams.append({
            "_id": e.get("id"),
            "title": e.get("title", ""),
            "grade": e.get("grade", ""),
            "subject": e.get("subject", ""),
            "duration": e.get("duration", 60),
            "is_active": e.get("is_active", True),
            "created_at": str(e.get("created_at", "")),
        })
    return JSONResponse(content=exams)


# ── Delete teacher resources ──────────────────────────────────

@router.delete("/teacher/guides/{guide_id}")
async def delete_guide(guide_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("guides").delete().eq("id", guide_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Guía no encontrada")
    return JSONResponse(content={"message": "Guía eliminada"})


@router.delete("/teacher/deliveries/{delivery_id}")
async def delete_delivery(delivery_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("deliveries").delete().eq("id", delivery_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Entrega no encontrada")
    return JSONResponse(content={"message": "Entrega eliminada"})


@router.delete("/teacher/exams/{exam_id}")
async def delete_exam(exam_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    db.table("exam_results").delete().eq("exam_id", exam_id).execute()
    result = db.table("exams").delete().eq("id", exam_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Examen no encontrado")
    return JSONResponse(content={"message": "Examen eliminado"})


# ── Reset exam attempt (legacy compatible) ─────────────────────

@router.delete("/teacher/reset-attempt/{student_id}/{exam_id}")
async def reset_exam_attempt(student_id: str, exam_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    db.table("exam_progress").delete().eq("student_id", student_id).eq("exam_id", exam_id).execute()
    return JSONResponse(content={"message": "Intento reseteado"})


# ── Exam incidents by teacher (legacy compatible) ──────────────

@router.get("/teacher/exam-incidents/{teacher_id}")
async def get_teacher_exam_incidents(teacher_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    teacher = db.table("profiles").select("id").eq("login_credential", teacher_id).execute()
    if not teacher.data:
        return JSONResponse(content=[])
    tid = teacher.data[0]["id"]
    teacher_exams = db.table("exams").select("id").eq("teacher_id", teacher_id).execute()
    exam_ids = [e["id"] for e in teacher_exams.data]
    if not exam_ids:
        incidents_list = db.table("incident_reports").select("*").order("created_at", desc=True).limit(50).execute()
    else:
        incidents_list = db.table("incident_reports").select("*").in_("exam_id", exam_ids).order("created_at", desc=True).limit(50).execute()
    formatted = []
    for inc in incidents_list.data:
        student_name = ""
        if inc.get("student_id"):
            p = db.table("profiles").select("fullname").eq("id", inc["student_id"]).execute()
            if p.data:
                student_name = p.data[0].get("fullname", "")
        formatted.append({
            "_id": inc.get("id"),
            "student_id": inc.get("student_id", ""),
            "student_name": student_name,
            "exam_id": inc.get("exam_id", ""),
            "strikes": inc.get("strikes", 1),
            "reason": inc.get("description", inc.get("incident_type", "Desconocido")),
            "created_at": str(inc.get("created_at", "")),
        })
    return JSONResponse(content=formatted)
