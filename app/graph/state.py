from typing import Annotated, Optional, TypedDict, Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ChatState(TypedDict):
    """
    Estado que LangGraph mantiene y pasa entre nodos durante toda la conversación.
    Cada nodo del grafo recibe este estado, lo modifica, y lo devuelve actualizado.
    """

    session_id: str
    messages: Annotated[list[BaseMessage], add_messages]

    pending_product_id: Optional[int]
    pending_product_name: Optional[str]
    pending_quantity: Optional[int]
    pending_unit_price: Optional[float]

    customer_id: Optional[int]
    state: str
    invoice_number: Optional[str]
    sale_origin: Optional[str]
    escalated: bool

    # Últimos productos encontrados por search_product (para el front)
    found_products: Optional[list[dict[str, Any]]]