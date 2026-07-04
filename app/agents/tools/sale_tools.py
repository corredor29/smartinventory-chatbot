from typing import Annotated, Any

from langchain_core.tools import tool
from pydantic import Field

from app.agents.tools.common import with_tool_error_handling
from app.clients.dotnet_client import dotnet_client
from app.core.logging import logger


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

    payload = {
        "session_id": session_id,
        "customer_id": customer_id,
        "items": [{"product_id": product_id, "quantity": quantity}],
        "origin": "Chatbot",
    }

    result = await dotnet_client.post("/sales", json=payload)
    return {
        "success": True,
        "sale_id": result.get("sale_id"),
        "invoice_number": result.get("invoice_number"),
        "total": result.get("total"),
        "message": "Venta registrada exitosamente.",
    }
