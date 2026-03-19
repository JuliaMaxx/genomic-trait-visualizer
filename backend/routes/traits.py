from fastapi import APIRouter

from backend.models.schemas import TraitResult, Variant
from backend.services.trait_service import analyze_traits

router = APIRouter(prefix="/traits", tags=["traits"])


@router.post("/", response_model=list[TraitResult])
def analyze(variants: list[Variant]) -> list[TraitResult]:
    return analyze_traits(variants)
