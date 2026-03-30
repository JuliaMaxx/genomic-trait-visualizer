from pydantic import BaseModel


class Variant(BaseModel):
    rsid: str
    chromosome: str
    position: int
    genotype: str | None


class TraitResult(BaseModel):
    trait: str
    probability: float


class ParseResult(BaseModel):
    variants: list[Variant]
    errors: list[str]
