from typing import Optional

from pydantic import BaseModel


class EscalationRequest(BaseModel):
    session_id: str
    reason: str


class EscalationResult(BaseModel):
    success: bool
    escalation_id: Optional[int] = None
    message: str