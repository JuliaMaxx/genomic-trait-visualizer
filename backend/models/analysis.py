from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .catalog import CuratedTraitRule, GenotypeInterpretation, TraitDefinition
from .common import AnalysisOutcome


class AnalysisModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Variant(AnalysisModel):
    rsid: str = Field(min_length=1)
    chromosome: str = Field(min_length=1)
    position: int = Field(ge=1)
    genotype: list[str] | None


class ParseResult(AnalysisModel):
    variants: list[Variant]
    errors: list[str]


@dataclass(frozen=True)
class EvaluatedRule:
    rule: CuratedTraitRule
    user_genotype: list[str] | None
    interpretation: GenotypeInterpretation | None

    @property
    def status(self) -> Literal["missing", "unmatched", "matched"]:
        if self.user_genotype is None:
            return "missing"
        return "matched" if self.interpretation is not None else "unmatched"


@dataclass(frozen=True)
class TraitEvaluation:
    trait: TraitDefinition
    evaluated_rules: list[EvaluatedRule]
    coverage: float
    confidence: float
    score: float | None
    result: AnalysisOutcome

    @property
    def matched_rsids(self) -> list[str]:
        return [
            entry.rule.rsid
            for entry in self.evaluated_rules
            if entry.status == "matched"
        ]

    @property
    def observed_rsids(self) -> list[str]:
        return [
            entry.rule.rsid
            for entry in self.evaluated_rules
            if entry.user_genotype is not None
        ]

    @property
    def missing_rsids(self) -> list[str]:
        return [
            entry.rule.rsid
            for entry in self.evaluated_rules
            if entry.status == "missing"
        ]


AnalysisStatus = Literal["missing", "unmatched", "matched"]
ContributionDirection = Literal["raises", "lowers", "neutral", "unknown"]
