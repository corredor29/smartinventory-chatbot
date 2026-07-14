from typing import Annotated, Optional, TypedDict, Any # Tipos utilizados para definir la estructura del estado.

from langchain_core.messages import BaseMessage # Representa cualquier mensaje del historial de LangChain.
# Función especial de LangGraph utilizada para agregar
# automáticamente nuevos mensajes al historial.
from langgraph.graph.message import add_messages


class ChatState(TypedDict):
    """
    Estado que LangGraph mantiene y pasa entre nodos durante toda la conversación.
    Cada nodo del grafo recibe este estado, lo modifica, y lo devuelve actualizado.
    """

    session_id: str # Identificador único de la sesión de conversación.
    messages: Annotated[list[BaseMessage], add_messages] # Lista de mensajes que conforman el historial de la conversación. Cada mensaje puede ser del tipo HumanMessage, AIMessage, SystemMessage, o ToolMessage.

    pending_product_id: Optional[int] #Identificador del producto pendiente
    pending_product_name: Optional[str] #Nombre del producto pendiente
    pending_quantity: Optional[int] #Cantidad pendiente de venta
    pending_unit_price: Optional[float] #Precio unitario pendiente

    customer_id: Optional[int] # Identificador del cliente
    state: str #estado de la conversación (ej. "WAITING_HUMAN_AGENT", "WAITING_CUSTOMER_CONFIRMATION", etc.)
    invoice_number: Optional[str] #Número de factura generado por la venta, si la venta fue exitosa.
    sale_origin: Optional[str] #Origen de la venta (ej. "CHATBOT", "FRONTEND", etc.)
    escalated: bool #Indica si la conversación fue escalada a un asesor humano. Se establece en True cuando la tool escalate_to_human es invocada con éxito.

    # Últimos productos encontrados por search_product (para el front)
    found_products: Optional[list[dict[str, Any]]] # Lista de productos encontrados por la herramienta search_product.