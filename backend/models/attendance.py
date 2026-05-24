from datetime import datetime, timezone
from enum import StrEnum

from bson import ObjectId
from pydantic import BaseModel, Field


class AttendanceStatus(StrEnum):
    PRESENT = "PRESENTE"
    ABSENT = "AUSENTE"
    LATE = "TARDE"
    EXCUSED = "EXCUSADO"


class AttendanceRecord(BaseModel):
    student_id: str = Field(..., min_length=1)
    status: AttendanceStatus = Field(default=AttendanceStatus.PRESENT)
    date: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    period: str = Field(default="JORNADA_UNICA")
    notes: str = Field(default="", max_length=200)

    model_config = {"extra": "forbid"}


class AttendanceDB(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    student_id: str
    grade: str = ""
    date: str
    status: AttendanceStatus
    period: str = "JORNADA_UNICA"
    notes: str = ""
    registered_by: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}


class AttendanceStats(BaseModel):
    student_id: str
    fullname: str = ""
    grade: str = ""
    total_days: int = 0
    present: int = 0
    absent: int = 0
    late: int = 0
    excused: int = 0
    attendance_rate: float = 0.0
