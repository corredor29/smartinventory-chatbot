import functools
import time
from typing import Any, Awaitable, Callable, TypeVar

from app.clients.dotnet_client import DotnetBusinessError, DotnetConnectionError
from app.core.logging import logger
from app.core.metrics import metrics

F = TypeVar("F", bound=Callable[..., Awaitable[dict[str, Any]]])


def with_tool_error_handling(fallback: dict[str, Any]) -> Callable[[F], F]:
    """
    Decorador para las funciones async que respaldan las tools del agente.
    Centraliza lo que antes se repetía igual en cada tool: medir cuánto tarda
    la llamada a la API .NET, loguearla, y devolver un dict de fallback
    (nunca lanzar la excepción hacia el agente) distinguiendo:
      - DotnetConnectionError: problema de red/timeout.
      - DotnetBusinessError: la API .NET respondió con un error (4xx/5xx).
      - Cualquier otra excepción no prevista.

    `fallback` es el dict "de forma correcta" que espera el LLM cuando la
    tool falla (ej. {"found": False, "products": []}); se le agrega siempre
    la clave "error" con el detalle de qué pasó.

    Se aplica DEBAJO de `@tool` (es decir, se define primero) para que
    `@tool` siga viendo la firma y el docstring originales de la función a
    través de `functools.wraps` (que preserva `__wrapped__`, usado por
    `inspect.signature`).
    """

    def decorator(func: F) -> F:
        tool_name = func.__name__

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start) * 1000
                logger.info(f"Tool '{tool_name}' OK en {elapsed_ms:.1f}ms")
                metrics.increment(f"tool.{tool_name}.success")
                return result
            except DotnetConnectionError as exc:
                logger.error(f"Tool '{tool_name}' no pudo contactar a la API .NET: {exc}")
                metrics.increment(f"tool.{tool_name}.connection_error")
                return {**fallback, "error": str(exc)}
            except DotnetBusinessError as exc:
                logger.error(
                    f"Tool '{tool_name}' recibió un error de negocio de la API .NET "
                    f"({exc.status_code}): {exc.detail}"
                )
                metrics.increment(f"tool.{tool_name}.business_error")
                return {**fallback, "error": str(exc)}
            except Exception as exc:  # noqa: BLE001 - frontera con el agente: nunca debe romper el turno
                logger.exception(f"Tool '{tool_name}' falló de forma inesperada: {exc}")
                metrics.increment(f"tool.{tool_name}.unexpected_error")
                return {**fallback, "error": "Error inesperado del sistema."}

        return wrapper  # type: ignore[return-value]

    return decorator
