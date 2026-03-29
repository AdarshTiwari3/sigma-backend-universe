from fastapi import APIRouter

from src.app.core.config import settings

router = APIRouter()


@router.get("/")
async def health_check():
    return {
        "status": "ok",
        "service": settings.app.SERVICE_NAME,
        "version": settings.app.VERSION,
    }
