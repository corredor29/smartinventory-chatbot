import asyncio

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, AIMessage

from app.core.config import settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.core.logging import logger, session_id_var
from app.core.metrics import metrics
from app.graph.builder import chat_graph
from app.session.memory_store import (
    get_or_create_state,
    save_state,
    clear_session,
    session_lock,
)

router = APIRouter()


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest) -> ChatResponse:
    """
    Recibe el mensaje del cliente (reenviado desde .NET), lo procesa a través
    del grafo de LangGraph, y devuelve la respuesta del bot.
    """
    token = session_id_var.set(request.session_id)
    try:
        return await _process_message(request)
    finally:
        session_id_var.reset(token)


async def _process_message(request: ChatRequest) -> ChatResponse:
    metrics.increment("chatbot.messages.received")
    logger.info(f"Mensaje recibido: {request.message}")

    # El lock serializa el procesamiento de mensajes que lleguen casi
    # simultáneamente para la misma sesión: sin esto, dos requests
    # concurrentes sobre el mismo session_id podrían pisarse el estado entre
    # sí (uno de los dos resultados del grafo se perdería al guardar).
    async with session_lock(request.session_id):
        # 1. Recuperar (o crear) el estado de esta conversación
        state = get_or_create_state(request.session_id)
        state["found_products"] = None
        state["messages"].append(HumanMessage(content=request.message))

        # 2. Ejecutar el grafo con el estado actualizado, con un timeout para
        #    no dejar el lock de la sesión (ni el request de .NET) colgado
        #    indefinidamente si el LLM o una tool se cuelga.
        try:
            result_state = await asyncio.wait_for(
                chat_graph.ainvoke(state), timeout=settings.graph_timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.error("Timeout ejecutando el grafo del chatbot")
            raise HTTPException(
                status_code=504,
                detail="El chatbot tardó demasiado en responder. Intenta de nuevo.",
            )
        except RuntimeError as exc:
            # Tipicamente OPENAI_API_KEY ausente (agente lazy)
            logger.error(f"Configuración del chatbot incompleta: {exc}")
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
            None,
        )
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
            response=response_text,
            state=result_state.get("state", "IN_PROGRESS"),
            invoice_number=invoice_number,
            sale_origin=sale_origin,
            products=result_state.get("found_products") or [],
        )
