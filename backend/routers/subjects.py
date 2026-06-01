import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from supabase import Client

from config.database import get_db
from dependencies import auth_dependency
from models import SubjectCreate, TeacherAssignment

logger = logging.getLogger("siee.subjects")
router = APIRouter(prefix="/api", tags=["subjects"])


@router.get("/subjects")
async def list_subjects(grade: Optional[str] = Query(None)) -> JSONResponse:
    db: Client = next(get_db())
    query = db.table("subjects").select("id, name, is_abp, grade, tutor_ai, planner_ai, description, created_at")
    if grade:
        query = query.eq("grade", grade)
    result = query.order("name").execute()
    return JSONResponse(content=result.data)


@router.post("/admin/subjects", status_code=201)
async def create_subject(data: SubjectCreate, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    db.table("subjects").insert(data.model_dump()).execute()
    return JSONResponse(content={"message": "Materia creada"}, status_code=201)


@router.delete("/admin/subjects/{subject_id}")
async def delete_subject(subject_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    db.table("subjects").delete().eq("id", subject_id).execute()
    return JSONResponse(content={"message": "Materia eliminada"})


@router.post("/admin/assign-teacher", status_code=201)
async def assign_teacher(data: TeacherAssignment, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    teacher_cred = data.document_id.strip()
    subject_name = data.subject

    teacher = db.table("profiles").select("id").eq("login_credential", teacher_cred).execute()
    if not teacher.data:
        raise HTTPException(status_code=404, detail="Docente no encontrado")
    teacher_id = teacher.data[0]["id"]

    subject = db.table("subjects").select("id").eq("name", subject_name).execute()
    if not subject.data:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    subject_id = subject.data[0]["id"]

    course = db.table("courses").select("id").eq("name", data.grade).execute()
    course_id = course.data[0]["id"] if course.data else None

    assignment = {"teacher_id": teacher_id, "subject_id": subject_id}
    if course_id:
        assignment["course_id"] = course_id
    db.table("teacher_assignments").insert(assignment).execute()

    return JSONResponse(content={"message": "Docente asignado"}, status_code=201)


@router.get("/admin/teachers")
async def list_teachers(user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("teacher_assignments").select("*, profiles!inner(fullname, login_credential), subjects!inner(name)").execute()
    teachers = []
    for t in result.data:
        teachers.append({
            "id": t.get("id"),
            "teacher_id": t.get("teacher_id"),
            "subject_id": t.get("subject_id"),
            "course_id": t.get("course_id"),
            "fullname": t.get("profiles", {}).get("fullname", ""),
            "subject_name": t.get("subjects", {}).get("name", ""),
        })
    return JSONResponse(content=teachers)


@router.delete("/admin/teachers/{assignment_id}")
async def delete_teacher(assignment_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    db.table("teacher_assignments").delete().eq("id", assignment_id).execute()
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

    db: Client = next(get_db())
    db.table("guides").insert({
        "grade": grade,
        "subject": subject,
        "filename": file.filename,
        "url": url,
    }).execute()
    return JSONResponse(content={"message": "Guía subida", "url": url}, status_code=201)


@router.get("/teacher/my-files/{grade}/{subject}")
async def get_teacher_files(grade: str, subject: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("guides").select("*").eq("grade", grade).eq("subject", subject).execute()
    files = [{"name": f.get("filename"), "url": f.get("url")} for f in result.data]
    return JSONResponse(content=files)


@router.get("/student/my-deliveries/{student_id}/{grade}/{subject}")
async def get_my_deliveries(
    student_id: str, grade: str, subject: str,
    user_id: str = Depends(auth_dependency),
) -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("deliveries").select("*").eq("student_id", student_id).eq("grade", grade).eq("subject", subject).order("created_at", desc=True).execute()
    files = [{"filename": d.get("filename"), "url": d.get("url"), "date": d.get("date", "")} for d in result.data]
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

    db: Client = next(get_db())
    db.table("deliveries").insert({
        "student_id": student_id,
        "grade": grade,
        "subject": subject,
        "filename": file.filename,
        "url": url,
        "date": datetime.now(timezone.utc).isoformat(),
    }).execute()
    return JSONResponse(content={"message": "Tarea subida", "url": url}, status_code=201)


@router.get("/teacher/view-deliveries/{grade}/{subject}")
async def view_deliveries(grade: str, subject: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("deliveries").select("*").eq("grade", grade).eq("subject", subject).execute()
    deliveries = [{
        "student_id": d.get("student_id"),
        "filename": d.get("filename"),
        "url": d.get("url"),
        "date": d.get("date", ""),
    } for d in result.data]
    return JSONResponse(content=deliveries)


@router.get("/student/deliveries/{student_id}")
async def get_student_deliveries(student_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db: Client = next(get_db())
    result = db.table("deliveries").select("*").eq("student_id", student_id).order("created_at", desc=True).limit(30).execute()
    deliveries = [{
        "student_id": d.get("student_id"),
        "grade": d.get("grade"),
        "subject": d.get("subject"),
        "filename": d.get("filename"),
        "url": d.get("url"),
        "date": d.get("date", ""),
    } for d in result.data]
    return JSONResponse(content=deliveries)
