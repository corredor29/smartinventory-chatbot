from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from app.graph.state import ChatState
from app.agents.agent import TOOLS
from app.graph.edges import route_after_model, route_after_tools
from app.graph.nodes import (
    call_model,
    capture_sale_result,
    capture_search_result,
    mark_escalated,
)


def build_graph():
    graph = StateGraph(ChatState)

    graph.add_node("call_model", call_model)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_node("mark_escalated", mark_escalated)
    graph.add_node("capture_sale_result", capture_sale_result)
    graph.add_node("capture_search_result", capture_search_result)

    graph.set_entry_point("call_model")

    graph.add_conditional_edges(
        "call_model",
        route_after_model,
        {"tools": "tools", END: END},
    )

    graph.add_conditional_edges(
        "tools",
        route_after_tools,
        {
            "mark_escalated": "mark_escalated",
            "capture_sale_result": "capture_sale_result",
            "capture_search_result": "capture_search_result",
            "call_model": "call_model",
        },
    )

    graph.add_edge("mark_escalated", END)
    graph.add_edge("capture_sale_result", "call_model")
    graph.add_edge("capture_search_result", "call_model")

    return graph.compile()


chat_graph = build_graph()
