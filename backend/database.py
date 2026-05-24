import logging
import os
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING

logger = logging.getLogger("siee.db")

MONGO_URI: str = os.getenv("MONGO_URL") or os.getenv(
    "MONGODB_URI",
    "mongodb+srv://admin:password@cluster0.example.mongodb.net/?retryWrites=true&w=majority",
)
MONGO_DB: str = os.getenv("MONGO_DB", "sie_core")

COLLECTIONS: dict[str, str] = {
    "STUDENTS": "students",
    "ADMINS": "admins",
    "TEACHERS": "teachers",
    "GRADES": "grades",
    "SUBJECTS": "subjects",
    "NOTICES": "notices",
    "DELIVERIES": "deliveries",
    "GUIDES": "guides",
    "ASSIGNMENTS": "assignments",
    "EXAMS": "exams",
    "EXAM_RESULTS": "exam_results",
    "EXAM_INCIDENTS": "exam_incidents",
    "CANDIDATES": "candidates",
    "VOTES": "votes",
    "ATTENDANCE": "attendance",
    "PAYMENTS": "payments",
}

COLLECTION_INDICES: dict[str, list[tuple[list[tuple[str, int]], dict[str, str]]]] = {
    "students": [
        ([("document_id", ASCENDING)], {"unique": True, "name": "idx_student_doc"}),
        ([("grade", ASCENDING), ("fullname", ASCENDING)], {"name": "idx_student_grade_name"}),
        ([("is_paid", ASCENDING)], {"name": "idx_student_payment"}),
        ([("is_at_risk", ASCENDING), ("risk_updated_at", DESCENDING)], {"name": "idx_student_risk"}),
        ([("role", ASCENDING)], {"name": "idx_student_role"}),
    ],
    "admins": [
        ([("document_id", ASCENDING)], {"unique": True, "name": "idx_admin_doc"}),
        ([("role", ASCENDING)], {"name": "idx_admin_role"}),
    ],
    "teachers": [
        ([("document_id", ASCENDING)], {"unique": True, "name": "idx_teacher_doc"}),
        ([("grade", ASCENDING)], {"name": "idx_teacher_grade"}),
        ([("subject", ASCENDING)], {"name": "idx_teacher_subject"}),
    ],
    "grades": [
        ([("student_id", ASCENDING), ("subject_id", ASCENDING), ("created_at", DESCENDING)], {"name": "idx_grade_student_subject"}),
        ([("teacher_id", ASCENDING), ("created_at", DESCENDING)], {"name": "idx_grade_teacher"}),
        ([("subject_id", ASCENDING)], {"name": "idx_grade_subject"}),
        ([("period", ASCENDING)], {"name": "idx_grade_period"}),
    ],
    "subjects": [
        ([("grade", ASCENDING), ("name", ASCENDING)], {"unique": True, "name": "idx_subject_grade_name"}),
    ],
    "notices": [
        ([("date", DESCENDING)], {"name": "idx_notice_date"}),
        ([("category", ASCENDING)], {"name": "idx_notice_category"}),
    ],
    "deliveries": [
        ([("student_id", ASCENDING), ("subject", ASCENDING)], {"name": "idx_delivery_student_subject"}),
        ([("grade", ASCENDING), ("subject", ASCENDING)], {"name": "idx_delivery_grade_subject"}),
    ],
    "guides": [
        ([("grade", ASCENDING), ("subject", ASCENDING)], {"name": "idx_guide_grade_subject"}),
    ],
    "exams": [
        ([("grade", ASCENDING), ("subject", ASCENDING)], {"name": "idx_exam_grade_subject"}),
        ([("is_active", ASCENDING)], {"name": "idx_exam_active"}),
        ([("due_date", ASCENDING)], {"name": "idx_exam_due"}),
    ],
    "exam_results": [
        ([("student_id", ASCENDING), ("exam_id", ASCENDING)], {"unique": True, "name": "idx_exam_result_unique"}),
        ([("exam_id", ASCENDING)], {"name": "idx_exam_result_exam"}),
        ([("student_id", ASCENDING)], {"name": "idx_exam_result_student"}),
    ],
    "exam_incidents": [
        ([("exam_id", ASCENDING), ("student_id", ASCENDING)], {"name": "idx_incident_exam_student"}),
        ([("timestamp", DESCENDING)], {"name": "idx_incident_time"}),
    ],
    "candidates": [
        ([("election_id", ASCENDING), ("name", ASCENDING)], {"unique": True, "name": "idx_candidate_election_name"}),
    ],
    "votes": [
        ([("student_id", ASCENDING), ("election_id", ASCENDING)], {"unique": True, "name": "idx_vote_unique"}),
        ([("candidate_id", ASCENDING)], {"name": "idx_vote_candidate"}),
    ],
    "attendance": [
        ([("student_id", ASCENDING), ("date", ASCENDING)], {"unique": True, "name": "idx_attendance_unique"}),
        ([("grade", ASCENDING), ("date", ASCENDING)], {"name": "idx_attendance_grade_date"}),
    ],
    "payments": [
        ([("student_id", ASCENDING), ("date", DESCENDING)], {"name": "idx_payment_student_date"}),
    ],
}

DEFAULT_ADMIN: dict = {
    "document_id": "12345678",
    "fullname": "Rector Administrador",
    "password": "admin",
    "role": "RECTOR",
    "created_at": datetime.now(timezone.utc),
}

DEFAULT_SUBJECTS: list[dict] = [
    {"name": "Matemáticas", "grade": "6°", "gem_tutor_url": "", "gem_planner_url": ""},
    {"name": "Lengua Castellana", "grade": "6°", "gem_tutor_url": "", "gem_planner_url": ""},
    {"name": "Ciencias Naturales", "grade": "6°", "gem_tutor_url": "", "gem_planner_url": ""},
    {"name": "Ciencias Sociales", "grade": "6°", "gem_tutor_url": "", "gem_planner_url": ""},
    {"name": "Inglés", "grade": "6°", "gem_tutor_url": "", "gem_planner_url": ""},
    {"name": "Tecnología e Informática", "grade": "6°", "gem_tutor_url": "", "gem_planner_url": ""},
    {"name": "Educación Física", "grade": "6°", "gem_tutor_url": "", "gem_planner_url": ""},
    {"name": "Ética y Valores", "grade": "6°", "gem_tutor_url": "", "gem_planner_url": ""},
]


async def create_indexes(db) -> None:
    for coll_name, indexes in COLLECTION_INDICES.items():
        collection = db[coll_name]
        existing = await collection.index_information()
        for keys, opts in indexes:
            idx_name = opts.get("name", "")
            if idx_name and idx_name not in existing:
                try:
                    await collection.create_index(keys, background=True, **{k: v for k, v in opts.items() if k != "name"})
                    logger.debug("index created: %s.%s", coll_name, idx_name)
                except Exception as exc:
                    logger.warning("index skipped %s.%s: %s", coll_name, idx_name, exc)


async def seed_defaults(db) -> None:
    admins_coll = db[COLLECTIONS["ADMINS"]]
    existing_admin = await admins_coll.find_one({"document_id": DEFAULT_ADMIN["document_id"]})
    if existing_admin is None:
        DEFAULT_ADMIN["created_at"] = datetime.now(timezone.utc)
        await admins_coll.insert_one(DEFAULT_ADMIN)
        logger.info("seeded default admin: %s", DEFAULT_ADMIN["document_id"])

    subjects_coll = db[COLLECTIONS["SUBJECTS"]]
    subject_count = await subjects_coll.count_documents({})
    if subject_count == 0:
        now = datetime.now(timezone.utc)
        docs = [{**s, "created_at": now} for s in DEFAULT_SUBJECTS]
        await subjects_coll.insert_many(docs)
        logger.info("seeded %d default subjects", len(docs))


async def init_database(mongo_uri: str = MONGO_URI, mongo_db: str = MONGO_DB):
    client = AsyncIOMotorClient(
        mongo_uri,
        maxPoolSize=20,
        minPoolSize=2,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )
    db = client[mongo_db]
    try:
        await client.admin.command("ping")
        logger.info("mongodb connected: %s", mongo_db)
    except Exception as exc:
        logger.error("mongodb unreachable: %s", exc)
        raise

    await create_indexes(db)
    await seed_defaults(db)

    collection_names = await db.list_collection_names()
    logger.info(
        "collections ready: %s (%d total)",
        mongo_db,
        len(collection_names),
    )

    return client, db
