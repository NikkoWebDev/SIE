import logging
from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from dependencies import auth_dependency, financial_guard, get_db
from models import CandidateCreate, VoteRequest

logger = logging.getLogger("siee.admin")
router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats")
async def admin_stats(user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    total_students = await db["students"].count_documents({})
    mora = await db["students"].count_documents({"is_paid": False})
    at_risk = await db["students"].count_documents({"is_at_risk": True})
    total_teachers = await db["admins"].count_documents({"role": "PROFESOR"})
    total_notices = await db["notices"].count_documents({})
    total_exams = await db["exams"].count_documents({})
    total_grades = await db["grades"].count_documents({})
    pipeline = [
        {"$group": {"_id": None, "avg": {"$avg": "$score"}}},
    ]
    avg_cursor = db["grades"].aggregate(pipeline)
    avg_list = await avg_cursor.to_list(length=1)
    promedio = round(avg_list[0]["avg"], 1) if avg_list else 0.0

    return JSONResponse(content={
        "total_students": total_students,
        "mora": mora,
        "at_risk": at_risk,
        "total_teachers": total_teachers,
        "total_notices": total_notices,
        "total_exams": total_exams,
        "total_grades": total_grades,
        "promedio_general": promedio,
    })


@router.get("/mora-students")
async def mora_students(user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    students: list[dict[str, Any]] = []
    async for s in db["students"].find({"is_paid": False}).sort("fullname", 1):
        students.append({
            "document_id": s.get("document_id"),
            "fullname": s.get("fullname"),
            "grade": s.get("grade"),
        })
    return JSONResponse(content=students)


@router.get("/at-risk-students")
async def risk_students(user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    students: list[dict[str, Any]] = []
    async for s in db["students"].find({"is_at_risk": True}).sort("fullname", 1):
        students.append({
            "document_id": s.get("document_id"),
            "fullname": s.get("fullname"),
            "grade": s.get("grade"),
        })
    return JSONResponse(content=students)


@router.post("/candidates", status_code=201)
async def add_candidate(
    name: str = Form(...),
    position: str = Form(...),
    file: UploadFile = File(...),
    user_id: str = Depends(auth_dependency),
) -> JSONResponse:
    try:
        import cloudinary
        import cloudinary.uploader
        result = cloudinary.uploader.upload(file.file, folder="elecciones")
        url = result.get("secure_url")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    db = get_db()
    await db["candidates"].insert_one({
        "name": name,
        "position": position,
        "photo_url": url,
        "votes": 0,
    })
    return JSONResponse(content={"message": "Candidato registrado"}, status_code=201)


@router.get("/candidates")
async def list_candidates(user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    candidates: list[dict[str, Any]] = []
    async for c in db["candidates"].find():
        c["_id"] = str(c["_id"])
        candidates.append(c)
    return JSONResponse(content=candidates)


@router.delete("/candidates/{candidate_id}")
async def delete_candidate(candidate_id: str, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    try:
        await db["candidates"].delete_one({"_id": ObjectId(candidate_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")
    return JSONResponse(content={"message": "Candidato eliminado"})


@router.get("/election-results")
async def election_results(user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    results: list[dict[str, Any]] = []
    async for c in db["candidates"].find():
        results.append({"name": c.get("name"), "votes": c.get("votes", 0), "position": c.get("position", "")})
    return JSONResponse(content=results)


@router.post("/student/cast-vote")
async def cast_vote(data: VoteRequest, user_id: str = Depends(auth_dependency)) -> JSONResponse:
    db = get_db()
    existing = await db["votes"].find_one({"student_id": data.student_id})
    if existing:
        raise HTTPException(status_code=400, detail="Ya has votado")

    await db["votes"].insert_one({
        "student_id": data.student_id,
        "candidate_id": data.candidate_id,
        "created_at": datetime.now(timezone.utc),
    })

    if data.candidate_id != "blank":
        try:
            await db["candidates"].update_one(
                {"_id": ObjectId(data.candidate_id)},
                {"$inc": {"votes": 1}},
            )
        except Exception:
            pass

    return JSONResponse(content={"message": "Voto registrado"})
