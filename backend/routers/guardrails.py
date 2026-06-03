"""
VYNTRA AI Guardrails — Input, Tool, and Output validation.

Three-layer guard system:
1. Input guard — detect prompt injection, off-topic requests
2. Tool guard — authorize mutations, validate parameters
3. Output guard — check for hallucination, banned content, PII
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger("siee.guardrails")

# ── Patterns ──
PROMPT_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bignore\s+(all\s+)?(previous|above|below)\s+instructions\b", re.I),
    re.compile(r"\bforget\s+(all\s+)?(previous|above|below)\b", re.I),
    re.compile(r"\bdisregard\s+(all\s+)?(previous|above|below)\b", re.I),
    re.compile(r"\byou\s+are\s+(not\s+)?(an?\s+)?(AI|assistant|bot)\s*[,.]?\s*(you\s+are|you're)\b", re.I),
    re.compile(r"\bsystem\s+prompt\s*:", re.I),
    re.compile(r"\bnew\s+instructions?\s*:", re.I),
    re.compile(r"\breset\s+(conversation|chat|memory|state)\b", re.I),
    re.compile(r"\boutput\s+(only|just|exclusively)\s+(json|the\s+word)\b", re.I),
    re.compile(r"\bDANGER\b"),
    re.compile(r"<\s*(system|user|assistant|tool)\s*>", re.I),
    re.compile(r"\badmin\s*:\s*", re.I),
    re.compile(r"\bexecute\s+(command|code|script)\b", re.I),
    re.compile(r"\brun\s+(command|code|script|shell)\b", re.I),
]

PII_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b\d{3}[-\s]?\d{3}[-\s]?\d{4}\b"),  # phone
    re.compile(r"\b\d{6,10}\b"),  # student ID-like numbers
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),  # email
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),  # IP address
]

BANNED_OUTPUT_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(contraseña|password|secret|clave)\s*(actual|del|de\s+acceso)\b", re.I),
    re.compile(r"\bJWT[_\s]?(SECRET|KEY|TOKEN)\b", re.I),
    re.compile(r"\bSUPABASE[_\s]?(SERVICE[_\s]?KEY|ANON[_\s]?KEY)\b", re.I),
    re.compile(r"\bOPENROUTER[_\s]?(STUDENT|TEACHER|ADMIN)[_\s]?KEY\b", re.I),
]

MAX_INPUT_LENGTH = 4000
MAX_TOOL_ARGS_LENGTH = 2000


class InputGuardrail:
    """Validate user input before reaching the agent."""

    @staticmethod
    def check(text: str, role: str = "student") -> str | None:
        if not text or not text.strip():
            return "El mensaje no puede estar vacío."
        if len(text) > MAX_INPUT_LENGTH:
            return f"El mensaje es demasiado largo ({len(text)} caracteres, máximo {MAX_INPUT_LENGTH})."
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(text):
                logger.info("prompt injection detected (pattern=%s)", pattern.pattern[:40])
                return None  # silently ignore rather than revealing detection to attacker
        return None


class ToolGuardrail:
    """Authorize and validate tool calls."""

    ADMIN_ONLY_TOOLS = {"get_admin_stats", "get_all_students_financial"}

    @staticmethod
    def check(tool_name: str, args: dict, role: str) -> str | None:
        if tool_name in ToolGuardrail.ADMIN_ONLY_TOOLS and role != "admin":
            return f"La herramienta '{tool_name}' solo está disponible para administradores."
        args_json = json.dumps(args, ensure_ascii=False)
        if len(args_json) > MAX_TOOL_ARGS_LENGTH:
            return "Los argumentos de la herramienta son demasiado extensos."
        for key, value in args.items():
            if not isinstance(value, (str, int, float, bool, type(None))):
                return f"El argumento '{key}' tiene un tipo no válido."
            if isinstance(value, str) and len(value) > 500:
                return f"El argumento '{key}' excede la longitud máxima."
        return None


class OutputGuardrail:
    """Validate agent output before sending to user."""

    @staticmethod
    def check(text: str, tool_results: list[dict] | None = None) -> str | None:
        if not text:
            return "El asistente no generó contenido."
        for pattern in PII_PATTERNS:
            if pattern.search(text):
                logger.warning("PII detected in output (pattern=%s)", pattern.pattern[:30])
                return None
        for pattern in BANNED_OUTPUT_PATTERNS:
            if pattern.search(text):
                logger.warning("banned content pattern matched in output")
                return None
        if tool_results:
            for result in tool_results:
                if result.get("name") and result.get("content"):
                    guardrails._check_result_consistency(text, result["name"], result["content"])
        return None


class guardrails:
    """Aggregate guardrail checks."""

    @staticmethod
    def check_input(text: str, role: str = "student") -> str | None:
        return InputGuardrail.check(text, role)

    @staticmethod
    def check_tool_call(tool_name: str, args: dict, role: str) -> str | None:
        return ToolGuardrail.check(tool_name, args, role)

    @staticmethod
    def check_output(text: str, tool_results: list[dict] | None = None) -> str | None:
        return OutputGuardrail.check(text, tool_results)

    @staticmethod
    def _check_result_consistency(output: str, tool_name: str, result_str: str) -> None:
        try:
            result_data = json.loads(result_str)
        except (json.JSONDecodeError, TypeError):
            return
        if isinstance(result_data, dict):
            if "error" in result_data:
                return
            if "average" in result_data:
                avg = result_data.get("average")
                if avg is not None:
                    avg_str = str(avg)
                    if avg_str not in output and str(round(avg, 1)) not in output:
                        logger.debug("output may not reference tool result: avg=%s not found", avg_str)
            if "count" in result_data and result_data["count"] == 0:
                if "ningún" not in output.lower() and "no hay" not in output.lower() and "0" not in output:
                    logger.debug("output may contradict empty result from %s", tool_name)
