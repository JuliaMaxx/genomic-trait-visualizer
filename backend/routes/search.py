from fastapi import APIRouter, Query

from backend.models import EvidenceLevel, SearchResponse, TraitCategory
from backend.services.active_traits import ActiveTraits

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/", response_model=SearchResponse)
async def search(
    traits: ActiveTraits,
    q: str = Query(default="", max_length=80),
    category: TraitCategory | None = Query(default=None),
    evidence_level: EvidenceLevel | None = Query(default=None),
    limit: int = Query(default=8, ge=1, le=20),
) -> SearchResponse:
    """Search is withheld until it can present the reviewed catalog correctly."""
    return SearchResponse(query=q, results=[])
