import json # Utilizado para interpretar respuestas JSON generadas por algunas herramientas. 

from langchain_core.messages import SystemMessage # Representa el mensaje del sistema enviado al modelo para definir su comportamiento.

from app.core.logging import log_duration, logger # Utilidades para registrar tiempos de ejecución y eventos del sistema.
from app.core.metrics import metrics # Contador de métricas del chatbot.
from app.graph.state import ChatState # Estado compartido entre todos los nodos del grafo.
from app.agents.agent import agent_model, SYSTEM_PROMPT # Modelo del agente y prompt principal del sistema.


def call_model(state: ChatState) -> dict:
    """
    Nodo principal: le pasa el historial de mensajes al agente (definido en
    app.agents.agent) y deja que decida si responde directo o invoca una tool.
    """
    messages = state["messages"]

    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT), *messages]

    """
    Registra información útil para monitorear la ejecución
    del chatbot.

    Se almacena:

        • Session ID.

        • Cantidad de mensajes enviados al modelo.
    """
    
    logger.info(f"[{state['session_id']}] Invocando modelo con {len(messages)} mensajes")

    with log_duration(f"[{state['session_id']}] Llamada al LLM"):
        response = agent_model.invoke(messages)

    return {"messages": [response]}


def mark_escalated(state: ChatState) -> dict:
    """
    Nodo que se ejecuta cuando la tool escalate_to_human fue invocada.
    Actualiza el estado de la conversación para que el backend .NET
    sepa que debe pasar a modo SignalR (chat en vivo con un asesor).
    """
    logger.info(f"[{state['session_id']}] Conversación escalada a asesor humano")
    metrics.increment("chatbot.escalations")
    return {"state": "WAITING_HUMAN_AGENT", "escalated": True}


def capture_sale_result(state: ChatState) -> dict:
    """
    Nodo que se ejecuta cuando la tool create_sale fue invocada. Extrae el
    número de factura del resultado de la tool hacia el estado de la
    conversación, para que `ChatResponse.invoice_number` (la respuesta que
    recibe .NET) refleje la venta real en vez de quedar siempre en None.

    Sin este nodo, el campo `invoice_number` declarado en el estado y en el
    schema de respuesta nunca se llenaba: ningún nodo lo escribía.
    """
    last_message = state["messages"][-1]
    content = last_message.content

    if isinstance(content, dict):
        payload = content
    else:
        try:
            payload = json.loads(content)
        except (TypeError, ValueError):
            logger.warning(
                f"[{state['session_id']}] No se pudo interpretar el resultado de create_sale"
            )
            return {}

    if not payload.get("success"): #Si la Tool indica que la venta no fue registrada, no se modifica el estado de la conversación.
        return {}

    metrics.increment("chatbot.sales.completed") #Incrementa el contador de ventas exitosas registradas por el chatbot.
    return {
        "invoice_number": payload.get("invoice_number"),
        "sale_origin": "CHATBOT",
        "state": "SALE_COMPLETED",
    }


def capture_search_result(state: ChatState) -> dict:
    """
    Extrae la lista de productos de search_product hacia el estado, para que
    .NET / el front puedan mostrar tarjetas estructuradas.
    """
    last_message = state["messages"][-1]
    content = last_message.content

    if isinstance(content, dict):
        payload = content
    else:
        try:
            payload = json.loads(content)
        except (TypeError, ValueError):
            return {}

    """
    Se obtiene la lista de productos encontrada por la Tool.

    Si no existe una lista válida, el estado permanece sin
    cambios.
    """
    products = payload.get("products") or []
    if not isinstance(products, list):
        return {}

    normalized = []
    for p in products:
        if not isinstance(p, dict):
            continue
        pid = p.get("productId") or p.get("product_id")
        if pid is None:
            continue
        normalized.append(
            {
                "product_id": int(pid), # Identificador del producto.
                "name": p.get("name") or "", # Nombre.
                "description": p.get("description"), # Descripción.
                "price": float(p.get("price") or 0), # Precio.
                "category_name": p.get("categoryName") or p.get("category_name") or "", # Categoría.
                "status_name": p.get("statusName") or p.get("status_name") or "", # Estado.
                "current_stock": int(p.get("currentStock") or p.get("current_stock") or 0), # Inventario disponible.
                "image_url": p.get("imageUrl") or p.get("image_url"),  # Imagen.
            }
        )

    # Si después de normalizar la lista no quedó ningún producto válido, no se modifica el estado.
    if not normalized:
        return {}

    """
    Registra la cantidad de productos preparados para ser
    enviados al frontend.

    Esta información facilita el monitoreo del chatbot.
    """
    
    logger.info(
        f"[{state['session_id']}] Capturados {len(normalized)} productos para el front"
    )
    return {"found_products": normalized}