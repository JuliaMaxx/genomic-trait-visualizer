"""Stage 2 interpretation data contracts. No uploaded genotypes are evaluated here."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Allele = Literal["A", "C", "G", "T"]
ClaimId = Annotated[str, Field(min_length=1)]


class InterpretationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class VariantPlacement(InterpretationModel):
    genome_build: Literal["GRCh37", "GRCh38"]
    chromosome: str = Field(pattern=r"^(?:[1-9]|1[0-9]|2[0-2])$")
    position: int = Field(gt=0, strict=True)
    sequence_accession: str = Field(pattern=r"^NC_\d+\.\d+$")


class VariantRequirements(InterpretationModel):
    rsid: str = Field(pattern=r"^rs\d+$")
    placements: list[VariantPlacement] = Field(min_length=1)
    orientation: Literal["forward_genomic"]
    coordinate_system: Literal["1-based"]
    ploidy: Literal[2]
    alleles: list[Allele] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def unambiguous_representation(self) -> "VariantRequirements":
        if len(set(self.alleles)) != 2:
            raise ValueError("requirements need two distinct SNV alleles")
        builds = [placement.genome_build for placement in self.placements]
        if len(set(builds)) != len(builds):
            raise ValueError("requirements allow only one placement per genome build")
        return self


class AlleleCountRule(InterpretationModel):
    genotype: str
    copies: int = Field(ge=0, le=2, strict=True)

    @field_validator("genotype")
    @classmethod
    def normalize_genotype(cls, value: str) -> str:
        # Only allele order and case vary. Separators and partial calls are invalid.
        value = value.upper()
        if len(value) != 2 or any(allele not in "ACGT" for allele in value):
            raise ValueError("rule genotype must contain exactly two SNV alleles")
        return "".join(sorted(value))


class AlleleCountInterpretation(InterpretationModel):
    strategy: Literal["allele_count"]
    claim_ids: list[ClaimId] = Field(min_length=1)
    requirements: VariantRequirements
    counted_allele: Allele
    rules: list[AlleleCountRule] = Field(min_length=1)
    unavailable_policy: Literal["withhold"]

    @model_validator(mode="after")
    def rules_match_requirements(self) -> "AlleleCountInterpretation":
        if self.counted_allele not in self.requirements.alleles:
            raise ValueError("counted allele must be supported by requirements")
        genotypes = [rule.genotype for rule in self.rules]
        if len(set(genotypes)) != len(genotypes):
            raise ValueError("normalized genotype rules overlap")
        for rule in self.rules:
            if not set(rule.genotype) <= set(self.requirements.alleles):
                raise ValueError("rule genotype contains incompatible alleles")
            if rule.copies != rule.genotype.count(self.counted_allele):
                raise ValueError("rule copies must match the counted allele")
        return self


class EducationalInterpretation(InterpretationModel):
    strategy: Literal["educational"]
    claim_ids: list[ClaimId] = Field(min_length=1)
