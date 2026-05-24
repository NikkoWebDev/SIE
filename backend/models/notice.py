from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class NoticeCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    file_url: str = Field(default="")
    category: str = Field(default="General", max_length=40)
    author: str = Field(default="Rectoría")

    model_config = {"extra": "forbid"}


class NoticeDB(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    content: str
    file_url: str = ""
    category: str = "General"
    author: str = "Rectoría"
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_pinned: bool = False

    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}
