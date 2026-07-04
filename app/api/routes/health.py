from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()

@router.get("/health", tags=["health"])
def health_check():
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }