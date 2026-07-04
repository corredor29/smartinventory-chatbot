from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Identificador de sesión asignado por el backend .NET.",
    )
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    response: str
    state: str = "IN_PROGRESS"
    invoice_number: Optional[str] = None
    sale_origin: Optional[str] = None
