from fastapi import APIRouter

from src.app.core.config import settings

router = APIRouter()


@router.get("/health", tags=["system"])
async def health_check():
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
    }
