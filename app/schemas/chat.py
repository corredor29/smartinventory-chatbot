from typing import Any, Optional

from pydantic import BaseModel, Field

"""
    Modelo utilizado para recibir un mensaje enviado desde el
    frontend (.NET) hacia el chatbot.

    Cada vez que un usuario escribe un mensaje, FastAPI valida
    automáticamente la información utilizando este esquema.

    Si alguno de los campos no cumple las reglas definidas,
    FastAPI devuelve automáticamente un HTTP 422 antes de que
    el mensaje llegue a la lógica del chatbot.

    Esto evita procesar solicitudes inválidas.
    """

class ChatRequest(BaseModel):
    session_id: str = Field( #identificador unico de la conversacion
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Identificador de sesión asignado por el backend .NET.",
    )
    message: str = Field(..., min_length=1, max_length=2000) # Mensaje enviado por el usuario restricciones


class ChatProductCard(BaseModel):
    product_id: int # Identificador del producto.
    name: str # Nombre comercial.
    description: Optional[str] = None # Descripción del producto Puede no existir.
    price: float = 0  # Precio del producto.
    category_name: str = "" # Categoría.
    status_name: str = "" # Estado del producto.
    current_stock: int = 0 # Stock disponible.
    image_url: Optional[str] = None # URL de la imagen del producto.


class ChatResponse(BaseModel):
    response: str # Respuesta del chatbot.
    state: str = "IN_PROGRESS" # Estado de la conversación.
    invoice_number: Optional[str] = None # Número de factura.
    sale_origin: Optional[str] = None # Origen de la venta.
    products: list[ChatProductCard] = []# Lista de productos devueltos por el chatbot. Puede estar vacía si no hay productos relevantes para la conversación.
