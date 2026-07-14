from typing import Annotated, Any # Tipos utilizados para mejorar el tipado de la Tool.

from langchain_core.tools import tool # Decorador que convierte una función en una Tool de LangChain.
from pydantic import Field # Permite validar automáticamente los parámetros recibidos por la Tool.

from app.agents.tools.common import with_tool_error_handling # Decorador encargado de registrar métricas, logs y manejar errores comunes.
from app.clients.dotnet_client import dotnet_client # Cliente HTTP utilizado para comunicarse con la API .NET.
from app.core.logging import logger # Logger del proyecto.


@tool
@with_tool_error_handling(
    fallback={
        "success": False,
        "message": "No se pudo registrar la venta. Es posible que el stock haya cambiado o hubo un error del sistema.",
    }
)
async def create_sale(
    session_id: str,
    product_id: Annotated[int, Field(gt=0)],
    quantity: Annotated[int, Field(gt=0, le=100)],
    customer_id: Annotated[int | None, Field(gt=0)] = None,
) -> dict[str, Any]:
    """
    Registra una venta en el sistema. SOLO debe usarse después de que el cliente
    haya confirmado explícitamente que quiere comprar (ej. dijo "sí", "confirmo",
    "dale"). Nunca la uses si el cliente todavía está decidiendo o preguntando.

    Args:
        session_id: identificador de la sesión de chat actual.
        product_id: identificador del producto a vender.
        quantity: cantidad confirmada por el cliente (máximo 100 por venta).
        customer_id: identificador del cliente, si ya fue identificado en la conversación.
    """
    logger.info(
        f"[{session_id}] Registrando venta: producto={product_id}, cantidad={quantity}"
    )
    
    """
    Construye el cuerpo de la petición HTTP que será
    enviado a la API .NET.

    Se utilizan nombres en formato camelCase porque el
    binder de ASP.NET Core los espera con esa convención.

    Estructura enviada:

        {
            sessionId,
            customerId,
            items,
            origin
        }
    """

    # camelCase para el binder de ASP.NET Core
    payload = {
        "sessionId": session_id, # Identificador de la conversación.
        "customerId": customer_id, # Cliente asociado.
        "items": [{"productId": product_id, "quantity": quantity}], # Productos vendidos.
        "origin": "Chatbot", # Origen de la venta.
    }
    
    """
    Envía una petición HTTP POST al endpoint encargado de
    registrar ventas.
    """
    result = await dotnet_client.post("/sales", json=payload)
    if result.get("success") is False:
        return {
            "success": False,
            "message": result.get("message")
            or "No se pudo registrar la venta.",
        }

    return {
        "success": True, # Venta creada correctamente.
        "sale_id": result.get("saleId") or result.get("sale_id"), # Identificador interno.
        "invoice_number": result.get("invoiceNumber") or result.get("invoice_number"), # Número de factura generado.
        "total": result.get("total"), # Valor total de la compra.
        "message": result.get("message") or "Venta registrada exitosamente.", # Mensaje de respuesta.
    }
