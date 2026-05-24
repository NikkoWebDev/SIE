from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from dependencies import auth_dependency, financial_guard, get_db, is_financial_locked_path
from models import PaymentToggle, StudentCreate, StudentUpdate

router = APIRouter(prefix="/api", tags=["students"])


@router.get("/students")
async def list_students(request: Request, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    grade = request.query_params.get("grade")
    query: dict[str, Any] = {}
    if grade:
        query["grade"] = grade
    students: list[dict[str, Any]] = []
    async for s in db["students"].find(query).sort("fullname", 1):
        s["_id"] = s.get("document_id", str(s.get("_id", "")))
        students.append(s)
    return JSONResponse(content=students)


@router.get("/students/{student_id}")
async def get_student(student_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    student = await db["students"].find_one({"document_id": student_id})
    if not student:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    student["_id"] = student.get("document_id", str(student.get("_id", "")))
    return JSONResponse(content=student)


@router.get("/students/{student_id}/grades")
async def get_student_grades(student_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    cursor = db["grades"].find({"student_id": student_id}).sort("created_at", -1)
    grades: list[dict[str, Any]] = []
    async for g in cursor:
        grades.append({
            "subject_id": g.get("subject_id"),
            "project_id": g.get("project_id"),
            "score": g.get("score"),
            "observations": g.get("observations", ""),
            "created_at": str(g.get("created_at", "")),
        })
    return JSONResponse(content=grades)


@router.get("/students/{student_id}/report")
async def get_student_report(student_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    if is_financial_locked_path("/api/students/report"):
        req = type("_R", (), {"query_params": {"student_id": student_id}})()
        await financial_guard(req)
    student = await db["students"].find_one({"document_id": student_id})
    if not student:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    cursor = db["grades"].find({"student_id": student_id}).sort("created_at", -1)
    grades: list[dict[str, Any]] = []
    async for g in cursor:
        grades.append({
            "subject_id": g.get("subject_id"),
            "project_id": g.get("project_id"),
            "score": g.get("score"),
            "observations": g.get("observations", ""),
            "created_at": str(g.get("created_at", "")),
        })
    from models import grade_status
    avg_score = sum(g["score"] for g in grades) / len(grades) if grades else 0.0
    return JSONResponse(content={
        "student": student.get("fullname"),
        "grade": student.get("grade"),
        "is_paid": student.get("is_paid", True),
        "promedio": round(avg_score, 1),
        "estado": grade_status(avg_score),
        "grades": grades,
    })


@router.post("/admin/students", status_code=201)
async def create_student(data: StudentCreate, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    doc = data.model_dump()
    doc["_id"] = data.document_id
    await db["students"].update_one(
        {"document_id": data.document_id},
        {"$set": doc},
        upsert=True,
    )
    return JSONResponse(content={"message": "Estudiante guardado"}, status_code=201)


@router.put("/admin/students/{student_id}")
async def update_student(student_id: str, data: StudentUpdate, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db["students"].update_one(
        {"document_id": student_id},
        {"$set": update},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return JSONResponse(content={"message": "Estudiante actualizado"})


@router.post("/admin/students/{student_id}/toggle-payment")
async def toggle_payment(student_id: str, data: PaymentToggle, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    await db["students"].update_one(
        {"document_id": student_id},
        {"$set": {"is_paid": data.is_paid}},
    )
    return JSONResponse(content={"message": "Pago actualizado"})


@router.delete("/admin/students/{student_id}")
async def delete_student(student_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    result = await db["students"].delete_one({"document_id": student_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return JSONResponse(content={"message": "Estudiante eliminado"})
