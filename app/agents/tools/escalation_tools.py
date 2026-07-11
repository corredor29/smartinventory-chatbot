from typing import Any

from langchain_core.tools import tool

from app.agents.tools.common import with_tool_error_handling
from app.clients.dotnet_client import DotnetBusinessError, dotnet_client
from app.core.logging import logger


@tool
@with_tool_error_handling(
    fallback={
        "success": False,
        "message": "Hubo un problema al conectarte con un asesor. Por favor intenta de nuevo en unos minutos.",
    }
)
async def escalate_to_human(session_id: str, reason: str) -> dict[str, Any]:
    """
    Escala la conversación completa a un asesor humano cuando NO puedes resolver
    la solicitud del cliente tú mismo. Úsala cuando el cliente pida hablar con una
    persona, confirme que quiere un asesor (dijo "sí" tras ofrecérselo), pregunte
    por garantías/devoluciones/reclamos, haga una pregunta fuera del alcance de
    ventas, o muestre frustración evidente.

    IMPORTANTE: el cliente debe estar registrado/logueado. Si la API responde que
    necesita iniciar sesión, NO digas que ya lo conectaste: explícale que debe
    iniciar sesión o registrarse para hablar con un asesor.

    Args:
        session_id: identificador de la sesión de chat actual.
        reason: resumen breve y claro de por qué se está escalando la conversación.
    """
    logger.info(f"[{session_id}] Escalando a asesor humano. Motivo: {reason}")

    payload = {"sessionId": session_id, "reason": reason}
    try:
        result = await dotnet_client.post("/chat/escalate", json=payload)
    except DotnetBusinessError as exc:
        # 400: típicamente "Debes iniciar sesión para hablar con un asesor"
        detail = exc.detail
        message = detail
        try:
            import json

            parsed = json.loads(detail) if isinstance(detail, str) else detail
            if isinstance(parsed, dict):
                message = parsed.get("message") or parsed.get("detail") or detail
        except (TypeError, ValueError):
            pass
        return {
            "success": False,
            "requires_login": True,
            "message": message
            or "Debes iniciar sesión o registrarte para hablar con un asesor.",
        }

    return {
        "success": True,
        "escalation_id": result.get("escalation_id")
        or result.get("chatEscalationId")
        or result.get("chat_escalation_id"),
        "message": "Te estoy conectando con un asesor humano, en un momento te atiende.",
    }


@tool
@with_tool_error_handling(fallback={"success": False})
async def notify_advisor(
    session_id: str, notification_type: str, details: str, sale_id: int | None = None
) -> dict[str, Any]:
    """
    Envía una notificación a un asesor SIN escalar ni pausar la conversación con
    el cliente (el bot sigue atendiendo normalmente). Úsala en dos casos:

    1. notification_type="shipping_verification": siempre que una venta se registre
       exitosamente, para que un asesor verifique manualmente el envío antes de
       despachar el producto. Todo método de pago es aceptado, pero el envío
       SIEMPRE requiere esta verificación humana antes de salir.

    2. notification_type="sale_problem": cuando ocurra un problema al intentar
       registrar una venta (ej. create_sale falló). Explica en 'details' qué pasó
       exactamente para que el asesor pueda revisar y corregir la venta manualmente.

    Args:
        session_id: identificador de la sesión de chat actual.
        notification_type: "shipping_verification" o "sale_problem".
        details: descripción clara de la situación (qué se compró, qué falló, etc.).
        sale_id: identificador de la venta relacionada, si ya existe.
    """
    logger.info(f"[{session_id}] Notificando asesor ({notification_type}): {details}")

    payload = {
        "sessionId": session_id,
        "notificationType": notification_type,
        "details": details,
        "saleId": sale_id,
    }
    await dotnet_client.post("/chat/notify-advisor", json=payload)
    return {"success": True}
