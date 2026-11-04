from fastapi import APIRouter, HTTPException, UploadFile

from backend.models import (
    RsidCatalogItem,
    RsidDetail,
    TraitAnalysisDetail,
    TraitCatalogDetail,
    TraitCatalogSummary,
)
from backend.services.dna_service import process_dna_file
from backend.services.trait_curation import (
    get_rsid_detail,
    get_trait_definition,
    list_rsid_catalog,
    list_trait_summaries,
    trait_catalog_detail,
)
from backend.services.trait_service import calculate_single_trait

router = APIRouter(prefix="/traits", tags=["traits"])


@router.get("/", response_model=list[TraitCatalogSummary])
async def read_traits() -> list[TraitCatalogSummary]:
    return list_trait_summaries()


@router.get("/{trait_id}", response_model=TraitCatalogDetail)
async def read_trait(trait_id: str) -> TraitCatalogDetail:
    trait = get_trait_definition(trait_id)
    if trait is None:
        raise HTTPException(status_code=404, detail="Trait not found")
    return trait_catalog_detail(trait)


@router.post("/{trait_id}/evaluate", response_model=TraitAnalysisDetail)
async def evaluate_trait(trait_id: str, file: UploadFile) -> TraitAnalysisDetail:
    variants = (await process_dna_file(file)).variants

    result = calculate_single_trait(trait_id, variants)
    if result is None:
        raise HTTPException(404)

    return result


rsid_router = APIRouter(prefix="/rsids", tags=["rsids"])


@rsid_router.get("/", response_model=list[RsidCatalogItem])
async def read_rsids() -> list[RsidCatalogItem]:
    return list_rsid_catalog()


@rsid_router.get("/{rsid}", response_model=RsidDetail)
async def read_rsid(rsid: str) -> RsidDetail:
    detail = get_rsid_detail(rsid)
    if detail is None:
        raise HTTPException(status_code=404, detail="rsID not found")
    return detail
