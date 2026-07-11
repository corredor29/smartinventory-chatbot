from langgraph.graph import END

from app.graph.state import ChatState


def route_after_model(state: ChatState) -> str:
    """
    Decide qué pasa después de que el modelo respondió:
    - Si el modelo pidió usar una tool -> ir al nodo "tools" a ejecutarla.
    - Si el modelo respondió con texto plano (sin tool calls) -> terminar el turno.
    """
    last_message = state["messages"][-1]

    if getattr(last_message, "tool_calls", None):
        return "tools"

    return END


def route_after_tools(state: ChatState) -> str:
    """
    Decide qué pasa después de ejecutar una tool:
    - Si escalate_to_human tuvo éxito -> marcar escalada y terminar.
    - Si escalate falló (ej. cliente no autenticado) -> volver al modelo
      para que informe al cliente (login requerido).
    - Si fue create_sale -> capturar factura.
    - En cualquier otro caso -> volver al modelo.
    """
    import json

    last_message = state["messages"][-1]
    tool_name = getattr(last_message, "name", None)

    if tool_name == "escalate_to_human":
        content = last_message.content
        payload = content if isinstance(content, dict) else None
        if payload is None:
            try:
                payload = json.loads(content) if isinstance(content, str) else {}
            except (TypeError, ValueError):
                payload = {}
        if payload.get("success"):
            return "mark_escalated"
        return "call_model"

    if tool_name == "create_sale":
        return "capture_sale_result"

    if tool_name == "search_product":
        return "capture_search_result"

    return "call_model"