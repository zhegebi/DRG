from fastapi import APIRouter
from .hello import hello_router


# Create main API router
router = APIRouter()

# Include sub-routers
router.include_router(hello_router, prefix="/hello")

__all__ = ["router"]