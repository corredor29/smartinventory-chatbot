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
    - Si la tool que se ejecutó fue escalate_to_human -> ir al nodo que marca
      la conversación como escalada, y terminar ahí (no seguir generando más
      respuestas del bot, ya que un humano tomó el control).
    - Si fue create_sale -> ir al nodo que captura el número de factura en
      el estado antes de continuar.
    - En cualquier otro caso -> volver al modelo para que continúe la conversación
      con el resultado de la tool ya disponible.
    """
    last_message = state["messages"][-1]
    tool_name = getattr(last_message, "name", None)

    if tool_name == "escalate_to_human":
        return "mark_escalated"

    if tool_name == "create_sale":
        return "capture_sale_result"

    return "call_model"