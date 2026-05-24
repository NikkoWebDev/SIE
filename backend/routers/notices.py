import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from dependencies import auth_dependency, get_db

logger = logging.getLogger("siee.notices")
router = APIRouter(prefix="/api", tags=["notices"])


@router.get("/notices")
async def list_notices(
    categoria: Optional[str] = None,
    limit: int = 50,
) -> JSONResponse:
    db = get_db()
    query: dict[str, Any] = {}
    if categoria:
        query["categoria"] = categoria
    notices: list[dict[str, Any]] = []
    async for n in db["notices"].find(query).sort("_id", -1).limit(limit):
        n["_id"] = str(n["_id"])
        notices.append(n)
    return JSONResponse(content=notices)


@router.get("/notices/{notice_id}")
async def get_notice(notice_id: str) -> JSONResponse:
    db = get_db()
    from bson import ObjectId
    try:
        n = await db["notices"].find_one({"_id": ObjectId(notice_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")
    if not n:
        raise HTTPException(status_code=404, detail="Aviso no encontrado")
    n["_id"] = str(n["_id"])
    return JSONResponse(content=n)


@router.post("/admin/notices", status_code=201)
async def create_notice(
    titulo: str = Form(..., min_length=1),
    contenido: str = Form(..., min_length=1),
    categoria: str = Form(default="General"),
    file: Optional[UploadFile] = File(None),
    user_id: str = Depends(auth_dependency),
) -> JSONResponse:
    db = get_db()
    archivo_url: Optional[str] = None
    if file:
        try:
            import cloudinary
            import cloudinary.uploader
            result = cloudinary.uploader.upload(
                file.file, folder="avisos", resource_type="auto",
            )
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
    result = await db["notices"].insert_one(doc)
    return JSONResponse(content={"message": "Aviso publicado", "id": str(result.inserted_id)}, status_code=201)


@router.put("/admin/notices/{notice_id}")
async def update_notice(
    notice_id: str,
    titulo: str = Form(None),
    contenido: str = Form(None),
    categoria: str = Form(None),
    user_id: str = Depends(auth_dependency),
) -> JSONResponse:
    db = get_db()
    from bson import ObjectId
    update: dict[str, Any] = {"fecha": datetime.now(timezone.utc).isoformat()}
    if titulo:
        update["titulo"] = titulo
    if contenido:
        update["contenido"] = contenido
    if categoria:
        update["categoria"] = categoria
    try:
        result = await db["notices"].update_one(
            {"_id": ObjectId(notice_id)},
            {"$set": update},
        )
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Aviso no encontrado")
    return JSONResponse(content={"message": "Aviso actualizado"})


@router.delete("/admin/notices/{notice_id}")
async def delete_notice(notice_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    from bson import ObjectId
    try:
        result = await db["notices"].delete_one({"_id": ObjectId(notice_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Aviso no encontrado")
    return JSONResponse(content={"message": "Aviso eliminado"})
