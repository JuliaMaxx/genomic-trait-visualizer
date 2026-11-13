from fastapi import APIRouter, UploadFile

from backend.models.reviewed_api import TraitAnalysisSummary, UploadError
from backend.services.active_traits import (
    ActiveTraits,
    ingest_upload,
    interpret_trait,
    release_identity,
)

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post(
    "/",
    response_model=list[TraitAnalysisSummary],
    responses={415: {"model": UploadError, "description": "Unsupported DNA upload"}},
)
async def analyze_dna(
    file: UploadFile, traits: ActiveTraits
) -> list[TraitAnalysisSummary]:
    ingestion = await ingest_upload(file)
    return [
        TraitAnalysisSummary.model_validate(
            {
                **interpret_trait(trait, ingestion).model_dump(),
                **release_identity(trait),
                "trait_id": trait.id,
                "name": trait.name,
                "strategy": trait.interpretation.strategy,
                "sources": trait.sources,
                "claims": trait.claims,
            }
        )
        for trait in traits.values()
    ]
