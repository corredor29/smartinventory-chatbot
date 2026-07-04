from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    state: str = "IN_PROGRESS"
    invoice_number: Optional[str] = None
    sale_origin: Optional[str] = None