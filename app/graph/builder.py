from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from app.graph.state import ChatState
from app.agents.agent import TOOLS
from app.graph.edges import route_after_model, route_after_tools


def build_graph():
    graph = StateGraph(ChatState)

    # Nodos
    graph.add_node("call_model", call_model)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_node("mark_escalated", mark_escalated)

    # Punto de entrada
    graph.set_entry_point("call_model")

    # Después de call_model: ¿va a tools o termina?
    graph.add_conditional_edges(
        "call_model",
        route_after_model,
        {"tools": "tools", END: END},
    )

    # Después de tools: ¿fue escalamiento o vuelve al modelo?
    graph.add_conditional_edges(
        "tools",
        route_after_tools,
        {"mark_escalated": "mark_escalated", "call_model": "call_model"},
    )

    # Después de marcar como escalado, se termina el turno
    graph.add_edge("mark_escalated", END)

    return graph.compile()


# Instancia compilada, lista para usar en el endpoint de chat
chat_graph = build_graph()