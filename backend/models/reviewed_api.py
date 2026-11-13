"""Public responses for verified releases; legacy engine models remain in api.py."""

from typing import Literal

from backend.services.dna_service import ObservationStatus
from backend.services.trait_curation.compiler import SHA256, ReleaseId
from backend.services.trait_curation.offline import OfflineResult

from .api import ApiModel
from .common import TraitCategory
from .curation import EvidenceSource
from .published_catalog import PublishedClaim, PublishedTrait

Strategy = Literal["allele_count", "educational"]


class ReleaseIdentity(ApiModel):
    release_id: ReleaseId
    manifest_sha256: SHA256
    release_set_id: SHA256


class TraitCatalogSummary(ReleaseIdentity):
    id: str
    name: str
    category: TraitCategory
    description: str
    strategy: Strategy


class TraitCatalogDetail(PublishedTrait, ReleaseIdentity):
    pass


class TraitAnalysisMetrics(OfflineResult):
    observation_status: ObservationStatus | None
    observation_diagnostics: list[str]


class TraitAnalysisSummary(TraitAnalysisMetrics, ReleaseIdentity):
    trait_id: str
    name: str
    strategy: Strategy
    sources: list[EvidenceSource]
    claims: list[PublishedClaim]


class TraitAnalysisDetail(ApiModel):
    trait: TraitCatalogDetail
    analysis: TraitAnalysisMetrics


class UploadError(ApiModel):
    detail: str
