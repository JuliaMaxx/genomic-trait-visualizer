from fastapi import APIRouter, File, UploadFile

from backend.models.schemas import Variant
from backend.services.dna_service import process_dna_file

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/")
async def upload_dna(file: UploadFile = File(...)) -> list[Variant]:
    variants = await process_dna_file(file)

    return variants[:10]
