from fastapi import APIRouter, HTTPException, UploadFile

from backend.models import TraitDefinition, TraitDetail
from backend.services.dna_service import process_dna_file
from backend.services.trait_curation import (
    get_trait_definition,
    list_trait_definitions,
)
from backend.services.trait_service import calculate_single_trait

router = APIRouter(prefix="/traits", tags=["traits"])


@router.get("/", response_model=list[TraitDefinition])
async def read_traits() -> list[TraitDefinition]:
    return list_trait_definitions()


@router.get("/{trait_id}", response_model=TraitDefinition)
async def read_trait(trait_id: str) -> TraitDefinition:
    trait = get_trait_definition(trait_id)
    if trait is None:
        raise HTTPException(status_code=404, detail="Trait not found")
    return trait


@router.post("/{trait_id}/evaluate")
async def evaluate_trait(trait_id: str, file: UploadFile) -> TraitDetail:
    variants = (await process_dna_file(file)).variants

    result = calculate_single_trait(trait_id, variants)
    if result is None:
        raise HTTPException(404)

    return result
