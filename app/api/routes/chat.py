from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, AIMessage

from app.schemas.chat import ChatRequest, ChatResponse
from app.core.logging import logger
from app.graph.builder import chat_graph
from app.session.memory_store import (
    get_or_create_state,
    save_state,
    clear_session,
)

router = APIRouter()


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest) -> ChatResponse:
    """
    Recibe el mensaje del cliente (reenviado desde .NET), lo procesa a través
    del grafo de LangGraph, y devuelve la respuesta del bot.
    """
    logger.info(f"[{request.session_id}] Mensaje recibido: {request.message}")

    # 1. Recuperar (o crear) el estado de esta conversación
    state = get_or_create_state(request.session_id)
    state["messages"].append(HumanMessage(content=request.message))

    # 2. Ejecutar el grafo con el estado actualizado
    try:
        result_state = await chat_graph.ainvoke(state)
    except Exception as e:
        logger.error(f"[{request.session_id}] Error ejecutando el grafo: {e}")
        raise HTTPException(status_code=500, detail="Error procesando el mensaje del chatbot.")

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

    return ChatResponse(
        response=response_text,
        state=result_state.get("state", "IN_PROGRESS"),
        invoice_number=result_state.get("invoice_number"),
    )