from fastapi import APIRouter, Query

from backend.models import SearchResponse
from backend.services.trait_curation import search_catalog

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/", response_model=SearchResponse)
async def search(
    q: str = Query(default="", max_length=80),
    category: str | None = Query(default=None),
    evidence_level: str | None = Query(default=None),
    limit: int = Query(default=8, ge=1, le=20),
) -> SearchResponse:
    return search_catalog(
        q,
        category=category,
        evidence_level=evidence_level,
        limit=limit,
    )
