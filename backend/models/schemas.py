from pydantic import BaseModel


class Variant(BaseModel):
    rsid: str
    chromosome: str
    position: int
    genotype: str | None


class ParseResult(BaseModel):
    variants: list[Variant]
    errors: list[str]


class TraitRule(BaseModel):
    rsid: str
    # TODO: should return only a list of strings even for a single case
    genotype: str | list[str]
    odds_ratio: float | None = None
    beta: float | None = None
    description: str


class TraitResult(BaseModel):
    trait_id: str
    name: str

    matched_rules: list[TraitRule]
    missing_rsids: list[str]

    confidence: float  # based on available SNPs

    notes: list[str]  # optional scientific notes
