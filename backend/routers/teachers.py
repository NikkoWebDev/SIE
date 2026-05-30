from __future__ import annotations

import io
import json
import logging
import os
import secrets
import string
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
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
async def submit_grade(submission: GradeSubmission, user_id: str = Depends(auth_dependency)) -> JSONResponse:
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
            logger.error("pdf extraction error: %s", exc)
            raise HTTPException(status_code=400, detail="No se pudo extraer texto del PDF")
    elif ext in ("docx", "doc"):
        try:
            import docx
            buf = io.BytesIO(content)
            doc = docx.Document(buf)
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as exc:
            logger.error("docx extraction error: %s", exc)
            raise HTTPException(status_code=400, detail="No se pudo extraer texto del documento Word")
    else:
        return content.decode("utf-8", errors="replace")


@router.post("/upload-material", status_code=201)
async def upload_material(
    file: UploadFile = File(...),
    subject_id: str = Form(...),
    grade_id: str = Form(...),
    user_id: str = Depends(teacher_dependency),
) -> JSONResponse:
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    raw_text = _extract_text_from_bytes(raw, file.filename or "document.pdf")
    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="No se pudo extraer texto del archivo")

    api_key = os.getenv("OPENROUTER_TEACHER_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_TEACHER_KEY no configurada")

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

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=md_payload,
                headers=headers,
            )
        if resp.status_code != 200:
            logger.error("OpenRouter MD compress error: status=%s body=%s", resp.status_code, resp.text[:300])
            raise HTTPException(status_code=502, detail="Error del asistente de compresión")
        body = resp.json()
        choices = body.get("choices", [])
        if not choices:
            raise HTTPException(status_code=502, detail="Respuesta vacía del asistente")
        md_text = choices[0].get("message", {}).get("content", "").strip()
        if not md_text:
            raise HTTPException(status_code=502, detail="Markdown vacío del asistente")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="El asistente de compresión no respondió a tiempo")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("md compression unexpected error: %s", exc)
        raise HTTPException(status_code=500, detail="Error interno de compresión")

    try:
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", ""),
            api_key="oza3Ptw6-d_bQyDeZjBjZYhGglU",
            api_secret=os.getenv("CLOUDINARY_API_SECRET", ""),
        )
        safe_name = (file.filename or "material").rsplit(".", 1)[0][:40]
        upload_result = cloudinary.uploader.upload(
            md_text.encode("utf-8"),
            folder=CLOUDINARY_MD_FOLDER,
            public_id=f"{safe_name}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            resource_type="raw",
        )
        file_url = upload_result.get("secure_url", "")
        if not file_url:
            raise HTTPException(status_code=500, detail="Error al obtener URL de Cloudinary")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("cloudinary md upload error: %s", exc)
        raise HTTPException(status_code=500, detail="Error al subir el material a la nube")

    db: Client = next(get_db())
    doc = {
        "subject_id": subject_id,
        "grade_id": grade_id,
        "file_url": file_url,
        "file_type": "md",
        "uploaded_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        result = db.table("class_materials").insert(doc).execute()
        record_id = result.data[0]["id"]
    except Exception as exc:
        logger.error("class_materials insert error: %s", exc)
        raise HTTPException(status_code=500, detail="Error al guardar el registro del material")

    logger.info("material uploaded id=%s subject=%s grade=%s url=%s", record_id, subject_id, grade_id, file_url)
    return JSONResponse(status_code=201, content={
        "id": record_id,
        "url": file_url,
        "subject_id": subject_id,
        "grade_id": grade_id,
        "status": "material_processed",
    })


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
