from typing import Optional

from pydantic import BaseModel, Field


class EscalationRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    reason: str = Field(..., min_length=1, max_length=500)


class EscalationResult(BaseModel):
    success: bool
    escalation_id: Optional[int] = None
    message: str
