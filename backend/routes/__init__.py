from fastapi import APIRouter

from .analyze_dna import router as analyze_router
from .search import router as search_router
from .traits import router as traits_router
from .traits import rsid_router

router = APIRouter()
router.include_router(analyze_router)
router.include_router(traits_router)
router.include_router(rsid_router)
router.include_router(search_router)

__all__ = ["router"]
