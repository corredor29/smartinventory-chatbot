from typing import Annotated, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ChatState(TypedDict):
    """
    Estado que LangGraph mantiene y pasa entre nodos durante toda la conversación.
    Cada nodo del grafo recibe este estado, lo modifica, y lo devuelve actualizado.
    """

    # Identificador de la sesión 
    session_id: str

    # Historial de mensajes de la conversación.
    # `add_messages` es un "reducer" de LangGraph: en vez de reemplazar la lista,
    # va acumulando los mensajes nuevos automáticamente.
    messages: Annotated[list[BaseMessage], add_messages]

    # Producto que el cliente está tratando de comprar en este momento
    pending_product_id: Optional[int]
    pending_product_name: Optional[str]
    pending_quantity: Optional[int]
    pending_unit_price: Optional[float]

    # Cliente asociado a la conversación
    customer_id: Optional[int]

    # Paso actual del flujo 
    state: str

    # Resultado final si la venta se completó
    invoice_number: Optional[str]

    # Si la conversación fue escalada a un asesor humano
    escalated: bool