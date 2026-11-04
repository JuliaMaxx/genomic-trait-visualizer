from fastapi import APIRouter, UploadFile

from backend.models import TraitAnalysisSummary
from backend.services import calculate_traits, process_dna_file

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("/", response_model=list[TraitAnalysisSummary])
async def analyze_dna(file: UploadFile) -> list[TraitAnalysisSummary]:
    variants = (await process_dna_file(file)).variants
    results = calculate_traits(variants)
    return results
