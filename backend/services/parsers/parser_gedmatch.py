from fastapi.logger import logger

from backend.models import ParseResult, Variant
from backend.services.parsers.common import (
    VALID_CHROMOSOMES,
    is_standard_rsid,
    normalize_chromosome,
    normalize_genotype,
    split_line,
)


def _is_header_row(parts: list[str]) -> bool:
    if not parts:
        return False

    normalized = [part.lstrip("\ufeff").strip().lower() for part in parts]
    if normalized[0] != "rsid":
        return False

    return "position" in normalized and (
        "chromosome" in normalized or "chr" in normalized
    )


def parse_gedmatch(lines: list[str]) -> ParseResult:
    """
    Parse a GEDmatch raw DNA export into the common Variant schema.

    GEDmatch exports typically include four fields:
    - rsid, chromosome, position, genotype

    This parser also tolerates:
    - optional header rows
    - comma/tab/whitespace delimiting
    - extra whitespace around separators
    - missing genotypes and split-allele inputs
    """
    variants: list[Variant] = []
    errors: list[str] = []
    header_skipped = False

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = split_line(line)

        if not header_skipped and _is_header_row(parts):
            header_skipped = True
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

        genotype: list[str] | None
        if len(parts) >= 5:
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
