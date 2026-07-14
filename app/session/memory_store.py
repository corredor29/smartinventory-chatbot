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

_sessions: dict[str, ChatState] = {} # Diccionario que mapea session_id a ChatState. Contiene todas las sesiones activas en memoria.
_last_activity: dict[str, float] = {} # Diccionario que mapea session_id a la marca de tiempo (time.monotonic()) de la última actividad. Se utiliza para determinar si una sesión ha expirado por inactividad.
_locks: dict[str, asyncio.Lock] = {} # Diccionario que mapea session_id a un asyncio.Lock. Se utiliza para serializar el acceso a la sesión y evitar condiciones de carrera cuando múltiples requests concurrentes intentan modificar el mismo estado de sesión.


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
    last_seen = _last_activity.get(session_id) #Obtiene la marca de tiempo de la última actividad para la sesión dada. Si no existe, significa que la sesión nunca ha sido activa o ya fue eliminada.
    if last_seen is None:
        return False
    return (time.monotonic() - last_seen) > settings.session_ttl_seconds #Compara la marca de tiempo actual con la última actividad para determinar si la sesión ha expirado según el TTL configurado.


def get_or_create_state(session_id: str) -> ChatState:
    """
    Recupera el estado de una sesión existente, o crea uno nuevo con los
    valores por defecto si es la primera vez que se ve ese session_id (o si
    la sesión anterior expiró por inactividad).
    """
    if session_id in _sessions and _is_expired(session_id): #Si la sesión existe pero ha expirado, se elimina y se crea una nueva.
        logger.info(f"[{session_id}] Sesión expirada por inactividad, se reinicia") # Registra la expiración de la sesión.
        clear_session(session_id) # Elimina la sesión expirada de los diccionarios de sesiones, última actividad y locks.

    if session_id not in _sessions:
        logger.info(f"[{session_id}] Nueva sesión de chat iniciada") # Registra la creación de una nueva sesión de chat.
        _sessions[session_id] = ChatState(
            session_id=session_id, # Identificador único de la sesión.
            messages=[], # Lista de mensajes intercambiados en la sesión.
            pending_product_id=None, # Identificador del producto pendiente de confirmación (si aplica).
            pending_product_name=None, # Nombre del producto pendiente de confirmación (si aplica).
            pending_quantity=None, # Cantidad pendiente de confirmación (si aplica).
            pending_unit_price=None, # Precio unitario pendiente de confirmación (si aplica).
            customer_id=None, # Identificador del cliente asociado a la sesión (si aplica).
            state="IN_PROGRESS", # Estado actual de la conversación (IN_PROGRESS, COMPLETED, ESCALATED, etc.).
            invoice_number=None, # Número de factura asociado a la venta (si aplica).
            sale_origin=None, # Origen de la venta (si aplica).
            escalated=False, # Indica si la sesión ha sido escalada a un asesor humano.
            found_products=None, # Lista de productos encontrados en la búsqueda (si aplica).
        )

    _last_activity[session_id] = time.monotonic() # Actualiza la marca de tiempo de la última actividad para la sesión actual.
    return _sessions[session_id] # Devuelve el estado de la sesión (ya sea existente o recién creada) para que pueda ser utilizado por la lógica del chatbot.


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
    return len(_sessions) #Devuelve el número de sesiones activas actualmente en memoria. Esto puede ser útil para monitoreo o métricas del sistema.


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
