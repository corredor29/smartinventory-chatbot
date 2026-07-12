from typing import Any # Tipado utilizado para especificar el tipo de retorno de la Tool.

from langchain_core.tools import tool # Decorador que registra la función como una Tool de LangChain.

from app.agents.tools.common import with_tool_error_handling # Decorador encargado de centralizar el manejo de errores, logs y métricas.
from app.clients.dotnet_client import dotnet_client # Cliente HTTP utilizado para comunicarse con la API .NET.
from app.core.logging import logger # Logger del proyecto.


@tool
@with_tool_error_handling(
    fallback={"found": False, "message": "No encontré una factura con ese número."}
)
async def get_invoice(invoice_number: str) -> dict[str, Any]:
    """
    Consulta el detalle de una factura ya generada por su número (ej. "FAC-000001").
    Úsala cuando el cliente pregunte por el estado de una compra que ya hizo o
    quiera confirmar los datos de una factura.

    Args:
        invoice_number: número de factura a consultar, en formato FAC-XXXXXX.
    """
    
    logger.info(f"Consultando factura: {invoice_number}")
    result = await dotnet_client.get(f"/invoices/number/{invoice_number}")
    
    
    return {
        "found": True, # Indica que la factura fue encontrada.
        "invoice_number": result.get("invoiceNumber") or result.get("invoice_number"), # Número de factura.
        "issue_date": result.get("issueDate") or result.get("issue_date"), # Fecha de emisión.
        "total": result.get("total"), # Valor total de la factura.
        "items": result.get("items", []), # Productos incluidos en la compra.
    }
