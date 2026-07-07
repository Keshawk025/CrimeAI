from fastapi import APIRouter

from app.api.v1 import enkrypt_health, firs, health, qdrant_health

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(qdrant_health.router)
api_router.include_router(enkrypt_health.router)
api_router.include_router(firs.router)
