"""Internal authoring contracts; validation does not establish scientific truth.

Legacy status labels (including ``validated`` and ``approved``) and assessments
are descriptive data only. Stage 3 derives approval from scoped review decisions
in services/trait_curation/workflow.py. AssessedClaim records a separate assessment
of source-reported findings. Publication remains a later stage.
"""

import re
from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from .common import EvidenceLevel, TraitCategory
from .interpretation import AlleleCountInterpretation, EducationalInterpretation


class CurationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


Text = Annotated[str, Field(min_length=1)]


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


class EvidenceLocation(CurationModel):
    locator: Text | None = None
    section: str | None = Field(default=None, min_length=1, max_length=200)
    page: str | None = Field(default=None, min_length=1, max_length=50)
    paragraph: int | None = Field(default=None, ge=1)
    table: str | None = Field(default=None, min_length=1, max_length=50)
    figure: str | None = Field(default=None, min_length=1, max_length=50)

    @model_validator(mode="after")
    def has_locator(self) -> "EvidenceLocation":
        if not any(self.model_dump().values()):
            raise ValueError("evidence location must identify a passage or data field")
        return self


class EvidenceSource(CurationModel):
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


class EvidenceClaim(CurationModel):
    """One finding from one source; assessed claims can combine several findings."""

    evidence_id: str = Field(
        min_length=1,
        max_length=128,
        validation_alias=AliasChoices("evidence_id", "claim_id"),
    )
    trait_id: str | None = Field(default=None, max_length=128)
    claim_type: ClaimType
    statement: str = Field(min_length=1, max_length=2000)
    rsid: str | None = Field(default=None, pattern=r"^rs\d+$", max_length=32)
    gene: str | None = Field(default=None, max_length=64)
    phenotype: str | None = Field(default=None, max_length=500)
    effect_allele: str | None = Field(default=None, max_length=32)
    effect_direction: str | None = Field(default=None, max_length=64)
    # Retain the recovered list shape, but give the locator exactly one source.
    source_ids: list[Text] = Field(min_length=1, max_length=1)
    source_passage: str | None = Field(default=None, max_length=1000)
    source_location: EvidenceLocation
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


class TraitCandidate(CurationModel):
    candidate_id: str = Field(min_length=1, max_length=128)
    revision: int = Field(default=1, ge=1)
    proposed_id: str = Field(min_length=1, max_length=128)
    proposed_name: str = Field(min_length=1, max_length=200)
    proposed_category: TraitCategory | None = None
    description: str | None = Field(default=None, max_length=2000)
    keywords: list[str] = Field(default_factory=list)
    evidence_ids: list[Text] = Field(
        default_factory=list,
        validation_alias=AliasChoices("evidence_ids", "claim_ids"),
    )
    source_ids: list[str] = Field(default_factory=list)
    pipeline_version: str = "manual"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: CandidateStatus = CandidateStatus.DRAFT
    reviewer_notes: list[str] = Field(default_factory=list)

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: datetime) -> datetime:
        return _require_timezone(value)  # type: ignore[return-value]


class ValidationFinding(CurationModel):
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


class EvidenceAssessment(CurationModel):
    assessment_id: str = Field(min_length=1, max_length=128)
    candidate_id: str = Field(min_length=1, max_length=128)
    evidence_level: EvidenceLevel | None = None
    replication_status: ReplicationStatus = ReplicationStatus.NOT_ASSESSED
    study_count: int | None = Field(default=None, ge=0)
    assessment_rationale: str | None = Field(
        default=None, min_length=1, max_length=4000
    )
    rubric_version: str = "evidence-rubric-v1"
    assessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed: bool = False

    @field_validator("assessed_at")
    @classmethod
    def validate_assessed_at(cls, value: datetime) -> datetime:
        return _require_timezone(value)  # type: ignore[return-value]


class ReviewDecision(CurationModel):
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


class AssessedClaim(CurationModel):
    """What the application proposes to say, assessed separately from extraction."""

    claim_id: Text
    claim_type: ClaimType
    statement: Text
    evidence_ids: list[Text] = Field(min_length=1)
    scope: Text
    limitations: list[Text] = Field(min_length=1)
    status: Literal["pending", "approved", "rejected"] = "pending"
    assessment: EvidenceAssessment | None = None

    @model_validator(mode="after")
    def decision_requires_assessment(self) -> "AssessedClaim":
        if self.status != "pending" and (
            self.assessment is None
            or not self.assessment.reviewed
            or not self.assessment.assessment_rationale
        ):
            raise ValueError("approved or rejected claims need a reviewed rationale")
        return self


class ExplanationContent(CurationModel):
    content_id: Text
    kind: Literal[
        "description",
        "simple_summary",
        "technical_summary",
        "mental_model",
        "model_limit_summary",
        "practical_takeaway",
        "simple_explanation",
        "technical_explanation",
        "research_spotlight",
        "calculation_notes",
        "card_tooltip",
        "headline",
        "headline_tooltip",
        "outcome_summary",
    ]
    title: Text | None = None
    body: Text
    claim_ids: list[Text] = Field(min_length=1)
    result_key: Text | None = None
    reviewed: bool = False
    # Opt in when otherwise general text discusses the interpretation's behavior.
    # Result content and inherently model-related kinds always depend on it.
    model_dependent: bool = False

    @model_validator(mode="after")
    def result_content_has_a_target(self) -> "ExplanationContent":
        result_specific = self.kind in {
            "card_tooltip",
            "headline",
            "headline_tooltip",
            "outcome_summary",
        }
        if result_specific != (self.result_key is not None):
            raise ValueError("result_key is required only for result-specific content")
        return self


def require_unique_ids(ids: list[str], label: str) -> None:
    if len(ids) != len(set(ids)):
        raise ValueError(f"{label} must be unique")


def require_references(refs: list[str], available: set[str], label: str) -> None:
    missing = set(refs) - available
    if missing:
        raise ValueError(f"{label} reference missing IDs: {sorted(missing)}")


class TraitDossier(CurationModel):
    """One self-contained trait, shared by authoring and the staged catalog."""

    candidate: TraitCandidate
    sources: list[EvidenceSource] = Field(default_factory=list)
    evidence: list[EvidenceClaim] = Field(default_factory=list)
    claims: list[AssessedClaim] = Field(default_factory=list)
    interpretation: Annotated[
        AlleleCountInterpretation | EducationalInterpretation | None,
        Field(discriminator="strategy"),
    ] = None
    explanations: list[ExplanationContent] = Field(default_factory=list)

    @model_validator(mode="after")
    def references_resolve(self) -> "TraitDossier":
        source_ids = [source.source_id for source in self.sources]
        evidence_ids = [finding.evidence_id for finding in self.evidence]
        claim_ids = [claim.claim_id for claim in self.claims]
        require_unique_ids(source_ids, "source IDs")
        require_unique_ids(evidence_ids, "evidence IDs")
        require_unique_ids(claim_ids, "assessed claim IDs")
        require_unique_ids(
            [content.content_id for content in self.explanations], "content IDs"
        )
        require_references(
            self.candidate.source_ids, set(source_ids), "candidate sources"
        )
        require_references(
            self.candidate.evidence_ids, set(evidence_ids), "candidate evidence"
        )
        for finding in self.evidence:
            require_references(finding.source_ids, set(source_ids), "evidence sources")
            if finding.trait_id not in (None, self.candidate.proposed_id):
                raise ValueError("evidence trait_id must match the dossier")
        for claim in self.claims:
            require_references(claim.evidence_ids, set(evidence_ids), "claim evidence")
            if (
                claim.assessment is not None
                and claim.assessment.candidate_id != self.candidate.candidate_id
            ):
                raise ValueError("assessment candidate_id must match the dossier")
        if self.interpretation is not None:
            require_references(
                self.interpretation.claim_ids, set(claim_ids), "interpretation claims"
            )
        for content in self.explanations:
            require_references(content.claim_ids, set(claim_ids), "content claims")
        return self
