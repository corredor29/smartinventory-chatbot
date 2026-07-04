from typing import Optional

from langchain_core.messages import BaseMessage

from app.core.logging import logger
from app.graph.state import ChatState


_sessions: dict[str, ChatState] = {}


def get_or_create_state(session_id: str) -> ChatState:
    """
    Recupera el estado de una sesión existente, o crea uno nuevo con los
    valores por defecto si es la primera vez que se ve ese session_id.
    """
    if session_id not in _sessions:
        logger.info(f"[{session_id}] Nueva sesión de chat iniciada")
        _sessions[session_id] = ChatState(
            session_id=session_id,
            messages=[],
            pending_product_id=None,
            pending_product_name=None,
            pending_quantity=None,
            pending_unit_price=None,
            customer_id=None,
            state="IN_PROGRESS",
            invoice_number=None,
            escalated=False,
        )

    return _sessions[session_id]


def save_state(session_id: str, state: ChatState) -> None:
    """
    Persiste el estado actualizado de la sesión después de ejecutar el grafo.
    """
    _sessions[session_id] = state


def append_user_message(session_id: str, message: BaseMessage) -> ChatState:
    """
    Atajo para agregar el mensaje del usuario al estado antes de invocar el grafo.
    """
    state = get_or_create_state(session_id)
    state["messages"].append(message)
    return state


def clear_session(session_id: str) -> None:
    """
    Elimina una sesión por completo (ej. cuando se cierra o se escala a un
    asesor y el bot ya no debe seguir participando).
    """
    _sessions.pop(session_id, None)
    logger.info(f"[{session_id}] Sesión eliminada de memoria")


def get_active_session_count() -> int:
    return len(_sessions)