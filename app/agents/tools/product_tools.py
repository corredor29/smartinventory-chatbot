from typing import Annotated, Any

from langchain_core.tools import tool
from pydantic import Field

from app.agents.tools.common import with_tool_error_handling
from app.clients.dotnet_client import dotnet_client
from app.core.logging import logger


@tool
@with_tool_error_handling(fallback={"found": False, "products": []})
async def search_product(query: str) -> dict[str, Any]:
    """
    Busca productos en el catálogo de SmartInventory por nombre, marca, categoría
    o descripción. Úsala SIEMPRE que el cliente mencione una marca o tipo de
    producto, aunque sea de forma vaga (ej. "me gustan los lenovos", "quiero una
    laptop", "tienen teclados?").

    Pasa términos cortos y útiles (marca o tipo), NO la frase completa del cliente.
    Ejemplos buenos de query: "lenovo", "laptop", "teclado mecánico".
    Ejemplos malos: "me gustan los lenovos", "no tienes un lenovo LOQ".

    Args:
        query: palabras clave de búsqueda (marca, modelo o categoría).
    """
    logger.info(f"Buscando producto: {query}")
    return await dotnet_client.get("/products/search", params={"q": query})


@tool
@with_tool_error_handling(fallback={"available": False, "current_stock": 0})
async def check_stock(
    product_id: Annotated[int, Field(gt=0)],
    quantity: Annotated[int, Field(gt=0, le=100)],
) -> dict[str, Any]:
    """
    Verifica si hay suficiente stock disponible de un producto para la cantidad
    solicitada. Úsala siempre antes de confirmar una venta.

    Args:
        product_id: identificador del producto a validar.
        quantity: cantidad que el cliente quiere comprar (máximo 100 por venta).
    """
    logger.info(f"Validando stock: producto={product_id}, cantidad={quantity}")
    result = await dotnet_client.get(f"/inventory/{product_id}/stock")
    current_stock = result.get("current_stock", 0)
    return {
        "available": current_stock >= quantity,
        "current_stock": current_stock,
        "requested_quantity": quantity,
    }
