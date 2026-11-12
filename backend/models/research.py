"""Stage 5 acquisition and field proposals; scientific review stays in Stage 3."""

from typing import Literal

from pydantic import AwareDatetime, ConfigDict, Field, JsonValue, field_validator

from backend.models.curation import CurationModel, Text

SourceId = Literal["gwas_catalog", "europe_pmc"]
ResponseKind = Literal["traits", "associations", "study", "publication", "literature"]


class ResearchRequest(CurationModel):
    trait_name: str = Field(min_length=1, max_length=200)
    synonyms: list[str] = Field(default_factory=list, max_length=4)
    limit: int = Field(default=3, ge=1, le=10)

    @field_validator("trait_name", "synonyms")
    @classmethod
    def plain_terms(cls, value: str | list[str]) -> str | list[str]:
        terms = [value] if isinstance(value, str) else value
        if any(not term.strip() or len(term) > 200 for term in terms):
            raise ValueError("search terms must contain 1 to 200 characters")
        return value


class ScientificSource(CurationModel):
    source_id: SourceId
    name: Text
    base_url: Text
    documentation_url: Text
    terms_url: Text
    capabilities: list[Text]
    retention: Text


class SourceRegistry(CurationModel):
    version: Literal["stage5-sources-v1"]
    sources: list[ScientificSource]
    synonyms: dict[str, list[Text]]


class SavedResponse(CurationModel):
    document_id: Text
    source_id: SourceId
    kind: ResponseKind
    url: Text
    parameters: dict[str, str]
    query_reason: Text
    retrieved_at: AwareDatetime
    elapsed_seconds: float = Field(ge=0)
    status_code: int | None = None
    path: Text | None = None
    sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    error: Text | None = None


class ResearchRun(CurationModel):
    version: Literal["stage5-v1", "stage5-v3"] = "stage5-v3"
    request: ResearchRequest
    registry: SourceRegistry
    search_terms: list[Text]
    started_at: AwareDatetime
    completed_at: AwareDatetime
    acquisition_seconds: float = Field(ge=0)
    responses: list[SavedResponse]
    warnings: list[str]


class RawRecord(CurationModel):
    """One record's untouched values and its locations in retained API bytes."""

    model_config = ConfigDict(str_strip_whitespace=False)

    record_id: Text
    kind: Literal["association", "study", "publication", "ontology"]
    document_id: Text
    locator: str  # JSON Pointer: the empty string identifies the document root.
    found_by: list[Text]
    fields: dict[str, JsonValue]


class FieldProposal(CurationModel):
    model_config = ConfigDict(str_strip_whitespace=False)

    field: Text
    reported_value: JsonValue
    proposed_value: JsonValue
    source_location: Text
    transformation: Text = "Copied without scientific reinterpretation."
    review_status: Literal["pending"] = "pending"


class NormalizedRecord(CurationModel):
    record_id: Text
    fields: list[FieldProposal]
    unresolved: list[Text]


class Extraction(CurationModel):
    extractor_version: Literal["stage5-v9", "stage5-v10"] = "stage5-v10"
    records: list[RawRecord]
    ontology_candidates: list[RawRecord] = Field(default_factory=list)
    warnings: list[str]
