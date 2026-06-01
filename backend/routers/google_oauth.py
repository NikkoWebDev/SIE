import logging
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from supabase import Client

from config.database import get_db
from dependencies import TOKEN_EXPIRY_HOURS, encode_jwt

logger = logging.getLogger("siee.google_oauth")
router = APIRouter(prefix="/api/auth", tags=["auth"])


class GoogleAuthRequest(BaseModel):
    credential: str = Field(..., min_length=1)
    model_config = {"extra": "forbid"}


@router.post("/google")
async def google_auth(data: GoogleAuthRequest) -> JSONResponse:
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    if not GOOGLE_CLIENT_ID:
        logger.error("GOOGLE_CLIENT_ID not configured on server")
        raise HTTPException(status_code=500, detail="Google OAuth no está configurado.")

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        idinfo = id_token.verify_oauth2_token(
            data.credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except ValueError as e:
        logger.warning("Google token verification failed: %s", e)
        raise HTTPException(status_code=401, detail="Token de Google inválido.")

    email = idinfo.get("email", "")
    if not email:
        raise HTTPException(status_code=400, detail="El token de Google no contiene un email.")

    db: Client = next(get_db())
    profile = db.table("profiles").select("*").eq("email", email).execute()
    if not profile.data:
        profile = db.table("profiles").select("*").eq("login_credential", email).execute()

    if not profile.data:
        logger.info("google auth: no profile found for email=%s", email)
        raise HTTPException(status_code=404, detail="No hay una cuenta asociada a este email. Contacta a administración.")

    prof = profile.data[0]
    role = prof.get("role", "student")

    if prof.get("supabase_auth_id") is None:
        db.table("profiles").update({"supabase_auth_id": idinfo.get("sub", "")}).eq("id", prof["id"]).execute()

    if not prof.get("email"):
        db.table("profiles").update({"email": email}).eq("id", prof["id"]).execute()

    claims = {
        "sub": prof["id"],
        "login_credential": prof["login_credential"],
        "role": role,
        "fullname": prof["fullname"],
    }
    token = encode_jwt(claims)

    return JSONResponse(content={
        "access_token": token,
        "token_type": "bearer",
        "expires_in_hours": TOKEN_EXPIRY_HOURS,
        "usuario": {
            "profile_id": prof["id"],
            "login_credential": prof["login_credential"],
            "rol": role,
            "nombre": prof["fullname"],
        },
    })
