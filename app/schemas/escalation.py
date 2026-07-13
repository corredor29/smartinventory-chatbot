from typing import Optional

from pydantic import BaseModel, Field


class EscalationRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$") # Identificador de sesión.
    reason: str = Field(..., min_length=1, max_length=500) # Motivo de la escalación.


class EscalationResult(BaseModel):
    success: bool # Indica si la escalación fue procesada exitosamente.
    escalation_id: Optional[int] = None # Identificador de la escalación.
    message: str # Mensaje de resultado.
