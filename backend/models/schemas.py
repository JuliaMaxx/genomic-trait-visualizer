from typing import Literal, NamedTuple, NotRequired, TypedDict

from pydantic import BaseModel, Field

# =========================
# Shared Types
# =========================

TraitCategory = Literal["nutrition", "appearance", "health", "behavior"]
EvidenceLevel = Literal["strong", "moderate", "limited"]
TraitResultLabel = Literal["likely", "unlikely", "inconclusive"]


# =========================
# DNA INPUT / PARSING
# =========================


class Variant(BaseModel):
    rsid: str
    chromosome: str
    position: int
    genotype: list[str] | None


class ParseResult(BaseModel):
    variants: list[Variant]
    errors: list[str]


# =========================
# CATALOG (STATIC DATA)
# =========================


class TraitSource(BaseModel):
    name: str
    url: str
    reference: str | None = None
    notes: str | None = None


class TraitContentSection(BaseModel):
    title: str
    body: str


class TraitResultContent(BaseModel):
    card_tooltip: str
    headline: str
    headline_tooltip: str
    outcome_summary: str


class GenotypeInterpretation(BaseModel):
    genotype: list[str]
    meaning: str
    effect: str | None = None
    score: float = 0.0


class CuratedTraitRule(BaseModel):
    rsid: str
    description: str
    gene: str | None = None
    effect: str | None = None
    odds_ratio: float | None = None
    weight: float = 1.0
    priority: int | None = None
    evidence_level: EvidenceLevel | None = None
    source_refs: list[str] = Field(default_factory=list)
    default_meaning: str = "No interpretation available for this genotype."
    genotype_meanings: list[GenotypeInterpretation] = Field(default_factory=list)


class TraitDefinition(BaseModel):
    id: str
    name: str
    category: TraitCategory

    description: str
    simple_summary: str
    technical_summary: str

    evidence_level: EvidenceLevel = "moderate"

    keywords: list[str] = Field(default_factory=list)
    sources: list[TraitSource] = Field(default_factory=list)
    result_content: dict[TraitResultLabel, TraitResultContent] = Field(
        default_factory=dict
    )
    practical_takeaway: list[TraitContentSection] = Field(default_factory=list)
    simple_explanation: list[TraitContentSection] = Field(default_factory=list)
    technical_explanation: list[TraitContentSection] = Field(default_factory=list)
    research_spotlight: list[TraitContentSection] = Field(default_factory=list)
    calculation_notes: list[TraitContentSection] = Field(default_factory=list)

    rules: list[CuratedTraitRule]


class TraitCatalog(BaseModel):
    version: str = "1.0"
    traits: list[TraitDefinition]


# =========================
# INTERNAL (NOT API)
# =========================


class EvaluatedRule(NamedTuple):
    rule: CuratedTraitRule
    user_genotype: list[str] | None
    interpretation: GenotypeInterpretation | None


class TraitEvaluation(NamedTuple):
    trait: TraitDefinition

    matched_rules: list[CuratedTraitRule]
    missing_rsids: list[str]

    coverage: float
    confidence: float
    score: float
    result: TraitResultLabel

    notes: list[str]

    evaluated_rules: list[EvaluatedRule]


class RawTrait(TypedDict):
    id: str
    name: str
    category: str
    description: str
    simple_summary: str
    technical_summary: str
    evidence_level: str
    keywords: list[str]
    sources: list[dict]
    result_content: dict
    practical_takeaway: list[dict]
    simple_explanation: list[dict]
    technical_explanation: list[dict]
    research_spotlight: list[dict]
    calculation_notes: list[dict]
    rules: list[dict]


class RawCatalogDict(TypedDict, total=False):
    version: NotRequired[str]
    traits: list[RawTrait]


RawCatalog = RawCatalogDict | list[RawTrait]


# =========================
# API RESPONSE (LIST VIEW)
# =========================


class TraitResult(BaseModel):
    trait_id: str
    name: str
    category: TraitCategory
    description: str
    missing_rsids: list[str]
    matched_rsids: list[str]
    observed_rsids: list[str]
    confidence: float
    coverage: float
    result: TraitResultLabel
    simple_summary: str
    user_summary: str
    explanation_preview: str
    result_badge_tooltip: str


# =========================
# API RESPONSE (DETAIL VIEW)
# =========================


class TraitRsidDetail(BaseModel):
    rsid: str
    genotype: list[str] | None
    user_genotype: list[str] | None
    gene: str | None = None
    effect: str | None
    odds_ratio: float | None = None
    score: float | None = None
    meaning: str
    rule_description: str
    status: Literal["matched", "no_match", "missing"]
    status_explanation: str
    contribution: Literal["raises", "lowers", "neutral", "unknown"]
    contribution_label: str
    contribution_explanation: str
    weight: float
    evidence_level: EvidenceLevel | None = None
    source_refs: list[str] = Field(default_factory=list)


class TraitDetail(BaseModel):
    id: str
    name: str
    category: TraitCategory
    result: TraitResultLabel
    confidence: float
    description: str
    simple_summary: str
    technical_summary: str
    evidence_level: EvidenceLevel
    keywords: list[str]
    coverage: float
    score: float
    headline: str
    headline_tooltip: str
    outcome_summary: str
    result_badge_tooltip: str
    practical_takeaway: list[TraitContentSection] = Field(default_factory=list)
    simple_explanation: list[TraitContentSection] = Field(default_factory=list)
    technical_explanation: list[TraitContentSection] = Field(default_factory=list)
    research_spotlight: list[TraitContentSection] = Field(default_factory=list)
    calculation_summary: list[TraitContentSection] = Field(default_factory=list)
    rsids: list[TraitRsidDetail]
    sources: list[TraitSource] = Field(default_factory=list)
