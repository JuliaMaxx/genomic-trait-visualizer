"""Successor TraitCatalog contract, staged separately from the active v2 catalog.

This validates catalog structure, not a release or its approval history. The
application continues importing backend.models.catalog until runtime migration.
Full dossiers are reused only for Stage 2 validation. Stage 4 must define the
smaller published payload before any runtime release is built.
"""

from typing import Literal

from pydantic import Field, model_validator

from .curation import (
    CandidateStatus,
    ClaimStatus,
    CurationModel,
    TraitDossier,
    require_unique_ids,
)
from .interpretation import EducationalInterpretation


class TraitCatalog(CurationModel):
    schema_version: Literal["3.0"]
    traits: list[TraitDossier] = Field(min_length=1)

    @model_validator(mode="after")
    def published_entries_are_complete_and_reviewed(self) -> "TraitCatalog":
        require_unique_ids(
            [trait.candidate.proposed_id for trait in self.traits], "trait IDs"
        )
        for trait in self.traits:
            if trait.candidate.status != CandidateStatus.APPROVED:
                raise ValueError("published candidates must be approved")
            if not trait.sources or not trait.evidence or not trait.claims:
                raise ValueError(
                    "published entries require sources, evidence and claims"
                )
            if trait.interpretation is None:
                raise ValueError("published entries require an interpretation")
            if not trait.explanations:
                raise ValueError("published entries require explanations")
            if any(claim.status != "approved" for claim in trait.claims):
                raise ValueError("published catalog claims must be approved")
            # A finding's legacy pending label may remain; scientific statements
            # need their own assessed-claim approval. Explicit concerns still block.
            if any(
                finding.status in {ClaimStatus.REJECTED, ClaimStatus.NEEDS_REVIEW}
                for finding in trait.evidence
            ):
                raise ValueError("published evidence cannot be rejected or need review")
            if any(not content.reviewed for content in trait.explanations):
                raise ValueError("published explanations must be reviewed")

            if isinstance(trait.interpretation, EducationalInterpretation):
                if any(
                    content.result_key is not None for content in trait.explanations
                ):
                    raise ValueError("educational entries cannot have result content")
                continue

            result_keys = {str(rule.copies) for rule in trait.interpretation.rules}
            result_keys.add("unavailable")
            interpretation_claims = set(trait.interpretation.claim_ids)
            result_slots: set[tuple[str, str]] = set()
            for content in trait.explanations:
                if content.result_key is None:
                    continue
                if content.result_key not in result_keys:
                    raise ValueError(
                        "result_key must match an allele count or unavailable"
                    )
                slot = (content.kind, content.result_key)
                if slot in result_slots:
                    raise ValueError(
                        "result content kind and result_key must be unique"
                    )
                result_slots.add(slot)
                if not interpretation_claims.intersection(content.claim_ids):
                    raise ValueError(
                        "result content must reference an interpretation claim"
                    )
        return self
