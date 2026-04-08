from fastapi.logger import logger

from backend.models.schemas import ParseResult, Variant
from backend.services.parsers.common import (
    VALID_CHROMOSOMES,
    is_standard_rsid,
    normalize_chromosome,
    normalize_genotype,
    split_line,
)


def _parse_header_row(parts: list[str]) -> dict[str, int] | None:
    if not parts:
        return None

    headers = [part.lstrip("\ufeff").strip().lower() for part in parts]
    if not headers or headers[0] != "rsid":
        return None

    if not any(
        field in headers
        for field in ("call", "genotype", "result", "allele1", "allele2")
    ):
        return None

    return {field: index for index, field in enumerate(headers)}


def _looks_like_split_alleles(allele1: str, allele2: str) -> bool:
    return bool(allele1.strip() or allele2.strip())


def parse_livingdna(lines: list[str]) -> ParseResult:
    """
    Parse a LivingDNA raw DNA export into the common Variant schema.

    LivingDNA exports are typically CSV with headers like:
    - rsid,chromosome,position,call

    This parser also tolerates:
    - tab/CSV/whitespace-delimited variants
    - optional header row
    - genotype stored in `call` or `genotype`
    - split allele columns when present
    - extra columns beyond the first four
    """
    variants: list[Variant] = []
    errors: list[str] = []
    header_fields: dict[str, int] | None = None

    for line_number, line in enumerate(lines, start=1):
        if not line or line.startswith("#"):
            continue

        parts = split_line(line)
        print(len(parts))

        if header_fields is None:
            header_fields = _parse_header_row(parts)
            if header_fields is not None:
                continue

        if len(parts) < 3:
            msg = f"Line {line_number}: invalid format"
            logger.warning(msg)
            errors.append(msg)
            continue

        rsid, chrom, pos = parts[0], parts[1], parts[2]
        rsid = rsid.lstrip("\ufeff")

        chrom = normalize_chromosome(chrom)
        if chrom not in VALID_CHROMOSOMES:
            msg = f"Line {line_number}: invalid chromosome"
            logger.warning(msg)
            errors.append(msg)
            continue

        try:
            position = int(pos)
        except ValueError:
            msg = f"Line {line_number}: invalid position"
            logger.warning(msg)
            errors.append(msg)
            continue

        if not is_standard_rsid(rsid):
            msg = f"Line {line_number}: invalid rsid"
            logger.warning(msg)
            errors.append(msg)

        genotype: str | None
        if header_fields:
            if "allele1" in header_fields and "allele2" in header_fields:
                allele1 = (
                    parts[header_fields["allele1"]]
                    if header_fields["allele1"] < len(parts)
                    else ""
                )
                allele2 = (
                    parts[header_fields["allele2"]]
                    if header_fields["allele2"] < len(parts)
                    else ""
                )
                genotype = normalize_genotype(allele1=allele1, allele2=allele2)
            else:
                field_index = header_fields.get(
                    "call",
                    header_fields.get("genotype", header_fields.get("result", 3)),
                )
                genotype = normalize_genotype(
                    genotype=parts[field_index] if field_index < len(parts) else ""
                )
        elif len(parts) >= 5 and _looks_like_split_alleles(parts[3], parts[4]):
            genotype = normalize_genotype(allele1=parts[3], allele2=parts[4])
        elif len(parts) >= 4:
            genotype = normalize_genotype(genotype=parts[3])
        else:
            genotype = None

        if genotype is None:
            msg = f"Line {line_number}: invalid genotype"
            logger.warning(msg)
            errors.append(msg)

        variants.append(
            Variant(
                rsid=rsid,
                chromosome=chrom,
                position=position,
                genotype=genotype,
            )
        )

    return ParseResult(variants=variants, errors=errors)
