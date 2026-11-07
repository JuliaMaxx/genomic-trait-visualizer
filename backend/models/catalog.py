"""Active legacy v2 models; the successor is staged in published_catalog.py."""

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    PositiveInt,
    model_validator,
)

from .common import EvidenceLevel, TraitCategory


class CatalogModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TraitSource(CatalogModel):
    name: str = Field(min_length=1)
    url: HttpUrl
    reference: str = Field(min_length=1)
    notes: str = Field(min_length=1)


class ContentSection(CatalogModel):
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)


class TraitResultContent(CatalogModel):
    card_tooltip: str = Field(min_length=1)
    headline: str = Field(min_length=1)
    headline_tooltip: str = Field(min_length=1)
    outcome_summary: str = Field(min_length=1)


class TraitResultByOutcome(CatalogModel):
    likely: TraitResultContent
    unlikely: TraitResultContent
    inconclusive: TraitResultContent


class GenotypeInterpretation(CatalogModel):
    genotype: list[str] = Field(min_length=1)
    meaning: str = Field(min_length=1)
    effect: str = Field(min_length=1)
    score: float = Field(ge=-1, le=1, allow_inf_nan=False)


class CuratedTraitRule(CatalogModel):
    rsid: str = Field(pattern=r"^rs\d+$")
    description: str = Field(min_length=1)
    gene: str = Field(min_length=1)
    odds_ratio: float | None = Field(gt=0, allow_inf_nan=False)
    odds_ratio_status: Literal["reported", "not_reported", "not_applicable"]
    weight: float = Field(gt=0, allow_inf_nan=False)
    priority: PositiveInt
    evidence_level: EvidenceLevel
    source_refs: list[str] = Field(min_length=1)
    genotype_meanings: list[GenotypeInterpretation] = Field(min_length=1)

    @model_validator(mode="after")
    def odds_ratio_matches_status(self) -> "CuratedTraitRule":
        if (self.odds_ratio_status == "reported") != (self.odds_ratio is not None):
            raise ValueError(
                "reported odds ratios must have a value; other states must not"
            )
        return self


class TraitDefinition(CatalogModel):
    id: str = Field(min_length=1, pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=1)
    category: TraitCategory
    description: str = Field(min_length=1)
    simple_summary: str = Field(min_length=1)
    technical_summary: str = Field(min_length=1)
    mental_model: list[ContentSection] = Field(min_length=1)
    model_limit_summary: str = Field(min_length=1)
    evidence_level: EvidenceLevel
    keywords: list[str] = Field(min_length=1)
    sources: list[TraitSource] = Field(min_length=1)
    result_content: TraitResultByOutcome
    practical_takeaway: list[ContentSection] = Field(min_length=1)
    simple_explanation: list[ContentSection] = Field(min_length=1)
    technical_explanation: list[ContentSection] = Field(min_length=1)
    research_spotlight: list[ContentSection] = Field(min_length=1)
    calculation_notes: list[ContentSection] = Field(min_length=1)
    rules: list[CuratedTraitRule] = Field(min_length=1)

    @model_validator(mode="after")
    def source_references_resolve(self) -> "TraitDefinition":
        rsids = [rule.rsid for rule in self.rules]
        if len(rsids) != len(set(rsids)):
            raise ValueError("each trait may define a given rsID only once")
        source_names = {source.name for source in self.sources}
        missing = {
            ref
            for rule in self.rules
            for ref in rule.source_refs
            if ref not in source_names
        }
        if missing:
            raise ValueError(
                f"rule source_refs do not resolve to trait sources: {sorted(missing)}"
            )
        return self


class TraitCatalog(CatalogModel):
    version: str = Field(min_length=1)
    traits: list[TraitDefinition] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_trait_ids(self) -> "TraitCatalog":
        ids = [trait.id for trait in self.traits]
        if len(ids) != len(set(ids)):
            raise ValueError("trait ids must be unique")
        return self
