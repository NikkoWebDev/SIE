import logging
from typing import Any

import bcrypt
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from supabase import Client

from config.database import get_db
from dependencies import encode_jwt, TOKEN_EXPIRY_HOURS
from models import LoginRequest, UserCreate, UserLogin

logger = logging.getLogger("siee.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _safe_query(db: Client, **kwargs):
    try:
        return kwargs["action"]().execute()
    except Exception as e:
        err = str(e)
        if "42501" in err or "permission denied" in err.lower():
            raise HTTPException(
                status_code=503,
                detail="Base de datos no inicializada — ejecuta seed.sql en Supabase Dashboard"
            )
        if "does not exist" in err.lower():
            raise HTTPException(
                status_code=503,
                detail="Base de datos no inicializada — ejecuta seed.sql en Supabase Dashboard"
            )
        raise


@router.post("/register", status_code=201)
async def register(data: UserCreate) -> JSONResponse:
    db: Client = next(get_db())
    res = _safe_query(
        db,
        action=lambda: db.table("profiles")
            .select("*")
            .eq("login_credential", data.login_credential)
    )
    if res.data:
        raise HTTPException(status_code=409, detail="Usuario ya existe")

    hashed = _hash_password(data.password)
    result = db.table("profiles").insert({
        "login_credential": data.login_credential,
        "fullname": data.fullname,
        "password_hash": hashed,
        "role": data.role.value,
        "is_active": True,
    }).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Error al crear usuario")
    profile = result.data[0]
    return JSONResponse(status_code=201, content={
        "profile_id": profile["id"],
        "login_credential": profile["login_credential"],
        "fullname": profile["fullname"],
        "role": profile["role"],
    })


@router.post("/login")
async def login(data: UserLogin) -> JSONResponse:
    db: Client = next(get_db())
    res = _safe_query(
        db,
        action=lambda: db.table("profiles")
            .select("*")
            .eq("login_credential", data.login_credential)
    )
    if not res.data:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    profile = res.data[0]
    if not profile.get("is_active", True):
        raise HTTPException(status_code=403, detail="Usuario desactivado")

    stored_hash = profile.get("password_hash", "")
    if not stored_hash or not _verify_password(data.password, stored_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    claims: dict[str, Any] = {
        "sub": profile["id"],
        "login_credential": profile["login_credential"],
        "role": profile["role"],
        "fullname": profile["fullname"],
    }
    token = encode_jwt(claims)

    return JSONResponse(content={
        "access_token": token,
        "token_type": "bearer",
        "expires_in_hours": TOKEN_EXPIRY_HOURS,
        "usuario": {
            "profile_id": profile["id"],
            "login_credential": profile["login_credential"],
            "rol": profile["role"],
            "nombre": profile["fullname"],
        },
    })


@router.post("/login-legacy")
async def login_legacy(data: LoginRequest) -> JSONResponse:
    db: Client = next(get_db())
    res = _safe_query(
        db,
        action=lambda: db.table("profiles")
            .select("*")
            .eq("login_credential", data.document_id)
    )
    if not res.data:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    profile = res.data[0]
    stored_hash = profile.get("password_hash", "")
    if data.password and stored_hash and _verify_password(data.password, stored_hash):
        claims: dict[str, Any] = {
            "sub": profile["id"],
            "login_credential": profile["login_credential"],
            "role": profile["role"],
            "fullname": profile["fullname"],
        }
        token = encode_jwt(claims)
        return JSONResponse(content={
            "token": token,
            "expires_in_hours": TOKEN_EXPIRY_HOURS,
            "usuario": {
                "profile_id": profile["id"],
                "rol": profile["role"],
                "nombre": profile["fullname"],
                "documento": data.document_id,
            },
        })

    raise HTTPException(status_code=401, detail="Credenciales inválidas")
