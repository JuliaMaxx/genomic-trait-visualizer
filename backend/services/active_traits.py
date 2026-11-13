"""Load an explicit release set once and connect Stage 6 to Stage 4."""

import os
from pathlib import Path
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import Field

from backend.models.api import ApiModel
from backend.models.curation import Text
from backend.models.interpretation import AlleleCountInterpretation
from backend.models.published_catalog import PublishedTrait, TraitCatalog
from backend.models.reviewed_api import (
    ReleaseIdentity,
    TraitAnalysisMetrics,
    TraitCatalogDetail,
)
from backend.services.dna_service import (
    IngestionResult,
    ingest_dna,
    match_observation,
)
from backend.services.trait_curation.compiler import sha256, stable_json, verify_release
from backend.services.trait_curation.offline import evaluate


class ReleaseSelection(ApiModel):
    releases: list[Text] = Field(min_length=1)


def load_active_traits() -> dict[str, TraitCatalogDetail]:
    selection_path = os.environ.get("WHOAMI_ACTIVE_RELEASE_SET")
    if not selection_path or not selection_path.strip():
        raise RuntimeError(
            "Set WHOAMI_ACTIVE_RELEASE_SET to a release selection JSON file"
        )
    selection_file = Path(selection_path).resolve()
    selection = ReleaseSelection.model_validate_json(
        selection_file.read_text(encoding="utf-8-sig")
    )
    traits: dict[str, PublishedTrait] = {}
    identities: dict[str, dict[str, str]] = {}
    for directory in selection.releases:
        release = (selection_file.parent / directory).resolve()
        manifest = verify_release(release)
        catalog_bytes = (release / "catalog.json").read_bytes()
        # Bind the loaded bytes to the verified manifest as well.
        if sha256(catalog_bytes) != manifest.files["catalog.json"]:
            raise ValueError(f"Release integrity check failed: {release}")
        trait = TraitCatalog.model_validate_json(catalog_bytes).traits[0]
        if trait.id in traits:
            raise ValueError(f"Duplicate trait ID in active releases: {trait.id}")
        traits[trait.id] = trait
        identities[trait.id] = {
            "release_id": manifest.release_id,
            "manifest_sha256": sha256((release / "manifest.json").read_bytes()),
        }
    # Paths and selection order do not describe scientific content.
    release_set_id = sha256(
        stable_json(
            [{"trait_id": key, **identities[key]} for key in sorted(identities)]
        )
    )
    return {
        key: TraitCatalogDetail.model_validate(
            {**trait.model_dump(), **identities[key], "release_set_id": release_set_id}
        )
        for key, trait in traits.items()
    }


def get_active_traits(request: Request) -> dict[str, TraitCatalogDetail]:
    traits = getattr(request.state, "active_traits", None)
    if traits is None:
        raise HTTPException(503, "Active releases have not been loaded")
    return cast(dict[str, TraitCatalogDetail], traits)


ActiveTraits = Annotated[dict[str, TraitCatalogDetail], Depends(get_active_traits)]


async def ingest_upload(file: UploadFile) -> IngestionResult:
    # Strict decoding: dropping invalid bytes could turn a malformed call into AA.
    try:
        # Only LF/CRLF delimit rows; other control characters stay in raw calls.
        lines = (await file.read()).decode("utf-8-sig").split("\n")
    except UnicodeDecodeError as error:
        raise HTTPException(
            415, "Unsupported DNA encoding; expected UTF-8 text"
        ) from error
    try:
        return await run_in_threadpool(ingest_dna, lines)
    except ValueError as error:
        raise HTTPException(415, str(error)) from error


def interpret_trait(
    trait: TraitCatalogDetail, ingestion: IngestionResult
) -> TraitAnalysisMetrics:
    # The offline evaluator accepts published fields, without API identity fields.
    published = PublishedTrait.model_validate(
        trait.model_dump(include=set(PublishedTrait.model_fields))
    )
    if isinstance(published.interpretation, AlleleCountInterpretation):
        match = match_observation(ingestion, published.interpretation.requirements)
        result = evaluate(published, match.observation)
        return TraitAnalysisMetrics(
            **result.model_dump(),
            observation_status=match.status,
            observation_diagnostics=match.diagnostics,
        )
    result = evaluate(published, None)
    return TraitAnalysisMetrics(
        **result.model_dump(), observation_status=None, observation_diagnostics=[]
    )


def release_identity(trait: TraitCatalogDetail) -> dict[str, str]:
    return trait.model_dump(include=set(ReleaseIdentity.model_fields))
