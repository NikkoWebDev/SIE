import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from supabase import Client

from config.database import get_db
from dependencies import auth_dependency

logger = logging.getLogger("siee.notices")
router = APIRouter(prefix="/api", tags=["notices"])


@router.get("/notices")
async def list_notices(
    categoria: Optional[str] = None,
    limit: int = 50,
) -> JSONResponse:
    db: Client = next(get_db())
    query = db.table("notices").select("*")
    if categoria:
        query = query.eq("categoria", categoria)
    result = query.order("created_at", desc=True).limit(limit).execute()
    return JSONResponse(content=result.data)


@router.get("/notices/{notice_id}")
async def get_notice(notice_id: str) -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("notices").select("*").eq("id", notice_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Aviso no encontrado")
    return JSONResponse(content=result.data[0])


@router.post("/admin/notices", status_code=201)
async def create_notice(
    titulo: str = Form(..., min_length=1),
    contenido: str = Form(..., min_length=1),
    categoria: str = Form(default="General"),
    file: Optional[UploadFile] = File(None),
    user_id: str = Depends(auth_dependency),
) -> JSONResponse:
    db: Client = next(get_db())
    archivo_url: Optional[str] = None
    if file:
        try:
            import cloudinary
            import cloudinary.uploader
            result = cloudinary.uploader.upload(file.file, folder="avisos", resource_type="auto")
            archivo_url = result.get("secure_url")
        except Exception as exc:
            logger.warning("cloudinary upload failed: %s", exc)

    doc = {
        "titulo": titulo,
        "contenido": contenido,
        "categoria": categoria,
        "archivo_url": archivo_url,
        "fecha": datetime.now(timezone.utc).isoformat(),
    }
    result = db.table("notices").insert(doc).execute()
    return JSONResponse(content={"message": "Aviso publicado", "id": result.data[0]["id"]}, status_code=201)


@router.put("/admin/notices/{notice_id}")
async def update_notice(
    notice_id: str,
    titulo: str = Form(None),
    contenido: str = Form(None),
    categoria: str = Form(None),
    user_id: str = Depends(auth_dependency),
) -> JSONResponse:
    db: Client = next(get_db())
    update: dict[str, Any] = {"fecha": datetime.now(timezone.utc).isoformat()}
    if titulo:
        update["titulo"] = titulo
    if contenido:
        update["contenido"] = contenido
    if categoria:
        update["categoria"] = categoria

    result = db.table("notices").update(update).eq("id", notice_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Aviso no encontrado")
    return JSONResponse(content={"message": "Aviso actualizado"})


@router.delete("/admin/notices/{notice_id}")
async def delete_notice(notice_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("notices").delete().eq("id", notice_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Aviso no encontrado")
    return JSONResponse(content={"message": "Aviso eliminado"})
