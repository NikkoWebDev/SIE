from typing import Optional

from pydantic import BaseModel, Field


class PaymentToggle(BaseModel):
    student_id: str = Field(..., min_length=1)
    is_paid: bool
    model_config = {"extra": "forbid"}


class PaymentToggleRequest(BaseModel):
    login_credential: str = Field(..., min_length=5)
    is_paid: bool
    model_config = {"extra": "forbid"}
