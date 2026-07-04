import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.clients.dotnet_client import dotnet_client
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.session.memory_store import purge_expired_sessions
from app.api.routes import health, chat

setup_logging()


async def _session_cleanup_loop() -> None:
    """
    Tarea de fondo que libera periódicamente las sesiones en memoria que
    llevan más de `session_ttl_seconds` sin actividad, para que el proceso no
    acumule memoria indefinidamente con conversaciones abandonadas.
    """
    while True:
        await asyncio.sleep(settings.session_cleanup_interval_seconds)
        try:
            purge_expired_sessions()
        except Exception:
            logger.exception("Error durante el barrido de sesiones inactivas")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"{settings.app_name} iniciado en modo {settings.app_env}")
    cleanup_task = asyncio.create_task(_session_cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        await dotnet_client.aclose()
        logger.info(f"{settings.app_name} detenido")


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router, prefix="/chat", tags=["chat"])
