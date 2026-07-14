from typing import Optional

from pydantic import BaseModel, Field

"""
    Representa un único producto incluido dentro de una venta.

    Una venta puede contener uno o varios productos, por lo
    que este modelo será utilizado dentro de una lista en
    SaleRequest.

    Cada elemento corresponde a un producto específico junto
    con la cantidad solicitada.
    """
class SaleItemRequest(BaseModel):
    product_id: int = Field(..., gt=0) # Identificador del producto.
    quantity: int = Field(..., gt=0, le=100) # Cantidad solicitada.


class SaleRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$") # Identificador de sesión.
    customer_id: Optional[int] = Field(default=None, gt=0) # Identificador del cliente.
    items: list[SaleItemRequest] = Field(..., min_length=1, max_length=20) # Lista de productos en la venta.
    origin: str = "Chatbot" # Origen de la venta.

class SaleResult(BaseModel):
    success: bool # Indica si la venta fue procesada exitosamente.
    sale_id: Optional[int] = None # Identificador de la venta.
    invoice_number: Optional[str] = None # Número de factura.
    total: Optional[float] = None # Total de la venta.
    message: str # Mensaje de resultado.