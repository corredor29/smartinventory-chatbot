from typing import Annotated, Any # Tipos utilizados para mejorar el tipado de las funciones.

from langchain_core.tools import tool # Decorador que convierte una función en una Tool de LangChain.
from pydantic import Field # Field permite validar automáticamente los parámetros recibidos por la Tool.

from app.agents.tools.common import with_tool_error_handling # Decorador encargado de manejar errores, registrar logs # y actualizar métricas.
from app.clients.dotnet_client import dotnet_client  # Cliente HTTP utilizado para comunicarse con la API .NET.
from app.core.logging import logger # Logger del proyecto.


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
    
    """
    Consulta la API .NET para conocer el inventario
    actual del producto.
    """
    result = await dotnet_client.get(f"/inventory/{product_id}/stock")
    current_stock = result.get("current_stock", 0) # Obtiene el inventario actual.
    return {
        "available": current_stock >= quantity, # Indica si existe inventario suficiente.
        "current_stock": current_stock,  #Cantidad existente.
        "requested_quantity": quantity, # Cantidad solicitada.
    }
