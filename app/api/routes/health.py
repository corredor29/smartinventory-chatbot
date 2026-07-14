# APIRouter permite agrupar endpoints relacionados para
# posteriormente registrarlos dentro de FastAPI.
from fastapi import APIRouter
# Configuración general de la aplicación.
#
# Se utiliza para obtener información como:
#
# • Nombre del servicio.
# • Entorno de ejecución.
from app.core.config import settings
# Sistema de métricas en memoria.
#
# Permite consultar los contadores registrados por el
# chatbot durante su ejecución.
from app.core.metrics import metrics
# Función encargada de obtener la cantidad de sesiones
# activas almacenadas actualmente en memoria
from app.session.memory_store import get_active_session_count

"""
Cada conjunto de endpoints posee su propio APIRouter.

Este router será registrado posteriormente desde main.py
mediante:

app.include_router(health.router)
"""

router = APIRouter()


@router.get("/health", tags=["health"])
def health_check():
    return {
        "status": "ok", # Estado general del servicio.
        "service": settings.app_name, # Nombre configurado de la aplicación.
        "environment": settings.app_env,  # Entorno donde se está ejecutando
    }


@router.get("/health/metrics", tags=["health"])
def health_metrics():
    """
    Métricas básicas en memoria (escalamientos, resultados de tools, etc.)
    para diagnóstico rápido. No reemplaza un backend de métricas real
    (Prometheus/Grafana) si el proyecto crece, ver resumen de recomendaciones.
    """
    return {
        "active_sessions": get_active_session_count(), # Cantidad de conversaciones activas almacenadas actualmente en memoria.
        "counters": metrics.snapshot(), # Copia de todos los contadores registrados durante la ejecución del chatbot.
    }