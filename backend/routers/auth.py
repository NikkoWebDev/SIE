import logging
from typing import Any

import bcrypt
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from dependencies import encode_jwt, get_db, TOKEN_EXPIRY_HOURS
from models import LoginRequest

logger = logging.getLogger("siee.auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])

FALLBACK_MODE: bool = False
FALLBACK_USERS: dict[str, dict[str, Any]] = {}

RECTOR_DOC_ID: str = "12345678"
RECTOR_NAME: str = "Rector Administrador"
RECTOR_PASS: str = "admin"


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


async def _hydrate_fallback(db: Any) -> None:
    global FALLBACK_MODE, FALLBACK_USERS
    try:
        count = await db["admins"].count_documents({})
    except Exception:
        count = 0

    if count == 0:
        FALLBACK_MODE = True
        base_claims = {
            RECTOR_DOC_ID: {
                "sub": RECTOR_DOC_ID,
                "role": "RECTOR",
                "fullname": RECTOR_NAME,
                "grade": "",
            },
        }
        hashed = _hash_password(RECTOR_PASS)
        FALLBACK_USERS = {
            k: {**v, "password_hash": hashed}
            for k, v in base_claims.items()
        }
        logger.warning("auth running in FALLBACK mode — seed admins collection")
    else:
        FALLBACK_MODE = False
        FALLBACK_USERS = {}
        logger.info("auth using live admins collection (%d docs)", count)


@router.post("/login")
async def login(data: LoginRequest) -> JSONResponse:
    db = get_db()
    doc_id = data.document_id.strip()
    plain_pw: str | None = None if data.password is None else str(data.password)

    if FALLBACK_MODE:
        fb = FALLBACK_USERS.get(doc_id)
        if fb is None:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        if plain_pw is not None and _verify_password(plain_pw, fb["password_hash"]):
            claims = {
                "sub": fb["sub"],
                "role": fb["role"],
                "fullname": fb["fullname"],
            }
            if fb.get("grade"):
                claims["grade"] = fb["grade"]
            token = encode_jwt(claims)
            return JSONResponse(content={
                "token": token,
                "expires_in_hours": TOKEN_EXPIRY_HOURS,
                "usuario": {
                    "rol": fb["role"],
                    "nombre": fb["fullname"],
                    "documento": doc_id,
                },
            })
        student = await db["students"].find_one({"document_id": doc_id})
        if student:
            claims = {
                "sub": doc_id,
                "role": "ESTUDIANTE",
                "fullname": student.get("fullname", ""),
                "grade": student.get("grade", ""),
            }
            token = encode_jwt(claims)
            return JSONResponse(content={
                "token": token,
                "expires_in_hours": TOKEN_EXPIRY_HOURS,
                "usuario": {
                    "rol": "ESTUDIANTE",
                    "nombre": student.get("fullname", ""),
                    "documento": doc_id,
                    "grado": student.get("grade", ""),
                    "is_paid": student.get("is_paid", True),
                },
            })
        raise HTTPException(status_code=404, detail="Usuario no registrado")

    if plain_pw is not None:
        admin = await db["admins"].find_one({"document_id": doc_id})
        if admin:
            hashed = str(admin.get("password", ""))
            if hashed.startswith("$2") or hashed.startswith("$argon"):
                ok = _verify_password(plain_pw, hashed)
            else:
                ok = plain_pw == hashed
            if ok:
                role = admin.get("role", "RECTOR")
                name = admin.get("fullname", "")
                claims: dict[str, Any] = {
                    "sub": doc_id,
                    "role": role,
                    "fullname": name,
                }
                assignment = await db["assignments"].find_one({"document_id": doc_id})
                if assignment:
                    claims["subject"] = assignment.get("subject", "")
                    claims["grade"] = assignment.get("grade", "")
                token = encode_jwt(claims)
                return JSONResponse(content={
                    "token": token,
                    "expires_in_hours": TOKEN_EXPIRY_HOURS,
                    "usuario": {
                        "rol": role,
                        "nombre": name,
                        "documento": doc_id,
                        **(
                            {"materia": claims.get("subject", ""), "grado": claims.get("grade", "")}
                            if role in ("PROFESOR", "RECTOR")
                            else {}
                        ),
                    },
                })
            raise HTTPException(status_code=401, detail="Credenciales inválidas")

        teacher = await db["teachers"].find_one({"document_id": doc_id})
        if teacher:
            hashed = str(teacher.get("password", ""))
            if hashed.startswith("$2") or hashed.startswith("$argon"):
                ok = _verify_password(plain_pw, hashed)
            else:
                ok = plain_pw == hashed
            if ok:
                claims: dict[str, Any] = {
                    "sub": doc_id,
                    "role": "PROFESOR",
                    "fullname": teacher.get("teacher_name", teacher.get("fullname", "")),
                }
                if teacher.get("subject"):
                    claims["subject"] = teacher.get("subject")
                if teacher.get("grade"):
                    claims["grade"] = teacher.get("grade")
                token = encode_jwt(claims)
                return JSONResponse(content={
                    "token": token,
                    "expires_in_hours": TOKEN_EXPIRY_HOURS,
                    "usuario": {
                        "rol": "PROFESOR",
                        "nombre": teacher.get("teacher_name", ""),
                        "documento": doc_id,
                        **(
                            {"materia": claims.get("subject", ""), "grado": claims.get("grade", "")}
                            if "subject" in claims
                            else {}
                        ),
                    },
                })
            raise HTTPException(status_code=401, detail="Credenciales inválidas")

    student = await db["students"].find_one({"document_id": doc_id})
    if student:
        claims: dict[str, Any] = {
            "sub": doc_id,
            "role": "ESTUDIANTE",
            "fullname": student.get("fullname", ""),
            "grade": student.get("grade", ""),
        }
        token = encode_jwt(claims)
        return JSONResponse(content={
            "token": token,
            "expires_in_hours": TOKEN_EXPIRY_HOURS,
            "usuario": {
                "rol": "ESTUDIANTE",
                "nombre": student.get("fullname", ""),
                "documento": doc_id,
                "grado": student.get("grade", ""),
                "is_paid": student.get("is_paid", True),
            },
        })

    raise HTTPException(status_code=404, detail="Usuario no registrado")
