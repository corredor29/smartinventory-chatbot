
# Librería estándar para manejo de tareas asíncronas
import asyncio
# Permite crear manejadores del ciclo de vida de FastAPI
from contextlib import asynccontextmanager
# Framework principal de la API
from fastapi import FastAPI
# Middleware para permitir peticiones desde frontend externos
from fastapi.middleware.cors import CORSMiddleware
# Cliente HTTP encargado de comunicarse con la API .NET
from app.clients.dotnet_client import dotnet_client
from app.core.config import settings # Configuración global del sistema
from app.core.logging import setup_logging, logger # Sistema de logs
from app.session.memory_store import purge_expired_sessions # Función encargada de eliminar sesiones expiradas
from app.api.routes import health, chat # Importación de rutas/endpoints

# Inicializa el sistema de logs al arrancar la aplicación.
# Esto permite registrar:
# - errores
# - eventos
# - tiempos de ejecución
# - actividad del chatbot
setup_logging()


async def _session_cleanup_loop() -> None:
    """
    Tarea de fondo que libera periódicamente las sesiones en memoria que
    llevan más de `session_ttl_seconds` sin actividad, para que el proceso no
    acumule memoria indefinidamente con conversaciones abandonadas.
    """
    while True:
        await asyncio.sleep(settings.session_cleanup_interval_seconds) # Espera el tiempo configurado antes de limpiar sesiones
        try:
            purge_expired_sessions()  # Elimina conversaciones expiradas/inactivas
        except Exception:
            logger.exception("Error durante el barrido de sesiones inactivas") # Registra cualquier error ocurrido durante la limpieza


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"{settings.app_name} iniciado en modo {settings.app_env}") # Log indicando inicio de la aplicación
    # Crea una tarea asíncrona en segundo plano
    # encargada de limpiar sesiones expiradas
    cleanup_task = asyncio.create_task(_session_cleanup_loop())
    try:
        yield # Mantiene viva la aplicación FastAPI
    finally:
        cleanup_task.cancel() # Cancela la tarea de limpieza
        try:
            await cleanup_task  # Espera a que la tarea termine correctamente
        except asyncio.CancelledError:
            pass # Ignora excepción normal de cancelación
        await dotnet_client.aclose() # Cierra conexiones HTTP abiertas con la API .NET
        logger.info(f"{settings.app_name} detenido")  # Log indicando apagado correcto


app = FastAPI(
    title=settings.app_name, # Nombre mostrado en Swagger/OpenAPI
    debug=settings.debug, # Activa/desactiva modo debug
    lifespan=lifespan, # Manejador del ciclo de vida
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list, # Lista de dominios permitidos
    allow_credentials=True, # Permite envío de cookies/autenticación
    allow_methods=["*"], # Permite todos los métodos HTTP
    allow_headers=["*"], # Permite todos los headers
)

app.include_router(health.router) # Endpoint de salud del sistema
app.include_router(chat.router, prefix="/chat", tags=["chat"]) # Endpoint principal del chatbot
