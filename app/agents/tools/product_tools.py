from langchain_core.tools import tool

from app.clients.dotnet_client import dotnet_client
from app.core.logging import logger


@tool
async def search_product(query: str) -> dict:
    """
    Busca productos en el catálogo de SmartInventory por nombre o descripción.
    Úsala cuando el cliente mencione algo que quiere comprar, por ejemplo
    "laptop para diseño" o "teclado mecánico".

    Args:
        query: términos de búsqueda (nombre, categoría o descripción del producto).
    """
    logger.info(f"Buscando producto: {query}")

    try:
        result = await dotnet_client.get("/products/search", params={"q": query})
        return result
    except Exception as e:
        logger.error(f"Error buscando producto '{query}': {e}")
        return {"found": False, "products": [], "error": str(e)}


@tool
async def check_stock(product_id: int, quantity: int) -> dict:
    """
    Verifica si hay suficiente stock disponible de un producto para la cantidad
    solicitada. Úsala siempre antes de confirmar una venta.

    Args:
        product_id: identificador del producto a validar.
        quantity: cantidad que el cliente quiere comprar.
    """
    logger.info(f"Validando stock: producto={product_id}, cantidad={quantity}")

    try:
        result = await dotnet_client.get(f"/inventory/{product_id}/stock")
        current_stock = result.get("current_stock", 0)
        return {
            "available": current_stock >= quantity,
            "current_stock": current_stock,
            "requested_quantity": quantity,
        }
    except Exception as e:
        logger.error(f"Error validando stock del producto {product_id}: {e}")
        return {"available": False, "current_stock": 0, "error": str(e)}