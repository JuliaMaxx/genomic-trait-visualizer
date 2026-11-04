from pydantic import BaseModel, ConfigDict, Field, model_validator

from .analysis import AnalysisStatus, ContributionDirection
from .catalog import (
    ContentSection,
    CuratedTraitRule,
    GenotypeInterpretation,
    TraitResultByOutcome,
    TraitResultContent,
    TraitSource,
)
from .common import AnalysisOutcome, EvidenceLevel, SearchResultKind, TraitCategory


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TraitCatalogSummary(ApiModel):
    id: str
    name: str
    category: TraitCategory
    description: str
    simple_summary: str
    technical_summary: str
    evidence_level: EvidenceLevel
    keywords: list[str]
    search_terms: list[str] = Field(min_length=1)


class TraitRuleStatus(ApiModel):
    rsid: str
    status: AnalysisStatus


class TraitCatalogDetail(ApiModel):
    id: str
    name: str
    category: TraitCategory
    description: str
    simple_summary: str
    technical_summary: str
    mental_model: list[ContentSection]
    model_limit_summary: str
    evidence_level: EvidenceLevel
    keywords: list[str]
    sources: list[TraitSource]
    result_content: TraitResultByOutcome
    practical_takeaway: list[ContentSection]
    simple_explanation: list[ContentSection]
    technical_explanation: list[ContentSection]
    research_spotlight: list[ContentSection]
    calculation_notes: list[ContentSection]
    rules: list[CuratedTraitRule] = Field(min_length=1)


class TraitAnalysisSummary(ApiModel):
    trait_id: str
    name: str
    category: TraitCategory
    description: str
    rule_statuses: list[TraitRuleStatus] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    coverage: float = Field(ge=0, le=1, allow_inf_nan=False)
    result: AnalysisOutcome
    result_badge_tooltip: str


class TraitRuleAnalysis(ApiModel):
    rsid: str
    user_genotype: list[str] | None
    interpretation: GenotypeInterpretation | None
    status: AnalysisStatus
    status_explanation: str
    contribution: ContributionDirection
    contribution_label: str
    contribution_explanation: str

    @model_validator(mode="after")
    def status_matches_observation(self) -> "TraitRuleAnalysis":
        if self.status == "missing":
            if self.user_genotype is not None or self.interpretation is not None:
                raise ValueError("missing rules cannot contain observed data")
        elif self.status == "unmatched":
            if self.user_genotype is None or self.interpretation is not None:
                raise ValueError(
                    "unmatched rules require a genotype without an interpretation"
                )
        elif self.user_genotype is None or self.interpretation is None:
            raise ValueError("matched rules require a genotype and interpretation")
        return self


class TraitAnalysisMetrics(ApiModel):
    result: AnalysisOutcome
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    coverage: float = Field(ge=0, le=1, allow_inf_nan=False)
    score: float | None
    result_content: TraitResultContent
    rules: list[TraitRuleAnalysis] = Field(min_length=1)
    calculation_explanation: list[ContentSection]

    @model_validator(mode="after")
    def score_requires_a_match(self) -> "TraitAnalysisMetrics":
        has_match = any(rule.status == "matched" for rule in self.rules)
        if has_match != (self.score is not None):
            raise ValueError(
                "a directional score is available only when a rule matched"
            )
        return self


class TraitAnalysisDetail(ApiModel):
    trait: TraitCatalogDetail
    analysis: TraitAnalysisMetrics


class RsidCatalogItem(ApiModel):
    rsid: str
    gene: str | None
    plain_english_summary: str
    trait_count: int = Field(ge=0)
    evidence_level: EvidenceLevel | None


class RsidTraitLink(ApiModel):
    trait_id: str
    trait_name: str
    category: TraitCategory
    description: str
    effect: str
    evidence_level: EvidenceLevel
    source_refs: list[str]


class RsidDetail(ApiModel):
    rsid: str
    gene: str | None
    plain_english_summary: str
    technical_summary: str
    description: str
    genotype_meanings: list[GenotypeInterpretation]
    effect_directions: list[str]
    traits: list[RsidTraitLink]
    story_sections: list[ContentSection]
    interpretation_notes: list[ContentSection]
    sources: list[TraitSource]


class SearchResult(ApiModel):
    kind: SearchResultKind
    title: str
    subtitle: str
    description: str
    url: str


class SearchResponse(ApiModel):
    query: str
    results: list[SearchResult]
