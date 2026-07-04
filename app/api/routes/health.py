from fastapi import APIRouter

from app.core.config import settings
from app.core.metrics import metrics
from app.session.memory_store import get_active_session_count

router = APIRouter()


@router.get("/health", tags=["health"])
def health_check():
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


@router.get("/health/metrics", tags=["health"])
def health_metrics():
    """
    Métricas básicas en memoria (escalamientos, resultados de tools, etc.)
    para diagnóstico rápido. No reemplaza un backend de métricas real
    (Prometheus/Grafana) si el proyecto crece, ver resumen de recomendaciones.
    """
    return {
        "active_sessions": get_active_session_count(),
        "counters": metrics.snapshot(),
    }