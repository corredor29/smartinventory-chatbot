from typing import Optional

from pydantic import BaseModel, Field


class SaleItemRequest(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0, le=100)


class SaleRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    customer_id: Optional[int] = Field(default=None, gt=0)
    items: list[SaleItemRequest] = Field(..., min_length=1, max_length=20)
    origin: str = "Chatbot"


class SaleResult(BaseModel):
    success: bool
    sale_id: Optional[int] = None
    invoice_number: Optional[str] = None
    total: Optional[float] = None
    message: str
