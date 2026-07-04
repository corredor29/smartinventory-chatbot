import asyncio
import time

from langchain_core.messages import BaseMessage

from app.core.config import settings
from app.core.logging import logger
from app.graph.state import ChatState

# NOTA DE DEUDA TÉCNICA (ver también `redis` en requirements.txt, hoy sin usar):
# Este store es un diccionario en memoria de un solo proceso. Es apropiado
# para un taller/entrega o para un despliegue de una sola réplica, pero tiene
# dos limitaciones que hay que resolver antes de escalar horizontalmente:
#   1. No se comparte entre procesos/réplicas: con más de un worker de
#      uvicorn (o más de un pod), una misma sesión podría "verse" en un
#      proceso y no en otro, perdiendo contexto de conversación.
#   2. Se pierde por completo si el proceso se reinicia (deploy, crash, etc.).
# La migración natural es un backend Redis (session_store="redis"), pero no
# es trivial: `ChatState["messages"]` contiene objetos `BaseMessage` de
# LangChain que no son JSON-serializables directamente. Habría que usar
# `langchain_core.messages.messages_to_dict` / `messages_from_dict` (u
# equivalente) para serializar/deserializar antes de guardar, y decidir un
# TTL nativo de Redis en vez del barrido manual que se hace aquí. Se deja
# documentado en vez de implementado porque cambia la infraestructura de
# despliegue (requiere un Redis corriendo) y no es necesario para el
# alcance actual del proyecto.

_sessions: dict[str, ChatState] = {}
_last_activity: dict[str, float] = {}
_locks: dict[str, asyncio.Lock] = {}


def session_lock(session_id: str) -> asyncio.Lock:
    """
    Devuelve (creándolo si hace falta) el lock asociado a una sesión, para
    serializar el procesamiento de mensajes que lleguen casi simultáneamente
    para el mismo session_id. Sin esto, dos requests concurrentes sobre la
    misma sesión podrían pisarse el estado entre sí (uno de los dos
    resultados del grafo se perdería al guardar).

    No hay condición de carrera al crear el lock: entre el `.get()` y el
    `[...] = lock` no hay ningún `await`, así que el scheduler de asyncio no
    puede intercalar otra tarea en medio.
    """
    lock = _locks.get(session_id)
    if lock is None:
        lock = asyncio.Lock()
        _locks[session_id] = lock
    return lock


def _is_expired(session_id: str) -> bool:
    last_seen = _last_activity.get(session_id)
    if last_seen is None:
        return False
    return (time.monotonic() - last_seen) > settings.session_ttl_seconds


def get_or_create_state(session_id: str) -> ChatState:
    """
    Recupera el estado de una sesión existente, o crea uno nuevo con los
    valores por defecto si es la primera vez que se ve ese session_id (o si
    la sesión anterior expiró por inactividad).
    """
    if session_id in _sessions and _is_expired(session_id):
        logger.info(f"[{session_id}] Sesión expirada por inactividad, se reinicia")
        clear_session(session_id)

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

    _last_activity[session_id] = time.monotonic()
    return _sessions[session_id]


def save_state(session_id: str, state: ChatState) -> None:
    """
    Persiste el estado actualizado de la sesión después de ejecutar el grafo.
    """
    _sessions[session_id] = state
    _last_activity[session_id] = time.monotonic()


def append_user_message(session_id: str, message: BaseMessage) -> ChatState:
    """
    Atajo para agregar el mensaje del usuario al estado antes de invocar el grafo.
    """
    state = get_or_create_state(session_id)
    state["messages"].append(message)
    return state


def clear_session(session_id: str) -> None:
    """
    Elimina una sesión por completo (ej. cuando se cierra, expira, o se
    escala a un asesor y el bot ya no debe seguir participando).
    """
    _sessions.pop(session_id, None)
    _last_activity.pop(session_id, None)
    _locks.pop(session_id, None)
    logger.info(f"[{session_id}] Sesión eliminada de memoria")


def get_active_session_count() -> int:
    return len(_sessions)


def purge_expired_sessions() -> int:
    """
    Recorre todas las sesiones y elimina las que llevan más de
    `session_ttl_seconds` sin actividad. `get_or_create_state` ya expira una
    sesión puntual cuando alguien vuelve a escribir en ella, pero una sesión
    que el cliente simplemente abandona (sin volver a escribir nunca) no pasa
    de nuevo por esa función, así que sin este barrido periódico su memoria
    nunca se liberaría. Pensado para llamarse desde una tarea periódica.
    """
    expired = [sid for sid in list(_sessions) if _is_expired(sid)]
    for session_id in expired:
        clear_session(session_id)
    if expired:
        logger.info(f"Barrido de sesiones inactivas: {len(expired)} sesión(es) liberada(s)")
    return len(expired)
