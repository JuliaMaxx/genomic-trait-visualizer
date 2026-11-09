"""Pure, deliberately narrow interpretation for publication checks, not uploads."""

from typing import Literal

from pydantic import ConfigDict, Field, model_validator

from backend.models.curation import CurationModel, ExplanationText
from backend.models.interpretation import EducationalInterpretation
from backend.models.published_catalog import PublishedTrait

UnavailableReason = Literal[
    "missing_genotype",
    "invalid_genotype",
    "unsupported_allele",
    "missing_representation",
    "unsupported_build",
    "unsupported_orientation",
    "incompatible_representation",
]


class Observation(CurationModel):
    """Explicit test input. None means unknown; no provider conventions inferred."""

    model_config = ConfigDict(extra="forbid", strict=True)
    genotype: str | None = None
    rsid: str | None = None
    genome_build: str | None = None
    chromosome: str | None = None
    position: int | None = None
    sequence_accession: str | None = None
    orientation: str | None = None
    coordinate_system: str | None = None
    ploidy: int | None = None


class Outcome(CurationModel):
    status: Literal["evaluated", "unavailable", "educational"]
    copies: int | None = Field(default=None, ge=0, le=2, strict=True)
    reason: UnavailableReason | None = None

    @model_validator(mode="after")
    def consistent_result(self) -> "Outcome":
        if (self.status == "evaluated") != (self.copies is not None):
            raise ValueError("only evaluated outcomes have allele copies")
        if (self.status == "unavailable") != (self.reason is not None):
            raise ValueError("only unavailable outcomes have a reason")
        return self


class OfflineResult(Outcome):
    explanations: list[ExplanationText]


def evaluate(trait: PublishedTrait, observation: Observation | None) -> OfflineResult:
    """Return a count or reviewed education; never infer an observation's metadata."""
    # Revalidate even model instances, since Pydantic objects can be mutated.
    trait = PublishedTrait.model_validate(trait.model_dump(mode="json"))
    model = trait.interpretation
    if isinstance(model, EducationalInterpretation):
        return OfflineResult(status="educational", explanations=trait.explanations)
    if observation is not None:
        observation = Observation.model_validate(observation.model_dump())

    def unavailable(reason: UnavailableReason) -> OfflineResult:
        return OfflineResult(
            status="unavailable",
            reason=reason,
            explanations=[
                text
                for text in trait.explanations
                if text.result_key in (None, "unavailable")
            ],
        )

    if observation is None or not observation.genotype:
        return unavailable("missing_genotype")
    genotype = observation.genotype.strip().upper()
    if len(genotype) != 2 or any(allele not in "ACGT" for allele in genotype):
        return unavailable("invalid_genotype")
    requirements = model.requirements
    if not set(genotype) <= set(requirements.alleles):
        return unavailable("unsupported_allele")
    if any(
        getattr(observation, field) in (None, "")
        for field in (
            "rsid",
            "genome_build",
            "chromosome",
            "position",
            "sequence_accession",
            "orientation",
            "coordinate_system",
            "ploidy",
        )
    ):
        return unavailable("missing_representation")
    placement = next(
        (
            item
            for item in requirements.placements
            if item.genome_build == observation.genome_build
        ),
        None,
    )
    if placement is None:
        return unavailable("unsupported_build")
    if observation.orientation != requirements.orientation:
        return unavailable("unsupported_orientation")
    if (
        observation.rsid != requirements.rsid
        or observation.ploidy != requirements.ploidy
        or observation.coordinate_system != requirements.coordinate_system
        or observation.chromosome != placement.chromosome
        or observation.position != placement.position
        or observation.sequence_accession != placement.sequence_accession
    ):
        return unavailable("incompatible_representation")
    genotype = "".join(sorted(genotype))
    # The published schema requires exactly one branch for every supported pair.
    rule = next(rule for rule in model.rules if rule.genotype == genotype)
    return OfflineResult(
        status="evaluated",
        copies=rule.copies,
        explanations=[
            text
            for text in trait.explanations
            if text.result_key in (None, str(rule.copies))
        ],
    )
