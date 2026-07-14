from langgraph.graph import StateGraph, END # Clase principal utilizada para construir grafos en LangGraph. 
from langgraph.prebuilt import ToolNode # Nodo predefinido encargado de ejecutar automáticamente las Tools registradas por el agente.

from app.graph.state import ChatState # Estado compartido entre todos los nodos.
from app.agents.agent import TOOLS # Lista de herramientas disponibles para el agente
from app.graph.edges import route_after_model, route_after_tools # Funciones encargadas de decidir las transiciones del grafo.
from app.graph.nodes import ( # Nodos personalizados del proyecto.
    call_model, # Invoca el modelo de IA.
    capture_sale_result, # Procesa el resultado de una venta.
    capture_search_result, # Procesa los productos encontrados.
    mark_escalated, # Marca una conversación como escalada.
)


def build_graph():
    """
    Se crea una nueva instancia del StateGraph utilizando
    ChatState como estado compartido entre todos los nodos.
    """
    graph = StateGraph(ChatState)
    """
    Cada nodo representa una operación concreta dentro del
    flujo conversacional.

    Los nombres registrados aquí serán utilizados por las
    funciones de enrutamiento.
    """
    graph.add_node("call_model", call_model)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_node("mark_escalated", mark_escalated)
    graph.add_node("capture_sale_result", capture_sale_result)
    graph.add_node("capture_search_result", capture_search_result)

    """
    Define cuál será el primer nodo ejecutado cada vez que
    el chatbot procese un mensaje.

    Toda conversación inicia llamando al modelo de IA.
    """
    
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
    
    """
    Algunas operaciones finalizan inmediatamente mientras
    que otras regresan al modelo para continuar la
    conversación.
    """

    graph.add_edge("mark_escalated", END) # Una conversación escalada termina el flujo.
    graph.add_edge("capture_sale_result", "call_model") # Después de registrar una venta se vuelve al modelo.
    graph.add_edge("capture_search_result", "call_model") # Después de capturar productos se vuelve al modelo.

    """
    Convierte la definición del grafo en un objeto listo
    para ejecutarse.

    A partir de este momento el flujo conversacional queda
    completamente construido.
    """
    return graph.compile()


chat_graph = build_graph()
