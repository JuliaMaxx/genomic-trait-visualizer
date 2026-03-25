from fastapi import APIRouter, UploadFile

from backend.models.schemas import TraitResult
from backend.services.dna_service import process_dna_file
from backend.services.trait_service import analyze_traits

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("/", response_model=list[TraitResult])
async def analyze_dna(file: UploadFile) -> list[TraitResult]:
    variants = await process_dna_file(file)
    results = analyze_traits(variants)
    return results
