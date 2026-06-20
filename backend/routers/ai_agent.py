from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from supabase import Client

from config.database import get_db
from dependencies import admin_dependency, auth_dependency, teacher_dependency
from routers.guardrails import guardrails
from routers.cache import CACHEABLE_TOOLS, tool_cache
from routers.ai_search import search_materials as _tool_search_materials

logger = logging.getLogger("siee.ai_agent")
router = APIRouter(prefix="/api/ai", tags=["ai"])

OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"
REFERER_URL = "https://colegiociudaddelsol.edu.co"
MAX_HISTORY = 20
RATE_LIMIT_PER_MINUTE = 15
CONTEXT_CACHE_TTL = 300  # seconds: reuse user context within a session
REACT_MAX_ITERATIONS = 5
TOOL_RESULT_MAX_CHARS = 2000
TOKEN_BUDGET_MAX = 12000
RETRY_MAX_ATTEMPTS = 2
RETRY_BASE_DELAY = 1.0

CIRCUIT_BREAKER_MAX_ERRORS = 3
ITERATION_TIMEOUT_SECONDS = 45

DEFAULT_MODEL = "openrouter/free"
FALLBACK_MODEL = "openrouter/auto"

GROQ_BASE = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_FALLBACK_MODEL = "qwen/qwen3-32b"

SCHOOL_CONTEXT = """Institución: Colegio Técnico Ciudad del Sol (Sogamoso, Boyacá, Colombia)
Metodología: Aprendizaje Basado en Proyectos (ABP) con 9 materias vinculadas
Escala: 0.0 - 5.0. Mínimo aprobación: 3.5
Estados: >=4.0 Sobresaliente (#00FF66), 3.5-4.0 Aceptable (#FFE600), <3.5 En Riesgo (#FF0055)
Mora: >=2 meses bloquea descargas PDF (excepto con override de rectoría)
Plataforma: VYNTRA Academic / Solaris"""

SYSTEM_PROMPTS: dict[str, str] = {
    "student": (
        f"Eres el TUTOR VYNTRA, asistente académico empático del Colegio Ciudad del Sol.\n\n"
        f"Contexto institucional:\n{SCHOOL_CONTEXT}\n\n"
        "INSTRUCCIONES:\n"
        "- Responde en español, tono motivador, claro y cercano.\n"
        "- Usa lenguaje sencillo — el estudiante puede tener 12-17 años.\n"
        "- Cuando te den contexto del estudiante (nombre, notas, materias), úsalo activamente para personalizar tu respuesta.\n"
        "- NUNCA preguntes al estudiante su nombre, curso, notas o cualquier información que YA esté en el contexto proporcionado.\n"
        "- Ofrece consejos de estudio, explicaciones de materias ABP, ayuda con tareas.\n"
        "- Si el estudiante está en riesgo académico, motívalo y sugiere estrategias.\n"
        "- NUNCA inventes notas o datos académicos — solo usa la información proporcionada.\n"
        "- Sé breve y directo en tus respuestas. Si es un saludo, saluda cordialmente y ofrece ayuda."
    ),
    "teacher": (
        f"Eres el ASISTENTE DOCENTE VYNTRA, analista pedagógico del Colegio Ciudad del Sol.\n\n"
        f"Contexto institucional:\n{SCHOOL_CONTEXT}\n\n"
        "INSTRUCCIONES:\n"
        "- Responde en español, tono profesional y analítico.\n"
        "- Ayuda a interpretar rendimiento de estudiantes, generar alertas tempranas.\n"
        "- Sugiere estrategias pedagógicas basadas en datos.\n"
        "- Identifica patrones de riesgo y propone intervenciones.\n"
        "- Usa los datos de contexto (calificaciones, estudiantes en riesgo) en tus análisis.\n"
        "- NO preguntes por información que ya está en el contexto (tu nombre, materias, etc).\n"
        "- Sé concreto: da números, porcentajes y recomendaciones accionables."
    ),
    "admin": (
        f"Eres el ASISTENTE ADMINISTRATIVO VYNTRA, asesor ejecutivo del Colegio Ciudad del Sol.\n\n"
        f"Contexto institucional:\n{SCHOOL_CONTEXT}\n\n"
        "INSTRUCCIONES:\n"
        "- Responde en español, tono formal, ejecutivo y orientado a resultados.\n"
        "- Proporciona análisis numéricos claros de situación financiera.\n"
        "- Ofrece recomendaciones estratégicas sobre morosidad, cobertura de pagos.\n"
        "- Usa los datos de contexto (estadísticas, estudiantes en mora) en tu análisis.\n"
        "- NO preguntes por información que ya está en el contexto.\n"
        "- Ayuda a identificar tendencias y tomar decisiones basadas en datos."
    ),
}

ENV_KEY_MAP: dict[str, str] = {
    "student": "OPENROUTER_STUDENT_KEY",
    "teacher": "OPENROUTER_TEACHER_KEY",
    "admin": "OPENROUTER_ADMIN_KEY",
}

ROLE_CONFIG: dict[str, dict[str, Any]] = {
    "student": {"max_tokens": 1024, "temperature": 0.7},
    "teacher": {"max_tokens": 2048, "temperature": 0.6},
    "admin": {"max_tokens": 2048, "temperature": 0.5},
}

ROLE_ENDPOINT: dict[str, str] = {
    "student": "/api/ai/student-tutor",
    "teacher": "/api/ai/teacher-tutor",
    "admin": "/api/ai/admin-assistant",
}


class ChatRequest(BaseModel):
    message: str = Field(default="", max_length=4000)
    context: str = Field(default="", max_length=8000)
    thread_id: str | None = Field(default=None, max_length=64)
    section: str = Field(default="")

    @model_validator(mode="after")
    def ensure_message(self) -> "ChatRequest":
        if not self.message or not self.message.strip():
            self.message = "Consulta académica general"
        return self


# In-memory conversation cache (DB is primary storage, cache reduces latency)
# All four module-level dicts below are mutated by sync helpers that FastAPI
# may run in a threadpool. _state_lock guards every compound read-modify-write.
_state_lock = threading.Lock()
_conversation_cache: dict[str, list[dict[str, str]]] = {}
_user_context_cache: dict[str, tuple[str, float]] = {}
CONVERSATION_CACHE_MAX = 100

rate_limit_store: dict[str, list[float]] = {}
tool_usage_counters: dict[str, dict[str, int]] = {}


def _check_rate_limit(user_id: str) -> None:
    now = time.time()
    window = 60.0
    with _state_lock:
        if user_id not in rate_limit_store:
            rate_limit_store[user_id] = []
        rate_limit_store[user_id] = [t for t in rate_limit_store[user_id] if now - t < window]
        if len(rate_limit_store[user_id]) >= RATE_LIMIT_PER_MINUTE:
            raise HTTPException(status_code=429, detail="Demasiadas solicitudes. Espera un momento antes de continuar.")
        rate_limit_store[user_id].append(now)


def _get_api_key(role: str) -> str:
    key = os.getenv(ENV_KEY_MAP[role])
    if not key:
        raise HTTPException(status_code=500, detail=f"OPENROUTER_{role.upper()}_KEY no configurada en el servidor")
    return key


def _get_db() -> Client:
    return next(get_db())


def _cache_put(role: str, user_id: str, messages: list[dict[str, str]]) -> None:
    """Store conversation in in-memory cache (LRU, max CONVERSATION_CACHE_MAX)."""
    key = f"{role}:{user_id}"
    with _state_lock:
        _conversation_cache[key] = messages
        if len(_conversation_cache) > CONVERSATION_CACHE_MAX:
            oldest = next(iter(_conversation_cache))
            del _conversation_cache[oldest]


def _cache_get(role: str, user_id: str) -> list[dict[str, str]] | None:
    return _conversation_cache.get(f"{role}:{user_id}")


def _cache_evict(role: str, user_id: str) -> None:
    with _state_lock:
        _conversation_cache.pop(f"{role}:{user_id}", None)


def _thread_cache_key(thread_id: str) -> str:
    return f"thread:{thread_id}"


def _load_messages(role: str, user_id: str, thread_id: str | None = None) -> list[dict[str, str]]:
    if thread_id:
        ck = _thread_cache_key(thread_id)
        cached = _conversation_cache.get(ck)
        if cached is not None:
            return cached
        try:
            db = _get_db()
            result = db.table("conversations").select("messages")\
                .eq("id", thread_id).eq("user_id", user_id).execute()
            if result.data:
                msgs = result.data[0].get("messages", [])
                # Strip thread metadata marker (first message with role=system, content=_thread_meta_)
                if msgs and isinstance(msgs[0], dict) and msgs[0].get("content") == "_thread_meta_":
                    msgs = msgs[1:]
                _conversation_cache[ck] = msgs
                return msgs
        except Exception as e:
            logger.debug("thread db load error: %s", e)
        return []
    cached = _cache_get(role, user_id)
    if cached is not None:
        return cached
    try:
        db = _get_db()
        result = db.table("conversations").select("messages")\
            .eq("user_id", user_id).eq("role", role)\
            .order("created_at", desc=True).limit(1).execute()
        if result.data:
            msgs = result.data[0].get("messages", [])
            _cache_put(role, user_id, msgs)
            return msgs
    except Exception as e:
        logger.debug("conversation db load error: %s", e)
    return []


def _save_messages(role: str, user_id: str, messages: list[dict[str, str]], thread_id: str | None = None) -> None:
    if thread_id:
        ck = _thread_cache_key(thread_id)
        _conversation_cache[ck] = messages
        try:
            db = _get_db()
            now = datetime.now(timezone.utc).isoformat()
            # Load existing row to preserve thread metadata marker
            existing = db.table("conversations").select("messages").eq("id", thread_id).eq("user_id", user_id).execute()
            if existing.data:
                existing_msgs = existing.data[0].get("messages", [])
                # If first msg is thread metadata, keep it; otherwise just save messages
                if existing_msgs and isinstance(existing_msgs[0], dict) and existing_msgs[0].get("content") == "_thread_meta_":
                    msgs_to_save = [existing_msgs[0]] + messages
                else:
                    msgs_to_save = messages
                db.table("conversations").update({"messages": msgs_to_save, "updated_at": now})\
                    .eq("id", thread_id).eq("user_id", user_id).execute()
            else:
                db.table("conversations").insert({
                    "id": thread_id, "user_id": user_id, "role": role,
                    "messages": messages, "updated_at": now, "created_at": now
                }).execute()
        except Exception as e:
            logger.warning("thread db save error: %s", e)
        return
    _cache_put(role, user_id, messages)
    try:
        db = _get_db()
        existing = db.table("conversations").select("id")\
            .eq("user_id", user_id).eq("role", role)\
            .order("created_at", desc=True).limit(1).execute()
        now = datetime.now(timezone.utc).isoformat()
        doc = {"user_id": user_id, "role": role, "messages": messages, "updated_at": now}
        if existing.data:
            db.table("conversations").update(doc).eq("id", existing.data[0]["id"]).execute()
        else:
            doc["created_at"] = now
            db.table("conversations").insert(doc).execute()
    except Exception as e:
        logger.warning("conversation db save error: %s", e)


def _estimate_tokens(messages: list[dict[str, str]]) -> int:
    total = 0
    for msg in messages:
        total += len(json.dumps(msg)) // 2
    return total


def _truncate_tool_result(text: str) -> str:
    if len(text) > TOOL_RESULT_MAX_CHARS:
        return text[:TOOL_RESULT_MAX_CHARS] + "\n\n[Resultado truncado — muy extenso]"
    return text


def _sanitize_output(text: str) -> str:
    return html.escape(text)


async def _stream_error(message: str) -> AsyncGenerator[str, None]:
    yield f"data: {json.dumps({'error': message})}\n\n"
    yield "data: [DONE]\n\n"


def _get_available_for_role(role: str) -> list[dict[str, str]]:
    tools = [
        {
            "name": "get_student_grades_summary",
            "description": "Obtiene el promedio general y desglose de materias de un estudiante, incluyendo cuáles están en riesgo académico (<3.5). Útil para generar reportes personalizados de rendimiento.",
            "parameters": {"student_id": {"type": "string", "description": "UUID del estudiante a consultar"}},
        },
        {
            "name": "get_financial_status",
            "description": "Consulta el estado financiero de un estudiante: meses en mora, si tiene bloqueo por mora (>=2 meses), si hay override de rectoría, y saldo total pendiente.",
            "parameters": {"student_id": {"type": "string", "description": "UUID del estudiante"}},
        },
        {
            "name": "get_risk_students",
            "description": "Lista los estudiantes cuyo promedio general está por debajo de 3.5 (En Riesgo). Incluye nombre, promedio y perfil. Máximo 20 resultados.",
            "parameters": {},
        },
        {
            "name": "get_teacher_grade_count",
            "description": "Obtiene la cantidad total de calificaciones que un docente ha registrado en el sistema. Útil para medir actividad docente.",
            "parameters": {"teacher_id": {"type": "string", "description": "UUID del docente"}},
        },
        {
            "name": "get_subject_info",
            "description": "Obtiene información detallada de una materia: nombre, si pertenece a ABP, descripción y enlaces a asistentes IA (tutor y planeador).",
            "parameters": {"subject_name": {"type": "string", "description": "Nombre exacto de la materia (ej: Matemáticas)"}},
        },
        {
            "name": "get_subject_materials",
            "description": "Obtiene los materiales educativos (guías PDF, enlaces, markdown) asociados a una materia y curso específicos. Incluye contenido generado por IA.",
            "parameters": {"subject_name": {"type": "string", "description": "Nombre exacto de la materia"}, "grade": {"type": "string", "description": "Curso (ej: 11-A)"}},
        },
        {
            "name": "search_materials",
            "description": "Busca materiales educativos y guías por texto. Útil cuando el estudiante pregunta sobre un tema específico (ej: 'fracciones', 'células', 'revolución industrial') y no sabes qué materia o curso es. Devuelve fragmentos relevantes con enlaces.",
            "parameters": {"query": {"type": "string", "description": "Término de búsqueda (mínimo 3 caracteres)"}, "max_results": {"type": "integer", "description": "Máximo de resultados (1-10, default 5)"}},
        },
    ]
    if role == "admin":
        tools.append({
            "name": "get_admin_stats",
            "description": "Obtiene estadísticas generales del sistema: total estudiantes, docentes, estudiantes al día vs en mora, promedio general de calificaciones y total de notas registradas.",
            "parameters": {},
        })
        tools.append({
            "name": "get_all_students_financial",
            "description": "Obtiene la lista completa de estudiantes con su estado financiero detallado: meses en mora, override, saldo pendiente y estado actual (AL_DIA / EN_MORA).",
            "parameters": {},
        })
        tools.append({
            "name": "run_sql_query",
            "description": "Ejecuta una consulta SQL de SOLO LECTURA (SELECT) sobre la base de datos. Solo para administradores. Tablas permitidas: profiles, subjects, grades, student_metadata, class_materials, guides, notices, exams, exam_progress, risk_alerts. Útil para responder preguntas que las herramientas existentes no cubren. LIMITA los resultados a 100 filas.",
            "parameters": {"query": {"type": "string", "description": "Consulta SELECT SQL válida. Solo SELECT. Máximo 500 caracteres."}},
        })
    return tools


TOOL_FUNCTIONS: dict[str, Any] = {}

async def _tool_get_student_grades_summary(db: Client, args: dict[str, Any], user_id: str) -> str:
    sid = args.get("student_id", user_id)
    result = db.table("grades").select("score, subject_id").eq("student_id", sid).execute()
    if not result.data:
        return "No se encontraron notas para este estudiante."
    grades = result.data
    scores = [float(g.get("score", 0)) for g in grades]
    avg = sum(scores) / len(scores) if scores else 0
    at_risk = [s for s in scores if s < 3.5]
    subjects_map = {}
    try:
        all_sub = db.table("subjects").select("id, name").execute()
        for s in all_sub.data:
            subjects_map[s["id"]] = s.get("name", s["id"])
    except Exception as e:
        logger.debug("subjects fetch error in get_student_grades_summary: %s", e)
    subject_details = []
    for g in grades:
        sub_name = subjects_map.get(g.get("subject_id", ""), g.get("subject_id", ""))
        subject_details.append(f"- {sub_name}: {float(g.get('score', 0)):.1f}")
    return json.dumps({
        "student_id": sid,
        "average": round(avg, 2),
        "total_subjects": len(grades),
        "at_risk_count": len(at_risk),
        "status": "Sobresaliente" if avg >= 4.0 else "Aceptable" if avg >= 3.5 else "En Riesgo",
        "subjects": subject_details,
    }, ensure_ascii=False)


async def _tool_get_financial_status(db: Client, args: dict[str, Any], user_id: str) -> str:
    sid = args.get("student_id", user_id)
    result = db.table("student_metadata").select("*").eq("profile_id", sid).execute()
    if not result.data:
        return "No se encontró información financiera."
    meta = result.data[0]
    months = meta.get("months_in_arrears", 0)
    override = meta.get("financial_override", False)
    is_blocked = months >= 2 and not override
    balance = float(meta.get("total_balance", 0))
    return json.dumps({
        "months_in_arrears": months,
        "financial_override": override,
        "is_blocked": is_blocked,
        "total_balance": balance,
        "current_status": meta.get("current_status", "AL_DIA"),
    }, ensure_ascii=False)


async def _tool_get_risk_students(db: Client, args: dict[str, Any], user_id: str) -> str:
    result = db.table("grades").select("student_id, score").execute()
    score_map: dict[str, list[float]] = {}
    for g in result.data:
        sid = g.get("student_id")
        if sid:
            if sid not in score_map:
                score_map[sid] = []
            score_map[sid].append(float(g.get("score", 0)))
    risk_ids = [sid for sid, scores in score_map.items() if (sum(scores) / len(scores)) < 3.5]
    if not risk_ids:
        return json.dumps({"students_at_risk": [], "count": 0}, ensure_ascii=False)
    # Batch query profiles instead of N+1
    profiles_result = db.table("profiles").select("id, fullname, login_credential").in_("id", risk_ids[:20]).execute()
    profile_map = {p["id"]: p for p in profiles_result.data}
    students = []
    for rid in risk_ids[:20]:
        p = profile_map.get(rid)
        if p:
            avg = sum(score_map[rid]) / len(score_map[rid])
            students.append({
                "profile_id": rid,
                "fullname": p.get("fullname", ""),
                "avg_score": round(avg, 2),
            })
    return json.dumps({"students_at_risk": students, "count": len(students)}, ensure_ascii=False)


async def _tool_get_teacher_grade_count(db: Client, args: dict[str, Any], user_id: str) -> str:
    tid = args.get("teacher_id", user_id)
    result = db.table("grades").select("id").eq("teacher_id", tid).execute()
    count = len(result.data)
    return json.dumps({"teacher_id": tid, "grades_registered": count}, ensure_ascii=False)


async def _tool_get_subject_info(db: Client, args: dict[str, Any], user_id: str) -> str:
    name = args.get("subject_name", "")
    result = db.table("subjects").select("*").eq("name", name).execute()
    if not result.data:
        return f"No se encontró la materia '{name}'."
    sub = result.data[0]
    return json.dumps({
        "id": sub.get("id"),
        "name": sub.get("name"),
        "is_abp": sub.get("is_abp", False),
        "description": sub.get("description", ""),
    }, ensure_ascii=False)


async def _tool_get_admin_stats(db: Client, args: dict[str, Any], user_id: str) -> str:
    profiles = db.table("profiles").select("role").execute()
    total_students = sum(1 for p in profiles.data if p.get("role") == "student")
    total_teachers = sum(1 for p in profiles.data if p.get("role") == "teacher")
    meta = db.table("student_metadata").select("current_status, months_in_arrears").execute()
    en_mora = sum(1 for m in meta.data if m.get("current_status") == "EN_MORA" or m.get("months_in_arrears", 0) >= 2)
    al_dia = len(meta.data) - en_mora
    grades = db.table("grades").select("score").execute()
    scores = [float(g.get("score", 0)) for g in grades.data]
    avg = round(sum(scores) / len(scores), 2) if scores else 0
    return json.dumps({
        "total_students": total_students,
        "total_teachers": total_teachers,
        "al_dia": al_dia,
        "en_mora": en_mora,
        "average_score": avg,
        "total_grades": len(grades.data),
    }, ensure_ascii=False)


async def _tool_get_all_students_financial(db: Client, args: dict[str, Any], user_id: str) -> str:
    result = db.table("student_metadata").select("profile_id, months_in_arrears, financial_override, total_balance, current_status").execute()
    if not result.data:
        return json.dumps({"total": 0, "paid": 0, "unpaid": 0, "students": []}, ensure_ascii=False)
    profile_ids = [m.get("profile_id") for m in result.data if m.get("profile_id")]
    profile_map = {}
    if profile_ids:
        profiles = db.table("profiles").select("id, fullname, login_credential").in_("id", profile_ids).execute()
        profile_map = {p["id"]: p for p in profiles.data}
    students = []
    for m in result.data:
        pid = m.get("profile_id")
        p = profile_map.get(pid) if pid else None
        students.append({
            "profile_id": pid,
            "fullname": p.get("fullname", "") if p else "",
            "months_in_arrears": m.get("months_in_arrears", 0),
            "financial_override": m.get("financial_override", False),
            "total_balance": float(m.get("total_balance", 0)),
            "status": m.get("current_status", "AL_DIA"),
        })
    paid = sum(1 for s in students if s["status"] != "EN_MORA")
    unpaid = len(students) - paid
    return json.dumps({"total": len(students), "paid": paid, "unpaid": unpaid, "students": students}, ensure_ascii=False)


async def _tool_get_subject_materials(db: Client, args: dict[str, Any], user_id: str) -> str:
    subject_name = args.get("subject_name", "")
    grade = args.get("grade", "")
    if not subject_name:
        return "Indica el nombre de la materia."
    result = db.table("subjects").select("*").eq("name", subject_name).execute()
    if not result.data:
        return f"No se encontró la materia '{subject_name}'."
    sub = result.data[0]
    sub_id = sub.get("id")
    material_result = db.table("class_materials").select("*").eq("subject_id", sub_id).execute()
    materials = material_result.data or []
    guides_result = db.table("guides").select("*").eq("subject", subject_name).execute()
    if grade:
        guides_result = db.table("guides").select("*").eq("grade", grade).eq("subject", subject_name).execute()
    guides = guides_result.data or []
    return json.dumps({
        "subject": {"name": sub.get("name"), "is_abp": sub.get("is_abp"), "tutor_ai": sub.get("tutor_ai", ""), "planner_ai": sub.get("planner_ai", "")},
        "materials": [{"title": m.get("file_type", "material"), "url": m.get("file_url", "")} for m in materials],
        "guides": [{"title": g.get("title", g.get("filename", "Guía")), "url": g.get("url", "")} for g in guides],
        "total_materials": len(materials) + len(guides),
    }, ensure_ascii=False)


async def _tool_run_sql_query(db: Client, args: dict[str, Any], user_id: str) -> str:
    if os.getenv("ENABLE_RAW_SQL_QUERIES", "").lower() not in ("true", "1", "yes"):
        return json.dumps({"error": "La ejecución de SQL directo está deshabilitada por seguridad."}, ensure_ascii=False, default=str)
    query = args.get("query", "").strip()
    query_lower = query.strip().lower()
    if not query_lower.startswith("select"):
        return json.dumps({"error": "Solo se permiten consultas SELECT."}, ensure_ascii=False, default=str)
    if query_lower.count(";") > 1:
        return json.dumps({"error": "Solo se permite una consulta a la vez."}, ensure_ascii=False, default=str)
    if len(query) > 500:
        return json.dumps({"error": "Consulta demasiado larga (máximo 500 caracteres)."}, ensure_ascii=False, default=str)
    allowed_tables = {"profiles", "subjects", "grades", "student_metadata", "class_materials", "guides", "notices", "exams", "exam_progress", "risk_alerts", "conversations"}
    table_refs = {t for t in allowed_tables if t in query_lower}
    if not table_refs:
        return json.dumps({"error": "La consulta no referencia ninguna tabla permitida."}, ensure_ascii=False, default=str)

    # Block dangerous patterns regardless
    dangerous = re.search(r'\b(drop|truncate|delete|insert|update|alter|create|grant|revoke|exec|execute|call|fetch|copy|set|reset|load|import|export|pg_sleep|dblink|lo_import|lo_export|pg_read_file|pg_write_file|pg_stat_file|generate_series|unnest)\b', query_lower, re.DOTALL | re.MULTILINE)
    if dangerous:
        return json.dumps({"error": "Operación no permitida."}, ensure_ascii=False, default=str)

    # Log query for audit
    logger.info("ai_agent running read-only query: user=%s query=%.200s", user_id, query)

    # Use parameterized query via Supabase RPC if available, otherwise deny
    try:
        result = db.rpc("run_readonly_query", {"query_text": query}).execute()
        data = result.data if hasattr(result, 'data') else result
        if isinstance(data, list):
            if len(data) > 100:
                data = data[:100]
                return json.dumps({"count": len(data), "truncated": True, "rows": data}, ensure_ascii=False, default=str)
            return json.dumps({"count": len(data), "rows": data}, ensure_ascii=False, default=str)
        return json.dumps({"result": str(data)[:2000]}, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error("sql query error (rpc fallback): %s", e)
        return json.dumps({"error": f"Error al ejecutar la consulta: {str(e)[:150]}"}, ensure_ascii=False, default=str)


TOOL_FUNCTIONS = {
    "get_student_grades_summary": _tool_get_student_grades_summary,
    "get_financial_status": _tool_get_financial_status,
    "get_risk_students": _tool_get_risk_students,
    "get_teacher_grade_count": _tool_get_teacher_grade_count,
    "get_subject_info": _tool_get_subject_info,
    "get_admin_stats": _tool_get_admin_stats,
    "get_all_students_financial": _tool_get_all_students_financial,
    "get_subject_materials": _tool_get_subject_materials,
    "search_materials": _tool_search_materials,
    "run_sql_query": _tool_run_sql_query,
}


def _build_user_context(role: str, user_id: str) -> str:
    """Auto-build rich user context from database. Results cached per session."""
    ck = f"{role}:{user_id}"
    cached = _user_context_cache.get(ck)
    if cached and time.time() - cached[1] < CONTEXT_CACHE_TTL:
        return cached[0]
    try:
        db = _get_db()
        profile = db.table("profiles").select("id, fullname, login_credential, role").eq("id", user_id).maybe_single().execute()
        name = profile.data.get("fullname", "") if profile.data else ""
        ctx_parts = []
        if role == "student":
            if name:
                ctx_parts.append(f"Nombre: {name}")
            # Fetch grades with subject names
            grades_raw = db.table("grades").select("score, subject_id").eq("student_id", user_id).execute()
            subjects_raw = db.table("subjects").select("id, name").execute()
            sub_map = {s["id"]: s.get("name", "?") for s in subjects_raw.data} if subjects_raw.data else {}
            if grades_raw.data:
                subject_grades = []
                scores = []
                for g in grades_raw.data:
                    sname = sub_map.get(g.get("subject_id", ""), "?")
                    score = float(g.get("score", 0))
                    scores.append(score)
                    subject_grades.append(f"{sname}: {score:.1f}")
                avg = sum(scores) / len(scores) if scores else 0
                at_risk = sum(1 for s in scores if s < 3.5)
                risk_subjects = [sg for i, sg in enumerate(subject_grades) if scores[i] < 3.5]
                ctx_parts.append(f"Promedio general: {avg:.1f}/5.0")
                ctx_parts.append(f"Materias cursadas: {', '.join(subject_grades)}")
                if at_risk:
                    ctx_parts.append(f"Materias en riesgo (<3.5): {', '.join(risk_subjects)}")
                ctx_parts.append(f"Estado: {'Sobresaliente' if avg >= 4.0 else 'Aceptable' if avg >= 3.5 else 'En Riesgo'}")
            # Financial status
            meta = db.table("student_metadata").select("current_status, months_in_arrears, financial_override, total_balance").eq("profile_id", user_id).execute()
            if meta.data and meta.data[0].get("current_status"):
                m = meta.data[0]
                ctx_parts.append(f"Estado financiero: {m['current_status']}")
                if m.get("months_in_arrears", 0) > 0:
                    ctx_parts.append(f"Meses en mora: {m['months_in_arrears']}")
        elif role == "teacher":
            if name:
                ctx_parts.append(f"Nombre: {name}")
            # Teacher's subjects
            my_subjects = db.table("subjects").select("name").execute()
            sub_names = [s.get("name", "") for s in my_subjects.data if s.get("name")]
            if sub_names:
                ctx_parts.append(f"Materias: {', '.join(sub_names[:10])}")
            # Risk summary
            risk = db.table("grades").select("student_id, score").execute()
            score_map: dict[str, list[float]] = {}
            for g in risk.data:
                sid = g.get("student_id")
                if sid:
                    score_map.setdefault(sid, []).append(float(g["score"]))
            risk_count = sum(1 for s in score_map.values() if (sum(s) / len(s)) < 3.5)
            ctx_parts.append(f"Estudiantes en riesgo académico: aproximadamente {risk_count}")
            ctx_parts.append(f"Total estudiantes con notas: {len(score_map)}")
        elif role == "admin":
            if name:
                ctx_parts.append(f"Nombre: {name}")
            students_res = db.table("profiles").select("*", count="exact").eq("role", "student").execute()
            teachers_res = db.table("profiles").select("*", count="exact").eq("role", "teacher").execute()
            total_students = getattr(students_res, 'count', 0) or 0
            total_teachers = getattr(teachers_res, 'count', 0) or 0
            ctx_parts.append(f"Total estudiantes: {total_students}")
            ctx_parts.append(f"Total docentes: {total_teachers}")
            paid_res = db.table("student_metadata").select("*", count="exact").eq("current_status", "AL_DIA").execute()
            mora_res = db.table("student_metadata").select("*", count="exact").eq("current_status", "EN_MORA").execute()
            al_dia = getattr(paid_res, 'count', 0) or 0
            en_mora = getattr(mora_res, 'count', 0) or 0
            ctx_parts.append(f"Al día: {al_dia} | En mora: {en_mora}")
            try:
                avg_res = db.table("grades").select("score.avg()").execute()
                if avg_res.data and len(avg_res.data) > 0:
                    raw = avg_res.data[0]
                    avg_val = raw.get("avg", raw) if isinstance(raw, dict) else raw
                    if isinstance(avg_val, dict):
                        avg_val = avg_val.get("score")
                    if avg_val is not None:
                        ctx_parts.append(f"Promedio general institucional: {round(float(avg_val), 2)}/5.0")
            except Exception:
                pass
        result = "\n".join(ctx_parts)
        logger.debug("user context for %s (%s): %d chars", role, user_id[:8], len(result))
        _user_context_cache[ck] = (result, time.time())
        return result
    except Exception as e:
        logger.debug("auto-build context error: %s", e)
        return ""


def _build_messages(role: str, user_message: str, context: str, user_id: str, thread_id: str | None = None) -> list[dict[str, str]]:
    system_prompt = SYSTEM_PROMPTS.get(role, SYSTEM_PROMPTS["student"])
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    resolved_context = context or _build_user_context(role, user_id)
    if resolved_context:
        messages.append({"role": "system", "content": f"Datos del usuario:\n{resolved_context}"})
    history = _load_messages(role, user_id, thread_id)
    for msg in history[-MAX_HISTORY:]:
        messages.append(msg)
    messages.append({"role": "user", "content": user_message})
    # Token budget check
    if _estimate_tokens(messages) > TOKEN_BUDGET_MAX:
        # Keep only system + last user message
        sys_msgs = [m for m in messages if m["role"] == "system"]
        messages = sys_msgs + [messages[-1]]
        logger.info("token budget exceeded for user=%s, trimmed to %d messages", user_id, len(messages))
    return messages


def _build_payload(role: str, messages: list[dict[str, str]], tools_enabled: bool = True) -> dict[str, Any]:
    config = ROLE_CONFIG.get(role, ROLE_CONFIG["student"])
    model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
        "max_tokens": config["max_tokens"],
        "temperature": config["temperature"],
    }
    if tools_enabled:
        tools = _get_available_for_role(role)
        if tools:
            payload["tools"] = [{
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": {
                        "type": "object",
                        "properties": t.get("parameters", {}),
                        "required": [k for k, v in t.get("parameters", {}).items() if k != "student_id"],
                    },
                },
            } for t in tools]
    return payload


def _build_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": REFERER_URL,
    }


async def _call_llm_with_retry(
    api_key: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    base_url: str = OPENROUTER_BASE,
    provider: str = "OpenRouter",
) -> httpx.Response:
    last_error = None
    for attempt in range(RETRY_MAX_ATTEMPTS + 1):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(base_url, json=payload, headers=headers)
            if resp.status_code < 500 or attempt == RETRY_MAX_ATTEMPTS:
                return resp
            last_error = resp.status_code
            if attempt < RETRY_MAX_ATTEMPTS:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.info("retrying %s after status=%s attempt=%d/%d", provider, resp.status_code, attempt + 1, RETRY_MAX_ATTEMPTS)
                await asyncio.sleep(delay)
                continue
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            last_error = e
            if attempt < RETRY_MAX_ATTEMPTS:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.info("retrying %s after %s attempt=%d/%d", provider, type(e).__name__, attempt + 1, RETRY_MAX_ATTEMPTS)
                await asyncio.sleep(delay)
            else:
                raise
    raise HTTPException(status_code=502, detail=f"Error de conexión con {provider} después de reintentos")


async def _execute_tool_call(db: Client, tool_call: dict[str, Any], user_id: str, role: str = "student") -> str:
    func_name = tool_call.get("function", {}).get("name", "")
    t0 = time.time()
    try:
        raw_args = tool_call.get("function", {}).get("arguments", "{}")
        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
    except json.JSONDecodeError:
        args = {}
    guard_result = guardrails.check_tool_call(func_name, args, role)
    if guard_result:
        logger.warning("tool guardrail blocked %s by user=%s role=%s: %s", func_name, user_id, role, guard_result)
        return json.dumps({"error": guard_result})
    cached = tool_cache.get(func_name, user_id, args)
    if cached is not None:
        logger.info("tool cache hit %s user=%s", func_name, user_id)
        return cached
    func = TOOL_FUNCTIONS.get(func_name)
    if not func:
        logger.warning("unknown tool called: %s by user=%s", func_name, user_id)
        return json.dumps({"error": f"La función '{func_name}' no está disponible en este momento. Intenta con otra consulta."})
    try:
        result = await func(db, args, user_id)
        elapsed = time.time() - t0
        logger.info("tool=%s user=%s elapsed=%.2fs result_len=%d", func_name, user_id, elapsed, len(result))
        if func_name in CACHEABLE_TOOLS:
            tool_cache.set(func_name, user_id, args, result)
        # Track usage
        with _state_lock:
            if user_id not in tool_usage_counters:
                tool_usage_counters[user_id] = {}
            tool_usage_counters[user_id][func_name] = tool_usage_counters[user_id].get(func_name, 0) + 1
        return _truncate_tool_result(result)
    except Exception as e:
        elapsed = time.time() - t0
        logger.error("tool %s error after %.2fs: %s", func_name, elapsed, e)
        return json.dumps({
            "error": f"Ocurrió un error al consultar {func_name}. Por favor intenta de nuevo o reformula tu pregunta.",
            "detail": str(e)[:100],
        })


def _parse_tool_calls(choice: dict[str, Any]) -> list[dict[str, Any]]:
    delta = choice.get("delta", {})
    if "tool_calls" in delta:
        return delta["tool_calls"]
    if "message" in choice and "tool_calls" in choice["message"]:
        return choice["message"]["tool_calls"]
    return []


def _try_save_react_result(role: str, user_id: str, original_message: str, full_text: str) -> None:
    if not full_text or not full_text.strip():
        return
    history = _load_messages(role, user_id)
    history.append({"role": "user", "content": original_message})
    history.append({"role": "assistant", "content": full_text})
    while len(history) > MAX_HISTORY * 2:
        history.pop(0)
    _save_messages(role, user_id, history)
    logger.info("saved partial react result role=%s user=%s msgs=%d", role, user_id, len(history))


async def _stream_with_react(
    api_key: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    user_id: str,
    original_message: str,
    role: str,
    request_id: str = "",
) -> AsyncGenerator[str, None]:
    db = _get_db()
    full_assistant_text = ""
    iteration = 0
    current_messages = list(payload["messages"])
    used_fallback = False
    used_groq = False
    consecutive_errors = 0

    while iteration < REACT_MAX_ITERATIONS:
        iteration += 1
        current_payload = dict(payload)
        current_payload["messages"] = current_messages
        current_payload["stream"] = True

        try:
            resp = await asyncio.wait_for(
                _call_llm_with_retry(api_key, current_payload, headers),
                timeout=ITERATION_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            consecutive_errors += 1
            logger.error("timeout req=%s iter=%s consecutive=%d", request_id, iteration, consecutive_errors)
            if consecutive_errors >= CIRCUIT_BREAKER_MAX_ERRORS:
                _try_save_react_result(role, user_id, original_message, full_assistant_text)
                yield f"data: {json.dumps({'error': 'El asistente no está respondiendo. Intenta de nuevo más tarde.'})}\n\n"
                yield "data: [DONE]\n\n"
                return
            if iteration == 1:
                yield f"data: {json.dumps({'error': 'El asistente tardó demasiado. Reintentando...'})}\n\n"
            continue
        except HTTPException as e:
            consecutive_errors += 1
            logger.error("OpenRouter call failed req=%s iter=%s: %s", request_id, iteration, e.detail)
            if consecutive_errors >= CIRCUIT_BREAKER_MAX_ERRORS:
                _try_save_react_result(role, user_id, original_message, full_assistant_text)
                yield f"data: {json.dumps({'error': 'Error de conexión con el asistente. Intenta de nuevo.'})}\n\n"
                yield "data: [DONE]\n\n"
                return
            if iteration == 1:
                yield f"data: {json.dumps({'error': 'Error de conexión con el asistente. Reintentando...'})}\n\n"
            continue

        if resp.status_code != 200:
            consecutive_errors += 1
            if consecutive_errors >= CIRCUIT_BREAKER_MAX_ERRORS:
                _try_save_react_result(role, user_id, original_message, full_assistant_text)
                yield f"data: {json.dumps({'error': 'Error del asistente después de múltiples intentos.'})}\n\n"
                yield "data: [DONE]\n\n"
                return
            # Try fallback model on same provider
            if not used_fallback:
                used_fallback = True
                logger.info("retrying with fallback model req=%s iter=%s", request_id, iteration)
                current_payload["model"] = FALLBACK_MODEL
                try:
                    resp = await asyncio.wait_for(
                        _call_llm_with_retry(api_key, current_payload, headers),
                        timeout=ITERATION_TIMEOUT_SECONDS,
                    )
                except (asyncio.TimeoutError, HTTPException) as e:
                    logger.error("fallback also failed req=%s iter=%s: %s", request_id, iteration, e)
                    if consecutive_errors >= CIRCUIT_BREAKER_MAX_ERRORS:
                        _try_save_react_result(role, user_id, original_message, full_assistant_text)
                        yield f"data: {json.dumps({'error': 'Error del asistente. Intenta de nuevo más tarde.'})}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                    continue
                if resp.status_code != 200:
                    logger.error("OpenRouter+fallback error req=%s status=%s", request_id, resp.status_code)
                    if consecutive_errors >= CIRCUIT_BREAKER_MAX_ERRORS:
                        _try_save_react_result(role, user_id, original_message, full_assistant_text)
                        yield f"data: {json.dumps({'error': 'Error del asistente. Intenta de nuevo más tarde.'})}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                    continue
            elif GROQ_API_KEY and not used_groq:
                used_groq = True
                logger.info("retrying with Groq req=%s iter=%s", request_id, iteration)
                current_payload["model"] = GROQ_FALLBACK_MODEL
                try:
                    resp = await asyncio.wait_for(
                        _call_llm_with_retry(GROQ_API_KEY, current_payload, {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}, GROQ_BASE, "Groq"),
                        timeout=ITERATION_TIMEOUT_SECONDS,
                    )
                except (asyncio.TimeoutError, HTTPException) as e:
                    logger.error("Groq also failed req=%s iter=%s: %s", request_id, iteration, e)
                    if consecutive_errors >= CIRCUIT_BREAKER_MAX_ERRORS:
                        _try_save_react_result(role, user_id, original_message, full_assistant_text)
                        yield f"data: {json.dumps({'error': 'Error del asistente. Intenta de nuevo más tarde.'})}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                    continue
                if resp.status_code != 200:
                    logger.error("Groq error req=%s status=%s", request_id, resp.status_code)
                    if consecutive_errors >= CIRCUIT_BREAKER_MAX_ERRORS:
                        _try_save_react_result(role, user_id, original_message, full_assistant_text)
                        yield f"data: {json.dumps({'error': 'Error del asistente. Intenta de nuevo más tarde.'})}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                    continue
            else:
                logger.error("OpenRouter error req=%s status=%s", request_id, resp.status_code)
                _try_save_react_result(role, user_id, original_message, full_assistant_text)
                if iteration == 1:
                    yield f"data: {json.dumps({'error': f'Error del asistente (código {resp.status_code})'})}\n\n"
                    yield "data: [DONE]\n\n"
                return

        consecutive_errors = 0
        if iteration == 1:
            model_name = current_payload.get("model", DEFAULT_MODEL)
            yield f"data: {json.dumps({'model': model_name})}\n\n"
        assistant_content = ""
        tool_calls_buffer: dict[int, dict[str, Any]] = {}
        tool_call_names: list[str] = []

        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
            except json.JSONDecodeError:
                continue
            choices = chunk.get("choices", [])
            if not choices:
                continue
            choice = choices[0]
            delta = choice.get("delta", {})

            if delta.get("content"):
                token = delta["content"]
                assistant_content += token
                full_assistant_text += token
                yield f"data: {json.dumps({'token': _sanitize_output(token)})}\n\n"

            finish_reason = choice.get("finish_reason")
            tc_raw = delta.get("tool_calls") or choice.get("message", {}).get("tool_calls")
            if tc_raw:
                for tc in tc_raw:
                    idx = tc.get("index", 0)
                    if idx not in tool_calls_buffer:
                        tool_calls_buffer[idx] = {"id": tc.get("id", f"call_{idx}"), "type": "function", "function": {"name": "", "arguments": ""}}
                        if tc.get("function", {}).get("name"):
                            tool_call_names.append(tc["function"]["name"])
                    buf = tool_calls_buffer[idx]
                    if tc.get("id"):
                        buf["id"] = tc["id"]
                    if tc.get("function"):
                        fn = tc["function"]
                        if fn.get("name"):
                            buf["function"]["name"] += fn["name"]
                        if fn.get("arguments"):
                            buf["function"]["arguments"] += fn["arguments"]

            if finish_reason == "tool_calls" or (finish_reason == "stop" and tool_calls_buffer):
                if tool_call_names:
                    tool_names_str = ", ".join(tool_call_names)
                    status = json.dumps({"tool_status": f"Consultando datos: {tool_names_str}"})
                    yield f"data: {status}\n\n"
                current_messages.append({"role": "assistant", "content": assistant_content or None})
                tool_calls_list = list(tool_calls_buffer.values())
                current_messages[-1]["tool_calls"] = [
                    {"id": tc["id"], "type": "function", "function": tc["function"]}
                    for tc in tool_calls_list
                ]
                for tc in tool_calls_list:
                    tool_name = tc["function"]["name"]
                    yield f"data: {json.dumps({'tool_status': f'Consultando {tool_name}...'})}\n\n"
                    tool_result = await _execute_tool_call(db, tc, user_id, role)
                    current_messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": tool_result,
                    })
                    logger.info("tool=%s user=%s req=%s result_len=%d", tool_name, user_id, request_id, len(tool_result))
                break
        else:
            if not full_assistant_text and not assistant_content:
                yield f"data: {json.dumps({'token': '...'})}\n\n"
            break

        if not tool_calls_buffer:
            break

    if not full_assistant_text.strip():
        fallback = "No pude generar una respuesta. ¿Podrías reformular tu consulta?"
        yield f"data: {json.dumps({'token': fallback})}\n\n"
        full_assistant_text = fallback
    guardrails.check_output(full_assistant_text)
    yield "data: [DONE]\n\n"
    history = _load_messages(role, user_id)
    history.append({"role": "user", "content": original_message})
    history.append({"role": "assistant", "content": full_assistant_text})
    while len(history) > MAX_HISTORY * 2:
        history.pop(0)
    _save_messages(role, user_id, history)
    logger.info("saved conv role=%s user=%s req=%s msgs=%d", role, user_id, request_id, len(history))


def _save_stream_result(role: str, user_id: str, original_message: str, full_text: str, thread_id: str | None = None) -> None:
    history = _load_messages(role, user_id, thread_id)
    history.append({"role": "user", "content": original_message})
    history.append({"role": "assistant", "content": full_text})
    while len(history) > MAX_HISTORY * 2:
        history.pop(0)
    _save_messages(role, user_id, history, thread_id)


async def _stream_simple(
    api_key: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    user_id: str,
    original_message: str,
    role: str,
    request_id: str = "",
    thread_id: str | None = None,
) -> AsyncGenerator[str, None]:
    full_text = ""
    consecutive_errors = 0
    used_fallback = False
    used_groq = False

    for attempt in range(RETRY_MAX_ATTEMPTS + 1):
        current_payload = dict(payload)
        current_headers = dict(headers)
        current_key = api_key
        current_base = OPENROUTER_BASE

        if used_groq:
            current_payload["model"] = GROQ_FALLBACK_MODEL
            current_key = GROQ_API_KEY
            current_headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            current_base = GROQ_BASE
        elif used_fallback:
            current_payload["model"] = FALLBACK_MODEL

        try:
            async with httpx.AsyncClient(timeout=ITERATION_TIMEOUT_SECONDS) as client:
                async with client.stream("POST", current_base, json=current_payload, headers=current_headers) as resp:
                    if resp.status_code != 200:
                        consecutive_errors += 1
                        if consecutive_errors >= CIRCUIT_BREAKER_MAX_ERRORS:
                            logger.error("OpenRouter fatal [%s] user=%s status=%d", role, user_id, resp.status_code)
                            yield f"data: {json.dumps({'error': 'El asistente no está disponible. Intenta de nuevo.'})}\n\n"
                            yield "data: [DONE]\n\n"
                            return
                        if not used_fallback:
                            used_fallback = True
                            logger.info("fallback model [%s] user=%s attempt=%d", role, user_id, attempt)
                            continue
                        if GROQ_API_KEY and not used_groq:
                            used_groq = True
                            logger.info("fallback Groq [%s] user=%s attempt=%d", role, user_id, attempt)
                            continue
                        logger.error("all fallbacks exhausted [%s] user=%s status=%d", role, user_id, resp.status_code)
                        yield f"data: {json.dumps({'error': f'Error del asistente (código {resp.status_code})'})}\n\n"
                        yield "data: [DONE]\n\n"
                        return

                    consecutive_errors = 0
                    model_name = current_payload.get("model", DEFAULT_MODEL)
                    yield f"data: {json.dumps({'model': model_name})}\n\n"
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            if not full_text.strip():
                                full_text = "No pude generar una respuesta. ¿Podrías reformular tu consulta?"
                                yield f"data: {json.dumps({'token': full_text})}\n\n"
                            _save_stream_result(role, user_id, original_message, full_text, thread_id)
                            logger.info("stream done [%s] user=%s req=%s tokens=%d", role, user_id, request_id, len(full_text))
                            yield "data: [DONE]\n\n"
                            return
                        try:
                            chunk = json.loads(data_str)
                            choices = chunk.get("choices", [])
                            if not choices:
                                continue
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_text += content
                                yield f"data: {json.dumps({'token': _sanitize_output(content)})}\n\n"
                        except json.JSONDecodeError:
                            continue

                    # Stream closed without [DONE] — save partial content
                    if full_text.strip():
                        _save_stream_result(role, user_id, original_message, full_text, thread_id)
                        logger.info("stream incomplete but saved [%s] user=%s req=%s tokens=%d", role, user_id, request_id, len(full_text))
                    else:
                        full_text = "La respuesta se interrumpió. Intenta de nuevo."
                        yield f"data: {json.dumps({'token': full_text})}\n\n"
                    yield "data: [DONE]\n\n"
                    return

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            consecutive_errors += 1
            logger.warning("stream %s [%s] user=%s attempt=%d err=%s", type(e).__name__, role, user_id, attempt, e)
            if consecutive_errors >= CIRCUIT_BREAKER_MAX_ERRORS:
                yield f"data: {json.dumps({'error': 'El asistente no responde. Intenta de nuevo.'})}\n\n"
                yield "data: [DONE]\n\n"
                return
            if attempt == 0:
                yield f"data: {json.dumps({'error': 'Reconectando...'})}\n\n"
            continue

        except Exception as e:
            logger.error("stream_simple unexpected [%s] user=%s req=%s: %s", role, user_id, request_id, e)
            if full_text.strip():
                _save_stream_result(role, user_id, original_message, full_text, thread_id)
            yield f"data: {json.dumps({'error': 'Error de conexión. Verifica tu red e intenta de nuevo.'})}\n\n"
            yield "data: [DONE]\n\n"
            return

    yield f"data: {json.dumps({'error': 'No se pudo conectar con el asistente.'})}\n\n"
    yield "data: [DONE]\n\n"


def _build_role_endpoint(role: str) -> str:
    return ROLE_ENDPOINT.get(role, ROLE_ENDPOINT["student"])


def _create_chat_handler(role: str):
    async def handler(req: ChatRequest, user_id: str = Depends(auth_dependency)) -> StreamingResponse:
        request_id = uuid.uuid4().hex[:12]
        _t0 = time.monotonic()
        logger.info("chat req=%s role=%s user=%s msg_len=%d", request_id, role, user_id, len(req.message))
        guard_result = guardrails.check_input(req.message, role)
        if guard_result:
            logger.info("chat guard blocked req=%s dt=%.2fms", request_id, (time.monotonic() - _t0) * 1000)
            return StreamingResponse(
                _stream_error(guard_result),
                media_type="text/event-stream",
            )
        _check_rate_limit(user_id)
        api_key = _get_api_key(role)
        thread_id = req.thread_id
        messages = _build_messages(role, req.message, req.context, user_id, thread_id)
        if role == "student" or thread_id:
            payload = _build_payload(role, messages, tools_enabled=False)
            headers = _build_headers(api_key)
            _t1 = time.monotonic()
            logger.info("chat setup done req=%s dt=%.2fms stream=simple", request_id, (_t1 - _t0) * 1000)
            return StreamingResponse(
                _stream_simple(api_key, payload, headers, user_id, req.message, role, request_id, thread_id),
                media_type="text/event-stream",
            )
        payload = _build_payload(role, messages)
        headers = _build_headers(api_key)
        _t1 = time.monotonic()
        logger.info("chat setup done req=%s dt=%.2fms stream=react", request_id, (_t1 - _t0) * 1000)
        return StreamingResponse(
            _stream_with_react(api_key, payload, headers, user_id, req.message, role, request_id),
            media_type="text/event-stream",
        )
    return handler


student_tutor = _create_chat_handler("student")
teacher_tutor = _create_chat_handler("teacher")
admin_assistant = _create_chat_handler("admin")

student_tutor.__name__ = "student_tutor"
teacher_tutor.__name__ = "teacher_tutor"
admin_assistant.__name__ = "admin_assistant"

router.post("/student-tutor")(student_tutor)
router.post("/teacher-tutor")(teacher_tutor)
router.post("/admin-assistant")(admin_assistant)


@router.post("/conversation/clear")
async def clear_conversation(role: str = "student", user_id: str = Depends(auth_dependency)) -> dict[str, str]:
    _cache_evict(role, user_id)
    try:
        db = _get_db()
        existing = db.table("conversations").select("id").eq("user_id", user_id).eq("role", role).order("created_at", desc=True).limit(1).execute()
        if existing.data:
            db.table("conversations").update({"messages": []}).eq("id", existing.data[0]["id"]).execute()
    except Exception as e:
        logger.debug("clear_conversation db error: %s", e)
    return {"status": "cleared"}


# ── Chat Threads (full-screen chat by subject) ──


class ThreadCreate(BaseModel):
    subject: str = Field(default="", max_length=100)
    title: str = Field(default="", max_length=200)


class ThreadResponse(BaseModel):
    id: str
    subject: str
    title: str
    last_message: str = ""
    updated_at: str


def _extract_thread_meta(messages: list) -> tuple[str, str]:
    subject = ""
    title = ""
    if messages and isinstance(messages[0], dict) and messages[0].get("content") == "_thread_meta_":
        subject = messages[0].get("subject", "")
        title = messages[0].get("title", "")
    return subject, title


@router.get("/threads")
async def list_threads(role: str = "student", user_id: str = Depends(auth_dependency)) -> list[dict[str, Any]]:
    db = _get_db()
    result = db.table("conversations").select("id, messages, updated_at")\
        .eq("user_id", user_id).eq("role", role)\
        .order("updated_at", desc=True).limit(50).execute()
    threads = []
    for row in result.data or []:
        msgs = row.get("messages", [])
        subject, title = _extract_thread_meta(msgs)
        # Skip floating-chat rows (no thread metadata)
        if not subject and not title:
            continue
        # Skip metadata marker to get real messages for last_message
        real_msgs = msgs[1:] if msgs and msgs[0].get("content") == "_thread_meta_" else msgs
        last = ""
        for m in reversed(real_msgs):
            if m.get("role") == "assistant" and m.get("content", "").strip():
                last = m["content"][:120]
                break
        threads.append({
            "id": row["id"],
            "subject": subject,
            "title": title,
            "last_message": last,
            "updated_at": row.get("updated_at", ""),
        })
    return threads


@router.post("/threads")
async def create_thread(body: ThreadCreate, role: str = "student", user_id: str = Depends(auth_dependency)) -> dict[str, Any]:
    db = _get_db()
    now = datetime.now(timezone.utc).isoformat()
    title = body.title or body.subject or "Nuevo chat"
    # Store thread metadata as first message in conversations table
    meta_msg = {"role": "system", "content": "_thread_meta_", "subject": body.subject, "title": title}
    doc = {
        "user_id": user_id,
        "role": role,
        "messages": [meta_msg],
        "created_at": now,
        "updated_at": now,
    }
    result = db.table("conversations").insert(doc).execute()
    row = result.data[0] if result.data else doc
    return {"id": row["id"], "subject": body.subject, "title": title}


@router.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str, user_id: str = Depends(auth_dependency)) -> dict[str, str]:
    db = _get_db()
    db.table("conversations").delete().eq("id", thread_id).eq("user_id", user_id).execute()
    ck = _thread_cache_key(thread_id)
    _conversation_cache.pop(ck, None)
    return {"status": "deleted"}


@router.get("/usage")
async def get_usage(user_id: str = Depends(auth_dependency)) -> dict[str, Any]:
    user_usage = tool_usage_counters.get(user_id, {})
    return {"user_id": user_id, "tool_usage": user_usage}
