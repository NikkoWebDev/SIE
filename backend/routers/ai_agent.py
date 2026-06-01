from __future__ import annotations

import json
import logging
import os
import re
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from supabase import Client

from config.database import get_db
from dependencies import admin_dependency, auth_dependency, teacher_dependency

logger = logging.getLogger("siee.ai_agent")
router = APIRouter(prefix="/api/ai", tags=["ai"])

OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"
REFERER_URL = "https://colegiociudaddelsol.edu.co"
MAX_HISTORY = 20
RATE_LIMIT_PER_MINUTE = 15
REACT_MAX_ITERATIONS = 5

FALLBACK_MODEL = "openrouter/auto"

SCHOOL_CONTEXT = """Institución: Colegio Técnico Ciudad del Sol (Sogamoso, Boyacá, Colombia)
Metodología: Aprendizaje Basado en Proyectos (ABP) con 9 materias vinculadas
Escala: 0.0 - 5.0. Mínimo aprobación: 3.5
Estados: ≥4.0 Sobresaliente (#00FF66), 3.5-4.0 Aceptable (#FFE600), <3.5 En Riesgo (#FF0055)
Mora: ≥2 meses bloquea descargas PDF (excepto con override de rectoría)
Plataforma: VYNTRA Academic / Solaris"""

SYSTEM_PROMPTS: dict[str, str] = {
    "student": (
        f"Eres el TUTOR VYNTRA, asistente académico empático del Colegio Ciudad del Sol.\n\n"
        f"Contexto institucional:\n{SCHOOL_CONTEXT}\n\n"
        "INSTRUCCIONES:\n"
        "- Responde en español, tono motivador, claro y cercano.\n"
        "- Usa lenguaje sencillo — el estudiante puede tener 12-17 años.\n"
        "- Cuando te den contexto del estudiante (notas, riesgo), úsalo activamente.\n"
        "- Ofrece consejos de estudio, explicaciones de materias ABP, ayuda con tareas.\n"
        "- Si el estudiante está en riesgo académico, motívalo y sugiere estrategias.\n"
        "- Puedes usar las herramientas disponibles para consultar datos del estudiante.\n"
        "- NUNca inventes notas o datos académicos — solo usa la información proporcionada.\n"
        "- Sé breve y directo en tus respuestas."
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

    @model_validator(mode="after")
    def ensure_message(self) -> "ChatRequest":
        if not self.message or not self.message.strip():
            self.message = "Consulta académica general"
        return self


in_memory_history: dict[str, list[dict[str, str]]] = OrderedDict()
rate_limit_store: dict[str, list[float]] = {}


def _check_rate_limit(user_id: str) -> None:
    now = time.time()
    window = 60.0
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


def _get_conversation_key(role: str, user_id: str) -> str:
    return f"{role}:{user_id}"


def _load_conversation(role: str, user_id: str) -> list[dict[str, str]]:
    key = _get_conversation_key(role, user_id)
    if key in in_memory_history:
        return in_memory_history[key]
    try:
        db = _get_db()
        result = db.table("conversations").select("messages").eq("user_id", user_id).eq("role", role).order("created_at", desc=True).limit(1).execute()
        if result.data:
            msgs = result.data[0].get("messages", [])
            in_memory_history[key] = msgs
            return msgs
    except Exception as e:
        logger.debug("db load error: %s", e)
    return []


def _save_conversation(role: str, user_id: str, messages: list[dict[str, str]]) -> None:
    key = _get_conversation_key(role, user_id)
    in_memory_history[key] = messages
    if len(in_memory_history) > 1000:
        in_memory_history.popitem(last=False)
    try:
        db = _get_db()
        existing = db.table("conversations").select("id").eq("user_id", user_id).eq("role", role).order("created_at", desc=True).limit(1).execute()
        now = datetime.now(timezone.utc).isoformat()
        doc = {"user_id": user_id, "role": role, "messages": messages, "updated_at": now}
        if existing.data:
            db.table("conversations").update(doc).eq("id", existing.data[0]["id"]).execute()
        else:
            doc["created_at"] = now
            db.table("conversations").insert(doc).execute()
    except Exception as e:
        logger.debug("db save error: %s", e)


def _get_available_for_role(role: str) -> list[dict[str, str]]:
    tools = [
        {
            "name": "get_student_grades_summary",
            "description": "Obtiene el promedio general y materias en riesgo de un estudiante",
            "parameters": {"student_id": {"type": "string", "description": "UUID del estudiante"}},
        },
        {
            "name": "get_financial_status",
            "description": "Obtiene el estado financiero de un estudiante (mora, saldo, override)",
            "parameters": {"student_id": {"type": "string", "description": "UUID del estudiante"}},
        },
        {
            "name": "get_risk_students",
            "description": "Lista estudiantes con promedio menor a 3.5 (En Riesgo)",
            "parameters": {},
        },
        {
            "name": "get_teacher_grade_count",
            "description": "Obtiene cantidad de calificaciones registradas por un docente",
            "parameters": {"teacher_id": {"type": "string", "description": "UUID del docente"}},
        },
        {
            "name": "get_subject_info",
            "description": "Obtiene información de una materia por nombre",
            "parameters": {"subject_name": {"type": "string", "description": "Nombre exacto de la materia"}},
        },
        {
            "name": "get_subject_materials",
            "description": "Obtiene materiales educativos y guías de una materia",
            "parameters": {"subject_name": {"type": "string", "description": "Nombre exacto de la materia"}, "grade": {"type": "string", "description": "Curso (ej: 11-A)"}},
        },
    ]
    if role == "admin":
        tools.append({
            "name": "get_admin_stats",
            "description": "Obtiene estadísticas generales del sistema (total estudiantes, mora, etc.)",
            "parameters": {},
        })
        tools.append({
            "name": "get_all_students_financial",
            "description": "Obtiene lista completa de estudiantes con su estado financiero",
            "parameters": {},
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
    risk_ids = {sid for sid, scores in score_map.items() if (sum(scores) / len(scores)) < 3.5}
    students = []
    for rid in list(risk_ids)[:20]:
        p = db.table("profiles").select("fullname, login_credential").eq("id", rid).execute()
        if p.data:
            avg = sum(score_map[rid]) / len(score_map[rid])
            students.append({
                "profile_id": rid,
                "fullname": p.data[0].get("fullname", ""),
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
    students = []
    for m in result.data:
        p = db.table("profiles").select("fullname, login_credential").eq("id", m.get("profile_id")).execute()
        name = p.data[0].get("fullname", "") if p.data else ""
        students.append({
            "profile_id": m.get("profile_id"),
            "fullname": name,
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


TOOL_FUNCTIONS = {
    "get_student_grades_summary": _tool_get_student_grades_summary,
    "get_financial_status": _tool_get_financial_status,
    "get_risk_students": _tool_get_risk_students,
    "get_teacher_grade_count": _tool_get_teacher_grade_count,
    "get_subject_info": _tool_get_subject_info,
    "get_admin_stats": _tool_get_admin_stats,
    "get_all_students_financial": _tool_get_all_students_financial,
    "get_subject_materials": _tool_get_subject_materials,
}


def _build_messages(role: str, user_message: str, context: str, user_id: str) -> list[dict[str, str]]:
    system_prompt = SYSTEM_PROMPTS.get(role, SYSTEM_PROMPTS["student"])
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if context:
        messages.append({"role": "system", "content": f"Datos del usuario:\n{context}"})
    history = _load_conversation(role, user_id)
    for msg in history[-MAX_HISTORY:]:
        messages.append(msg)
    messages.append({"role": "user", "content": user_message})
    return messages


def _build_payload(role: str, messages: list[dict[str, str]]) -> dict[str, Any]:
    config = ROLE_CONFIG.get(role, ROLE_CONFIG["student"])
    model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
        "max_tokens": config["max_tokens"],
        "temperature": config["temperature"],
    }
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


async def _call_openrouter(
    api_key: str,
    payload: dict[str, Any],
    headers: dict[str, str],
) -> httpx.Response:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(OPENROUTER_BASE, json=payload, headers=headers)
        return resp


async def _execute_tool_call(db: Client, tool_call: dict[str, Any], user_id: str) -> str:
    func_name = tool_call.get("function", {}).get("name", "")
    try:
        raw_args = tool_call.get("function", {}).get("arguments", "{}")
        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
    except json.JSONDecodeError:
        args = {}
    func = TOOL_FUNCTIONS.get(func_name)
    if not func:
        return json.dumps({"error": f"Función '{func_name}' no disponible"})
    try:
        result = await func(db, args, user_id)
        return result
    except Exception as e:
        logger.error("tool %s error: %s", func_name, e)
        return json.dumps({"error": f"Error al ejecutar {func_name}: {str(e)[:200]}"})


def _parse_tool_calls(choice: dict[str, Any]) -> list[dict[str, Any]]:
    delta = choice.get("delta", {})
    if "tool_calls" in delta:
        return delta["tool_calls"]
    if "message" in choice and "tool_calls" in choice["message"]:
        return choice["message"]["tool_calls"]
    return []


async def _stream_with_react(
    api_key: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    user_id: str,
    original_message: str,
    role: str,
) -> AsyncGenerator[str, None]:
    db = _get_db()
    full_assistant_text = ""
    iteration = 0
    current_messages = list(payload["messages"])

    while iteration < REACT_MAX_ITERATIONS:
        iteration += 1
        current_payload = dict(payload)
        current_payload["messages"] = current_messages
        current_payload["stream"] = True

        resp = await _call_openrouter(api_key, current_payload, headers)

        if resp.status_code != 200:
            error_text = await resp.aread()
            logger.error("OpenRouter error [%s] iter=%s status=%s: %s", role, iteration, resp.status_code, error_text.decode()[:300])
            if iteration == 1:
                yield f"data: {json.dumps({'error': f'Error del asistente (código {resp.status_code})'})}\n\n"
                yield "data: [DONE]\n\n"
            return

        assistant_content = ""
        tool_calls_buffer: dict[int, dict[str, Any]] = {}

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
                if iteration == 1:
                    full_assistant_text += token
                    yield f"data: {json.dumps({'token': token})}\n\n"

            finish_reason = choice.get("finish_reason")
            tc_raw = delta.get("tool_calls") or choice.get("message", {}).get("tool_calls")
            if tc_raw:
                for tc in tc_raw:
                    idx = tc.get("index", 0)
                    if idx not in tool_calls_buffer:
                        tool_calls_buffer[idx] = {"id": tc.get("id", f"call_{idx}"), "type": "function", "function": {"name": "", "arguments": ""}}
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
                current_messages.append({"role": "assistant", "content": assistant_content or None})
                tool_calls_list = list(tool_calls_buffer.values())
                current_messages[-1]["tool_calls"] = [
                    {"id": tc["id"], "type": "function", "function": tc["function"]}
                    for tc in tool_calls_list
                ]
                for tc in tool_calls_list:
                    tool_result = await _execute_tool_call(db, tc, user_id)
                    current_messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": tool_result,
                    })
                    logger.info("tool=%s user=%s result_len=%d", tc["function"]["name"], user_id, len(tool_result))
                break
        else:
            if iteration == 1 and not full_assistant_text and not assistant_content:
                yield f"data: {json.dumps({'token': '...'})}\n\n"
            break

        if not tool_calls_buffer:
            break

    yield "data: [DONE]\n\n"
    if full_assistant_text.strip():
        history = _load_conversation(role, user_id)
        history.append({"role": "user", "content": original_message})
        history.append({"role": "assistant", "content": full_assistant_text})
        while len(history) > MAX_HISTORY * 2:
            history.pop(0)
        _save_conversation(role, user_id, history)
        logger.info("saved conv role=%s user=%s msgs=%d", role, user_id, len(history))


async def _stream_simple(
    api_key: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    user_id: str,
    original_message: str,
    role: str,
) -> AsyncGenerator[str, None]:
    full_text = ""
    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream("POST", OPENROUTER_BASE, json=payload, headers=headers) as resp:
            if resp.status_code != 200:
                error_text = await resp.aread()
                logger.error("OpenRouter error [%s] user=%s status=%s: %s", role, user_id, resp.status_code, error_text.decode()[:500])
                yield f"data: {json.dumps({'error': f'Error del asistente (código {resp.status_code})'})}\n\n"
                yield "data: [DONE]\n\n"
                return
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        if full_text.strip():
                            history = _load_conversation(role, user_id)
                            history.append({"role": "user", "content": original_message})
                            history.append({"role": "assistant", "content": full_text})
                            while len(history) > MAX_HISTORY * 2:
                                history.pop(0)
                            _save_conversation(role, user_id, history)
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
                            yield f"data: {json.dumps({'token': content})}\n\n"
                    except json.JSONDecodeError:
                        continue


def _build_role_endpoint(role: str) -> str:
    return ROLE_ENDPOINT.get(role, ROLE_ENDPOINT["student"])


def _create_chat_handler(role: str):
    async def handler(req: ChatRequest, user_id: str) -> StreamingResponse:
        _check_rate_limit(user_id)
        api_key = _get_api_key(role)
        messages = _build_messages(role, req.message, req.context, user_id)
        payload = _build_payload(role, messages)
        headers = _build_headers(api_key)
        return StreamingResponse(
            _stream_with_react(api_key, payload, headers, user_id, req.message, role),
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
    key = _get_conversation_key(role, user_id)
    in_memory_history.pop(key, None)
    try:
        db = _get_db()
        existing = db.table("conversations").select("id").eq("user_id", user_id).eq("role", role).order("created_at", desc=True).limit(1).execute()
        if existing.data:
            db.table("conversations").update({"messages": []}).eq("id", existing.data[0]["id"]).execute()
    except Exception as e:
        logger.debug("clear_conversation db error: %s", e)
    return {"status": "cleared"}
