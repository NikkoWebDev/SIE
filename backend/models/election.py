from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class CandidateCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=120)
    position: str = Field(..., min_length=2, max_length=80)
    photo_url: str = Field(default="")

    model_config = {"extra": "forbid"}


class CandidateDB(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    name: str
    position: str
    photo_url: str = ""
    votes: int = 0
    election_id: str = "2026"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}


class VoteRequest(BaseModel):
    student_id: str = Field(..., min_length=1)
    candidate_id: str = Field(..., min_length=1)
    election_id: str = Field(default="2026")

    model_config = {"extra": "forbid"}


class VoteDB(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    student_id: str
    candidate_id: str
    election_id: str = "2026"
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}


class ElectionResult(BaseModel):
    candidate_id: str = ""
    candidate_name: str
    position: str
    photo_url: str = ""
    votes: int = 0
    percentage: float = 0.0
