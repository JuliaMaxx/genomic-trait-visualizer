"""Recovered internal authoring records; these do not authorize publication.

Legacy status labels (including ``validated`` and ``approved``), assessments and
review actions are descriptive data only. No runtime or approval workflow consumes
them. See data/legacy/3ffbaf3/README.md for provenance and deferred limitations.
"""

import re
from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from .common import EvidenceLevel, TraitCategory


def _require_timezone(value: datetime | None) -> datetime | None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError("timestamps must include a timezone")
    return value


class SourceType(StrEnum):
    SCIENTIFIC_PUBLICATION = "scientific_publication"
    VARIANT_DATABASE = "variant_database"
    ASSOCIATION_DATABASE = "association_database"
    REVIEW_ARTICLE = "review_article"
    OTHER = "other"


class ClaimType(StrEnum):
    TRAIT_ASSOCIATION = "trait_association"
    VARIANT_EFFECT = "variant_effect"
    GENE_FUNCTION = "gene_function"
    BIOLOGICAL_MECHANISM = "biological_mechanism"
    POPULATION_LIMITATION = "population_limitation"
    STUDY_LIMITATION = "study_limitation"
    OTHER = "other"


class ExtractionMethod(StrEnum):
    STRUCTURED_API = "structured_api"
    RULE_BASED = "rule_based"
    LLM = "llm"
    MANUAL = "manual"


class ClaimStatus(StrEnum):
    PENDING = "pending"
    VALIDATED = "validated"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


class CandidateStatus(StrEnum):
    DRAFT = "draft"
    RETRIEVED = "retrieved"
    VALIDATING = "validating"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class FindingSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ReplicationStatus(StrEnum):
    INDEPENDENT_REPLICATION_FOUND = "independent_replication_found"
    PARTIAL_REPLICATION = "partial_replication"
    NOT_ESTABLISHED = "not_established"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    NOT_ASSESSED = "not_assessed"


class ReviewAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"


class EvidenceLocation(BaseModel):
    section: str | None = Field(default=None, max_length=200)
    page: str | None = Field(default=None, max_length=50)
    paragraph: int | None = Field(default=None, ge=1)
    table: str | None = Field(default=None, max_length=50)
    figure: str | None = Field(default=None, max_length=50)


class EvidenceSource(BaseModel):
    source_id: str = Field(min_length=1, max_length=128)
    source_type: SourceType
    name: str = Field(min_length=1, max_length=200)
    url: str | None = Field(default=None, max_length=2048)
    title: str | None = Field(default=None, max_length=500)
    doi: str | None = Field(default=None, max_length=128)
    pmid: str | None = Field(default=None, max_length=32)
    pmcid: str | None = Field(default=None, max_length=32)
    publication_year: int | None = Field(default=None, ge=1500, le=2200)
    retrieved_at: datetime | None = None
    source_version: str | None = Field(default=None, max_length=128)

    @field_validator("retrieved_at")
    @classmethod
    def validate_retrieved_at(cls, value: datetime | None) -> datetime | None:
        return _require_timezone(value)

    @field_validator("url")
    @classmethod
    def validate_http_url(cls, value: str | None) -> str | None:
        if value is not None and not re.match(r"^https?://[^\s]+$", value):
            raise ValueError("url must be an absolute http or https URL")
        return value

    @field_validator("pmid")
    @classmethod
    def validate_pmid(cls, value: str | None) -> str | None:
        if value is not None and not value.isdigit():
            raise ValueError("pmid must contain digits only")
        return value

    @field_validator("pmcid")
    @classmethod
    def validate_pmcid(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"PMC\d+", value, re.IGNORECASE):
            raise ValueError("pmcid must use the PMC followed by digits format")
        return value


class EvidenceClaim(BaseModel):
    """A source-reported proposal, not an assessed application claim."""

    claim_id: str = Field(min_length=1, max_length=128)
    trait_id: str | None = Field(default=None, max_length=128)
    claim_type: ClaimType
    statement: str = Field(min_length=1, max_length=2000)
    rsid: str | None = Field(default=None, pattern=r"^rs\d+$", max_length=32)
    gene: str | None = Field(default=None, max_length=64)
    phenotype: str | None = Field(default=None, max_length=500)
    effect_allele: str | None = Field(default=None, max_length=32)
    effect_direction: str | None = Field(default=None, max_length=64)
    source_ids: list[str] = Field(min_length=1)
    source_passage: str | None = Field(default=None, max_length=1000)
    source_location: EvidenceLocation | None = None
    extraction_method: ExtractionMethod
    extractor_version: str | None = Field(default=None, max_length=128)
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    extraction_confidence: float | None = Field(default=None, ge=0, le=1)
    status: ClaimStatus = ClaimStatus.PENDING
    validation_notes: list[str] = Field(default_factory=list)

    @field_validator("extracted_at")
    @classmethod
    def validate_extracted_at(cls, value: datetime) -> datetime:
        return _require_timezone(value)  # type: ignore[return-value]


class TraitCandidate(BaseModel):
    candidate_id: str = Field(min_length=1, max_length=128)
    revision: int = Field(default=1, ge=1)
    proposed_id: str = Field(min_length=1, max_length=128)
    proposed_name: str = Field(min_length=1, max_length=200)
    proposed_category: TraitCategory | None = None
    description: str | None = Field(default=None, max_length=2000)
    keywords: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    pipeline_version: str = "manual"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: CandidateStatus = CandidateStatus.DRAFT
    reviewer_notes: list[str] = Field(default_factory=list)

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: datetime) -> datetime:
        return _require_timezone(value)  # type: ignore[return-value]


class ValidationFinding(BaseModel):
    finding_id: str = Field(min_length=1, max_length=128)
    candidate_id: str = Field(min_length=1, max_length=128)
    claim_id: str | None = Field(default=None, max_length=128)
    check_name: str = Field(min_length=1, max_length=128)
    severity: FindingSeverity
    message: str = Field(min_length=1, max_length=2000)
    passed: bool
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: datetime) -> datetime:
        return _require_timezone(value)  # type: ignore[return-value]


class EvidenceAssessment(BaseModel):
    assessment_id: str = Field(min_length=1, max_length=128)
    candidate_id: str = Field(min_length=1, max_length=128)
    evidence_level: EvidenceLevel | None = None
    replication_status: ReplicationStatus = ReplicationStatus.NOT_ASSESSED
    study_count: int | None = Field(default=None, ge=0)
    assessment_rationale: str | None = Field(default=None, max_length=4000)
    rubric_version: str = "evidence-rubric-v1"
    assessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed: bool = False

    @field_validator("assessed_at")
    @classmethod
    def validate_assessed_at(cls, value: datetime) -> datetime:
        return _require_timezone(value)  # type: ignore[return-value]


class ReviewDecision(BaseModel):
    decision_id: str = Field(min_length=1, max_length=128)
    candidate_id: str = Field(min_length=1, max_length=128)
    candidate_revision: int = Field(ge=1)
    action: ReviewAction
    reviewer_id: str = Field(min_length=1, max_length=128)
    claim_ids_reviewed: list[str] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=4000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: datetime) -> datetime:
        return _require_timezone(value)  # type: ignore[return-value]
