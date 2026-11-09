"""Independently authored cases: expected answers are inputs, never generated."""

from itertools import product
from typing import Any, Literal

from pydantic import Field, model_validator

from backend.models.curation import CurationModel, Text, require_unique_ids
from backend.models.interpretation import EducationalInterpretation
from backend.models.published_catalog import PublishedTrait
from backend.services.trait_curation.offline import Observation, Outcome, evaluate


class ExpectedCase(CurationModel):
    case_id: Text
    disposition: Literal["required", "deferred"] = "required"
    rationale: Text
    observation: Observation | None = None
    expected: Outcome | None = None

    @model_validator(mode="after")
    def expected_only_when_resolved(self) -> "ExpectedCase":
        if (self.disposition == "required") != (self.expected is not None):
            raise ValueError(
                "required cases need expectations; deferred cases must not"
            )
        return self


class ExpectedCases(CurationModel):
    case_set_id: Text
    trait_id: Text
    basis: Text
    kind: Literal["synthetic", "reference"]
    cases: list[ExpectedCase] = Field(min_length=1)

    @model_validator(mode="after")
    def distinct_cases(self) -> "ExpectedCases":
        require_unique_ids([case.case_id for case in self.cases], "case IDs")
        if not any(case.disposition == "required" for case in self.cases):
            raise ValueError("at least one required independent case is needed")
        return self


def _check_coverage(trait: PublishedTrait, cases: ExpectedCases) -> None:
    """Require meaningful coverage without manufacturing any expected answers."""
    if cases.trait_id != trait.id:
        raise ValueError("Expected cases belong to another trait")
    required = [case for case in cases.cases if case.disposition == "required"]
    model = trait.interpretation
    if isinstance(model, EducationalInterpretation):
        if not any(case.observation is None for case in required) or not any(
            case.observation is not None for case in required
        ):
            raise ValueError("Educational cases must cover absent and supplied input")
        return
    requirements = model.requirements
    # Check both orders at every approved placement, independent of the rule table.
    for placement in requirements.placements:
        for pair in product(requirements.alleles, repeat=2):
            genotype = "".join(pair)
            if not any(
                case.observation is not None
                and case.observation.genotype == genotype
                and all(
                    getattr(case.observation, key) == value
                    for key, value in {
                        **placement.model_dump(),
                        "rsid": requirements.rsid,
                        "orientation": requirements.orientation,
                        "coordinate_system": requirements.coordinate_system,
                        "ploidy": requirements.ploidy,
                    }.items()
                )
                for case in required
            ):
                raise ValueError(
                    f"Independent cases missing {placement.genome_build} {genotype}"
                )
    reasons = {case.expected.reason for case in required if case.expected is not None}
    needed = {
        "missing_genotype",
        "invalid_genotype",
        "unsupported_allele",
        "missing_representation",
        "unsupported_build",
        "unsupported_orientation",
        "incompatible_representation",
    }
    if missing := needed - reasons:
        raise ValueError(f"Independent unavailable cases missing: {sorted(missing)}")


def verify_cases(trait: PublishedTrait, cases: ExpectedCases) -> dict[str, Any]:
    cases = ExpectedCases.model_validate(cases.model_dump(mode="json"))
    _check_coverage(trait, cases)
    results: list[dict[str, Any]] = []
    for case in cases.cases:
        if case.disposition == "deferred":
            results.append(
                {
                    "case_id": case.case_id,
                    "state": "deferred",
                    "rationale": case.rationale,
                }
            )
            continue
        result = evaluate(trait, case.observation)
        actual = Outcome.model_validate(result.model_dump(exclude={"explanations"}))
        results.append(
            {
                "case_id": case.case_id,
                "state": "passed" if actual == case.expected else "failed",
                "observation": (
                    case.observation.model_dump() if case.observation else None
                ),
                "expected": case.expected.model_dump() if case.expected else None,
                "actual": actual.model_dump(),
                "content_ids": [text.content_id for text in result.explanations],
                "rationale": case.rationale,
            }
        )
    return {
        "case_set_id": cases.case_set_id,
        "kind": cases.kind,
        "basis": cases.basis,
        "passed": all(item["state"] != "failed" for item in results),
        "cases": results,
    }
