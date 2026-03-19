from pydantic import BaseModel


class Variant(BaseModel):
    rsid: str
    genotype: str


class TraitResult(BaseModel):
    trait: str
    probability: float
