import contextlib
import logging
import sys
import time
from contextvars import ContextVar

from app.core.config import settings

# Contexto de la sesión actual, para que cada línea de log emitida durante el
# procesamiento de un request (incluyendo dentro de las tools, que no siempre
# reciben session_id como argumento) quede etiquetada automáticamente sin
# tener que pasarlo manualmente por cada llamada a logger.
session_id_var: ContextVar[str] = ContextVar("session_id", default="-")


class SessionIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.session_id = session_id_var.get()
        return True


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(SessionIdFilter())

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | [session=%(session_id)s] | %(message)s",
        handlers=[handler],
        force=True,
    )


logger = logging.getLogger("smartinventory-chatbot")


@contextlib.contextmanager
def log_duration(operation: str):
    """
    Context manager para medir y loguear cuánto tarda una operación (llamada
    al LLM, ejecución de una tool, etc.). Loguea el resultado incluso si la
    operación lanza una excepción, para no perder visibilidad de fallos lentos.
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(f"{operation} completado en {elapsed_ms:.1f}ms")
