# Librería estándar utilizada para ejecutar tareas asíncronas
# y controlar tiempos de espera (timeout).
import asyncio
# APIRouter permite registrar endpoints independientes que
# posteriormente serán agregados a FastAPI.
#
# HTTPException permite devolver respuestas HTTP con códigos
# de error personalizados.
from fastapi import APIRouter, HTTPException
# Clases de LangChain utilizadas para representar mensajes
# dentro del historial de conversación.
#
# HumanMessage:
#     Representa un mensaje enviado por el usuario.
#
# AIMessage:
#     Representa una respuesta generada por la IA.
from langchain_core.messages import HumanMessage, AIMessage

from app.core.config import settings # Configuración global del sistema.
# Modelos Pydantic utilizados para validar tanto la petición
# recibida como la respuesta enviada.
from app.schemas.chat import ChatRequest, ChatResponse
# Sistema de logging.
#
# logger:
#     Permite registrar eventos.
#
# session_id_var:
#     Variable de contexto utilizada para asociar cada log
#     con la sesión correspondiente.
from app.core.logging import logger, session_id_var
from app.core.metrics import metrics # Sistema de métricas en memoria.
# Grafo principal encargado de ejecutar toda la lógica del
# chatbot.
from app.graph.builder import chat_graph
# Funciones responsables del manejo del estado de las
# conversaciones.
from app.session.memory_store import (
    get_or_create_state, # Recupera una conversación existente o crea una nueva.
    save_state, # Guarda el estado actualizado de una conversación.
    clear_session, # Elimina completamente una sesión.
    session_lock,  # Lock que evita que dos mensajes de la misma sesión se procesen simultáneamente.
)

"""
Cada módulo de rutas posee su propio APIRouter.

Posteriormente este router será registrado dentro de
main.py mediante:

app.include_router(chat.router)
"""

router = APIRouter()


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest) -> ChatResponse:
    """
    Recibe el mensaje del cliente (reenviado desde .NET), lo procesa a través
    del grafo de LangGraph, y devuelve la respuesta del bot.
    """
    token = session_id_var.set(request.session_id) # Delega todo el procesamiento al método interno.
    try:
        return await _process_message(request)
    finally:
        session_id_var.reset(token)


async def _process_message(request: ChatRequest) -> ChatResponse:
    metrics.increment("chatbot.messages.received")
    logger.info(f"Mensaje recibido: {request.message}") # Registra el mensaje recibido para auditoría.

    # El lock serializa el procesamiento de mensajes que lleguen casi
    # simultáneamente para la misma sesión: sin esto, dos requests
    # concurrentes sobre el mismo session_id podrían pisarse el estado entre
    # sí (uno de los dos resultados del grafo se perdería al guardar).
    async with session_lock(request.session_id):
        # 1. Recuperar (o crear) el estado de esta conversación
        state = get_or_create_state(request.session_id)
        state["found_products"] = None  # Reinicia la lista temporal de productos encontrados.
        # Agrega el nuevo mensaje del usuario al historial
        # utilizando el formato esperado por LangChain.
        state["messages"].append(HumanMessage(content=request.message))

        # 2. Ejecutar el grafo con el estado actualizado, con un timeout para
        #    no dejar el lock de la sesión (ni el request de .NET) colgado
        #    indefinidamente si el LLM o una tool se cuelga.
        try:
            # asyncio.wait_for establece un tiempo máximo de
            # ejecución para el grafo.
            result_state = await asyncio.wait_for(
                # Ejecuta el grafo utilizando el estado actual de la conversación.
                chat_graph.ainvoke(state), timeout=settings.graph_timeout_seconds # Tiempo máximo permitido para responder.
            )
        except asyncio.TimeoutError:
            logger.error("Timeout ejecutando el grafo del chatbot") 
            raise HTTPException(
                status_code=504, #Tiempo de espera de puerta de enlace
                detail="El chatbot tardó demasiado en responder. Intenta de nuevo.",
            )
        except RuntimeError as exc:
            # Tipicamente OPENAI_API_KEY ausente (agente lazy)
            logger.error(f"Configuración del chatbot incompleta: {exc}") # Servicio temporalmente no disponible.
            raise HTTPException(status_code=503, detail=str(exc))
        except Exception:
            logger.exception("Error ejecutando el grafo")
            raise HTTPException(
                status_code=500, detail="Error procesando el mensaje del chatbot."
            )

        # 3. Guardar el estado actualizado para la siguiente llamada
        save_state(request.session_id, result_state)

        # 4. Extraer el último mensaje del asistente para responder a .NET
        last_ai_message = next(
            (m for m in reversed(result_state["messages"]) if isinstance(m, AIMessage)),
            None, # Si por alguna razón no existe una respuesta, devuelve None.
        )
        # Obtiene únicamente el contenido textual del mensaje.
        response_text = last_ai_message.content if last_ai_message else "..."

        # 5. Si la conversación fue escalada, liberar la sesión de memoria
        #    (el bot ya no debe seguir participando, el asesor toma el control)
        if result_state.get("escalated"):
            clear_session(request.session_id)

        invoice_number = result_state.get("invoice_number")
        sale_origin = result_state.get("sale_origin")
        if invoice_number and not sale_origin:
            sale_origin = "CHATBOT"

        return ChatResponse(
            response=response_text, # Texto generado por el asistente.
            state=result_state.get("state", "IN_PROGRESS"), # Estado actual del flujo conversacional.
            invoice_number=invoice_number, # Número de factura generado.
            sale_origin=sale_origin, # Origen de la venta.
            products=result_state.get("found_products") or [], # Lista de productos encontrados.
        )
