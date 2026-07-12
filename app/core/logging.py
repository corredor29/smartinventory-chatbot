import contextlib # Permite crear context managers mediante decoradores.
import logging # Librería estándar para el sistema de logs.
import sys # Permite enviar la salida del log a la consola.
import time # Utilizado para medir tiempos de ejecución.
# Variable de contexto que mantiene información independiente
# para cada tarea asíncrona.
from contextvars import ContextVar

from app.core.config import settings # Configuración general de la aplicación.

# Contexto de la sesión actual, para que cada línea de log emitida durante el
# procesamiento de un request (incluyendo dentro de las tools, que no siempre
# reciben session_id como argumento) quede etiquetada automáticamente sin
# tener que pasarlo manualmente por cada llamada a logger.
session_id_var: ContextVar[str] = ContextVar("session_id", default="-")


class SessionIdFilter(logging.Filter):
    
    """
    Filtro personalizado para el sistema de logging.

    Su función consiste en agregar automáticamente el
    identificador de la sesión a cada registro generado.

    De esta forma todos los logs quedan asociados a una
    conversación específica.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Agrega el session_id al registro actual.

        Parámetros:
            record:
                Registro de log que será modificado antes de
                imprimirse.

        Retorna:
            True para indicar que el log debe continuar su
            procesamiento.
        """
        record.session_id = session_id_var.get()
        return True


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout) # Crea un manejador que enviará los logs a la consola.
    handler.addFilter(SessionIdFilter()) # Agrega el filtro encargado de insertar el session_id.
    # Configuración global del sistema de logging.
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO), # Nivel de severidad.
        format="%(asctime)s | %(levelname)s | %(name)s | [session=%(session_id)s] | %(message)s", # Formato mostrado en cada línea del log.
        handlers=[handler], # Manejadores utilizados.
        force=True, # Reemplaza configuraciones anteriores.
    )

"""
Logger reutilizable por toda la aplicación.

Ejemplo:

logger.info("Producto encontrado")

logger.error("Error al consultar inventario")
"""

logger = logging.getLogger("smartinventory-chatbot")


@contextlib.contextmanager
def log_duration(operation: str):
    """
    Context manager para medir y loguear cuánto tarda una operación (llamada
    al LLM, ejecución de una tool, etc.). Loguea el resultado incluso si la
    operación lanza una excepción, para no perder visibilidad de fallos lentos.
    """
    start = time.perf_counter() # Registra el instante inicial.
    try:
        yield # Ejecuta el código contenido dentro del context manager.
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000 # Calcula el tiempo transcurrido.
        logger.info(f"{operation} completado en {elapsed_ms:.1f}ms") # Registra el resultado.
