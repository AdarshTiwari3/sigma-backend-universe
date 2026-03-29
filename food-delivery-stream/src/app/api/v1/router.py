from fastapi import APIRouter

from src.app.api.v1.endpoints import health, orders

api_v1_router = APIRouter()


api_v1_router.include_router(health.router, prefix="/health", tags=["Health"])
api_v1_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
