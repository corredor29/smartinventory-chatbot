from typing import Optional

from pydantic import BaseModel


class SaleItemRequest(BaseModel):
    product_id: int
    quantity: int


class SaleRequest(BaseModel):
    session_id: str
    customer_id: Optional[int] = None
    items: list[SaleItemRequest]
    origin: str = "Chatbot"


class SaleResult(BaseModel):
    success: bool
    sale_id: Optional[int] = None
    invoice_number: Optional[str] = None
    total: Optional[float] = None
    message: str