from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from dependencies import encode_jwt, get_db
from models import LoginRequest

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login")
async def login(data: LoginRequest) -> JSONResponse:
    db = get_db()
    doc_id = data.documento.strip()

    admin = await db["admins"].find_one({"document_id": doc_id})
    if admin:
        stored_pw = str(admin.get("password", ""))
        if data.contraseña and str(data.contraseña) == stored_pw:
            role = admin.get("role", "PROFESOR")
            name = admin.get("fullname", "")
            claims: dict[str, Any] = {
                "sub": doc_id,
                "role": role,
                "fullname": name,
            }
            if role in ("PROFESOR", "RECTOR"):
                assignment = await db["assignments"].find_one({"document_id": doc_id})
                if assignment:
                    claims["subject"] = assignment.get("subject", "")
                    claims["grade"] = assignment.get("grade", "")
            token = encode_jwt(claims)
            return JSONResponse(content={
                "token": token,
                "usuario": {
                    "rol": role,
                    "nombre": name,
                    "documento": doc_id,
                    **({"materia": claims.get("subject", ""), "grado": claims.get("grade", "")} if role in ("PROFESOR", "RECTOR") else {}),
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
            "usuario": {
                "rol": "ESTUDIANTE",
                "nombre": student.get("fullname", ""),
                "documento": doc_id,
                "grado": student.get("grade", ""),
                "is_paid": student.get("is_paid", True),
            },
        })

    raise HTTPException(status_code=404, detail="Usuario no registrado")
