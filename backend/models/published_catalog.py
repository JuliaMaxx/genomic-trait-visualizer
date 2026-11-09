"""Compact offline publication schema 3.1; active application v2 is unchanged.

Models validate structure. Only the Stage 4 compiler checks Stage 3 decisions;
validating a hand-written catalog never establishes publication approval.
"""

from itertools import combinations_with_replacement
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .common import TraitCategory
from .curation import (
    ClaimType,
    CurationModel,
    EvidenceLocation,
    EvidenceSource,
    ExplanationText,
    Text,
    TraitDossier,
    require_references,
    require_unique_ids,
)
from .interpretation import AlleleCountInterpretation, EducationalInterpretation


def publication_structure_errors(trait: "TraitDossier | PublishedTrait") -> list[str]:
    """Shared completeness/content checks, independent of approval labels."""
    errors: list[str] = []
    if not trait.sources or not trait.evidence or not trait.claims:
        errors.append("published entries require sources, evidence and claims")
    if trait.interpretation is None:
        errors.append("published entries require an interpretation")
    if not trait.explanations:
        errors.append("published entries require explanations")
    if trait.interpretation is None:
        return errors
    if isinstance(trait.interpretation, EducationalInterpretation):
        if any(content.result_key is not None for content in trait.explanations):
            errors.append("educational entries cannot have result content")
        return errors

    result_keys = {str(rule.copies) for rule in trait.interpretation.rules}
    result_keys.add("unavailable")
    interpretation_claims = set(trait.interpretation.claim_ids)
    result_slots: set[tuple[str, str]] = set()
    for content in trait.explanations:
        if content.result_key is None:
            continue
        if content.result_key not in result_keys:
            errors.append("result_key must match an allele count or unavailable")
        slot = (content.kind, content.result_key)
        if slot in result_slots:
            errors.append("result content kind and result_key must be unique")
        result_slots.add(slot)
        if not interpretation_claims.intersection(content.claim_ids):
            errors.append("result content must reference an interpretation claim")
    return errors


class PublishedEvidence(CurationModel):
    evidence_id: Text
    claim_type: ClaimType
    statement: Text
    source_ids: list[Text] = Field(min_length=1, max_length=1)
    source_location: EvidenceLocation
    rsid: str | None = Field(default=None, pattern=r"^rs\d+$")
    gene: Text | None = None
    phenotype: Text | None = None
    effect_allele: Text | None = None
    effect_direction: Text | None = None


class PublishedClaim(CurationModel):
    claim_id: Text
    claim_type: ClaimType
    statement: Text
    evidence_ids: list[Text] = Field(min_length=1)
    scope: Text
    limitations: list[Text] = Field(min_length=1)


class PublishedTrait(CurationModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    name: Text
    category: TraitCategory
    description: Text
    sources: list[EvidenceSource] = Field(min_length=1)
    evidence: list[PublishedEvidence] = Field(min_length=1)
    claims: list[PublishedClaim] = Field(min_length=1)
    interpretation: Annotated[
        AlleleCountInterpretation | EducationalInterpretation,
        Field(discriminator="strategy"),
    ]
    explanations: list[ExplanationText] = Field(min_length=1)

    @model_validator(mode="after")
    def complete_and_traceable(self) -> "PublishedTrait":
        for records, field in (
            (self.sources, "source_id"),
            (self.evidence, "evidence_id"),
            (self.claims, "claim_id"),
            (self.explanations, "content_id"),
        ):
            require_unique_ids([getattr(item, field) for item in records], field)
        sources = {source.source_id for source in self.sources}
        evidence = {finding.evidence_id for finding in self.evidence}
        claims = {claim.claim_id for claim in self.claims}
        for finding in self.evidence:
            require_references(finding.source_ids, sources, "evidence sources")
        for claim in self.claims:
            require_references(claim.evidence_ids, evidence, "claim evidence")
        require_references(self.interpretation.claim_ids, claims, "model claims")
        for content in self.explanations:
            require_references(content.claim_ids, claims, "content claims")
        errors = publication_structure_errors(self)
        if errors:
            raise ValueError(errors[0])
        if not any(text.result_key is None for text in self.explanations):
            raise ValueError("publication requires a general explanation")
        if isinstance(self.interpretation, AlleleCountInterpretation):
            expected = {
                "".join(pair)
                for pair in combinations_with_replacement(
                    sorted(self.interpretation.requirements.alleles), 2
                )
            }
            if {rule.genotype for rule in self.interpretation.rules} != expected:
                raise ValueError("publication requires a complete genotype table")
            summaries = {
                text.result_key
                for text in self.explanations
                if text.kind == "outcome_summary"
            }
            if summaries != {"0", "1", "2", "unavailable"}:
                raise ValueError(
                    "publication requires outcome_summary for 0, 1, 2 and unavailable"
                )
        return self


class TraitCatalog(CurationModel):
    schema_version: Literal["3.1"]
    traits: list[PublishedTrait] = Field(min_length=1, max_length=1)
