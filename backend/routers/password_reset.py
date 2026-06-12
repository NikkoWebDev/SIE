import logging
import secrets
import string
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from supabase import Client

from config.database import get_db

logger = logging.getLogger("siee.password_reset")
router = APIRouter(prefix="/api/auth", tags=["auth"])

RESET_CODE_LENGTH = 6
RESET_CODE_TTL_MINUTES = 15


class ForgotPasswordRequest(BaseModel):
    login_credential: str = Field(..., min_length=1)
    model_config = {"extra": "forbid"}


class ResetPasswordRequest(BaseModel):
    login_credential: str = Field(..., min_length=1)
    code: str = Field(..., min_length=RESET_CODE_LENGTH, max_length=RESET_CODE_LENGTH)
    new_password: str = Field(..., min_length=4, max_length=128)
    model_config = {"extra": "forbid"}


def _generate_reset_code(length: int = RESET_CODE_LENGTH) -> str:
    return "".join(secrets.choice(string.digits) for _ in range(length))


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest) -> JSONResponse:
    db: Client = next(get_db())

    profile = db.table("profiles").select("id, login_credential, fullname, email").eq("login_credential", data.login_credential).execute()
    if not profile.data:
        logger.info("forgot-password: unknown credential=%s", data.login_credential)
        return JSONResponse(content={"message": "Si el usuario existe, recibirás un código de recuperación."})

    prof = profile.data[0]
    profile_id = prof["id"]

    existing = db.table("password_reset_codes").select("*").eq("profile_id", profile_id).eq("used", False).execute()
    if existing.data:
        for old in existing.data:
            db.table("password_reset_codes").update({"used": True}).eq("id", old["id"]).execute()

    code = _generate_reset_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_CODE_TTL_MINUTES)

    db.table("password_reset_codes").insert({
        "profile_id": profile_id,
        "login_credential": data.login_credential,
        "code": code,
        "expires_at": expires_at.isoformat(),
    }).execute()

    logger.info("reset code generated for credential=%s (expires %s) code=%s", data.login_credential, expires_at.isoformat(), code)
    try:
        email = prof.get("email")
        nombre = prof.get("fullname", "Usuario")
        if email:
            logger.info("[EMAIL PLACEHOLDER] Enviando código a %s: Código=%s para %s", email, code, nombre)
    except Exception as e:
        logger.warning("failed to prepare delivery for %s: %s", data.login_credential, e)

    return JSONResponse(content={
        "message": "Si el usuario existe, recibirás un código de recuperación.",
    })


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest) -> JSONResponse:
    db: Client = next(get_db())

    now = datetime.now(timezone.utc)
    result = db.table("password_reset_codes").select("*").eq("login_credential", data.login_credential).eq("code", data.code).eq("used", False).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Código inválido o ya utilizado.")

    reset_record = result.data[0]
    expires = reset_record.get("expires_at")
    if expires:
        expires_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        if now > expires_dt:
            raise HTTPException(status_code=400, detail="El código ha expirado. Solicita uno nuevo.")

    hashed = bcrypt.hashpw(data.new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    db.table("profiles").update({"password_hash": hashed}).eq("id", reset_record["profile_id"]).execute()

    db.table("password_reset_codes").update({"used": True}).eq("id", reset_record["id"]).execute()

    logger.info("password reset successful for profile=%s", reset_record["profile_id"])
    return JSONResponse(content={"message": "Contraseña actualizada exitosamente."})
