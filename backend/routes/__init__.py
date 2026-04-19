from fastapi import APIRouter

from .analyze_dna import router as analyze_router
from .traits import router as traits_router

router = APIRouter()
router.include_router(analyze_router)
router.include_router(traits_router)

__all__ = ["router"]
