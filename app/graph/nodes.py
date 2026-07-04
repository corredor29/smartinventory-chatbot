from langchain_core.messages import SystemMessage

from app.core.logging import logger
from app.graph.state import ChatState
from app.agents.agent import agent_model, SYSTEM_PROMPT


def call_model(state: ChatState) -> dict:
    """
    Nodo principal: le pasa el historial de mensajes al agente (definido en
    app.agents.agent) y deja que decida si responde directo o invoca una tool.
    """
    messages = state["messages"]

    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT), *messages]

    logger.info(f"[{state['session_id']}] Invocando modelo con {len(messages)} mensajes")

    response = agent_model.invoke(messages)

    return {"messages": [response]}


def mark_escalated(state: ChatState) -> dict:
    """
    Nodo que se ejecuta cuando la tool escalate_to_human fue invocada.
    Actualiza el estado de la conversación para que el backend .NET
    sepa que debe pasar a modo SignalR (chat en vivo con un asesor).
    """
    logger.info(f"[{state['session_id']}] Conversación escalada a asesor humano")
    return {"state": "WAITING_HUMAN_AGENT", "escalated": True}