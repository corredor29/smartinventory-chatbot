from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from app.graph.state import ChatState
from app.agents.agent import TOOLS
from app.graph.edges import route_after_model, route_after_tools
from app.graph.nodes import call_model, capture_sale_result, mark_escalated


def build_graph():
    graph = StateGraph(ChatState)

    # Nodos
    graph.add_node("call_model", call_model)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_node("mark_escalated", mark_escalated)
    graph.add_node("capture_sale_result", capture_sale_result)

    # Punto de entrada
    graph.set_entry_point("call_model")

    # Después de call_model: ¿va a tools o termina?
    graph.add_conditional_edges(
        "call_model",
        route_after_model,
        {"tools": "tools", END: END},
    )

    # Después de tools: ¿fue escalamiento, una venta, o vuelve al modelo?
    graph.add_conditional_edges(
        "tools",
        route_after_tools,
        {
            "mark_escalated": "mark_escalated",
            "capture_sale_result": "capture_sale_result",
            "call_model": "call_model",
        },
    )

    # Después de marcar como escalado, se termina el turno
    graph.add_edge("mark_escalated", END)

    # Después de capturar el resultado de la venta, se vuelve al modelo para
    # que continúe (ej. invocar notify_advisor y responder al cliente)
    graph.add_edge("capture_sale_result", "call_model")

    return graph.compile()


# Instancia compilada, lista para usar en el endpoint de chat
chat_graph = build_graph()
