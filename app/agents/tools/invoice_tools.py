from typing import Any

from langchain_core.tools import tool

from app.agents.tools.common import with_tool_error_handling
from app.clients.dotnet_client import dotnet_client
from app.core.logging import logger


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
        "found": True,
        "invoice_number": result.get("invoiceNumber") or result.get("invoice_number"),
        "issue_date": result.get("issueDate") or result.get("issue_date"),
        "total": result.get("total"),
        "items": result.get("items", []),
    }
