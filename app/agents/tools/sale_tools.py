from langchain_core.tools import tool

from app.clients.dotnet_client import dotnet_client
from app.core.logging import logger


@tool
async def create_sale(
    session_id: str,
    product_id: int,
    quantity: int,
    customer_id: int | None = None,
) -> dict:
    """
    Registra una venta en el sistema. SOLO debe usarse después de que el cliente
    haya confirmado explícitamente que quiere comprar (ej. dijo "sí", "confirmo",
    "dale"). Nunca la uses si el cliente todavía está decidiendo o preguntando.

    Args:
        session_id: identificador de la sesión de chat actual.
        product_id: identificador del producto a vender.
        quantity: cantidad confirmada por el cliente.
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

    try:
        result = await dotnet_client.post("/sales", json=payload)
        return {
            "success": True,
            "sale_id": result.get("sale_id"),
            "invoice_number": result.get("invoice_number"),
            "total": result.get("total"),
            "message": "Venta registrada exitosamente.",
        }
    except Exception as e:
        logger.error(f"[{session_id}] Error registrando venta: {e}")
        return {
            "success": False,
            "message": "No se pudo registrar la venta. Es posible que el stock haya cambiado o hubo un error del sistema.",
            "error": str(e),
        }