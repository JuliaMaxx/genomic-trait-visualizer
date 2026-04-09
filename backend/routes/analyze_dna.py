from fastapi import APIRouter, UploadFile

from backend.models import TraitResult
from backend.services import analyze_traits, process_dna_file

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("/", response_model=list[TraitResult])
async def analyze_dna(file: UploadFile) -> list[TraitResult]:
    variants = await process_dna_file(file)
    results = analyze_traits(variants)
    return results
