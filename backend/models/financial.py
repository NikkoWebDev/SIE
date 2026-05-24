from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class PaymentStatus(StrEnum):
    AL_DIA = "AL_DIA"
    EN_MORA = "EN_MORA"


class FinancialStatus(BaseModel):
    student_id: str
    is_paid: bool
    current_status: PaymentStatus = PaymentStatus.AL_DIA
    last_payment_date: Optional[datetime] = None
    overdue_months: int = 0
    total_balance: float = 0.0

    model_config = {"extra": "ignore"}


class PaymentToggleRequest(BaseModel):
    document_id: str = Field(..., min_length=5)
    is_paid: bool

    model_config = {"extra": "forbid"}


class PaymentRecordDB(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    student_id: str
    amount: float = 0.0
    concept: str = "PENSION_MENSUAL"
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    registered_by: str = ""
    period: str = ""

    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}
