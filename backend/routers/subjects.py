import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from dependencies import auth_dependency, get_db

logger = logging.getLogger("siee.subjects")
router = APIRouter(prefix="/api", tags=["subjects"])


@router.get("/subjects")
async def list_subjects(grade: Optional[str] = Query(None)) -> JSONResponse:
    db = get_db()
    query: dict[str, Any] = {}
    if grade:
        query["grade"] = grade
    subjects: list[dict[str, Any]] = []
    async for s in db["subjects"].find(query):
        subjects.append({
            "name": s.get("name"),
            "grade": s.get("grade"),
            "gem_tutor_url": s.get("gem_tutor_url", ""),
            "gem_planner_url": s.get("gem_planner_url", ""),
        })
    return JSONResponse(content=subjects)


@router.post("/admin/subjects", status_code=201)
async def create_subject(data: dict[str, Any], user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    await db["subjects"].insert_one({
        "name": data.get("name"),
        "grade": data.get("grade"),
        "gem_tutor_url": data.get("gem_tutor_url", ""),
        "gem_planner_url": data.get("gem_planner_url", ""),
    })
    return JSONResponse(content={"message": "Materia creada"}, status_code=201)


@router.delete("/admin/subjects/{name}")
async def delete_subject(name: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    await db["subjects"].delete_one({"name": name})
    return JSONResponse(content={"message": "Materia eliminada"})


@router.post("/admin/assign-teacher", status_code=201)
async def assign_teacher(data: dict[str, Any], user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    doc_id = data.get("document_id", "").strip()
    teacher = {
        "_id": doc_id,
        "document_id": doc_id,
        "fullname": data.get("fullname", data.get("teacher_name", "")),
        "password": data.get("password", ""),
        "role": "PROFESOR",
    }
    await db["admins"].update_one({"document_id": doc_id}, {"$set": teacher}, upsert=True)
    assignment = {
        "document_id": doc_id,
        "teacher_name": data.get("fullname", data.get("teacher_name", "")),
        "subject": data.get("subject", ""),
        "grade": data.get("grade", ""),
    }
    await db["assignments"].insert_one(assignment)
    return JSONResponse(content={"message": "Docente asignado"}, status_code=201)


@router.get("/admin/teachers")
async def list_teachers(user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    teachers: list[dict[str, Any]] = []
    async for t in db["assignments"].find():
        t["_id"] = str(t.get("_id", ""))
        teachers.append(t)
    return JSONResponse(content=teachers)


@router.delete("/admin/teachers/{teacher_id}")
async def delete_teacher(teacher_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    from bson import ObjectId
    try:
        await db["assignments"].delete_one({"_id": ObjectId(teacher_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")
    return JSONResponse(content={"message": "Asignación eliminada"})


@router.post("/admin/upload-guide", status_code=201)
async def upload_guide(
    grade: str = Form(...),
    subject: str = Form(...),
    file: UploadFile = File(...),
    user_id: str = Depends(auth_dependency),
) -> JSONResponse:
    try:
        import cloudinary
        import cloudinary.uploader
        result = cloudinary.uploader.upload(
            file.file,
            folder=f"guias/{grade}/{subject}",
            resource_type="auto",
        )
        url = result.get("secure_url")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    db = get_db()
    await db["guides"].insert_one({
        "grade": grade,
        "subject": subject,
        "filename": file.filename,
        "url": url,
    })
    return JSONResponse(content={"message": "Guía subida", "url": url}, status_code=201)


@router.get("/teacher/my-files/{grade}/{subject}")
async def get_teacher_files(grade: str, subject: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    files: list[dict[str, Any]] = []
    async for f in db["guides"].find({"grade": grade, "subject": subject}):
        files.append({"name": f.get("filename"), "url": f.get("url")})
    return JSONResponse(content=files)


@router.get("/student/my-deliveries/{student_id}/{grade}/{subject}")
async def get_my_deliveries(student_id: str, grade: str, subject: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    files: list[dict[str, Any]] = []
    async for d in db["deliveries"].find({"student_id": student_id, "grade": grade, "subject": subject}).sort("_id", -1):
        files.append({"filename": d.get("filename"), "url": d.get("url"), "date": d.get("date", "")})
    return JSONResponse(content=files)


@router.post("/student/upload-homework", status_code=201)
async def upload_homework(
    student_id: str = Form(...),
    grade: str = Form(...),
    subject: str = Form(...),
    file: UploadFile = File(...),
    user_id: str = Depends(auth_dependency),
) -> JSONResponse:
    try:
        import cloudinary
        import cloudinary.uploader
        result = cloudinary.uploader.upload(
            file.file,
            folder=f"tareas/{grade}/{subject}",
            public_id=f"{student_id}_{file.filename.split('.')[0]}",
            resource_type="auto",
        )
        url = result.get("secure_url")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    db = get_db()
    await db["deliveries"].insert_one({
        "student_id": student_id,
        "grade": grade,
        "subject": subject,
        "filename": file.filename,
        "url": url,
        "date": datetime.now(timezone.utc).isoformat(),
    })
    return JSONResponse(content={"message": "Tarea subida", "url": url}, status_code=201)


@router.get("/teacher/view-deliveries/{grade}/{subject}")
async def view_deliveries(grade: str, subject: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    deliveries: list[dict[str, Any]] = []
    async for d in db["deliveries"].find({"grade": grade, "subject": subject}):
        deliveries.append({
            "student_id": d.get("student_id"),
            "filename": d.get("filename"),
            "url": d.get("url"),
            "date": d.get("date", ""),
        })
    return JSONResponse(content=deliveries)


@router.get("/student/deliveries/{student_id}")
async def get_student_deliveries(student_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    deliveries: list[dict[str, Any]] = []
    async for d in db["deliveries"].find({"student_id": student_id}).sort("_id", -1).limit(30):
        deliveries.append({
            "student_id": d.get("student_id"),
            "grade": d.get("grade"),
            "subject": d.get("subject"),
            "filename": d.get("filename"),
            "url": d.get("url"),
            "date": d.get("date", ""),
        })
    return JSONResponse(content=deliveries)
