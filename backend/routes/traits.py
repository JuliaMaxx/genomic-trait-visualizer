from fastapi import APIRouter, HTTPException, UploadFile

from backend.models import RsidCatalogItem, RsidDetail
from backend.models.reviewed_api import (
    TraitAnalysisDetail,
    TraitCatalogDetail,
    TraitCatalogSummary,
    UploadError,
)
from backend.services.active_traits import (
    ActiveTraits,
    ingest_upload,
    interpret_trait,
    release_identity,
)

router = APIRouter(prefix="/traits", tags=["traits"])


@router.get("/", response_model=list[TraitCatalogSummary])
async def read_traits(traits: ActiveTraits) -> list[TraitCatalogSummary]:
    return [
        TraitCatalogSummary.model_validate(
            {
                **trait.model_dump(include={"id", "name", "category", "description"}),
                **release_identity(trait),
                "strategy": trait.interpretation.strategy,
            }
        )
        for trait in traits.values()
    ]


@router.get("/{trait_id}", response_model=TraitCatalogDetail)
async def read_trait(trait_id: str, traits: ActiveTraits) -> TraitCatalogDetail:
    trait = traits.get(trait_id)
    if trait is None:
        raise HTTPException(status_code=404, detail="Trait not found")
    return trait


@router.post(
    "/{trait_id}/evaluate",
    response_model=TraitAnalysisDetail,
    responses={415: {"model": UploadError, "description": "Unsupported DNA upload"}},
)
async def evaluate_trait(
    trait_id: str, file: UploadFile, traits: ActiveTraits
) -> TraitAnalysisDetail:
    trait = traits.get(trait_id)
    if trait is None:
        raise HTTPException(404, "Trait not found")
    ingestion = await ingest_upload(file)
    return TraitAnalysisDetail(trait=trait, analysis=interpret_trait(trait, ingestion))


rsid_router = APIRouter(prefix="/rsids", tags=["rsids"])


@rsid_router.get("/", response_model=list[RsidCatalogItem])
async def read_rsids(traits: ActiveTraits) -> list[RsidCatalogItem]:
    """Marker browsing is withheld until it can present published content."""
    return []


@rsid_router.get("/{rsid}", response_model=RsidDetail)
async def read_rsid(rsid: str, traits: ActiveTraits) -> RsidDetail:
    raise HTTPException(status_code=404, detail="rsID browsing is unavailable")
